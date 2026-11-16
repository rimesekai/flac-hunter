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


@check("f.alt_titles_for 别名命中 + config.load_config 临时 TOML")
def t_alt_titles():
    from flac_hunter.config import load_config
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

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_cfg_"))
    try:
        toml_path = tmp / "config.toml"
        toml_path.write_text(
            '[paths]\nmusic = "my_music"\nstaging = "my_staging"\n\n'
            '[rate]\ngd_min_interval = 1.25\nper_track_sleep = 0.2\n\n'
            '[match]\nsearch_win = 10.0\nverify_win = 18.0\nmin_video_score = 60.0\n\n'
            '[aliases]\nvirtual_singers = ["TestVocal"]\n'
            'manual_picks = ["BV1test12345"]\n'
            'no_picks = ["BV1bad123456"]\n'
            'permanent_skip = ["SkipMe"]\n'
            'art_aliases = { "ArtistA" = ["AliasA", "A2"] }\n'
            'alt_titles = [{ title = "Good Weather", artist = "Orangestar", alts = ["快晴"] }]\n',
            encoding="utf-8",
        )
        cfg = load_config(toml_path)
        assert cfg.paths.music == "my_music", cfg.paths
        assert cfg.rate.gd_min_interval == 1.25, cfg.rate
        assert cfg.match.search_win == 10.0 and cfg.match.verify_win == 18.0, cfg.match
        assert cfg.aliases.art_aliases == {"ArtistA": ["AliasA", "A2"]}, cfg.aliases.art_aliases
        assert len(cfg.aliases.alt_titles) == 1 and cfg.aliases.alt_titles[0]["alts"] == ["快晴"], cfg.aliases.alt_titles
        assert cfg.aliases.manual_picks == ["BV1test12345"], cfg.aliases.manual_picks
        assert cfg.aliases.no_picks == ["BV1bad123456"], cfg.aliases.no_picks
        assert cfg.aliases.permanent_skip == ["SkipMe"], cfg.aliases.permanent_skip

        bad_path = tmp / "broken.toml"
        bad_path.write_text("not valid = [toml", encoding="utf-8")
        cfg_bad = load_config(bad_path)
        assert cfg_bad.paths.music == "music" and cfg_bad.match.verify_win == 15.0
        cfg_missing = load_config(tmp / "nonexistent.toml")
        assert cfg_missing.rate.gd_min_interval == 1.05
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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


@check("u.build_durations_cache 条目时长 ≈5.0（临时目录隔离）")
def t_durations_cache():
    from flac_hunter import library as _lib
    from flac_hunter.library import build_durations_cache

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_dur_"))
    orig_tasks_dir = _lib.TASKS_DIR
    try:
        _lib.TASKS_DIR = tmp / "tasks"
        _make_sine_flac(tmp / "Cache - Item.flac", 5)
        cache_file = tmp / "local_durations.json"
        res = _call_adapted(
            build_durations_cache,
            music_dir=str(tmp),
            music=str(tmp),
            path=str(tmp),
            cfg={"tasks_dir": str(tmp)},
            cache_path=str(cache_file),
        )
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
        assert cache_file.exists(), "未写入临时目录 local_durations.json"
    finally:
        _lib.TASKS_DIR = orig_tasks_dir
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

    # 收藏夹 v2 解析：《》引号段提取 + 翻唱标记保留 + covered by/from 歌手
    fav2 = _json.dumps({"code": 0, "data": {"medias": [
        {"bvid": "BV2y", "title": "日文翻唱《トーキョーナイトダイブ/Tokyo Night Dive》 - KOTORI",
         "duration": 227, "upper": {"name": "up_主"}}]}}).encode("utf-8")
    t3, _ = parse_fav_payload(fav2)
    assert t3[0]["name"] == "トーキョーナイトダイブ/Tokyo Night Dive（翻唱）", t3
    assert t3[0]["artists"] == ["KOTORI"], t3
    fav3 = _json.dumps({"code": 0, "data": {"medias": [
        {"bvid": "BV3z", "title": "「共鳴」from V.W.P 4th ONE-MAN LIVE「現象Ⅳ -反転」",
         "duration": 358}]}}).encode("utf-8")
    t4, _ = parse_fav_payload(fav3)
    assert t4[0]["name"] == "共鳴" and t4[0]["artists"] == ["V.W.P"], t4
    fav4 = _json.dumps({"code": 0, "data": {"medias": [
        {"bvid": "BV4a", "title": "アンインストール covered by ヰ世界情緒",
         "duration": 281}]}}).encode("utf-8")
    t5, _ = parse_fav_payload(fav4)
    assert t5[0]["name"] == "アンインストール（翻唱）" and t5[0]["artists"] == ["ヰ世界情緒"], t5

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


# ---------- z1-z7. 修复验证与端到端离线回归 ----------


