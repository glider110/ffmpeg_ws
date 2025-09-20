"""
功能3: 宫格视频组合模块
将短视频片段排列组合成2、3、4、6宫格的视频
"""
import os
import subprocess
import random
from typing import List, Tuple, Optional, Callable
from moviepy.editor import VideoFileClip, clips_array, CompositeVideoClip
from config.settings import Settings


class GridComposer:
    """宫格视频组合器"""
    
    def __init__(self):
        self.settings = Settings()
    
    def _get_grid_dimensions(self, layout: str) -> Tuple[int, int]:
        """
        获取宫格布局的行列数
        
        Args:
            layout: 布局名称 (如 '2×2', '3×1' 等)
            
        Returns:
            Tuple[int, int]: (行数, 列数)
        """
        if layout in self.settings.GRID_LAYOUTS:
            return self.settings.GRID_LAYOUTS[layout]
        else:
            # 解析自定义布局
            if '×' in layout:
                try:
                    rows, cols = map(int, layout.split('×'))
                    return (rows, cols)
                except:
                    raise ValueError(f"无效的布局格式: {layout}")
            else:
                raise ValueError(f"不支持的布局: {layout}")
    
    def _select_videos(self, video_paths: List[str], grid_size: int, selection_method: str = 'random') -> List[str]:
        """
        选择视频用于宫格布局
        
        Args:
            video_paths: 视频文件路径列表
            grid_size: 需要的视频数量
            selection_method: 选择方法 ('random', 'first', 'duration')
            
        Returns:
            List[str]: 选中的视频路径列表
        """
        if len(video_paths) < grid_size:
            raise ValueError(f"视频数量不足: 需要 {grid_size} 个，只有 {len(video_paths)} 个")
        
        if selection_method == 'random':
            return random.sample(video_paths, grid_size)
        elif selection_method == 'first':
            return video_paths[:grid_size]
        elif selection_method == 'duration':
            # 按时长选择（选择时长相近的视频）
            video_durations = []
            for path in video_paths:
                try:
                    with VideoFileClip(path) as clip:
                        video_durations.append((path, clip.duration))
                except:
                    video_durations.append((path, 0))
            
            # 按时长排序
            video_durations.sort(key=lambda x: x[1])
            return [path for path, _ in video_durations[:grid_size]]
        else:
            return video_paths[:grid_size]
    
    def _resize_videos_for_grid(self, video_clips: List[VideoFileClip], rows: int, cols: int, 
                               target_size: Tuple[int, int] = None) -> List[VideoFileClip]:
        """
        为宫格布局调整视频尺寸
        
        Args:
            video_clips: 视频片段列表
            rows: 行数
            cols: 列数
            target_size: 目标总尺寸
            
        Returns:
            List[VideoFileClip]: 调整尺寸后的视频片段列表
        """
        if target_size is None:
            # 使用第一个视频的尺寸作为参考
            target_size = video_clips[0].size
        
        # 计算每个格子的尺寸
        cell_width = target_size[0] // cols
        cell_height = target_size[1] // rows
        
        resized_clips = []
        for clip in video_clips:
            resized_clip = clip.resize(newsize=(cell_width, cell_height))
            resized_clips.append(resized_clip)
        
        return resized_clips
    
    def create_grid_moviepy(self,
                           video_paths: List[str],
                           layout: str = '2×2',
                           output_path: str = None,
                           duration: float = None,
                           sync: bool = True,
                           selection_method: str = 'random',
                           target_size: Tuple[int, int] = (1920, 1080),
                           progress_callback: Optional[Callable] = None) -> str:
        """
        使用MoviePy创建宫格视频
        
        Args:
            video_paths: 输入视频路径列表
            layout: 宫格布局 ('2×1', '2×2', '3×1', '2×3' 等)
            output_path: 输出文件路径
            duration: 输出视频时长，None则使用最短视频的时长
            sync: 是否同步播放
            selection_method: 视频选择方法
            target_size: 输出视频尺寸
            progress_callback: 进度回调函数
            
        Returns:
            str: 输出文件路径
        """
        rows, cols = self._get_grid_dimensions(layout)
        grid_size = rows * cols
        
        # 选择视频
        selected_videos = self._select_videos(video_paths, grid_size, selection_method)
        
        if output_path is None:
            output_path = os.path.join(
                self.settings.OUTPUT_DIR, 
                'grid_videos', 
                f'grid_{layout}_{len(selected_videos)}_videos.mp4'
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"开始创建 {layout} 宫格视频...")
        print(f"选中的视频: {[os.path.basename(p) for p in selected_videos]}")
        
        # 加载视频片段
        video_clips = []
        for i, video_path in enumerate(selected_videos):
            try:
                clip = VideoFileClip(video_path)
                video_clips.append(clip)
                
                if progress_callback:
                    progress = (i + 1) / len(selected_videos) * 30  # 加载占30%进度
                    progress_callback(progress, f"加载视频 {i + 1}/{len(selected_videos)}")
                    
            except Exception as e:
                print(f"加载视频失败 {video_path}: {e}")
                continue
        
        if len(video_clips) != grid_size:
            raise RuntimeError(f"成功加载的视频数量不足: {len(video_clips)}/{grid_size}")
        
        try:
            # 确定视频时长
            if duration is None:
                if sync:
                    duration = min(clip.duration for clip in video_clips)
                else:
                    duration = max(clip.duration for clip in video_clips)
            
            # 裁剪到指定时长
            video_clips = [clip.subclip(0, min(duration, clip.duration)) for clip in video_clips]
            
            # 调整尺寸
            resized_clips = self._resize_videos_for_grid(video_clips, rows, cols, target_size)
            
            if progress_callback:
                progress_callback(60, "正在组合宫格...")
            
            # 创建宫格布局
            grid_clips = []
            for row in range(rows):
                row_clips = []
                for col in range(cols):
                    index = row * cols + col
                    if index < len(resized_clips):
                        row_clips.append(resized_clips[index])
                    else:
                        # 如果视频不够，用黑色背景填充
                        from moviepy.editor import ColorClip
                        cell_width = target_size[0] // cols
                        cell_height = target_size[1] // rows
                        black_clip = ColorClip(size=(cell_width, cell_height), color=(0, 0, 0), duration=duration)
                        row_clips.append(black_clip)
                grid_clips.append(row_clips)
            
            # 组合成宫格
            final_clip = clips_array(grid_clips)
            
            if progress_callback:
                progress_callback(80, "正在渲染输出...")
            
            # 输出视频
            final_clip.write_videofile(
                output_path,
                codec=self.settings.VIDEO_CODEC,
                audio_codec=self.settings.AUDIO_CODEC,
                bitrate=self.settings.VIDEO_BITRATE,
                verbose=False,
                logger=None
            )
            
            # 清理资源
            for clip in video_clips + resized_clips:
                clip.close()
            final_clip.close()
            
            if progress_callback:
                progress_callback(100, "宫格视频创建完成!")
            
            print(f"宫格视频创建成功: {output_path}")
            return output_path
            
        except Exception as e:
            # 清理资源
            for clip in video_clips:
                clip.close()
            raise RuntimeError(f"创建宫格视频失败: {e}")
    
    def create_grid_ffmpeg(self,
                          video_paths: List[str],
                          layout: str = '2×2',
                          output_path: str = None,
                          duration: float = None,
                          selection_method: str = 'random') -> str:
        """
        使用FFmpeg创建宫格视频 (更高效)
        
        Args:
            video_paths: 输入视频路径列表
            layout: 宫格布局
            output_path: 输出文件路径
            duration: 输出视频时长
            selection_method: 视频选择方法
            
        Returns:
            str: 输出文件路径
        """
        rows, cols = self._get_grid_dimensions(layout)
        grid_size = rows * cols
        
        # 选择视频
        selected_videos = self._select_videos(video_paths, grid_size, selection_method)
        
        if output_path is None:
            output_path = os.path.join(
                self.settings.OUTPUT_DIR, 
                'grid_videos', 
                f'grid_{layout}_ffmpeg.mp4'
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 构建FFmpeg命令
        cmd = ['ffmpeg']
        
        # 添加输入文件
        for video in selected_videos:
            cmd.extend(['-i', video])
        
        # 构建filter_complex
        filter_parts = []
        
        # 缩放每个视频
        for i in range(len(selected_videos)):
            filter_parts.append(f"[{i}:v] scale=iw/{cols}:ih/{rows} [v{i}]")
        
        # 构建xstack布局
        if layout == '2×1':
            layout_str = "0_0|w0_0"
        elif layout == '1×2':
            layout_str = "0_0|0_h0"
        elif layout == '2×2':
            layout_str = "0_0|w0_0|0_h0|w0_h0"
        elif layout == '3×1':
            layout_str = "0_0|w0_0|w0+w1_0"
        elif layout == '1×3':
            layout_str = "0_0|0_h0|0_h0+h1"
        elif layout == '2×3':
            layout_str = "0_0|w0_0|w0+w1_0|0_h0|w0_h0|w0+w1_h0"
        else:
            # 自动生成布局
            layout_parts = []
            for r in range(rows):
                for c in range(cols):
                    if r == 0 and c == 0:
                        layout_parts.append("0_0")
                    elif r == 0:
                        layout_parts.append("w0_0" if c == 1 else f"w0+w{c-1}_0")
                    elif c == 0:
                        layout_parts.append("0_h0" if r == 1 else f"0_h0+h{r-1}")
                    else:
                        layout_parts.append(f"w0_h0" if r == 1 and c == 1 else f"w0+w{c-1}_h0+h{r-1}")
            layout_str = "|".join(layout_parts)
        
        # xstack命令
        inputs = ''.join([f"[v{i}]" for i in range(len(selected_videos))])
        filter_parts.append(f"{inputs}xstack=inputs={len(selected_videos)}:layout={layout_str}[v]")
        
        cmd.extend(['-filter_complex', '; '.join(filter_parts)])
        cmd.extend(['-map', '[v]'])
        
        # 设置时长
        if duration:
            cmd.extend(['-t', str(duration)])
        
        # 输出参数
        cmd.extend([
            '-c:v', self.settings.VIDEO_CODEC,
            '-b:v', self.settings.VIDEO_BITRATE,
            '-y',
            output_path
        ])
        
        print(f"执行FFmpeg宫格命令: {' '.join(cmd[:10])}...")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"FFmpeg宫格视频创建成功: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg创建宫格视频失败: {e.stderr}")
    
    def create_grid_video(self,
                         video_paths: List[str],
                         layout: str = '2×2',
                         output_path: str = None,
                         duration: float = None,
                         method: str = 'moviepy',
                         sync: bool = True,
                         selection_method: str = 'random',
                         target_size: Tuple[int, int] = (1920, 1080),
                         progress_callback: Optional[Callable] = None) -> str:
        """
        统一的宫格视频创建接口
        
        Args:
            video_paths: 输入视频路径列表
            layout: 宫格布局
            output_path: 输出文件路径
            duration: 输出视频时长
            method: 创建方法 ('moviepy', 'ffmpeg')
            sync: 是否同步播放
            selection_method: 视频选择方法
            target_size: 输出视频尺寸
            progress_callback: 进度回调函数
            
        Returns:
            str: 输出文件路径
        """
        if method == 'ffmpeg':
            return self.create_grid_ffmpeg(
                video_paths, layout, output_path, duration, selection_method
            )
        else:  # moviepy
            return self.create_grid_moviepy(
                video_paths, layout, output_path, duration, sync, 
                selection_method, target_size, progress_callback
            )
    
    def batch_create_grids(self,
                          video_paths: List[str],
                          layouts: List[str] = ['2×2', '3×1', '2×3'],
                          output_dir: str = None,
                          num_variations: int = 3,
                          progress_callback: Optional[Callable] = None) -> List[str]:
        """
        批量创建多种宫格布局的视频
        
        Args:
            video_paths: 输入视频路径列表
            layouts: 要创建的布局列表
            output_dir: 输出目录
            num_variations: 每种布局创建的变体数量
            progress_callback: 进度回调函数
            
        Returns:
            List[str]: 输出文件路径列表
        """
        if output_dir is None:
            output_dir = os.path.join(self.settings.OUTPUT_DIR, 'batch_grids')
        
        os.makedirs(output_dir, exist_ok=True)
        
        output_files = []
        total_tasks = len(layouts) * num_variations
        completed = 0
        
        for layout in layouts:
            for variation in range(num_variations):
                try:
                    output_filename = f"grid_{layout}_v{variation + 1}.mp4"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    result = self.create_grid_video(
                        video_paths=video_paths,
                        layout=layout,
                        output_path=output_path,
                        selection_method='random'  # 每个变体随机选择
                    )
                    
                    output_files.append(result)
                    completed += 1
                    
                    if progress_callback:
                        progress = (completed / total_tasks) * 100
                        progress_callback(progress, f"完成 {layout} 变体 {variation + 1}")
                    
                except Exception as e:
                    print(f"创建宫格失败 [{layout} 变体 {variation + 1}]: {e}")
                    continue
        
        print(f"批量创建宫格视频完成! 共生成 {len(output_files)} 个文件到: {output_dir}")
        return output_files


# 命令行测试
if __name__ == "__main__":
    composer = GridComposer()
    
    # 测试用例 - 使用项目中的sock文件夹中的视频
    test_dir = "/home/admins/project/ffmpeg_ws/sock"
    
    if os.path.exists(test_dir):
        # 获取测试视频文件
        video_files = []
        for file in os.listdir(test_dir):
            if file.lower().endswith(('.mp4', '.mov', '.avi')):
                video_files.append(os.path.join(test_dir, file))
        
        if len(video_files) >= 4:
            print(f"找到 {len(video_files)} 个测试视频")
            
            def progress_callback(percent, message):
                print(f"进度: {percent:.1f}% - {message}")
            
            try:
                # 测试2×2宫格
                result = composer.create_grid_video(
                    video_paths=video_files,
                    layout='2×2',
                    duration=8.0,  # 8秒
                    progress_callback=progress_callback
                )
                print(f"成功创建宫格视频: {result}")
                
            except Exception as e:
                print(f"测试失败: {e}")
        else:
            print(f"测试视频数量不足: 需要至少4个，找到 {len(video_files)} 个")
    else:
        print(f"测试目录不存在: {test_dir}")