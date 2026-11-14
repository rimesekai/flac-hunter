"""musicdl 包装源（pip 包 musicdl 2.14.2，PolyForm Noncommercial 1.0.0 许可，长尾音源）。

本地实测探明的真实 API（只读 site-packages 源码，绝不调用其 search/download 联网）：
- 入口：`from musicdl.musicdl import MusicClient`（musicdl/musicdl.py:46；顶层 musicdl/__init__.py
  只含元数据，`from musicdl import MusicClient` 会 ImportError——已实测）。
- 构造：MusicClient(music_sources=[], init_music_clients_cfg={}, clients_threadings={},
  requests_overrides={}, search_rules={})；默认源 DEFAULT_MUSIC_SOURCES =
  ['MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient', 'QianqianMusicClient']。
- 搜索：MusicClient.search(keyword) -> dict[str, list[SongInfo]]（musicdl/musicdl.py:106-115）。
- SongInfo 字段（musicdl/modules/utils/data.py）：song_name/singers(str)/album/ext/file_size_bytes/
  file_size/duration_s(int 秒)/duration(str)/bitrate/identifier/download_url/download_url_status['ok']/
  source/root_source/_save_path。
- 无损扩展名集合 LOSSLESS_QUALITY_DEFINITIONS = {'flac','wav','alac','ape','wv','tta','dsf','dff'}
  （musicdl/musicdl.py:47），quality 推断与其对齐。
离线铁律：模块 import 只探测可用性（AVAILABLE），绝不触发网络。
"""
from __future__ import annotations

import re
import shutil
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from ..util import download_stream
from .base import make_candidate

try:  # 本机已装 musicdl 2.14.2；缺席时优雅降级（AVAILABLE=False）
    from musicdl.musicdl import MusicClient  # noqa: F401
    AVAILABLE = True
except Exception:  # pragma: no cover - musicdl 缺席
    MusicClient = None
    AVAILABLE = False

# 与 musicdl MusicClient.LOSSLESS_QUALITY_DEFINITIONS（musicdl/musicdl.py:47）对齐
LOSSLESS_EXTS = {"flac", "wav", "alac", "ape", "wv", "tta", "dsf", "dff"}


def _norm_ext(ext: Any) -> str:
    """SongInfo.ext -> 规范化扩展名（剥前导点；"NULL"/空 -> ""）。"""
    e = str(ext or "").strip().lower().lstrip(".")
    if not e or e == "null":
        return ""
    return "." + e


def infer_quality(ext: Any, bitrate: Any = None,
                  file_size_bytes: Any = None, duration_s: Any = None) -> str:
    """按 ext/码率/尺寸推断候选 quality：flac（无损 ext）| 320 | 128。"""
    if _norm_ext(ext).lstrip(".") in LOSSLESS_EXTS:
        return "flac"
    try:
        br = int(bitrate or 0)
    except (TypeError, ValueError):
        br = 0
    if br >= 320000 or 320 <= br < 1000:  # musicdl 各 client 码率单位不一，双档判断
        return "320"
    try:  # 尺寸反推码率：size*8/dur >= 290kbps 视为 320
        fs, du = int(file_size_bytes or 0), float(duration_s or 0)
        if fs > 0 and du > 0 and fs * 8 / du >= 290_000:
            return "320"
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return "128"


def songinfo_to_candidate(info: Any, keyword: str = "") -> dict:
    """SongInfo -> 统一候选（字段来源 musicdl/modules/utils/data.py）。"""
    singers = str(getattr(info, "singers", None) or "").strip()
    artists = [p.strip() for p in re.split(r"[,，/、&]", singers) if p.strip()]
    ext = _norm_ext(getattr(info, "ext", None))
    duration = None
    try:
        if getattr(info, "duration_s", None):
            duration = float(info.duration_s)
    except (TypeError, ValueError):
        duration = None
    url = info.download_url if isinstance(getattr(info, "download_url", None), str) else None
    bitrate = getattr(info, "bitrate", None)
    quality = infer_quality(info.ext, bitrate, getattr(info, "file_size_bytes", None), duration)
    extra = {"quality": quality, "bitrate": bitrate,
             "file_size_bytes": getattr(info, "file_size_bytes", None),
             "album": getattr(info, "album", None),
             "client": getattr(info, "source", None),
             "root_source": getattr(info, "root_source", None),
             "keyword": keyword,
             "download_ok": bool((getattr(info, "download_url_status", None) or {}).get("ok"))}
    return make_candidate(
        source="musicdl", id=str(getattr(info, "identifier", None) or ""),
        title=str(getattr(info, "song_name", None) or "")[:60],
        artists=artists, duration=duration, ext=ext or None, url=url, extra=extra)


def track_query(track: dict) -> str:
    """track dict -> "歌手 歌名" 搜索词。"""
    name = str(track.get("name") or track.get("title") or "").strip()
    artists = track.get("artists") or []
    artist = str(artists[0]).strip() if artists else ""
    return f"{artist} {name}".strip()


def _default_client_factory():
    if not AVAILABLE or MusicClient is None:
        raise RuntimeError("musicdl 未安装或导入失败")
    return MusicClient()


# ---------- 多平台歌单导入（prepare --uri <平台歌单URL>，走 musicdl.parseplaylist） ----------