@check("z1.LibraryIndex.scan + dedupe_track 三层查重 + Config 别名生效 [依赖 library-audit]")
def check_z1_library_index_dedupe():
    from flac_hunter import library as _lib
    from flac_hunter.config import Aliases, Config, Paths
    from flac_hunter.library import LibraryIndex

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_z1_"))
    orig_tasks_dir = _lib.TASKS_DIR
    try:
        _lib.TASKS_DIR = tmp / "tasks"
        music = tmp / "music"
        music.mkdir()
        _make_sine_flac(music / "SongA - Alpha.flac", 5)
        _make_sine_flac(music / "SongB - Other (cover).flac", 5)
        _make_sine_flac(music / "SongC - AliasOne.flac", 5)
        _make_sine_flac(music / "SongD - 花譜.flac", 5)

        cfg = Config(
            paths=Paths(music=str(music), staging=str(tmp / "staging")),
            aliases=Aliases(art_aliases={"AliasOne": ["AliasTwo"]}),
        )
        idx = LibraryIndex(music, cfg)
        assert idx.by_file == {}, "LibraryIndex.__init__ 不应隐式扫描目录"
        idx.scan()
        assert "SongA - Alpha.flac" in idx.by_file, idx.by_file
        assert idx.by_file["SongA - Alpha.flac"]["path"] == str(music / "SongA - Alpha.flac")

        # ① 艺人层直接命中
        entry, reason = idx.dedupe_track({"name": "SongA", "artists": ["Alpha"], "duration_ms": 5000})
        assert reason == "artist" and entry and entry["path"] == str(music / "SongA - Alpha.flac"), (entry, reason)

        # ① Config.aliases.art_aliases 别名命中（依赖 library-audit 对 Config dataclass 适配）
        entry_cfg, reason_cfg = idx.dedupe_track({"name": "SongC", "artists": ["AliasTwo"], "duration_ms": 99000})
        assert reason_cfg == "artist" and entry_cfg and entry_cfg["file"] == "SongC - AliasOne.flac", (entry_cfg, reason_cfg)

        # ① 内置 14 组 ARTIST_ALIAS_GROUPS 命中（依赖 library-audit 合并内置别名组）
        entry_bi, reason_bi = idx.dedupe_track({"name": "SongD", "artists": ["KAF"], "duration_ms": 99000})
        assert reason_bi == "artist" and entry_bi and entry_bi["file"] == "SongD - 花譜.flac", (entry_bi, reason_bi)

        # ② 标题+时长层命中
        entry_d, reason_d = idx.dedupe_track({"name": "SongA", "artists": ["SomeoneElse"], "duration_ms": 5000})
        assert reason_d == "duration" and entry_d and entry_d["file"] == "SongA - Alpha.flac", (entry_d, reason_d)

        # ③ cover 类文件不按时长判重，落入 same_title_other
        entry_c, reason_c = idx.dedupe_track({"name": "SongB", "artists": ["SomeoneElse"], "duration_ms": 5000})
        assert reason_c == "same_title_other" and entry_c is None, (entry_c, reason_c)

        # 新曲目
        entry_n, reason_n = idx.dedupe_track({"name": "BrandNewSong", "artists": ["Nobody"], "duration_ms": 5000})
        assert reason_n == "new" and entry_n is None, (entry_n, reason_n)
    finally:
        _lib.TASKS_DIR = orig_tasks_dir
        shutil.rmtree(tmp, ignore_errors=True)


@check("z2.cli._audit_concl 四项门严检 + cmd_audit 透传 dur_tol + cmd_dedupe 格式化")
def check_z2_cli_audit_dedupe():
    import argparse
    import cli as _cli
    from flac_hunter import audit as _audit
    from flac_hunter import config as _cfg
    from flac_hunter import library as _lib
    from flac_hunter.config import Config, MatchCfg, Paths

    # 四项门任意一项为假或 issues 非空都必须 FAIL
    assert _cli._audit_concl({"dur_ok": True, "tags_ok": True, "jpg_ok": True, "flac_ok": True, "issues": []}) == "PASS"
    for bad_key in ("dur_ok", "tags_ok", "jpg_ok", "flac_ok"):
        r = {"dur_ok": True, "tags_ok": True, "jpg_ok": True, "flac_ok": True, "issues": []}
        r[bad_key] = False
        concl = _cli._audit_concl(r)
        assert "FAIL" in concl.upper(), f"{bad_key}=False 未判 FAIL: {concl}"
    concl_iss = _cli._audit_concl({"dur_ok": True, "tags_ok": True, "jpg_ok": True, "flac_ok": True, "issues": ["缺标签"]})
    assert "FAIL" in concl_iss.upper(), f"issues 非空未判 FAIL: {concl_iss}"

    # real audit_one 缺封面必须 FAIL
    tmp = Path(tempfile.mkdtemp(prefix="fhchk_z2_"))
    orig_load_config = _cfg.load_config
    orig_audit_one = _audit.audit_one
    orig_find_dups = _lib.find_dups
    orig_check_lyrics = _audit.check_lyrics_dir
    try:
        music = tmp / "music"
        music.mkdir()
        f_nocover = music / "NoCover - Tester.flac"
        _make_sine_flac(f_nocover, 5)
        r_real = _call_adapted(_audit.audit_one, path=str(f_nocover), duration_ms=5000)
        assert "FAIL" in _cli._audit_concl(r_real).upper(), f"缺封面+缺标签真实文件未判 FAIL: {r_real}"

        # cmd_audit：若 audit_one 支持 dur_tol，透传 cfg.match.verify_win
        seen_kwargs = []

        def fake_audit_one(path, duration_ms=None, *, dur_tol=15.0):
            seen_kwargs.append({"path": path, "dur_tol": dur_tol})
            return {"dur_ok": True, "tags_ok": True, "jpg_ok": True, "flac_ok": True, "issues": []}

        cfg_obj = Config(
            paths=Paths(music=str(music), staging=str(tmp / "staging")),
            match=MatchCfg(verify_win=23.5),
        )
        _cfg.load_config = lambda path=None: cfg_obj
        _audit.audit_one = fake_audit_one
        _cli.cmd_audit(argparse.Namespace())
        assert len(seen_kwargs) == 1 and seen_kwargs[0]["dur_tol"] == 23.5, seen_kwargs

        # cmd_dedupe / cmd_lyrics_check：透传 cfg 给 find_dups / check_lyrics_dir
        seen_dedupe_cfg = []
        seen_lrc_cfg = []
        _lib.find_dups = lambda m, cfg=None, **k: (seen_dedupe_cfg.append(cfg), [])[1]
        _audit.check_lyrics_dir = lambda m, cfg=None: (seen_lrc_cfg.append(cfg), {})[1]
        _cli.cmd_dedupe(argparse.Namespace())
        _cli.cmd_lyrics_check(argparse.Namespace())
        assert seen_dedupe_cfg == [cfg_obj], seen_dedupe_cfg
        assert seen_lrc_cfg == [cfg_obj], seen_lrc_cfg

        # cmd_dedupe：members dict 格式化为可读文本，不直接 str(dict)
        groups = list(_cli._iter_groups([
            {"title_key": "song", "artist_key": "tester",
             "members": [{"file": "Song - Tester.flac", "duration": 12.34, "bit_rate": 850000}]}
        ]))
        line = groups[0][0]
        assert "Song - Tester.flac" in line and "{" not in line and "12.3s" in line and "850kbps" in line, line
    finally:
        _cfg.load_config = orig_load_config
        _audit.audit_one = orig_audit_one
        _lib.find_dups = orig_find_dups
        _audit.check_lyrics_dir = orig_check_lyrics
        shutil.rmtree(tmp, ignore_errors=True)


