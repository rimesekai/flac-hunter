"""z21. cookie 注入与空 cookie 回归（T2 私密歌单支持，[cookies] 配置段）。

覆盖（详见任务契约）：
a) config.py [cookies] 段解析（netease/qq 均接受 str，缺失/非 str 回退 ""，config.py:64-69 _str_map）；
a2) netease._cfg_cookie 三形态（None/Config/dict，蓝本 gdstudio._cfg_rate gdstudio.py:53-63）
    + NeteaseSource._cookie 注入 + http_fn 分支调用签名不动（z7 依赖）；
b) netease.fetch_playlist cookie 透传（原形 netease.py:201-208）+ util._headers 空 cookie 无 Cookie 键佐证（util.py:24-31）；
c) spotify_cli.fetch_qq_playlist cookie 透传（原形 spotify_cli.py:168-172）+ 空 cookie 无 Cookie 头；
d) cli.cmd_prepare 四个 fetch 调用点端到端接线（qq:/netease: 前缀入口，cli.py:283/290/309；
    函数内 import cli.py:225-228，patch flac_hunter.* 模块属性即可生效）；
e) 零 cookie 回归：仓库真实 config.toml（只读）解析出空 cookies。

独立运行：python tests/checks_extra/cookie.py
被 tests/run_checks.py 主流程前的加载钩子加载时，check 为注入注册器（CHECKS.append 形态，run_checks.py:35-41）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # 仓库根，便于独立运行

_LOCAL = []

try:
    check  # noqa: F821  # tests/run_checks.py 注入的注册器
except NameError:
    def check(name):
        def deco(fn):
            _LOCAL.append((name, fn))
            return fn
        return deco


@check("z21. cookie 注入与空 cookie 回归（netease/qq/cli 透传）")
def check_z21_cookie_injection():
    import argparse
    import shutil
    import tempfile

    import cli as _cli
    from flac_hunter import config as _cfg
    from flac_hunter import library as _lib
    from flac_hunter import spotify_cli as _sp
    from flac_hunter.config import Config, Cookies, Paths
    from flac_hunter.sources import netease as _nea
    from flac_hunter.util import CHROME_UA, _headers

    tmp = Path(tempfile.mkdtemp(prefix="fhchk_z21_"))
    try:
        # ---- a) config 解析：含 [cookies] 段 ----
        toml_with = tmp / "with_cookies.toml"
        toml_with.write_text('[cookies]\nnetease = "MUSIC_U=abc"\nqq = "xyz"\n', encoding="utf-8")
        cfg_parsed = _cfg.load_config(toml_with)
        assert cfg_parsed.cookies.netease == "MUSIC_U=abc", cfg_parsed.cookies
        assert cfg_parsed.cookies.qq == "xyz", cfg_parsed.cookies
        # a) 无 [cookies] 段：两字段回退 ""（零 cookie 默认）
        toml_without = tmp / "without_cookies.toml"
        toml_without.write_text('[paths]\nmusic = "m"\n', encoding="utf-8")
        cfg_plain = _cfg.load_config(toml_without)
        assert cfg_plain.cookies.netease == "" and cfg_plain.cookies.qq == "", cfg_plain.cookies

        # 带登录态的 Config（供 a2/d 复用）；paths.music=临时空目录（cmd_prepare 无真实写盘）
        music_dir = tmp / "music"
        music_dir.mkdir()
        cfg_full = Config(paths=Paths(music=str(music_dir), staging=str(tmp / "staging")),
                          cookies=Cookies(netease="NEA_FROM_CFG", qq="QQ_FROM_CFG"))

        # ---- a2) _cfg_cookie 三形态（None/Config/dict）+ NeteaseSource._cookie ----
        assert _nea._cfg_cookie(None, "netease") == "", "None 配置应回退空串"
        assert _nea._cfg_cookie({"cookies": {"netease": "DICT_COOKIE"}}, "netease") == "DICT_COOKIE"
        assert _nea._cfg_cookie({"cookies": {"qq": 5}}, "qq") == "", "非 str 值应回退空串"
        assert _nea.NeteaseSource(cfg_full)._cookie == "NEA_FROM_CFG"  # upgrade.py:146 以 Config 构造
        assert _nea.NeteaseSource({"cookies": {"netease": "DICT_COOKIE"}})._cookie == "DICT_COOKIE"
        assert _nea.NeteaseSource()._cookie == "", "无配置应回退空串（匿名行为不变）"
        # http_fn 分支调用签名一个字不动（z7 依赖）：_get 只以 (url, timeout) 两参调注入 http_fn
        seen_fn = []
        src_fn = _nea.NeteaseSource(cfg_full, http_fn=lambda u, t: (seen_fn.append((u, t)) or "ok"))
        assert src_fn._get("http://x", 20) == "ok" and seen_fn == [("http://x", 20)], seen_fn

        # ---- b) netease 注入：patch netease.http_get 捕获请求（桩返回 bytes，与真实 http_get 形态一致）----
        captured = []

        def _fake_http(url, **kw):
            captured.append({"url": url, **kw})
            return b"{}"

        orig_http_get = _nea.http_get
        _nea.http_get = _fake_http
        try:
            assert _nea.fetch_playlist(123, cookie="MUSIC_U=abc") == []  # b"{}" 解析为空歌单
            assert captured[-1]["cookie"] == "MUSIC_U=abc", captured[-1]
            _nea.fetch_playlist(123, cookie="")
            assert not captured[-1]["cookie"], f"空 cookie 应归一 falsy: {captured[-1]}"
            _nea.fetch_playlist(123)
            assert not captured[-1]["cookie"], f"缺省 cookie 应归一 falsy: {captured[-1]}"
        finally:
            _nea.http_get = orig_http_get
        # util._headers 佐证：cookie 为空时请求头无 Cookie 键（util.py:24-31），非空时原样透传
        assert "Cookie" not in _headers(CHROME_UA, _nea.NETEASE_REFERER, None)
        assert _headers(CHROME_UA, _nea.NETEASE_REFERER, "MUSIC_U=abc")["Cookie"] == "MUSIC_U=abc"

        # ---- c) qq 注入：patch spotify_cli.http_get 同法 ----
        captured_qq = []

        def _fake_qq_http(url, **kw):
            captured_qq.append({"url": url, **kw})
            return b"{}"

        orig_sp_http_get = _sp.http_get
        _sp.http_get = _fake_qq_http
        try:
            assert _sp.fetch_qq_playlist(456, cookie="tencent=1") == []
            assert captured_qq[-1]["cookie"] == "tencent=1", captured_qq[-1]
            _sp.fetch_qq_playlist(456, cookie="")
            assert not captured_qq[-1]["cookie"], f"空 cookie 应无 Cookie 头: {captured_qq[-1]}"
            assert "Cookie" not in _headers(_sp.QQ_UA, "https://y.qq.com/", None)
        finally:
            _sp.http_get = orig_sp_http_get

        # ---- d) cli 端到端接线（防「模块好了入口没接」）----
        # 桩返回 []（空曲列表 -> cmd_prepare 只扫临时空曲库 + 写临时 tracks.json，无网络无真实写盘）
        captured_d = {"qq": [], "netease": []}

        def _stub_qq(disstid, cookie=None):
            captured_d["qq"].append((disstid, cookie))
            return []

        def _stub_netease(playlist_id, timeout=20, cookie=None):
            captured_d["netease"].append((playlist_id, cookie))
            return []

        orig_load_config = _cfg.load_config
        orig_sp_fetch = _sp.fetch_qq_playlist
        orig_nea_fetch = _nea.fetch_playlist
        orig_tasks_dir = _lib.TASKS_DIR  # 防 LibraryIndex 意外触碰仓库真实 tasks/（z3 范式 run_checks.py:961-964）
        _cfg.load_config = lambda path=None: cfg_full
        _sp.fetch_qq_playlist = _stub_qq
        _nea.fetch_playlist = _stub_netease
        _lib.TASKS_DIR = tmp / "tasks"
        try:
            # qq: 前缀入口 -> fetch_qq_playlist 桩收到 cfg.cookies.qq（cli.py:283）
            ns = _cli.build_parser().parse_args(
                ["prepare", "--uri", "qq:123", "--out", str(tmp / "t_qq.json")])
            _cli.cmd_prepare(ns)
            assert captured_d["qq"][-1] == ("123", "QQ_FROM_CFG"), captured_d["qq"]
            assert (tmp / "t_qq.json").exists(), "tracks.json 未写临时输出"
            # netease: 前缀入口 -> fetch_playlist 桩收到 cfg.cookies.netease（cli.py:290）
            ns2 = _cli.build_parser().parse_args(
                ["prepare", "--uri", "netease:456", "--out", str(tmp / "t_nea.json")])
            _cli.cmd_prepare(ns2)
            assert captured_d["netease"][-1] == ("456", "NEA_FROM_CFG"), captured_d["netease"]
            # 零 cookie：默认空 cookies 的 Config -> 透传值为 falsy（回归保护）
            cfg_empty = Config(paths=Paths(music=str(music_dir), staging=str(tmp / "staging")))
            _cfg.load_config = lambda path=None: cfg_empty
            ns3 = _cli.build_parser().parse_args(
                ["prepare", "--uri", "qq:789", "--out", str(tmp / "t_qq2.json")])
            _cli.cmd_prepare(ns3)
            assert captured_d["qq"][-1] == ("789", None), captured_d["qq"][-1]
            ns4 = _cli.build_parser().parse_args(
                ["prepare", "--uri", "netease:999", "--out", str(tmp / "t_nea2.json")])
            _cli.cmd_prepare(ns4)
            assert captured_d["netease"][-1] == ("999", None), captured_d["netease"][-1]
        finally:
            _cfg.load_config = orig_load_config
            _sp.fetch_qq_playlist = orig_sp_fetch
            _nea.fetch_playlist = orig_nea_fetch
            _lib.TASKS_DIR = orig_tasks_dir

        # ---- e) 零 cookie 回归：解析仓库自带的 config.example.toml（发布默认态）----
        # 不读本机真实 config.toml——用户填入真实 cookie 后该断言必挂（环境耦合，
        # 独立审查 L4）；发布默认态由随仓库走的 config.example.toml 保证。
        example_toml = Path(__file__).resolve().parents[2] / "config.example.toml"
        cfg_example = _cfg.load_config(str(example_toml))
        assert cfg_example.cookies.netease == "" and cfg_example.cookies.qq == "", (
            f"config.example.toml 的 [cookies] 必须为空占位: {cfg_example.cookies}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    _failed = []
    for _name, _fn in _LOCAL:
        try:
            _fn(); print(f"PASS  {_name}")
        except Exception as _e:
            _failed.append(_name); print(f"FAIL  {_name}: {_e}")
    if _failed:
        raise SystemExit(1)
    print("ALL COOKIE CHECKS PASSED")
