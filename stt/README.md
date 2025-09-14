# 语音转文字（stt）使用说明

本目录包含两套方案：
- `stt_whisper.py`：基于 faster-whisper（CTranslate2），支持 CPU/GPU，效果好、速度快（建议优先）。
- `stt_vosk.py`：基于 Vosk，纯离线 CPU，部署简单，适合弱网/无网环境。

---

## 一、Whisper（faster-whisper）

### 1) 环境与依赖
- Python 3.8（仓库已使用 conda 环境 `ffmpeg_ws-py38`）
- 依赖（requirements.txt 已给出）：
  - faster-whisper
  - opencc-python-reimplemented（可选，用于简体转换）
- 系统需安装 ffmpeg（命令可用）

建议国内镜像与本地缓存（减少模型下载卡顿）：
```zsh
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=$(pwd)/.hf
export HUGGINGFACE_HUB_CACHE=$(pwd)/.hf/hub
```

### 2) 执行位置与路径对照（重要）
- 从“仓库根目录”运行：脚本路径需带前缀，例如 `python stt/stt_whisper.py`，输入文件 `-i stt/input/xxx.mp3`
- 从“stt 目录内”运行：脚本直接 `python stt_whisper.py`，输入文件 `-i input/xxx.mp3`

常见错误：在 stt 目录内运行却写成 `python stt/stt_whisper.py` 会导致找不到文件；在仓库根目录运行却写成 `python stt_whisper.py` 也会失败。

### 3) 快速开始（CPU, tiny, 简体输出）
从仓库根目录运行：
```zsh
conda run --name ffmpeg_ws-py38 \
  python stt/stt_whisper.py \
  -i stt/input/1.mp3 \
  -m /home/std/project/ffmpeg_ws/.hf/hub/models--Systran--faster-whisper-tiny/snapshots/d90ca5fe260221311c53c58e660288d3deb8d356 \
  --device cpu --compute-type int8 \
  --task transcribe --zh-simplified --print
```

从 stt 目录运行：
```zsh
conda run --name ffmpeg_ws-py38 \
  python stt_whisper.py \
  -i input/1.mp3 \
  -m tiny --device cpu --compute-type int8 \
  --task transcribe --zh-simplified --print
```

- 默认输出路径：`stt/output/<音频名>.whisper.txt` 与 `stt/output/<音频名>.whisper.srt`。
- 如需指定输出：
  - `--txt <路径>` 仅指定 txt
  - `--srt <路径>` 仅指定 srt
  - `-o <基名>` 同时生成 `<基名>.txt` 与 `<基名>.srt`

### 4) 常用参数
- `-m/--model`：模型名称或本地目录（如 `tiny`/`small`/`medium`/`large-v3` 或本地权重路径）
- `--device`：`auto`/`cpu`/`cuda`
- `--compute-type`：`int8`(CPU 推荐) / `float16`(GPU 推荐) / `float32` 等
- `--language`：语言代码，默认 `zh`；留空自动检测
- `--task`：`transcribe`（转写）/ `translate`（翻译）
- `--beam-size`：解码 beam 大小
- `--no-vad`：关闭 VAD 过滤
- `--word-timestamps`：输出词级时间戳（更慢）
- `--zh-simplified`：将输出统一为简体（需要 `opencc-python-reimplemented`）

### 5) GPU 示例
从仓库根目录运行：
```zsh
conda run --name ffmpeg_ws-py38 \
  python stt/stt_whisper.py \
  -i stt/input/1.mp3 \
  -m small --device cuda --compute-type float16 \
  --task transcribe --zh-simplified --print
```

从 stt 目录运行：
```zsh
conda run --name ffmpeg_ws-py38 \
  python stt_whisper.py \
  -i input/1.mp3 \
  -m small --device cuda --compute-type float16 \
  --task transcribe --zh-simplified --print
```

### 6) 方案A（纯离线）：直接使用本地模型目录

已缓存的 tiny 模型路径（绝对路径示例）：
`/home/std/project/ffmpeg_ws/.hf/hub/models--Systran--faster-whisper-tiny/snapshots/d90ca5fe260221311c53c58e660288d3deb8d356`

从仓库根目录运行（直接路径）：
```zsh
conda run --name ffmpeg_ws-py38 \
  python stt/stt_whisper.py \
  -i stt/input/1.mp3 \
  -m /home/std/project/ffmpeg_ws/.hf/hub/models--Systran--faster-whisper-tiny/snapshots/d90ca5fe260221311c53c58e660288d3deb8d356 \
  --device cpu --compute-type int8 \
  --task transcribe --zh-simplified --print
```

创建软链接并使用短路径：
```zsh
ln -sfn /home/std/project/ffmpeg_ws/.hf/hub/models--Systran--faster-whisper-tiny/snapshots/d90ca5fe260221311c53c58e660288d3deb8d356 \
  stt/models/whisper-tiny
```

从仓库根目录运行（短路径）：
```zsh
conda run --name ffmpeg_ws-py38 \
  python stt/stt_whisper.py \
  -i stt/input/1.mp3 \
  -m stt/models/whisper-tiny \
  --device cpu --compute-type int8 \
  --task transcribe --zh-simplified --print
```

从 stt 目录运行（短路径）：
```zsh
conda run --name ffmpeg_ws-py38 \
  python stt_whisper.py \
  -i input/1.mp3 \
  -m models/whisper-tiny \
  --device cpu --compute-type int8 \
  --task transcribe --zh-simplified --print
```

---

## 二、Vosk（纯离线）

### 1) 环境与依赖
- `pip install vosk`
- 系统需安装 ffmpeg
- 需要下载中文模型并解压，本仓库示例默认：
  - `stt/vosk-model-small-cn-0.22`
  - 或 `stt/vosk-model-cn-0.22`

### 2) 快速开始
从仓库根目录运行：
```zsh
conda run --name ffmpeg_ws-py38 \
  python stt/stt_vosk.py \
  -i stt/input/1.mp3 \
  -m stt/vosk-model-small-cn-0.22 \
  -o stt/output/1.vosk.txt
```

从 stt 目录运行：
```zsh
conda run --name ffmpeg_ws-py38 \
  python stt_vosk.py \
  -i input/1.mp3 \
  -m vosk-model-small-cn-0.22 \
  -o output/1.vosk.txt
```

- 若不加 `-o`，结果将打印到控制台。
- `--partial` 开启时会打印增量识别（便于观察进度）。

### 3) 模型下载
访问 https://alphacephei.com/vosk/models 下载中文模型，解压后将 `--model` 指向该目录即可。

---

## 常见问题
- ffmpeg 未安装：请按系统安装并确保命令可用。
- 模型下载慢（Whisper）：
  - 使用上面的 HF 镜像与本地缓存变量；或预下载到本地目录并用 `-m <本地路径>`。
- 输出目录：Whisper 默认输出到 `stt/output/`；Vosk 若指定 `-o` 也建议放到该目录，方便统一管理。
 - 退出码 2：通常是参数或路径错误，请核对当前工作目录与示例命令的路径是否匹配（根目录 vs stt 目录）。