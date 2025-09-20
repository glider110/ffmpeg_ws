"""
功能1: 视频抽帧模块
从视频中提取帧图片，支持自定义时间间隔和输出格式
"""
import os
import subprocess
from typing import Optional, Callable
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("Warning: OpenCV not installed. CV2 method will not be available.")

try:
    from moviepy.editor import VideoFileClip
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False
    print("Warning: MoviePy not installed. MoviePy method will not be available.")

from config.settings import Settings


class FrameExtractor:
    """视频抽帧器"""
    
    def __init__(self):
        self.settings = Settings()
    
    def extract_frames_cv2(self, 
                          video_path: str, 
                          output_dir: str,
                          interval: float = 1.0,
                          image_format: str = 'png',
                          progress_callback: Optional[Callable] = None) -> list:
        """
        使用OpenCV提取视频帧
        
        Args:
            video_path: 输入视频路径
            output_dir: 输出目录
            interval: 提取间隔（秒）
            image_format: 输出图片格式 ('png', 'jpg')
            progress_callback: 进度回调函数
            
        Returns:
            list: 输出的图片文件路径列表
        """
        if not HAS_CV2:
            raise RuntimeError("OpenCV未安装，无法使用CV2方法。请安装opencv-python包。")
            
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取视频基本信息
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        frame_interval = int(fps * interval)  # 每隔多少帧提取一次
        extracted_files = []
        
        frame_count = 0
        extracted_count = 0
        
        print(f"开始提取帧: {video_path}")
        print(f"视频时长: {duration:.2f}秒, FPS: {fps:.2f}, 总帧数: {total_frames}")
        print(f"提取间隔: {interval}秒 ({frame_interval}帧)")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 按间隔提取帧
            if frame_count % frame_interval == 0:
                timestamp = frame_count / fps
                output_filename = f"{video_name}_frame_{extracted_count:04d}_t{timestamp:.1f}s.{image_format}"
                output_path = os.path.join(output_dir, output_filename)
                
                # 保存帧
                success = cv2.imwrite(output_path, frame)
                if success:
                    extracted_files.append(output_path)
                    extracted_count += 1
                    print(f"提取帧: {output_filename} (时间: {timestamp:.1f}s)")
                
                # 进度回调
                if progress_callback:
                    progress = (frame_count / total_frames) * 100
                    progress_callback(progress, f"已提取 {extracted_count} 帧")
            
            frame_count += 1
        
        cap.release()
        print(f"提取完成! 共提取 {extracted_count} 帧到: {output_dir}")
        return extracted_files
    
    def extract_frames_ffmpeg(self,
                             video_path: str,
                             output_dir: str, 
                             interval: float = 1.0,
                             image_format: str = 'png',
                             quality: str = 'high') -> list:
        """
        使用FFmpeg提取视频帧 (更高效)
        
        Args:
            video_path: 输入视频路径
            output_dir: 输出目录  
            interval: 提取间隔（秒）
            image_format: 输出图片格式
            quality: 输出质量 ('high', 'medium', 'low')
            
        Returns:
            list: 输出的图片文件路径列表
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
        os.makedirs(output_dir, exist_ok=True)
        
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_pattern = os.path.join(output_dir, f"{video_name}_frame_%04d.{image_format}")
        
        # 构建FFmpeg命令
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f'fps=1/{interval}',  # 每interval秒提取一帧
            '-y'  # 覆盖输出文件
        ]
        
        # 根据质量设置参数
        if image_format.lower() == 'jpg' or image_format.lower() == 'jpeg':
            quality_map = {'high': 2, 'medium': 5, 'low': 10}
            cmd.extend(['-q:v', str(quality_map.get(quality, 2))])
        
        cmd.append(output_pattern)
        
        print(f"执行FFmpeg命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("FFmpeg提取完成!")
            
            # 收集生成的文件
            extracted_files = []
            for file in sorted(os.listdir(output_dir)):
                if file.startswith(f"{video_name}_frame_") and file.endswith(f'.{image_format}'):
                    extracted_files.append(os.path.join(output_dir, file))
                    
            print(f"共提取 {len(extracted_files)} 帧到: {output_dir}")
            return extracted_files
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg提取失败: {e.stderr}")
    
    def extract_frames_moviepy(self,
                              video_path: str,
                              output_dir: str,
                              interval: float = 1.0,
                              image_format: str = 'png',
                              progress_callback: Optional[Callable] = None) -> list:
        """
        使用MoviePy提取视频帧
        
        Args:
            video_path: 输入视频路径
            output_dir: 输出目录
            interval: 提取间隔（秒）
            image_format: 输出图片格式
            progress_callback: 进度回调函数
            
        Returns:
            list: 输出的图片文件路径列表
        """
        if not HAS_MOVIEPY:
            raise RuntimeError("MoviePy未安装，无法使用MoviePy方法。请安装moviepy包。")
            
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
        os.makedirs(output_dir, exist_ok=True)
        
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        with VideoFileClip(video_path) as clip:
            duration = clip.duration
            timestamps = [i * interval for i in range(int(duration // interval) + 1) if i * interval < duration]
            
            extracted_files = []
            total_frames = len(timestamps)
            
            print(f"开始使用MoviePy提取帧: {video_path}")
            print(f"视频时长: {duration:.2f}秒, 将提取 {total_frames} 帧")
            
            for i, timestamp in enumerate(timestamps):
                try:
                    frame = clip.get_frame(timestamp)
                    output_filename = f"{video_name}_frame_{i:04d}_t{timestamp:.1f}s.{image_format}"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # 使用Pillow保存 (MoviePy的frame是numpy数组)
                    from PIL import Image
                    img = Image.fromarray(frame)
                    img.save(output_path)
                    
                    extracted_files.append(output_path)
                    print(f"提取帧: {output_filename}")
                    
                    # 进度回调
                    if progress_callback:
                        progress = (i + 1) / total_frames * 100
                        progress_callback(progress, f"已提取 {i + 1}/{total_frames} 帧")
                        
                except Exception as e:
                    print(f"提取帧失败 (时间: {timestamp:.1f}s): {e}")
                    continue
            
            print(f"MoviePy提取完成! 共提取 {len(extracted_files)} 帧到: {output_dir}")
            return extracted_files
    
    def extract_frames(self, 
                      video_path: str,
                      output_dir: str = None,
                      interval: float = 1.0,
                      image_format: str = 'png', 
                      method: str = 'auto',
                      quality: str = 'high',
                      progress_callback: Optional[Callable] = None) -> list:
        """
        统一的视频抽帧接口
        
        Args:
            video_path: 输入视频路径
            output_dir: 输出目录，默认为settings.OUTPUT_DIR/frames
            interval: 提取间隔（秒）
            image_format: 图片格式 ('png', 'jpg')
            method: 提取方法 ('auto', 'cv2', 'ffmpeg', 'moviepy')
            quality: 输出质量 ('high', 'medium', 'low')
            progress_callback: 进度回调函数
            
        Returns:
            list: 输出的图片文件路径列表
        """
        if output_dir is None:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = os.path.join(self.settings.OUTPUT_DIR, 'frames', video_name)
        
        # 自动选择最佳方法
        if method == 'auto':
            # 优先级: ffmpeg > moviepy > cv2
            method = 'ffmpeg'  # FFmpeg通常系统都有安装
            if not HAS_MOVIEPY and not HAS_CV2:
                print("警告: MoviePy和OpenCV都未安装，将使用FFmpeg方法")
        
        # 根据方法调用对应函数
        if method == 'ffmpeg':
            return self.extract_frames_ffmpeg(video_path, output_dir, interval, image_format, quality)
        elif method == 'moviepy' and HAS_MOVIEPY:
            return self.extract_frames_moviepy(video_path, output_dir, interval, image_format, progress_callback)
        elif method == 'cv2' and HAS_CV2:
            return self.extract_frames_cv2(video_path, output_dir, interval, image_format, progress_callback)
        else:
            # 回退到可用的方法
            if HAS_MOVIEPY:
                print(f"警告: {method} 方法不可用，回退到MoviePy方法")
                return self.extract_frames_moviepy(video_path, output_dir, interval, image_format, progress_callback)
            elif HAS_CV2:
                print(f"警告: {method} 方法不可用，回退到OpenCV方法")
                return self.extract_frames_cv2(video_path, output_dir, interval, image_format, progress_callback)
            else:
                print(f"警告: {method} 方法不可用，回退到FFmpeg方法")
                return self.extract_frames_ffmpeg(video_path, output_dir, interval, image_format, quality)


# 命令行测试
if __name__ == "__main__":
    extractor = FrameExtractor()
    
    # 测试用例
    test_video = "/home/admins/project/ffmpeg_ws/11.mp4"  # 使用项目中已有的视频
    
    if os.path.exists(test_video):
        print("测试视频抽帧功能...")
        
        def progress_callback(percent, message):
            print(f"进度: {percent:.1f}% - {message}")
        
        try:
            # 测试CV2方法
            result = extractor.extract_frames(
                test_video, 
                interval=2.0,  # 每2秒提取一帧
                method='cv2',
                progress_callback=progress_callback
            )
            print(f"成功提取 {len(result)} 帧")
            
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print(f"测试视频不存在: {test_video}")