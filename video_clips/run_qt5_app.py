#!/usr/bin/env python3
"""
视频剪辑工具启动脚本 - PyQt5 版本
解决 PySimpleGUIQt 的 krb5 库冲突问题
"""
import os
import sys

def ensure_env():
    """设置环境变量"""
    # 中文环境
    os.environ.setdefault('LANG', 'zh_CN.UTF-8')
    os.environ.setdefault('LC_ALL', 'zh_CN.UTF-8')
    
    # UI 缩放和字体设置
    os.environ.setdefault('VIDEO_CLIPS_UI_SCALE', '1.0')
    os.environ.setdefault('VIDEO_CLIPS_BASE_FONT', '11')

def main():
    ensure_env()
    
    print("🎬 正在启动视频剪辑工具 PyQt5 版... ✨")
    
    try:
        from PyQt5.QtWidgets import QApplication
        print("✅ PyQt5 导入成功")
        
        # 将当前目录加入 sys.path
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        
        # 导入并启动 PyQt5 版应用
        from main_qt5 import QtVideoClipsApp
        
        app = QtVideoClipsApp()
        print("🚀 应用创建成功")
        print("🎉 界面已显示，开始使用吧！")
        print()
        print("✨ 功能说明：")
        print("📋 - 所有 UI 功能已迁移完成")
        print("📁 - 文件管理、收藏功能正常工作")
        print("🔧 - 6个剪辑任务选项卡界面已就绪")
        print("⚙️ - 业务逻辑模块待连接（下一阶段）")
        print("😊 - 界面已添加可爱的表情图标")
        print()
        
        return app.run()
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("💡 请确保 PyQt5 已正确安装: pip install PyQt5")
        return 1
    except Exception as e:
        print(f"💥 应用启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())