@check("z3.cli.prepare 显式 scan + existing_file 全路径 + 无歌手无尾部横杠 + spotify type")
def check_z3_cli_prepare():
    import argparse
    import cli as _cli
    from flac_hunter import config as _cfg
    from flac_hunter import library as _lib
    from flac_hunter import spotify_cli as _sp
    from flac_hunter.config import Config, Paths

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_z3_"))
    orig_load_config = _cfg.load_config
    orig_tasks_dir = _lib.TASKS_DIR
    orig_sp_cls = _sp.SpotifyCli
    try:
        _lib.TASKS_DIR = tmp / "tasks"
        music = tmp / "music"
        music.mkdir()
        existing_path = music / "SongA - Alpha.flac"
        _make_sine_flac(existing_path, 5)
        _cfg.load_config = lambda path=None: Config(
            paths=Paths(music=str(music), staging=str(tmp / "staging")),
        )

        # --list 入口：空歌手不拼尾部 " - " + scan 查重命中 existing_file 为全路径
        list_file = tmp / "list.txt"
        list_file.write_text("SoloNoArtist\nSongA - Alpha | 5\n", encoding="utf-8")
        out_list = tmp / "tracks_list.json"
        _cli.cmd_prepare(argparse.Namespace(uri=None, list_file=str(list_file), out=str(out_list)))
        recs = json.loads(out_list.read_text(encoding="utf-8"))
        assert len(recs) == 2, recs
        assert recs[0]["filename_stem"] == "SoloNoArtist", f"空歌手不应带尾部横杠: {recs[0]['filename_stem']!r}"
        assert recs[1]["existing"] is True and recs[1]["dedupe_reason"] == "artist", recs[1]
        assert recs[1]["existing_file"] == str(existing_path), f"existing_file 应为完整路径: {recs[1]!r}"

        # spotify: 入口：type 必须为 "spotify"，空歌手无尾部横杠
        class _FakeSpotifyCli:
            def __init__(self, *a, **k):
                pass

            def playlist_get(self, uri):
                return {
                    "name": "TestPL",
                    "track_count": 2,
                    "tracks": [
                        {"uri": "spotify:track:1", "name": "NoArtistTrack", "artists": [], "album": {"name": "Alb1"}},
                        {"uri": "spotify:track:2", "name": "SongA", "artists": [{"name": "Alpha"}], "album": {"name": "Alb2"}},
                    ],
                }

            def lookup_durations(self, uris):
                return {"spotify:track:1": {"duration_ms": 180000, "image_url": "http://img/1.jpg"}}

        _sp.SpotifyCli = _FakeSpotifyCli
        out_sp = tmp / "tracks_sp.json"
        _cli.cmd_prepare(argparse.Namespace(uri="spotify:playlist:123", list_file=None, out=str(out_sp)))
        recs_sp = json.loads(out_sp.read_text(encoding="utf-8"))
        assert len(recs_sp) == 2, recs_sp
        assert all(r["type"] == "spotify" for r in recs_sp), recs_sp
        assert recs_sp[0]["filename_stem"] == "NoArtistTrack", recs_sp[0]
        assert recs_sp[0]["duration_ms"] == 180000, recs_sp[0]
        assert recs_sp[1]["existing"] is True and recs_sp[1]["existing_file"] == str(existing_path), recs_sp[1]
    finally:
        _cfg.load_config = orig_load_config
        _lib.TASKS_DIR = orig_tasks_dir
        _sp.SpotifyCli = orig_sp_cls
        shutil.rmtree(tmp, ignore_errors=True)


@check("z4.find_dups 同键异时长不丢文件 + 损坏非空文件不崩溃 [依赖 library-audit]")
def check_z4_find_dups_edge():
    from flac_hunter import library as _lib
    from flac_hunter.library import find_dups

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_z4_"))
    orig_probe_meta = _lib.probe_meta
    try:
        # 四文件同一 (norm_title_dups="same", artist_key="singer")，两对不同时长(3s vs 10s)
        _make_sine_flac(tmp / "Same - Singer.flac", 3)
        _make_sine_flac(tmp / "Same (feat. A) - Singer.flac", 3)
        _make_sine_flac(tmp / "Same (feat. B) - Singer.flac", 10)
        _make_sine_flac(tmp / "Same (feat. C) - Singer.flac", 10)
        # 损坏非空文件（且模拟 probe_meta 抛错）不应导致 find_dups 崩溃
        (tmp / "Corrupt - Singer.flac").write_bytes(b"NOT_A_VALID_FLAC_STREAM" * 64)

        def _probe_with_corrupt(path, *a, **k):
            if "Corrupt" in str(path):
                raise RuntimeError("corrupt audio stream")
            return orig_probe_meta(path, *a, **k)

        _lib.probe_meta = _probe_with_corrupt
        res = _call_adapted(find_dups, music_dir=str(tmp), music=str(tmp), path=str(tmp), print_fn=None)
        groups = [g for g in _uni_list(res) if len(g) > 1]
        has_3s = any(any("Same - Singer.flac" in m for m in g) and any("feat. A" in m for m in g) for g in groups)
        has_10s = any(any("feat. B" in m for m in g) and any("feat. C" in m for m in g) for g in groups)
        assert has_3s and has_10s, f"同键异时长聚类丢失组: {groups!r}"
    finally:
        _lib.probe_meta = orig_probe_meta
        shutil.rmtree(tmp, ignore_errors=True)


