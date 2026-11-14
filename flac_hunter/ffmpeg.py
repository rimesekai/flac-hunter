"""ffmpeg/ffprobe 封装：时长/元数据探测、FLAC remux、MP3 320 转码、无损改标签、PCM 指纹。

蓝本：prepare.py:86-93、verify_duration_first.py:60-70、verify_kaisei.py:27-32、
rename_apply.py:44-55、download.py:249-268、hunt_last3.py:394-408、upgrade_original.py:225-231。
所有子进程统一 encoding="utf-8", errors="replace"；ffmpeg 带 -y -hide_banner -loglevel error，
ffprobe 不认 -y（实测 Option not found），只用 -hide_banner -loglevel error。
"""
import json
import os
import subprocess
from pathlib import Path

# ffmpeg 公共参数（蓝本 download.py:251）
FF_BASE = ["-y", "-hide_banner", "-loglevel", "error"]
# ffprobe 公共参数：-hide_banner/-loglevel 实测可用，-y 不存在
FFPROBE_BASE = ["-hide_banner", "-loglevel", "error"]


def _run(args, timeout=120, cwd=None):
    """统一执行子进程：UTF-8 解码，非零退出抛 RuntimeError（stderr 截尾）。"""
    try:
        p = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"ffmpeg/ffprobe 超时({timeout}s): {' '.join(str(a) for a in args[:3])}") from e
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "ffmpeg/ffprobe 失败")[-400:])
    return p.stdout


def probe_duration(path, timeout=30):
    """探测时长（秒）；任何失败返回 None（蓝本 prepare.py:86-93）。"""
    args = ["ffprobe", *FFPROBE_BASE, "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(path)]
    try:
        return float(_run(args, timeout=timeout).strip())
    except Exception:
        return None


def probe_full(path, timeout=30):
    """完整探测：{format:…, streams:[…]} JSON（失败抛错）。"""
    args = ["ffprobe", *FFPROBE_BASE, "-print_format", "json",
            "-show_format", "-show_streams", str(path)]
    return json.loads(_run(args, timeout=timeout))


def probe_meta(path, timeout=30):
    """探测时长/码率/标签，返回 {'duration': float|None, 'bit_rate': int|None, 'tags': {'title','artist'}}。"""
    args = ["ffprobe", *FFPROBE_BASE, "-print_format", "json",
            "-show_entries", "format=duration,bit_rate:format_tags=title,artist", str(path)]
    data = json.loads(_run(args, timeout=timeout))
    fmt = data.get("format") or {}
    tags = fmt.get("tags") or {}
    dur, br = fmt.get("duration"), fmt.get("bit_rate")
    return {
        "duration": float(dur) if dur not in (None, "", "N/A") else None,
        "bit_rate": int(br) if br not in (None, "", "N/A") else None,
        "tags": {"title": tags.get("title"), "artist": tags.get("artist")},
    }


def remux_flac(src, dst, *, cover=None, title=None, artist=None, album=None, timeout=180):
    """真 FLAC 源 -c copy 重封装 + 标签 + 可选内嵌封面。

    显式 -f flac 必须（hunt_last3.py:394-408 HANDOFF 踩坑）：输出路径扩展名也必须是真 .flac。
    成功返回 dst 字符串，失败抛 RuntimeError。
    """
    dst = Path(dst)
    args = ["ffmpeg", *FF_BASE, "-i", str(src)]
    if cover and Path(cover).exists():
        args += ["-i", str(cover), "-map", "0:a", "-map", "1:v",
                 "-c:v", "copy", "-disposition:v:0", "attached_pic"]
    else:
        args += ["-map", "0:a"]
    args += ["-c", "copy"]
    if title is not None:
        args += ["-metadata", f"title={title}"]
    if artist is not None:
        args += ["-metadata", f"artist={artist}"]
    if album is not None:
        args += ["-metadata", f"album={album}"]
    args += ["-f", "flac", str(dst)]
    _run(args, timeout=timeout)
    if not dst.exists():
        raise RuntimeError(f"remux 失败：输出未生成 {dst}")
    return str(dst)


def transcode_mp3(src, out_dir, stem, *, cover=None, title=None, artist=None, album=None,
                  timeout=300):
    """转 MP3 320 + ID3v2.3 标签 + 可选内嵌封面（蓝本 download.py:249-268）。

    关键：cwd=out_dir + 相对输出名，防 Windows 长路径。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cover_ok = bool(cover) and Path(cover).exists()
    args = ["ffmpeg", *FF_BASE, "-i", str(src)]
    if cover_ok:
        args += ["-i", str(cover)]
    args += ["-map", "0:a"]
    if cover_ok:
        args += ["-map", "1:v", "-c:v", "mjpeg", "-id3v2_version", "3",
                 "-metadata:s:v", "title=Album cover",
                 "-metadata:s:v", "comment=Cover (front)"]
    args += ["-c:a", "libmp3lame", "-b:a", "320k", "-ar", "44100", "-ac", "2",
             "-id3v2_version", "3"]
    if title is not None:
        args += ["-metadata", f"title={title}"]
    if artist is not None:
        args += ["-metadata", f"artist={artist}"]
    if album is not None:
        args += ["-metadata", f"album={album}"]
    # cwd=out_dir + 相对输出名（蓝本 download.py:263-265）
    args.append(f"{stem}.mp3")
    _run(args, timeout=timeout, cwd=str(out_dir))
    out = out_dir / f"{stem}.mp3"
    if not out.exists():
        raise RuntimeError(f"转码失败：输出未生成 {out}")
    return str(out)


def retag_copy(src, dst=None, *, title=None, artist=None, timeout=120):
    """无损重写标签（-map 0 -c copy）：先输出 <stem>.tagtmp<ext> 再 os.replace 到目标。

    dst=None 时原地更新 src；mp3 追加 -id3v2_version 3（蓝本 rename_apply.py:44-55）。
    """
    src = Path(src)
    target = Path(dst) if dst is not None else src
    tmp = target.with_name(target.stem + ".tagtmp" + target.suffix)
    args = ["ffmpeg", *FF_BASE, "-i", str(src), "-map", "0", "-c", "copy"]
    if title is not None:
        args += ["-metadata", f"title={title}"]
    if artist is not None:
        args += ["-metadata", f"artist={artist}"]
    if src.suffix.lower() == ".mp3":
        args += ["-id3v2_version", "3"]
    args.append(str(tmp))
    _run(args, timeout=timeout)
    if not tmp.exists():
        raise RuntimeError(f"标签写入失败：{tmp} 未生成")
    os.replace(tmp, target)
    return str(target)


def pcm_md5(path, timeout=120):
    """PCM 指纹：解码重采样 44.1k/2ch/pcm_s16le 后的 MD5（stdout 形如 'MD5=…'，蓝本 verify_kaisei.py:27-32）。"""
    args = ["ffmpeg", *FF_BASE, "-i", str(path), "-map", "0:a",
            "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", "-f", "md5", "-"]
    return _run(args, timeout=timeout).strip()
