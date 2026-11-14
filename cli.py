"""flac-hunter 命令行入口：音乐无损下载/曲库管理。

子命令：prepare / download / upgrade / audit / dedupe / lyrics-check /
rename / durations-cache / fingerprint。
"""
from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
try:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 支持 python -I 隔离模式运行：把脚本所在目录插到 sys.path 最前
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _log(msg: str) -> None:
    """统一经 console.log 输出（带时间戳）。"""
    from flac_hunter.console import log

    log(msg)


def _jsonify(x):
    """str 形态的 JSON 文本解成对象，其余原样返回。"""
    if isinstance(x, str):
        return json.loads(x)
    return x


def _tracks_from(res):
    """从 fetch 结果提取曲目列表：list 直接用，dict 取常用键。"""
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        for k in ("tracks", "songlist", "items"):
            v = res.get(k)
            if isinstance(v, list):
                return v
    return []


def _lookup_map(res):
    """lookup 结果归一为 {uri: {duration_ms, image_url}}。"""
    res = _jsonify(res)
    if isinstance(res, dict) and isinstance(res.get("entities"), list):
        out = {}
        for e in res["entities"]:
            dur = None
            for m in e.get("metadata", []):
                if m.get("field") == "duration":
                    try:
                        dur = int(m["value"])
                    except (TypeError, ValueError):
                        dur = None
            out[e.get("uri")] = {"duration_ms": dur, "image_url": e.get("image_url")}
        return out
    if isinstance(res, dict):
        # 已是 {uri: {...}} 形态
        return res
    return {}


def _artist_names(artists):
    """artists 字段归一成字符串列表（兼容 dict 列表形态）。"""
    out = []
    for a in artists or []:
        if isinstance(a, dict):
            v = a.get("name")
        else:
            v = a
        if v:
            out.append(str(v))
    return out


def _norm_spotify_track(t):
    """spotify 原始 track -> 统一 schema（artists 拆 name、album 取 name）。"""
    album = t.get("album")
    if isinstance(album, dict):
        album = album.get("name")
    out = {
        "uri": t.get("uri"),
        "name": t.get("name") or t.get("trackName") or "",
        "artists": _artist_names(t.get("artists")),
        "album": album,
        "position": t.get("position"),
        "duration_ms": t.get("duration_ms"),
        "image_url": t.get("image_url"),
    }
    return out


def _qq_track_map(s, pos):
    """QQ songlist 原始条目 -> 统一 schema（qq2_dl.py:140-152 字段语义）。"""
    interval = s.get("interval")
    try:
        duration_ms = int(float(interval) * 1000) if interval else None
    except (TypeError, ValueError):
        duration_ms = None
    album = s.get("album")
    if isinstance(album, dict):
        album = album.get("name")
    uri_id = s.get("songmid") or s.get("songid") or s.get("mid") or s.get("id")
    return {
        "uri": f"qq:{uri_id}" if uri_id else None,
        "name": s.get("songname") or s.get("songtit") or "",
        "artists": _artist_names(s.get("singer") or s.get("singers")),
        "album": album,
        "position": pos,
        "duration_ms": duration_ms,
        "image_url": None,
    }


# ---------- prepare ----------


