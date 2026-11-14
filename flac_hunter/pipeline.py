"""下载编排：逐 track 选源→搜索→打分/分档→下载→验证→sidecar→safe-replace 落库。

蓝本：download.py:119-211/249-282（打分、封面、转码、yt-dlp）、download_bili.py:225-403
（score_bili、低置信、三段式）、hunt_last3.py:477-718（候选池→阶梯→下载→验证→落位）。

零网络约定：sources 参数可注入假源、sidecars=False 跳过封面/歌词、lyrics_fetcher 可注入；
默认路径的搜索/下载仅在真实源实例上发生。
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import random
import re
import time
from pathlib import Path

from .config import REPO_ROOT
from .console import setup_console
from .sources.base import track_duration_s
from .util import cross_move, download_stream, guess_ext_from_url

try:  # 入口模块 UTF-8 输出保护
    import sys as _sys
    for _s in (_sys.stdout, _sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
except Exception:
    pass

# FLAC 优先（用户裁定 2026-11-15）：yt-dlp 渠道（bili/youtube bestaudio）只有 AAC/Opus
# 拿不到无损，musicdl 音乐平台源实测可返回 flac 候选，故排在视频站之前
SOURCE_ORDER = ("gdstudio", "netease", "musicdl", "bili", "youtube")

STATUS_DOWNLOADED = "downloaded"
STATUS_EXISTS = "exists"
STATUS_LOW_CONFIDENCE = "low_confidence"
STATUS_NO_RESULT = "no_result"
STATUS_SEARCH_FAILED = "search_failed"
STATUS_FAILED = "failed"
STATUS_NO_SOURCE = "no_source"
STATUS_ALL = {STATUS_DOWNLOADED, STATUS_EXISTS, STATUS_LOW_CONFIDENCE,
              STATUS_NO_RESULT, STATUS_SEARCH_FAILED, STATUS_FAILED, STATUS_NO_SOURCE}

LOSSLESS_BR = 999000   # gdstudio/netease 无损命中码率下限（999999 表示无损）
MIN_DUR = 20.0         # 下载验证时长下限（蓝本 upgrade_ogg.py:215 同款设计）
YT_MIN_SCORE = 50.0    # youtube 候选最低分（蓝本 download.py 阈值）
GD_NETEASE = ("gdstudio", "netease")

_TASKS_DIR = REPO_ROOT / "tasks"      # 运行产物目录（results.jsonl 所在）
_RESULTS = "results.jsonl"

# 默认源注册表：源名 -> (模块名, 类名)
_SOURCE_SPECS = {
    "gdstudio": ("flac_hunter.sources.gdstudio", "GdStudioSource"),
    "netease": ("flac_hunter.sources.netease", "NeteaseSource"),
    "bili": ("flac_hunter.sources.bilibili", "BilibiliSource"),
    "youtube": ("flac_hunter.sources.youtube", "YtDlpSource"),
    "musicdl": ("flac_hunter.sources.musicdl_ext", "MusicDlSource"),
}


def _rm(path: Path | str | None) -> None:
    """删文件，失败静默（半成品清理）。"""
    if not path:
        return
    try:
        Path(path).unlink()
    except OSError:
        pass


# ---------- 运行产物 ----------

def tasks_dir() -> Path:
    """运行产物目录（仓库根 tasks/，被 .gitignore 覆盖）。"""
    return _TASKS_DIR


def _accepts_kw(fn, name: str) -> bool:
    """检查可调用对象是否接受指定关键字参数或 **kwargs。"""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False
    return name in params or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )


def _load_done_uris(tasks: Path, music_dir: Path | None = None) -> set:
    """断点续跑：results.jsonl 中 status==downloaded 且目标文件仍存在的 uri 集合。"""
    done: set = set()
    try:
        with open(tasks / _RESULTS, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if not (isinstance(r, dict) and r.get("status") == STATUS_DOWNLOADED):
                    continue
                uri = r.get("uri")
                if not uri:
                    continue
                p = r.get("path")
                if p:
                    if Path(p).exists():
                        done.add(uri)
                elif music_dir is not None and r.get("file"):
                    if (Path(music_dir) / str(r["file"])).exists():
                        done.add(uri)
    except OSError:
        pass
    return done


def _append_result(tasks: Path, rec: dict) -> None:
    """逐曲追加一行 JSON 到 results.jsonl。"""
    with open(tasks / _RESULTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


# ---------- 别名 / 变体（match 层缺失时降级） ----------

def _alias_groups(cfg) -> list:
    """内置 14 组 + config [aliases] art_aliases 合并的别名组列表。"""
    try:
        from .match.normalize import cfg_alias_groups
        return list(cfg_alias_groups(cfg))
    except Exception:
        pass
    groups: list = []
    try:
        from .match.blacklist import ARTIST_ALIAS_GROUPS
        groups.extend(ARTIST_ALIAS_GROUPS)
    except Exception:
        pass
    aliases = cfg.get("aliases") if isinstance(cfg, dict) else getattr(cfg, "aliases", None)
    art = (aliases.get("art_aliases") if isinstance(aliases, dict)
           else getattr(aliases, "art_aliases", None)) or {}
    if isinstance(art, dict):
        for k, vs in art.items():
            if isinstance(vs, (list, tuple, set)):
                groups.append({k, *vs})
    return groups


def _artist_variants(name: str, alias_groups: list) -> set:
    """艺人归一化变体并集；match 层缺失时退化为简单 lower。"""
    try:
        from .match.normalize import artist_variants
        return set(artist_variants(name, alias_groups))
    except Exception:
        return {str(name or "").strip().lower()} - {""}


def _alt_titles(track, cfg) -> list:
    """曲名别名：match.normalize.alt_titles_for 优先（吃 config alt_titles 条目）。"""
    name = str(track.get("name") or "")
    artists = track.get("artists") or []
    artist0 = str(artists[0]) if artists else ""
    entries = getattr(getattr(cfg, "aliases", None), "alt_titles", None) or []
    try:
        from .match.normalize import alt_titles_for
        if _accepts_kw(alt_titles_for, "alias_groups"):
            return list(alt_titles_for(name, artist0, entries, alias_groups=_alias_groups(cfg)))
        return list(alt_titles_for(name, artist0, entries))
    except Exception:
        pass
    out: list = []
    for e in entries:
        if str(e.get("title") or "") == name and (not e.get("artist") or str(e.get("artist")) == artist0):
            out.extend(e.get("alts") or [])
    return list(dict.fromkeys(out))


def _virtual_set(cfg) -> set:
    """虚拟歌手集合：blacklist 内置 + config 追加（归一化后）。"""
    virt: set = set()
    try:
        from .match.blacklist import VIRTUAL_SINGERS
        virt |= set(VIRTUAL_SINGERS)
    except Exception:
        pass
    try:
        from .match.normalize import norm_text
        virt |= {norm_text(v) for v in (getattr(cfg.aliases, "virtual_singers", None) or [])}
    except Exception:
        virt |= {str(v).strip().lower() for v in (getattr(cfg.aliases, "virtual_singers", None) or [])}
    return virt


def _filename_stem(track) -> str:
    """落位文件名主干：track['filename_stem'] 优先，缺失按 "<名> - <艺人 _ 连接>" 构造。"""
    stem = track.get("filename_stem")
    if stem:
        s = str(stem)
        if s.endswith(" - ") or (not track.get("artists") and s.endswith(" -")):
            s = re.sub(r" -\s*$", "", s)
        return s.strip().rstrip(".")
    name = str(track.get("name") or "")
    artists = [str(a).strip() for a in (track.get("artists") or []) if str(a).strip()]
    raw = f"{name} - {' _ '.join(artists)}" if artists else name
    try:
        from .match.normalize import sanitize
        return sanitize(raw)
    except Exception:
        raw = re.sub(r'[\\/:*?"<>|]', "_", raw)
        return raw.strip().rstrip(".")


# ---------- 源实例与码率解析 ----------

def _source_name(src) -> str:
    """源对象名：name 属性（实例或类），缺失返回空串。"""
    n = getattr(src, "name", None)
    if n is None:
        n = getattr(type(src), "name", "")
    return str(n or "")


def _default_sources(cfg, source: str = "auto") -> list:
    """按 SOURCE_ORDER 实例化默认源；单源指定时只实例化该源。模块缺失则跳过。"""
    order = SOURCE_ORDER if source == "auto" else (source,)
    out: list = []
    for sname in order:
        spec = _SOURCE_SPECS.get(sname)
        if not spec:
            continue
        try:
            mod = importlib.import_module(spec[0])
            cls = getattr(mod, spec[1])
            out.append(cls(cfg))
        except Exception:
            continue
    return out


def _gd_resolver(srcs, cfg):
    """GDStudio 直链/码率解析器：仅当源列表含真实 GdStudioSource/NeteaseSource 实例时
    复用/新建（注入的假 gd/netease 名源不触网）。"""
    real = False
    for s in srcs or ():
        if type(s).__name__ in ("GdStudioSource", "NeteaseSource"):
            real = True
            if type(s).__name__ == "GdStudioSource":
                return s
    if not real:
        return None
    try:
        from .sources.gdstudio import GdStudioSource
        return GdStudioSource(cfg)
    except Exception:
        return None


def _resolve_br_gd(gd_resolver, cand) -> tuple:
    """确定 (url, br)：extra['br'] 优先；url 后缀 .flac 视为无损；
    否则经 GDStudio types=url 阶梯（999999→320000→128000）解析并写回候选。"""
    extra = cand.get("extra") or {}
    url = str(cand.get("url") or "")
    br = extra.get("br")
    if isinstance(br, (int, float)) and not isinstance(br, bool) and br > 0:
        return url, int(br)
    if url and url.split("?")[0].lower().endswith(".flac"):
        return url, 999999
    if gd_resolver is None:
        return url, None
    sub = extra.get("gd_source") or "netease"
    try:
        u, b, _size = gd_resolver.get_url(sub, str(cand.get("id") or ""))
    except Exception:
        return url, None
    if u:
        cand["url"] = u
        if isinstance(cand.get("extra"), dict):
            cand["extra"]["br"] = b
        return u, int(b or 0)
    return url, None


# ---------- 候选挑选 ----------

def _match_picks(cand: dict, picks: list[str]) -> bool:
    """候选是否命中 picks（id 精确命中或 title 含任一非空子串）。"""
    if not picks:
        return False
    cid = str(cand.get("id") or "")
    ctitle = str(cand.get("title") or "")
    return any(p and (p == cid or p in ctitle) for p in picks)


def _evaluate_source(sname, src, cands, track, cfg, alts, others, gd_resolver) -> tuple:
    """按源类型挑选可接受候选。返回 (cand, score)；无合格候选返回 (None, 最高落选分或 None)。

    - manual_picks（id 或 title 非空子串）在所有源中优先级最高
    - gdstudio/netease：tier_of=='A' 且经阶梯解析 br≥999000（无损命中）
    - bili：score_bili≥min_video_score 且非低置信（分数<55 或时长差>60）
    - youtube：score_youtube≥50（注意冻结参数序 cand, track）
    - musicdl/其他注入源：tier_of=='A'；同档内按 quality（无损 > 320 > 其余）取最优
    """
    from .match.score import bili_low_confidence, pick_best, score_bili, score_youtube
    from .match.tier import tier_of, tier_sort_key

    aliases_cfg = getattr(cfg, "aliases", None)
    no_picks = [str(x) for x in (getattr(aliases_cfg, "no_picks", None) or []) if str(x)]
    if no_picks:
        cands = [c for c in cands if isinstance(c, dict) and not _match_picks(c, no_picks)]
    manual_picks = [str(x) for x in (getattr(aliases_cfg, "manual_picks", None) or []) if str(x)]
    manual_cands = [c for c in cands if isinstance(c, dict) and _match_picks(c, manual_picks)]

    sdur = track_duration_s(track)
    name = str(track.get("name") or "")
    artists = track.get("artists") or []
    artist0 = str(artists[0]) if artists else ""
    name_aliases = [name] + [a for a in alts if a]
    alias_groups = _alias_groups(cfg)
    aliases = sorted(_artist_variants(artist0, alias_groups)) if artist0 else []
    search_win = getattr(getattr(cfg, "match", None), "search_win", 8.0)

    def _tier(c):
        if _accepts_kw(tier_of, "search_win"):
            return tier_of(c, sdur, name, aliases, name_aliases, search_win=search_win)
        return tier_of(c, sdur, name, aliases, name_aliases)

    if sname in GD_NETEASE:
        if manual_cands:
            resolved_manual = []
            for c in manual_cands:
                u, br = _resolve_br_gd(gd_resolver, c)
                if br is not None and br >= LOSSLESS_BR:
                    return c, None
                resolved_manual.append((c, u, br))
            for c, u, _br in resolved_manual:
                if u or gd_resolver is None or sname == "netease":
                    return c, None
        tiered = [c for c in cands if _tier(c) == "A"]
        tiered.sort(key=lambda c: tier_sort_key(c, "A", sdur))
        for c in tiered:
            _url, br = _resolve_br_gd(gd_resolver, c)
            if br is None or br < LOSSLESS_BR:
                continue  # 非无损（mp3/m4a/128k/无法确认）不算命中，换下一候选
            return c, None
        return None, None

    if sname == "bili":
        bili_kw = {"alts": alts, "other_artists": others}
        if _accepts_kw(score_bili, "alias_groups"):
            bili_kw["alias_groups"] = alias_groups
        if manual_cands:
            best_m = pick_best(manual_cands, track, lambda t, c: score_bili(t, c, **bili_kw))
            return best_m, score_bili(track, best_m, **bili_kw)
        best = pick_best(cands, track, lambda t, c: score_bili(t, c, **bili_kw))
        if best is None:
            return None, None
        sc = score_bili(track, best, **bili_kw)
        if sc >= cfg.match.min_video_score and not bili_low_confidence(sc, best, track):
            return best, sc
        return None, sc

    if sname == "youtube":
        yt_kw = {"alias_groups": alias_groups} if _accepts_kw(score_youtube, "alias_groups") else {}
        if manual_cands:
            best_m = pick_best(manual_cands, track, lambda t, c: score_youtube(c, t, **yt_kw))
            return best_m, score_youtube(best_m, track, **yt_kw)
        best = pick_best(cands, track, lambda t, c: score_youtube(c, t, **yt_kw))
        if best is None:
            return None, None
        sc = score_youtube(best, track, **yt_kw)
        if sc >= YT_MIN_SCORE:
            return best, sc
        return None, sc

    # musicdl 与其他注入源：A 档即可；同档内无损品质优先（flac/wav/ape/alac… > 320 > 其余）
    def _qrank(c):
        q = str((c.get("extra") or {}).get("quality") or "").lower()
        if q in ("flac", "wav", "ape", "alac", "wv", "tta", "dsf", "dff"):
            return 0
        if q == "320":
            return 1
        return 2

    if manual_cands:
        manual_sorted = sorted(manual_cands, key=lambda c: (_qrank(c), tier_sort_key(c, "A", sdur)))
        return manual_sorted[0], None
    tiered = [c for c in cands if _tier(c) == "A"]
    if not tiered:
        return None, None
    tiered.sort(key=lambda c: (_qrank(c), tier_sort_key(c, "A", sdur)))
    return tiered[0], None


# ---------- 下载 / 验证 / 转换 ----------

def _fetch_candidate(src, cand, staging: Path) -> str | None:
    """下载候选到 staging，返回落盘路径。

    gd/netease 源：阶梯直链已写进 cand['url']，直接 download_stream
    （真实源 fetch 会二次解析或走 128k 兜底，与无损流冲突）；
    其余源（含注入假源）走 Source.fetch 协议。
    """
    sname = _source_name(src)
    url = str(cand.get("url") or "")
    if sname in GD_NETEASE and url.startswith("http") \
            and type(src).__name__ in ("GdStudioSource", "NeteaseSource"):
        ext = guess_ext_from_url(url)
        if ext == ".bin":
            ext = ".mp3"
        stem = (cand.get("extra") or {}).get("filename_stem") \
            or f"{sname}_{re.sub(r'[^0-9A-Za-z]', '', str(cand.get('id') or 'unknown'))[:24]}"
        out = staging / f"{stem}{ext}"
        download_stream(url, str(out), timeout=300)
        return str(out)
    return src.fetch(cand, str(staging))


def _download_and_convert(track, cand, src, cfg, dirs, cover_path) -> tuple:
    """下载→ffprobe 验证（>20s 且 |dur−sdur|≤verify_win）→remux_flac 或 transcode_mp3
    →成品复验。返回 (成品路径|None, 错误|None, 最终扩展名)。失败时清理半成品。"""
    from . import ffmpeg

    staging = Path(dirs["staging"])
    try:
        got = _fetch_candidate(src, cand, staging)
    except Exception as e:
        return None, f"下载失败: {str(e)[:200]}", None
    if not got:
        return None, "下载失败: 源未产出文件", None
    src_path = Path(got)
    if not src_path.exists():
        return None, "下载失败: 文件不存在", None

    sdur = track_duration_s(track)
    dur = ffmpeg.probe_duration(str(src_path))
    if not dur or dur <= MIN_DUR or (sdur and abs(dur - sdur) > cfg.match.verify_win):
        _rm(src_path)
        return None, f"验证不过: 实测 {dur}s", None

    # 源真 FLAC 判定：gd br≥999000 或 url 后缀 .flac 算元数据声称无损；
    # 实测编码兜底对所有源生效——B站 30280「Hi-Res」层可能是真 FLAC 也可能只是 AAC，
    # yt-dlp 各站同理。元数据会撒谎，codec_name 不会：实测 flac 就保 FLAC remux，不转码。
    br = (cand.get("extra") or {}).get("br")
    url = str(cand.get("url") or "")
    lossless = (isinstance(br, (int, float)) and not isinstance(br, bool) and br >= LOSSLESS_BR) \
        or (bool(url) and url.split("?")[0].lower().endswith(".flac"))
    try:
        info = ffmpeg.probe_full(str(src_path))
        audio = next((s for s in info.get("streams") or []
                      if s.get("codec_type") == "audio"), None)
        codec = ((audio or {}).get("codec_name") or "").lower()
    except Exception:
        codec = ""
    if (cand.get("extra") or {}).get("quality") == "flac":
        lossless = codec == "flac"  # musicdl 契约：声称 flac 必须实测确认，防错标
    elif not lossless and codec == "flac":
        lossless = True  # 元数据没报无损但实测是 FLAC（如 B站真 Hi-Res）→ 保无损不转码

    stem = _filename_stem(track)
    title = str(track.get("name") or "")
    artist = ", ".join(str(a) for a in (track.get("artists") or []))
    album = str(track.get("album") or "")
    cover = str(cover_path) if cover_path else None

    if lossless:
        out = staging / f"{stem}.flac"
        final_ext = ".flac"
        try:
            ffmpeg.remux_flac(str(src_path), str(out), cover=cover,
                              title=title, artist=artist, album=album)
            ok, err = True, ""
        except Exception as e:
            ok, err = False, str(e)[:300]
    else:
        out = staging / f"{stem}.mp3"
        final_ext = ".mp3"
        try:
            ffmpeg.transcode_mp3(str(src_path), str(staging), stem, cover=cover,
                                 title=title, artist=artist, album=album)
            ok, err = True, ""
        except Exception as e:
            ok, err = False, str(e)[:300]

    if not ok:
        _rm(out)
        _rm(src_path)
        return None, f"转换失败: {err}", final_ext
    # 成品复验（safe-replace 要求新文件验证通过才落位）
    dur2 = ffmpeg.probe_duration(str(out))
    if not dur2 or dur2 <= MIN_DUR or (sdur and abs(dur2 - sdur) > cfg.match.verify_win):
        _rm(out)
        _rm(src_path)
        return None, f"成品验证不过: 实测 {dur2}s", final_ext
    _rm(src_path)
    return out, None, final_ext


# ---------- sidecar ----------

def _fetch_cover(track, staging: Path) -> Path | None:
    """Spotify 封面下载（蓝本 download.py:195-211）：ab67616d[0-9a-f]{8}→ab67616d0000b273
    取大图，>5000 字节才收。仅 sidecars=True 时调用。失败返回 None。"""
    from .util import http_get

    url = track.get("image_url")
    if not url:
        return None
    raw_id = str(track.get("uri") or "cover").split(":")[-1]
    safe_id = re.sub(r"[^0-9A-Za-z._-]", "_", raw_id).strip("._") or "cover"
    big = re.sub(r"ab67616d[0-9a-f]{8}", "ab67616d0000b273", url)
    for u in (big, url):
        try:
            data = http_get(u, timeout=30)
            if len(data) > 5000:
                staging.mkdir(parents=True, exist_ok=True)
                p = staging / f"{safe_id[:64]}.jpg"
                p.write_bytes(data)
                return p
        except Exception:
            continue
    return None


def _default_lyrics_fetcher(artist, title, duration_s, alt_variants, min_interval: float = 0.5):
    """默认歌词获取：sources.lrclib.search_lyrics（仅 sidecars=True 且未注入时调用）。"""
    try:
        from .sources import lrclib
        kw = {"min_interval": min_interval} if _accepts_kw(lrclib.search_lyrics, "min_interval") else {}
        res = lrclib.search_lyrics(artist, title, duration_s, alt_variants, **kw)
    except Exception:
        return None
    if isinstance(res, dict):
        text = res.get("synced") or res.get("plain")
        return str(text).strip() + "\n" if text else None
    if isinstance(res, str) and res.strip():
        return res.strip() + "\n"
    return None


def _fetch_lyrics(track, alts, lyrics_fetcher, sdur, cfg=None) -> str | None:
    """经 lyrics_fetcher(artist, title, duration_s, alt_variants) 取歌词文本。"""
    artists = track.get("artists") or []
    artist0 = str(artists[0]) if artists else ""
    title = str(track.get("name") or "")
    try:
        if lyrics_fetcher is not None:
            text = lyrics_fetcher(artist0, title, sdur, alts)
        else:
            min_interval = getattr(getattr(cfg, "rate", None), "lrclib_min_interval", 0.5)
            text = _default_lyrics_fetcher(artist0, title, sdur, alts, min_interval=min_interval)
    except Exception:
        return None
    if not text:
        return None
    text = str(text).strip()
    return text + "\n" if text else None


# ---------- 落位 ----------

def _place_file(new: Path, target: Path, backup_dir: Path) -> None:
    """safe-replace：目标已存在先 cross_move 到备份目录，os.replace 落位，失败回滚备份。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if target.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / target.name
        cross_move(target, backup)
    try:
        try:
            os.replace(str(new), str(target))
        except OSError:
            cross_move(new, target)  # 跨盘回退
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            cross_move(backup, target)
        raise
    if backup is not None and backup.exists():
        _rm(backup)


