import os
import random
import tkinter as tk
from tkinter import simpledialog
from moviepy.editor import VideoFileClip, clips_array

def create_grid_video(grid_size, clip_duration, video_folder, output_filename):
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
    final_clip.write_videofile(output_filename, codec="libx264")

def main():
    # 创建一个Tk窗口对象
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_reqwidth()) / 2
    y = (root.winfo_screenheight() - root.winfo_reqheight()) / 2
    root.geometry(f"+{int(x)}+{int(y)}")

    try:
        # 使用simpledialog询问用户输入
        video_folder = simpledialog.askstring("Input", "Enter the path to your video folder:", parent=root)
        if not video_folder or not os.path.exists(video_folder):
            raise ValueError("Invalid video folder path provided.")
        num_videos = simpledialog.askinteger("Input", "Enter the number of videos to generate:", parent=root)
        if not num_videos or num_videos < 1:
            raise ValueError("Invalid number of videos specified.")
        grid_size = simpledialog.askinteger("Input", "Enter the grid size (4 for 2x2, 9 for 3x3):", parent=root, minvalue=4, maxvalue=9)
        clip_duration = simpledialog.askinteger("Input", "Enter the clip duration in seconds:", parent=root, minvalue=1, maxvalue=30)

        # 循环生成视频
        for i in range(num_videos):
            output_filename = f"{video_folder}/{grid_size}_grid_video_{i+1}.mp4"
            create_grid_video(grid_size, clip_duration, video_folder, output_filename)
            print(f"Video {i+1} generated successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        root.destroy()

if __name__ == "__main__":
    main()
