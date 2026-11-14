"""YouTube 音源（yt-dlp 搜索 + 下载）。

蓝本（只读转录）：download.py:110-116（ytsearch 搜索）、271-282（下载）。
离线铁律：yt-dlp 命令只构造不执行；所有 subprocess 传 encoding='utf-8', errors='replace'。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from .base import make_candidate


def track_query(track: dict) -> str:
    """track dict -> "歌手 歌名" 搜索词。"""
    name = str(track.get("name") or track.get("title") or "").strip()
    artists = track.get("artists") or []
    artist = str(artists[0]).strip() if artists else ""
    return f"{artist} {name}".strip()


def parse_search_json(stdout: str, query: str) -> list:
    """解析 yt-dlp --dump-single-json 输出（download.py:115-116 语义）-> 统一候选列表（纯函数）。"""
    try:
        data = json.loads(stdout)
    except Exception:
        return []
    out = []
    for e in data.get("entries") or []:
        if not isinstance(e, dict) or not e.get("id"):
            continue
        vid = str(e["id"])
        dur = None
        try:
            dur = float(e.get("duration")) if e.get("duration") is not None else None
        except (TypeError, ValueError):
            dur = None
        out.append(make_candidate(
            source="youtube", id=vid,
            title=str(e.get("title") or ""),
            artists=[],  # 候选艺人留空；score_youtube 用目标艺人变体在 title/uploader 上判分
            duration=dur,
            ext=None,
            url=e.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
            extra={"uploader": e.get("uploader") or "", "channel": e.get("channel") or "",
                   "view_count": e.get("view_count"), "query": query}))
    return out


class YtDlpSource:
    """YouTube 源：yt-dlp ytsearch8 搜索 + bestaudio 下载。"""

    name = "youtube"
    lossless = False

    def __init__(self, cfg: Optional[dict] = None):
        self.cfg = cfg or {}

    def search(self, track: dict, n: int = 8) -> list:
        """yt-dlp --dump-single-json "ytsearch{n}:<query>"（download.py:110-116 逐行转录）。失败返回 []。"""
        query = track_query(track)
        try:
            p = subprocess.run(
                ["yt-dlp", "--dump-single-json", "--no-warnings", "--no-playlist", f"ytsearch{n}:{query}"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        except Exception:
            return []
        if p.returncode != 0:
            return []
        return parse_search_json(p.stdout, query)

    def fetch(self, cand: dict, dest_dir: str) -> Optional[str]:
        """yt-dlp 下载（download.py:271-282 逐行转录；-o <vid>.%(ext)s，cwd=dest_dir）。失败返回 None。"""
        vid = cand.get("id")
        if not vid:
            return None
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        try:
            stage_tpl = str(dest / f"{vid}.%(ext)s")
            webpage = cand.get("url") or f"https://www.youtube.com/watch?v={vid}"
            p = subprocess.run(
                ["yt-dlp", "--no-playlist", "--no-warnings", "--no-part", "--no-continue",
                 "-f", "bestaudio/best", "-o", stage_tpl, webpage],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=300, cwd=str(dest))
            if p.returncode != 0:
                return None
            files = dest.glob(f"{vid}.*")
            media = [f for f in files if f.suffix.lower() not in {".jpg", ".json"}]
            return str(media[0]) if media else None
        except Exception:
            return None