# ---------- 单曲处理 ----------

def _manual_bvid_rec(track, bvid, bili_src, cfg, dirs, sidecars, lyrics_fetcher) -> dict:
    """收藏夹钦点视频直下（yt-dlp bestaudio → 转码/验证/落位/侧车）。

    收藏的是用户亲手挑选的具体投稿（翻唱/现场等），平台官方版本不能顶替——
    因此对 uri=bili:video:<bvid> 的曲目直下视频本体，失败记 STATUS_FAILED 并记录原因。
    """
    from .sources.base import make_candidate

    name = str(track.get("name") or "")
    cand = make_candidate(
        source="bili", id=bvid, title=name,
        artists=[str(a) for a in (track.get("artists") or [])],
        duration=track_duration_s(track), ext=None,
        url=f"https://www.bilibili.com/video/{bvid}",
        extra={"manual": True})
    rec = {"uri": str(track.get("uri") or ""), "track": track, "score": None,
           "source": "bili-manual", "path": None,
           "dedupe_reason": str(track.get("dedupe_reason") or "")}
    stem = _filename_stem(track)
    cover_path = None
    try:
        if sidecars and track.get("image_url"):
            cover_path = _fetch_cover(track, Path(dirs["staging"]))
        out, err, final_ext = _download_and_convert(track, cand, bili_src, cfg, dirs, cover_path)
        if out is None:
            rec["status"] = STATUS_FAILED
            rec["error"] = err or "bili-manual 下载失败"
            return rec
        target = Path(dirs["music"]) / f"{stem}{final_ext}"
        try:
            _place_file(out, target, Path(dirs["backup"]))
        except Exception as e:
            _rm(out)
            rec["status"] = STATUS_FAILED
            rec["error"] = f"落位失败: {str(e)[:200]}"
            return rec
        jpg_done = lrc_done = False
        if sidecars:
            if cover_path is not None and cover_path.exists():
                try:
                    (Path(dirs["music"]) / f"{stem}.jpg").write_bytes(cover_path.read_bytes())
                    jpg_done = True
                except Exception:
                    pass
            lrc_text = _fetch_lyrics(track, _alt_titles(track, cfg), lyrics_fetcher,
                                     track_duration_s(track), cfg=cfg)
            if lrc_text:
                try:
                    (Path(dirs["music"]) / f"{stem}.lrc").write_text(lrc_text, encoding="utf-8")
                    lrc_done = True
                except Exception:
                    pass
        rec.update(status=STATUS_DOWNLOADED, path=str(target), file=target.name,
                   ext=final_ext, jpg=jpg_done, lyrics=lrc_done,
                   candidate={"id": bvid, "title": name})
        return rec
    finally:
        _rm(cover_path)


