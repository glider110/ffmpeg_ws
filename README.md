
# ffmpeg_ws

#### 视频自动化剪辑开发项

- [x] 视频抽帧封面

- [x] 时间间隔剪辑

- [x] 随机组合视频素材4/9宫格拼图视频

- [x] 随机组合音频素材功能

- [x] 合成视频高清适配

- [ ] 字幕讲解开发

- [x] 视频调色功能(Luts预设来实现)

- [ ] 特效转场开发

- [ ] log标注

  



#视频语音提取
ffmpeg -i 20240603_165541.mp4 -vn -acodec libmp3lame -ab 128k output_audio.mp3
#封面裁剪
ffmpeg -i jia.mp4 -r 1 image-%3d.jpeg 
#视频裁剪
ffmpeg -i output.mp4 -f segment -segment_time 10 -c copy -reset_timestamps 1 output%03d.mp4



问题汇总:

1. Unknown encoder 'libx264'  缺少libx264

   ```makefile
   编译源码
   git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg
   cd ffmpeg
   ./configure --enable-gpl --enable-libx264
   make
   sudo make install
   ```

2. 安装moviepy不生效

   用coda安装会绑定依赖一起安装 `conda install -c conda-forge moviepy`




资源汇总
1.stt    
https://www.csubtitle.com/?gad_source=1&gclid=Cj0KCQjwh7K1BhCZARIsAKOrVqGf147u6j7L2Al3JDVEK2XfrFVXzxFHDv_-G5A_BHFmOpTzBAULlQ4aAuHLEALw_wcB