def _make_large_jpg(path):
    """生成 >5KB 的有效测试封面 JPG（供 _fetch_cover 大小门限与 remux 内嵌）。"""
    _run_ff([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=s=640x640:rate=1",
        "-frames:v", "1", str(path),
    ])


def _make_noise_flac(path, seconds=22.0):
    """生成 >20s 且体积 >100KB 的有效测试 FLAC。"""
    _run_ff([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"anoisesrc=duration={seconds}",
        "-c:a", "flac", str(path),
    ])


def _make_mp3_320(path, seconds=22.0):
    """生成 >20s 的 320kbps 测试 MP3。"""
    _run_ff([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
        "-c:a", "libmp3lame", "-b:a", "320k", str(path),
    ])


def _make_ogg_128(path, seconds=22.0):
    """生成 >20s 的 ~128kbps 测试 OGG。"""
    _run_ff([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"anoisesrc=duration={seconds}",
        "-c:a", "libvorbis", "-b:a", "128k", str(path),
    ])


@check("z5.run_download 离线端到端（假源+tasks_dir+sidecars+封面清理+落位顺序） [依赖 pipeline-upgrade]")
def check_z5_run_download_e2e():
    from flac_hunter import pipeline as _pl
    from flac_hunter import util as _util
    from flac_hunter.config import Config, Paths, Rate
    from flac_hunter.sources.base import make_candidate

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_z5_"))
    orig_tasks_dir = _pl._TASKS_DIR
    orig_http_get = _util.http_get
    orig_place_file = _pl._place_file
    try:
        music = tmp / "music"
        staging = tmp / "staging"
        tasks = tmp / "tasks"
        assets = tmp / "assets"
        music.mkdir()
        staging.mkdir()
        assets.mkdir()

        src_flac = assets / "sample22.flac"
        cover_jpg = assets / "cover.jpg"
        _make_noise_flac(src_flac, 22.0)
        _make_large_jpg(cover_jpg)
        jpg_bytes = cover_jpg.read_bytes()
        assert len(jpg_bytes) > 5000, len(jpg_bytes)

        _util.http_get = lambda url, *a, **k: jpg_bytes

        class _FakeSrc:
            name = "musicdl"
            lossless = True

            def search(self, track):
                return [make_candidate(
                    source="musicdl", id="fake1", title=track["name"],
                    artists=track["artists"], duration=22.0, ext=".flac",
                    url="", extra={"quality": "flac"},
                )]

            def fetch(self, cand, dest_dir):
                dst = Path(dest_dir) / f"{cand['id']}.flac"
                shutil.copyfile(src_flac, dst)
                return str(dst)

        cfg = Config(
            paths=Paths(music=str(music), staging=str(staging)),
            rate=Rate(per_track_sleep=0.01),
        )
        dl_params = inspect.signature(_pl.run_download).parameters
        assert "tasks_dir" in dl_params, "run_download 缺少 tasks_dir 可选参数"

        track1 = {
            "type": "spotify",
            "uri": "spotify:track:cov1",
            "name": "TrackOne",
            "artists": ["Tester"],
            "album": "Alb",
            "duration_ms": 22000,
            "image_url": "https://i.scdn.co/image/ab67616d00001e0212345678",
        }
        res = _pl.run_download(
            [track1], cfg, sources=[_FakeSrc()], sidecars=True,
            lyrics_fetcher=lambda *a: "[00:01.00]hello offline\n",
            tasks_dir=tasks,
        )
        assert len(res) == 1 and res[0]["status"] == "downloaded", res
        assert (music / "TrackOne - Tester.flac").exists()
        assert (music / "TrackOne - Tester.jpg").exists()
        assert (music / "TrackOne - Tester.lrc").exists()
        assert (tasks / "results.jsonl").exists()
        assert not list(staging.glob("*.jpg")), f"staging 临时封面未清理: {list(staging.glob('*.jpg'))}"

        # 落位失败时：不得留孤儿侧车(.jpg/.lrc)，且 staging 封面仍须清理
        def _boom_place(*a, **k):
            raise RuntimeError("simulated place failure")

        _pl._place_file = _boom_place
        track2 = {
            "type": "spotify",
            "uri": "spotify:track:cov2",
            "name": "TrackTwo",
            "artists": ["Tester"],
            "album": "Alb",
            "duration_ms": 22000,
            "image_url": "https://i.scdn.co/image/ab67616d00001e02abcdef00",
        }
        res2 = _pl.run_download(
            [track2], cfg, sources=[_FakeSrc()], sidecars=True,
            lyrics_fetcher=lambda *a: "[00:01.00]orphan check\n",
            tasks_dir=tasks,
        )
        assert len(res2) == 1 and res2[0]["status"] == "failed", res2
        assert not (music / "TrackTwo - Tester.jpg").exists(), "落位失败不应留下孤儿 .jpg"
        assert not (music / "TrackTwo - Tester.lrc").exists(), "落位失败不应留下孤儿 .lrc"
        assert not list(staging.glob("*.jpg")), f"落位失败后 staging 封面未清理: {list(staging.glob('*.jpg'))}"
    finally:
        _pl._TASKS_DIR = orig_tasks_dir
        _util.http_get = orig_http_get
        _pl._place_file = orig_place_file
        shutil.rmtree(tmp, ignore_errors=True)


