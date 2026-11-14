"""B 站音源（api.bilibili.com 综合搜索 + yt-dlp 下载）。

蓝本（只读转录）：download_bili.py:169-177（buvid3）、180-190（parse_duration）、193-195（clean_title）、
198-222（search_bili）、318-328（yt-dlp 下载）、384-403（三段式搜索升级）。
勘误：搜索 URL 以蓝本为准 = api.bilibili.com/x/web-interface/search/all/v2（brief 漏写 web-interface 段）。
离线铁律：HTTP 只写不调；parse_duration / clean_title / build_search_url / parse_search 为纯函数。
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Optional

from ..util import CHROME_UA, http_get
from .base import make_candidate

try:  # 三段计划优先用 match 层公共实现（match/score.py:225）
    from ..match.score import plan_search_queries as _match_plan
except Exception:  # pragma: no cover - match 层未合入时内置等价三段查询
    _match_plan = None

BILI_API = "https://api.bilibili.com/x/web-interface/search/all/v2"
BILI_FINGER_SPI = "https://api.bilibili.com/x/frontend/finger/spi"
BILI_REFERER = "https://www.bilibili.com/"

# buvid3 模块级缓存（蓝本 download_bili.py:170 global _buvid 的列表等价）
_buvid_cache = [None]


def parse_duration(s: Any) -> Optional[float]:
    """解析 "M:SS"/"H:MM:SS" 秒数（download_bili.py:180-190 逐行转录；解析失败返回 None）。"""
    if isinstance(s, (int, float)):
        return float(s)
    parts = str(s or "").split(":")
    try:
        sec = 0
        for p in parts:
            sec = sec * 60 + int(p)
        return float(sec)
    except Exception:
        return None


def clean_title(s: Any) -> str:
    """剥 <[^>]+> HTML 标签 + html.unescape（download_bili.py:193-195 逐行转录）。"""
    s = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(s).strip()


def build_search_url(keyword: str, page: int = 1) -> str:
    """构造综合搜索 URL（蓝本 download_bili.py:201-202 / hunt_last3.py:298-299）。"""
    return BILI_API + "?" + urllib.parse.urlencode({"keyword": keyword, "page": page})


def parse_search(payload: Any) -> list:
    """解析综合搜索响应：抓 data.result[] 中 result_type=='video' 块（download_bili.py:204-221 逐行转录）。"""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except Exception:
            return []
    data = payload if isinstance(payload, dict) else {}
    vids = []
    for g in (data.get("data") or {}).get("result", []) or []:
        if isinstance(g, dict) and g.get("result_type") == "video":
            vids = g.get("data") or []
            break
    out = []
    for v in vids:
        if not isinstance(v, dict) or not v.get("bvid"):
            continue
        bvid = v.get("bvid")
        out.append(make_candidate(
            source="bili", id=str(bvid),
            title=clean_title(v.get("title")),
            artists=[str(v.get("author") or "")],
            duration=parse_duration(v.get("duration")),
            ext=None, url=f"https://www.bilibili.com/video/{bvid}",
            extra={"author": v.get("author") or "", "bvid": bvid,
                   "desc": v.get("desc") or "", "play": v.get("play") or 0}))
    return out


def get_buvid3(http_fn: Optional[Callable] = None) -> Optional[str]:
    """GET finger/spi 取 data.b_3 作 buvid3 cookie（download_bili.py:169-177 逐行转录；失败返回 None）。"""
    if _buvid_cache[0] is not None:
        return _buvid_cache[0] or None
    try:
        fn = http_fn or _default_http
        d = json.loads(fn(BILI_FINGER_SPI, 10))
        _buvid_cache[0] = str(d["data"]["b_3"])
    except Exception:
        _buvid_cache[0] = "0"  # 蓝本哨兵：失败缓存，避免重复打 finger 接口
    return _buvid_cache[0] or None


def _default_http(url: str, timeout: int = 15, cookie: Optional[str] = None) -> str:
    return http_get(url, ua=CHROME_UA, referer=BILI_REFERER, cookie=cookie, timeout=timeout)


def track_query(track: dict) -> str:
    """track dict -> "歌手 歌名" 搜索词。"""
    name = str(track.get("name") or track.get("title") or "").strip()
    artists = track.get("artists") or []
    artist = str(artists[0]).strip() if artists else ""
    return f"{artist} {name}".strip()


def default_plan(track: dict) -> list:
    """内置等价三段计划的降级版（match 层未合入时兜底，蓝本 download_bili.py:384-403 语义）。

    别名展开依赖 config [aliases]（match 层 plan_search_queries 的职责），
    这里只出主查询与纯艺人名 3 页两段。返回 [(query, pages), ...]。
    """
    artist = str((track.get("artists") or [""])[0]).strip() if track.get("artists") else ""
    title = str(track.get("name") or track.get("title") or "").strip()
    plan = []
    main_q = f"{artist} {title}".strip() if artist else title
    if main_q:
        plan.append((main_q, 1))
    if artist:
        plan.append((artist, 3))
    return plan


class BilibiliSource:
    """B 站源：综合搜索（video 块）+ yt-dlp bestaudio 下载。"""

    name = "bili"
    lossless = False

    def __init__(self, cfg: Optional[dict] = None, http_fn: Optional[Callable] = None):
        self.cfg = cfg or {}
        self._http_fn = http_fn  # 可注入假 http 供离线测试

    def _search_once(self, query: str, page: int = 1) -> list:
        """单页搜索：带 Cookie: buvid3=<...> 与 Referer（蓝本 download_bili.py:198-222 语义）。失败返回 []。"""
        try:
            buvid = get_buvid3(self._http_fn)
            url = build_search_url(query, page)
            if self._http_fn is not None:
                raw = self._http_fn(url, 15)
            else:
                raw = _default_http(url, 15, cookie=f"buvid3={buvid}" if buvid else None)
            return parse_search(raw)
        except Exception:
            return []

    def _alt_entries(self) -> list:
        """从 cfg 提取 config [aliases] alt_titles 条目（兼容 dict 与 config 对象两种形态）。"""
        try:
            cfg = self.cfg
            aliases = getattr(cfg, "aliases", None)
            if aliases is not None:
                return list(getattr(aliases, "alt_titles", None) or [])
            if isinstance(cfg, dict):
                aliases = cfg.get("aliases")
                if isinstance(aliases, dict):
                    return list(aliases.get("alt_titles") or [])
                return list(aliases or [])
        except Exception:
            pass
        return []

    def search(self, track: dict) -> list:
        """三段式搜索合并候选（蓝本 download_bili.py:384-403）：
        首搜 -> ALT 别名逐个重搜合并 -> 纯艺人名搜 3 页。
        """
        plan = None
        if _match_plan is not None:
            try:
                plan = _match_plan(track, self._alt_entries())
            except Exception:
                plan = None
        if not plan:
            plan = default_plan(track)
        pool: dict = {}
        for item in plan:
            if isinstance(item, (tuple, list)):
                query = str(item[0])
                pages = int(item[1]) if len(item) > 1 else 1
            else:
                query, pages = str(item), 1
            for page in range(1, max(1, pages) + 1):
                for c in self._search_once(query, page):
                    pool.setdefault(c["id"], c)
        return list(pool.values())

    def fetch(self, cand: dict, dest_dir: str) -> Optional[str]:
        """yt-dlp 下载（download_bili.py:318-328 逐行转录；--no-part --no-continue，cwd=dest_dir）。失败返回 None。"""
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        extra = cand.get("extra") or {}
        bvid = cand.get("id") or extra.get("bvid")
        if not bvid:
            return None
        try:
            stage_tpl = str(dest / f"bili_{bvid}.%(ext)s")
            p = subprocess.run(
                ["yt-dlp", "--no-playlist", "--no-warnings", "--no-part", "--no-continue",
                 "-f", "bestaudio/best", "-o", stage_tpl, f"https://www.bilibili.com/video/{bvid}"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=300, cwd=str(dest))
            if p.returncode != 0:
                return None
            files = dest.glob(f"bili_{bvid}.*")
            media = [f for f in files if f.suffix.lower() not in {".jpg", ".json"}]
            return str(media[0]) if media else None
        except Exception:
            return None