def _process_track(track, cfg, srcs, done_uris, all_variants, virt, alias_groups,
                   include_existing, sidecars, lyrics_fetcher, dirs, gd_resolver) -> dict:
    """处理单条 track，返回结果记录（不落盘）。"""
    uri = str(track.get("uri") or "")
    rec = {"uri": uri, "track": track, "score": None, "source": None, "path": None,
           "dedupe_reason": str(track.get("dedupe_reason") or "")}

    # a) 断点续跑：非 include_existing 时，已 downloaded 且文件存在的 uri 跳过
    if uri and uri in done_uris and not include_existing:
        rec["status"] = STATUS_EXISTS
        rec["reason"] = "resume: results.jsonl 已 downloaded"
        return rec

    # permanent_skip 子串命中 track 名：跳过
    name = str(track.get("name") or "")
    for s in (getattr(cfg.aliases, "permanent_skip", None) or []):
        if s and s in name:
            rec["status"] = STATUS_FAILED
            rec["reason"] = f"permanent_skip: {s}"
            return rec

    # 三层查重命中（existing）且未指定 include_existing：exists 跳过
    if track.get("existing") and not include_existing:
        rec["status"] = STATUS_EXISTS
        rec["path"] = track.get("existing_file") or None
        rec["reason"] = "曲库已存在"
        return rec

    # B站收藏夹钦点视频（uri=bili:video:<bvid>）：存在 bili 源时直下视频本体，失败不得回退顶替
    bvid = uri.split(":", 2)[2] if uri.startswith("bili:video:") else ""
    if bvid:
        bili_src = next((s for s in srcs if _source_name(s) == "bili"), None)
        if bili_src is not None:
            return _manual_bvid_rec(track, bvid, bili_src, cfg, dirs,
                                    sidecars, lyrics_fetcher)

    # 候选循环
    alts = _alt_titles(track, cfg)
    own: set = set()
    for a in (track.get("artists") or []):
        own |= _artist_variants(str(a), alias_groups)
    others = {v for v in (all_variants - own) if v and v not in virt}
    no_picks = [str(x) for x in (getattr(cfg.aliases, "no_picks", None) or []) if str(x)]

    saw_candidates = False
    saw_search_error = False
    best_reject: tuple | None = None  # (score, source)
    chosen = None
    for src in srcs:
        sname = _source_name(src)
        try:
            cands = src.search(track) or []
        except Exception:
            saw_search_error = True
            continue
        cands = [c for c in cands if isinstance(c, dict) and not _match_picks(c, no_picks)]
        if cands:
            saw_candidates = True
        try:
            cand, sc = _evaluate_source(sname, src, cands, track, cfg, alts, others, gd_resolver)
        except Exception:
            cand, sc = None, None
        # NeteaseSource 主搜索无 A 档无损命中时，若存在 search_album_artists 方法则补充深挖一次
        if cand is None and sname == "netease" and callable(getattr(src, "search_album_artists", None)):
            try:
                deep = src.search_album_artists(track) or []
            except Exception:
                deep = []
            seen_ids = {str(c.get("id") or "") for c in cands}
            deep = [c for c in deep if isinstance(c, dict)
                    and str(c.get("id") or "") not in seen_ids
                    and not _match_picks(c, no_picks)]
            if deep:
                saw_candidates = True
                try:
                    cand, sc = _evaluate_source(sname, src, deep, track, cfg, alts, others, gd_resolver)
                except Exception:
                    cand, sc = None, None
        if cand is not None:
            chosen = (cand, sc, sname, src)
            break
        if sc is not None and (best_reject is None or sc > best_reject[0]):
            best_reject = (sc, sname)

    if chosen is None:
        if not srcs:
            rec["status"] = STATUS_NO_SOURCE
            rec["reason"] = "无可用音源"
        elif best_reject is not None or saw_candidates:
            rec["status"] = STATUS_LOW_CONFIDENCE
            if best_reject is not None:
                rec["score"], rec["source"] = best_reject[0], best_reject[1]
        elif saw_search_error:
            rec["status"] = STATUS_SEARCH_FAILED
        else:
            rec["status"] = STATUS_NO_RESULT
        return rec

    cand, sc, sname, src = chosen
    rec["source"] = sname
    rec["score"] = sc
    stem = _filename_stem(track)

    # sidecar 封面（转换内嵌用；仅 sidecars=True 时下载，finally 确保清理暂存）
    cover_path = None
    try:
        if sidecars and track.get("image_url"):
            cover_path = _fetch_cover(track, Path(dirs["staging"]))

        out, err, final_ext = _download_and_convert(track, cand, src, cfg, dirs, cover_path)
        if out is None:
            rec["status"] = STATUS_FAILED
            rec["error"] = err
            return rec

        # safe-replace 原子落位到曲库（先落位音频，成功后再写 .jpg / .lrc 侧车）
        target = Path(dirs["music"]) / f"{stem}{final_ext}"
        try:
            _place_file(out, target, Path(dirs["backup"]))
        except Exception as e:
            _rm(out)
            rec["status"] = STATUS_FAILED
            rec["error"] = f"落位失败: {str(e)[:200]}"
            return rec

        # sidecar：.jpg + .lrc（蓝本 download.py:195-246；仅 sidecars=True）
        jpg_done = lrc_done = False
        if sidecars:
            if cover_path is not None and cover_path.exists():
                try:
                    (Path(dirs["music"]) / f"{stem}.jpg").write_bytes(cover_path.read_bytes())
                    jpg_done = True
                except Exception:
                    pass
            lrc_text = _fetch_lyrics(track, alts, lyrics_fetcher, track_duration_s(track), cfg=cfg)
            if lrc_text:
                try:
                    (Path(dirs["music"]) / f"{stem}.lrc").write_text(lrc_text, encoding="utf-8")
                    lrc_done = True
                except Exception:
                    pass

        rec["status"] = STATUS_DOWNLOADED
        rec["path"] = str(target)
        rec["file"] = target.name
        rec["ext"] = final_ext
        rec["jpg"] = jpg_done
        rec["lyrics"] = lrc_done
        rec["candidate"] = {"id": str(cand.get("id") or ""), "title": str(cand.get("title") or "")}
        return rec
    finally:
        _rm(cover_path)


