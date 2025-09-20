"""
功能5: 音乐配对模块
从音乐库随机选择音乐，配对到视频上，支持音量控制、淡入淡出等效果
"""
import os
import random
import subprocess
from typing import List, Optional, Callable, Tuple
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
from config.settings import Settings


class AudioMixer:
    """音频混音器"""
    
    def __init__(self):
        self.settings = Settings()
    
    def get_audio_files(self, music_dir: str = None) -> List[str]:
        """
        获取音乐库中的音频文件
        
        Args:
            music_dir: 音乐目录路径，默认使用settings中的配置
            
        Returns:
            List[str]: 音频文件路径列表
        """
        if music_dir is None:
            music_dir = self.settings.MUSIC_DIR
        
        if not os.path.exists(music_dir):
            print(f"音乐目录不存在: {music_dir}")
            return []
        
        audio_files = []
        for root, dirs, files in os.walk(music_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.settings.SUPPORTED_AUDIO_FORMATS):
                    audio_files.append(os.path.join(root, file))
        
        print(f"找到 {len(audio_files)} 个音频文件")
        return audio_files
    
    def select_random_music(self, music_dir: str = None, duration: float = None) -> Optional[str]:
        """
        随机选择一个音乐文件
        
        Args:
            music_dir: 音乐目录路径
            duration: 视频时长，用于筛选合适长度的音乐
            
        Returns:
            Optional[str]: 选中的音乐文件路径
        """
        audio_files = self.get_audio_files(music_dir)
        
        if not audio_files:
            return None
        
        if duration is None:
            # 随机选择
            return random.choice(audio_files)
        
        # 根据视频时长筛选合适的音乐
        suitable_music = []
        for audio_file in audio_files:
            try:
                with AudioFileClip(audio_file) as audio:
                    audio_duration = audio.duration
                    # 选择时长大于视频的音乐
                    if audio_duration >= duration:
                        suitable_music.append(audio_file)
            except:
                continue
        
        if suitable_music:
            selected = random.choice(suitable_music)
            print(f"选择音乐: {os.path.basename(selected)}")
            return selected
        else:
            # 如果没有合适的，随机选择一个
            selected = random.choice(audio_files)
            print(f"没有找到合适时长的音乐，随机选择: {os.path.basename(selected)}")
            return selected
    
    def add_music_to_video_moviepy(self,
                                   video_path: str,
                                   music_path: str = None,
                                   output_path: str = None,
                                   music_volume: float = 0.3,
                                   video_volume: float = 0.7,
                                   fade_in_duration: float = 1.0,
                                   fade_out_duration: float = 1.0,
                                   music_start_offset: float = 0.0,
                                   progress_callback: Optional[Callable] = None) -> str:
        """
        使用MoviePy为视频添加背景音乐
        
        Args:
            video_path: 输入视频路径
            music_path: 音乐文件路径，None则随机选择
            output_path: 输出文件路径
            music_volume: 背景音乐音量 (0.0-1.0)
            video_volume: 原视频音量 (0.0-1.0)
            fade_in_duration: 音乐淡入时长（秒）
            fade_out_duration: 音乐淡出时长（秒）
            music_start_offset: 音乐开始偏移时间（秒）
            progress_callback: 进度回调函数
            
        Returns:
            str: 输出文件路径
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 随机选择音乐
        if music_path is None:
            with VideoFileClip(video_path) as temp_video:
                video_duration = temp_video.duration
            music_path = self.select_random_music(duration=video_duration)
            
            if music_path is None:
                raise RuntimeError("没有找到可用的音乐文件")
        
        if not os.path.exists(music_path):
            raise FileNotFoundError(f"音乐文件不存在: {music_path}")
        
        # 设置输出路径
        if output_path is None:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            music_name = os.path.splitext(os.path.basename(music_path))[0]
            output_path = os.path.join(
                self.settings.OUTPUT_DIR,
                'music_videos',
                f'{video_name}_with_{music_name}.mp4'
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"开始为视频添加背景音乐...")
        print(f"视频: {os.path.basename(video_path)}")
        print(f"音乐: {os.path.basename(music_path)}")
        
        try:
            # 加载视频和音乐
            if progress_callback:
                progress_callback(10, "加载视频文件...")
            
            video_clip = VideoFileClip(video_path)
            video_duration = video_clip.duration
            
            if progress_callback:
                progress_callback(30, "加载音乐文件...")
            
            music_clip = AudioFileClip(music_path)
            
            # 处理音乐时长和偏移
            if music_start_offset > 0 and music_start_offset < music_clip.duration:
                music_clip = music_clip.subclip(music_start_offset)
            
            # 如果音乐比视频短，循环播放
            if music_clip.duration < video_duration:
                loops_needed = int(video_duration / music_clip.duration) + 1
                music_parts = [music_clip] * loops_needed
                from moviepy.editor import concatenate_audioclips
                music_clip = concatenate_audioclips(music_parts)
            
            # 裁剪音乐到视频长度
            music_clip = music_clip.subclip(0, video_duration)
            
            if progress_callback:
                progress_callback(50, "调整音量...")
            
            # 调整音量
            music_clip = music_clip.volumex(music_volume)
            
            # 添加淡入淡出效果
            if fade_in_duration > 0:
                music_clip = music_clip.audio_fadein(fade_in_duration)
            if fade_out_duration > 0:
                music_clip = music_clip.audio_fadeout(fade_out_duration)
            
            if progress_callback:
                progress_callback(70, "混合音频轨道...")
            
            # 处理原视频音频
            if video_clip.audio is not None:
                # 调整原音频音量
                original_audio = video_clip.audio.volumex(video_volume)
                # 混合音频
                mixed_audio = CompositeAudioClip([original_audio, music_clip])
            else:
                # 视频没有原音频，直接使用音乐
                mixed_audio = music_clip
            
            # 将混合音频设置到视频
            final_video = video_clip.set_audio(mixed_audio)
            
            if progress_callback:
                progress_callback(90, "正在渲染最终视频...")
            
            # 输出视频
            final_video.write_videofile(
                output_path,
                codec=self.settings.VIDEO_CODEC,
                audio_codec=self.settings.AUDIO_CODEC,
                bitrate=self.settings.VIDEO_BITRATE,
                audio_bitrate=self.settings.AUDIO_BITRATE,
                verbose=False,
                logger=None
            )
            
            # 清理资源
            video_clip.close()
            music_clip.close()
            mixed_audio.close()
            final_video.close()
            
            if progress_callback:
                progress_callback(100, "音乐配对完成!")
            
            print(f"音乐配对成功: {output_path}")
            return output_path
            
        except Exception as e:
            # 清理资源
            if 'video_clip' in locals():
                video_clip.close()
            if 'music_clip' in locals():
                music_clip.close()
            raise RuntimeError(f"添加背景音乐失败: {e}")
    
    def add_music_to_video_ffmpeg(self,
                                  video_path: str,
                                  music_path: str = None,
                                  output_path: str = None,
                                  music_volume: float = 0.3,
                                  video_volume: float = 0.7,
                                  fade_duration: float = 2.0,
                                  music_start_offset: float = 0.0) -> str:
        """
        使用FFmpeg为视频添加背景音乐 (更高效)
        
        Args:
            video_path: 输入视频路径
            music_path: 音乐文件路径
            output_path: 输出文件路径
            music_volume: 背景音乐音量
            video_volume: 原视频音量
            fade_duration: 淡入淡出时长
            music_start_offset: 音乐开始偏移时间
            
        Returns:
            str: 输出文件路径
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 随机选择音乐
        if music_path is None:
            # 获取视频时长
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', video_path
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                video_duration = float(result.stdout.strip())
                music_path = self.select_random_music(duration=video_duration)
            except:
                music_path = self.select_random_music()
            
            if music_path is None:
                raise RuntimeError("没有找到可用的音乐文件")
        
        if not os.path.exists(music_path):
            raise FileNotFoundError(f"音乐文件不存在: {music_path}")
        
        # 设置输出路径
        if output_path is None:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            music_name = os.path.splitext(os.path.basename(music_path))[0]
            output_path = os.path.join(
                self.settings.OUTPUT_DIR,
                'music_videos',
                f'{video_name}_with_{music_name}_ffmpeg.mp4'
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 构建FFmpeg命令
        cmd = [
            'ffmpeg', '-i', video_path, '-i', music_path,
            '-filter_complex',
            f'[1:a]volume={music_volume},afade=t=in:ss=0:d={fade_duration},afade=t=out:st=-{fade_duration}:d={fade_duration}[music];' +
            f'[0:a]volume={video_volume}[original];' +
            f'[original][music]amix=inputs=2:duration=first:dropout_transition=0[audio]',
            '-map', '0:v', '-map', '[audio]',
            '-c:v', 'copy',  # 不重新编码视频，提高速度
            '-c:a', self.settings.AUDIO_CODEC,
            '-b:a', self.settings.AUDIO_BITRATE,
            '-y',
            output_path
        ]
        
        # 如果有音乐偏移
        if music_start_offset > 0:
            cmd[3] = f'-ss {music_start_offset}'  # 在音乐输入前添加偏移
            cmd.insert(3, '-ss')
            cmd.insert(4, str(music_start_offset))
        
        print(f"执行FFmpeg音乐混合: {' '.join(cmd[:8])}...")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"FFmpeg音乐配对成功: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg添加背景音乐失败: {e.stderr}")
    
    def add_music_to_video(self,
                          video_path: str,
                          music_path: str = None,
                          output_path: str = None,
                          method: str = 'moviepy',
                          music_volume: float = 0.3,
                          video_volume: float = 0.7,
                          fade_in_duration: float = 1.0,
                          fade_out_duration: float = 1.0,
                          music_start_offset: float = 0.0,
                          progress_callback: Optional[Callable] = None) -> str:
        """
        统一的音乐配对接口
        
        Args:
            video_path: 输入视频路径
            music_path: 音乐文件路径，None则随机选择
            output_path: 输出文件路径
            method: 处理方法 ('moviepy', 'ffmpeg')
            music_volume: 背景音乐音量
            video_volume: 原视频音量
            fade_in_duration: 淡入时长
            fade_out_duration: 淡出时长
            music_start_offset: 音乐偏移时间
            progress_callback: 进度回调函数
            
        Returns:
            str: 输出文件路径
        """
        if method == 'ffmpeg':
            fade_duration = max(fade_in_duration, fade_out_duration)
            return self.add_music_to_video_ffmpeg(
                video_path, music_path, output_path, music_volume, video_volume, 
                fade_duration, music_start_offset
            )
        else:  # moviepy
            return self.add_music_to_video_moviepy(
                video_path, music_path, output_path, music_volume, video_volume,
                fade_in_duration, fade_out_duration, music_start_offset, progress_callback
            )
    
    def batch_add_music(self,
                       video_paths: List[str],
                       output_dir: str = None,
                       music_dir: str = None,
                       music_volume: float = 0.3,
                       video_volume: float = 0.7,
                       unique_music: bool = False,
                       progress_callback: Optional[Callable] = None) -> List[str]:
        """
        批量为视频添加背景音乐
        
        Args:
            video_paths: 视频文件路径列表
            output_dir: 输出目录
            music_dir: 音乐目录
            music_volume: 背景音乐音量
            video_volume: 原视频音量
            unique_music: 每个视频是否使用不同的音乐
            progress_callback: 进度回调函数
            
        Returns:
            List[str]: 输出文件路径列表
        """
        if output_dir is None:
            output_dir = os.path.join(self.settings.OUTPUT_DIR, 'batch_music_videos')
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取音乐文件列表
        audio_files = self.get_audio_files(music_dir)
        if not audio_files:
            raise RuntimeError("没有找到可用的音乐文件")
        
        output_files = []
        
        # 如果不要求唯一音乐，选择一个音乐用于所有视频
        if not unique_music:
            selected_music = random.choice(audio_files)
            print(f"所有视频将使用音乐: {os.path.basename(selected_music)}")
        
        for i, video_path in enumerate(video_paths):
            try:
                # 选择音乐
                if unique_music:
                    music_path = random.choice(audio_files)
                else:
                    music_path = selected_music
                
                # 设置输出路径
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                output_filename = f"{video_name}_with_music.mp4"
                output_path = os.path.join(output_dir, output_filename)
                
                # 添加音乐
                result = self.add_music_to_video(
                    video_path=video_path,
                    music_path=music_path,
                    output_path=output_path,
                    music_volume=music_volume,
                    video_volume=video_volume
                )
                
                output_files.append(result)
                
                if progress_callback:
                    progress = (i + 1) / len(video_paths) * 100
                    progress_callback(progress, f"完成 {i + 1}/{len(video_paths)} 个视频")
                
            except Exception as e:
                print(f"为视频添加音乐失败 {video_path}: {e}")
                continue
        
        print(f"批量音乐配对完成! 共处理 {len(output_files)} 个视频到: {output_dir}")
        return output_files
    
    def analyze_music_library(self, music_dir: str = None) -> dict:
        """
        分析音乐库统计信息
        
        Args:
            music_dir: 音乐目录路径
            
        Returns:
            dict: 统计信息字典
        """
        audio_files = self.get_audio_files(music_dir)
        
        if not audio_files:
            return {"total": 0, "durations": [], "formats": {}}
        
        durations = []
        formats = {}
        total_duration = 0
        
        for audio_file in audio_files:
            try:
                with AudioFileClip(audio_file) as audio:
                    duration = audio.duration
                    durations.append(duration)
                    total_duration += duration
                
                # 统计格式
                ext = os.path.splitext(audio_file)[1].lower()
                formats[ext] = formats.get(ext, 0) + 1
                
            except Exception as e:
                print(f"分析音频文件失败 {audio_file}: {e}")
                continue
        
        stats = {
            "total": len(audio_files),
            "valid": len(durations),
            "durations": durations,
            "formats": formats,
            "total_duration": total_duration,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0
        }
        
        print(f"音乐库分析结果:")
        print(f"  总文件数: {stats['total']}")
        print(f"  有效文件数: {stats['valid']}")
        print(f"  格式分布: {stats['formats']}")
        print(f"  总时长: {stats['total_duration']:.1f}秒")
        print(f"  平均时长: {stats['avg_duration']:.1f}秒")
        print(f"  时长范围: {stats['min_duration']:.1f}s - {stats['max_duration']:.1f}s")
        
        return stats


# 命令行测试
if __name__ == "__main__":
    mixer = AudioMixer()
    
    # 测试音乐库分析
    print("分析音乐库...")
    stats = mixer.analyze_music_library()
    
    # 测试用例
    test_video = "/home/admins/project/ffmpeg_ws/11.mp4"
    
    if os.path.exists(test_video) and stats['total'] > 0:
        print("\\n测试音乐配对功能...")
        
        def progress_callback(percent, message):
            print(f"进度: {percent:.1f}% - {message}")
        
        try:
            # 测试为视频添加随机音乐
            result = mixer.add_music_to_video(
                video_path=test_video,
                music_volume=0.4,
                video_volume=0.6,
                progress_callback=progress_callback
            )
            print(f"成功为视频添加背景音乐: {result}")
            
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        if not os.path.exists(test_video):
            print(f"测试视频不存在: {test_video}")
        if stats['total'] == 0:
            print("没有找到可用的音乐文件")