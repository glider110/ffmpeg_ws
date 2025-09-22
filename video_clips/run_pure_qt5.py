"""
PyQt5 版本的视频剪辑应用启动器
直接使用 PyQt5，避免 PySimpleGUIQt 的库冲突问题
"""
import sys
import os

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    try:
        from PyQt5.QtWidgets import QApplication
        
        print("✓ PyQt5 导入成功，正在创建应用...")
        
        # 导入我们的主窗口类
        from main_qt5 import QtVideoClipsApp
        
        app = QtVideoClipsApp()
        
        print("✓ 视频剪辑应用启动成功")
        
        return app.run()
        
    except Exception as e:
        print(f"✗ PyQt5 应用启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())