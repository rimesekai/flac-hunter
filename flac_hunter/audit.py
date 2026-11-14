"""质量审计：四项 FLAC 质量门、歌词体检、文件名垃圾扫描与无损重命名。

蓝本：audit_group_b.py:24-135（四项门）、check_lyrics.py:37-119（歌词 8 类）、
rename_scan.py:20-119（JUNK_PATTERNS/classify）、rename_apply.py:44-81（apply）。
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from pathlib import Path

from .util import smart_read_text

try:  # 入口模块 UTF-8 输出保护
    import sys as _sys
    for _s in (_sys.stdout, _sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
except Exception:
    pass

DUR_TOL = 15.0  # 时长容差（秒），audit_group_b.py:24
AUDIO_EXT = {".flac", ".ogg", ".mp3", ".m4a", ".opus", ".wav"}

# JUNK_PATTERNS 6 正则，逐条转录 rename_scan.py:20-27
JUNK_PATTERNS = [
    re.compile(r"\[[0-9A-Za-z_\-]{11}\]"),                # YouTube 视频 id
    re.compile(r"BV[0-9A-Za-z]{10}"),
    re.compile(r"\[(lyrics|lyric video|official\s*(?:mv|video|audio)?|mv|audio|cc|中字|中日|双语|字幕|4k|60帧|hi-?res|无损|音质|audio)\s*\]", re.I),
    re.compile(r"\((lyrics|lyric video|official\s*(?:mv|video|audio)?|mv|audio|完整版|full ver\.?|audio)\s*\)", re.I),
    re.compile(r"【[^】]*】"),
    re.compile(r"\s*[-–]\s*(official\s*(?:mv|video|audio)|music video|mv|lyric[s]? video|audio)\s*$", re.I),
]

# 歌词时间戳 [mm:ss] / [mm:ss.xxx]，check_lyrics.py:37
_TS = re.compile(r"\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]")
# 内嵌元数据行 [ti:...] / [ar:...] 等，check_lyrics.py:42
_META = re.compile(r"^\[(ti|ar|al|by|offset|length):(.*?)\]", re.M | re.I)


def _sanitize(s: str) -> str:
    """Windows 文件名清洗（rename_scan.py:30-33）。"""
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().rstrip(".")


def _norm(s: str) -> str:
    """NFKC→lower→仅保留 [0-9a-z 假名 汉字]（rename_scan.py:36-39）。"""
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]+", "", s)


def _strip_junk(s: str) -> str:
    """套用全部 JUNK_PATTERNS 后折叠空白、剥首尾垃圾字符（rename_scan.py:60-65）。"""
    out = s
    for pat in JUNK_PATTERNS:
        out = pat.sub(" ", out)
    out = re.sub(r"\s+", " ", out)
    return out.strip(" -–_.")


def classify_rename(stem: str, title: str = "", artist: str = "") -> tuple[list[str], str | None]:
    """按 rename_scan.py:68-119 的 classify 逐行转录。

    stem 传不含扩展名的文件名主干；title/artist 为内嵌标签（可为空）。
    返回 (issues, proposal)：issues 取值 junk/no_separator/inverted/artist_junk。
    """
    issues: list[str] = []
    cur = stem
    stripped = _strip_junk(cur)
    if stripped != cur:
        issues.append("junk")

    parts = cur.split(" - ")
    tag_title_n, tag_artist_n = _norm(title), _norm(artist)

    if " - " not in cur:
        if title and artist:
            issues.append("no_separator")
            return issues, f"{_sanitize(title)} - {_sanitize(artist)}"
        if issues:
            return issues, _sanitize(stripped)
        return issues, None

    # 倒置判断：前段≈artist 标签 且 后段≈title 标签
    p1 = _strip_junk(parts[0])
    rest = _strip_junk(" - ".join(parts[1:]))
    inverted = False
    if tag_artist_n and (tag_artist_n == _norm(p1) or _norm(p1) in tag_artist_n or tag_artist_n in _norm(p1)):
        if tag_title_n and (tag_title_n == _norm(rest) or tag_title_n in _norm(rest)):
            inverted = True
    if inverted:
        issues.append("inverted")

    # artist 段尾部垃圾（_hires / .hires）
    a_stripped = re.sub(r"[\s._-]*[Hh]i-?[Rr]es\s*$", "", rest).strip(" -–_.")
    junk_in_artist = a_stripped != rest
    if junk_in_artist:
        issues.append("artist_junk")

    if not issues:
        return issues, None

    if inverted and title and artist:
        return issues, f"{_sanitize(title)} - {_sanitize(artist)}"
    if issues == ["junk"]:
        return issues, _sanitize(stripped)
    if issues == ["artist_junk"]:
        if p1 and a_stripped:
            return issues, _sanitize(f"{p1} - {a_stripped}")
        return issues, _sanitize(p1 or a_stripped)
    # 混合情形：标签可用则优先按标签重建
    if title and artist:
        return issues, f"{_sanitize(title)} - {_sanitize(artist)}"
    if "artist_junk" in issues:
        if p1 and a_stripped:
            return issues, _sanitize(f"{p1} - {a_stripped}")
        return issues, _sanitize(p1 or a_stripped)
    return issues, _sanitize(stripped)


def _get_tags(path: str | Path) -> tuple[str, str]:
    """读内嵌 title/artist 标签（rename_scan.py:42-57，走 ffmpeg.probe_meta）。"""
    try:
        from . import ffmpeg
        meta = ffmpeg.probe_meta(str(path))
    except Exception:
        return "", ""
    tags = None
    if isinstance(meta, dict):
        fmt = meta.get("format")
        if isinstance(fmt, dict):
            tags = fmt.get("tags")
        else:
            tags = meta.get("tags")
    elif isinstance(meta, (tuple, list)):
        # (duration, bit_rate, title, artist) 或 (duration, title, artist) 两种形态兜底
        if len(meta) >= 4:
            return str(meta[2] or "").strip(), str(meta[3] or "").strip()
        if len(meta) == 3:
            return str(meta[1] or "").strip(), str(meta[2] or "").strip()
    if not isinstance(tags, dict):
        return "", ""

    def pick(*keys: str) -> str:
        for k in keys:
            for kk, v in tags.items():
                if kk.lower() == k.lower() and v and str(v).strip():
                    return str(v).strip()
        return ""

    return pick("title", "TITLE"), pick("artist", "ARTIST", "ARTIST_ID3")


def scan_rename(music_dir: str | Path, cfg=None) -> list[dict]:
    """dry-run 重命名计划：对曲库全部音频 stem 跑 classify_rename。

    返回计划列表：{'old': 原stem, 'new': 建议stem, 'issues': [...],
                  'proposal': 建议stem, 'title': 标签title, 'artist': 标签artist}。
    """
    root = Path(music_dir)
    plans: list[dict] = []
    if not root.is_dir():
        return plans
    for f in sorted(os.listdir(root)):
        p = Path(f)
        if p.suffix.lower() not in AUDIO_EXT:
            continue
        title, artist = _get_tags(root / f)
        issues, prop = classify_rename(p.stem, title, artist)
        if prop and prop != p.stem:
            plans.append({"old": p.stem, "new": prop, "issues": issues,
                          "proposal": prop, "file": f, "title": title, "artist": artist})
    return plans


def apply_rename(cfg, plans: list[dict]) -> list[dict]:
    """执行重命名：无损 retag_copy 写标签 → 改名 → sidecar(.jpg/.lrc) 同步改名。

    目标 stem 已存在则跳过不动；retag 失败跳过该文件（rename_apply.py:44-81 语义）。
    同 stem 多扩展名（如 .flac 与 .mp3）或计划列表含重复 old stem 时，不互相误跳、不重复报错。
    cfg 仅用于取曲库目录。返回逐条执行记录。
    """
    from . import ffmpeg

    if isinstance(cfg, dict):
        music_dir = Path((cfg.get("paths") or {}).get("music") or cfg.get("music") or "music")
    else:
        paths = getattr(cfg, "paths", None)
        music_dir = Path(getattr(paths, "music", "music") if paths is not None else "music")
    records: list[dict] = []
    existing_stems = {p.stem for p in music_dir.iterdir()
                      if p.is_file() and p.suffix.lower() in AUDIO_EXT}
    claimed_new: dict[str, str] = {}
    renamed_olds: set[str] = set()
    seen_plans: set[tuple[str, str, str]] = set()

    for plan in plans or []:
        old, new = plan.get("old") or "", plan.get("new") or plan.get("proposal") or ""
        file_hint = str(plan.get("file") or "").strip()
        plan_key = (old, new, Path(file_hint).name if file_hint else "")
        if plan_key in seen_plans:
            continue
        seen_plans.add(plan_key)

        if not old or not new or old == new:
            records.append({"old": old, "new": new, "status": "skip", "detail": "空计划或同名"})
            continue

        if file_hint:
            cand = music_dir / Path(file_hint).name
            srcs = [cand] if (cand.is_file() and cand.stem == old and cand.suffix.lower() in AUDIO_EXT) else []
        else:
            srcs = sorted(
                [q for q in music_dir.iterdir()
                 if q.is_file() and q.stem == old and q.suffix.lower() in AUDIO_EXT],
                key=lambda q: q.name,
            )
        if not srcs:
            if old in renamed_olds:
                continue
            records.append({"old": old, "new": new, "status": "skip", "detail": "missing"})
            continue
        if new in existing_stems and claimed_new.get(new) != old:
            records.append({"old": old, "new": new, "status": "skip", "detail": "name exists"})
            continue
        title = str(plan.get("title") or "").strip()
        artist = str(plan.get("artist") or "").strip()
        done_any = False
        failed = ""
        for q in srcs:
            target = q.with_name(f"{new}{q.suffix}")
            if target.exists():
                records.append({"old": old, "new": new, "status": "skip", "detail": "name exists"})
                continue
            try:
                if title and artist:
                    ffmpeg.retag_copy(str(q), title=title, artist=artist)  # .tagtmp + os.replace，失败抛错
            except Exception as e:
                failed = str(e)[:200]
                break
            os.replace(str(q), str(target))
            for ext in (".jpg", ".lrc"):
                side = q.with_name(f"{old}{ext}")
                if side.exists():
                    t2 = q.with_name(f"{new}{ext}")
                    if not t2.exists():
                        os.replace(str(side), str(t2))
            claimed_new[new] = old
            existing_stems.add(new)
            renamed_olds.add(old)
            records.append({"old": old, "new": new, "status": "renamed",
                            "detail": f"{q.name} -> {target.name}"})
            done_any = True
        if done_any:
            if not any(q.is_file() and q.stem == old and q.suffix.lower() in AUDIO_EXT
                       for q in music_dir.iterdir()):
                existing_stems.discard(old)
        elif failed:
            records.append({"old": old, "new": new, "status": "failed", "detail": failed})
    return records


def _tag_get(tags, key: str):
    """ffprobe tags 键名大小写不敏感查找（audit_group_b.py:80-87）。"""
    if not isinstance(tags, dict):
        return None
    for k, v in tags.items():
        if k.lower() == key.lower():
            return v
    return None


def audit_one(path: str | Path, duration_ms=None, *, dur_tol: float = DUR_TOL) -> dict:
    """对单个 FLAC 做四项质量门（audit_group_b.py:90-135）。

    ① |ffprobe dur − duration_ms/1000| ≤ dur_tol（默认 15s）→ dur_ok
    ② format.tags title/artist 非空 → tags_ok
    ③ 同名 .jpg 存在 → jpg_ok
    ④ 真 FLAC：stream codec_name=='flac' 且 format_name 含 flac → flac_ok
    返回 {'path','dur_ok','tags_ok','jpg_ok','flac_ok','issues'}。
    """
    from . import ffmpeg

    p = str(path)
    issues: list[str] = []
    try:
        probe = ffmpeg.probe_full(p)
    except Exception as e:
        probe = None
        probe_err = str(e)[:120]
    else:
        probe_err = ""
    if not isinstance(probe, dict):
        return {"path": p, "dur_ok": False, "tags_ok": False, "jpg_ok": False,
                "flac_ok": False, "issues": [f"ffprobe 失败: {probe_err or '无法读取探测 JSON'}"]}

    fmt = probe.get("format") or {}
    streams = probe.get("streams") or []
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    # ① 时长差（duration_ms 未给出时跳过该项）
    dur_ok = True
    if duration_ms:
        try:
            dur = float(fmt.get("duration"))
            diff = dur - float(duration_ms) / 1000.0
            if abs(diff) > dur_tol:
                dur_ok = False
                issues.append(f"时长差{diff:+.1f}s")
        except (TypeError, ValueError):
            dur_ok = False
            issues.append("无法读取时长")

    # ② 标签
    tags = fmt.get("tags") or {}
    title = _tag_get(tags, "title")
    artist = _tag_get(tags, "artist")
    tags_ok = bool(title and str(title).strip()) and bool(artist and str(artist).strip())
    if not tags_ok:
        issues.append("缺标签")

    # ③ 同名封面
    jpg_ok = os.path.isfile(os.path.splitext(p)[0] + ".jpg")
    if not jpg_ok:
        issues.append("缺封面")

    # ④ 真 FLAC 编解码
    fmt_name = (fmt.get("format_name") or "").lower()
    codec = ((audio or {}).get("codec_name") or "").lower()
    flac_ok = codec == "flac" and "flac" in fmt_name
    if not flac_ok:
        issues.append(f"编解码异常({codec or '?'}/{fmt_name or '?'})")

    return {"path": p, "dur_ok": dur_ok, "tags_ok": tags_ok, "jpg_ok": jpg_ok,
            "flac_ok": flac_ok, "issues": issues}


def _verify_win(cfg) -> float:
    """从 Config dataclass 或 dict 读取 match.verify_win，缺省回退 DUR_TOL。"""
    val = None
    if isinstance(cfg, dict):
        m = cfg.get("match")
        if isinstance(m, dict):
            val = m.get("verify_win")
    elif cfg is not None:
        m = getattr(cfg, "match", None)
        if isinstance(m, dict):
            val = m.get("verify_win")
        elif m is not None:
            val = getattr(m, "verify_win", None)
    if isinstance(val, (int, float)) and not isinstance(val, bool) and val >= 0:
        return float(val)
    return DUR_TOL


def audit_dir(music_dir: str | Path, cfg=None) -> list[dict]:
    """四项质量门扫全库（audit cli 默认动作）：对每个 .flac 跑 audit_one。"""
    root = Path(music_dir)
    out: list[dict] = []
    if not root.is_dir():
        return out
    dur_tol = _verify_win(cfg)
    for f in sorted(os.listdir(root)):
        if Path(f).suffix.lower() != ".flac":
            continue
        out.append(audit_one(root / f, dur_tol=dur_tol))
    return out


def _parse_lrc(text: str) -> tuple[dict, float | None, int]:
    """解析 [ti/ar/...] 元数据行与时间戳（check_lyrics.py:40-49）。

    返回 (meta, 最大时间戳秒, 时间戳个数)。
    """
    meta: dict[str, str] = {}
    for m in _META.finditer(text):
        meta[m.group(1).lower()] = m.group(2).strip()
    stamps: list[float] = []
    for m in _TS.finditer(text):
        mm, ss, frac = int(m.group(1)), int(m.group(2)), m.group(3) or "0"
        frac = int(frac) / (10 ** len(frac))
        stamps.append(mm * 60 + ss + frac)
    return meta, (max(stamps) if stamps else None), len(stamps)


def _split_stem(stem: str) -> tuple[str, str]:
    """stem 按 " - " 拆 (标题, 歌手)，歌手取末段（check_lyrics.py:62-66）。"""
    parts = stem.split(" - ")
    if len(parts) >= 2:
        return " - ".join(parts[:-1]), parts[-1]
    return stem, ""


def check_lyrics_file(lrc_path: str | Path, *, audio_duration: float | None = None,
                      audio_exists: bool = True, title: str | None = None,
                      artist: str | None = None) -> list[str]:
    """单文件歌词体检（check_lyrics.py:93-119 的便捷版）。

    返回命中的类别名列表（orphan/empty/no_timestamps/meta_title/meta_artist/
    too_long/too_short）；dup_content 需跨文件聚类，属目录级检查不出现在此。
    """
    p = Path(lrc_path)
    issues: list[str] = []
    if not audio_exists:
        issues.append("orphan")
        return issues
    text = smart_read_text(p)
    if text is None:
        issues.append("empty")
        return issues
    meta, last_ts, n_ts = _parse_lrc(text)
    try:
        size = p.stat().st_size
    except OSError:
        size = 0
    if size < 60:
        issues.append("empty")
    if n_ts == 0:
        issues.append("no_timestamps")
    if title is not None and meta.get("ti") and title:
        a, b = _norm(meta["ti"]), _norm(title)
        if a and b and a != b and a not in b and b not in a:
            issues.append("meta_title")
    if artist is not None and meta.get("ar") and artist:
        a, b = _norm(meta["ar"]), _norm(artist)
        if a and b and a != b and a not in b and b not in a:
            issues.append("meta_artist")
    if last_ts is not None and audio_duration:
        if last_ts > audio_duration + 10:
            issues.append("too_long")
        elif audio_duration - last_ts > 150:
            issues.append("too_short")
    return issues


def check_lyrics_dir(music_dir: str | Path, cfg=None) -> dict[str, list]:
    """歌词体检全流程，逐行转录 check_lyrics.py:69-119。

    音频按 norm(stem) 与 lrc 配对；读文件用 util.smart_read_text 多编码探测。
    返回键为 8 类类别名的字典：orphan/meta_title/meta_artist/too_long/
    too_short/dup_content/empty/no_timestamps。
    """
    from . import ffmpeg

    root = Path(music_dir)
    issues: dict[str, list] = {"orphan": [], "meta_title": [], "meta_artist": [],
                               "too_long": [], "too_short": [], "dup_content": [],
                               "empty": [], "no_timestamps": []}
    if not root.is_dir():
        return issues
    audio = {f: root / f for f in os.listdir(root)
             if Path(f).suffix.lower() in AUDIO_EXT}
    audio_stems = {Path(f).stem: f for f in audio}
    audio_norm = {_norm(Path(f).stem): f for f in audio}
    lrcs = [f for f in os.listdir(root) if Path(f).suffix.lower() == ".lrc"]
    hashes: dict[str, list[str]] = {}

    for lf in sorted(lrcs):
        p = root / lf
        stem = p.stem
        af = audio_stems.get(stem)
        if not af:
            cand = audio_norm.get(_norm(stem))
            if cand:
                af = cand
            else:
                issues["orphan"].append(lf)
                continue
        text = smart_read_text(p)
        if text is None:
            text = ""
        meta, last_ts, n_ts = _parse_lrc(text)
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        if size < 60:
            issues["empty"].append(lf)
        if n_ts == 0:
            issues["no_timestamps"].append(lf)
        h = hashlib.md5(re.sub(r"\s+", "", text).encode("utf-8", "ignore")).hexdigest()
        hashes.setdefault(h, []).append(lf)

        title, artist = _split_stem(Path(af).stem)
        if meta.get("ti") and title:
            a, b = _norm(meta["ti"]), _norm(title)
            if a and b and a != b and a not in b and b not in a:
                issues["meta_title"].append((lf, meta["ti"], title))
        if meta.get("ar") and artist:
            a, b = _norm(meta["ar"]), _norm(artist)
            if a and b and a != b and a not in b and b not in a:
                issues["meta_artist"].append((lf, meta["ar"], artist))

        dur = None
        try:
            dur = ffmpeg.probe_duration(str(root / af))
        except Exception:
            dur = None
        if last_ts is not None and dur:
            if last_ts > dur + 10:
                issues["too_long"].append((lf, round(last_ts, 1), round(dur, 1)))
            elif dur - last_ts > 150:
                issues["too_short"].append((lf, round(last_ts, 1), round(dur, 1)))

    for h, files in hashes.items():
        if len(files) > 1:
            issues["dup_content"].append(files)
    return issues
