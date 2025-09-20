"""
视频处理工具
提供视频信息获取、格式转换等功能
"""
import os
import subprocess
from typing import Dict, Optional, Tuple, List
try:
    from moviepy.editor import VideoFileClip
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False
    
from config.settings import Settings


class VideoUtils:
    """视频处理工具类"""
    
    def __init__(self):
        self.settings = Settings()
    
    def get_video_info_ffprobe(self, video_path: str) -> Optional[Dict]:
        """
        使用ffprobe获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Optional[Dict]: 视频信息字典
        """
        if not os.path.exists(video_path):
            return None
        
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            data = json.loads(result.stdout)
            
            # 提取视频流信息
            video_stream = None
            audio_stream = None
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video' and video_stream is None:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and audio_stream is None:
                    audio_stream = stream
            
            if video_stream is None:
                return None
            
            # 构建信息字典
            info = {
                'filename': os.path.basename(video_path),
                'filepath': video_path,
                'filesize': os.path.getsize(video_path),
                'duration': float(data['format'].get('duration', 0)),
                'bitrate': int(data['format'].get('bit_rate', 0)),
                'format_name': data['format'].get('format_name', ''),
                'video': {
                    'codec': video_stream.get('codec_name', ''),
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': self._parse_fps(video_stream.get('r_frame_rate', '0/1')),
                    'bitrate': int(video_stream.get('bit_rate', 0)) if video_stream.get('bit_rate') else 0,
                    'pixel_format': video_stream.get('pix_fmt', '')
                }
            }
            
            # 添加音频信息（如果有）
            if audio_stream:
                info['audio'] = {
                    'codec': audio_stream.get('codec_name', ''),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0)),
                    'bitrate': int(audio_stream.get('bit_rate', 0)) if audio_stream.get('bit_rate') else 0
                }
            else:
                info['audio'] = None
            
            return info
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, Exception) as e:
            print(f"获取视频信息失败 (ffprobe): {e}")
            return None
    
    def get_video_info_moviepy(self, video_path: str) -> Optional[Dict]:
        """
        使用MoviePy获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Optional[Dict]: 视频信息字典
        """
        if not HAS_MOVIEPY or not os.path.exists(video_path):
            return None
        
        try:
            with VideoFileClip(video_path) as clip:
                info = {
                    'filename': os.path.basename(video_path),
                    'filepath': video_path,
                    'filesize': os.path.getsize(video_path),
                    'duration': clip.duration,
                    'video': {
                        'width': clip.w,
                        'height': clip.h,
                        'fps': clip.fps,
                    }
                }
                
                # 添加音频信息
                if clip.audio is not None:
                    info['audio'] = {
                        'duration': clip.audio.duration,
                        'fps': clip.audio.fps
                    }
                else:
                    info['audio'] = None
                
                return info
                
        except Exception as e:
            print(f"获取视频信息失败 (MoviePy): {e}")
            return None
    
    def get_video_info(self, video_path: str, method: str = 'ffprobe') -> Optional[Dict]:
        """
        获取视频信息的统一接口
        
        Args:
            video_path: 视频文件路径
            method: 获取方法 ('ffprobe', 'moviepy')
            
        Returns:
            Optional[Dict]: 视频信息字典
        """
        if method == 'moviepy' and HAS_MOVIEPY:
            return self.get_video_info_moviepy(video_path)
        else:
            return self.get_video_info_ffprobe(video_path)
    
    def _parse_fps(self, fps_str: str) -> float:
        """解析帧率字符串"""
        try:
            if '/' in fps_str:
                num, den = fps_str.split('/')
                return float(num) / float(den)
            else:
                return float(fps_str)
        except:
            return 0.0
    
    def convert_video_format(self, 
                           input_path: str,
                           output_path: str,
                           target_format: str = 'mp4',
                           video_codec: str = None,
                           audio_codec: str = None,
                           quality: str = 'medium') -> bool:
        """
        转换视频格式
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            target_format: 目标格式
            video_codec: 视频编码器
            audio_codec: 音频编码器
            quality: 质量等级 ('low', 'medium', 'high')
            
        Returns:
            bool: 是否转换成功
        """
        if not os.path.exists(input_path):
            return False
        
        # 设置默认编码器
        if video_codec is None:
            video_codec = self.settings.VIDEO_CODEC
        if audio_codec is None:
            audio_codec = self.settings.AUDIO_CODEC
        
        # 设置质量参数
        quality_map = {
            'low': {'crf': '28', 'preset': 'fast'},
            'medium': {'crf': '23', 'preset': 'medium'},
            'high': {'crf': '18', 'preset': 'slow'}
        }
        quality_params = quality_map.get(quality, quality_map['medium'])
        
        # 构建ffmpeg命令
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', video_codec,
            '-c:a', audio_codec,
            '-crf', quality_params['crf'],
            '-preset', quality_params['preset'],
            '-y',  # 覆盖输出文件
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"视频格式转换失败: {e}")
            return False
    
    def resize_video(self,
                    input_path: str,
                    output_path: str,
                    width: int,
                    height: int,
                    maintain_aspect: bool = True) -> bool:
        """
        调整视频尺寸
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            width: 目标宽度
            height: 目标高度
            maintain_aspect: 是否保持宽高比
            
        Returns:
            bool: 是否调整成功
        """
        if not os.path.exists(input_path):
            return False
        
        # 构建缩放参数
        if maintain_aspect:
            scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        else:
            scale_filter = f"scale={width}:{height}"
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', scale_filter,
            '-c:a', 'copy',  # 音频直接复制
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"视频尺寸调整失败: {e}")
            return False
    
    def extract_audio_from_video(self,
                               video_path: str,
                               output_path: str,
                               audio_format: str = 'mp3',
                               audio_quality: str = '320k') -> bool:
        """
        从视频中提取音频
        
        Args:
            video_path: 视频文件路径
            output_path: 输出音频路径
            audio_format: 音频格式
            audio_quality: 音频质量
            
        Returns:
            bool: 是否提取成功
        """
        if not os.path.exists(video_path):
            return False
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn',  # 不要视频流
            '-acodec', 'libmp3lame' if audio_format == 'mp3' else 'aac',
            '-ab', audio_quality,
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"音频提取失败: {e}")
            return False
    
    def create_video_thumbnail(self,
                             video_path: str,
                             output_path: str,
                             timestamp: float = 1.0,
                             width: int = 320,
                             height: int = 240) -> bool:
        """
        创建视频缩略图
        
        Args:
            video_path: 视频文件路径
            output_path: 输出图片路径
            timestamp: 截取时间点（秒）
            width: 缩略图宽度
            height: 缩略图高度
            
        Returns:
            bool: 是否创建成功
        """
        if not os.path.exists(video_path):
            return False
        
        cmd = [
            'ffmpeg', '-ss', str(timestamp),
            '-i', video_path,
            '-vf', f'scale={width}:{height}',
            '-vframes', '1',
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"缩略图创建失败: {e}")
            return False
    
    def get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            float: 视频时长（秒）
        """
        info = self.get_video_info(video_path)
        if info:
            return info.get('duration', 0.0)
        return 0.0
    
    def get_video_resolution(self, video_path: str) -> Tuple[int, int]:
        """
        获取视频分辨率
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Tuple[int, int]: (宽度, 高度)
        """
        info = self.get_video_info(video_path)
        if info and 'video' in info:
            video_info = info['video']
            return (video_info.get('width', 0), video_info.get('height', 0))
        return (0, 0)
    
    def is_video_valid(self, video_path: str) -> bool:
        """
        检查视频文件是否有效
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            bool: 视频文件是否有效
        """
        info = self.get_video_info(video_path)
        return info is not None and info.get('duration', 0) > 0
    
    def batch_analyze_videos(self, video_paths: List[str]) -> Dict:
        """
        批量分析视频文件
        
        Args:
            video_paths: 视频文件路径列表
            
        Returns:
            Dict: 分析结果统计
        """
        results = {
            'total': len(video_paths),
            'valid': 0,
            'invalid': 0,
            'total_duration': 0.0,
            'total_size': 0,
            'resolutions': {},
            'formats': {},
            'codecs': {}
        }
        
        valid_durations = []
        
        for video_path in video_paths:
            info = self.get_video_info(video_path)
            
            if info is None:
                results['invalid'] += 1
                continue
            
            results['valid'] += 1
            
            # 统计时长
            duration = info.get('duration', 0)
            if duration > 0:
                results['total_duration'] += duration
                valid_durations.append(duration)
            
            # 统计文件大小
            results['total_size'] += info.get('filesize', 0)
            
            # 统计分辨率
            if 'video' in info:
                video_info = info['video']
                width = video_info.get('width', 0)
                height = video_info.get('height', 0)
                resolution = f"{width}x{height}"
                results['resolutions'][resolution] = results['resolutions'].get(resolution, 0) + 1
                
                # 统计编码器
                codec = video_info.get('codec', 'unknown')
                results['codecs'][codec] = results['codecs'].get(codec, 0) + 1
            
            # 统计格式
            format_name = info.get('format_name', 'unknown')
            results['formats'][format_name] = results['formats'].get(format_name, 0) + 1
        
        # 计算平均值
        if valid_durations:
            results['avg_duration'] = sum(valid_durations) / len(valid_durations)
            results['min_duration'] = min(valid_durations)
            results['max_duration'] = max(valid_durations)
        else:
            results['avg_duration'] = 0
            results['min_duration'] = 0
            results['max_duration'] = 0
        
        return results


# 命令行测试
if __name__ == "__main__":
    utils = VideoUtils()
    
    # 测试视频信息获取
    test_video = "/home/admins/project/ffmpeg_ws/11.mp4"
    
    if os.path.exists(test_video):
        print(f"分析视频: {test_video}")
        info = utils.get_video_info(test_video)
        
        if info:
            print(f"文件大小: {info['filesize']} bytes")
            print(f"时长: {info['duration']:.2f} seconds")
            print(f"分辨率: {info['video']['width']}x{info['video']['height']}")
            print(f"帧率: {info['video']['fps']:.2f} fps")
            print(f"视频编码器: {info['video']['codec']}")
            
            if info['audio']:
                print(f"音频编码器: {info['audio']['codec']}")
                print(f"采样率: {info['audio']['sample_rate']} Hz")
                print(f"声道数: {info['audio']['channels']}")
        else:
            print("获取视频信息失败")
    else:
        print(f"测试视频不存在: {test_video}")