"""
功能4: 时长组合模块
将短视频片段组合成指定时长(10s、15s、20s)的视频，支持多种组合策略和转场效果
"""
import os
import random
from typing import List, Optional, Callable
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip

# 检查是否有转场效果功能
try:
    from moviepy.editor import crossfadein, crossfadeout, fadein, fadeout
    HAS_TRANSITIONS = True
except ImportError:
    HAS_TRANSITIONS = False
    print("Warning: MoviePy transition effects not available. Using basic transitions.")
from config.settings import Settings


class DurationComposer:
    """时长组合器"""
    
    def __init__(self):
        self.settings = Settings()
    
    def _select_clips_for_duration(self, 
                                  video_paths: List[str], 
                                  target_duration: float,
                                  strategy: str = 'random') -> List[str]:
        """
        为目标时长选择合适的视频片段
        
        Args:
            video_paths: 可用的视频片段路径列表
            target_duration: 目标总时长（秒）
            strategy: 选择策略 ('random', 'shortest', 'longest', 'balanced')
            
        Returns:
            List[str]: 选中的视频片段路径列表
        """
        if not video_paths:
            raise ValueError("视频片段列表为空")
        
        # 获取每个视频的时长信息
        video_info = []
        for path in video_paths:
            try:
                with VideoFileClip(path) as clip:
                    duration = clip.duration
                    video_info.append((path, duration))
            except:
                print(f"无法获取视频信息: {path}")
                continue
        
        if not video_info:
            raise ValueError("没有有效的视频片段")
        
        selected_clips = []
        current_duration = 0
        available_clips = video_info.copy()
        
        while current_duration < target_duration and available_clips:
            remaining_time = target_duration - current_duration
            
            if strategy == 'random':
                # 随机选择
                clip_path, clip_duration = random.choice(available_clips)
            elif strategy == 'shortest':
                # 优先选择最短的片段
                available_clips.sort(key=lambda x: x[1])
                clip_path, clip_duration = available_clips[0]
            elif strategy == 'longest':
                # 优先选择最长的片段
                available_clips.sort(key=lambda x: x[1], reverse=True)
                clip_path, clip_duration = available_clips[0]
            elif strategy == 'balanced':
                # 选择最接近剩余时间的片段
                best_clip = min(available_clips, 
                               key=lambda x: abs(x[1] - remaining_time))
                clip_path, clip_duration = best_clip
            else:
                clip_path, clip_duration = available_clips[0]
            
            selected_clips.append(clip_path)
            current_duration += clip_duration
            
            # 从可用列表中移除已选择的片段（避免重复）
            available_clips = [(p, d) for p, d in available_clips if p != clip_path]
            
            # 如果没有更多片段但时长不够，允许重复使用
            if not available_clips and current_duration < target_duration:
                available_clips = [(p, d) for p, d in video_info if p not in selected_clips[-3:]]  # 避免连续重复
        
        print(f"为目标时长 {target_duration}s 选择了 {len(selected_clips)} 个片段，总时长约 {current_duration:.1f}s")
        return selected_clips
    
    def _add_transitions(self, 
                        clips: List[VideoFileClip], 
                        transition_type: str = 'cut',
                        transition_duration: float = 0.5) -> VideoFileClip:
        """
        为视频片段添加转场效果
        
        Args:
            clips: 视频片段列表
            transition_type: 转场类型 ('cut', 'fade', 'crossfade')
            transition_duration: 转场持续时间(秒)
            
        Returns:
            VideoFileClip: 添加转场效果后的视频
        """
        if len(clips) == 1:
            return clips[0]
        
        if transition_type == 'cut' or not HAS_TRANSITIONS:
            # 直接拼接，无转场 (或不支持转场效果)
            return concatenate_videoclips(clips)
        
        elif transition_type == 'fade' and HAS_TRANSITIONS:
            # 淡入淡出转场
            transition_clips = []
            for i, clip in enumerate(clips):
                if i == 0:
                    # 第一个片段：只淡出
                    transition_clips.append(clip.fx(crossfadeout, transition_duration))
                elif i == len(clips) - 1:
                    # 最后一个片段：只淡入
                    transition_clips.append(clip.fx(crossfadein, transition_duration))
                else:
                    # 中间片段：淡入淡出
                    fade_clip = clip.fx(crossfadein, transition_duration).fx(crossfadeout, transition_duration)
                    transition_clips.append(fade_clip)
            
            return concatenate_videoclips(transition_clips)
        
        elif transition_type == 'crossfade' and HAS_TRANSITIONS:
            # 交叉淡化转场
            if len(clips) < 2:
                return clips[0]
            
            # 第一个片段
            final_clip = clips[0]
            
            for i in range(1, len(clips)):
                # 计算重叠时间
                overlap_duration = min(transition_duration, 
                                     min(final_clip.duration, clips[i].duration) / 2)
                
                # 创建交叉淡化效果
                clip1_end = final_clip.duration - overlap_duration
                clip2_start = overlap_duration
                
                # 分割片段
                part1 = final_clip.subclip(0, clip1_end)
                overlap1 = final_clip.subclip(clip1_end).fx(crossfadeout, overlap_duration)
                overlap2 = clips[i].subclip(0, overlap_duration).fx(crossfadein, overlap_duration)
                part2 = clips[i].subclip(overlap_duration)
                
                # 组合重叠部分
                overlap_composite = CompositeVideoClip([overlap1, overlap2])
                
                # 合并所有部分
                final_clip = concatenate_videoclips([part1, overlap_composite, part2])
            
            return final_clip
        
        else:
            # 默认无转场拼接
            return concatenate_videoclips(clips)
    
    def compose_duration_video(self,
                              video_paths: List[str],
                              target_duration: float = 15.0,
                              output_path: str = None,
                              strategy: str = 'random',
                              transition_type: str = 'crossfade',
                              transition_duration: float = 0.5,
                              trim_to_exact: bool = True,
                              progress_callback: Optional[Callable] = None) -> str:
        """
        组合视频片段到指定时长
        
        Args:
            video_paths: 输入视频片段路径列表
            target_duration: 目标时长（秒）
            output_path: 输出文件路径
            strategy: 片段选择策略
            transition_type: 转场类型
            transition_duration: 转场时长
            trim_to_exact: 是否精确裁剪到目标时长
            progress_callback: 进度回调函数
            
        Returns:
            str: 输出文件路径
        """
        if not video_paths:
            raise ValueError("视频片段列表为空")
        
        # 选择视频片段
        selected_paths = self._select_clips_for_duration(video_paths, target_duration, strategy)
        
        if output_path is None:
            output_path = os.path.join(
                self.settings.OUTPUT_DIR,
                'duration_videos',
                f'composed_{target_duration}s_{transition_type}.mp4'
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"开始组合 {target_duration}s 视频...")
        print(f"选中的片段: {[os.path.basename(p) for p in selected_paths]}")
        
        # 加载视频片段
        clips = []
        for i, path in enumerate(selected_paths):
            try:
                clip = VideoFileClip(path)
                clips.append(clip)
                
                if progress_callback:
                    progress = (i + 1) / len(selected_paths) * 30
                    progress_callback(progress, f"加载片段 {i + 1}/{len(selected_paths)}")
                    
            except Exception as e:
                print(f"加载视频片段失败 {path}: {e}")
                continue
        
        if not clips:
            raise RuntimeError("没有成功加载的视频片段")
        
        try:
            if progress_callback:
                progress_callback(50, "添加转场效果...")
            
            # 添加转场效果
            final_clip = self._add_transitions(clips, transition_type, transition_duration)
            
            # 精确裁剪到目标时长
            if trim_to_exact and final_clip.duration > target_duration:
                final_clip = final_clip.subclip(0, target_duration)
                print(f"裁剪到精确时长: {target_duration}s")
            
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
            for clip in clips:
                clip.close()
            final_clip.close()
            
            if progress_callback:
                progress_callback(100, "时长组合视频创建完成!")
            
            print(f"时长组合视频创建成功: {output_path}")
            return output_path
            
        except Exception as e:
            # 清理资源
            for clip in clips:
                clip.close()
            raise RuntimeError(f"创建时长组合视频失败: {e}")
    
    def batch_compose_durations(self,
                               video_paths: List[str],
                               target_durations: List[float] = [10, 15, 20],
                               output_dir: str = None,
                               num_variations: int = 3,
                               strategies: List[str] = ['random', 'balanced'],
                               transition_types: List[str] = ['crossfade', 'fade'],
                               progress_callback: Optional[Callable] = None) -> List[str]:
        """
        批量创建不同时长的组合视频
        
        Args:
            video_paths: 输入视频片段路径列表
            target_durations: 目标时长列表
            output_dir: 输出目录
            num_variations: 每种配置的变体数量
            strategies: 选择策略列表
            transition_types: 转场类型列表
            progress_callback: 进度回调函数
            
        Returns:
            List[str]: 输出文件路径列表
        """
        if output_dir is None:
            output_dir = os.path.join(self.settings.OUTPUT_DIR, 'batch_durations')
        
        os.makedirs(output_dir, exist_ok=True)
        
        output_files = []
        total_tasks = len(target_durations) * len(strategies) * len(transition_types) * num_variations
        completed = 0
        
        for duration in target_durations:
            for strategy in strategies:
                for transition in transition_types:
                    for variation in range(num_variations):
                        try:
                            output_filename = f"composed_{duration}s_{strategy}_{transition}_v{variation + 1}.mp4"
                            output_path = os.path.join(output_dir, output_filename)
                            
                            result = self.compose_duration_video(
                                video_paths=video_paths,
                                target_duration=duration,
                                output_path=output_path,
                                strategy=strategy,
                                transition_type=transition,
                                transition_duration=0.5
                            )
                            
                            output_files.append(result)
                            completed += 1
                            
                            if progress_callback:
                                progress = (completed / total_tasks) * 100
                                progress_callback(
                                    progress, 
                                    f"完成 {duration}s-{strategy}-{transition} 变体 {variation + 1}"
                                )
                            
                        except Exception as e:
                            print(f"创建组合视频失败 [{duration}s-{strategy}-{transition} v{variation + 1}]: {e}")
                            completed += 1
                            continue
        
        print(f"批量创建时长组合视频完成! 共生成 {len(output_files)} 个文件到: {output_dir}")
        return output_files
    
    def create_highlight_reel(self,
                             video_paths: List[str],
                             target_duration: float = 60.0,
                             clips_per_video: int = 3,
                             clip_duration: float = 5.0,
                             output_path: str = None,
                             progress_callback: Optional[Callable] = None) -> str:
        """
        创建精彩集锦视频
        
        Args:
            video_paths: 输入视频路径列表
            target_duration: 目标总时长
            clips_per_video: 每个视频提取的片段数
            clip_duration: 每个片段的时长
            output_path: 输出文件路径
            progress_callback: 进度回调函数
            
        Returns:
            str: 输出文件路径
        """
        if output_path is None:
            output_path = os.path.join(
                self.settings.OUTPUT_DIR,
                'highlight_reels',
                f'highlight_{target_duration}s.mp4'
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"开始创建精彩集锦: {target_duration}s")
        
        # 从每个视频中提取精彩片段
        all_clips = []
        for i, video_path in enumerate(video_paths):
            try:
                with VideoFileClip(video_path) as video:
                    video_duration = video.duration
                    
                    # 随机选择片段位置
                    for j in range(clips_per_video):
                        if video_duration > clip_duration:
                            max_start = video_duration - clip_duration
                            start_time = random.uniform(0, max_start)
                            end_time = start_time + clip_duration
                            
                            clip = video.subclip(start_time, end_time)
                            all_clips.append(clip)
                
                if progress_callback:
                    progress = (i + 1) / len(video_paths) * 50
                    progress_callback(progress, f"提取精彩片段 {i + 1}/{len(video_paths)}")
                    
            except Exception as e:
                print(f"处理视频失败 {video_path}: {e}")
                continue
        
        if not all_clips:
            raise RuntimeError("没有成功提取的视频片段")
        
        # 随机打乱片段顺序
        random.shuffle(all_clips)
        
        # 选择片段直到达到目标时长
        selected_clips = []
        current_duration = 0
        
        for clip in all_clips:
            if current_duration >= target_duration:
                break
            selected_clips.append(clip)
            current_duration += clip.duration
        
        if progress_callback:
            progress_callback(70, "组合精彩片段...")
        
        # 组合所有片段
        final_clip = concatenate_videoclips(selected_clips)
        
        # 裁剪到精确时长
        if final_clip.duration > target_duration:
            final_clip = final_clip.subclip(0, target_duration)
        
        if progress_callback:
            progress_callback(90, "正在渲染精彩集锦...")
        
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
        for clip in all_clips + selected_clips:
            clip.close()
        final_clip.close()
        
        if progress_callback:
            progress_callback(100, "精彩集锦创建完成!")
        
        print(f"精彩集锦创建成功: {output_path}")
        return output_path