# 歌单解析启用的源（音乐平台优先；逐 client 试到成功为止，异常自动跳过）
_PLAYLIST_SOURCES = ("NeteaseMusicClient", "QQMusicClient", "KugouMusicClient",
                     "KuwoMusicClient", "MiguMusicClient", "QianqianMusicClient",
                     "BilibiliMusicClient", "SodaMusicClient")


def songinfo_to_track(info: Any) -> dict:
    """musicdl SongInfo -> 统一 track schema（歌单导入用，不走下载候选）。"""
    singers = str(getattr(info, "singers", "") or "")
    artists = [p.strip() for p in re.split(r"[,，/、&]", singers) if p.strip()]
    try:
        duration_ms = int(getattr(info, "duration_s", 0) or 0) * 1000 or None
    except (TypeError, ValueError):
        duration_ms = None
    return {
        "uri": f"musicdl:{getattr(info, 'identifier', '') or ''}",
        "name": str(getattr(info, "song_name", "") or ""),
        "artists": artists,
        "album": str(getattr(info, "album", "") or "") or None,
        "duration_ms": duration_ms,
        "image_url": None,
    }


# musicdl 的 parseplaylist 部分平台实现会无限挂起（实测 netease 端点 2026-11 已失效：
# 带 #/ 的 URL 挂死、纯 URL 返回 0 首）。守护线程 + 截止时间硬性兜底，绝不拖死 CLI。
_PLAYLIST_TIMEOUT_S = 90.0


def parse_playlist(url: str, timeout: float = _PLAYLIST_TIMEOUT_S) -> list:
    """多平台歌单 URL -> 统一 track 列表；musicdl 缺席/超时/解析失败一律返回 []。

    注意：网易云/QQ/B站请优先走直连入口（netease:<id> / qq:<disstid> / bili:fav:<media_id>，
    cli 会把已知平台的 http URL 自动路由过去）；本入口仅兜 musicdl 独有平台。
    """
    if not AVAILABLE:
        return []
    holder = []

    def _run():
        try:
            client = MusicClient(music_sources=list(_PLAYLIST_SOURCES))
            holder.append(client.parseplaylist(url) or [])
        except Exception:
            holder.append([])

    th = threading.Thread(target=_run, daemon=True)
    th.start()
    th.join(timeout)
    if not holder:  # 超时：守护线程随进程退出销毁，这里直接判失败
        return []
    out = []
    for info in holder[0]:
        try:
            t = songinfo_to_track(info)
            if t["name"]:
                out.append(t)
        except Exception:
            continue
    return out


class MusicDlSource:
    """musicdl 长尾源：client 搜索 -> 统一候选；AVAILABLE=False 或任何异常一律降级为空结果。"""

    name = "musicdl"
    lossless = False  # 类属性保守 False；候选级 lossless 看 extra.quality=='flac'

    def __init__(self, cfg: Optional[dict] = None, client_factory: Optional[Callable] = None):
        self.cfg = cfg or {}
        self._client_factory = client_factory or _default_client_factory
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def search(self, track: dict) -> list:
        """对 (title, artists) 构造 keyword 调 client.search；任何异常（含 factory 抛错）返回 [] 绝不抛出。"""
        try:
            if not AVAILABLE and self._client_factory is _default_client_factory:
                return []
            client = self._ensure_client()
            keyword = track_query(track)
            if not keyword:
                return []
            results = client.search(keyword) or {}
            out = []
            for infos in results.values():
                for info in infos or []:
                    try:
                        out.append(songinfo_to_candidate(info, keyword))
                    except Exception:
                        continue
            return out
        except Exception:
            return []

    def fetch(self, cand: dict, dest_dir: str) -> Optional[str]:
        """有直链走 util.download_stream；否则按 musicdl 自身 download 逻辑。失败返回 None。"""
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        try:
            extra = cand.get("extra") or {}
            ext = _norm_ext(cand.get("ext")) or ".mp3"
            stem = extra.get("filename_stem") or f"musicdl_{cand.get('id') or 'unknown'}"
            url = cand.get("url")
            if isinstance(url, str) and url.startswith("http"):
                out = dest / f"{stem}{ext}"
                download_stream(url, str(out), timeout=300)
                return str(out)
            # 无直链：按 musicdl 自身 download 逻辑（SongInfo 透传，落盘后搬到 dest_dir）
            if not AVAILABLE and self._client_factory is _default_client_factory:
                return None
            from musicdl.musicdl import SongInfo  # musicdl/modules/utils/data.py
            duration_s = None
            try:
                duration_s = int(cand["duration"]) if cand.get("duration") else None
            except (TypeError, ValueError):
                duration_s = None
            info = SongInfo(
                source=extra.get("client"),
                song_name=str(cand.get("title") or ""),
                singers=", ".join(cand.get("artists") or []),
                ext=_norm_ext(cand.get("ext")) or None,
                file_size_bytes=extra.get("file_size_bytes"),
                duration_s=duration_s,
                identifier=str(cand.get("id") or ""),
                download_url=url,
                download_url_status=extra.get("download_url_status") or {},
                work_dir=str(dest),
            )
            got = self._ensure_client().download([info]) or []
            for gi in got:
                sp = getattr(gi, "_save_path", None) or getattr(gi, "save_path", None)
                if not sp or not Path(sp).exists():
                    continue
                target = dest / Path(sp).name
                if Path(sp).resolve() != target.resolve():
                    shutil.move(sp, target)  # 跨盘必须 shutil.move
                return str(target)
            return None
        except Exception:
            return None
