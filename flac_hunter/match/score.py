"""匹配层打分与选优（纯函数，无网络无 IO）。

逐行转录蓝本：score_youtube/pick = download.py:119-192；score_bili = download_bili.py:225-303；
低置信判定 = download_bili.py:406-413；三段式查询计划 = download_bili.py:384-403（只产出计划不执行搜索）。

候选 dict 一律使用 sources.base.make_candidate 统一字段（source/id/title/artists/duration/
ext/url/extra）；蓝本参考实现的 name/artist/dur/channel/play 字段在模块内部适配：
频道名 = cand["channel"] or extra["author"]，播放量 = extra["play"]。
"""
import math
import re

from .blacklist import BILI_BAD, EDGE_WORDS, has_bad_version
from .normalize import (
    alt_titles_for,
    artist_variants,
    contains_variant,
    loose_bili,
    norm_bili,
    norm_text,
    romaji_fold,
)

# 与 config [aliases] no_picks 一致的永拒视频（download_bili.py:84-86）
NO_PICKS = {"BV1mTaQ63Ek3"}

# B站高音质标签加分词（download_bili.py:114）
GOOD_TAGS = ["hi-res", "hires", "hdr", "4k", "无损", "flac", "高音质", "高品质"]


def _cand_channel(cand: dict) -> str:
    """统一候选的频道名：channel 字段或 extra.author（蓝本 cand["channel"]）。"""
    return cand.get("channel") or (cand.get("extra") or {}).get("author") or ""


def _cand_play(cand: dict) -> int:
    """统一候选的播放量 extra.play；缺失/非数值按 0（蓝本 cand.get("play")）。"""
    play = (cand.get("extra") or {}).get("play")
    try:
        return int(play)
    except (TypeError, ValueError):
        return 0


def score_bili(track: dict, cand: dict, alts=None, other_artists=None) -> float:
    """B站候选打分（逐行转录 download_bili.py:225-303，适配统一候选字段）。

    track：prepare 产出曲目 dict（name/artists/duration_ms/album）。
    other_artists：调用方传入的「已归一化歌单艺人变体集合」（playlist_artists 语义，
    artist_variants 展开并集且已剔虚拟歌手与当前 track 自身变体），本函数直接使用、
    不再归一（蓝本 download_bili.py:267-269 直接 o in loose_title）。
    返回浮点分值（蓝本实现即为浮点累加）。
    """
    if cand.get("id") in NO_PICKS:
        return -999
    names = [norm_bili(track["name"])] + [norm_bili(a) for a in (alts or [])]
    title = norm_bili(cand.get("title"))
    channel = norm_bili(_cand_channel(cand))
    sdur = (track.get("duration_ms") or 0) / 1000
    dur = cand.get("duration") or 0
    s = 0.0

    raw = (cand.get("title") or "").lower()
    sn = track["name"].lower()
    for w in BILI_BAD:
        if w in raw and w not in sn:
            return -999

    title_score = 0.0
    matched_name = names[0] if names else ""
    for name in names:
        if not name:
            continue
        local = 0.0
        if name in title:
            local = 50.0
        else:
            toks = set(name.split())
            local = 35 * len(toks & set(title.split())) / max(len(toks), 1)
        n2, t2 = romaji_fold(name), romaji_fold(title)
        if n2 and n2 in t2:
            local = max(local, 45.0)
        if local > title_score:
            title_score, matched_name = local, name
    s += title_score

    variants = artist_variants(track["artists"][0]) if track["artists"] else set()
    loose_title = loose_bili(cand.get("title"))
    artist_in_title = any(loose_bili(v) in loose_title for v in variants)
    artist_in_channel = any(contains_variant(channel, v) for v in variants)
    if artist_in_title:
        s += 18
    if artist_in_channel:
        s += 30
    others = other_artists or set()
    if any(o in loose_title or o in channel for o in others):
        s -= 60
    if not (artist_in_title or artist_in_channel):
        cjk = re.search(r"[\u3040-\u30ff\u3400-\u9fff]", matched_name)
        distinctive = (cjk and len(matched_name.replace(" ", "")) >= 7) or len(matched_name.split()) >= 3
        s -= 10 if distinctive else 30
        if not distinctive and len(matched_name.split()) <= 2:
            s -= 20
    # 点赞曲明确是 cover 时，候选必须出现覆盖艺人（download_bili.py:276-278）
    if "cover" in (track["name"] + " " + (track.get("album") or "")).lower() and not (artist_in_title or artist_in_channel):
        return -999
    if re.search(r"official|官方|公式", channel):
        s += 10
    if any(t in raw for t in GOOD_TAGS):
        s += 8
    play = _cand_play(cand)
    if play:
        s += min(8.0, math.log10(play + 1) * 2)

    if sdur and dur:
        diff = abs(sdur - dur)
        if diff <= 3:
            s += 25
        elif diff <= 8:
            s += 15
        elif diff <= 15:
            s += 5
        elif diff <= 30:
            s -= 10
        elif diff <= 60:
            s -= 30
        else:
            s -= 50

    if play < 1000:
        s -= 10
    return s


