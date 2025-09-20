# Video Clips - 智能视频剪辑工具

## 📌 项目简介

Video Clips 是一个基于 Python 开发的智能视频剪辑工具，提供了完整的视频处理工作流，包括视频抽帧、切割、宫格组合、时长组合和音乐配对等功能。

## ✨ 主要功能

### 🖼️ 功能1: 视频抽帧
- 从视频中提取静态图片帧
- 支持自定义抽帧间隔（秒）
- 多种输出格式：PNG、JPG
- 多种提取方法：OpenCV、FFmpeg、MoviePy

### ✂️ 功能2: 视频切割  
- 将长视频切割为5-30秒的短片段
- 支持等时长切割和随机时长切割
- 可设置片段重叠时间
- 高效的FFmpeg无重编码切割

### 🏢 功能3: 宫格视频组合
- 支持2×1、2×2、3×1、2×3等多种宫格布局
- 智能视频选择策略（随机、时长优先等）
- 自动尺寸调整和布局对齐
- 高质量视频输出

### ⏱️ 功能4: 时长组合
- 将短片段组合成10s、15s、20s等指定时长视频
- 多种组合策略：随机、平衡、时长优先
- 丰富的转场效果：交叉淡化、淡入淡出、直接拼接
- 智能片段选择算法

### 🎵 功能5: 音乐配对
- 从音乐库随机选择背景音乐
- 智能音乐时长匹配
- 音量控制和淡入淡出效果
- 支持音视频混合

## 🔧 技术架构

### 项目结构
```
video_clips/
├── main.py                    # GUI主程序
├── run.py                     # 启动脚本
├── requirements.txt           # 依赖包
├── config/
│   └── settings.py           # 配置管理
├── modules/                  # 核心功能模块
│   ├── frame_extractor.py    # 视频抽帧
│   ├── video_splitter.py     # 视频切割
│   ├── grid_composer.py      # 宫格组合
│   ├── duration_composer.py  # 时长组合
│   └── audio_mixer.py        # 音乐配对
├── utils/                    # 工具模块
│   ├── file_handler.py       # 文件处理
│   └── video_utils.py        # 视频工具
├── gui/                      # GUI界面
├── temp/                     # 临时文件
└── output/                   # 输出文件
```

### 技术栈
- **GUI框架**: tkinter (Python内置)
- **视频处理**: MoviePy, OpenCV
- **高性能处理**: FFmpeg
- **图像处理**: Pillow
- **进度显示**: tqdm

## 🚀 安装和使用

### 环境要求
- Python 3.7+
- FFmpeg (系统级安装)

### 安装步骤

1. **克隆项目**
```bash
cd /home/admins/project/ffmpeg_ws/video_clips
```

2. **安装Python依赖**
```bash
pip install -r requirements.txt
```

3. **安装FFmpeg** (如果未安装)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS (使用Homebrew)
brew install ffmpeg

# Windows (使用Chocolatey)
choco install ffmpeg
```

### 启动程序

**方法1: 使用启动脚本**
```bash
python run.py
```

**方法2: 直接运行主程序**
```bash
python main.py
```

## 💡 使用指南

### GUI界面说明

1. **文件选择**
   - 点击"📁 选择视频"选择单个或多个视频文件
   - 点击"📂 选择文件夹"批量添加文件夹中的所有视频

2. **功能选择**
   - 左侧面板选择要使用的功能
   - 根据不同功能调整相应参数

3. **参数设置**
   - 每个功能都有专门的参数面板
   - 支持实时调整和预览

4. **开始处理**
   - 点击"开始处理"执行任务
   - 进度条显示实时进度
   - 状态文本框显示详细日志

### 功能使用示例

**视频抽帧示例**
```python
# 通过GUI或代码方式
from modules.frame_extractor import FrameExtractor

