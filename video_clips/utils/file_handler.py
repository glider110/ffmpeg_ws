"""
文件处理工具
提供文件操作、路径处理等通用功能
"""
import os
import shutil
import hashlib
from typing import List, Optional, Tuple
from config.settings import Settings


class FileHandler:
    """文件处理器"""
    
    def __init__(self):
        self.settings = Settings()
    
    def get_video_files(self, directory: str, recursive: bool = True) -> List[str]:
        """
        获取目录中的视频文件
        
        Args:
            directory: 目录路径
            recursive: 是否递归搜索子目录
            
        Returns:
            List[str]: 视频文件路径列表
        """
        if not os.path.exists(directory):
            return []
        
        video_files = []
        
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if self.is_video_file(file):
                        video_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and self.is_video_file(file):
                    video_files.append(file_path)
        
        return sorted(video_files)
    
    def get_audio_files(self, directory: str, recursive: bool = True) -> List[str]:
        """
        获取目录中的音频文件
        
        Args:
            directory: 目录路径
            recursive: 是否递归搜索子目录
            
        Returns:
            List[str]: 音频文件路径列表
        """
        if not os.path.exists(directory):
            return []
        
        audio_files = []
        
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if self.is_audio_file(file):
                        audio_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and self.is_audio_file(file):
                    audio_files.append(file_path)
        
        return sorted(audio_files)
    
    def is_video_file(self, filename: str) -> bool:
        """判断是否为视频文件"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.settings.SUPPORTED_VIDEO_FORMATS
    
    def is_audio_file(self, filename: str) -> bool:
        """判断是否为音频文件"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.settings.SUPPORTED_AUDIO_FORMATS
    
    def is_image_file(self, filename: str) -> bool:
        """判断是否为图片文件"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.settings.SUPPORTED_IMAGE_FORMATS
    
    def ensure_directory(self, directory: str) -> str:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            directory: 目录路径
            
        Returns:
            str: 目录路径
        """
        os.makedirs(directory, exist_ok=True)
        return directory
    
    def get_unique_filename(self, filepath: str) -> str:
        """
        获取唯一的文件名（如果文件已存在，添加数字后缀）
        
        Args:
            filepath: 原文件路径
            
        Returns:
            str: 唯一的文件路径
        """
        if not os.path.exists(filepath):
            return filepath
        
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        
        counter = 1
        while True:
            new_filename = f"{name}_{counter}{ext}"
            new_filepath = os.path.join(directory, new_filename)
            
            if not os.path.exists(new_filepath):
                return new_filepath
            
            counter += 1
    
    def get_file_size(self, filepath: str) -> int:
        """获取文件大小（字节）"""
        if os.path.exists(filepath):
            return os.path.getsize(filepath)
        return 0
    
    def format_file_size(self, size_bytes: int) -> str:
        """
        格式化文件大小
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            str: 格式化的文件大小字符串
        """
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def get_file_md5(self, filepath: str) -> str:
        """
        计算文件的MD5哈希值
        
        Args:
            filepath: 文件路径
            
        Returns:
            str: MD5哈希值
        """
        if not os.path.exists(filepath):
            return ""
        
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def copy_file(self, src: str, dst: str, overwrite: bool = False) -> bool:
        """
        复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            bool: 是否复制成功
        """
        try:
            if not os.path.exists(src):
                return False
            
            # 确保目标目录存在
            dst_dir = os.path.dirname(dst)
            self.ensure_directory(dst_dir)
            
            # 如果不覆盖且目标文件存在，获取唯一文件名
            if not overwrite and os.path.exists(dst):
                dst = self.get_unique_filename(dst)
            
            shutil.copy2(src, dst)
            return True
            
        except Exception as e:
            print(f"复制文件失败: {e}")
            return False
    
    def move_file(self, src: str, dst: str, overwrite: bool = False) -> bool:
        """
        移动文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            bool: 是否移动成功
        """
        try:
            if not os.path.exists(src):
                return False
            
            # 确保目标目录存在
            dst_dir = os.path.dirname(dst)
            self.ensure_directory(dst_dir)
            
            # 如果不覆盖且目标文件存在，获取唯一文件名
            if not overwrite and os.path.exists(dst):
                dst = self.get_unique_filename(dst)
            
            shutil.move(src, dst)
            return True
            
        except Exception as e:
            print(f"移动文件失败: {e}")
            return False
    
    def delete_file(self, filepath: str) -> bool:
        """
        删除文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            bool: 是否删除成功
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"删除文件失败: {e}")
            return False
    
    def cleanup_temp_files(self, temp_dir: str = None) -> int:
        """
        清理临时文件
        
        Args:
            temp_dir: 临时目录，默认使用settings中的配置
            
        Returns:
            int: 删除的文件数量
        """
        if temp_dir is None:
            temp_dir = self.settings.TEMP_DIR
        
        if not os.path.exists(temp_dir):
            return 0
        
        deleted_count = 0
        try:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except:
                        continue
            
            # 删除空目录
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        if not os.listdir(dir_path):  # 如果目录为空
                            os.rmdir(dir_path)
                    except:
                        continue
                        
        except Exception as e:
            print(f"清理临时文件失败: {e}")
        
        return deleted_count
    
    def organize_files_by_date(self, source_dir: str, target_dir: str) -> dict:
        """
        按日期组织文件
        
        Args:
            source_dir: 源目录
            target_dir: 目标目录
            
        Returns:
            dict: 组织结果统计
        """
        import datetime
        
        if not os.path.exists(source_dir):
            return {"error": "源目录不存在"}
        
        self.ensure_directory(target_dir)
        
        organized_count = 0
        failed_count = 0
        
        for file in os.listdir(source_dir):
            src_path = os.path.join(source_dir, file)
            
            if not os.path.isfile(src_path):
                continue
            
            try:
                # 获取文件修改时间
                mtime = os.path.getmtime(src_path)
                date_obj = datetime.datetime.fromtimestamp(mtime)
                date_folder = date_obj.strftime("%Y-%m-%d")
                
                # 创建日期目录
                date_dir = os.path.join(target_dir, date_folder)
                self.ensure_directory(date_dir)
                
                # 移动文件
                dst_path = os.path.join(date_dir, file)
                dst_path = self.get_unique_filename(dst_path)
                
                shutil.move(src_path, dst_path)
                organized_count += 1
                
            except Exception as e:
                print(f"组织文件失败 {file}: {e}")
                failed_count += 1
        
        return {
            "organized": organized_count,
            "failed": failed_count,
            "target_dir": target_dir
        }