@check("z6.run_upgrade 离线测试（bps->kbps better 判定 + 无时长终验不误删） [依赖 pipeline-upgrade]")
def check_z6_run_upgrade_offline():
    from flac_hunter import upgrade as _upg
    from flac_hunter import util as _util
    from flac_hunter.config import Config, Paths, Rate

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_z6_"))
    orig_match_fails = _upg.MATCH_FAILS
    orig_search = _upg._netease_search
    orig_url = _upg._gd_url_for
    orig_dl_stream = _util.download_stream
    orig_probe_meta = _upg._probe_meta
    try:
        music = tmp / "music"
        staging = tmp / "staging"
        assets = tmp / "assets"
        music.mkdir()
        staging.mkdir()
        assets.mkdir()

        ogg_file = music / "SongOgg - Artist.ogg"
        mp3_320 = assets / "high320.mp3"
        flac_22 = assets / "lossless22.flac"
        _make_ogg_128(ogg_file, 22.0)
        _make_mp3_320(mp3_320, 22.0)
        _make_noise_flac(flac_22, 22.0)

        # 1) _probe_meta 返回码率必须已是 kbps（< 1000），而非 bps（~128000）
        dur0, in_br0, _, _ = _upg._probe_meta(str(ogg_file))
        assert dur0 > 20.0 and 0 < in_br0 < 1000, f"_probe_meta 码率单位未转 kbps: dur={dur0}, br={in_br0}"
        assert _upg.better(False, 320, in_br0) is True, f"better(False, 320, {in_br0}) 应为 True"

        cfg = Config(
            paths=Paths(music=str(music), staging=str(staging)),
            rate=Rate(netease_min_interval=0.0, per_track_sleep=0.0),
        )
        mf_path = tmp / "match_fails.json"

        def fake_search(*a, **k):
            return [{"id": "101", "name": "SongOgg", "dur": 22.0, "artists": "Artist"}]

        def fake_url_mp3(*a, **k):
            return "http://offline.local/high320.mp3", 320

        def fake_dl_mp3(url, dst, *a, **k):
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(mp3_320, dst)
            return Path(dst).stat().st_size

        _util.download_stream = fake_dl_mp3
        upg_params = inspect.signature(_upg.run_upgrade).parameters
        kw_ogg = {"ext": "ogg", "full_retry": True}
        if "match_fails_path" in upg_params:
            kw_ogg["match_fails_path"] = mf_path
        else:
            _upg.MATCH_FAILS = mf_path
        if "search_fn" in upg_params:
            kw_ogg["search_fn"] = fake_search
        else:
            _upg._netease_search = fake_search
        if "url_fn" in upg_params:
            kw_ogg["url_fn"] = fake_url_mp3
        else:
            _upg._gd_url_for = fake_url_mp3

        res_ogg = _upg.run_upgrade(cfg, **kw_ogg)
        rec_ogg = [r for r in res_ogg if r.get("file") == "SongOgg - Artist.ogg"]
        assert rec_ogg and rec_ogg[0]["status"] == "upgraded", res_ogg
        assert (music / "SongOgg - Artist.mp3").exists() and not ogg_file.exists()

        # 2) 无时长旧文件（sdur == 0.0）升级 FLAC 终验不得误判 final_duration_mismatch
        music2 = tmp / "music2"
        music2.mkdir()
        mp3_old = music2 / "NoDur - Artist.mp3"
        _make_mp3_320(mp3_old, 22.0)

        _upg._probe_meta = lambda *a, **k: (0.0, 128, "NoDur", "Artist")
        _util.download_stream = lambda url, dst, *a, **k: (
            Path(dst).parent.mkdir(parents=True, exist_ok=True),
            shutil.copyfile(flac_22, dst),
            Path(dst).stat().st_size,
        )[-1]

        def fake_search2(*a, **k):
            return [{"id": "202", "name": "NoDur", "dur": 22.0, "artists": "Artist"}]

        def fake_url_flac(*a, **k):
            return "http://offline.local/lossless.flac", 999999

        cfg2 = Config(
            paths=Paths(music=str(music2), staging=str(staging)),
            rate=Rate(netease_min_interval=0.0, per_track_sleep=0.0),
        )
        kw_mp3 = {"ext": "mp3", "full_retry": True}
        if "match_fails_path" in upg_params:
            kw_mp3["match_fails_path"] = mf_path
        if "search_fn" in upg_params:
            kw_mp3["search_fn"] = fake_search2
        else:
            _upg._netease_search = fake_search2
        if "url_fn" in upg_params:
            kw_mp3["url_fn"] = fake_url_flac
        else:
            _upg._gd_url_for = fake_url_flac

        res_mp3 = _upg.run_upgrade(cfg2, **kw_mp3)
        rec_mp3 = [r for r in res_mp3 if r.get("file") == "NoDur - Artist.mp3"]
        assert rec_mp3 and rec_mp3[0]["status"] == "upgraded", f"sdur==0.0 终验异常: {res_mp3}"
        assert (music2 / "NoDur - Artist.flac").exists() and not mp3_old.exists()
    finally:
        _upg.MATCH_FAILS = orig_match_fails
        _upg._netease_search = orig_search
        _upg._gd_url_for = orig_url
        _util.download_stream = orig_dl_stream
        _upg._probe_meta = orig_probe_meta
        shutil.rmtree(tmp, ignore_errors=True)