def cmd_prepare(args):
    """拉歌单元数据 + 时长补齐 + 三层查重，输出 tracks.json。"""
    from flac_hunter.config import load_config
    from flac_hunter.library import LibraryIndex
    from flac_hunter.match.normalize import sanitize

    cfg = load_config()
    uri = args.uri
    tracks = []
    kind = "spotify"
    if uri.startswith("spotify:"):
        from flac_hunter.spotify_cli import (
            SpotifyCli,
            parse_playlist_json,
            parse_lookup_json,
        )

        cli = SpotifyCli(cfg.paths.spotify_cli)
        raw_raw = cli.playlist_get(uri)  # 已解析 dict（parse_playlist_json）
        raw = _jsonify(raw_raw)
        try:
            parsed = parse_playlist_json(raw if isinstance(raw, dict) else raw_raw)
        except Exception:
            parsed = None
        tracks_raw = _tracks_from(parsed) if parsed is not None else _tracks_from(raw)
        tracks = [_norm_spotify_track(t) for t in tracks_raw]
        _log(
            f"playlist: {raw.get('name') if isinstance(raw, dict) else '?'} | "
            f"track_count={raw.get('track_count') if isinstance(raw, dict) else '?'} "
            f"fetched={len(tracks)}"
        )
        uris = [t.get("uri") for t in tracks if t.get("uri")]
        by_uri = {}
        if uris:
            out = _jsonify(cli.lookup_durations(uris))
            by_uri = _lookup_map(parse_lookup_json(out) or out)
        for t in tracks:
            info = by_uri.get(t.get("uri")) or {}
            if t.get("duration_ms") is None and info.get("duration_ms") is not None:
                t["duration_ms"] = info["duration_ms"]
            if not t.get("image_url") and info.get("image_url"):
                t["image_url"] = info["image_url"]
    elif uri.startswith("qq:"):
        from flac_hunter.spotify_cli import fetch_qq_playlist

        kind = "qq"
        disstid = uri.split(":", 1)[1]
        songlist = _tracks_from(fetch_qq_playlist(disstid))
        tracks = [_qq_track_map(s, pos) for pos, s in enumerate(songlist, 1)]
    else:
        raise SystemExit("--uri 仅支持 spotify:... 或 qq:<disstid>")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    index = LibraryIndex(cfg.paths.music)
    records = []
    for i, t in enumerate(tracks, 1):
        artists = list(t.get("artists") or [])
        rec = {
            "type": kind,
            "uri": t.get("uri"),
            "name": t.get("name"),
            "artists": artists,
            "album": t.get("album"),
            "position": t.get("position") or i,
            "duration_ms": t.get("duration_ms"),
            "image_url": t.get("image_url"),
        }
        rec["filename_stem"] = "{0} - {1}".format(
            sanitize(rec["name"] or ""),
            " _ ".join(sanitize(a) for a in artists),
        )
        rec["existing"] = False
        rec["existing_file"] = None
        rec["dedupe_reason"] = None
        try:
            res = index.dedupe_track(rec)
        except Exception as exc:  # 查重失败不阻断整体输出
            _log(f"查重失败 [{rec.get('name')}]: {exc}")
            res = None
        entry, reason = None, None
        if isinstance(res, tuple) and res:
            entry, reason = (list(res) + [None])[:2]
        elif isinstance(res, dict):  # 未来可能的 dict 形态
            entry, reason = res.get("existing_file"), res.get("dedupe_reason")
        if isinstance(entry, dict):
            entry = entry.get("file")
        if reason in ("artist", "duration") and entry:
            rec["existing"] = True
            rec["existing_file"] = entry
            rec["dedupe_reason"] = reason
        elif reason == "same_title_other":
            rec["dedupe_reason"] = "same_title_other"  # 照常下载
        records.append(rec)

    out_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _log(f"tracks.json 写入 {len(records)} 条 -> {out_path}")


# ---------- download / upgrade ----------


def cmd_download(args):
    """按 tracks.json 编排下载（pipeline.run_download）。"""
    from flac_hunter.config import load_config
    from flac_hunter.pipeline import run_download

    cfg = load_config()
    tracks = json.loads(Path(args.tracks).read_text(encoding="utf-8"))
    only_ids = None
    if args.only:
        only_ids = [x.strip() for x in args.only.split(",") if x.strip()]
    res = run_download(
        tracks,
        cfg,
        source=args.source,
        only_ids=only_ids,
        limit=args.limit,
        include_existing=args.include_existing,
    )
    if isinstance(res, (list, tuple)):
        stat = {}
        for r in res:
            st = str(r.get("status") if isinstance(r, dict) else r)
            stat[st] = stat.get(st, 0) + 1
        for k in sorted(stat, key=lambda k: -stat[k]):
            _log(f"  {k}: {stat[k]}")
    _log("download 完成（明细见 tasks/results.jsonl）")


def cmd_upgrade(args):
    """旧文件无损升级（upgrade.run_upgrade）。"""
    from flac_hunter.config import load_config
    from flac_hunter.upgrade import run_upgrade

    cfg = load_config()
    run_upgrade(cfg, ext=args.ext, full_retry=args.full_retry, limit=args.limit)
    _log("upgrade 完成")


# ---------- audit / dedupe / lyrics-check / rename / durations-cache ----------


def _audit_concl(r):
    """把 audit_one 的返回归一成结论字符串。"""
    if isinstance(r, dict):
        ok = r.get("flac_ok", r.get("ok"))
        if ok in (True, "PASS", "pass", "真FLAC"):
            return "PASS"
        return f"FAIL({r})"
    if isinstance(r, tuple) and r:
        return str(r[0])
    return str(r)


