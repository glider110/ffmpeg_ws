#!/usr/bin/env python3
"""
Video Clips 启动脚本
简单的启动入口，用于从项目根目录启动GUI
"""

import sys
import os

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from main import VideoClipsGUI
    
    def main():
        print("启动 Video Clips 智能视频剪辑工具...")
        
        # 检查依赖
        missing_deps = []
        
        try:
            import tkinter
        except ImportError:
            missing_deps.append("tkinter")
        
        try:
            import moviepy
        except ImportError:
            missing_deps.append("moviepy")
        
        if missing_deps:
            print(f"缺少依赖包: {', '.join(missing_deps)}")
            print("请运行: pip install -r requirements.txt")
            return
        
        # 启动GUI
        app = VideoClipsGUI()
        app.run()
    
    if __name__ == "__main__":
        main()
        
except Exception as e:
    print(f"启动失败: {e}")
    print("请确保在 video_clips 目录下运行此脚本")
    import traceback
    traceback.print_exc()