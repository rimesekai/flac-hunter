"""曲库索引与三层查重、ffprobe 时长缓存、重复聚类。

蓝本：prepare.py:124-141（两级索引）、prepare.py:167-182（三层查重）、
verify_duration_first.py:60-87（时长缓存）、find_dups.py:26-89（聚类与归一键）。
文件名约定（prepare.py:129-131 与 find_dups.py:72 一致）：标题在前、艺人在后，
即 "Title - Artist1 _ Artist2.flac"；文件 artist 键按 prepare.py:52-56 语义归一
（lower、剥非法字符，括号内文字原样拼接，如 'Other (cover)' -> 'othercover'）。
nk/core_key/is_cover_like/artist_variants 来自 flac_hunter.match（前置模块）。
"""
import json
import os
import re
import time
import unicodedata
from pathlib import Path

from flac_hunter.ffmpeg import probe_duration, probe_meta
from flac_hunter.match.blacklist import ARTIST_ALIAS_GROUPS, is_cover_like
from flac_hunter.match.normalize import artist_variants, core_key, norm_text

AUDIO_EXT = {".flac", ".mp3", ".ogg", ".m4a", ".opus", ".wav"}

# 运行产物目录（tasks/ 被 .gitignore 覆盖）
_REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = _REPO_ROOT / "tasks"
DURATIONS_CACHE_NAME = "local_durations.json"


def artist_norm(s):
    """artist 基础归一（prepare.py:52-55）：NFKC -> lower -> 剥尾部 hires -> 剥非法字符。

    括号本身被剥掉但括号内文字保留拼接：'Other (cover)' -> 'othercover'。
    """
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"[\s._]*hires$", "", s.strip())
    s = re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]+", "", s)
    return s


def _alias_groups_from_cfg(cfg):
    """合并内置 ARTIST_ALIAS_GROUPS 与 config [aliases] art_aliases。

    兼容 Config dataclass、dict 与 None；art_aliases 支持 dict(canon->别名列表) 与列表套列表。
    """
    groups = [list(g) for g in ARTIST_ALIAS_GROUPS]
    raw = None
    if isinstance(cfg, dict):
        raw = (cfg.get("aliases") or {}).get("art_aliases")
    elif cfg is not None:
        aliases_obj = getattr(cfg, "aliases", None)
        if isinstance(aliases_obj, dict):
            raw = aliases_obj.get("art_aliases")
        elif aliases_obj is not None:
            raw = getattr(aliases_obj, "art_aliases", None)
    if not raw:
        return groups
    if isinstance(raw, dict):
        for canon, others in raw.items():
            if isinstance(others, (list, tuple, set)):
                groups.append([canon, *others])
            elif others:
                groups.append([canon, others])
    else:
        for g in raw:
            if isinstance(g, (list, tuple, set)):
                groups.append(list(g))
    return groups


def _merge_norm_groups(groups):
    """将有交集的归一化别名集合并，确保内置组与用户扩展组共用同一等价类。"""
    merged = []
    for group in groups:
        normed = {artist_norm(x) for x in group}
        normed.discard("")
        if not normed:
            continue
        hit = [g for g in merged if g & normed]
        if not hit:
            merged.append(normed)
        else:
            rest = [g for g in merged if not (g & normed)]
            combined = set(normed)
            for g in hit:
                combined |= g
            rest.append(combined)
            merged = rest
    return merged


def _canon_map(groups):
    """{归一成员: canon}，canon = sorted(归一组)[0]（蓝本 prepare.py:29-33 / find_dups.py:39-43）。"""
    m = {}
    for normed in _merge_norm_groups(groups):
        canon = sorted(normed)[0]
        for x in normed:
            m[x] = canon
    return m


def artist_key(s, canon_map=None):
    """文件 artist 键：artist_norm 后经别名表规范到组 canon（find_dups.py:35-43）。"""
    n = artist_norm(s)
    if canon_map and n in canon_map:
        return canon_map[n]
    return n


def norm_title_dups(s):
    """find_dups 分组标题键（find_dups.py:26-32）：保留半角化后的括号内容，与 norm_text 不同。"""
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"\((explicit|feat\.?[^)]*)\)|\[explicit\]", "", s)
    s = re.sub(r"[（【\[]", "(", s).replace("）", ")").replace("】", ")").replace("]", ")")
    s = re.sub(r'[\\/:*?"<>|]', "", s)
    s = re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff()]+", "", s)
    return s


