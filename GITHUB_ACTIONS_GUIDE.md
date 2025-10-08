# GitHub Actions 自动构建指南

本项目使用 GitHub Actions 自动构建 Windows 和 Linux 平台的可执行文件。

## 使用方法

### 1. 推送代码触发构建
```bash
git add .
git commit -m "Update application"
git push origin main
```

### 2. 手动触发构建
1. 访问 GitHub 仓库页面
2. 点击 "Actions" 标签
3. 选择 "Build Windows Executable" workflow
4. 点击 "Run workflow" 按钮

### 3. 下载构建结果
1. 在 Actions 页面找到完成的构建
2. 在 "Artifacts" 部分下载：
   - `VideoClipsApp-Windows` - Windows 可执行文件
   - `VideoClipsApp-Linux` - Linux 可执行文件

## 构建输出

### Windows 版本
- `VideoClipsApp/VideoClipsApp.exe` - 主程序
- `VideoClipsApp/_internal/` - 依赖库文件
- `run_app.bat` - 启动脚本

### Linux 版本
- `VideoClipsApp/VideoClipsApp` - 主程序
- `VideoClipsApp/_internal/` - 依赖库文件
- `run_app.sh` - 启动脚本

## 本地测试构建配置

如果需要在本地测试构建配置，可以使用以下命令：

### Windows (在 PowerShell 中)
```powershell
cd video_clips
python -m PyInstaller `
  --clean `
  --noconfirm `
  --onedir `
  --windowed `
  --name "VideoClipsApp" `
  --add-data "config;config" `
  --add-data "modules;modules" `
  --add-data "utils;utils" `
  --hidden-import "PyQt5.QtCore" `
  --hidden-import "PyQt5.QtGui" `
  --hidden-import "PyQt5.QtWidgets" `
  --hidden-import "PyQt5.sip" `
  --hidden-import "numpy" `
  --hidden-import "PIL" `
  --hidden-import "PIL.Image" `
  --collect-submodules "PyQt5" `
  --collect-submodules "numpy" `
  --collect-submodules "PIL" `
  main_qt5.py
```

### Ubuntu/Linux
```bash
cd video_clips
python -m PyInstaller \
  --clean \
  --noconfirm \
  --onedir \
  --windowed \
  --name "VideoClipsApp" \
  --add-data "config:config" \
  --add-data "modules:modules" \
  --add-data "utils:utils" \
  --hidden-import "PyQt5.QtCore" \
  --hidden-import "PyQt5.QtGui" \
  --hidden-import "PyQt5.QtWidgets" \
  --hidden-import "PyQt5.sip" \
  --hidden-import "numpy" \
  --hidden-import "PIL" \
  --hidden-import "PIL.Image" \
  --collect-submodules "PyQt5" \
  --collect-submodules "numpy" \
  --collect-submodules "PIL" \
  main_qt5.py
```

## 故障排除

### 依赖项问题
如果构建失败，检查 `requirements.txt` 是否包含所有必需的依赖项。

### PyQt5 问题
在 Windows 上，确保 PyQt5 正确安装：
```bash
pip install PyQt5>=5.15
```

### 隐藏导入
如果应用程序在运行时报告缺少模块，在 `--hidden-import` 参数中添加相应的模块。

## 构建环境

- Python 3.8
- PyInstaller 6.0+
- Windows: windows-latest runner
- Linux: ubuntu-latest runner

构建的可执行文件不需要安装 Python 环境即可运行。