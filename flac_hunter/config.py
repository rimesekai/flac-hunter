"""配置加载：tomllib 读 config.toml；文件缺失或损坏时回退全默认，绝不抛错。"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# 仓库根 = flac_hunter 包所在目录的上一级；缺省配置即仓库根 config.toml
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.toml"


@dataclass
class Paths:
    """路径配置（music/staging 可为相对路径，相对当前工作目录）。"""

    music: str = "music"
    staging: str = "staging"
    spotify_cli: str = ""


@dataclass
class Rate:
    """限速配置：各音源最小请求间隔与每曲间隔（秒）。"""

    gd_min_interval: float = 1.05
    per_track_sleep: float = 1.0
    lrclib_min_interval: float = 0.5
    netease_min_interval: float = 0.5


@dataclass
class MatchCfg:
    """匹配配置：搜索时长窗 / 验证时长窗 / B站候选最低分。"""

    search_win: float = 8.0
    verify_win: float = 15.0
    min_video_score: float = 55.0


@dataclass
class Aliases:
    """别名配置：艺人别名组、曲名别名、内置表补充与人工名单。"""

    art_aliases: dict[str, list[str]] = field(default_factory=dict)
    alt_titles: list[dict] = field(default_factory=list)
    virtual_singers: list[str] = field(default_factory=list)
    manual_picks: list[str] = field(default_factory=list)
    no_picks: list[str] = field(default_factory=list)
    permanent_skip: list[str] = field(default_factory=list)


@dataclass
class Config:
    """配置聚合对象，属性与 config.toml 顶层表一一对应。"""

    paths: Paths = field(default_factory=Paths)
    rate: Rate = field(default_factory=Rate)
    match: MatchCfg = field(default_factory=MatchCfg)
    aliases: Aliases = field(default_factory=Aliases)


def _str_map(section: dict, keys: tuple[str, ...], obj: object) -> None:
    """把 section 内指定 str 字段覆盖到 dataclass，非 str 值忽略。"""
    for k in keys:
        v = section.get(k)
        if isinstance(v, str):
            setattr(obj, k, v)


def _num_map(section: dict, keys: tuple[str, ...], obj: object) -> None:
    """把 section 内指定数值字段覆盖到 dataclass，保留 int/float 原类型，非数值忽略。"""
    for k in keys:
        v = section.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            setattr(obj, k, v)


def load_config(path: str | Path | None = None) -> Config:
    """读取配置；path 为 None 时默认仓库根 config.toml。

    文件不存在、损坏（TOML 解析失败）或字段类型不符时，对应字段保持默认，不抛错。
    """
    cfg = Config()
    p = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    try:
        with open(p, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return cfg

    paths = data.get("paths")
    if isinstance(paths, dict):
        _str_map(paths, ("music", "staging", "spotify_cli"), cfg.paths)

    rate = data.get("rate")
    if isinstance(rate, dict):
        _num_map(rate, ("gd_min_interval", "per_track_sleep",
                          "lrclib_min_interval", "netease_min_interval"), cfg.rate)

    match = data.get("match")
    if isinstance(match, dict):
        _num_map(match, ("search_win", "verify_win", "min_video_score"), cfg.match)

    aliases = data.get("aliases")
    if isinstance(aliases, dict):
        aa = aliases.get("art_aliases")
        if isinstance(aa, dict):
            art: dict[str, list[str]] = {}
            for k, v in aa.items():
                if isinstance(k, str) and isinstance(v, list):
                    items = [x for x in v if isinstance(x, str)]
                    if items:
                        art[k] = items
            cfg.aliases.art_aliases = art
        at = aliases.get("alt_titles")
        if isinstance(at, list):
            rows: list[dict] = []
            for row in at:
                if not isinstance(row, dict):
                    continue
                title, artist = row.get("title"), row.get("artist")
                alts = row.get("alts")
                if isinstance(title, str) and isinstance(artist, str) and isinstance(alts, list):
                    alt_items = [x for x in alts if isinstance(x, str)]
                    if alt_items:
                        rows.append({"title": title, "artist": artist, "alts": alt_items})
            cfg.aliases.alt_titles = rows
        for k in ("virtual_singers", "manual_picks", "no_picks", "permanent_skip"):
            v = aliases.get(k)
            if isinstance(v, list):
                setattr(cfg.aliases, k, [x for x in v if isinstance(x, str)])

    return cfg
