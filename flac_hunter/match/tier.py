"""匹配层 A/B/C/C2 分档（纯函数，无网络无 IO）。

逐行转录蓝本：norm_dur = hunt_last3.py:130-140；tier_of = hunt_last3.py:186-197；
SEARCH_WIN/B_HIGH 常量 = hunt_last3.py:39,41（与 config [match] search_win/verify_win 语义一致）。
候选 cand 为 sources.base.make_candidate 统一字段：歌名取 title、歌手取 '/'.join(artists)、
时长取 duration（秒，None 即无时长）；蓝本参考实现的 name/artist/dur 字段在模块内适配。
"""
from .normalize import artist_related, name_related, name_similar

SEARCH_WIN = 8.0  # A 档搜索匹配窗
B_HIGH = 15.0     # C 档上限

# 档序：A（唯一允许写入）< B < C < C2
_TIER_ORDER = {"A": 0, "B": 1, "C": 2, "C2": 3}


def norm_dur(raw) -> "float | None":
    """归一化时长：netease 多为毫秒，tencent interval / kuwo 为秒，>2000 视为毫秒；空/0/非法→None（hunt_last3.py:130-140）。"""
    if raw in (None, "", 0, "0"):
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return v / 1000.0 if v > 2000 else v


def tier_of(
    cand: dict,
    sdur,
    want_name: str,
    aliases,
    name_aliases,
    *,
    search_win: float = SEARCH_WIN,
    b_high: float = B_HIGH,
) -> "str | None":
    """A=±8s 且歌手相关且歌名相关（唯一允许写入档）；B=±8s 但歌手/歌名不符；
    C=8~15s 且歌名相似；C2=无时长且歌名相关且歌名相似。B/C/C2 仅作疑似线索，不写入（防硬凑）。
    当 sdur 为 None 或 <=0 时不作时长差 0.0 假定，改按歌手与歌名相关性判 A/B/None。"""
    cand_name = cand.get("title") or ""
    cand_artist = "/".join(cand.get("artists") or [])
    cand_dur = cand.get("duration")
    name_ok = name_related(cand_name, name_aliases)
    if cand_dur is None:
        return "C2" if (name_ok and name_similar(cand_name, want_name)) else None
    if sdur is None or sdur <= 0:
        if artist_related(cand_artist, aliases) and name_ok:
            return "A"
        return "B" if name_ok else None
    d = abs(cand_dur - sdur)
    if d <= search_win:
        return "A" if (artist_related(cand_artist, aliases) and name_ok) else "B"
    if d <= b_high and name_similar(cand_name, want_name):
        return "C"
    return None


def tier_sort_key(cand: dict, tier, sdur=None) -> tuple:
    """候选排序键：档序 A<B<C<C2，同档按 |duration−sdur| 升序；tier 为 None 排最后，
    同档内时长未知排最后。sdur 可选（秒）：调用方便于传入时给准，缺省或<=0 时长差按未知处理。"""
    rank = _TIER_ORDER.get(tier, len(_TIER_ORDER))
    dur = cand.get("duration")
    if dur is None or sdur is None or sdur <= 0:
        diff = float("inf")
    else:
        diff = abs(dur - sdur)
    return (0 if tier else 1, rank, diff)
