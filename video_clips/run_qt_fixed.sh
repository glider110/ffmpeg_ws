#!/bin/bash
# Qt 应用启动脚本 - 解决 krb5 库冲突

# 保存原始环境
original_ld_path="$LD_LIBRARY_PATH"

# 清除冲突的库路径（包括 OpenCV 的 Qt 插件）
export LD_LIBRARY_PATH=""

# 强制使用系统库
export LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libkrb5.so.3"

# 正确设置 Qt 插件路径 - 不要设置 QT_PLUGIN_PATH，让 Qt 自动寻找
unset QT_PLUGIN_PATH

# 中文环境
export LANG="zh_CN.UTF-8"
export LC_ALL="zh_CN.UTF-8"

# 禁用 OpenCV 的 Qt 后端，避免插件冲突
export OPENCV_VIDEOIO_PRIORITY_MSMF=0

echo "正在启动 Qt 应用..."
echo "LD_PRELOAD: $LD_PRELOAD"

# 运行脚本
python3 "$(dirname "$0")/run_psg_qt.py"

# 恢复环境
export LD_LIBRARY_PATH="$original_ld_path"
unset LD_PRELOAD