import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from moviepy.editor import VideoFileClip, clips_array
from tkinter.ttk import Progressbar


def create_grid_video(grid_size, clip_duration, video_folder, num_videos, progress_callback):
    video_files = [os.path.join(video_folder, f) for f in os.listdir(video_folder) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    if len(video_files) < grid_size:
        raise ValueError("Not enough video files in the folder to create a grid.")
    
    for i in range(num_videos):
        selected_videos = random.sample(video_files, grid_size)
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
        final_clip = clips_array([clips[j:j+int(grid_size**0.5)] for j in range(0, grid_size, int(grid_size**0.5))])
        output_filename = f"{video_folder}/{grid_size}_grid_video_{i+1}.mp4"
        final_clip.write_videofile(output_filename, codec="libx264")
        progress_callback(i + 1)  # Update progress

def submit():
    try:
        grid_size = int(grid_var.get())
        clip_duration = int(duration_entry.get())
        num_videos = int(number_entry.get())
        video_folder = folder_path.get()
        if clip_duration < 1 or num_videos < 1:
            raise ValueError("Duration and number of videos must be at least 1.")
        if not os.path.exists(video_folder):
            raise ValueError("Invalid video folder path provided.")

        progress_bar["maximum"] = num_videos
        def update_progress(num):
            progress_bar["value"] = num
            root.update_idletasks()

        create_grid_video(grid_size, clip_duration, video_folder, num_videos, update_progress)
        messagebox.showinfo("Success", "All videos generated successfully.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def browse_folder():
    directory = filedialog.askdirectory()
    if directory:
        folder_path.set(directory)

root = tk.Tk()
root.title("Video Grid Generator")
style = ttk.Style(root)
style.theme_use('clam')  # Modern theme

grid_var = tk.IntVar(value=4)
folder_path = tk.StringVar()

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

ttk.Label(frame, text="Video Folder:").grid(column=0, row=0, sticky=tk.W)
folder_entry = ttk.Entry(frame, textvariable=folder_path, width=50)
folder_entry.grid(column=1, row=0, sticky=(tk.W, tk.E))
browse_button = ttk.Button(frame, text="Browse", command=browse_folder)
browse_button.grid(column=2, row=0)

ttk.Label(frame, text="Number of Videos:").grid(column=0, row=1, sticky=tk.W)
number_entry = ttk.Entry(frame)
number_entry.grid(column=1, row=1, columnspan=2, sticky=(tk.W, tk.E))

ttk.Label(frame, text="Clip Duration (seconds):").grid(column=0, row=2, sticky=tk.W)
duration_entry = ttk.Entry(frame)
duration_entry.grid(column=1, row=2, columnspan=2, sticky=(tk.W, tk.E))

ttk.Radiobutton(frame, text="4 Grid (2x2)", variable=grid_var, value=4).grid(column=0, row=3, sticky=tk.W)
ttk.Radiobutton(frame, text="9 Grid (3x3)", variable=grid_var, value=9).grid(column=1, row=3, sticky=tk.W)

submit_button = ttk.Button(frame, text="Generate Videos", command=submit)
submit_button.grid(column=0, row=4, columnspan=3)

progress_bar = Progressbar(frame, orient="horizontal", length=200, mode="determinate")
progress_bar.grid(column=0, row=5, columnspan=3, sticky=(tk.W, tk.E))

root.mainloop()
