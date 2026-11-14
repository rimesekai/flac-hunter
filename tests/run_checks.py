"""flac-hunter 离线自检脚本（零网络）。

逐项跑 check(name, fn)；断言失败抛 AssertionError 并记录，全部通过时
结尾打印 ALL CHECKS PASSED。ffmpeg/ffprobe 仅本地执行，不发起任何
对 GDStudio/网易云/B站/LRCLIB/QQ/Spotify 的请求。临时文件放 tempfile，
结束清理。全文应 <60s。
"""
from __future__ import annotations

import inspect
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
try:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn

    return deco


# ---------- 通用工具 ----------


def _run_ff(args):
    """本地跑 ffmpeg/ffprobe（非网络），失败抛 AssertionError。"""
    p = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=60,
    )
    if p.returncode != 0:
        raise AssertionError(f"ffmpeg 失败 {args}: {p.stderr.strip()[-300:]}")
    return p


def _make_sine_flac(path, seconds=5.0):
    """本地生成正弦波 flac。"""
    _run_ff([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
        "-c:a", "flac", str(path),
    ])


def _make_color_jpg(path):
    """本地生成纯色 jpg（封面）。"""
    _run_ff([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=red:s=320x320",
        "-frames:v", "1", str(path),
    ])


def _call_adapted(fn, **kwargs):
    """按 fn 实际签名过滤 kwargs 后调用（对实现签名的宽容适配）。"""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return fn(**kwargs)
    kw = {k: v for k, v in kwargs.items() if k in params}
    return fn(**kw)


def _remux_flac_adapted(ff, src, out, cover, title, artist, album):
    """remux_flac 的签名宽容适配调用。"""
    try:
        sig = inspect.signature(ff.remux_flac)
        params = sig.parameters
    except (TypeError, ValueError):
        params = {}
    name_map = {
        "src": ("src", "source", "inp", "in_path", "path", "in_"),
        "out": ("out", "dest", "dst", "out_path"),
        "cover": ("cover", "cover_jpg", "jpg", "cover_path"),
        "title": ("title",),
        "artist": ("artist",),
        "album": ("album",),
    }
    values = {
        "src": str(src), "out": str(out), "cover": str(cover),
        "title": title, "artist": artist, "album": album,
    }
    kw = {}
    for want, names in name_map.items():
        for n in names:
            if n in params:
                kw[n] = values[want]
                break
    missing = [
        p for p in params
        if p not in kw
        and p not in ("self", "args", "kwargs")
        and params[p].default is inspect.Parameter.empty
    ]
    if missing:
        raise AssertionError(f"remux_flac 签名不识别: {list(params)}，缺 {missing}")
    return ff.remux_flac(**kw)


def _tag_pick(tags, key):
    """ffprobe 标签大小写不敏感取值。"""
    for k, v in (tags or {}).items():
        if k.lower() == key.lower() and str(v).strip():
            return str(v).strip()
    return ""


def _uni_list(x):
    """把返回值归一成成员列表（供 find_dups 断言）。"""
    if isinstance(x, dict):
        groups = list(x.values())
    elif isinstance(x, (list, tuple)):
        groups = list(x)
    else:
        groups = [x]
    out = []
    for g in groups:
        if isinstance(g, dict):
            members = g.get("files") or g.get("members") or []
        elif isinstance(g, (list, tuple)):
            members = g
        else:
            members = [g]
        out.append([str(m[0]) if isinstance(m, (list, tuple)) and m else str(m) for m in members])
    return out


# ---------- a) norm_text 各步 ----------


@check("a.norm_text 括号剥离/feat 去除/过滤/分隔符")
def t_norm_text():
    from flac_hunter.match.normalize import norm_text

    assert norm_text("Track featuring X") == "track", norm_text("Track featuring X")
    assert norm_text("夜に駆ける (feat. Mota)") == "夜に駆ける"
    assert norm_text("Song (Live ver.)") == "song"          # () 剥离
    assert norm_text("Song【特典】（版）[x]") == "song"        # 【】（）[] 整段剥离
    assert norm_text("Hello! World#") == "hello world"       # 纯字符过滤
    assert norm_text("  x   y  ") == "x y"                   # 空格折叠
    assert norm_text("A／B") == "a b"                        # 全角／ NFKC->/ 被过滤
    assert norm_text("A\u29f8B") == "a b"                    # ⧸(U+29F8) 被过滤