def bili_low_confidence(score: float, cand: dict, track: dict) -> bool:
    """分数<55 或时长差>60 → 不可信（转录 download_bili.py:406-413）。"""
    sdur = (track.get("duration_ms") or 0) / 1000
    diff = abs(sdur - (cand.get("duration") or 0)) if sdur else 0.0
    return bool(score < 55 or (sdur and diff > 60))


def score_youtube(cand: dict, track: dict) -> float:
    """YouTube 候选打分（逐行转录 download.py:119-179，适配统一候选字段；注意参数序为 cand, track）。"""
    name = norm_text(track["name"])
    artist = norm_text(track["artists"][0]) if track["artists"] else ""
    raw_title = cand.get("title") or ""
    title = norm_text(raw_title)
    channel = norm_text(cand.get("channel") or (cand.get("extra") or {}).get("author")
                        or (cand.get("extra") or {}).get("uploader") or "")
    dur = cand.get("duration") or 0
    sdur = (track.get("duration_ms") or 0) / 1000
    s = 0.0

    if has_bad_version(raw_title, track["name"]):
        return -999

    if name and name in title:
        s += 50
    elif name:
        toks = set(name.split())
        hit = len(toks & set(title.split()))
        s += 35 * hit / max(len(toks), 1)
    # 罗马音标题（Kaijuu -> Kaiju 等）
    n2, t2 = romaji_fold(name), romaji_fold(title)
    if n2 and n2 in t2:
        s = max(s, 45)

    variants = artist_variants(track["artists"][0]) if track["artists"] else set()
    if any(contains_variant(title, v) for v in variants):
        s += 18
    channel_tokens = set(channel.split())
    strong_channel = any(channel == v or channel.startswith(v + " ") or v in channel_tokens for v in variants)
    if strong_channel:
        s += 40
    elif any(contains_variant(channel, v) for v in variants):
        s += 12
    if channel.endswith("topic"):
        s += 15
    if re.search(r"가사|lyrics?|歌詞|歌词|lyric", raw_title, re.I) or re.search(r"가사|lyrics?|歌詞|歌词|lyric", channel):
        s -= 15
    for a in track["artists"][1:3]:
        if norm_text(a) in title:
            s += 4

    if sdur and dur:
        diff = abs(sdur - dur)
        if diff <= 3:
            s += 25
        elif diff <= 8:
            s += 15
        elif diff <= 15:
            s += 5
        elif diff <= 30:
            s -= 10
        elif diff <= 60:
            s -= 30
        else:
            s -= 50

    for w in EDGE_WORDS:
        if w in title:
            s -= 4

    return s


def pick_best(cands, track: dict, score_fn):
    """选优（转录 download.py:182-192 pick）：分数高者优先，平分时长差小者优先；无候选返回 None。

    score_fn 调用约定为 score_fn(track, cand)；score_youtube 参数序相反，调用方用
    lambda c, t: score_youtube(c, t) 适配。返回最优候选 dict（蓝本另返回分值，接口
    冻结为仅返回候选，分值由调用方复算）。
    """
    if not cands:
        return None
    sdur = (track.get("duration_ms") or 0) / 1000
    scored = sorted(
        ((score_fn(track, c), c) for c in cands),
        key=lambda x: (x[0], -(abs(sdur - (x[1].get("duration") or 0)) if sdur else 0)),
        reverse=True,
    )
    return scored[0][1]


def plan_search_queries(track: dict, alt_entries):
    """三段式查询计划（转录 download_bili.py:384-403 的查询展开，只产出计划不执行搜索）。

    首搜「艺人 歌名」→ alt_titles_for 取别名，每个别名出「艺人 别名」与裸别名两条 →
    仍不够时纯艺人名搜 3 页。调用方按序执行、可在分数达标后提前停止后续阶段。
    返回 [(query, pages), ...]。
    """
    queries = []
    artists = track.get("artists") or []
    artist0 = artists[0] if artists else ""
    name = track.get("name") or ""
    if artist0 and name:
        queries.append((f"{artist0} {name}", 1))
    alts = alt_titles_for(name, artist0, alt_entries or [])
    for a in alts:
        if artist0:
            queries.append((f"{artist0} {a}", 1))
        queries.append((a, 1))
    if artist0:
        queries.append((artist0, 3))
    return queries