# 命令行测试
if __name__ == "__main__":
    composer = DurationComposer()
    
    # 测试用例 - 使用已切割的视频片段
    test_dir = "/home/admins/project/ffmpeg_ws/video_clips/output/segments"
    
    # 如果没有切割好的片段，使用原始视频目录
    if not os.path.exists(test_dir):
        test_dir = "/home/admins/project/ffmpeg_ws/sock"
    
    if os.path.exists(test_dir):
        # 获取测试视频文件
        video_files = []
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.lower().endswith(('.mp4', '.mov', '.avi')):
                    video_files.append(os.path.join(root, file))
        
        if len(video_files) >= 3:
            print(f"找到 {len(video_files)} 个测试视频")
            
            def progress_callback(percent, message):
                print(f"进度: {percent:.1f}% - {message}")
            
            try:
                # 测试15秒组合视频
                result = composer.compose_duration_video(
                    video_paths=video_files[:6],  # 使用前6个视频
                    target_duration=15.0,
                    strategy='random',
                    transition_type='crossfade',
                    progress_callback=progress_callback
                )
                print(f"成功创建15秒组合视频: {result}")
                
            except Exception as e:
                print(f"测试失败: {e}")
        else:
            print(f"测试视频数量不足: 需要至少3个，找到 {len(video_files)} 个")
    else:
        print(f"测试目录不存在: {test_dir}")