# ---------- b) romaji_fold ----------


@check("b.romaji_fold 长音折叠")
def t_romaji_fold():
    from flac_hunter.match.normalize import romaji_fold

    assert romaji_fold("Toukyou") == "Tokyo", romaji_fold("Toukyou")
    assert romaji_fold("Kaijuu") == "Kaiju"
    assert romaji_fold("Room") == "Rom"


# ---------- c) contains_variant ----------


@check("c.contains_variant 整词匹配（rim 不撞 pilgrim）")
def t_contains_variant():
    from flac_hunter.match.normalize import contains_variant

    assert not contains_variant("pilgrim", "rim"), "rim 不得撞 pilgrim"
    assert contains_variant("rim tokusetsu", "rim")
    assert contains_variant("(rim) live", "rim")
    assert not contains_variant("Mili", "mili")  # 蓝本大小写敏感


# ---------- d) core_key ----------


@check("d.core_key 保留版本词括号、剥 feat/explicit")
def t_core_key():
    from flac_hunter.match.normalize import core_key

    assert core_key("Song (Remix)") == "songremix", core_key("Song (Remix)")
    assert core_key("Song (Live ver.)") == "songlivever"
    assert core_key("Song (feat. X)") == "song", core_key("Song (feat. X)")
    assert core_key("Song (Explicit)") == "song"


# ---------- e) t2s ----------


@check("e.t2s 繁转简")
def t_t2s():
    from flac_hunter.match.normalize import t2s

    assert t2s("雲") == "云", t2s("雲")
    assert t2s("愛") == "爱"
    assert t2s("龍の雲と愛") == "龙の云と爱"  # 表外假名原样保留


# ---------- f) alt_titles_for + config 校验 ----------


@check("f.alt_titles_for 别名命中 + config.toml 14/13 条")
def t_alt_titles():
    from flac_hunter.match.normalize import alt_titles_for

    forms = [
        {"Good Weather|Orangestar": ["快晴"]},
        [("Good Weather", "Orangestar", ["快晴"])],
        [{"title": "Good Weather", "artist": "Orangestar", "alts": ["快晴"]}],
    ]
    ok, last = False, None
    for e in forms:
        try:
            r = alt_titles_for("Good Weather", "Orangestar", e)
        except Exception as exc:
            last = exc
            continue
        if list(r) == ["快晴"]:
            ok = True
            break
        last = r
    assert ok, f"alt_titles_for 未返回 ['快晴']: {last!r}"

    cfg_path = REPO / "config.toml"
    if cfg_path.exists():  # 存在时才校验个人表规模
        import tomllib

        with open(cfg_path, "rb") as fh:
            cfg = tomllib.load(fh)
        al = cfg.get("aliases") or {}
        art = al.get("art_aliases") or []
        alt = al.get("alt_titles") or []
        assert len(art) == 14, f"art_aliases={len(art)}"
        assert len(alt) == 13, f"alt_titles={len(alt)}"


# ---------- g) is_cover_like ----------


@check("g.is_cover_like BV/【/cover 命中与反例")
def t_is_cover_like():
    from flac_hunter.match.blacklist import is_cover_like

    assert is_cover_like("BV1mTaQ63Ek3 - Sky.flac")
    assert is_cover_like("【MV】Song.flac")
    assert is_cover_like("Song (cover).flac")
    assert is_cover_like("Song (off vocal).flac")
    assert not is_cover_like("Song - Artist.flac")
    assert not is_cover_like("Song (Live).flac")


# ---------- h) score_bili 翻唱 -999 ----------


@check("h.score_bili 含『翻唱』候选 -> -999")
def t_score_bili_cover():
    from flac_hunter.match.score import score_bili

    track = {"name": "Song", "artists": ["Orangestar"], "album": "",
             "duration_ms": 200000}
    cand = {
        "source": "bili", "id": "BV1x", "title": "【翻唱】Song",
        "artists": ["foo"], "duration": 200, "ext": None, "url": "",
        "extra": {"channel": "foo", "play": 10000},
        "channel": "foo", "play": 10000,
    }
    s = score_bili(track, cand, [], set())
    assert s == -999, f"score={s!r}"