extractor = FrameExtractor()
result = extractor.extract_frames(
    video_path="input.mp4",
    interval=2.0,      # 每2秒提取一帧
    image_format="png",
    method="cv2"
)
```

**视频切割示例**
```python
from modules.video_splitter import VideoSplitter

splitter = VideoSplitter()
segments = splitter.split_video(
    video_path="input.mp4",
    segment_duration=8.0,  # 8秒一段
    method="equal"
)
```

**宫格组合示例**
```python
from modules.grid_composer import GridComposer

composer = GridComposer()
result = composer.create_grid_video(
    video_paths=["video1.mp4", "video2.mp4", "video3.mp4", "video4.mp4"],
    layout="2×2",
    duration=10.0
)
```

## 🛠️ 高级配置

### 配置文件 (config/settings.py)

```python
# 输出质量设置
VIDEO_CODEC = 'libx264'
VIDEO_BITRATE = '5000k'
AUDIO_CODEC = 'aac'
AUDIO_BITRATE = '320k'

# 支持的文件格式
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv']
SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a']

# 默认参数
DEFAULT_FRAME_INTERVAL = 1.0
DEFAULT_SEGMENT_DURATION = 8
DEFAULT_OUTPUT_DURATION = [10, 15, 20]
```

### 自定义宫格布局

```python
# 在settings.py中添加自定义布局
GRID_LAYOUTS = {
    '2×1': (2, 1),
    '2×2': (2, 2),
    '3×1': (3, 1),
    '2×3': (2, 3),
    # 添加自定义布局
    '4×1': (4, 1),
    '2×4': (2, 4)
}
```

## 📊 性能优化

### 处理大文件建议
- 使用FFmpeg方法进行无重编码操作
- 定期清理临时文件
- 为大批量处理预留足够磁盘空间

### 内存优化
- 视频处理采用流式处理
- 自动释放不使用的资源
- 支持后台处理，避免界面卡顿

## 🔍 故障排除

### 常见问题

1. **FFmpeg未找到**
   ```
   解决方案: 确保FFmpeg已正确安装并添加到系统PATH
   测试命令: ffmpeg -version
   ```

2. **依赖包安装失败**
   ```
   解决方案: 使用conda安装MoviePy
   命令: conda install -c conda-forge moviepy
   ```

3. **视频编码错误**
   ```
   解决方案: 检查输入视频格式是否支持
   尝试使用不同的编码器参数
   ```

4. **内存不足**
   ```
   解决方案: 减小处理批次大小
   关闭其他占用内存的程序
   ```

### 日志和调试

程序运行时会在GUI的状态文本框中显示详细日志，包括：
- 文件处理进度
- 错误信息和警告
- 性能统计信息

## 🎯 使用场景

### 适用场景
- **短视频制作**: 快速生成多种风格的短视频内容
- **社交媒体**: 批量制作适合不同平台的视频格式
- **教育培训**: 将长视频切割为便于学习的短片段
- **电商展示**: 创建产品展示的宫格视频
- **内容创作**: 自动化视频编辑工作流

### 行业应用
- 数字营销公司
- 教育培训机构  
- 电商平台
- 自媒体创作者
- 视频制作工作室

## 📈 未来规划

### 计划功能
- [ ] 智能场景检测切割
- [ ] 视频风格迁移
- [ ] 批量字幕生成
- [ ] 云端处理支持
- [ ] 视频质量增强
- [ ] 更多转场特效

### 性能优化
- [ ] GPU加速处理
- [ ] 分布式处理
- [ ] 缓存机制优化
- [ ] 内存使用优化

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

### 开发环境设置
```bash
# 克隆仓库
git clone <repository-url>
cd video_clips

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 代码规范
- 遵循PEP 8代码风格
- 添加适当的文档字符串
- 编写单元测试
- 使用type hints

## 📄 许可证

本项目采用MIT许可证，详情请查看LICENSE文件。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至开发者
- 参与项目讨论

---

**Video Clips** - 让视频编辑变得简单高效！ 🎬✨