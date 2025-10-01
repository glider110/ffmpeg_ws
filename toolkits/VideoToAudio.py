'''
Author: glider
Date: 2024-08-11 09:09:05
LastEditTime: 2025-10-01 13:03:05
FilePath: /ffmpeg_ws/toolkits/VideoToAudio.py
Version:  v0.01
Description: 
************************************************************************
Copyright (c) 2024 by  ${git_email}, All Rights Reserved. 
************************************************************************
'''
import os
import subprocess

# 定义输入和输出目录
input_dir = "./input"   # 将这个路径替换为你的视频文件夹路径
output_dir = "./output" # 将这个路径替换为你想要保存MP3文件的路径

# 创建输出目录，如果不存在
os.makedirs(output_dir, exist_ok=True)

# 遍历输入目录中的所有文件
for filename in os.listdir(input_dir):
    # 构建完整的输入文件路径
    input_file = os.path.join(input_dir, filename)
    
    # 检查是否为文件且不是目录
    if os.path.isfile(input_file):
        # 提取文件名和扩展名
        file_base, file_extension = os.path.splitext(filename)
        
        # 设置输出文件路径
        output_file = os.path.join(output_dir, f"{file_base}.mp3")
        
        # 使用FFmpeg将视频转换为高质量MP3
        subprocess.run([
            "ffmpeg", "-i", input_file, "-b:a", "320k", "-map", "a", output_file
        ])

print("所有文件已成功转换为高质量MP3格式！")