# ---------- i) score_bili 时长窗三档 ----------


@check("i.score_bili 时长窗 ≤3s/≤8s/>60s 分数与蓝本一致")
def t_score_bili_windows():
    from flac_hunter.match.score import score_bili

    track = {"name": "Song", "artists": ["Orangestar"], "album": "",
             "duration_ms": 200000}

    def cand(d):
        return {
            "source": "bili", "id": "BV1", "title": "Song",
            "artists": ["Orangestar"], "duration": d, "ext": None, "url": "",
            "extra": {"channel": "Orangestar", "play": 10000},
            "channel": "Orangestar", "play": 10000,
        }

    s3 = score_bili(track, cand(203), [], set())
    s8 = score_bili(track, cand(207), [], set())
    s60 = score_bili(track, cand(300), [], set())
    # 蓝本数值：标题50 + 频道30 + 热度8(上限) + 时长窗(+25/+15/-50)
    assert abs(s3 - 113.0) < 1e-6, f"≤3s: {s3!r} (期望 113.0)"
    assert abs(s8 - 103.0) < 1e-6, f"≤8s: {s8!r} (期望 103.0)"
    assert abs(s60 - 38.0) < 1e-6, f">60s: {s60!r} (期望 38.0)"


# ---------- j) tier 分档 ----------


@check("j.tier_of A/B/C2 分档 + norm_dur")
def t_tier():
    from flac_hunter.match.tier import norm_dur, tier_of, tier_sort_key

    assert norm_dur(215000) == 215.0
    assert norm_dur(215) == 215.0
    assert norm_dur(None) is None

    aliases = ["artist"]
    name_aliases = ["song"]
    cand_a = {
        "source": "gdstudio", "id": "1", "title": "Song",
        "artists": ["Artist"], "duration": 203.0, "ext": None, "url": "",
        "extra": {},
    }
    assert tier_of(cand_a, 200.0, "Song", aliases, name_aliases) == "A"
    cand_b = dict(cand_a, artists=["Someone Else"])
    assert tier_of(cand_b, 200.0, "Song", aliases, name_aliases) == "B"
    cand_c2 = dict(cand_a, duration=None)
    assert tier_of(cand_c2, 200.0, "Song", aliases, name_aliases) == "C2"
    # 排序键可调用即可
    tier_sort_key(cand_a, "A")


# ---------- k) 空标题保护 ----------


@check("k.空标题保护 name_similar/name_core")
def t_empty_title():
    from flac_hunter.match.normalize import name_core, name_similar

    assert name_similar("", "X") is False
    assert name_similar("X", "") is False
    assert name_core("") == ""
    assert name_core(None) == ""


# ---------- l) nt-in-nc 方向 ----------


@check("l.upgrade.nt_in_nc 方向强制")
def t_nt_in_nc():
    from flac_hunter.upgrade import nt_in_nc

    assert nt_in_nc("Song (Live ver.)", "Song") is False, "禁止反向 nc-in-nt"
    assert nt_in_nc("Song (Live ver.)", "Song (Live ver.) [HQ]") is True


# ---------- m) ⧸ 分隔符处理 ----------


@check("m.⧸(U+29F8)/全角／分隔符处理")
def t_slash_separators():
    from flac_hunter.match.normalize import artist_related, name_related

    assert artist_related("Foo\u29f8Bar", {"foo"})
    assert artist_related("Foo／Bar", {"bar"})
    assert name_related("Song\u29f8Ver", ["Song"])
    assert name_related("Song／Ver", ["Song"])


# ---------- n) 词表长度 ----------


@check("n.BAD_WORDS 42/BILI_BAD 81/VIRTUAL_SINGERS 24/VERSION_MARKERS 22")
def t_wordlists():
    from flac_hunter.match import blacklist as bl

    assert len(bl.BAD_WORDS) == 42, len(bl.BAD_WORDS)
    assert len(bl.BILI_BAD) == 81, len(bl.BILI_BAD)
    assert len(bl.VIRTUAL_SINGERS) == 24, len(bl.VIRTUAL_SINGERS)
    assert len(bl.VERSION_MARKERS) == 22, len(bl.VERSION_MARKERS)
    assert len(bl.EDGE_WORDS) == 6, len(bl.EDGE_WORDS)
    # has_bad_version：命中黑名单但点赞曲本身含该词时放行
    assert bl.has_bad_version("Song (cover by X)", "Song")
    assert not bl.has_bad_version("Song (cover)", "Song (cover)")


