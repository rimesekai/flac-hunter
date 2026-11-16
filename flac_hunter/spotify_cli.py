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


def _cjk_score(s: str) -> int:
    """中日文字符密度（歌名元数据的语言语境必然是日文/中文）。"""
    return sum(1 for c in s if "\u3040" <= c <= "\u30ff" or "\u3400" <= c <= "\u9fff")


def _fix_mojibake(s: str) -> str:
    """修复单个字符串的乱码：高位字节还原回原始字节后按 UTF-8 / GB18030 有向消歧。

    歧义是双向的：GBK 字节对大多恰好也是合法 UTF-8（解成希腊/西里尔字母
    垃圾），而 UTF-8 的 CJK 字节对在 GB18030 下也常解成 CJK 垃圾——所以
    计数比多少没用。用方向性规则：
    ① UTF-8 严格解码成功且含任何 CJK → 必是真 UTF-8（GBK 误读成 UTF-8
       只会产生欧洲区字符，不会产生 CJK）；
    ② 否则 GB18030 解码含 CJK → 判 GBK；
    ③ 都不含 CJK → 平手取 UTF-8（ASCII 情形两者等价）。
    """
    if not any("\x80" <= c <= "\xff" for c in s):
        return s  # 纯 ASCII，无需处理
    raw = s.encode("latin-1", errors="ignore")
    cands: dict = {}
    for enc in ("utf-8", "gb18030"):
        try:
            fixed = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if "\ufffd" in fixed:
            continue
        cands[enc] = fixed
    if "utf-8" in cands and _cjk_score(cands["utf-8"]) > 0:
        return cands["utf-8"]
    if "gb18030" in cands and _cjk_score(cands["gb18030"]) > 0:
        return cands["gb18030"]
    if "utf-8" in cands:
        return cands["utf-8"]
    return raw.decode("gb18030", errors="replace")


def _deep_fix(obj):
    """递归修复解析结果里所有字符串的乱码。"""
    if isinstance(obj, str):
        return _fix_mojibake(obj)
    if isinstance(obj, list):
        return [_deep_fix(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _deep_fix(v) for k, v in obj.items()}
    return obj


def _parse_qq_response(raw: bytes):
    """解析 QQ 歌单响应字节，返回 cdlist[0].songlist（可能为空列表）。

    主路径：latin-1 解码（字节与字符一一对应，JSON 结构绝对完整，不受内容
    编码影响）→ 解析成功后逐字符串按 UTF-8/GB18030 修复乱码——同包混用
    两种编码也能各自还原。备用路径：latin-1 结构解析失败才退回多解码竞争。
    """
    try:
        text = raw.decode("latin-1")
        qq = parse_qq_jsonp(text)
        songs = (qq.get("cdlist") or [{}])[0].get("songlist") or []
        if songs:
            return _deep_fix(songs)
    except Exception:
        pass
    for decode in (
        lambda: raw.decode("utf-8", errors="replace"),
        lambda: raw.decode("gb18030", errors="replace"),
    ):
        try:
            qq = parse_qq_jsonp(decode())
            songs = (qq.get("cdlist") or [{}])[0].get("songlist") or []
            if songs:
                return songs
        except Exception:
            continue
    return []


def fetch_qq_playlist(disstid, cookie: str | None = None):
    """拉取 QQ 歌单，返回 cdlist[0].songlist 列表（唯一发起网络请求的函数，离线时绝不调用）。

    cookie 非空时附带 Cookie 头（[cookies].qq 登录态，可读私密歌单）；
    空则匿名——util._headers（util.py:24-31）对空 cookie 天然不加 Cookie 键。
    """
    url = f"{QQ_FCG_URL}?type=1&disstid={disstid}&format=json"
    raw = http_get(url, ua=QQ_UA, referer="https://y.qq.com/", cookie=cookie or None)  # 返回 bytes
    return _parse_qq_response(raw)
