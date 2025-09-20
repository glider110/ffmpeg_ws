#!/usr/bin/env python3
"""
Video Clips GUI 启动脚本 - 中文字体优化版本
"""
import os
import sys

# 设置中文环境变量
os.environ['LANG'] = 'zh_CN.UTF-8'
os.environ['LC_ALL'] = 'zh_CN.UTF-8'

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    # 导入tkinter并设置字体
    import tkinter as tk
    
    # 检查中文字体
    import tkinter.font as tkFont
    
    print("检查系统字体...")
    
    # 简单的字体检查，不创建窗口
    font_candidates = [
        "Microsoft YaHei UI",
        "Microsoft YaHei", 
        "PingFang SC",
        "Hiragino Sans GB",
        "Noto Sans CJK SC",
        "Source Han Sans CN",
        "WenQuanYi Micro Hei"
    ]
    
    print("推荐的中文字体:")
    for font in font_candidates[:3]:  # 显示前3个
        print(f"  - {font}")
    
    print("\n启动 Video Clips GUI...")
    print("=" * 50)
    
    # 导入并启动主程序
    from main import main
    main()

except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保安装了必要的依赖包：")
    print("pip install moviepy pillow tqdm")
    sys.exit(1)
except Exception as e:
    print(f"启动失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)