# ---------- o) musicdl_ext 降级 ----------


@check("o.musicdl_ext 注入抛错 factory 后 search 返回 []")
def t_musicdl_degrade():
    from flac_hunter.sources import musicdl_ext

    assert hasattr(musicdl_ext, "MusicDlSource")
    assert hasattr(musicdl_ext, "AVAILABLE")

    def boom(*a, **k):
        raise RuntimeError("offline test")

    try:
        src = musicdl_ext.MusicDlSource(client_factory=boom)
    except TypeError:
        src = musicdl_ext.MusicDlSource(boom)
    track = {"name": "Song", "artists": ["Tester"], "duration_ms": 180000,
             "album": ""}
    try:
        r = src.search(track)
    except TypeError:
        r = src.search("Song", ["Tester"])
    assert r == [], f"期望空结果，得到 {r!r}"


# ---------- p) ffmpeg 往返 ----------


@check("p.ffmpeg 往返 remux/探测/标签/pcm_md5")
def t_ffmpeg_roundtrip():
    from flac_hunter import ffmpeg as ff

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_rt_"))
    try:
        src = tmp / "rt_src.flac"
        cover = tmp / "rt_cover.jpg"
        out = tmp / "rt_out.flac"
        _make_sine_flac(src, 5)
        _make_color_jpg(cover)
        _remux_flac_adapted(ff, src, out, cover, "Test Song", "Test Artist",
                            "Test Album")
        d = ff.probe_duration(out)
        assert d is not None and abs(d - 5.0) < 0.5, f"duration={d!r}"
        full = ff.probe_full(out)
        assert isinstance(full, dict), type(full)
        assert "format" in full and "streams" in full, list(full)
        meta = ff.probe_meta(out)
        tags = {}
        if isinstance(meta, dict):
            fmt = meta.get("format") or {}
            tags = fmt.get("tags") if isinstance(fmt, dict) else {}
            if not isinstance(tags, dict):
                tags = meta.get("tags") or {}
        assert _tag_pick(tags, "title") == "Test Song", tags
        assert _tag_pick(tags, "artist") == "Test Artist", tags
        h1 = ff.pcm_md5(out)
        h2 = ff.pcm_md5(out)
        assert h1 and h1 == h2, (h1, h2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- q) audit_one 四项门 ----------


@check("q.audit_one 四项门（remux 产物 flac_ok）")
def t_audit_one():
    from flac_hunter import ffmpeg as ff
    from flac_hunter.audit import audit_one

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_aud_"))
    try:
        src = tmp / "aud_src.flac"
        cover = tmp / "aud_cover.jpg"
        out = tmp / "aud_out.flac"
        _make_sine_flac(src, 5)
        _make_color_jpg(cover)
        _remux_flac_adapted(ff, src, out, cover, "Test Song", "Test Artist",
                            "Test Album")
        # audit 检查同名 .jpg 封面：把封面放到成品旁边
        shutil.copyfile(cover, tmp / "aud_out.jpg")
        r = _call_adapted(audit_one, path=str(out), flac_path=str(out),
                          duration_ms=5000, expect_ms=5000)
        if isinstance(r, dict):
            ok = r.get("flac_ok", r.get("ok"))
            assert ok in (True, "PASS", "pass"), f"audit_one={r!r}"
        elif isinstance(r, tuple) and r:
            concl = str(r[0])
            assert "FAIL" not in concl and "PASS" in concl, concl
        else:
            concl = str(r)
            assert "FAIL" not in concl, concl
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- r) classify_rename ----------


@check("r.classify_rename junk 命中")
def t_classify_rename():
    from flac_hunter.audit import classify_rename

    r = classify_rename("Song 【MV】 - aBcDeFgHiJk.mp3")
    issues = r[0] if isinstance(r, tuple) and r else r
    names = [str(x) for x in (issues if isinstance(issues, (list, tuple)) else [issues])]
    assert "junk" in names, r


