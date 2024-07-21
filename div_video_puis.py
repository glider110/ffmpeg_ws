import os
import random
from moviepy.editor import VideoFileClip, clips_array

def create_grid_video(grid_size, clip_duration):
    # 设置视频文件夹路径
    video_folder = "./sock"

    # 获取文件夹中所有视频文件
    video_files = [os.path.join(video_folder, f) for f in os.listdir(video_folder) if f.endswith(('.mp4', '.avi', '.mov', '.MOV'))]

    # 确保有足够的视频文件可用
    if len(video_files) < grid_size:
        raise ValueError("Not enough video files in the folder to create a grid.")

    # 随机选择视频文件
    selected_videos = random.sample(video_files, grid_size)

    # 从每个视频中随机裁剪指定秒数的片段并调整尺寸
    clips = []
    for video in selected_videos:
        clip = VideoFileClip(video)
        max_start = clip.duration - clip_duration
        if max_start < 0:
            raise ValueError(f"The video {video} is too short to extract {clip_duration} seconds.")
        start_time = random.uniform(0, max_start)
        end_time = start_time + clip_duration
        clip_resized = clip.subclip(start_time, end_time).resize(newsize=(clip.size[0] // int(grid_size**0.5), clip.size[1] // int(grid_size**0.5)))
        clips.append(clip_resized)

    # 组合视频片段
    final_clip = clips_array([clips[i:i+int(grid_size**0.5)] for i in range(0, grid_size, int(grid_size**0.5))])

    # 输出最终的视频文件
    final_clip.write_videofile(f"{grid_size}_grid_video.mp4", codec="libx264")

# 用户输入
grid_size = int(input("Enter the grid size (4 for 2x2, 9 for 3x3): "))
clip_duration = int(input("Enter the clip duration in seconds: "))

# 调用函数
create_grid_video(grid_size, clip_duration)
