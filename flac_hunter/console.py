"""控制台工具：UTF-8 输出、带时间戳日志、宽字符安全截断。"""

from __future__ import annotations

import sys
import time
import unicodedata


def setup_console() -> None:
    """强制 stdout/stderr 为 UTF-8（Windows 控制台防乱码）；失败静默。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def log(msg: str) -> None:
    """打印带 [HH:MM:SS] 前缀的一行日志。"""
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")
    except Exception:
        pass


def _char_width(ch: str) -> int:
    """单字符显示宽度：东亚宽字（W/F）算 2，其余算 1。"""
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def display_width(text: str) -> int:
    """整串显示宽度。"""
    return sum(_char_width(ch) for ch in text)


def elide(text: str, max_width: int) -> str:
    """按显示宽度截断：宽字符算 2 列，超宽时截断并在末尾加 …。"""
    if max_width <= 0:
        return ""
    if display_width(text) <= max_width:
        return text
    out: list[str] = []
    w = 0
    for ch in text:
        cw = _char_width(ch)
        if w + cw > max_width - 1:  # 预留 1 列给省略号
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"