# ---------- s) 歌词体检 ----------


@check("s.歌词体检 empty/no_timestamps/orphan")
def t_lyrics_check():
    from flac_hunter.audit import check_lyrics_dir

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_lrc_"))
    try:
        (tmp / "Test - Alpha.flac").write_bytes(b"")
        (tmp / "Test - Alpha.lrc").write_text(
            "[ti:Test]\n[ar:Alpha]\n[00:01.00]hello world line one\n"
            "[00:02.00]hello world line two\n[00:03.00]hello world line three\n",
            encoding="utf-8",
        )
        # Broken 有音频（0 字节，探测失败不触发 too_long/too_short），
        # 否则蓝本逻辑 orphan + continue 会跳过 empty/no_timestamps 判定
        (tmp / "Broken - Beta.flac").write_bytes(b"")
        (tmp / "Broken - Beta.lrc").write_text("no stamps here", encoding="utf-8")
        (tmp / "Ghost.lrc").write_text("[00:01.00]orphan\n", encoding="utf-8")

        res = check_lyrics_dir(str(tmp))
        assert isinstance(res, dict), type(res)

        def hit(cls, name):
            entries = res.get(cls) or []
            return any(name in str(e) for e in entries)

        assert hit("empty", "Broken - Beta.lrc"), res.get("empty")
        assert hit("no_timestamps", "Broken - Beta.lrc"), res.get("no_timestamps")
        assert hit("orphan", "Ghost.lrc"), res.get("orphan")
        normal = [
            cls for cls in res
            for e in (res[cls] or [])
            if "Test - Alpha.lrc" in str(e)
        ]
        assert not normal, f"正常 lrc 不应有 issue: {normal}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- t) find_dups ----------


@check("t.find_dups 聚类/0 字节不并入")
def t_find_dups():
    from flac_hunter.library import find_dups

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_dup_"))
    try:
        _make_sine_flac(tmp / "Song - Alpha.flac", 5)
        _make_sine_flac(tmp / "Song - Alpha 2.flac", 5)
        _make_sine_flac(tmp / "Other - Beta.flac", 5)
        (tmp / "Song - Zero.flac").write_bytes(b"")  # 探测失败不并入
        res = _call_adapted(find_dups, music_dir=str(tmp), music=str(tmp),
                            path=str(tmp))
        groups = _uni_list(res)
        has_pair = any(
            any("Song - Alpha.flac" in m for m in g)
            and any("Song - Alpha 2.flac" in m for m in g)
            for g in groups
        )
        assert has_pair, f"Alpha/Alpha 2 未聚组: {groups!r}"
        zero_groups = [g for g in groups if any("Song - Zero" in m for m in g)]
        assert all(len(g) == 1 for g in zero_groups), f"Zero 不应并入组: {zero_groups!r}"
        assert not any(
            any("Other - Beta" in m for m in g) and len(g) > 1 for g in groups
        ), "Beta 不应聚组"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- u) build_durations_cache ----------


@check("u.build_durations_cache 条目时长 ≈5.0")
def t_durations_cache():
    from flac_hunter.library import build_durations_cache

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_dur_"))
    try:
        _make_sine_flac(tmp / "Cache - Item.flac", 5)
        res = _call_adapted(build_durations_cache, music_dir=str(tmp),
                            music=str(tmp), path=str(tmp))
        if isinstance(res, tuple) and res and isinstance(res[0], dict):
            res = res[0]
        assert isinstance(res, dict), type(res)
        entry = None
        for k, v in res.items():
            if "Cache - Item" in str(k):
                entry = v
                break
        assert entry is not None, f"缺条目: {list(res)[:5]!r}"
        if isinstance(entry, (list, tuple)):
            entry = entry[0]
        assert abs(float(entry) - 5.0) < 0.5, f"duration={entry!r}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- v) scan_rename dry-run ----------