@check("z7.tier_of 无时长sdur=None返A + score_bili Alive不误杀 + GdStudioSource限速 [依赖 matcher-sources]")
def check_z7_matcher_sources_fixes():
    from flac_hunter.config import Config, Rate
    from flac_hunter.match.score import score_bili
    from flac_hunter.match.tier import tier_of
    from flac_hunter.sources import gdstudio as _gd

    # 1) tier_of: sdur=None / 0 不再把 sdur 当 0.0 与 cand_dur 比较
    cand_a = {
        "source": "gdstudio", "id": "1", "title": "Song",
        "artists": ["Artist"], "duration": 203.0, "ext": None, "url": "", "extra": {},
    }
    assert tier_of(cand_a, None, "Song", ["artist"], ["song"]) == "A", tier_of(cand_a, None, "Song", ["artist"], ["song"])
    assert tier_of(cand_a, 0, "Song", ["artist"], ["song"]) == "A"
    cand_b = dict(cand_a, artists=["Other"])
    assert tier_of(cand_b, None, "Song", ["artist"], ["song"]) == "B"

    # 2) score_bili: "Alive"/"Discover"/"Table" 不触发 BILI_BAD 词边界误杀；真 "live" 仍 -999
    track = {"name": "Song", "artists": ["Orangestar"], "album": "", "duration_ms": 200000}
    for good_title in ("Song (Alive ver)", "Song (Discover)", "Song on Table"):
        c_good = {
            "source": "bili", "id": "BV1good", "title": good_title,
            "artists": ["Orangestar"], "duration": 200, "ext": None, "url": "",
            "extra": {"channel": "Orangestar", "play": 10000},
            "channel": "Orangestar", "play": 10000,
        }
        sc = score_bili(track, c_good, [], set())
        assert sc > 0, f"{good_title!r} 被误杀: score={sc}"
    c_live = {
        "source": "bili", "id": "BV1live", "title": "Song (live)",
        "artists": ["Orangestar"], "duration": 200, "ext": None, "url": "",
        "extra": {"channel": "Orangestar", "play": 10000},
        "channel": "Orangestar", "play": 10000,
    }
    assert score_bili(track, c_live, [], set()) == -999

    # 3) GdStudioSource._get(http_fn=None) 必须调用 gd_throttle 遵守 >=1.05s 限速
    orig_http_get = _gd.http_get
    orig_throttle = _gd.gd_throttle
    orig_sleep = _gd.time.sleep
    orig_last_hit = _gd._gd_last_hit[0]
    try:
        throttle_calls = []
        sleeps = []

        def fake_http_get(url, *a, **k):
            if "types=url" in url:
                return '{"url":"http://offline.local/1.flac","size":12345}'
            return "[]"

        def spy_throttle(*a, **k):
            throttle_calls.append((a, k))
            return orig_throttle(*a, **k)

        _gd.http_get = fake_http_get
        _gd.gd_throttle = spy_throttle
        _gd.time.sleep = lambda sec: sleeps.append(sec)
        _gd._gd_last_hit[0] = time.time()

        src = _gd.GdStudioSource(Config(rate=Rate(gd_min_interval=1.05)), http_fn=None)
        src.search({"name": "Song", "artists": ["Artist"]})
        src.get_url("netease", "123")
        assert len(throttle_calls) >= 4, f"GdStudioSource 未触发 gd_throttle: calls={len(throttle_calls)}"
        assert any(s >= 1.0 for s in sleeps), f"GdStudioSource 限速休眠未生效: sleeps={sleeps}"
    finally:
        _gd.http_get = orig_http_get
        _gd.gd_throttle = orig_throttle
        _gd.time.sleep = orig_sleep
        _gd._gd_last_hit[0] = orig_last_hit


# ---------- z8. 曲名侧 cover 词边界（评审发现的 L136 残留缺陷） ----------


@check("z8. score_bili 曲名含 discover 等子串不被「点赞曲是 cover」规则误杀")
def check_z8_trackname_cover_boundary():
    from flac_hunter.match.score import score_bili
    from flac_hunter.sources.base import make_candidate

    # 曲名 "Alive and Discover" 内含 cover 子串，但不是独立词——不得判为翻唱曲
    trk = {"name": "Alive and Discover", "artists": ["SomeBand"], "duration_ms": 200000, "album": ""}
    cand = make_candidate(source="bili", id="BVz8", title="Alive and Discover (Official Video)",
                          artists=["SomeBand"], duration=200.0,
                          url="https://www.bilibili.com/video/BVz8", extra={"play": 50000})
    sc = score_bili(trk, cand, alts=[], other_artists=set())
    assert sc > 55, f"曲名子串 cover 误杀: score={sc}"

    # 真翻唱标记（英文独立词 cover）仍拦截：曲名含 cover 且候选无覆盖艺人 → -999
    trk2 = {"name": "Song - Cover", "artists": ["SomeoneElse"], "duration_ms": 200000, "album": ""}
    cand2 = make_candidate(source="bili", id="BVz8b", title="Song (Different Story)",
                           artists=["Other"], duration=200.0,
                           url="https://www.bilibili.com/video/BVz8b")
    sc2 = score_bili(trk2, cand2, alts=[], other_artists=set())
    assert sc2 == -999, f"真 cover 曲名未被拦截: score={sc2}"


# ---------- z9. GUI 模块：页面资源 + 作业运行器（子进程日志/退出码） ----------


@check("z9. gui JobRunner 跑通自定义子进程作业 + PAGE_HTML 含关键 API")
def check_z9_gui():
    import gui as _gui

    # 页面资源：关键 API 与 UI 文案在场
    for marker in ("/api/state", "/api/download", "任务列表", "无损升级"):
        assert marker in _gui.PAGE_HTML, f"页面缺 {marker!r}"

    # 作业运行器：跑一个自定义子进程作业，收日志与退出码
    r = _gui.Runner(_gui.load_config())
    snap0 = r.submit("custom", [sys.executable, "-c", "print('z9gui-ok')"])
    job = r.jobs[snap0["id"]]
    deadline = time.time() + 20
    while time.time() < deadline and job.status in ("queued", "running"):
        time.sleep(0.2)
    assert job.status == "done" and job.exit_code == 0, \
        f"作业未正常完成: status={job.status} exit={job.exit_code}"
    assert any("z9gui-ok" in line for line in job.log), f"日志未捕获输出: {list(job.log)}"
    snap = job.snapshot(with_log=True)
    assert "log_tail" in snap and snap["progress"]["total"] == 0


