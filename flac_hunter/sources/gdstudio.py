"""GDStudio 聚合音源（music-api.gdstudio.xyz）：netease/tencent/kuwo 三源搜索与直链获取。

蓝本（只读转录）：hunt_last3.py:101-113（限速器）、200-219（search 解析）、262-272（url 阶梯）、315-325（源健康）。
离线铁律：本模块 HTTP 函数只写不调；请求构造与响应解析均为可离线单测的纯函数。
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Optional

from ..util import CHROME_UA, download_stream, guess_ext_from_url, http_get
from .base import make_candidate

try:  # match 层合入后优先用公共 norm_dur；未合入时用蓝本等价实现
    from ..match.tier import norm_dur
except Exception:  # pragma: no cover - 仅前置缺失时兜底
    def norm_dur(raw):
        """归一化时长：netease 多为毫秒，tencent interval / kuwo 为秒。>2000 视为毫秒（hunt_last3.py:130-140）。"""
        if raw in (None, "", 0, "0"):
            return None
        try:
            v = float(raw)
        except (TypeError, ValueError):
            return None
        if v <= 0:
            return None
        return v / 1000.0 if v > 2000 else v


GD_API_BASE = "https://music-api.gdstudio.xyz/api.php"
GD_SOURCES = ("netease", "tencent", "kuwo")
GD_MIN_INTERVAL = 1.05  # 防限流，硬要求

# 模块级限速时间戳（hunt_last3.py:101 逐行转录）
_gd_last_hit = [0.0]


def gd_throttle(now: Optional[float] = None, min_interval: float = GD_MIN_INTERVAL) -> None:
    """所有 GD API 调用前保证间隔 >= min_interval（默认 1.05 秒，防限流硬要求）。"""
    interval = GD_MIN_INTERVAL if min_interval is None else float(min_interval)
    if now is None:
        now = time.time()
    gap = now - _gd_last_hit[0]
    if gap < interval:
        time.sleep(interval - gap)
    _gd_last_hit[0] = time.time()


def _cfg_rate(cfg: Any, attr: str, default: float) -> float:
    """从 Config dataclass 或 dict 读取 rate.<attr>，缺失或非法回退 default。"""
    if cfg is None:
        return default
    rate = cfg.get("rate") if isinstance(cfg, dict) else getattr(cfg, "rate", None)
    if rate is None:
        return default
    val = rate.get(attr) if isinstance(rate, dict) else getattr(rate, attr, None)
    if isinstance(val, (int, float)) and not isinstance(val, bool) and val >= 0:
        return float(val)
    return default


def build_search_url(source: str, name: str, count: int = 8) -> str:
    """构造 types=search 请求 URL（纯函数，离线可测）。"""
    return GD_API_BASE + "?" + urllib.parse.urlencode(
        {"types": "search", "source": source, "name": name, "count": count, "pages": 1})


def build_url_url(source: str, song_id: str, br: int = 999999) -> str:
    """构造 types=url 请求 URL（纯函数，离线可测）。"""
    return GD_API_BASE + "?" + urllib.parse.urlencode(
        {"types": "url", "source": source, "id": song_id, "br": br})


def _split_artists(raw: Any, limit: int = 48) -> list:
    """候选歌手字符串 -> 艺人列表（按 ,，/、& 拆分；先按蓝本截断到 48 字符）。"""
    s = str(raw or "")[:limit].strip()
    if not s:
        return []
    return [p.strip() for p in re.split(r"[,，/、&]", s) if p.strip()]


def parse_gd_search(payload: Any, source: str) -> list:
    """GDStudio search 结果归一化（各源 id/duration 字段名不同，hunt_last3.py:200-219 逐行转录）。

    payload 可为已解析的 list 或原始 JSON 文本；source 记入候选 source，
    子源信息写进 extra.gd_source / extra.via（语义沿蓝本 make_cand 的 via="gd:<source>"）。
    """
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except Exception:
            return []
    if not isinstance(payload, list):
        return []
    out = []
    for it in payload:
        if not isinstance(it, dict):
            continue
        cid = it.get("id") or it.get("hash") or it.get("mid") or it.get("songid") or it.get("musicrid")
        if cid is None or str(cid).strip() == "":
            continue
        title = it.get("name") or it.get("songName") or it.get("title")
        extra = {"via": f"gd:{source}", "gd_source": source}
        out.append(make_candidate(
            source=source, id=str(cid),
            title=str(title or "")[:60],
            artists=_split_artists(it.get("artist") or it.get("singer")),
            duration=norm_dur(it.get("duration") or it.get("interval") or it.get("length")),
            ext=None, url=None, extra=extra))
    return out


def track_query(track: dict) -> str:
    """track dict -> "歌手 歌名" 搜索词（artists 列表取首艺人，蓝本 name=<歌手 歌名>）。"""
    name = str(track.get("name") or track.get("title") or "").strip()
    artists = track.get("artists") or []
    artist = str(artists[0]).strip() if artists else ""
    return f"{artist} {name}".strip()


def gd_api(params: dict, timeout: int = 30, http_fn: Optional[Callable] = None) -> str:
    """GDStudio 聚合 API（hunt_last3.py:104-113 逐行转录；只写不调，离线铁律）。

    所有请求（search/url）之间强制间隔 >=1.05 秒（防限流，硬要求）。
    """
    gd_throttle()
    url = GD_API_BASE + "?" + urllib.parse.urlencode(params)
    if http_fn is not None:  # 离线测试注入点
        return http_fn(url, timeout)
    return http_get(url, ua=CHROME_UA, timeout=timeout)


class GdStudioSource:
    """GDStudio 源：三源合并搜索 + br 阶梯直链 + 下载。"""

    name = "gdstudio"
    lossless = True

    def __init__(self, cfg: Any = None, http_fn: Optional[Callable] = None):
        self.cfg = cfg if cfg is not None else {}
        self._http_fn = http_fn  # 可注入假 http 供离线测试
        self._min_interval = _cfg_rate(cfg, "gd_min_interval", GD_MIN_INTERVAL)
        self.last_throttle_calls = 0

    def _get(self, url: str, timeout: int = 30) -> str:
        if self._http_fn is not None:
            return self._http_fn(url, timeout)
        gd_throttle(min_interval=self._min_interval)
        self.last_throttle_calls += 1
        return http_get(url, ua=CHROME_UA, timeout=timeout)

    def search(self, track: dict) -> list:
        """三源（netease/tencent/kuwo）各 count=8 合并候选；单源异常降级跳过。"""
        query = track_query(track)
        out, seen = [], set()
        for src in GD_SOURCES:
            try:
                raw = self._get(build_search_url(src, query, count=8), 30)
                cands = parse_gd_search(raw, src)
            except Exception:
                cands = []
            for c in cands:
                # 统一源名 gdstudio（pipeline 源序判定用），子源留在 extra
                c["source"] = "gdstudio"
                key = (c["id"], c.get("extra", {}).get("gd_source"))
                if key in seen:
                    continue
                seen.add(key)
                out.append(c)
        return out

    def get_url(self, source: str, song_id: str, timeout: int = 30):
        """types=url 拿直链：br=999999 优先（可能 FLAC 无损），退 320000/128000（hunt_last3.py:262-272 逐行转录）。

        返回 (url, br, size)；全部失败返回 (None, 0, 0)。
        """
        for br in (999999, 320000, 128000):
            try:
                raw = self._get(build_url_url(source, song_id, br), timeout)
                data = json.loads(raw)
                if isinstance(data, dict) and data.get("url"):
                    return str(data["url"]), br, data.get("size")
            except Exception:
                pass
        return None, 0, 0

    def fetch(self, cand: dict, dest_dir: str) -> Optional[str]:
        """get_url -> download_stream 落盘；br 写进候选 extra；失败返回 None。"""
        try:
            dest = Path(dest_dir)
            dest.mkdir(parents=True, exist_ok=True)
            extra = cand.get("extra") or {}
            gd_source = extra.get("gd_source") or "netease"
            url, br, _size = self.get_url(gd_source, cand.get("id") or "")
            if not url:
                return None
            ext = guess_ext_from_url(url)
            stem = extra.get("filename_stem") or f"gdstudio_{cand.get('id') or 'unknown'}"
            out = dest / f"{stem}{ext}"
            download_stream(url, str(out), timeout=300)
            if isinstance(cand.get("extra"), dict):
                cand["extra"]["br"] = br
            return str(out)
        except Exception:
            return None


def gd_source_health(http_fn: Optional[Callable] = None) -> dict:
    """GDStudio tencent/kuwo 源健康检查（'love' 基准关键词，hunt_last3.py:315-325 逐行转录；只写不调）。"""
    res = {}
    for src in ("tencent", "kuwo"):
        try:
            raw = gd_api({"types": "search", "source": src, "name": "love", "count": 5}, http_fn=http_fn)
            data = json.loads(raw)
            res[src] = f"正常，{len(data) if isinstance(data, list) else '非列表响应'} 条"
        except Exception as e:
            res[src] = f"故障：{str(e)[:60]}"
    return res
