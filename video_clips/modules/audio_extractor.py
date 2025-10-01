from __future__ import annotations

"""
音频提取模块：从视频文件提取音频，支持常见格式（mp3/wav/aac/flac/ogg 等）。
依赖系统 ffmpeg。
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "未检测到 ffmpeg，请先安装并确保命令可用。\n"
            "- Ubuntu/Debian: sudo apt-get install -y ffmpeg\n"
            "- CentOS/RHEL:   sudo yum install -y epel-release && sudo yum install -y ffmpeg\n"
        )


@dataclass
class ExtractOptions:
    format: str = "mp3"           # 输出音频格式
    bitrate_k: Optional[int] = 192 # 比特率（kbps），WAV 无需比特率
    sample_rate: Optional[int] = None  # 采样率，例如 44100/48000
    start_sec: Optional[float] = None  # 起始秒
    duration_sec: Optional[float] = None  # 持续秒


def build_ffmpeg_cmd(input_path: str, output_path: str, opt: ExtractOptions) -> List[str]:
    cmd = [
        "ffmpeg", "-y",
    ]
    # 时间裁剪参数需在输入之前或之后取决于是否精确，简单使用 -ss -t 放在输入前即可快速切片
    if opt.start_sec is not None:
        cmd += ["-ss", str(opt.start_sec)]
    if opt.duration_sec is not None:
        cmd += ["-t", str(opt.duration_sec)]
    cmd += ["-i", input_path]

    # 音频参数
    if opt.sample_rate:
        cmd += ["-ar", str(opt.sample_rate)]
    # 不要视频流
    cmd += ["-vn"]

    fmt = opt.format.lower()
    if fmt == "mp3":
        if opt.bitrate_k:
            cmd += ["-b:a", f"{opt.bitrate_k}k"]
        cmd += ["-acodec", "libmp3lame"]
    elif fmt == "wav":
        cmd += ["-acodec", "pcm_s16le"]
    elif fmt == "aac" or fmt == "m4a":
        if opt.bitrate_k:
            cmd += ["-b:a", f"{opt.bitrate_k}k"]
        cmd += ["-acodec", "aac"]
        # 对 m4a 容器，增加 faststart 以便更好地流式播放
        if fmt == "m4a":
            cmd += ["-movflags", "+faststart"]
    elif fmt == "flac":
        cmd += ["-acodec", "flac"]
    elif fmt == "ogg":
        if opt.bitrate_k:
            cmd += ["-b:a", f"{opt.bitrate_k}k"]
        cmd += ["-acodec", "libvorbis"]
    else:
        # 默认走 ffmpeg 自动编码
        if opt.bitrate_k:
            cmd += ["-b:a", f"{opt.bitrate_k}k"]

    cmd += [output_path]
    return cmd


def extract_audio(input_path: str, output_path: str, opt: Optional[ExtractOptions] = None) -> str:
    """从视频中提取音频并保存到 output_path，返回输出文件路径。"""
    ensure_ffmpeg()
    opt = opt or ExtractOptions()

    in_p = Path(os.path.expanduser(input_path)).resolve()
    if not in_p.exists():
        raise FileNotFoundError(f"找不到输入文件：{in_p}")

    out_p = Path(os.path.expanduser(output_path)).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # 第一次尝试：按用户要求格式编码
    cmd = build_ffmpeg_cmd(str(in_p), str(out_p), opt)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode == 0:
        return str(out_p)

    stderr_tail = proc.stderr[-4000:] if proc.stderr else ''

    # 当 mp3 编码器不可用时，自动回退到 AAC(M4A)，仍失败则回退 WAV
    fmt_lower = (opt.format or '').lower()
    if fmt_lower == 'mp3' and ('Unknown encoder' in stderr_tail and 'libmp3lame' in stderr_tail):
        # 回退到 AAC（容器改为 .m4a 更通用）
        out_m4a = out_p.with_suffix('.m4a')
        opt_aac = ExtractOptions(
            format='aac',
            bitrate_k=opt.bitrate_k,
            sample_rate=opt.sample_rate,
            start_sec=opt.start_sec,
            duration_sec=opt.duration_sec,
        )
        cmd2 = build_ffmpeg_cmd(str(in_p), str(out_m4a), opt_aac)
        proc2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc2.returncode == 0:
            return str(out_m4a)

        # 最后回退到 WAV（无损，兼容性最好）
        out_wav = out_p.with_suffix('.wav')
        opt_wav = ExtractOptions(
            format='wav',
            bitrate_k=None,
            sample_rate=opt.sample_rate,
            start_sec=opt.start_sec,
            duration_sec=opt.duration_sec,
        )
        cmd3 = build_ffmpeg_cmd(str(in_p), str(out_wav), opt_wav)
        proc3 = subprocess.run(cmd3, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc3.returncode == 0:
            return str(out_wav)

        # 三次均失败，抛出聚合错误
        combined = (
            f"[mp3失败]\n{' '.join(cmd)}\n{stderr_tail}\n\n"
            f"[aac回退失败]\n{' '.join(cmd2)}\n{proc2.stderr[-4000:] if proc2.stderr else ''}\n\n"
            f"[wav回退失败]\n{' '.join(cmd3)}\n{proc3.stderr[-4000:] if proc3.stderr else ''}"
        )
        raise RuntimeError(f"ffmpeg 提取失败（已尝试 mp3/aac/wav）：\n{combined}")

    # 其它失败情况，直接给出详细错误
    raise RuntimeError(f"ffmpeg 提取失败：\n{' '.join(cmd)}\n{stderr_tail}")
