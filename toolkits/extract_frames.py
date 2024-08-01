'''
Author: glider
Date: 2024-08-01 22:05:09
LastEditTime: 2024-08-01 22:14:22
FilePath: /ffmpeg_ws/toolkits/extrack_frame.py
Version:  v0.01
Description: 
************************************************************************
Copyright (c) 2024 by  ${git_email}, All Rights Reserved. 
************************************************************************
'''
import os
import subprocess

def extract_frames(video_path, output_dir):
    """
    使用 ffmpeg 从视频中每秒提取一帧并保存为 PNG 图片。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # 如果输出目录不存在，则创建
    
    video_name = os.path.splitext(os.path.basename(video_path))[0]  # 获取视频文件的基本名称，无扩展名
    
    # 构建 ffmpeg 命令
    command = [
        'ffmpeg',
        '-i', video_path,  # 输入视频路径
        '-vf', 'fps=1,format=yuv420p',  # 设置每秒提取一帧，并指定颜色格式
        '-compression_level', '0',  # 设置无损压缩
        os.path.join(output_dir, f'{video_name}-%3d.png')  # 输出文件路径和格式，包含视频名
    ]
    
    # 执行 ffmpeg 命令
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def process_all_videos(directory):
    """
    遍历给定目录中的所有视频文件并提取帧。
    """
    # 支持的视频格式列表
    supported_formats = ['.mp4', '.mov', '.avi']
    
    output_dir = os.path.join(directory, 'output')  # 定义输出目录路径
    for filename in os.listdir(directory):
        file_ext = os.path.splitext(filename)[1].lower()  # 获取文件扩展名，并转换为小写
        if file_ext in supported_formats:
            video_path = os.path.join(directory, filename)
            extract_frames(video_path, output_dir)
            print(f'Processed {filename}')

if __name__ == '__main__':
    video_directory = os.path.dirname(os.path.abspath(__file__))  # 获取脚本所在目录
    process_all_videos(video_directory)
