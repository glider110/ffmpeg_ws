#!/bin/bash
# UV Python 环境专用构建脚本 - 使用当前激活的 uv Python 环境

set -e

echo "========================================="
echo "视频剪辑工具 - UV Python 环境构建"
echo "========================================="
echo

cd "$(dirname "$0")"

# 检查是否在 uv 环境中
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "警告：当前不在虚拟环境中"
    echo "请先激活 uv 环境："
    echo "cd /home/admins/project/ffmpeg_ws && uv shell"
    exit 1
fi

# 显示当前 Python 环境信息
echo "当前 Python 环境："
echo "Python 版本: $(python --version)"
echo "Python 路径: $(which python)"
echo "虚拟环境: $VIRTUAL_ENV"
echo

# 升级 pip 和安装工具
echo "升级构建工具..."
python -m pip install --upgrade pip setuptools wheel

# 安装 PyInstaller (使用较新版本，支持 Python 3.8)
echo "安装 PyInstaller..."
python -m pip install "pyinstaller>=5.0,<7.0"

# 安装其他必要的构建依赖（如果还没有）
echo "检查并安装必要依赖..."
python -c "
import sys
missing = []
try:
    import PyQt5
    print('✓ PyQt5 已安装')
except ImportError:
    missing.append('PyQt5>=5.15')

try:
    import numpy
    print('✓ NumPy 已安装')
except ImportError:
    missing.append('numpy>=1.20')

try:
    import PIL
    print('✓ Pillow 已安装')
except ImportError:
    missing.append('Pillow>=8.0')

try:
    import moviepy
    print('✓ MoviePy 已安装')
except ImportError:
    missing.append('moviepy>=1.0.3')

if missing:
    print(f'需要安装: {missing}')
    sys.exit(1)
else:
    print('✓ 所有核心依赖都已安装')
"

if [ $? -ne 0 ]; then
    echo "正在安装缺失的依赖..."
    python -m pip install PyQt5>=5.15 numpy>=1.20 Pillow>=8.0 moviepy>=1.0.3
fi

echo "依赖检查完成"
echo

# 清理构建
echo "清理之前的构建..."
rm -rf build/ dist/ release/

# 检查 main_qt5.py 是否存在
if [ ! -f "main_qt5.py" ]; then
    echo "错误：找不到 main_qt5.py 文件"
    exit 1
fi

# 使用 PyInstaller 5.x+ 构建（支持 Python 3.8）
echo "开始构建 (使用当前 uv Python 环境)..."
python -m PyInstaller \
    --clean \
    --noconfirm \
    --onedir \
    --windowed \
    --name "VideoClipsApp" \
    --distpath "dist" \
    --workpath "build" \
    --specpath "." \
    --paths "." \
    --paths ".." \
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
    --hidden-import "moviepy.editor" \
    --hidden-import "moviepy.video.io.VideoFileClip" \
    --hidden-import "moviepy.audio.io.AudioFileClip" \
    --collect-submodules "PyQt5" \
    --collect-submodules "numpy" \
    --collect-submodules "PIL" \
    --collect-submodules "moviepy" \
    main_qt5.py

if [ $? -eq 0 ]; then
    echo
    echo "构建成功！"
    
    # 创建发布包
    echo "创建发布包..."
    mkdir -p release
    
    if [ -d "dist/VideoClipsApp" ]; then
        cp -r dist/VideoClipsApp release/
        
        # 创建运行脚本
        cat > release/run_app.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
cd VideoClipsApp
./VideoClipsApp
EOF
        chmod +x release/run_app.sh
        
        # Windows 批处理文件
        cat > release/run_app.bat << 'EOF'
@echo off
cd /d "%~dp0"
cd VideoClipsApp
VideoClipsApp.exe
pause
EOF
        
        # 创建说明文件
        cat > release/使用说明.txt << EOF
视频剪辑工具 Windows 版本

运行方法：
1. 双击 run_app.bat (Windows)
2. 或直接进入 VideoClipsApp 文件夹运行 VideoClipsApp.exe

注意：
- 此版本使用 UV Python 3.8.20 环境构建
- 使用了 PyInstaller 5.x+ 版本
- 在 Ubuntu 系统上跨平台构建
- 建议在目标系统上测试所有功能

技术信息：
- 构建环境: Ubuntu Linux (UV Python 环境)
- Python 版本: $(python --version)
- Python 路径: $(which python)
- PyInstaller 版本: 5.x+
- 构建时间: $(date)
EOF
        
        # 显示构建信息
        echo
        echo "========================================="
        echo "构建完成！"
        echo "========================================="
        echo
        echo "构建环境信息："
        echo "- Python: $(python --version)"
        echo "- 环境路径: $VIRTUAL_ENV"
        echo "- PyInstaller: $(python -m PyInstaller --version)"
        echo
        echo "发布包位置: ./release/"
        echo "应用程序: ./release/VideoClipsApp/"
        echo
        echo "在 Windows 上使用："
        echo "1. 复制整个 release 文件夹到 Windows 系统"
        echo "2. 双击 run_app.bat 运行程序"
        echo
        echo "优势："
        echo "- 使用最新的 Python 3.8.20 和 PyInstaller 5.x+"
        echo "- UV 环境管理，依赖清晰"
        echo "- 更好的兼容性和稳定性"
        
    else
        echo "错误：构建产物不存在"
        exit 1
    fi
    
else
    echo "构建失败！"
    echo
    echo "可能的解决方案："
    echo "1. 确保在正确的 uv 环境中"
    echo "2. 检查所有依赖是否正确安装"
    echo "3. 确保 main_qt5.py 和相关模块文件存在"
    echo "4. 查看上面的错误信息"
    exit 1
fi