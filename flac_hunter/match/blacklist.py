"""匹配层黑名单词表与判定函数（纯数据 + 纯函数，无网络无 IO）。

逐词转录蓝本：BAD_WORDS/EDGE_WORDS/ARTIST_ALIASES/has_bad_version = download.py:29-52,86-97；
BILI_BAD/VIRTUAL_SINGERS = download_bili.py:37-48,89-94；
VERSION_MARKERS/is_cover_like = prepare.py:25-28,71-78。
计数勘误口径（领队 AST 实测）：BAD_WORDS=42、BILI_BAD=81、VIRTUAL_SINGERS=24、VERSION_MARKERS=22。
"""
import re
from pathlib import Path

# 候选标题坏词：命中且点赞曲名本身不含 → 拒（download.py:29-36，42 词）
BAD_WORDS = [
    "cover", "covered", "カバー", "歌って", "歌ってみた", "弾いてみた", "弾き語り", "live", "ライブ", "remix", "リミックス",
    "instrumental", "off vocal", "offvocal", "カラオケ", "karaoke", "nightcore", "8d",
    "sped up", "slowed", "reverb", "mashup", "マッシュアップ", "piano ver", "acoustic ver",
    "acoustic version", "reaction", "解説", "切り抜き", "tutorial", "lesson",
    "8bit", "8-bit", "ファミコン", "arrange", "rearrange", "アレンジ", "replica",
    "オルゴール", "music box", "オーケストラ", "orchestra",
]

# 边缘词：YouTube 打分轻度降分（download.py:37）
EDGE_WORDS = ["mv", "music video", "official video", "lyric video", "ショート", "short"]

# B站候选坏词：命中且点赞曲名不含 → -999（download_bili.py:37-48，81 词）
BILI_BAD = [
    "翻唱", "翻自", "歌ってみた", "covered", "cover", "现场", "live", "演唱会", "ライブ",
    "伴奏", "纯音乐", "off vocal", "offvocal", "カラオケ", "卡拉ok", "karaoke",
    "鼓谱", "琴谱", "tab谱", "tab", "教学", "翻弹", "钢琴", "8bit", "8-bit", "remix", "混音",
    "剪辑", "amv", "mmd", "光遇", "投屏", "合集", "reaction", "解说", "切片", "replica",
    "arrange", "アレンジ", "オルゴール", "music box", "acoustic ver", "piano ver",
    "弾いてみた", "ギター", "guitar", "bass", "ベース", "吉他", "贝斯", "扒谱", "教程",
    "试音", "音箱", "音响", "diy", "ニコカラ", "オフボーカル",
    "ピアノ", "楽譜", "piano", "翻弾", "歌いたい", "重音", "鼓童", "ongeki", "太鼓",
    "踊ってみた", "踊り", "翻跳", "dance cover", "乐谱", "譜面", "ドラム", "drum",
    "教会", "三分钟", "原琴", "演奏", "cover by", "covered by",
]

# 版本词：core_key 保留含这些词的括号段（prepare.py:25-28，22 项）
VERSION_MARKERS = ("ver", "version", "remix", "live", "acoustic", "instrumental",
                   "offvocal", "off vocal", "cover", "edit", "mix", "remaster",
                   "demo", "karaoke", "sped", "slowed", "nightcore", "size",
                   "movie", "tv", "short", "inst")

# 虚拟歌手名：歌单艺人池剔除用（download_bili.py:89-94，24 词）
VIRTUAL_SINGERS = {
    "ia", "初音未来", "初音ミク", "hatsunemiku", "miku", "鏡音リン", "鏡音レン", "kagamine",
    "flower", "vflower", "可不", "重音テト", "重音", "gumi", "巡音ルカ", "luka", "meiko",
    "kaito", "moremorejump", "桐谷遥", "桃井愛莉",
    "cevio", "歌愛ユキ", "galaco",
}

# 同一艺人不同写法/译名分组：download.py:40-52 的 11 组 + download_bili.py:140-144 追加 3 组 = 14 组
ARTIST_ALIAS_GROUPS = [
    {"sakanaction", "魚韻"},
    {"yohkamiyama", "神山羊"},
    {"rokudenashi", "ロクデナシ"},
    {"suisoh", "水槽"},
    {"moumoon", "沐月"},
    {"mary", "めありー"},
    {"rim", "理芽"},
    {"kaf", "花譜"},
    {"isekaijoucho", "ヰ世界情緒"},
    {"vwp", "v.w.p"},
    {"inoriminase", "水瀬いのり", "水瀨祈"},
    {"baishajaws", "白鲨jaws"},
    {"jin", "じん"},
    {"rinu", "莉犬", "りぬ"},
]


def is_cover_like(filename: str) -> bool:
    """翻唱/BV 投稿类文件名：禁止仅按时长判重（prepare.py:71-78）。"""
    stem = Path(filename).stem
    if re.search(r"BV[0-9A-Za-z]{8,}", stem):
        return True
    if re.search(r"cover|歌ってみた|翻唱|翻自|弾いてみた|指弹|伴奏|off ?vocal|instrumental", stem, re.I):
        return True
    return stem.startswith("【")


def has_bad_version(title: str, liked_name: str) -> bool:
    """拒绝 live/cover/remix 等版本，除非点赞曲名本身含该词；纯 ASCII 词按整词边界匹配（download.py:86-97）。"""
    t, s = (title or "").lower(), (liked_name or "").lower()
    for w in BAD_WORDS:
        if w not in t or w in s:
            continue
        if re.fullmatch(r"[a-z ]+", w):
            if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t):
                return True
        else:
            return True
    return False