def cmd_audit(args):
    """四项质量门扫全库 .flac：时长/标签/封面/真 FLAC。"""
    from flac_hunter.audit import audit_one
    from flac_hunter.config import load_config

    cfg = load_config()
    music = Path(cfg.paths.music)
    if not music.is_dir():
        _log(f"曲库目录不存在: {music}")
        return
    files = sorted(music.glob("*.flac"))
    _log(f"audit: {len(files)} 个 .flac")
    try:
        params = set(inspect.signature(audit_one).parameters)
    except (TypeError, ValueError):
        params = set()
    kwargs = {}
    for name in ("duration_ms", "expect_ms"):
        if name in params:
            kwargs[name] = None  # 无期望时长来源，时长门交由调用方配置
            break
    passed = failed = 0
    fail_lines = []
    for f in files:
        try:
            r = audit_one(str(f), **kwargs) if kwargs else audit_one(str(f))
        except TypeError:
            try:
                r = audit_one(str(f))
            except Exception as exc:
                r = f"FAIL({exc})"
        except Exception as exc:
            r = f"FAIL({exc})"
        concl = _audit_concl(r)
        if "FAIL" in concl.upper():
            failed += 1
            fail_lines.append(f"{f.name}: {concl}")
        else:
            passed += 1
    _log(f"audit 完成: PASS={passed} FAIL={failed}")
    for line in fail_lines[:50]:
        _log(f"  {line}")


def _iter_groups(res):
    """find_dups 返回值归一成成员列表的迭代。"""
    if isinstance(res, dict):
        values = list(res.values())
    elif isinstance(res, (list, tuple)):
        values = list(res)
    else:
        raise ValueError(f"find_dups 返回形态不识别: {type(res)!r}")
    for g in values:
        if isinstance(g, dict):
            members = g.get("files") or g.get("members") or []
        elif isinstance(g, (list, tuple)):
            members = g
        else:
            members = [g]
        yield [str(m[0]) if isinstance(m, (list, tuple)) and m else str(m) for m in members]


def cmd_dedupe(args):
    """曲库查重聚类（library.find_dups）。"""
    from flac_hunter.config import load_config
    from flac_hunter.library import find_dups

    cfg = load_config()
    music = Path(cfg.paths.music)
    if not music.is_dir():
        _log(f"曲库目录不存在: {music}")
        return
    res = find_dups(str(music))
    groups = [g for g in _iter_groups(res) if len(g) > 1]
    groups.sort(key=len, reverse=True)
    _log(f"dedupe: {len(groups)} 组疑似重复")
    for i, g in enumerate(groups, 1):
        _log(f"== 组 {i} ({len(g)} 个) ==")
        for m in g:
            _log(f"   {m}")


def cmd_lyrics_check(args):
    """歌词体检八类（audit.check_lyrics_dir）。"""
    from flac_hunter.audit import check_lyrics_dir
    from flac_hunter.config import load_config

    cfg = load_config()
    music = Path(cfg.paths.music)
    if not music.is_dir():
        _log(f"曲库目录不存在: {music}")
        return
    res = check_lyrics_dir(str(music))
    if isinstance(res, dict):
        for cls in sorted(res):
            entries = res[cls] or []
            if entries:
                _log(f"{cls}: {len(entries)}")
                for e in entries[:30]:
                    _log(f"   {e}")
    else:
        _log(str(res))
    _log("lyrics-check 完成")


def _plan_items(plan):
    """scan_rename 返回值归一成 [(file, issues, proposal)] 列表。"""
    if isinstance(plan, dict):
        if "plan" in plan or "items" in plan:
            plan = plan.get("plan") or plan.get("items") or []
        else:
            plan = list(plan.items())
    out = []
    for it in plan or []:
        if isinstance(it, dict):
            f = it.get("file") or it.get("filename") or it.get("path")
            out.append((str(f), list(it.get("issues") or []), it.get("proposal")))
        elif isinstance(it, (list, tuple)) and it:
            f = str(it[0])
            issues = list(it[1]) if len(it) > 1 and isinstance(it[1], (list, tuple)) else []
            proposal = it[2] if len(it) > 2 else None
            out.append((f, issues, proposal))
        else:
            out.append((str(it), [], None))
    return out