# ---------- 入口 ----------

def run_download(tracks, cfg, *, source: str = "auto", only_ids=None, limit=None,
                 include_existing: bool = False, sources=None, sidecars: bool = True,
                 lyrics_fetcher=None, tasks_dir: str | Path | None = None) -> list:
    """下载编排入口：返回逐曲结果记录列表（并逐曲追加到 tasks/results.jsonl）。

    tracks: prepare 产出的 track dict 列表；cfg: config.Config。
    source: "auto" 按 SOURCE_ORDER 逐源尝试，或指定单源名。
    sources: 注入源实例列表（离线单测用），None 时按默认注册表实例化。
    sidecars: False 时跳过封面/歌词全部步骤（零网络离线测试的官方开关）。
    lyrics_fetcher: 注入歌词函数 (artist, title, duration_s, alt_variants)->text|None，
    None 时默认 lrclib.search_lyrics。
    tasks_dir: 运行产物目录（默认 REPO_ROOT / "tasks"），方便离线测试隔离。
    """
    setup_console()
    music_dir = Path(cfg.paths.music)
    staging = Path(cfg.paths.staging)
    staging.mkdir(parents=True, exist_ok=True)
    dirs = {"music": str(music_dir), "staging": str(staging), "backup": str(staging / "backup")}
    tasks = Path(tasks_dir) if tasks_dir is not None else globals()["tasks_dir"]()
    tasks.mkdir(parents=True, exist_ok=True)

    # 过滤：only_ids → limit（蓝本 download_bili.py:437-453）；
    # existing 曲目不过滤——由 _process_track 记 exists 后跳过（include_existing=True 时照常下载）
    sel = [t for t in (tracks or []) if isinstance(t, dict)]
    if only_ids:
        wanted = {str(x).strip() for x in only_ids if str(x).strip()}
        sel = [t for t in sel
               if str(t.get("uri") or "").split(":")[-1] in wanted or t.get("name") in wanted]
    if limit:
        sel = sel[:limit]

    done_uris = set() if include_existing else _load_done_uris(tasks, music_dir)
    alias_groups = _alias_groups(cfg)
    all_variants: set = set()
    for t in (tracks or []):
        for a in (t.get("artists") or [] if isinstance(t, dict) else []):
            all_variants |= _artist_variants(str(a), alias_groups)
    virt = _virtual_set(cfg)

    srcs = sources
    if srcs is None:
        srcs = _default_sources(cfg, source)
    elif source != "auto":
        srcs = [s for s in srcs if _source_name(s) == source]
    gd_resolver = _gd_resolver(srcs, cfg) if any(
        _source_name(s) in GD_NETEASE for s in (srcs or [])) else None

    raw_scale = getattr(getattr(cfg, "rate", None), "per_track_sleep", 1.0)
    scale = max(float(1.0 if raw_scale is None else raw_scale), 0.0)
    results: list = []
    for track in sel:
        rec = _process_track(track, cfg, srcs or [], done_uris, all_variants, virt,
                             alias_groups, include_existing, sidecars, lyrics_fetcher,
                             dirs, gd_resolver)
        results.append(rec)
        _append_result(tasks, rec)
        if scale > 0:
            time.sleep(random.uniform(0.8, 1.8) * scale)  # 每曲后限速
    return results
