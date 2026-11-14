"""网易云音源（music.163.com 匿名接口）：单曲/专辑/歌手搜索、128k 兜底直链、歌曲详情。

蓝本（只读转录）：hunt_last3.py:222-245（搜索）、248-259（专辑）、593-608（歌手 hotSongs 深挖）、
upgrade_ogg.py:188-196（player/url 匿名 128k）、verify_kaisei.py:61-63（song/detail）。
离线铁律：本模块 HTTP 函数只写不调；请求构造与响应解析均为可离线单测的纯函数。
"""
from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Optional

from ..util import CHROME_UA, download_stream, guess_ext_from_url, http_get
from .base import make_candidate
from .gdstudio import norm_dur

NETEASE_BASE = "https://music.163.com"
NETEASE_REFERER = "https://music.163.com/"


def build_search_url(keyword: str, type: int = 1, limit: int = 30) -> str:
    """构造匿名搜索 URL（type=1 单曲 / 10 专辑 / 100 歌手；蓝本 hunt_last3.py:224-225）。"""
    return NETEASE_BASE + "/api/search/get/web?" + urllib.parse.urlencode(
        {"s": keyword, "type": type, "offset": 0, "total": "true", "limit": limit})


def build_player_url(song_id: str, br: int = 128000) -> str:
    """构造匿名 player/url 直链请求（蓝本 upgrade_ogg.py:189-190）。"""
    return NETEASE_BASE + "/api/song/enhance/player/url?" + urllib.parse.urlencode(
        {"ids": f"[{song_id}]", "br": br})


def build_detail_url(song_id: str) -> str:
    """构造 song/detail 请求（蓝本 verify_kaisei.py:62）。"""
    return NETEASE_BASE + "/api/song/detail?" + urllib.parse.urlencode(
        {"id": song_id, "ids": f"[{song_id}]"})


def _join_artists(arr: Any) -> str:
    """艺人列表 -> "A, B" 串（蓝本 hunt_last3.py:235/240/244 同款）。"""
    return ", ".join(a.get("name", "") for a in (arr or []) if isinstance(a, dict))


def parse_search(payload: Any) -> list:
    """解析单曲搜索响应（result.songs[].duration 毫秒 -> norm_dur 秒，hunt_last3.py:242-245 逐行转录）。"""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except Exception:
            return []
    if not isinstance(payload, dict):
        return []
    res = payload.get("result") or {}
    out = []
    for s in res.get("songs") or []:
        if not isinstance(s, dict) or s.get("id") is None:
            continue
        out.append(make_candidate(
            source="netease", id=str(s.get("id")),
            title=str(s.get("name") or "")[:60],
            artists=[p.strip() for p in _join_artists(s.get("artists")).split(", ") if p.strip()],
            duration=norm_dur(s.get("duration")),
            ext=None, url=None,
            extra={"via": "netease"}))
    return out


def parse_album(payload: Any) -> list:
    """解析专辑详情响应（/api/album/{id} 的 album.songs，hunt_last3.py:248-259 逐行转录）。"""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except Exception:
            return []
    if not isinstance(payload, dict):
        return []
    alb = payload.get("album") or {}
    out = []
    for s in alb.get("songs") or []:
        if not isinstance(s, dict) or s.get("id") is None:
            continue
        out.append(make_candidate(
            source="netease", id=str(s.get("id")),
            title=str(s.get("name") or "")[:60],
            artists=[p.strip() for p in _join_artists(s.get("artists")).split(", ") if p.strip()],
            duration=norm_dur(s.get("duration")),
            ext=None, url=None,
            extra={"via": f"album:{alb.get('id')}"},))
    return out


def parse_artist_songs(payload: Any, artist_name: str = "") -> list:
    """解析歌手 hotSongs（/api/artist/{id}，匿名接口上限 50 首，hunt_last3.py:596-608 逐行转录）。"""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except Exception:
            return []
    if not isinstance(payload, dict):
        return []
    out = []
    for s in (payload.get("hotSongs") or [])[:50]:
        if not isinstance(s, dict) or s.get("id") is None:
            continue
        out.append(make_candidate(
            source="netease", id=str(s.get("id")),
            title=str(s.get("name") or "")[:60],
            artists=[artist_name] if artist_name else [],
            duration=norm_dur(s.get("duration")),
            ext=None, url=None,
            extra={"via": f"artist:{artist_name}"}))
    return out


def _default_http(url: str, timeout: int = 20) -> str:
    return http_get(url, ua=CHROME_UA, referer=NETEASE_REFERER, timeout=timeout)


def parse_artist_search(payload: Any) -> list:
    """解析歌手搜索响应（type=100，蓝本 hunt_last3.py:237-241：返回 [{id,name}]）。"""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except Exception:
            return []
    if not isinstance(payload, dict):
        return []
    res = payload.get("result") or {}
    return [{"id": str(a.get("id")), "name": str(a.get("name") or "")[:60]}
            for a in res.get("artists") or [] if isinstance(a, dict) and a.get("id") is not None]