@check("v.scan_rename dry-run 计划")
def t_scan_rename():
    from flac_hunter.audit import scan_rename

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_ren_"))
    try:
        _make_sine_flac(tmp / "Song 【MV】 - aBcDeFgHiJk.flac", 5)
        _make_sine_flac(tmp / "Song - Alpha.flac", 5)
        res = _call_adapted(scan_rename, music_dir=str(tmp), music=str(tmp),
                            path=str(tmp))
        items = []
        if isinstance(res, dict):
            if "plan" in res or "items" in res:
                items = list(res.get("plan") or res.get("items") or [])
            else:
                items = list(res.items())  # {file: (issues, proposal)}
        elif isinstance(res, (list, tuple)):
            items = list(res)
        files = []
        junk_seen = False
        for it in items:
            if isinstance(it, dict):
                f = str(it.get("file") or it.get("filename") or it.get("path"))
                issues = [str(x) for x in (it.get("issues") or [])]
            elif isinstance(it, (list, tuple)) and it:
                f = str(it[0])
                inner = it[1] if len(it) > 1 else None
                if isinstance(inner, (list, tuple)) and inner and not isinstance(inner[0], (list, tuple)):
                    issues = [str(x) for x in inner]
                elif isinstance(inner, (list, tuple)) and inner:
                    issues = [str(x) for x in (inner[0] or [])]
                else:
                    issues = []
            else:
                f, issues = str(it), []
            files.append(f)
            if "aBcDeFgHiJk" in f:
                junk_seen = any("junk" in s for s in issues)
        assert any("aBcDeFgHiJk" in f for f in files), f"垃圾名未进计划: {files!r}"
        assert junk_seen, "计划项未标 junk"
        assert not any(
            f.endswith("Song - Alpha.flac") for f in files
        ), "正常文件不应进计划"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- w. parse_* 接受 bytes 载荷（真路径回归：util.http_get 返回 bytes） ----------


@check("w. parse_* 接受 bytes 载荷（真路径回归）")
def check_w_bytes_payload():
    import json as _json

    from flac_hunter.sources.bilibili import parse_search as bili_parse
    from flac_hunter.sources.gdstudio import parse_gd_search
    from flac_hunter.sources.netease import parse_search as ne_parse

    # netease：bytes 载荷（曾因 isinstance(payload, str) 盲区返回 [] 的真 bug）
    ne = _json.dumps({"result": {"songs": [
        {"id": 28483032, "name": "セプテンバーさん",
         "artists": [{"name": "RADWIMPS"}], "duration": 307173}]}}).encode("utf-8")
    c = ne_parse(ne)
    assert len(c) == 1 and str(c[0]["id"]) == "28483032" and abs((c[0]["duration"] or 0) - 307.173) < 0.01, \
        f"netease bytes 解析失败: {c!r}"

    # bilibili：bytes 载荷（video 块结构）
    bili = _json.dumps({"code": 0, "data": {"result": [
        {"result_type": "video", "data": [
            {"bvid": "BV1vw411p7ef", "title": "RADWIMPS - セプテンバーさん",
             "duration": "5:07", "author": "RADWIMPS", "play": 10000}]}]}}).encode("utf-8")
    b = bili_parse(bili)
    assert len(b) == 1 and b[0]["id"] == "BV1vw411p7ef" and abs((b[0]["duration"] or 0) - 307.0) < 0.01, \
        f"bilibili bytes 解析失败: {b!r}"

    # gdstudio：bytes 载荷（三源字段归一）
    gd = _json.dumps([{"id": "28483032", "name": "セプテンバーさん",
                       "artist": ["RADWIMPS"], "duration": 307173}]).encode("utf-8")
    g = parse_gd_search(gd, "netease")
    assert len(g) == 1 and g[0]["id"] == "28483032", f"gd bytes 解析失败: {g!r}"

    # str 载荷路径不受影响
    c2 = ne_parse(_json.dumps({"result": {"songs": [{"id": 1, "name": "x", "artists": [], "duration": 1000}]}}))
    assert len(c2) == 1, "str 载荷路径回归"


# ---------- x. SOURCE_ORDER 策略（FLAC 优先，用户裁定） ----------


@check("x. SOURCE_ORDER：musicdl 先于视频站（yt-dlp 渠道无 FLAC）")
def check_x_source_order():
    from flac_hunter.pipeline import SOURCE_ORDER

    assert SOURCE_ORDER[0] == "gdstudio" and SOURCE_ORDER[1] == "netease", SOURCE_ORDER
    assert SOURCE_ORDER.index("musicdl") < SOURCE_ORDER.index("bili"), SOURCE_ORDER
    assert SOURCE_ORDER.index("musicdl") < SOURCE_ORDER.index("youtube"), SOURCE_ORDER


