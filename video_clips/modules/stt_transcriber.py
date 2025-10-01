from __future__ import annotations

"""
Whisper 语音转文字封装模块（供 video_clips 使用）

依赖：faster-whisper、可选 opencc-python-reimplemented、系统需安装 ffmpeg。
输出：txt、srt 到 video_clips/output/transcripts/
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

try:
    from faster_whisper import WhisperModel  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "未检测到 faster-whisper，请先安装（项目已在 requirements.txt 中声明）：\n"
        "pip install faster-whisper\n"
        f"导入错误：{e}"
    )

_opencc = None
_opencc_warned = False


def to_simplified(text: str) -> str:
    global _opencc, _opencc_warned
    if not text:
        return text
    try:
        if _opencc is None:
            from opencc import OpenCC  # type: ignore
            _opencc = OpenCC("t2s")
        return _opencc.convert(text)
    except Exception:
        if not _opencc_warned:
            print("[提示] 未安装 opencc-python-reimplemented，无法进行简体转换，已使用原文。")
            _opencc_warned = True
        return text


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "未检测到 ffmpeg，请先安装并确保命令可用。\n"
            "- Ubuntu/Debian: sudo apt-get install -y ffmpeg\n"
            "- CentOS/RHEL:   sudo yum install -y epel-release && sudo yum install -y ffmpeg\n"
        )


def secs_to_srt_time(t: float) -> str:
    if t < 0:
        t = 0
    hours = int(t // 3600)
    t -= hours * 3600
    minutes = int(t // 60)
    t -= minutes * 60
    seconds = int(t)
    milliseconds = int(round((t - seconds) * 1000))
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def write_txt(lines: Iterable[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(s.strip() for s in lines if s and s.strip()) + "\n"
    path.write_text(content, encoding="utf-8")


def write_srt(segments: Iterable[Tuple[int, float, float, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parts: List[str] = []
    for idx, start, end, text in segments:
        parts.append(str(idx))
        parts.append(f"{secs_to_srt_time(start)} --> {secs_to_srt_time(end)}")
        parts.append(text.strip())
        parts.append("")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def default_outputs_under_videoclips(input_media: Path) -> Tuple[Path, Path]:
    """将输出统一放在 video_clips/output/transcripts 下。"""
    # video_clips/modules/stt_transcriber.py -> video_clips
    vc_root = Path(__file__).resolve().parents[1]
    out_dir = vc_root / "output" / "transcripts"
    stem = input_media.stem
    txt = out_dir / f"{stem}.whisper.txt"
    srt = out_dir / f"{stem}.whisper.srt"
    return txt, srt


@dataclass
class TranscribeResult:
    language: Optional[str]
    duration: Optional[float]
    text: str
    txt_path: Optional[Path]
    srt_path: Optional[Path]


def transcribe_to_files(
    input_path: str,
    model_name_or_path: Optional[str] = None,
    device: str = "cpu",
    compute_type: str = "int8",
    language: Optional[str] = "zh",
    task: str = "transcribe",
    beam_size: int = 5,
    vad_filter: bool = True,
    word_timestamps: bool = False,
    zh_simplified: bool = True,
    out_txt: Optional[str] = None,
    out_srt: Optional[str] = None,
) -> TranscribeResult:
    """
    使用 faster-whisper 将音/视频转写为文本与字幕文件。

    返回 TranscribeResult，包含文本、元信息与生成的文件路径。
    """
    ensure_ffmpeg()

    media = Path(os.path.expanduser(input_path)).resolve()
    if not media.exists():
        raise FileNotFoundError(f"找不到输入文件：{media}")

    # 模型默认：优先使用项目 stt/models/whisper-small，否则使用 'small'
    if not model_name_or_path:
        proj_root = Path(__file__).resolve().parents[2]
        local_small = proj_root / "stt" / "models" / "whisper-small"
        model_name_or_path = str(local_small) if local_small.exists() else "small"

    model = WhisperModel(
        model_name_or_path,
        device=device,
        compute_type=compute_type,
    )

    segments, info = model.transcribe(
        str(media),
        language=language,
        task=task,
        beam_size=beam_size,
        vad_filter=vad_filter,
        word_timestamps=word_timestamps,
    )

    texts: List[str] = []
    srt_segments: List[Tuple[int, float, float, str]] = []
    for i, seg in enumerate(segments, start=1):
        text = (seg.text or "").strip()
        if zh_simplified:
            text = to_simplified(text)
        if text:
            texts.append(text)
            srt_segments.append((i, seg.start or 0.0, seg.end or 0.0, text))

    # 输出路径
    txt_path: Optional[Path] = Path(os.path.expanduser(out_txt)).resolve() if out_txt else None
    srt_path: Optional[Path] = Path(os.path.expanduser(out_srt)).resolve() if out_srt else None
    if txt_path is None and srt_path is None:
        txt_path, srt_path = default_outputs_under_videoclips(media)

    if txt_path:
        write_txt([" ".join(texts).strip()], txt_path)
    if srt_path:
        write_srt(srt_segments, srt_path)

    return TranscribeResult(
        language=getattr(info, "language", None),
        duration=getattr(info, "duration", None),
        text=" ".join(texts).strip(),
        txt_path=txt_path,
        srt_path=srt_path,
    )
