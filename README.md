<!--
 * @Author: glider
 * @Date: 2024-07-20 21:18:53
 * @LastEditTime: 2024-07-21 20:50:51
 * @FilePath: /ffmpeg_ws/README.md
 * @Version:  v0.01
 * @Descriptio
 * ************************************************************************
 * Copyright (c) 2024 by  ${git_email}, All Rights Reserved. 
 * ************************************************************************
-->

# ffmpeg_ws

#视频语音提取
ffmpeg -i 20240603_165541.mp4 -vn -acodec libmp3lame -ab 128k output_audio.mp3
#封面裁剪
ffmpeg -i jia.mp4 -r 1 image-%3d.jpeg 
#视频裁剪
ffmpeg -i output.mp4 -f segment -segment_time 10 -c copy -reset_timestamps 1 output%03d.mp4


1.多宫格视频功能开发
2.视频调色功能
3.视频抽帧封面
4.时间间隔剪辑



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


