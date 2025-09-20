"""
功能2: 视频切割模块  
将长视频切割为5-10秒的短片段，支持自定义时长和切割策略
"""
import os
import subprocess
from typing import List, Optional, Callable
from moviepy.editor import VideoFileClip
from config.settings import Settings


class VideoSplitter:
    """视频切割器"""
    
    def __init__(self):
        self.settings = Settings()
    
    def split_video_equal(self,
                         video_path: str,
                         segment_duration: float = 8.0,
                         output_dir: str = None,
                         overlap: float = 0.0,
                         progress_callback: Optional[Callable] = None) -> List[str]:
        """
        等时长切割视频
        
        Args:
            video_path: 输入视频路径
            segment_duration: 每段时长（秒）
            output_dir: 输出目录
            overlap: 片段重叠时间（秒）
            progress_callback: 进度回调函数
            
        Returns:
            List[str]: 输出的视频片段路径列表
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 设置输出目录
        if output_dir is None:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = os.path.join(self.settings.OUTPUT_DIR, 'segments', video_name)
        
        os.makedirs(output_dir, exist_ok=True)
        
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_files = []
        
        with VideoFileClip(video_path) as clip:
            total_duration = clip.duration
            print(f"开始切割视频: {video_path}")
            print(f"总时长: {total_duration:.2f}秒, 切割时长: {segment_duration}秒")
            
            # 计算切割点
            step = segment_duration - overlap  # 实际步长
            segments = []
            start_time = 0
            segment_index = 0
            
            while start_time < total_duration:
                end_time = min(start_time + segment_duration, total_duration)
                
                # 如果剩余时间太短，合并到上一段
                if total_duration - start_time < segment_duration * 0.3:
                    if segments:  # 如果已有片段，扩展最后一个片段
                        segments[-1] = (segments[-1][0], total_duration, segments[-1][2])
                        break
                
                segments.append((start_time, end_time, segment_index))
                start_time += step
                segment_index += 1
            
            print(f"计划切割 {len(segments)} 个片段")
            
            # 执行切割
            for i, (start, end, idx) in enumerate(segments):
                try:
                    output_filename = f"{video_name}_segment_{idx:03d}_{start:.1f}s-{end:.1f}s.mp4"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # 切割片段
                    segment_clip = clip.subclip(start, end)
                    segment_clip.write_videofile(
                        output_path,
                        codec=self.settings.VIDEO_CODEC,
                        audio_codec=self.settings.AUDIO_CODEC,
                        verbose=False,
                        logger=None
                    )
                    segment_clip.close()
                    
                    output_files.append(output_path)
                    print(f"切割完成: {output_filename} ({end-start:.1f}s)")
                    
                    # 进度回调
                    if progress_callback:
                        progress = (i + 1) / len(segments) * 100
                        progress_callback(progress, f"已切割 {i + 1}/{len(segments)} 个片段")
                        
                except Exception as e:
                    print(f"切割片段失败 [{start:.1f}s-{end:.1f}s]: {e}")
                    continue
        
        print(f"视频切割完成! 共生成 {len(output_files)} 个片段到: {output_dir}")
        return output_files
    
    def split_video_ffmpeg(self,
                          video_path: str,
                          segment_duration: float = 8.0,
                          overlap: float = 0.0,
                          output_dir: str = None) -> List[str]:
        """
        使用FFmpeg进行高效切割 (无重编码)
        
        Args:
            video_path: 输入视频路径
            segment_duration: 每段时长（秒）
            output_dir: 输出目录
            
        Returns:
            List[str]: 输出的视频片段路径列表
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 设置输出目录
        if output_dir is None:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = os.path.join(self.settings.OUTPUT_DIR, 'segments', video_name)
        
        os.makedirs(output_dir, exist_ok=True)
        
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_pattern = os.path.join(output_dir, f"{video_name}_segment_%03d.mp4")
        
        # 计算切割区间，支持重叠
        import math
        from moviepy.editor import VideoFileClip
        with VideoFileClip(video_path) as clip:
            total_duration = clip.duration
        step = segment_duration - overlap if segment_duration > overlap else segment_duration
        segments = []
        start_time = 0
        idx = 0
        while start_time < total_duration:
            end_time = min(start_time + segment_duration, total_duration)
            # 如果最后一个片段长度不足 segment_duration 的 80%，则不切割
            if end_time - start_time < segment_duration * 0.8:
                break
            segments.append((start_time, end_time, idx))
            start_time += step
            idx += 1
        output_files = []
        for start, end, idx in segments:
            output_filename = f"{video_name}_segment_{idx:03d}_{start:.1f}s-{end:.1f}s.mp4"
            output_path = os.path.join(output_dir, output_filename)
            # 构建FFmpeg命令，精确区间切割
            cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-ss', str(start), '-to', str(end),
                '-c', 'copy', output_path
            ]
            print(f"执行FFmpeg切割: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                output_files.append(output_path)
                print(f"切割完成: {output_filename} ({end-start:.1f}s)")
            except subprocess.CalledProcessError as e:
                print(f"切割片段失败 [{start:.1f}s-{end:.1f}s]: {e.stderr}")
                continue
        print(f"视频切割完成! 共生成 {len(output_files)} 个片段到: {output_dir}")
        return output_files
    
    def split_video_random(self,
                          video_path: str,
                          num_segments: int = 10,
                          min_duration: float = 5.0,
                          max_duration: float = 10.0,
                          output_dir: str = None,
                          progress_callback: Optional[Callable] = None) -> List[str]:
        """
        随机时长切割视频
        
        Args:
            video_path: 输入视频路径
            num_segments: 目标片段数量
            min_duration: 最小片段时长（秒）
            max_duration: 最大片段时长（秒）
            output_dir: 输出目录
            progress_callback: 进度回调函数
            
        Returns:
            List[str]: 输出的视频片段路径列表
        """
        import random
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 设置输出目录
        if output_dir is None:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = os.path.join(self.settings.OUTPUT_DIR, 'segments_random', video_name)
        
        os.makedirs(output_dir, exist_ok=True)
        
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_files = []
        
        with VideoFileClip(video_path) as clip:
            total_duration = clip.duration
            print(f"开始随机切割视频: {video_path}")
            print(f"总时长: {total_duration:.2f}秒, 目标片段数: {num_segments}")
            
            # 生成随机切割点
            segments = []
            for i in range(num_segments):
                # 随机时长
                duration = random.uniform(min_duration, max_duration)
                
                # 随机开始时间
                max_start = max(0, total_duration - duration)
                if max_start <= 0:
                    continue
                    
                start_time = random.uniform(0, max_start)
                end_time = min(start_time + duration, total_duration)
                
                segments.append((start_time, end_time, i))
            
            # 按开始时间排序
            segments.sort(key=lambda x: x[0])
            
            print(f"计划随机切割 {len(segments)} 个片段")
            
            # 执行切割
            for i, (start, end, idx) in enumerate(segments):
                try:
                    output_filename = f"{video_name}_random_{idx:03d}_{start:.1f}s-{end:.1f}s.mp4"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # 切割片段
                    segment_clip = clip.subclip(start, end)
                    segment_clip.write_videofile(
                        output_path,
                        codec=self.settings.VIDEO_CODEC,
                        audio_codec=self.settings.AUDIO_CODEC,
                        verbose=False,
                        logger=None
                    )
                    segment_clip.close()
                    
                    output_files.append(output_path)
                    print(f"随机切割完成: {output_filename} ({end-start:.1f}s)")
                    
                    # 进度回调
                    if progress_callback:
                        progress = (i + 1) / len(segments) * 100
                        progress_callback(progress, f"已切割 {i + 1}/{len(segments)} 个片段")
                        
                except Exception as e:
                    print(f"随机切割片段失败 [{start:.1f}s-{end:.1f}s]: {e}")
                    continue
        
        print(f"随机视频切割完成! 共生成 {len(output_files)} 个片段到: {output_dir}")
        return output_files
    
    def split_video(self,
                   video_path: str,
                   segment_duration: float = 8.0,
                   output_dir: str = None,
                   method: str = 'equal',
                   overlap: float = 0.0,
                   num_segments: int = 10,
                   min_duration: float = 5.0,
                   max_duration: float = 10.0,
                   progress_callback: Optional[Callable] = None) -> List[str]:
        """
        统一的视频切割接口
        
        Args:
            video_path: 输入视频路径
            segment_duration: 切割时长（秒）
            output_dir: 输出目录
            method: 切割方法 ('equal', 'ffmpeg', 'random')
            overlap: 重叠时间（秒）
            num_segments: 随机切割的目标片段数
            min_duration: 随机切割最小时长
            max_duration: 随机切割最大时长
            progress_callback: 进度回调函数
            
        Returns:
            List[str]: 输出的视频片段路径列表
        """
        if method == 'ffmpeg':
            return self.split_video_ffmpeg(video_path, segment_duration, output_dir)
        elif method == 'random':
            return self.split_video_random(
                video_path, num_segments, min_duration, max_duration, 
                output_dir, progress_callback
            )
        else:  # 默认等时长切割
            return self.split_video_equal(
                video_path, segment_duration, output_dir, overlap, progress_callback
            )
    
    def get_video_info(self, video_path: str) -> dict:
        """
        获取视频基本信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            dict: 视频信息字典
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        try:
            with VideoFileClip(video_path) as clip:
                info = {
                    'duration': clip.duration,
                    'fps': clip.fps,
                    'size': clip.size,
                    'filename': os.path.basename(video_path),
                    'filesize': os.path.getsize(video_path)
                }
            return info
        except Exception as e:
            raise RuntimeError(f"获取视频信息失败: {e}")


# 命令行测试
if __name__ == "__main__":
    splitter = VideoSplitter()
    
    # 测试用例
    test_video = "/home/admins/project/ffmpeg_ws/11.mp4"
    
    if os.path.exists(test_video):
        print("测试视频切割功能...")
        
        def progress_callback(percent, message):
            print(f"进度: {percent:.1f}% - {message}")
        
        try:
            # 获取视频信息
            info = splitter.get_video_info(test_video)
            print(f"视频信息: {info}")
            
            # 测试等时长切割
            result = splitter.split_video(
                test_video,
                segment_duration=6.0,  # 6秒一段
                method='equal',
                progress_callback=progress_callback
            )
            print(f"成功切割 {len(result)} 个片段")
            
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print(f"测试视频不存在: {test_video}")