# ---------- z10. GUI 逐曲下载模式（跳过闸门 + 桩命令 + 台账隔离） ----------


@check("z10. gui 逐曲下载：首曲跳过写台账、次曲桩命令执行、暂停即停")
def check_z10_pertrack():
    import tempfile

    import gui as _gui

    tmp = Path(tempfile.mkdtemp(prefix="fh_z10_"))
    try:
        r = _gui.Runner(_gui.load_config())
        job = _gui.Job("z10per", "download", None, tmp, total=2, tracks_path="t.json",
                       tracks_list=[{"uri": "bili:video:A", "name": "T1"},
                                    {"uri": "bili:video:B", "name": "T2"}])
        r.jobs[job.id] = job
        r.order.append(job.id)
        orig_cmd = r._download_cmd
        r._download_cmd = lambda j, k: [sys.executable, "-c", "print('z10-pertrack-ok')"]
        try:
            job.skip_requested = True   # 第一首：入队即点跳过 → 写 skipped 台账不开工
            job.paused = False
            r._run_download_pertrack(job)  # 同步直跑（worker 线程外）
        finally:
            r._download_cmd = orig_cmd
            job._stop_tail.set()

        assert job.skip_requested is False, "跳过标志未被消费"
        # 第一首被跳过 → 台账写 skipped；第二首跑了桩命令
        ledger = (tmp / "tasks" / "results.jsonl")
        assert ledger.exists(), "skipped 台账未写入"
        recs = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert any(x.get("status") == "skipped" and x.get("track", {}).get("name") == "T1"
                   for x in recs), f"skipped 记录缺失: {recs}"
        assert any("z10-pertrack-ok" in line for line in job.log), "第二首桩命令未执行"
        assert job.current is None, "处理完当前曲目后 current 未清空"
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- z11. GUI 修复回归：路径越界 / only 筛选 / audit 错误退出码 / 前端契约 ----------


@check("z11. gui 修复回归：路径越界防绕过、only 筛选、audit 失败退出码")
def check_z11_gui_fixes():
    import gui as _gui
    from flac_hunter.config import load_config
    from flac_hunter.gui_page import PAGE_HTML

    # 1) _resolve_tracks_path：同前缀兄弟目录（如 flac-hunter-evil）与非 tracks.json 必须被拒绝
    evil_sibling = str(_gui.REPO.parent / (_gui.REPO.name + "-evil") / "tracks.json")
    for bad in (evil_sibling, str(_gui.REPO / "output" / "other.json"), ""):
        try:
            _gui._resolve_tracks_path(bad)
            raise AssertionError(f"应当拒绝非法 tracks 路径: {bad!r}")
        except ValueError:
            pass

    # 2) _read_tracks：支持完整 spotify:track:xxx、尾部 id、纯文本歌单 pos:<n>，且 only=[] 返回 0 首
    tmp = Path(tempfile.mkdtemp(prefix="fh_z11_"))
    orig_repo = _gui.REPO
    try:
        _gui.REPO = tmp
        tj = tmp / "tasks" / "tracks.json"
        tj.parent.mkdir(parents=True, exist_ok=True)
        tj.write_text(json.dumps({
            "records": [
                {"position": 1, "name": "SongA", "uri": "spotify:track:AAA111", "existing": None},
                {"position": 2, "name": "SongB", "uri": "spotify:track:BBB222", "existing": "b.mp3"},
                {"position": 3, "name": "LocalOnly,Song", "uri": None, "existing": None},
            ]
        }), encoding="utf-8")

        items_empty, tot_empty = _gui._read_tracks(str(tj), True, [])
        assert items_empty == [] and tot_empty == 0, f"only=[] 应返回空: {items_empty}"

        items_uri, tot_uri = _gui._read_tracks(str(tj), True, ["spotify:track:AAA111"])
        assert [x["name"] for x in items_uri] == ["SongA"] and tot_uri == 1

        items_id, _ = _gui._read_tracks(str(tj), False, ["BBB222"])
        assert items_id == [], "include_existing=False 应跳过已有曲目"

        items_pos, _ = _gui._read_tracks(str(tj), True, ["pos:3"])
        assert [x["name"] for x in items_pos] == ["LocalOnly,Song"], f"--list pos 匹配失败: {items_pos}"

        # 3) _run_audit 在曲库目录不存在时必须保持 status=error 与 exit_code=1
        cfg = load_config()
        cfg.paths.music = tmp / "nonexistent_music_dir"
        cfg.paths.tasks = tmp / "tasks"
        cfg.paths.output = tmp / "output"
        r = _gui.Runner(cfg)
        snap = r.submit("audit", None)
        job = r.jobs[snap["id"]]
        deadline = time.time() + 5.0
        while job.status in ("queued", "running") and time.time() < deadline:
            time.sleep(0.03)
        assert job.status == "error" and job.exit_code == 1, (
            f"audit 缺目录应报错并保留 exit_code=1，实际: status={job.status}, exit_code={job.exit_code}"
        )
    finally:
        _gui.REPO = orig_repo
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    # 4) FlClash 设计系统关键标记与前端交互修复
    for marker in ("--fc-surface-card", "--fc-surface-chrome", "btn-selnew", 'existing !== "1"', "请至少勾选一首曲目再下载", 'id="dl-dir"'):
        assert marker in PAGE_HTML, f"PAGE_HTML 缺失关键设计或修复标记: {marker}"

    # 5) Runner._download_cmd 自定义下载目录参数透传
    j_dir = _gui.Job("jdir", "download", None, Path("."), tracks_path="t.json", music_dir="/tmp/my_flac")
    cmd_dir = _gui.Runner(load_config())._download_cmd(j_dir, "k1")
    assert "--music-dir" in cmd_dir and "/tmp/my_flac" in cmd_dir, f"未透传 --music-dir: {cmd_dir}"


