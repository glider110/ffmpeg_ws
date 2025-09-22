#!/usr/bin/env python3
"""
PySimpleGUIQt 启动脚本 - 彻底解决库冲突版本
"""
import os
import sys

def fix_qt_conflicts():
    """解决 Qt 库冲突问题"""
    
    # 1. 预设环境变量，必须在导入任何 Qt 模块前设置
    os.environ['LC_ALL'] = 'zh_CN.UTF-8'
    os.environ['LANG'] = 'zh_CN.UTF-8'
    
    # 2. 清除可能冲突的 Qt 插件路径
    os.environ.pop('QT_PLUGIN_PATH', None)
    
    # 3. 禁用 OpenCV 的 Qt 后端
    os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
    
    # 4. 强制使用系统 krb5 库
    current_preload = os.environ.get('LD_PRELOAD', '')
    krb5_lib = '/usr/lib/x86_64-linux-gnu/libkrb5.so.3'
    if os.path.exists(krb5_lib) and krb5_lib not in current_preload:
        os.environ['LD_PRELOAD'] = f"{current_preload}:{krb5_lib}".strip(':')
    
    # 5. 移除 anaconda OpenCV 的 Qt 插件路径
    ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    if ld_path:
        paths = [p for p in ld_path.split(':') if 'cv2' not in p and p.strip()]
        if paths != ld_path.split(':'):
            os.environ['LD_LIBRARY_PATH'] = ':'.join(paths)

def main():
    # 首先修复冲突
    fix_qt_conflicts()
    
    print("正在尝试导入 PySimpleGUIQt...")
    
    try:
        # 强制重新导入，清除之前的导入缓存
        if 'PySimpleGUIQt' in sys.modules:
            del sys.modules['PySimpleGUIQt']
        
        import PySimpleGUIQt as sg
        print("✓ PySimpleGUIQt 导入成功")
        del sg
    except Exception as e:
        print(f"✗ PySimpleGUIQt 导入失败: {e}")
        
        # 尝试降级方案：直接使用 PyQt5
        try:
            print("尝试直接导入 PyQt5...")
            from PyQt5.QtWidgets import QApplication
            print("✓ PyQt5 可用，但 PySimpleGUIQt 不可用")
            print("建议：考虑直接使用 PyQt5 或 tkinter 版 PySimpleGUI")
            return
        except Exception as e2:
            print(f"✗ PyQt5 也不可用: {e2}")
            return

    # 将当前目录加入 sys.path
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    try:
        from main import QtVideoClipsApp
        print("✓ 正在启动 Qt 视频剪辑应用...")
        app = QtVideoClipsApp()
        app.run()
    except Exception as e:
        print(f"✗ 应用启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()