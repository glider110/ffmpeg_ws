# Video Clips Configuration
import os

class Settings:
    """项目配置类"""
    
    # 项目根目录
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 各种目录路径
    TEMP_DIR = os.path.join(PROJECT_ROOT, 'temp')
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
    MUSIC_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), 'audio')  # 使用已有的音频文件夹
    
    # 默认参数
    DEFAULT_FRAME_INTERVAL = 1.0  # 抽帧间隔（秒）
    DEFAULT_SEGMENT_DURATION = 8  # 默认切割时长（秒）
    DEFAULT_OUTPUT_DURATION = [10, 15, 20]  # 默认组合时长
    
    # 支持的文件格式
    SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.MOV']
    SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a']
    SUPPORTED_IMAGE_FORMATS = ['.png', '.jpg', '.jpeg']
    
    # 视频输出质量
    VIDEO_CODEC = 'libx264'
    VIDEO_BITRATE = '5000k'
    AUDIO_CODEC = 'aac'
    AUDIO_BITRATE = '320k'
    
    # GUI配置
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    PREVIEW_WIDTH = 400
    PREVIEW_HEIGHT = 300
    # UI 缩放（可通过环境变量覆盖）
    UI_SCALE = float(os.environ.get('VIDEO_CLIPS_UI_SCALE', '1.0'))
    BASE_FONT_SIZE = int(float(os.environ.get('VIDEO_CLIPS_BASE_FONT', '10')))  # 默认10
    
    # 宫格配置
    GRID_LAYOUTS = {
        '2×1': (2, 1),
        '1×2': (1, 2), 
        '2×2': (2, 2),
        '3×1': (3, 1),
        '1×3': (1, 3),
        '2×3': (2, 3),
        '3×2': (3, 2),
        '3×3': (3, 3)
    }
    
    @classmethod
    def ensure_dirs(cls):
        """确保必要的目录存在"""
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)