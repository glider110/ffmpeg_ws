'''
Author: glider
Date: 2024-07-21 21:53:21
LastEditTime: 2024-07-21 21:57:03
FilePath: /ffmpeg_ws/div_video_9.py
Version:  v0.01
Description: 
************************************************************************
Copyright (c) 2024 by  ${git_email}, All Rights Reserved. 
************************************************************************
'''
from moviepy.editor import VideoFileClip, clips_array

# 载入原始视频文件
video = VideoFileClip("11.mp4")

# 获取视频总时长和原始尺寸
total_duration = video.duration
original_width, original_height = video.size

# 计算每部分的时长
segment_duration = total_duration / 9

# 分割视频为九部分
parts = [video.subclip(i * segment_duration, (i + 1) * segment_duration) for i in range(9)]

# 调整每个片段的尺寸为原始尺寸的三分之一
third_width = original_width / 3
third_height = original_height / 3
resized_parts = [part.resize(width=third_width, height=third_height) for part in parts]

# 组合视频片段成三行三列
final_clip = clips_array([[resized_parts[0], resized_parts[1], resized_parts[2]],
                          [resized_parts[3], resized_parts[4], resized_parts[5]],
                          [resized_parts[6], resized_parts[7], resized_parts[8]]])

# 输出最终的视频文件
final_clip.write_videofile("nine_grid_video.mp4", codec="libx264")