def parse_album_search(payload: Any) -> list:
    """解析专辑搜索响应（type=10，蓝本 hunt_last3.py:232-236：返回 [{id,name,artist}]）。"""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except Exception:
            return []
    if not isinstance(payload, dict):
        return []
    res = payload.get("result") or {}
    out = []
    for a in res.get("albums") or []:
        if not isinstance(a, dict) or a.get("id") is None:
            continue
        out.append({"id": str(a.get("id")), "name": str(a.get("name") or "")[:60],
                    "artist": _join_artists(a.get("artists"))[:48]})
    return out


class NeteaseSource:
    """网易云源：单曲搜索为主，专辑/歌手 hotSongs 深挖为辅，player/url 128k 兜底。"""

    name = "netease"
    lossless = False

    def __init__(self, cfg: Optional[dict] = None, http_fn: Optional[Callable] = None):
        self.cfg = cfg or {}
        self._http_fn = http_fn  # 可注入假 http 供离线测试

    def _get(self, url: str, timeout: int = 20) -> str:
        if self._http_fn is not None:
            return self._http_fn(url, timeout)
        return _default_http(url, timeout)

    def search(self, track: dict) -> list:
        """type=1 单曲搜索（Referer: https://music.163.com/）；失败返回 []。"""
        from .gdstudio import track_query
        try:
            raw = self._get(build_search_url(track_query(track), 1, 30), 20)
            return parse_search(raw)
        except Exception:
            return []

    def search_album_artists(self, track: dict, max_artists: int = 2, max_albums: int = 2) -> list:
        """专辑/歌手通道深挖（蓝本 hunt_last3.py:248-259、593-608 语义；供 pipeline 可选调用）。

        type=100 歌手搜索 -> 名称包含匹配的前 max_artists 个歌手拉 hotSongs[:50]；
        type=10 专辑搜索 -> 前 max_albums 张专辑拉 /api/album/{id} 曲目。返回统一候选列表。
        """
        from .gdstudio import track_query
        artist = str((track.get("artists") or [""])[0]).strip() if track.get("artists") else ""
        out, seen = [], set()

        def _add(cands):
            for c in cands:
                if c["id"] in seen:
                    continue
                seen.add(c["id"])
                out.append(c)

        # 通道 a：歌手 hotSongs 深挖
        try:
            arts = parse_artist_search(self._get(build_search_url(artist, 100, 8), 20))
        except Exception:
            arts = []
        matched = [a for a in arts
                   if artist and (artist.lower() in a["name"].lower() or a["name"].lower() in artist.lower())]
        for art in matched[:max_artists]:
            try:
                _add(parse_artist_songs(self._get(f"{NETEASE_BASE}/api/artist/{art['id']}", 20), art["name"]))
            except Exception:
                continue
        # 通道 b：专辑曲目深挖
        try:
            albums = parse_album_search(self._get(build_search_url(track_query(track), 10, 8), 20))
        except Exception:
            albums = []
        for alb in albums[:max_albums]:
            try:
                _add(parse_album(self._get(f"{NETEASE_BASE}/api/album/{alb['id']}", 20)))
            except Exception:
                continue
        return out

    def get_url(self, song_id: str, timeout: int = 15):
        """匿名 player/url 128k 兜底（upgrade_ogg.py:188-196 逐行转录）。返回 (url, br) 或 None。"""
        try:
            data = json.loads(self._get(build_player_url(song_id, 128000), timeout))
            item = (data.get("data") or [{}])[0]
            if item.get("url") and item.get("code") == 200:
                return str(item["url"]), item.get("br") or 0
        except Exception:
            pass
        return None

    def song_detail(self, song_id: str, timeout: int = 15) -> Optional[dict]:
        """song/detail 查歌曲详情（verify_kaisei.py:61-63 逐行转录）。失败/无歌返回 None。"""
        try:
            data = json.loads(self._get(build_detail_url(song_id), timeout))
            songs = data.get("songs") or []
            return songs[0] if songs else None
        except Exception:
            return None

    def fetch(self, cand: dict, dest_dir: str) -> Optional[str]:
        """get_url 兜底 128k 下载（util.download_stream）；br 写进候选 extra；失败返回 None。"""
        try:
            dest = Path(dest_dir)
            dest.mkdir(parents=True, exist_ok=True)
            url, br = self.get_url(cand.get("id") or "")
            if not url:
                return None
            ext = guess_ext_from_url(url)
            stem = (cand.get("extra") or {}).get("filename_stem") or f"netease_{cand.get('id') or 'unknown'}"
            out = dest / f"{stem}{ext}"
            download_stream(url, str(out), timeout=300)
            if isinstance(cand.get("extra"), dict):
                cand["extra"]["br"] = br
            return str(out)
        except Exception:
            return None
