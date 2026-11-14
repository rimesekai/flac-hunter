"""匹配层文本归一化纯函数。

逐行转录蓝本：download.py:55-102、download_bili.py:117-155、prepare.py:43-68、
hunt_last3.py:143-183。无网络无 IO；除同级 blacklist 外只 import 标准库，
别名/词表数据可经参数传入，缺省用本包 blacklist 内置表。
"""
import re
import unicodedata

from .blacklist import ARTIST_ALIAS_GROUPS, VERSION_MARKERS

# 装饰斜杠(U+29F8)与全角斜杠(U+FF0F)按分隔符处理（brief 对蓝本的补充）
EXTRA_SEPS = "⧸／"

# 繁→简字面映射对（download_bili.py:117-133，约 90 对，首对为双字词）
_T2S_PAIRS = [
    ("魚鱗", "鱼鳞"), ("雲", "云"), ("龍", "龙"), ("夢", "梦"), ("愛", "爱"), ("戀", "恋"),
    ("時", "时"), ("間", "间"), ("風", "风"), ("聲", "声"), ("樂", "乐"), ("團", "团"),
    ("園", "园"), ("變", "变"), ("讓", "让"), ("說", "说"), ("話", "话"), ("語", "语"),
    ("讀", "读"), ("車", "车"), ("門", "门"), ("關", "关"), ("開", "开"), ("見", "见"),
    ("現", "现"), ("實", "实"), ("學", "学"), ("覺", "觉"), ("聽", "听"), ("從", "从"),
    ("來", "来"), ("這", "这"), ("麼", "么"), ("樣", "样"), ("誰", "谁"), ("為", "为"),
    ("對", "对"), ("錯", "错"), ("還", "还"), ("過", "过"), ("經", "经"), ("給", "给"),
    ("與", "与"), ("會", "会"), ("個", "个"), ("們", "们"), ("無", "无"), ("數", "数"),
    ("處", "处"), ("長", "长"), ("萬", "万"), ("億", "亿"), ("點", "点"), ("電", "电"),
    ("際", "际"), ("紅", "红"), ("綠", "绿"), ("藍", "蓝"), ("黃", "黄"), ("鳥", "鸟"),
    ("島", "岛"), ("灣", "湾"), ("邊", "边"), ("遠", "远"), ("進", "进"), ("運", "运"),
    ("動", "动"), ("場", "场"), ("陽", "阳"), ("陰", "阴"), ("霧", "雾"), ("華", "华"),
    ("葉", "叶"), ("樹", "树"), ("鯊", "鲨"), ("貝", "贝"), ("殼", "壳"), ("鳳", "凤"),
    ("龜", "龟"), ("齒", "齿"), ("腦", "脑"), ("臉", "脸"), ("頭", "头"), ("髮", "发"),
    ("淚", "泪"), ("寫", "写"), ("詩", "诗"), ("傷", "伤"), ("憶", "忆"), ("願", "愿"),
]
T2S = {}
for _a, _b in _T2S_PAIRS:
    for _ca, _cb in zip(_a, _b):
        T2S[ord(_ca)] = _cb


def norm_text(s: str) -> str:
    """NFKC→lower→剥括号段→去 feat/ft/featuring 及其后→仅保留数字/字母/假名/汉字→空格折叠（download.py:71-76）。"""
    s = s or ""
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"\(.*?\)|\[.*?\]|【.*?】|（.*?）", " ", s)
    s = re.sub(r"\b(feat|ft|featuring)\.?\b.*$", " ", s)
    s = re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]+", " ", s)
    return " ".join(s.split())


def romaji_fold(s: str) -> str:
    """罗马音长音折叠 ou→o/uu→u/oo→o/aa→a/ii→i/ee→e，让 Kaijuu 匹配 Kaiju（download.py:79-83）。"""
    s = s or ""
    for a, b in (("ou", "o"), ("uu", "u"), ("oo", "o"), ("aa", "a"), ("ii", "i"), ("ee", "e")):
        s = s.replace(a, b)
    return s


def contains_variant(text: str, v: str) -> bool:
    """≤4 字符的 ASCII 词整词匹配，防 rim 撞 pilgrim；其余普通子串（download.py:55-58）。"""
    text = text or ""
    if len(v) <= 4 and v.isascii():
        return re.search(r"(?<![a-z])" + re.escape(v) + r"(?![a-z])", text) is not None
    return v in text


def artist_variants(name: str, alias_groups=None) -> set:
    """艺人归一变体并集：自身归一 + 命中的别名组整组并入（download.py:61-68）；缺省用 blacklist.ARTIST_ALIAS_GROUPS。"""
    base = norm_text(name)
    out = {base}
    for group in (ARTIST_ALIAS_GROUPS if alias_groups is None else alias_groups):
        ng = {norm_text(x) for x in group}
        if base in ng:
            out |= ng
    return {x for x in out if x}


def nk(s: str) -> str:
    """对比键归一（prepare.py:43-49）：lower、剥 explicit/feat 括注、非法字符→_、仅保留数字/字母/假名/汉字。"""
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"\((explicit|feat\.?[^)]*)\)|\[explicit\]", "", s)
    s = re.sub(r"[\\/:*?\"<>|]", "_", s)
    s = re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]+", "", s)
    return s


