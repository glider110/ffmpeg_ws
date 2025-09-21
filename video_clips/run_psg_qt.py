#!/usr/bin/env python3
"""
PySimpleGUIQt 启动脚本
复用 video_clips.main 中的 QtVideoClipsApp（不改变剪辑逻辑）。
"""
import os
import sys


def ensure_env():
    # 设定中文环境以避免界面乱码
    os.environ.setdefault('LANG', 'zh_CN.UTF-8')
    os.environ.setdefault('LC_ALL', 'zh_CN.UTF-8')
    # 可按需调节 UI 缩放与基础字号
    os.environ.setdefault('VIDEO_CLIPS_UI_SCALE', '1.0')
    os.environ.setdefault('VIDEO_CLIPS_BASE_FONT', '11')


def main():
    ensure_env()

    try:
        import PySimpleGUIQt as sg  # 确认依赖可用
        del sg
    except Exception as e:
        print("未检测到 PySimpleGUIQt，或其依赖未安装。\n"
              "请先安装依赖: pip install PySimpleGUIQt PyQt5\n"
              f"详细错误: {e}")
        sys.exit(1)

    # 将当前目录加入 sys.path 以便导入本包模块
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    # 导入并启动 Qt 版 GUI
    from main import QtVideoClipsApp

    app = QtVideoClipsApp()
    app.run()


if __name__ == '__main__':
    main()