class LibraryIndex:
    """曲库文件索引：stem 按 ' - ' 分割注册两组 (title, artist)，各建 nk 与 core_key 两级索引。

    import 无 IO；scan() 显式扫描，dedupe_track() 做三层查重。
    """

    def __init__(self, music_dir, cfg=None):
        self.music_dir = Path(music_dir)
        self.cfg = cfg
        alias_groups = _alias_groups_from_cfg(cfg)
        self._canon_map = _canon_map(alias_groups)
        self._norm_groups = _merge_norm_groups(alias_groups)  # 内置+cfg 别名组的归一形态（track 侧展开用）
        self.by_file = {}    # file -> entry（首个 combo 注册的那份）
        self.index_full = {}  # norm_text(title) -> [entry]
        self.index_core = {}  # core_key(title) -> [entry]
        self.durations = {}   # file -> 秒（缓存文件载入 + 按需 probe）
        self._load_duration_cache()

    # ---- 索引（蓝本 prepare.py:124-141）----

    def scan(self):
        """平铺扫描曲库目录，构建两级标题索引。"""
        self.by_file.clear()
        self.index_full.clear()
        self.index_core.clear()
        try:
            names = os.listdir(self.music_dir)
        except FileNotFoundError:
            return self
        for f in names:
            p = Path(f)
            if p.suffix.lower() not in AUDIO_EXT:
                continue
            stem = p.stem
            parts = stem.split(" - ")
            # 每个 ' - ' 分割点都注册一次，标题含 ' - ' 也能匹配
            combos = [(parts[0], " - ".join(parts[1:]))]
            if len(parts) > 2:
                combos.append((" - ".join(parts[:-1]), parts[-1]))
            seen_pairs = set()
            for title_part, artist_part in combos:
                entry = {
                    "file": f,
                    "path": os.path.abspath(self.music_dir / f),
                    "title": title_part,
                    "artist": artist_part,
                    "artist_key": artist_key(artist_part, self._canon_map),
                    "nk": norm_text(title_part),
                    "core": core_key(title_part),
                }
                if f not in self.by_file:
                    self.by_file[f] = entry
                for idx, key in ((self.index_full, entry["nk"]),
                                 (self.index_core, entry["core"])):
                    if key and (f, key) not in seen_pairs:
                        seen_pairs.add((f, key))
                        idx.setdefault(key, []).append(entry)
        return self

    def _file_duration(self, filename):
        """时长：先查缓存，缺失才 probe 并写回内存（蓝本 prepare.py:119-120 probe_cache 语义）。"""
        if filename in self.durations:
            return self.durations[filename]
        d = probe_duration(self.music_dir / filename)
        self.durations[filename] = d
        return d

    def _load_duration_cache(self):
        path = self._cache_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.durations.update(data)
            except Exception:
                pass  # 缓存损坏按无缓存处理

    def _cache_path(self):
        return _resolve_tasks_dir(self.cfg) / DURATIONS_CACHE_NAME

    # ---- 三层查重（蓝本 prepare.py:167-182）----

    def _track_artist_keys(self, track):
        """track 各歌手的归一键集合 + 别名组展开（match.normalize.artist_variants 与 cfg 组并集）。"""
        keys = set()
        for a in track.get("artists") or []:
            n = artist_norm(a)
            if not n:
                continue
            keys.add(n)
            keys |= {v for v in artist_variants(a) if v}  # 蓝本 download.py:61-68 语义
            for group in self._norm_groups:
                if n in group:
                    keys |= group
        return keys

    def dedupe_track(self, track):
        """三层查重。返回 (命中 entry | None, reason)。

        reason：'artist'（命中文件）/ 'duration'（命中文件）/ 'same_title_other'（照常下载）/ 'new'。
        ① 艺人层：track 任一歌手（含别名展开）与文件 artist 键双向子串（双方非空）；
        ② 标题层：nk 或 core_key 相等 且 时长差<=3s 且非 is_cover_like——被排除的文件
           不在本层返回，落到第③层（防 'Other (cover)' 被按时长判重）；
        ③ 同标题候选存在但①②未命中 -> (None, 'same_title_other')，照常下载。
        标题归一化后必须双方非空才比较——空串 in 一切陷阱。
        """
        tk = norm_text(track.get("name") or "")
        tcore = core_key(track.get("name") or "")
        # 候选：nk 与 core_key 两级索引合并（蓝本 prepare.py:156-162）
        cands = {}
        if tk:
            for e in self.index_full.get(tk, []):
                cands[e["file"]] = e
        if tcore:
            for e in self.index_core.get(tcore, []):
                cands.setdefault(e["file"], e)
        cands = list(cands.values())

        # ① 艺人层（蓝本 prepare.py:167-171，扩展为任一歌手 + 别名展开）
        t_keys = self._track_artist_keys(track)
        for c in cands:
            ck = c["artist_key"]
            if not ck:
                continue
            for ak in t_keys:
                if ak and (ak in ck or ck in ak):
                    return c, "artist"

        # ② 标题+时长层（蓝本 prepare.py:173-178）
        sdur = (track.get("duration_ms") or 0) / 1000
        if sdur:
            for c in cands:
                if is_cover_like(c["file"]):
                    continue  # cover 类文件禁按时长判重，落到第③层
                cd = self._file_duration(c["file"])
                if cd and abs(cd - sdur) <= 3:
                    return c, "duration"

        # ③ 同标题不同歌手/版本（蓝本 prepare.py:179-182）
        if cands:
            return None, "same_title_other"
        return None, "new"


