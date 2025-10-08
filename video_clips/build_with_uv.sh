#!/bin/bash
# UV 专用构建脚本 - 直接使用 uv 管理的 Python 环境

set -e

echo "========================================="
echo "视频剪辑工具 - UV 环境构建"
echo "========================================="
echo

cd "$(dirname "$0")"

# 检查是否在项目根目录的 uv 环境中
if [[ ! -f "../pyproject.toml" ]]; then
    echo "错误：请确保在正确的项目目录中"
    exit 1
fi

# 显示当前环境信息
echo "当前环境信息："
echo "Python 版本: $(python --version)"
echo "Python 路径: $(which python)"
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "虚拟环境: $VIRTUAL_ENV"
else
    echo "未检测到虚拟环境标记，但可能在 uv 环境中"
fi
echo

# 检查 PyInstaller 是否可用
echo "检查 PyInstaller..."
if python -c "import PyInstaller" 2>/dev/null; then
    echo "✓ PyInstaller 已安装: $(python -c 'import PyInstaller; print(PyInstaller.__version__)')"
else
    echo "PyInstaller 未安装，正在安装..."
    cd .. && uv add pyinstaller && cd video_clips
fi

echo

# 检查核心依赖
echo "检查核心依赖..."
python -c "
import sys
print('Python 版本:', sys.version)
try:
    import PyQt5
    print('✓ PyQt5 已安装')
except ImportError:
    print('✗ PyQt5 未安装')
    sys.exit(1)

try:
    import numpy
    print('✓ NumPy 已安装')
except ImportError:
    print('✗ NumPy 未安装')
    sys.exit(1)

try:
    import PIL
    print('✓ Pillow 已安装')
except ImportError:
    print('✗ Pillow 未安装') 
    sys.exit(1)

print('✓ 所有核心依赖检查通过')
"

if [ $? -ne 0 ]; then
    echo "依赖检查失败，请确保所有必要包已安装"
    exit 1
fi

echo
echo "开始构建..."

# 清理之前的构建
rm -rf build/ dist/ release/

# 检查主文件
if [ ! -f "main_qt5.py" ]; then
    echo "错误：找不到 main_qt5.py"
    exit 1
fi

# 使用 PyInstaller 构建
echo "执行 PyInstaller 构建..."
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
    --collect-submodules "PyQt5" \
    --collect-submodules "numpy" \
    --collect-submodules "PIL" \
    main_qt5.py

if [ $? -eq 0 ]; then
    echo
    echo "PyInstaller 构建成功！"
    
    # 创建发布包
    echo "创建发布包..."
    mkdir -p release
    
    if [ -d "dist/VideoClipsApp" ]; then
        cp -r dist/VideoClipsApp release/
        
        # 创建 Windows 运行脚本
        cat > release/run_app.bat << 'EOF'
@echo off
echo 启动视频剪辑工具...
cd /d "%~dp0"
cd VideoClipsApp
VideoClipsApp.exe
if errorlevel 1 (
    echo 程序运行出错，按任意键退出...
    pause
)
EOF
        
        # 创建 Linux 运行脚本
        cat > release/run_app.sh << 'EOF'
#!/bin/bash
echo "启动视频剪辑工具..."
cd "$(dirname "$0")"
cd VideoClipsApp
./VideoClipsApp
EOF
        chmod +x release/run_app.sh
        
        # 创建详细说明
        cat > release/README.txt << EOF
视频剪辑工具 - Windows 可执行版本
=====================================

构建信息：
- 构建时间: $(date)
- Python 版本: $(python --version)
- PyInstaller 版本: $(python -c 'import PyInstaller; print(PyInstaller.__version__)')
- 构建环境: Ubuntu + UV Python 环境

使用方法：
1. Windows 系统：双击 run_app.bat
2. Linux 系统：运行 ./run_app.sh
3. 直接运行：进入 VideoClipsApp 文件夹，运行主程序

系统要求：
- Windows 10/11 (64位) 
- 2GB+ 内存
- DirectX 支持

注意事项：
- 首次运行可能需要几秒启动时间
- 如遇到问题，请检查 Windows 防火墙设置
- 建议在目标系统上测试所有功能

技术支持：
如有问题，请提供完整的错误信息和系统环境。
EOF
        
        echo
        echo "========================================="
        echo "🎉 构建完成！"
        echo "========================================="
        echo
        echo "✅ 构建环境："
        echo "   - Python: $(python --version)"
        echo "   - PyInstaller: $(python -c 'import PyInstaller; print(PyInstaller.__version__)')"
        echo "   - 构建模式: UV 环境 + 跨平台"
        echo
        echo "📁 输出位置:"
        echo "   - 发布包: ./release/"
        echo "   - 应用程序: ./release/VideoClipsApp/"
        echo
        echo "🚀 Windows 使用方法:"
        echo "   1. 复制 release 文件夹到 Windows 系统"
        echo "   2. 双击 run_app.bat 运行"
        echo
        echo "🎯 优势:"
        echo "   ✓ 使用最新 Python 3.8.20"
        echo "   ✓ PyInstaller 6.x 最新版本"
        echo "   ✓ UV 环境管理，依赖清晰"
        echo "   ✓ 跨平台构建，Windows 兼容"
        
    else
        echo "❌ 错误：构建产物不存在于 dist/VideoClipsApp"
        echo "请检查构建日志中的错误信息"
        exit 1
    fi
    
else
    echo "❌ PyInstaller 构建失败"
    echo
    echo "故障排除："
    echo "1. 检查所有模块文件是否存在"
    echo "2. 确保在正确的 uv 环境中"
    echo "3. 查看上面的详细错误信息"
    echo "4. 尝试手动运行: python main_qt5.py"
    exit 1
fi