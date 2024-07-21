from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.fx import fadein, fadeout
from moviepy.video.tools import subtitles
 
# 加载视频剪辑
clip = VideoFileClip("4.mov")
 
# 添加淡入和淡出效果
clip = fadein.fadein(clip, 2)  # 从开始处淡入2秒
clip = fadeout.fadeout(clip, 2)  # 从结束处淡出2秒
 
# 添加字幕
subtitles_txt = [
    ("Hello, World!", 1),  # 在1秒时显示 "Hello, World!"
    ("Welcome to MoviePy", 3),  # 在3秒时显示 "Welcome to MoviePy"
]
clip = subtitles.subtitles(clip, subtitles_txt)
 
# 保存视频
clip.write_videofile("output.mp4")