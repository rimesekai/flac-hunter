"""flac-hunter：本地私有音乐无损下载/曲库管理 CLI。

包地图：
- config      配置加载（tomllib 读 config.toml，缺失回退全默认）
- console     控制台输出（UTF-8、时间戳日志、宽字符截断）
- util        通用工具（HTTP、下载流、多编码读文本、跨盘移动）
- match       匹配层（normalize 归一化 / blacklist 词表 / score 打分 / tier 分档）
- sources     音源适配（base 协议 + gdstudio/netease/bilibili/youtube/musicdl/lrclib）
- pipeline    下载编排（选源、下载、验证、sidecar、落位）
- upgrade     旧文件无损升级
- audit       质量门与歌词体检
- spotify_cli spotify_cli.exe 与 QQ 歌单元数据
- library     本地曲库扫描与查重
- ffmpeg      ffprobe 探测 / remux / 转码 / 指纹
"""

__version__ = "0.1.0"
