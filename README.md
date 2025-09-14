
## 中文语音转文字（Vosk，离线，CPU）

前置准备：

- 安装 ffmpeg（系统包管理器安装即可）
- 安装 Python 依赖：`pip install -r requirements.txt`（已包含 `vosk`）
- 下载并解压中文模型至 `stt/` 目录，例如：
   - 小模型：`stt/vosk-model-small-cn-0.22`
   - 大模型：`stt/vosk-model-cn-0.22`

运行命令示例：

```zsh
conda run --name ffmpeg_ws-py38 python stt/stt_vosk.py \
   -i output/video.mp3 \
   -m stt/vosk-model-cn-0.22 \
   -o stt/transcript2.txt \
   --partial
```

参数说明：

- `-i/--input`：输入音频路径（mp3/wav/m4a 等 ffmpeg 支持的格式）
- `-m/--model`：Vosk 中文模型目录
- `-o/--output`：将最终识别文本写入到该文件（可选）
- `--partial`：是否打印增量识别结果（可选）

# ffmpeg_ws

#### 视频自动化剪辑开发项

- [x] 视频抽帧封面

- [x] 时间间隔剪辑

- [x] 随机组合视频素材4/9宫格拼图视频

- [x] 随机组合音频素材功能

- [x] 合成视频高清适配

- [ ] 字幕讲解开发

- [x] 视频调色功能(Luts预设来实现)

- [ ] 特效转场开发

- [ ] log标注

  



#视频语音提取
ffmpeg -i 20240603_165541.mp4 -vn -acodec libmp3lame -ab 128k output_audio.mp3
#封面裁剪
ffmpeg -i jia.mp4 -r 1 image-%3d.jpeg 
#视频裁剪
ffmpeg -i output.mp4 -f segment -segment_time 10 -c copy -reset_timestamps 1 output%03d.mp4



问题汇总:

1. Unknown encoder 'libx264'  缺少libx264

   ```makefile
   编译源码
   git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg
   cd ffmpeg
   ./configure --enable-gpl --enable-libx264
   make
   sudo make install
   ```

2. 安装moviepy不生效

   用coda安装会绑定依赖一起安装 `conda install -c conda-forge moviepy`




资源汇总
1.stt    
https://www.csubtitle.com/?gad_source=1&gclid=Cj0KCQjwh7K1BhCZARIsAKOrVqGf147u6j7L2Al3JDVEK2XfrFVXzxFHDv_-G5A_BHFmOpTzBAULlQ4aAuHLEALw_wcB

## 小红书图片/视频下载（新增）

- 脚本：`toolkits/xhs_downloader.py`
- 依赖：`pip install -r requirements.txt`（需要本机安装 Chrome/Chromium；视频 m3u8 合并需要 ffmpeg）
- 用法示例：

   单条笔记下载：
   ```bash
   python toolkits/xhs_downloader.py --note "https://www.xiaohongshu.com/explore/68c65770000000001d0209b5?xsec_token=ABECQgrO2p4BY_zpnP9MzuYVy5K8KgNIKVPrMeOZ5x88I=&xsec_source=pc_feed" -o ./xhs_downloads
   ```

   用户主页前 N 条笔记：
   ```bash
   python toolkits/xhs_downloader.py --profile "https://www.xiaohongshu.com/user/profile/xxxxxxxx" -n 20 -o ./xhs_downloads
   ```

   如果需要手动登录（推荐关闭无头模式）：
   ```bash
   python toolkits/xhs_downloader.py --profile "https://www.xiaohongshu.com/user/profile/xxxxxxxx" -n 20 -o ./xhs_downloads --headless
   ```

注意：小红书页面结构可能变化，如抓取失败请根据当前 DOM 调整选择器。
\n+## 语音转文字（Whisper · faster-whisper）
\n+说明：
\n+- 新增脚本：`stt/stt_whisper.py`
- 依赖：`faster-whisper`（已加入 `requirements.txt`）。首次使用某些模型名称（如 `small`/`large-v3`）会自动下载权重，网络受限环境建议提前准备离线模型目录并用 `-m <模型目录>` 指定。
- 需系统安装 `ffmpeg`（用于音频解码）。
\n+安装依赖（如未安装）：
\n+```zsh
conda run --name ffmpeg_ws-py38 python -m pip install -r requirements.txt
```
\n+运行示例（使用示例音频 `stt/input/1.mp3`，自动选择设备，int8 精度）：
\n+```zsh
conda run --name ffmpeg_ws-py38 python stt/stt_whisper.py \
   -i stt/input/1.mp3 \
   -m small \
   --device auto \
   --compute-type int8 \
   --language zh \
   --task transcribe \
   --print
```
\n+默认会在输入同目录生成：
\n+- `1.whisper.txt`（整段文本）
- `1.whisper.srt`（分段字幕）
\n+常用参数：
\n+- `-m/--model`：模型名称或本地权重目录（如：`tiny`/`base`/`small`/`medium`/`large-v3`/`large-v3-turbo`）。
- `--device`：`auto`/`cpu`/`cuda`。
- `--compute-type`：`int8`（CPU 推荐）/`float16`（GPU 推荐）/`float32` 等。
- `--language`：语言代码，中文可用 `zh`；留空可自动检测。
- `--task`：`transcribe` 原语种转写；`translate` 翻译成英文。
- `--txt`、`--srt` 或 `-o/--output-basename`：控制输出文件路径。
- `--no-vad`：关闭静音/噪声过滤（默认开启）。
\n+离线/内网环境建议：
\n+1) 使用国内镜像安装依赖（如清华）：
\n+```zsh
conda run --name ffmpeg_ws-py38 python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple faster-whisper ctranslate2
```
\n+2) 预下载/准备离线模型（CTranslate2 格式），放置到本地，例如 `stt/models/whisper-small/`，然后：
\n+```zsh
conda run --name ffmpeg_ws-py38 python stt/stt_whisper.py -i stt/input/1.mp3 -m stt/models/whisper-small --print
```