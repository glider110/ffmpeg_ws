from __future__ import annotations

"""
Whisper 语音转文字（使用 faster-whisper，本地推理，支持 CPU/GPU）

功能特性：
- 支持选择模型（名称或本地权重路径），如：tiny, base, small, medium, large-v3, large-v3-turbo
- 支持设备选择：auto/cpu/cuda；以及计算精度：int8/float16/float32 等
- 支持中文语言指定（默认 zh）与任务模式（transcribe/translate）
- 输出 txt 与 srt 文件；也可仅打印到控制台
- 可选开启/关闭 VAD 过滤，减少静音片段

使用示例：
  python stt/stt_whisper.py -i stt/input/1.mp3 \
      -m small --device auto --compute-type int8 --language zh --task transcribe \
      --txt stt/transcript_whisper.txt --srt stt/transcript_whisper.srt

依赖：
  pip install faster-whisper
系统需求：
  需已安装 ffmpeg 并可在命令行调用（用于音频解码）
"""

import argparse
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

try:
    # faster-whisper 基于 CTranslate2，较原版 whisper 更轻量
    from faster_whisper import WhisperModel  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "未检测到 faster-whisper，请先安装：pip install faster-whisper\n"
        f"导入错误：{e}"
    )


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "未检测到 ffmpeg，请先安装并确保命令可用。例如：\n"
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
    """写入 SRT 文件。
    segments: 迭代 (idx, start, end, text)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    parts: List[str] = []
    for idx, start, end, text in segments:
        parts.append(str(idx))
        parts.append(f"{secs_to_srt_time(start)} --> {secs_to_srt_time(end)}")
        parts.append(text.strip())
        parts.append("")  # 空行
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


@dataclass
class TranscribeResult:
    language: Optional[str]
    duration: Optional[float]
    text: str


def transcribe(
    input_audio: Path,
    model_name_or_path: str = "small",
    device: str = "auto",
    compute_type: str = "int8",
    language: Optional[str] = "zh",
    task: str = "transcribe",
    beam_size: int = 5,
    vad_filter: bool = True,
    word_timestamps: bool = False,
) -> Tuple[TranscribeResult, List[Tuple[int, float, float, str]]]:
    """使用 faster-whisper 进行转写。

    返回: (总体结果, 片段列表[(idx, start, end, text)])
    """
    ensure_ffmpeg()

    model = WhisperModel(
        model_name_or_path,
        device=device,
        compute_type=compute_type,
    )

    segments, info = model.transcribe(
        str(input_audio),
        language=language,
        task=task,
        beam_size=beam_size,
        vad_filter=vad_filter,
        word_timestamps=word_timestamps,
    )

    # 收集文本与 SRT 片段
    texts: List[str] = []
    srt_segments: List[Tuple[int, float, float, str]] = []
    for i, seg in enumerate(segments, start=1):
        text = (seg.text or "").strip()
        if text:
            texts.append(text)
            srt_segments.append((i, seg.start or 0.0, seg.end or 0.0, text))

    result = TranscribeResult(
        language=getattr(info, "language", None),
        duration=getattr(info, "duration", None),
        text=" ".join(texts).strip(),
    )
    return result, srt_segments


def default_outputs(input_audio: Path) -> Tuple[Path, Path]:
    """根据输入文件构造默认的 txt/srt 输出路径。放在同一目录，添加 .whisper 后缀。"""
    parent = input_audio.parent
    stem = input_audio.stem
    txt = parent / f"{stem}.whisper.txt"
    srt = parent / f"{stem}.whisper.srt"
    return txt, srt


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir / "input" / "1.mp3"

    p = argparse.ArgumentParser(
        description="使用 Whisper (faster-whisper) 进行语音转文字",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-i", "--input", type=str, default=str(default_input), help="输入音频路径")
    p.add_argument("-m", "--model", type=str, default="small", help="模型名称或本地权重路径")
    p.add_argument("--device", type=str, choices=["auto", "cpu", "cuda"], default="auto", help="推理设备")
    p.add_argument(
        "--compute-type",
        type=str,
        default="int8",
        choices=["int8", "int8_float16", "int8_float32", "float16", "float32"],
        help="计算精度（cpu 推荐 int8；gpu 推荐 float16）",
    )
    p.add_argument("--language", type=str, default="zh", help="语言代码，如 zh, en。留空自动检测")
    p.add_argument("--task", type=str, choices=["transcribe", "translate"], default="transcribe", help="任务模式")
    p.add_argument("--beam-size", type=int, default=5, help="解码 beam 大小")
    p.add_argument("--no-vad", dest="vad", action="store_false", help="关闭 VAD 过滤")
    p.add_argument("--word-timestamps", action="store_true", help="输出词级时间戳（可能更慢）")
    p.set_defaults(vad=True)

    out = p.add_argument_group("输出")
    out.add_argument("--txt", type=str, default=None, help="输出 TXT 文件路径")
    out.add_argument("--srt", type=str, default=None, help="输出 SRT 文件路径")
    out.add_argument("-o", "--output-basename", type=str, default=None, help="输出基名（不含扩展名），会生成 .txt 与 .srt")
    out.add_argument("--print", dest="do_print", action="store_true", help="在控制台打印最终文本")

    return p.parse_args()


def main() -> None:
    args = parse_args()

    input_audio = Path(os.path.expanduser(args.input)).resolve()
    if not input_audio.exists():
        raise SystemExit(f"未找到输入音频文件：{input_audio}")

    # 计算输出路径
    out_txt: Optional[Path] = None
    out_srt: Optional[Path] = None
    if args.output_basename:
        base = Path(os.path.expanduser(args.output_basename)).resolve()
        out_txt = base.with_suffix(".txt")
        out_srt = base.with_suffix(".srt")
    else:
        if args.txt:
            out_txt = Path(os.path.expanduser(args.txt)).resolve()
        if args.srt:
            out_srt = Path(os.path.expanduser(args.srt)).resolve()
        if out_txt is None and out_srt is None:
            out_txt, out_srt = default_outputs(input_audio)

    result, segments = transcribe(
        input_audio=input_audio,
        model_name_or_path=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=(None if not args.language else args.language),
        task=args.task,
        beam_size=args.beam_size,
        vad_filter=args.vad,
        word_timestamps=args.word_timestamps,
    )

    # 写文件
    if out_txt:
        write_txt([result.text], out_txt)
    if out_srt:
        write_srt(segments, out_srt)

    # 控制台输出
    if args.do_print or (not out_txt and not out_srt):
        print("\n===== Whisper 最终识别文本 =====")
        print(result.text)
        if result.language or result.duration:
            print("\n[meta]", {"language": result.language, "duration": result.duration})


if __name__ == "__main__":
    main()