# ---- 时长缓存（蓝本 verify_duration_first.py:60-87）----

def ffprobe_dur(path, attempts=2):
    """单文件时长探测，失败重试 attempts 次（间隔 0.5s），仍失败返回 None。"""
    for _ in range(attempts):
        d = probe_duration(path)
        if d is not None:
            return d
        time.sleep(0.5)
    return None


def load_durations_cache(path):
    """读时长缓存 JSON；缺失/损坏返回 {}。"""
    p = Path(path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def save_durations_cache(path, cache):
    """写时长缓存 JSON（父目录不存在则创建）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def _resolve_tasks_dir(cfg):
    """从 Config dataclass 或 dict 解析 tasks_dir，缺省回退 TASKS_DIR。"""
    tasks = None
    if isinstance(cfg, dict):
        tasks = cfg.get("tasks_dir")
        if not tasks and isinstance(cfg.get("paths"), dict):
            tasks = cfg["paths"].get("tasks_dir")
    elif cfg is not None:
        tasks = getattr(cfg, "tasks_dir", None)
        if not tasks:
            paths = getattr(cfg, "paths", None)
            if isinstance(paths, dict):
                tasks = paths.get("tasks_dir")
            elif paths is not None:
                tasks = getattr(paths, "tasks_dir", None)
    return Path(tasks) if tasks else TASKS_DIR


def _default_cache_path(cfg):
    return _resolve_tasks_dir(cfg) / DURATIONS_CACHE_NAME


def build_durations_cache(music_dir, cfg=None, cache_path=None, print_fn=print):
    """全库时长缓存：只探缺失/None 的文件，每 50 个增量落盘；单文件重试 2 次后记 None。"""
    cache_path = Path(cache_path) if cache_path else _default_cache_path(cfg)
    cache = load_durations_cache(cache_path)
    music_dir = Path(music_dir)
    files = [f for f in os.listdir(music_dir) if Path(f).suffix.lower() in AUDIO_EXT]
    todo = [f for f in files if f not in cache or cache[f] is None]
    if print_fn:
        print_fn(f"duration cache: {len(files)} files, probing {len(todo)} missing...")
    for i, f in enumerate(todo, 1):
        cache[f] = ffprobe_dur(music_dir / f)  # 失败记 None，下次重探
        if i % 50 == 0:
            save_durations_cache(cache_path, cache)
            if print_fn:
                print_fn(f"  probed {i}/{len(todo)}")
    save_durations_cache(cache_path, cache)
    return cache


# ---- 重复聚类（蓝本 find_dups.py:62-89）----

def find_dups(music_dir, cfg=None, print_fn=print):
    """按 (norm_title, artist_key) 聚类重复文件，返回 len>1 的组（list[dict]）。

    时长语义严格按蓝本 find_dups.py:82：仅当组首与当前文件 probe 时长均非 None 且差<=3s
    才并入；任一方未知（探测失败/0 字节）不并入，另起同键新组。
    标题/艺人键双方非空才比较（防空串 in 一切陷阱；蓝本 find_dups.py:80 无此防护，此处加固）。
    """
    canon_map = _canon_map(_alias_groups_from_cfg(cfg))
    music_dir = Path(music_dir)
    files = sorted(f for f in os.listdir(music_dir) if Path(f).suffix.lower() in AUDIO_EXT)
    dur_cache = {}
    for f in files:
        try:
            meta = probe_meta(music_dir / f)  # {'duration','bit_rate','tags'}
        except Exception:
            meta = {"duration": None, "bit_rate": None, "tags": {}}
        if not isinstance(meta, dict):
            meta = {"duration": None, "bit_rate": None, "tags": {}}
        dur_cache[f] = meta

    clusters = []
    for f in files:
        stem = Path(f).stem
        if " - " in stem:
            title, artist = stem.rsplit(" - ", 1)
        else:
            title, artist = stem, ""
        key = (norm_title_dups(title), artist_key(artist, canon_map))
        d = dur_cache[f].get("duration")
        br = dur_cache[f].get("bit_rate")
        placed = False
        for kt, ka, members in clusters:
            if kt and key[0] and kt == key[0] and ka and key[1] and \
                    (ka == key[1] or ka in key[1] or key[1] in ka):
                ref = dur_cache[members[0][0]].get("duration")
                if ref and d and abs(ref - d) <= 3:
                    members.append((f, d, br))
                    placed = True
                    break
        if not placed:
            clusters.append((key[0], key[1], [(f, d, br)]))

    out = []
    for kt, ka, members in clusters:
        if len(members) > 1:
            out.append({
                "title_key": kt,
                "artist_key": ka,
                "members": [{"file": f, "duration": d, "bit_rate": br} for f, d, br in members],
            })
    out.sort(key=lambda g: -len(g["members"]))
    if print_fn:
        print_fn(f"total audio: {len(files)} | duplicate groups: {len(out)}")
    return out
