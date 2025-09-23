import os
import random
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.ttk import Progressbar
from moviepy.editor import VideoFileClip

def generate_ffmpeg_grid_command(input_files, output_file, grid_size, duration, music_folder):
    filter_complex_commands = []
    for i, file in enumerate(input_files):
        clip = VideoFileClip(file)
        max_start = clip.duration - duration
        start_time = random.uniform(0, max_start) if max_start > 0 else 0
        filter_complex_commands.append(
            f"[{i}:v] trim=start={start_time}:duration={duration}, setpts=PTS-STARTPTS, scale=iw/{int(grid_size**0.5)}:ih/{int(grid_size**0.5)}:flags=lanczos, setsar=1 [video{i}]"
        )

    xstack_inputs = ''.join([f"[video{i}]" for i in range(len(input_files))])
    layout = {
        4: '0_0|w0_0|0_h0|w0_h0',
        9: '0_0|w0_0|w0+w0_0|0_h0|w0_h0|w0+w0_h0|0_h0+h0|w0_h0+h0|w0+w0_h0+h0'
    }[grid_size]
    filter_complex_commands.append(
        f"{xstack_inputs}xstack=inputs={len(input_files)}:layout={layout} [v]"
    )

    # 随机选择一个音乐文件
    music_files = [os.path.join(music_folder, f) for f in os.listdir(music_folder) if f.endswith('.mp3')]
    selected_music = random.choice(music_files)

    # 添加音乐处理命令
    filter_complex_commands.append(f"[{len(input_files)}:a] atrim=start=0:duration={duration}, asetpts=PTS-STARTPTS [a]")

    cmd = ['ffmpeg', '-y']
    for file in input_files:
        cmd += ['-i', file]
    cmd += ['-i', selected_music]
    # cmd += ['-filter_complex', '; '.join(filter_complex_commands), '-map', '[v]', '-map', '[a]',  '-b:v', '5000k', '-c:a', 'aac', '-b:a', '320k', output_file]
    cmd += ['-filter_complex', '; '.join(filter_complex_commands), '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'slow', '-b:v', '8000k', '-c:a', 'aac', '-b:a', '320k', output_file]
    return cmd


def create_grid_video(grid_size, clip_duration, video_folder, num_videos, music_folder, progress_callback):
    video_files = [os.path.join(video_folder, f) for f in os.listdir(video_folder) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    if len(video_files) < grid_size:
        raise ValueError("文件夹中的视频文件不足以创建网格。")
    
    for i in range(num_videos):
        selected_videos = random.sample(video_files, grid_size)
        output_filename = f"{video_folder}/../output/{grid_size}_grid_video_{i+1}.mp4"
        cmd = generate_ffmpeg_grid_command(selected_videos, output_filename, grid_size, clip_duration, music_folder)
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode != 0:
            print(f"处理视频 {i+1} 时出错: {process.stderr.decode()}")
            continue
        progress_callback(i + 1)

def submit():
    try:
        grid_size = int(grid_var.get())
        clip_duration = int(duration_entry.get())
        num_videos = int(number_entry.get())
        video_folder = folder_path.get()
        music_folder = folder_path_music.get()
        if clip_duration < 1 or num_videos < 1:
            raise ValueError("视频持续时间和数量必须至少为1。")
        if not os.path.exists(video_folder) or not os.path.exists(music_folder):
            raise ValueError("提供的视频或音乐文件夹路径无效。")

        progress_bar["maximum"] = num_videos
        def update_progress(num):
            progress_bar["value"] = num
            root.update_idletasks()

        create_grid_video(grid_size, clip_duration, video_folder, num_videos, music_folder, update_progress)
        messagebox.showinfo("Success", "所有视频已成功生成。")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def browse_folder_video():
    directory = filedialog.askdirectory()
    if directory:
        folder_path.set(directory)

def browse_folder_music():
    directory = filedialog.askdirectory()
    if directory:
        folder_path_music.set(directory)

root = tk.Tk()
root.title("Video Grid Generator")
style = ttk.Style(root)
style.theme_use('clam')

grid_var = tk.IntVar(value=4)
folder_path = tk.StringVar()
folder_path_music = tk.StringVar()

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

ttk.Label(frame, text="Video Folder:").grid(column=0, row=0, sticky=tk.W)
folder_entry = ttk.Entry(frame, textvariable=folder_path, width=50)
folder_entry.grid(column=1, row=0, sticky=(tk.W, tk.E))
browse_button_video = ttk.Button(frame, text="Browse Video", command=browse_folder_video)
browse_button_video.grid(column=2, row=0)

ttk.Label(frame, text="Music Folder:").grid(column=0, row=1, sticky=tk.W)
music_entry = ttk.Entry(frame, textvariable=folder_path_music, width=50)
music_entry.grid(column=1, row=1, sticky=(tk.W, tk.E))
browse_button_music = ttk.Button(frame, text="Browse Music", command=browse_folder_music)
browse_button_music.grid(column=2, row=1)

ttk.Label(frame, text="Number of Videos:").grid(column=0, row=2, sticky=tk.W)
number_entry = ttk.Entry(frame)
number_entry.grid(column=1, row=2, columnspan=2, sticky=(tk.W, tk.E))

ttk.Label(frame, text="Clip Duration (seconds):").grid(column=0, row=3, sticky=tk.W)
duration_entry = ttk.Entry(frame)
duration_entry.grid(column=1, row=3, columnspan=2, sticky=(tk.W, tk.E))

ttk.Radiobutton(frame, text="4 Grid (2x2)", variable=grid_var, value=4).grid(column=0, row=4, sticky=tk.W)
ttk.Radiobutton(frame, text="9 Grid (3x3)", variable=grid_var, value=9).grid(column=1, row=4, sticky=tk.W)

submit_button = ttk.Button(frame, text="Generate Videos", command=submit)
submit_button.grid(column=0, row=5, columnspan=3)

progress_bar = Progressbar(frame, orient="horizontal", length=200, mode="determinate")
progress_bar.grid(column=0, row=6, columnspan=3, sticky=(tk.W, tk.E))

root.mainloop()
