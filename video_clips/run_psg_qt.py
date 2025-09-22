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
    
    # 解决 krb5 库冲突：强制使用系统库
    # 移除 ROS 等可能冲突的库路径
    ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    if '/opt/ros' in ld_path:
        # 过滤掉 ROS 路径
        paths = [p for p in ld_path.split(':') if '/opt/ros' not in p and p]
        os.environ['LD_LIBRARY_PATH'] = ':'.join(paths)
    
    # 强制 Qt 使用系统 XCB 插件
    os.environ.setdefault('QT_PLUGIN_PATH', '/usr/lib/x86_64-linux-gnu/qt5/plugins')
    
    # 预加载系统 krb5 库
    preload = os.environ.get('LD_PRELOAD', '')
    krb5_lib = '/usr/lib/x86_64-linux-gnu/libkrb5.so.3'
    if os.path.exists(krb5_lib) and krb5_lib not in preload:
        os.environ['LD_PRELOAD'] = f"{preload}:{krb5_lib}".lstrip(':')


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
    from main_qt5 import QtVideoClipsApp

    app = QtVideoClipsApp()
    app.run()


if __name__ == '__main__':
    main()