def core_key(s: str) -> str:
    """标题核心键：逐括号判断，含版本词(VERSION_MARKERS)的括号保留、其余剥掉，再压 nk 键（prepare.py:59-68）。"""
    s = unicodedata.normalize("NFKC", s)

    def _repl(m):
        inner = m.group(1).lower()
        return m.group(0) if any(v in inner for v in VERSION_MARKERS) else " "

    s = re.sub(r"[\(\[（【]([^\)\]）】]*)[\)\]）】]", _repl, s)
    return nk(s)


def t2s(s: str) -> str:
    """繁体→简体字面映射（download_bili.py:117-137 的映射表 + 147-148 用法）。"""
    return (s or "").translate(T2S)


def norm_bili(s: str) -> str:
    """B站标题归一：先繁转简再 norm_text（download_bili.py:147-148）。"""
    return norm_text(t2s(s))


def loose_bili(s: str) -> str:
    """B站宽松归一：繁转简→NFKC lower→仅保留数字/字母/假名/汉字；不去括号、【】内文本保留（download_bili.py:151-155）。"""
    s = t2s(s)
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]+", "", s)


def name_core(s: str) -> str:
    """歌名核心：去空白/括号类/间隔号及装饰·全角斜杠后 lower（hunt_last3.py:143-144 + 斜杠补充）。"""
    return re.sub(r"[\s（）()（）\[\]【】・·⧸／]", "", s or "").lower()


def name_similar(a: str, b: str) -> bool:
    """双方 name_core 非空才比较：相等或双向子串（hunt_last3.py:147-151，防空串陷阱）。"""
    ca, cb = name_core(a), name_core(b)
    if not ca or not cb:
        return False
    return ca == cb or ca in cb or cb in ca


def artist_related(cand_artist: str, aliases) -> bool:
    """候选歌手与目标歌手（含别名）是否相关：整串含任一别名，或按 ,，/、& 与 ⧸／ 拆分后每段双向子串（hunt_last3.py:154-166）。"""
    a = (cand_artist or "").lower()
    if not a:
        return False
    for alt in aliases or ():
        if alt.lower() in a:
            return True
    for part in re.split(r"[,，/、&⧸／]", cand_artist or ""):
        p = part.strip().lower()
        if p and any(p in alt.lower() or alt.lower() in p for alt in aliases or ()):
            return True
    return False


def name_related(cand_name: str, name_aliases) -> bool:
    """候选歌名与目标歌名（含罗马音/汉字别名，core 后双向子串）是否相关（hunt_last3.py:174-183）。"""
    c = name_core(cand_name)
    if not c:
        return False
    for alt in name_aliases or ():
        a = name_core(alt)
        if a and (a in c or c in a):
            return True
    return False


def sanitize(s: str) -> str:
    """Windows 文件名清洗：非法字符→下划线，strip 后去尾部点（download.py:100-102）。"""
    s = re.sub(r'[\\/:*?"<>|]', "_", s or "")
    return s.strip().rstrip(".")


def cfg_alias_groups(cfg) -> "list[set[str]]":
    """合并内置 ARTIST_ALIAS_GROUPS 与 cfg.aliases.art_aliases（兼容 Config dataclass、dict 与 None）。"""
    groups = [set(g) for g in ARTIST_ALIAS_GROUPS]
    if cfg is None:
        return groups
    aliases = cfg.get("aliases") if isinstance(cfg, dict) else getattr(cfg, "aliases", None)
    if aliases is None:
        return groups
    raw = aliases.get("art_aliases") if isinstance(aliases, dict) else getattr(aliases, "art_aliases", None)
    if isinstance(raw, dict):
        for k, vs in raw.items():
            items = [k]
            if isinstance(vs, (list, tuple, set)):
                items.extend(vs)
            elif vs:
                items.append(vs)
            clean = {str(x).strip() for x in items if x is not None and str(x).strip()}
            if clean:
                groups.append(clean)
    elif isinstance(raw, (list, tuple, set)):
        for g in raw:
            if isinstance(g, (list, tuple, set)):
                clean = {str(x).strip() for x in g if x is not None and str(x).strip()}
                if clean:
                    groups.append(clean)
    return groups


def _artist_alias_match(artist: str, entry_artist: str, alias_groups=None) -> bool:
    """条目艺人与目标艺人相关：变体并集相交，或双向 artist_related。"""
    va = artist_variants(artist, alias_groups=alias_groups)
    ve = artist_variants(entry_artist, alias_groups=alias_groups)
    return bool(va & ve) or artist_related(entry_artist, va) or artist_related(artist, ve)


def alt_titles_for(title: str, artist: str, alt_entries, alias_groups=None) -> list:
    """按 config [aliases] alt_titles 条目取别名表（download_bili.py:51-69 ALT_TITLES 的 config 化）。

    条目命中条件：norm_text(title) 与条目 title 归一相等（或互为 name_similar），
    且条目 artist 为空或与目标艺人相关；返回条目 alts 列表（可多条目合并）。
    """
    out = []
    nt = norm_text(title)
    for e in alt_entries or ():
        et = norm_text(e.get("title") or "")
        if not nt or not et or not (nt == et or name_similar(nt, et)):
            continue
        ea = (e.get("artist") or "").strip()
        if ea and not _artist_alias_match(artist, ea, alias_groups=alias_groups):
            continue
        out.extend(e.get("alts") or [])
    return out
