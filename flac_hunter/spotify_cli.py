"""Spotify CLI（spotify_cli.exe）包装 + QQ 歌单匿名接口。

蓝本：prepare.py:103-117（playlist get / lookup 分批）、qq2_dl.py:136-143（JSONP 剥壳）。
parse_playlist_json / parse_lookup_json / parse_qq_jsonp 为纯函数，离线可测；
fetch_qq_playlist 内部才经 util.http_get 发起请求（HTTP 只写不调，由调用方离线禁用）。
"""
import json
import subprocess
from pathlib import Path

from flac_hunter.util import http_get

# QQ 匿名歌单接口（qq2_dl.py:136-143 蓝本）
QQ_FCG_URL = "https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg"
QQ_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0"


class SpotifyCliError(Exception):
    """spotify_cli.exe 调用失败（路径不存在 / 进程出错 / 输出不可解析）。"""


def parse_playlist_json(raw):
    """playlist get 原始 dict -> 曲目列表（raw['tracks']，prepare.py:104）。"""
    return raw["tracks"]


def parse_lookup_json(raw):
    """lookup --fields duration 原始 dict -> {uri: {'duration_ms': int|None, 'image_url': str|None}}。

    entities[].metadata[] 里 field=='duration' 的 int 值即毫秒（prepare.py:112-117）。
    """
    out = {}
    for e in raw.get("entities", []):
        dur = None
        for m in e.get("metadata", []):
            if m.get("field") == "duration":
                dur = int(m["value"])
        out[e["uri"]] = {"duration_ms": dur, "image_url": e.get("image_url")}
    return out


class SpotifyCli:
    """spotify_cli.exe 子进程包装；exe 路径不存在不立即抛，调用时抛 SpotifyCliError。"""

    def __init__(self, exe_path):
        self.exe_path = str(exe_path)

    def _run(self, args, timeout=120):
        if not Path(self.exe_path).exists():
            raise SpotifyCliError(
                f"spotify_cli.exe 不存在：{self.exe_path}（请在 config.toml [paths] spotify_cli 配置有效路径）")
        try:
            p = subprocess.run([self.exe_path, *args], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise SpotifyCliError(f"spotify_cli.exe 超时({timeout}s)：{self.exe_path}") from e
        if p.returncode != 0:
            raise SpotifyCliError(
                f"spotify_cli.exe 退出码 {p.returncode}：{(p.stderr or p.stdout or '')[-300:]}")
        return p.stdout

    def playlist_get(self, uri, limit=500):
        """playlist get <uri> --limit N --format json -> 原始 dict（prepare.py:103-105）。"""
        out = self._run(["playlist", "get", uri, "--limit", str(limit), "--format", "json"])
        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            raise SpotifyCliError(f"playlist get 输出不是合法 JSON：{e}") from e

    def lookup_durations(self, uris):
        """每 20 个 URI 一批 lookup --fields duration -> {uri: {'duration_ms','image_url'}}（prepare.py:107-117）。"""
        by_uri = {}
        for i in range(0, len(uris), 20):
            chunk = uris[i:i + 20]
            text = self._run(["lookup", *chunk, "--fields", "duration", "--format", "json"])
            try:
                by_uri.update(parse_lookup_json(json.loads(text)))
            except json.JSONDecodeError as e:
                raise SpotifyCliError(f"lookup 输出不是合法 JSON：{e}") from e
        return by_uri


def parse_qq_jsonp(text):
    """剥 JSONP 外壳（qq2_dl.py:137-138）：strip 后首字符非 {/[ 则取首个 ( 之后、末个 ) 之前；返回 dict。"""
    s = text.strip()
    if s[:1] not in "{[":
        s = s[s.find("(") + 1:s.rfind(")")]
    return json.loads(s)


def fetch_qq_playlist(disstid):
    """匿名拉取 QQ 歌单，返回 cdlist[0].songlist 列表（唯一发起网络请求的函数，离线时绝不调用）。"""
    url = f"{QQ_FCG_URL}?type=1&disstid={disstid}&format=json"
    raw = http_get(url, ua=QQ_UA, referer="https://y.qq.com/")  # util.http_get 返回 bytes
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("gb18030", errors="replace")
    qq = parse_qq_jsonp(text)
    return (qq.get("cdlist") or [{}])[0].get("songlist") or []
