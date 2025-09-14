from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

try:
    from vosk import Model, KaldiRecognizer  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "未检测到 vosk，请先在 Python 环境中安装：pip install vosk\n"
        f"导入错误：{e}"
    )


def ensure_prerequisites(model_path: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "未检测到 ffmpeg，请先安装并确保命令可用。例如：\n"
            "- Ubuntu/Debian: sudo apt-get install -y ffmpeg\n"
            "- CentOS/RHEL:   sudo yum install -y epel-release && sudo yum install -y ffmpeg\n"
        )

    if not model_path.exists():
        hint = (
            f"未找到模型目录：{model_path}\n"
            "请下载 Vosk 中文模型并解压后，使用 --model 指向模型目录。\n"
            "常用模型：\n"
            "- vosk-model-small-cn-0.22（体积小、速度快）\n"
            "- vosk-model-cn-0.22（体积大、准确率更高）\n"
            "模型下载页：https://alphacephei.com/vosk/models\n"
        )
        raise SystemExit(hint)


def build_ffmpeg_cmd(input_audio: Path) -> list[str]:
    return [
        "ffmpeg",
        "-loglevel",
        "quiet",
        "-i",
        str(input_audio),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-",
    ]


def transcribe(
    input_audio: Path,
    model_dir: Path,
    output_file: Path | None = None,
    print_partial: bool = False,
) -> str:
    ensure_prerequisites(model_dir)

    model = Model(model_dir.as_posix())
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)

    cmd = build_ffmpeg_cmd(input_audio)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    if proc.stdout is None:
        raise RuntimeError("ffmpeg stdout 打开失败")

    texts: list[str] = []
    try:
        while True:
            data = proc.stdout.read(4000)
            if not data:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                seg_text = (res.get("text") or "").strip()
                if seg_text:
                    texts.append(seg_text)
                    if print_partial:
                        print(seg_text)
            else:
                if print_partial:
                    pres = json.loads(rec.PartialResult())
                    ptext = (pres.get("partial") or "").strip()
                    if ptext:
                        print(ptext, end="\r", flush=True)
    finally:
        final_res = json.loads(rec.FinalResult())
        final_text = (final_res.get("text") or "").strip()
        if final_text:
            texts.append(final_text)
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    full_text = " ".join(texts).strip()

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(full_text, encoding="utf-8")

    return full_text


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir / "1.mp3"
    default_model = script_dir / "vosk-model-small-cn-0.22"

    p = argparse.ArgumentParser(
        description="使用 Vosk (离线, CPU) 进行中文语音转文字",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-i", "--input", type=str, default=str(default_input), help="输入音频文件路径")
    p.add_argument("-m", "--model", type=str, default=str(default_model), help="Vosk 中文模型目录")
    p.add_argument("-o", "--output", type=str, default=None, help="识别结果输出到该文件(可选)")
    p.add_argument("--partial", action="store_true", help="输出增量 partial 结果")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_audio = Path(os.path.expanduser(args.input)).resolve()
    model_dir = Path(os.path.expanduser(args.model)).resolve()
    output_file = Path(os.path.expanduser(args.output)).resolve() if args.output else None

    if not input_audio.exists():
        raise SystemExit(f"未找到输入音频文件：{input_audio}")

    text = transcribe(
        input_audio=input_audio,
        model_dir=model_dir,
        output_file=output_file,
        print_partial=args.partial,
    )

    if not output_file:
        print("\n===== 最终识别文本 =====")
        print(text)


if __name__ == "__main__":
    main()
