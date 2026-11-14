"""LRCLIB 歌词源（lrclib.net/api/search）：多变体轮询 + 双重筛选选最优条目。

蓝本（只读转录）：hunt_last3.py:429-464（lrclib_fetch 主逻辑）、download.py:214-246（备用筛选）。
离线铁律：HTTP 只写不调；build_queries / pick_best_entry 为可离线单测的纯函数。
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from typing import Any, Callable, Optional

from ..util import CHROME_UA, http_get

try:  # 备用筛选的归一化用 match 层 norm_text；未合入时退化为蓝本 name_core
    from ..match.normalize import norm_text as _norm_text
except Exception:  # pragma: no cover - 仅前置缺失时兜底
    def _norm_text(s):
        """蓝本 hunt_last3.py:143-144 的 name_core 等价实现。"""
        return re.sub(r"[\s（）()（）\[\]【】・·]", "", s or "").lower()

LRCLIB_API = "https://lrclib.net/api/search"


def _name_core(s: str) -> str:
    """蓝本 hunt_last3.py:143-144 逐行转录（lrclib 变体去重专用）。"""
    return re.sub(r"[\s（）()（）\[\]【】・·]", "", s or "").lower()


def build_queries(artist: str, title: str, alt_variants: Optional[list] = None) -> list:
    """多变体查询序列（hunt_last3.py:439-445 逐行转录）：歌手+歌名 / 裸歌名 / 别名前 3 / 剥 [ 前截断。"""
    artist, title = str(artist or "").strip(), str(title or "").strip()
    tries_q = [f"{artist} {title}".strip(), title]
    for v in (alt_variants or [])[:3]:
        if _name_core(v) != _name_core(title):
            tries_q.append(f"{artist} {v}".strip())
            tries_q.append(v)
    if "[" in title:
        tries_q.append(f"{artist} {title.split('[')[0].strip()}".strip())
    # 去重保持顺序（同一变体可能重复出现）
    out, seen = [], set()
    for q in tries_q:
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def pick_best_entry(entries: Any, duration_s: Optional[float],
                    title: Optional[str] = None, artist: Optional[str] = None) -> Optional[dict]:
    """条目双重筛选（hunt_last3.py:447-461 主逻辑 + download.py:229-241 备用筛选）。

    主筛选：有 syncedLyrics 的条目取时长差最小者（条目无时长视为 9999）。
    备用筛选（主筛选无命中且 title/artist 提供时）：
    trackName 归一化相等 + artistName 包含 + 时长差<=10s，rank=(非synced, 差) 最优（允许 plain）。
    """
    if not isinstance(entries, list):
        return None
    best, bestd = None, None
    for it in entries:
        if not isinstance(it, dict) or not it.get("syncedLyrics"):
            continue
        try:
            d = float(it.get("duration") or 0)
        except (TypeError, ValueError):
            d = 0.0
        if duration_s is None or not d:
            diff = 9999.0
        else:
            diff = abs(d - float(duration_s))
        if best is None or diff < bestd:
            best, bestd = it, diff
    if best is not None and bestd is not None and duration_s is not None and bestd <= 5.0:
        return best
    if best is not None and duration_s is None:
        return best
    # 备用筛选（download.py:229-241 逐行转录）
    if title is not None:
        nname = _norm_text(title)
        nartist = _norm_text(artist or "")
        sdur = float(duration_s or 0)
        best2 = None
        for it in entries:
            if not isinstance(it, dict) or not (it.get("syncedLyrics") or it.get("plainLyrics")):
                continue
            if _norm_text(it.get("trackName") or "") != nname:
                continue
            if nartist and nartist not in _norm_text(it.get("artistName") or ""):
                continue
            try:
                d = abs(float(it.get("duration") or 0) - sdur)
            except (TypeError, ValueError):
                continue
            if sdur and d > 10:
                continue
            rank = (0 if it.get("syncedLyrics") else 1, d)
            if best2 is None or rank < best2[0]:
                best2 = (rank, it)
        if best2:
            return best2[1]
    return None


def _default_http(url: str, timeout: int = 20) -> str:
    return http_get(url, ua=CHROME_UA, timeout=timeout)


def search_lyrics(artist: str, title: str, duration_s: Optional[float] = None,
                  alt_variants: Optional[list] = None, http_fn: Optional[Callable] = None,
                  min_interval: float = 0.5) -> Optional[dict]:
    """逐 build_queries 轮询 lrclib.net/api/search，每查询间 sleep（rate.lrclib_min_interval，默认 0.5s）。

    返回 {'synced':..., 'plain':..., 'duration':..., 'trackName':..., 'artistName':...}；
    任何异常返回 None 不抛出（HTTP 只写不调）。
    """
    fn = http_fn or _default_http
    queries = build_queries(artist, title, alt_variants)
    best, bestd = None, None
    try:
        for q in queries:
            if http_fn is None and min_interval and min_interval > 0:
                time.sleep(min_interval)
            url = LRCLIB_API + "?" + urllib.parse.urlencode({"q": q})
            try:
                arr = json.loads(fn(url, 20))
            except Exception:
                continue
            if not isinstance(arr, list):
                continue
            hit = pick_best_entry(arr, duration_s, title=title, artist=artist)
            if hit is None:
                continue
            try:
                d = float(hit.get("duration") or 0)
            except (TypeError, ValueError):
                d = 0.0
            diff = abs(d - float(duration_s)) if (duration_s is not None and d) else 9999.0
            if best is None or diff < bestd:
                best, bestd = hit, diff
            if best is not None and (hit.get("syncedLyrics") or best.get("syncedLyrics")) \
                    and duration_s is not None and bestd <= 5.0:
                break  # 时长差 <=5.0s 早停（hunt_last3.py:460-461）
    except Exception:
        return None
    if best is None:
        return None
    return {
        "synced": best.get("syncedLyrics"),
        "plain": best.get("plainLyrics"),
        "duration": best.get("duration"),
        "trackName": best.get("trackName"),
        "artistName": best.get("artistName"),
    }
