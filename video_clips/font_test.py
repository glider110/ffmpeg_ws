#!/usr/bin/env python3
"""
字体测试脚本 - 测试中文字体是否正确显示
"""
import tkinter as tk
import tkinter.font as tkFont
import os
import sys

def test_font():
    print("=" * 50)
    print("字体测试程序")
    print("=" * 50)
    
    # 创建测试窗口
    root = tk.Tk()
    root.title("字体测试")
    root.geometry("600x400")
    
    # 检测可用字体
    print("检测系统字体...")
    available_fonts = tkFont.families()
    
    # 中文字体候选
    chinese_fonts = []
    candidates = [
        "song ti",               # 宋体
        "fangsong ti",           # 仿宋体
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei", 
        "SimHei",
        "Microsoft YaHei",
        "Liberation Sans",
        "DejaVu Sans"
    ]
    
    for font in candidates:
        if font in available_fonts:
            chinese_fonts.append(font)
            print(f"✓ 找到字体: {font}")
    
    if not chinese_fonts:
        print("✗ 未找到推荐的中文字体")
        chinese_fonts = ["Liberation Sans", "Arial"]  # 备用
    
    # 创建测试标签
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)
    
    tk.Label(frame, text="字体测试 Font Test", 
             font=("Arial", 16, "bold"),
             fg="blue").pack(pady=10)
    
    # 测试每个字体
    for i, font_name in enumerate(chinese_fonts[:3]):  # 最多测试3个字体
        try:
            test_font = tkFont.Font(family=font_name, size=12)
            label = tk.Label(frame, 
                           text=f"字体: {font_name} - 中文测试：视频剪辑工具", 
                           font=test_font,
                           fg="black",
                           justify=tk.LEFT)
            label.pack(anchor=tk.W, pady=5)
            
            # 测试功能标签
            func_label = tk.Label(frame,
                                text=f"[抽帧] 视频抽帧 [切割] 视频切割 [宫格] 宫格组合",
                                font=test_font,
                                fg="darkgreen")
            func_label.pack(anchor=tk.W, pady=2)
            
        except Exception as e:
            print(f"✗ 字体 {font_name} 测试失败: {e}")
    
    # 添加退出按钮
    quit_btn = tk.Button(frame, text="退出测试", command=root.quit,
                        font=("Liberation Sans", 10))
    quit_btn.pack(pady=20)
    
    print("\n字体测试窗口已打开，请检查中文显示效果...")
    print("如果中文显示正常，则字体配置成功")
    print("如果显示异常，可能需要安装额外的中文字体包")
    
    root.mainloop()

if __name__ == "__main__":
    try:
        test_font()
    except Exception as e:
        print(f"字体测试失败: {e}")
        import traceback
        traceback.print_exc()