def cmd_rename(args):
    """曲库改名扫描；--apply 才执行，否则 dry-run。"""
    from flac_hunter.audit import apply_rename, scan_rename
    from flac_hunter.config import load_config

    cfg = load_config()
    music = Path(cfg.paths.music)
    if not music.is_dir():
        _log(f"曲库目录不存在: {music}")
        return
    plan = scan_rename(str(music), cfg)
    items = _plan_items(plan)
    _log(f"rename {'apply' if args.apply else 'dry-run'}: {len(items)} 个待处理")
    for f, issues, proposal in items:
        _log(f"   {f} [{','.join(map(str, issues))}] -> {proposal}")
    if args.apply:
        try:
            res = apply_rename(cfg, plan)
        except TypeError:
            res = apply_rename(plan)
        _log(f"apply 完成: {res}")
    else:
        _log("dry-run：未改动任何文件")


def cmd_durations_cache(args):
    """重建 tasks/local_durations.json（library.build_durations_cache）。"""
    from flac_hunter.config import load_config
    from flac_hunter.library import build_durations_cache

    cfg = load_config()
    music = Path(cfg.paths.music)
    if not music.is_dir():
        _log(f"曲库目录不存在: {music}")
        return
    res = build_durations_cache(str(music), cfg)
    cache = None
    if isinstance(res, dict):
        cache = res
    elif isinstance(res, tuple) and res and isinstance(res[0], dict):
        cache = res[0]
    if cache is not None:
        # build_durations_cache 内部已按 TASKS_DIR/local_durations.json 落盘
        _log(f"durations-cache 完成（{len(cache)} 条，tasks/local_durations.json）")
    else:
        _log("durations-cache 完成")


def cmd_fingerprint(args):
    """对比两文件 PCM 指纹（ffmpeg.pcm_md5）。"""
    from flac_hunter.ffmpeg import pcm_md5

    h1 = pcm_md5(args.a)
    h2 = pcm_md5(args.b)
    _log(f"{args.a}  md5={h1}")
    _log(f"{args.b}  md5={h2}")
    _log("指纹一致" if (h1 and h1 == h2) else "指纹不一致")


# ---------- argparse 装配 ----------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="flac-hunter",
        description="音乐无损下载/曲库管理 CLI（私有自用）",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare", help="拉取歌单元数据并三层查重，输出 tracks.json")
    p.add_argument("--uri", required=True, help="spotify:... 或 qq:<disstid>")
    p.add_argument("--out", default="tasks/tracks.json", help="输出路径")
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("download", help="按 tracks.json 编排下载")
    p.add_argument("--tracks", default="tasks/tracks.json", help="输入 tracks.json")
    p.add_argument(
        "--source",
        default="auto",
        choices=["auto", "gdstudio", "netease", "bili", "youtube", "musicdl"],
        help="音源（默认 auto 依次择优）",
    )
    p.add_argument("--only", default=None, help="仅处理指定 id（逗号分隔）")
    p.add_argument("--limit", type=int, default=None, help="最多处理 N 条")
    p.add_argument("--include-existing", action="store_true", help="包含查重命中的曲目")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("upgrade", help="旧文件无损升级")
    p.add_argument("--ext", default="mp3", choices=["mp3", "ogg", "all"], help="目标扩展名")
    p.add_argument("--full-retry", action="store_true", help="清空 match_fails.json 跳名单重试")
    p.add_argument("--limit", type=int, default=None, help="最多处理 N 个文件")
    p.set_defaults(func=cmd_upgrade)

    p = sub.add_parser("audit", help="四项质量门扫全库 .flac")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("dedupe", help="曲库查重聚类")
    p.set_defaults(func=cmd_dedupe)

    p = sub.add_parser("lyrics-check", help="歌词体检八类")
    p.set_defaults(func=cmd_lyrics_check)

    p = sub.add_parser("rename", help="曲库改名扫描（默认 dry-run）")
    p.add_argument("--apply", action="store_true", help="执行改名（缺省仅预览）")
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("durations-cache", help="重建 tasks/local_durations.json")
    p.set_defaults(func=cmd_durations_cache)

    p = sub.add_parser("fingerprint", help="对比两文件 PCM 指纹")
    p.add_argument("a", help="文件 A")
    p.add_argument("b", help="文件 B")
    p.set_defaults(func=cmd_fingerprint)

    return ap


def main(argv=None):
    from flac_hunter.console import setup_console

    try:
        setup_console()
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