# ---------- z12. GUI HTTP 安全加固与 API 集成测试 ----------


@check("z12. gui HTTP 本地隔离、安全头、/api/audit/last 与部分下载")
def check_z12_gui_http_security():
    import threading
    import urllib.request
    import urllib.error
    import gui as _gui
    from flac_hunter.config import load_config

    tmp = Path(tempfile.mkdtemp(prefix="fh_z12_"))
    orig_repo = _gui.REPO
    srv = None
    try:
        _gui.REPO = tmp
        (tmp / "tasks").mkdir(parents=True, exist_ok=True)
        (tmp / "output").mkdir(parents=True, exist_ok=True)
        (tmp / "music").mkdir(parents=True, exist_ok=True)
        tj = tmp / "tasks" / "tracks.json"
        tj.write_text(json.dumps({
            "records": [
                {"position": 1, "name": "T1", "uri": "spotify:track:T1ID", "existing": None},
                {"position": 2, "name": "T2", "uri": "spotify:track:T2ID", "existing": None},
            ]
        }), encoding="utf-8")

        cfg = load_config()
        cfg.paths.music = tmp / "music"
        cfg.paths.tasks = tmp / "tasks"
        cfg.paths.output = tmp / "output"
        runner = _gui.Runner(cfg)
        runner._download_cmd = lambda j, k: [sys.executable, "-c", f"print('z12-dl:{k}')"]

        class TestHandler(_gui.Handler):
            pass
        TestHandler.runner = runner
        srv = _gui._LocalServer(("127.0.0.1", 0), TestHandler)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        base = f"http://127.0.0.1:{port}"

        # 1) GET / 返回 200 与安全响应头
        with urllib.request.urlopen(base + "/") as resp:
            assert resp.status == 200
            assert resp.headers.get("X-Content-Type-Options") == "nosniff"
            assert resp.headers.get("X-Frame-Options") == "DENY"
            assert resp.headers.get("Cross-Origin-Resource-Policy") == "same-origin"

        # 2) GET /api/audit/last 无缓存时返回 200 {"audit": None}，避免控制台 404
        with urllib.request.urlopen(base + "/api/audit/last") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert resp.status == 200 and data == {"audit": None}, f"audit/last 异常: {data}"

        # 3) GET /api/state 包含 music_dir
        with urllib.request.urlopen(base + "/api/state") as resp:
            st = json.loads(resp.read().decode("utf-8"))
            assert st.get("music_dir") == str(cfg.paths.music)

        # 4) 跨站 POST（Origin 或 Sec-Fetch-Site: cross-site）必须被 403 拦截
        for bad_hdrs in (
            {"Origin": "https://evil.example", "Content-Type": "application/json"},
            {"Sec-Fetch-Site": "cross-site", "Content-Type": "application/json"},
        ):
            req = urllib.request.Request(
                base + "/api/audit", data=b"{}", headers=bad_hdrs, method="POST",
            )
            try:
                urllib.request.urlopen(req)
                raise AssertionError(f"跨站请求应当被拦截: {bad_hdrs}")
            except urllib.error.HTTPError as e:
                assert e.code == 403, f"跨站请求应返回 403，实际: {e.code}"

        # 5) 合法同源 POST /api/download（部分勾选 + 自定义下载目录）应仅执行选中曲目并记录目标目录
        custom_dir = tmp / "custom_out"
        req = urllib.request.Request(
            base + "/api/download",
            data=json.dumps({
                "tracks": str(tj),
                "only": ["spotify:track:T2ID"],
                "include_existing": True,
                "music_dir": str(custom_dir),
            }).encode("utf-8"),
            headers={"Origin": base, "Sec-Fetch-Site": "same-origin", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            snap = json.loads(resp.read().decode("utf-8"))
        assert snap["total"] == 1, f"部分选中应只下载 1 首，实际: {snap}"
        assert snap.get("music_dir") == str(custom_dir), f"music_dir 未透传: {snap}"
        job = runner.jobs[snap["id"]]
        deadline = time.time() + 8.0
        while job.status in ("queued", "running") and time.time() < deadline:
            time.sleep(0.05)
        assert job.status == "done", f"部分下载失败: {list(job.log)}"
        assert any("z12-dl:T2ID" in line for line in job.log)
        assert not any("z12-dl:T1ID" in line for line in job.log)
    finally:
        if srv is not None:
            srv.shutdown()
            srv.server_close()
        _gui.REPO = orig_repo
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


@check("z13: 下载封面/歌词开关 + 升级补封面修复回归")
def check_z13_cover_lyrics_and_upgrade_repair():
    from flac_hunter.gui_page import PAGE_HTML
    import cli as _cli
    import gui as _gui
    import flac_hunter.upgrade as _upg

    assert 'id="dl-cover"' in PAGE_HTML and 'id="dl-lyrics"' in PAGE_HTML
    assert 'id="dl-lyrics" class="fc-switch">' in PAGE_HTML
    assert "download_cover" in PAGE_HTML and "download_lyrics" in PAGE_HTML
    assert hasattr(_upg, "json") and callable(getattr(_upg, "_repair_existing_flac", None))

    parser = _cli.build_parser()
    ns = parser.parse_args(["download", "--tracks", "t.json", "--no-cover", "--no-lyrics"])
    assert ns.no_cover is True and ns.no_lyrics is True

    r = _gui.Runner(_gui.load_config())
    j = _gui.Job("j1", "download", None, Path("."), total=1, tracks_path="t.json",
                 download_cover=True, download_lyrics=False)
    cmd = r._download_cmd(j, "k1")
    assert "--no-lyrics" in cmd and "--no-cover" not in cmd
    assert 'data-tab="dedupe"' in PAGE_HTML and "/api/dedupe/delete" in PAGE_HTML


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
