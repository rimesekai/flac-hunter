"""Source 协议与统一候选 dict：跨任务公共契约，字段以本文件为准。

两个 schema（冻结契约）：

1. track dict —— cli.prepare 产出、Source.search(track) 的入参：
   - type           来源类型："spotify" 或 "qq"
   - uri            曲目 URI（spotify:track:... 或 qq:disstid 序号键）
   - name           曲名
   - artists        list[str]，歌手列表
   - album          专辑名
   - position       歌单内序号（从 1 起）
   - duration_ms    时长毫秒（int；未知为 0）
   - image_url      封面图 URL（可为 ""）
   - filename_stem  曲库落位文件名主干："<sanitize(name)> - <artists ' _ ' 连接>"
   - existing       bool，曲库已存在
   - existing_file  已存在文件绝对路径（否则 ""）
   - dedupe_reason  查重命中类型："artist" / "duration" / "same_title_other"（未命中 ""）

2. 统一候选 dict —— make_candidate 产出、search 返回、score/tier/pipeline 消费：
   - source   源名："gdstudio" / "netease" / "bili" / "youtube" / "musicdl"
   - id       源内标识（平台 id / bvid / vid 等）
   - title    标题
   - artists  list[str]，歌手/频道名
   - duration 时长（秒，float；未知为 None）
   - ext      音频扩展名（含点，如 ".flac"；未知 ""）
   - url      直链或下载页地址
   - extra    dict，源自定义字段：
       * bili    → author（频道名）、play（播放数）、bvid
       * gd      → br（码率，999999 表示无损）、size（字节数）
       * youtube → uploader（频道名）、vid（视频 id）
       * musicdl → quality（"flac" / "320" / "128" 等）
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


def make_candidate(*, source: str, id: str, title: str = "",
                   artists: list[str] | None = None,
                   duration: float | None = None,
                   ext: str = "", url: str = "",
                   extra: dict[str, Any] | None = None) -> dict:
    """构造统一候选 dict；artists/extra 做拷贝防共享可变状态。"""
    return {
        "source": source,
        "id": str(id),
        "title": title,
        "artists": list(artists) if artists else [],
        "duration": duration,
        "ext": ext,
        "url": url,
        "extra": dict(extra) if extra else {},
    }


def track_duration_s(track: dict) -> float | None:
    """track 的时长换算为秒；duration_ms 缺失、非数值或 ≤0 返回 None。"""
    ms = track.get("duration_ms")
    if isinstance(ms, (int, float)) and not isinstance(ms, bool) and ms > 0:
        return float(ms) / 1000.0
    return None


@runtime_checkable
class Source(Protocol):
    """音源协议：实现类需提供 name/lossless 属性与 search/fetch 两方法。

    - search(track)     依统一 track dict 搜索，返回统一候选 dict 列表
    - fetch(cand, dest_dir) 下载候选到目录，返回下载后文件绝对路径
    """

    name: str
    lossless: bool

    def search(self, track: dict) -> list[dict]: ...

    def fetch(self, cand: dict, dest_dir: str) -> str: ...