# ---------- y. 多平台歌单入口（bytes 合成载荷 + 文本清单解析） ----------


@check("y. 多平台歌单入口（netease/bili bytes 载荷 + --list 文本解析）")
def check_y_playlist_ingest():
    import json as _json

    import cli as _cli
    from flac_hunter.sources import musicdl_ext
    from flac_hunter.sources.bilibili import parse_fav_payload
    from flac_hunter.sources.netease import parse_playlist_payload

    # 网易云歌单：bytes 载荷
    ne = _json.dumps({"result": {"tracks": [
        {"id": 28483032, "name": "セプテンバーさん", "artists": [{"name": "RADWIMPS"}],
         "duration": 307200, "album": {"name": "RADWIMPS 3", "picUrl": "http://p/1.jpg"}}]}}).encode("utf-8")
    t = parse_playlist_payload(ne)
    assert len(t) == 1 and t[0]["name"] == "セプテンバーさん" and t[0]["duration_ms"] == 307200 \
        and t[0]["album"] == "RADWIMPS 3" and t[0]["image_url"] == "http://p/1.jpg", t

    # B站收藏夹：bytes 载荷（【】块剥离 + "歌名 - UP主" 拆分）
    fav = _json.dumps({"code": 0, "data": {"has_more": True, "medias": [
        {"bvid": "BV1x", "title": "【4K】セプテンバーさん - RADWIMPS", "duration": 307,
         "upper": {"name": "someone"}, "cover": "http://i/1.jpg"}]}}).encode("utf-8")
    t2, more = parse_fav_payload(fav)
    assert more is True and len(t2) == 1, t2
    assert t2[0]["name"] == "セプテンバーさん" and t2[0]["artists"] == ["RADWIMPS"], t2
    assert t2[0]["duration_ms"] == 307000 and t2[0]["uri"] == "bili:video:BV1x", t2

    # 文本清单：'歌名 - 歌手 | 秒' / " _ " 与 / ，多歌手 / 无分隔行
    r1 = _cli._list_track_map("快晴 - Orangestar | 263.5", 1)
    assert r1["name"] == "快晴" and r1["artists"] == ["Orangestar"] and r1["duration_ms"] == 263500, r1
    r2 = _cli._list_track_map("Song - A _ B/C", 2)
    assert r2["name"] == "Song" and r2["artists"] == ["A", "B", "C"], r2
    r3 = _cli._list_track_map("只名无歌手", 3)
    assert r3["name"] == "只名无歌手" and r3["artists"] == [] and r3["duration_ms"] is None, r3

    # musicdl 歌单入口存在；musicdl 缺席场景由 o 项降级检查覆盖
    assert hasattr(musicdl_ext, "parse_playlist"), "musicdl_ext.parse_playlist 缺失"

    # musicdl 歌单超时兜底：parseplaylist 挂死时按截止时间返回 []（守护线程，实测踩坑）
    class _HangClient:
        def __init__(self, *a, **k):
            pass

        def parseplaylist(self, url, **k):
            time.sleep(5)
            return []

    orig_available, orig_client = musicdl_ext.AVAILABLE, musicdl_ext.MusicClient
    try:
        musicdl_ext.AVAILABLE = True
        musicdl_ext.MusicClient = _HangClient
        t0 = time.time()
        out = musicdl_ext.parse_playlist("http://example.com/pl", timeout=1.0)
        dt = time.time() - t0
        assert out == [] and dt < 3.0, f"超时兜底失效: dt={dt:.1f}s out={out!r}"
    finally:
        musicdl_ext.AVAILABLE, musicdl_ext.MusicClient = orig_available, orig_client


# ---------- 主流程 ----------


def main():
    t0 = time.time()
    failed = []
    for name, fn in CHECKS:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed.append((name, e))
            print(f"FAIL  {name}: {e}")
        except Exception as e:
            failed.append((name, e))
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    dt = time.time() - t0
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} 项通过，耗时 {dt:.1f}s")
    if failed:
        for name, e in failed:
            print(f"  FAILED: {name}: {e!r}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
