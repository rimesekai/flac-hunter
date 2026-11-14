"""通用工具：HTTP GET、分块下载流、多编码读文本、跨盘移动、URL 扩展名推断。"""

from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

CHROME_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_CHUNK = 64 * 1024  # 64KB 分块
_TEXT_ENCODINGS = ("utf-8-sig", "utf-16", "gbk", "shift_jis")  # 探测顺序，见 check_lyrics.py:27-34


class UtilError(Exception):
    """工具层基础异常。"""


class DownloadError(UtilError):
    """下载失败或响应小于下限、疑似报错页。"""


def _headers(ua: str, referer: str | None, cookie: str | None) -> dict[str, str]:
    """组装请求头：UA 必带，Referer/Cookie 可选。"""
    h = {"User-Agent": ua}
    if referer:
        h["Referer"] = referer
    if cookie:
        h["Cookie"] = cookie
    return h


def http_get(url: str, *, ua: str = CHROME_UA, referer: str | None = None,
             cookie: str | None = None, timeout: float = 20.0) -> bytes:
    """GET 请求，返回响应字节；异常向上抛给调用方处理。"""
    req = urllib.request.Request(url, headers=_headers(ua, referer, cookie))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _unlink_quiet(path: Path) -> None:
    """删除文件，失败静默（半成品清理）。"""
    try:
        path.unlink()
    except OSError:
        pass


def download_stream(url: str, dest: str | Path, *, ua: str = CHROME_UA,
                    referer: str | None = None, cookie: str | None = None,
                    min_bytes: int = 102400, timeout: float = 300.0) -> int:
    """分块下载 url 到 dest，返回总字节数。

    64KB 分块写盘；总字节 < min_bytes（默认 100KB）视为报错页：
    删除半成品并抛 DownloadError。中途异常同样清理半成品后原样抛出。
    """
    req = urllib.request.Request(url, headers=_headers(ua, referer, cookie))
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, \
                open(dest_path, "wb") as f:
            while True:
                block = resp.read(_CHUNK)
                if not block:
                    break
                f.write(block)
                total += len(block)
    except Exception:
        _unlink_quiet(dest_path)
        raise
    if total < min_bytes:
        _unlink_quiet(dest_path)
        raise DownloadError(
            f"仅收到 {total} 字节（< {min_bytes}），疑似报错页，已拒收并删除: {url}")
    return total


def smart_read_text(path: str | Path) -> str | None:
    """多编码顺序探测读文本（蓝本 check_lyrics.py:27-34）。

    顺序：utf-8-sig → utf-16 → gbk → shift_jis → utf-8(errors=replace)。
    文件不可读返回 None；编码全部失败时以 utf-8 replace 兜底，不抛错。
    """
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    for enc in _TEXT_ENCODINGS:
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", "replace")


def cross_move(src: str | Path, dst: str | Path) -> None:
    """移动文件（含跨盘）：一律 shutil.move——os.replace 跨盘抛 WinError 17。"""
    src_path, dst_path = Path(src), Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_path), str(dst_path))


def guess_ext_from_url(url: str) -> str:
    """按 URL 去查询串后的后缀推断扩展名（蓝本 hunt_last3.py:328-333）。"""
    p = url.split("?")[0].lower()
    for e in (".flac", ".mp3", ".m4a", ".wav", ".ape", ".ogg"):
        if p.endswith(e):
            return e
    return ".bin"
