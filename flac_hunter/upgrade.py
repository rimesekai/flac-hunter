"""旧库无损升级：扫描曲库旧文件（mp3/ogg），经网易云搜索 + GDStudio 阶梯
取得无损直链，下载验证后 remux 成 FLAC 落位并删旧文件。

蓝本：upgrade_original.py:106-164（匹配方向与查询变体）、upgrade_ogg.py:188-230
（gd 阶梯 + 匿名兜底 + better() 判定）、verify_kaisei.py:27-32（pcm_md5）。
匹配方向修复：蓝本 upgrade_original.py:111-116 的双向包含（nt-in-nc 或 nc-in-nt）
是事故根源——本模块强制单向 nt-in-nc。
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from pathlib import Path

from .config import REPO_ROOT
from .console import setup_console
from .util import guess_ext_from_url

try:  # 入口模块 UTF-8 输出保护
    import sys as _sys
    for _s in (_sys.stdout, _sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
except Exception:
    pass

MATCH_FAILS = REPO_ROOT / "tasks" / "match_fails.json"  # 无匹配跳名单
SEARCH_WIN = 8.0    # 搜索期时长窗（秒）
VERIFY_WIN = 15.0   # 下载/成品验证时长窗（秒）
MIN_DUR = 20.0      # 成品时长下限（蓝本 upgrade_ogg.py:215 ndur<20 同款）
PCM_SAMPLE_EVERY = 5  # 按比例抽样 pcm_md5：每 5 个升级文件抽 1 个


def norm(s: str) -> str:
    """lower + 仅保留 isalnum 字符（upgrade_original.py:106-108）。"""
    s = (s or "").lower()
    return "".join(ch for ch in s if ch.isalnum())


def nt_in_nc(target: str, cand: str) -> bool:
    """修复已知事故：目标标题归一化后必须完整包含于候选标题（单向 nt-in-nc）。

    蓝本 upgrade_original.py:111-116 的双向包含允许候选名反向包含目标名，
    会把「候选标题恰含目标标题子串」的同类曲错配；带版本后缀的目标
    （VERSION_MARKERS，如 Live ver./inst.）受害最重，故一律禁止反向。
    任一空串返回 False。
    """
    nt, nc = norm(target), norm(cand or "")
    if not nt or not nc:
        return False
    return nt in nc


def artist_ok(target_artists, cand_artists_str: str, alias_groups=None) -> bool:
    """目标任一歌手出现在候选歌手串接中（大小写不敏感 + 别名变体展开）。"""
    from .match.normalize import artist_variants, contains_variant, norm_text

    credited = cand_artists_str or ""
    credited_lower = credited.lower()
    credited_norm = norm_text(credited)
    for a in (target_artists or []):
        a_str = str(a or "").strip()
        if not a_str:
            continue
        if contains_variant(credited_lower, a_str.lower()):
            return True
        variants = artist_variants(a_str, alias_groups)
        if any(contains_variant(credited_norm, v) for v in variants):
            return True
    return False


def _alias_groups(cfg) -> list[set[str]]:
    """合并内置 ARTIST_ALIAS_GROUPS 与 cfg.aliases.art_aliases。"""
    try:
        from .match.normalize import cfg_alias_groups
        return list(cfg_alias_groups(cfg))
    except Exception:
        pass
    groups: list[set[str]] = []
    try:
        from .match.blacklist import ARTIST_ALIAS_GROUPS
        groups.extend(set(g) for g in ARTIST_ALIAS_GROUPS)
    except Exception:
        pass
    aliases = cfg.get("aliases") if isinstance(cfg, dict) else getattr(cfg, "aliases", None)
    art = (aliases.get("art_aliases") if isinstance(aliases, dict)
           else getattr(aliases, "art_aliases", None)) or {}
    if isinstance(art, dict):
        for k, vs in art.items():
            if isinstance(k, str) and isinstance(vs, (list, tuple, set)):
                grp = {str(k)} | {str(v) for v in vs if v}
                if grp:
                    groups.append(grp)
    return groups


def _cfg_section(cfg, name: str):
    if cfg is None:
        return None
    return cfg.get(name) if isinstance(cfg, dict) else getattr(cfg, name, None)


def _cfg_get(cfg, section: str, key: str, default):
    sec = _cfg_section(cfg, section)
    if sec is None:
        return default
    val = sec.get(key, default) if isinstance(sec, dict) else getattr(sec, key, default)
    return default if val is None else val


def better(lossless: bool, src_br: float, ogg_br: float) -> bool:
    """OGG 升级判定（upgrade_ogg.py:222-230）：无损，或源码率 ≥ max(260, ogg+60)。"""
    return bool(lossless) or src_br >= max(260, ogg_br + 60)


# ---------- 前置模块适配（sources/ffmpeg 签名已落地，按实际 API 调用） ----------

def _norm_dur(raw) -> float | None:
    """毫秒/秒归一：>2000 视为毫秒（hunt_last3.py:130-140）。"""
    if raw in (None, "", 0, "0"):
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return v / 1000.0 if v > 2000 else v


def _netease_search(q: str, limit: int = 8, cfg=None) -> list[dict]:
    """网易云单曲搜索适配：NeteaseSource.search 以假 track（name=查询词）传词。

    行归一为 {'id','name','dur'(秒或None),'artists'(串接str)}；
    模块缺失或请求异常一律返回 []，绝不抛出。
    """
    try:
        from .sources.netease import NeteaseSource
        src = NeteaseSource(cfg) if cfg is not None else NeteaseSource()
        rows = src.search({"name": q, "artists": []}) or []
    except Exception:
        return []
    out: list[dict] = []
    for r in rows[: max(limit, 1) * 2] if limit else rows:
        if not isinstance(r, dict):
            continue
        artists = r.get("artists")
        if isinstance(artists, str):
            credited = artists
        elif isinstance(artists, list):
            parts = [str(a.get("name") or "") if isinstance(a, dict) else str(a)
                     for a in artists]
            credited = ", ".join(x for x in parts if x)
        else:
            credited = ""
        out.append({"id": str(r.get("id") or ""),
                    "name": str(r.get("title") or r.get("name") or ""),
                    "dur": _norm_dur(r.get("duration")), "artists": credited})
    return [r for r in out if r["id"]]


def _gd_url_for(sid: str, cfg=None) -> tuple[str | None, int]:
    """GDStudio types=url 阶梯适配（netease 源）：999999→320000→128000。

    返回 (url, br)；无直链返回 (None, 0)。
    """
    try:
        from .sources.gdstudio import GdStudioSource
        src = GdStudioSource(cfg) if cfg is not None else GdStudioSource()
        url, br, _size = src.get_url("netease", str(sid))
    except Exception:
        return None, 0
    return (str(url) if url else None), int(br or 0)


def _probe_meta(path: str) -> tuple[float, int, str, str]:
    """ffprobe (时长秒, 码率kbps, title, artist)；失败 (0.0, 0, '', '')。

    ffmpeg.probe_meta 返回 {'duration','bit_rate'(bps),'tags':{'title','artist'}}。
    """
    try:
        from . import ffmpeg
        meta = ffmpeg.probe_meta(path)
    except Exception:
        return 0.0, 0, "", ""
    if not isinstance(meta, dict):
        return 0.0, 0, "", ""
    tags = meta.get("tags") or {}
    title = str(_tag_get(tags, "title") or "").strip()
    artist = str(_tag_get(tags, "artist") or "").strip()
    dur = meta.get("duration") or 0.0
    br = meta.get("bit_rate") or 0
    try:
        dur_f = float(dur) if dur else 0.0
    except (TypeError, ValueError):
        dur_f = 0.0
    try:
        br_i = round(float(br) / 1000) if br else 0
    except (TypeError, ValueError):
        br_i = 0
    return dur_f, int(br_i), title, artist


def _tag_get(tags, key: str):
    """ffprobe tags 键名大小写不敏感查找。"""
    if not isinstance(tags, dict):
        return None
    for k, v in tags.items():
        if k.lower() == key.lower():
            return v
    return None


def _fetch_netease_cover(sid: str, dst: Path) -> bool:
    """从网易云歌曲详情补拉专辑封面到 dst（仅真实网络升级时调用，失败静默返回 False）。"""
    from .util import http_get

    try:
        detail_url = f"https://music.163.com/api/song/detail/?id={sid}&ids=%5B{sid}%5D"
        raw = http_get(detail_url, timeout=12)
        songs = (json.loads(raw.decode("utf-8", errors="replace")).get("songs") or [])
        pic_url = ((songs[0].get("album") or {}).get("picUrl") or "") if songs else ""
        if not pic_url:
            return False
        img = http_get(pic_url, timeout=20)
        if len(img) > 1000 and img[:1] != b"<":
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(img)
            return True
    except Exception:
        return False
    return False


def _remux_flac(src: Path, out: Path, title: str, artist: str, cover: Path | None) -> tuple[bool, str]:
    """remux 成 FLAC（-c copy + 标签 + 可选内嵌封面，显式 -f flac）。

    ffmpeg.remux_flac(src, dst, *, cover, title, artist, album) 失败抛 RuntimeError。
    """
    try:
        from . import ffmpeg
        ffmpeg.remux_flac(str(src), str(out), cover=str(cover) if cover else None,
                          title=title, artist=artist)
        return True, ""
    except Exception as e:
        return False, str(e)[:300]


def _repair_existing_flac(p: Path, music_dir: Path, stem: str, title: str,
                          artist: str, sid: str | None, search_fn) -> tuple[bool, str]:
    """当输入本身已是 .flac 时，就地补齐封面与标签（免重下整首音频）。"""
    cover = music_dir / f"{stem}.jpg"
    if not cover.exists() and search_fn is None and sid:
        _fetch_netease_cover(sid, cover)
    if not cover.exists():
        return False, "no_cover"
    tmp_final = music_dir / f"{stem}.new.flac"
    ok, err = _remux_flac(p, tmp_final, title, artist, cover)
    if not ok:
        tmp_final.unlink(missing_ok=True)
        return False, err
    try:
        os.replace(str(tmp_final), str(p))
        return True, ""
    except Exception as e:
        tmp_final.unlink(missing_ok=True)
        return False, str(e)[:200]


def _is_real_flac(p: Path) -> bool:
    """用 ffprobe 确认文件音频流确为 flac 且时长合法。"""
    if p.suffix.lower() != ".flac":
        return False
    try:
        from . import ffmpeg
        info = ffmpeg.probe_full(str(p))
        audio = next((st for st in (info.get("streams") or [])
                      if st.get("codec_type") == "audio"), None)
        codec = ((audio or {}).get("codec_name") or "").lower()
        dur = float((info.get("format") or {}).get("duration") or 0.0)
        return codec == "flac" and dur >= MIN_DUR
    except Exception:
        return False


def _log_up(msg: str) -> None:
    print(msg, flush=True)


# ---------- 主流程 ----------

def _load_match_fails(full_retry: bool, path: Path = MATCH_FAILS) -> dict:
    """读 match_fails.json；full_retry 或环境变量 FULL_RETRY=1 清空。"""
    if full_retry or os.getenv("FULL_RETRY") == "1":
        return {}
    try:
        import json
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_match_fails(skip: dict, path: Path = MATCH_FAILS) -> None:
    import json
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(skip, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _bump_match_fails(skip: dict, fname: str, path: Path = MATCH_FAILS) -> None:
    skip[fname] = skip.get(fname, 0) + 1
    _save_match_fails(skip, path)


def _queries_for(title: str, artist: str) -> list[str]:
    """搜索变体：歌手 歌名 / 裸歌名 / 剥括号裸标题（upgrade_original.py:156-164）。"""
    queries: list[str] = []
    if artist:
        queries.append(f"{artist} {title}")
    queries.append(title)
    bare = re.sub(r"[\(（\[【].*?[\)）\]】]", "", title).strip()
    if bare and bare != title:
        queries.append(f"{artist} {bare}".strip())
        queries.append(bare)
    return list(dict.fromkeys(q for q in queries if q.strip()))


def run_upgrade(cfg, *, ext: str = "mp3", full_retry: bool = False,
                limit: int | None = None,
                only_files: list[str] | None = None,
                match_fails_path: str | Path | None = None,
                search_fn=None, url_fn=None, download_fn=None) -> list[dict]:
    """扫描曲库该扩展名旧文件并逐个尝试无损升级，返回逐文件结果记录列表。

    ext: "mp3" / "ogg" / "all"（all = mp3+ogg）。
    流程：permanent_skip（优先级最高）→ match_fails 跳名单 → 网易云 ±search_win 搜 id
    → GDStudio get_url 阶梯 → br>=999000 或 .flac 才下载（mp3 输入；ogg 输入走 better()）
    → util.download_stream 下载（<100KB 拒收）→ ffprobe ±verify_win 验证 + codec_name 实测 FLAC
    → remux_flac 成品 <stem>.new.flac 再验 ±verify_win → 备份落位后删旧文件 →
    按比例抽样 pcm_md5 留证（只记录不强制相等）。
    match_fails_path / search_fn / url_fn / download_fn 为离线单测依赖注入。
    """
    from . import ffmpeg
    from .util import cross_move, download_stream

    setup_console()

    music_dir = Path(_cfg_get(cfg, "paths", "music", "music"))
    staging = Path(_cfg_get(cfg, "paths", "staging", "staging"))
    staging.mkdir(parents=True, exist_ok=True)
    ext = (ext or "mp3").lower()
    exts = (".mp3", ".ogg") if ext == "all" else (f".{ext}",)
    permanent_skip = [s for s in (_cfg_get(cfg, "aliases", "permanent_skip", []) or []) if s]
    no_picks = [str(s) for s in (_cfg_get(cfg, "aliases", "no_picks", []) or []) if str(s)]
    search_win = float(_cfg_get(cfg, "match", "search_win", SEARCH_WIN))
    verify_win = float(_cfg_get(cfg, "match", "verify_win", VERIFY_WIN))
    netease_interval = max(float(_cfg_get(cfg, "rate", "netease_min_interval", 0.5)), 0.0)
    per_track_sleep = max(float(_cfg_get(cfg, "rate", "per_track_sleep", 1.0)), 0.0)
    alias_groups = _alias_groups(cfg)

    fails_path = Path(match_fails_path) if match_fails_path is not None else MATCH_FAILS
    _search = search_fn if search_fn is not None else (lambda q: _netease_search(q, cfg=cfg))
    _get_url = url_fn if url_fn is not None else (lambda sid: _gd_url_for(sid, cfg=cfg))
    _dl = download_fn if download_fn is not None else (
        lambda u, dst: download_stream(u, dst, min_bytes=102400, timeout=300)
    )

    skip = _load_match_fails(full_retry, fails_path)
    if only_files is not None:
        wanted_names = {Path(str(x)).name for x in only_files if str(x).strip()}
        files = sorted(f for f in os.listdir(music_dir) if f in wanted_names)
    else:
        files = sorted(f for f in os.listdir(music_dir)
                       if f.lower().endswith(exts))
    results: list[dict] = []
    upgraded = 0
    total_files = len(files)
    _log_up(f"[upgrade] 共 {total_files} 个文件待处理（目录: {music_dir}）")
    for idx, fname in enumerate(files, 1):
        p = music_dir / fname
        stem = p.stem
        rec: dict = {"file": fname, "status": "kept"}

        # permanent_skip 子串匹配文件名：优先级最高
        if any(s and s in fname for s in permanent_skip):
            rec["status"] = "permanent_skip"
            _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 永久跳过")
            results.append(rec)
            continue
        # 同文件无匹配 ≥2 次跳过（full_retry 已清空）
        if skip.get(fname, 0) >= 2:
            rec["status"] = "skipped_fails"
            rec["fails"] = skip[fname]
            _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 跳名单略过（连续失败 {skip[fname]} 次）")
            results.append(rec)
            continue
        if limit is not None and len([r for r in results if r["status"] not in
                                      ("permanent_skip", "skipped_fails")]) >= limit:
            break
        _log_up(f"[upgrade] ({idx}/{total_files}) 正在处理: {fname}")

        sdur, in_br, t_title, t_artist = _probe_meta(str(p))
        sdur = sdur or 0.0
        # 标签优先，文件名兜底（upgrade_original.py:145-155）
        if " - " in stem:
            f_title, f_artist = stem.split(" - ", 1)
        else:
            f_title, f_artist = stem, ""
        f_title = re.sub(r"\[(BV|yt)[0-9A-Za-z_\-]+\]", "", f_title).strip(" -_")
        f_artist = re.sub(r"[\s._-]*hires$", "", f_artist, flags=re.I).strip(" _")
        f_artist = f_artist.replace("Covered by ", " ").strip()
        title = t_title or f_title
        artist = t_artist or f_artist
        artist_list = [a.strip() for a in re.split(r" _ |[,，/、&]", artist) if a.strip()]
        is_ogg_input = p.suffix.lower() == ".ogg"

        # 网易云 ±search_win 搜 id
        sid = None
        for q in _queries_for(title, artist):
            for s in (_search(q) or []):
                if not isinstance(s, dict):
                    continue
                cand_id = str(s.get("id") or "")
                cand_name = str(s.get("name") or s.get("title") or "")
                if not cand_id:
                    continue
                if no_picks and any(pk == cand_id or pk in cand_name for pk in no_picks):
                    continue
                if not nt_in_nc(title, cand_name):
                    continue
                raw_artists = s.get("artists")
                if isinstance(raw_artists, list):
                    cand_artists = ", ".join(
                        str(a.get("name") or "") if isinstance(a, dict) else str(a)
                        for a in raw_artists if a
                    )
                else:
                    cand_artists = str(raw_artists or "")
                if artist_list and not artist_ok(artist_list, cand_artists, alias_groups=alias_groups):
                    continue
                sd = s.get("dur") if "dur" in s else _norm_dur(s.get("duration"))
                if sd and sdur and abs(sd - sdur) > search_win:
                    continue
                sid = cand_id
                break
            if sid:
                break
            if netease_interval > 0:
                time.sleep(netease_interval)
        if not sid:
            _bump_match_fails(skip, fname, fails_path)
            rec["status"] = "no_match"
            rec["fails"] = skip[fname]
            _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 未匹配到网易云条目")
            results.append(rec)
            continue

        is_flac_input = p.suffix.lower() == ".flac"
        if is_flac_input and _is_real_flac(p):
            # 已是真 FLAC：仅就地补齐封面与标签，免重下整首音频
            repaired, rep_err = _repair_existing_flac(p, music_dir, stem, title, artist, sid, search_fn)
            if repaired:
                rec["status"] = "upgraded"
                rec["mode"] = "cover_tags_only"
                rec["final"] = p.name
                rec["src_ext"] = ".flac"
                upgraded += 1
                _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 已补封面/标签（真 FLAC 免重下）")
            else:
                rec["status"] = "no_cover"
                _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 补封面失败（{rep_err}）")
            results.append(rec)
            continue

        # GDStudio get_url 阶梯
        url_res = _get_url(sid)
        url, src_br_tag = url_res[0], int(url_res[1] or 0)
        if not url:
            rec["status"] = "no_url"
            _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 无可用直链")
            results.append(rec)
            continue
        raw_ext = guess_ext_from_url(url)
        if raw_ext == ".bin":
            raw_ext = ".mp3"  # 蓝本兜底：未知后缀按 mp3 处理
        claims_lossless = (raw_ext == ".flac") or (
            isinstance(src_br_tag, (int, float))
            and not isinstance(src_br_tag, bool)
            and src_br_tag >= 999000
        )

        # mp3/flac 输入：仅声称无损（.flac 后缀或 br>=999000）才下载进入实测确认
        if not is_ogg_input and not claims_lossless:
            rec["status"] = "not_lossless"
            rec["src_ext"] = raw_ext
            rec["src_br"] = src_br_tag
            _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 非无损源（{raw_ext} / {src_br_tag}），保留原文件")
            results.append(rec)
            continue

        # 下载验证（<100KB 由 util.download_stream 拒收抛错）
        tmp = staging / f"upg_{idx}_{re.sub(r'[^0-9A-Za-z]', '', stem)[:24]}{raw_ext}"
        try:
            nbytes = _dl(url, tmp)
        except Exception as e:
            rec["status"] = "download_error"
            rec["error"] = str(e)[:200]
            _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 下载失败（{rec['error'][:60]}）")
            results.append(rec)
            continue
        ndur = None
        try:
            ndur = ffmpeg.probe_duration(str(tmp))
        except Exception:
            ndur = None
        if not ndur or ndur < MIN_DUR or (sdur and abs(ndur - sdur) > verify_win):
            tmp.unlink(missing_ok=True)
            rec["status"] = "duration_mismatch"
            rec["ndur"] = ndur
            _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 时长不符（{ndur}s），跳过")
            results.append(rec)
            continue

        # 实测 FLAC 判定（同步 c0a6aa8）：ffprobe 查音频流 codec_name == "flac"
        src_lossless = raw_ext == ".flac"
        try:
            info = ffmpeg.probe_full(str(tmp))
            audio = next((st for st in (info.get("streams") or [])
                          if st.get("codec_type") == "audio"), None)
            codec = ((audio or {}).get("codec_name") or "").lower()
            src_lossless = codec == "flac"
        except Exception:
            pass

        # mp3 输入经实测确认非真 FLAC：不升并清理临时文件
        if not is_ogg_input and not src_lossless:
            tmp.unlink(missing_ok=True)
            rec["status"] = "not_lossless"
            rec["src_ext"] = raw_ext
            rec["src_br"] = src_br_tag
            results.append(rec)
            continue

        # OGG 输入：better() 判定（lossless 或 码率 ≥ max(260, ogg+60)，两端均为 kbps）
        if is_ogg_input and not src_lossless:
            src_br = round(nbytes * 8 / ndur / 1000)
            if not better(src_lossless, src_br, in_br):
                tmp.unlink(missing_ok=True)
                rec["status"] = "kept_not_better"
                rec["src_ext"] = raw_ext
                rec["src_br"] = src_br
                rec["ogg_br"] = in_br
                results.append(rec)
                continue

        # 抽样留证：替换前旧文件 PCM 指纹（不强制相等，只记录）
        pcm_old = None
        need_pcm = idx % PCM_SAMPLE_EVERY == 1
        if need_pcm:
            try:
                pcm_old = ffmpeg.pcm_md5(str(p))
            except Exception:
                pcm_old = None

        final: Path
        tmp_final: Path
        if src_lossless:
            # FLAC 源：remux 成 <stem>.new.flac（真扩展名 + 显式 -f flac）
            final = music_dir / f"{stem}.flac"
            tmp_final = music_dir / f"{stem}.new.flac"
            cover = music_dir / f"{stem}.jpg"
            if not cover.exists() and search_fn is None and sid:
                _fetch_netease_cover(sid, cover)
            ok, err = _remux_flac(tmp, tmp_final, title, artist,
                                  cover if cover.exists() else None)
            if not ok:
                tmp_final.unlink(missing_ok=True)
                tmp.unlink(missing_ok=True)
                rec["status"] = "failed"
                rec["error"] = f"remux: {err}"
                results.append(rec)
                continue
            fdur = None
            try:
                fdur = ffmpeg.probe_duration(str(tmp_final))
            except Exception:
                fdur = None
            if not fdur or fdur < MIN_DUR or (sdur and abs(fdur - sdur) > verify_win):
                # 不过连 .new.flac 一起删、写 match_fails
                tmp_final.unlink(missing_ok=True)
                tmp.unlink(missing_ok=True)
                _bump_match_fails(skip, fname, fails_path)
                rec["status"] = "final_duration_mismatch"
                rec["fdur"] = fdur
                rec["fails"] = skip[fname]
                results.append(rec)
                continue
        else:
            # OGG 输入的高码率 mp3/m4a 源：-c copy 重写标签后落位
            final = music_dir / f"{stem}{raw_ext}"
            try:
                from . import ffmpeg as _ff
                _ff.retag_copy(str(tmp), title=title, artist=artist)  # 原地 .tagtmp+os.replace
            except Exception as e:
                tmp.unlink(missing_ok=True)
                rec["status"] = "failed"
                rec["error"] = f"retag: {str(e)[:200]}"
                results.append(rec)
                continue
            tmp_final = tmp

        # 安全落位：若目标 final 已存在且与旧文件 p 路径不同，先备份再替换，失败回滚
        backup_path: Path | None = None
        try:
            if final.exists() and final.resolve() != p.resolve():
                backup_dir = staging / "backup"
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_path = backup_dir / final.name
                cross_move(final, backup_path)
            try:
                os.replace(str(tmp_final), str(final))
            except OSError:
                cross_move(tmp_final, final)
        except Exception as e:
            if backup_path is not None and backup_path.exists() and not final.exists():
                try:
                    cross_move(backup_path, final)
                except Exception:
                    pass
            tmp_final.unlink(missing_ok=True)
            tmp.unlink(missing_ok=True)
            rec["status"] = "failed"
            rec["error"] = f"place: {str(e)[:200]}"
            results.append(rec)
            continue

        if backup_path is not None and backup_path.exists():
            backup_path.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)
        if p.exists() and p.resolve() != final.resolve():
            p.unlink(missing_ok=True)

        rec["status"] = "upgraded"
        rec["final"] = final.name
        rec["src_ext"] = ".flac" if src_lossless else raw_ext
        _log_up(f"[upgrade] ({idx}/{total_files}) {fname} -> 已升级为 {final.name}")
        if src_lossless:
            rec["ndur"] = round(ndur, 1)
        if need_pcm:
            try:
                rec["pcm_md5_old"] = pcm_old
                rec["pcm_md5_new"] = ffmpeg.pcm_md5(str(final))
                rec["pcm_equal"] = rec["pcm_md5_new"] == pcm_old
            except Exception:
                rec["pcm_md5_new"] = None
        upgraded += 1
        if per_track_sleep > 0:
            time.sleep(per_track_sleep)
        results.append(rec)

    summary = {"total": len(files), "upgraded": upgraded,
               "kept": sum(1 for r in results if r["status"].startswith(("kept", "no_", "not_"))),
               "failed": sum(1 for r in results if r["status"] == "failed")}
    return [{"summary": summary}] + results
