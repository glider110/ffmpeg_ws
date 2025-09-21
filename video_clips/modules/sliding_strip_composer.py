"""
滑动条合成模块：1x3 布局，按规则播放/定格/黑屏，并在新视频到来时左移过渡动画。
"""
import os
from typing import List, Tuple, Optional, Callable
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, ImageClip

from config.settings import Settings


class SlidingStripComposer:
    def __init__(self):
        self.settings = Settings()

    def _parse_size(self, size_text: Optional[str], fallback: Tuple[int, int]) -> Tuple[int, int]:
        if not size_text:
            return fallback
        try:
            w, h = map(int, size_text.lower().replace('x', ' ').split())
            return (w, h)
        except Exception:
            return fallback

    def compose_1x3_sliding(
        self,
        video_paths: List[str],
        output_path: str,
        output_size: Optional[Tuple[int, int]] = None,
        transition_duration: float = 0.4,
        bg_color: Tuple[int, int, int] = (0, 0, 0),
        progress_callback: Optional[Callable] = None,
    ) -> str:
        if not video_paths:
            raise ValueError("视频列表为空")

        # 打开首个视频获取回退尺寸
        with VideoFileClip(video_paths[0]) as first:
            base_w, base_h = first.size

        if output_size is None:
            W, H = base_w, base_h
        else:
            W, H = output_size

        cell_w, cell_h = W // 3, H

        # 预加载所有视频（仅一次读取以获得时长、尺寸、最后帧）
        clips: List[VideoFileClip] = []
        resized: List[VideoFileClip] = []
        durations: List[float] = []
        try:
            total_count = len(video_paths)
            for idx, p in enumerate(video_paths):
                c = VideoFileClip(p)
                clips.append(c)
                r = c.resize(newsize=(cell_w, cell_h))
                resized.append(r)
                durations.append(c.duration)
                if progress_callback:
                    progress_callback(5 + (idx + 1) / total_count * 10, f"加载 {idx+1}/{total_count}")

            # 计算时间轴
            Δ = max(0.0, float(transition_duration))
            stages = []  # list of (start, end, type, payload)
            t = 0.0

            def add_stage(kind: str, dur: float, payload):
                nonlocal t
                stages.append((t, t + dur, kind, payload))
                t += dur

            n = len(resized)
            # Stage 1..3（无滑动）
            if n >= 1:
                add_stage('play1', durations[0], None)
            if n >= 2:
                add_stage('play2', durations[1], None)
            if n >= 3:
                add_stage('play3', durations[2], None)

            # 后续带滑动与播放
            for i in range(3, n):  # i = 3 表示第4个视频
                if Δ > 0:
                    add_stage('slide', Δ, {'i': i})
                add_stage('playN', durations[i], {'i': i})

            total_duration = t if n <= 3 else t

            # 生成叠加元素
            overlays = []

            def freeze_of(k: int) -> ImageClip:
                # 取最后一帧
                frame = resized[k].get_frame(max(0, durations[k] - 1e-3))
                img = ImageClip(frame).set_duration(1)  # 实际时长后续覆盖
                return img

            # 帮助函数：固定位置片段
            def add_fixed(imgclip_or_videoclip, start: float, duration: float, xcell: int):
                clip = imgclip_or_videoclip.set_start(start).set_duration(duration).set_position((xcell * cell_w, 0))
                overlays.append(clip)

            # 帮助函数：滑动动画：从 x0cell 到 x1cell 线性移动
            def add_slide(imgclip: ImageClip, start: float, duration: float, x0cell: float, x1cell: float):
                def pos_fn(tlocal):
                    α = 0 if duration <= 0 else max(0.0, min(1.0, tlocal / duration))
                    x = (x0cell + (x1cell - x0cell) * α) * cell_w
                    return (x, 0)
                overlays.append(imgclip.set_start(start).set_duration(duration).set_position(pos_fn))

            # 构建阶段
            current_time = 0.0
            stage_idx = 0
            for (s, e, kind, payload) in stages:
                dur = e - s
                if progress_callback:
                    progress_callback(20 + stage_idx / max(1, len(stages)) * 40, f"合成阶段 {stage_idx+1}/{len(stages)}: {kind}")
                if kind == 'play1':
                    # V1 live @ left
                    overlays.append(resized[0].subclip(0, durations[0]).set_start(s).set_position((0, 0)))
                elif kind == 'play2':
                    # left: V1 freeze, center: V2 live
                    add_fixed(freeze_of(0), s, dur, 0)
                    overlays.append(resized[1].subclip(0, durations[1]).set_start(s).set_position((cell_w, 0)))
                elif kind == 'play3':
                    # left: V1 freeze, center: V2 freeze, right: V3 live
                    add_fixed(freeze_of(0), s, dur, 0)
                    add_fixed(freeze_of(1), s, dur, 1)
                    overlays.append(resized[2].subclip(0, durations[2]).set_start(s).set_position((2 * cell_w, 0)))
                elif kind == 'slide':
                    i = payload['i']
                    # 在滑动窗口：V{i-3}, V{i-2}, V{i-1} 都是 freeze，整体左移，V{i} 尚未出现
                    add_slide(freeze_of(i - 3), s, dur, 0, -1)   # 左移并移出
                    add_slide(freeze_of(i - 2), s, dur, 1, 0)    # center -> left
                    add_slide(freeze_of(i - 1), s, dur, 2, 1)    # right -> center
                elif kind == 'playN':
                    i = payload['i']
                    # 左: V{i-2} freeze，中: V{i-1} freeze，右: Vi live
                    add_fixed(freeze_of(i - 2), s, dur, 0)
                    add_fixed(freeze_of(i - 1), s, dur, 1)
                    overlays.append(resized[i].subclip(0, durations[i]).set_start(s).set_position((2 * cell_w, 0)))
                stage_idx += 1

            # 背景与合成
            bg = ColorClip(size=(W, H), color=bg_color, duration=total_duration)
            final = CompositeVideoClip([bg] + overlays, size=(W, H))

            # 输出
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if progress_callback:
                progress_callback(80, "渲染输出...")
            final.write_videofile(
                output_path,
                codec=self.settings.VIDEO_CODEC,
                audio_codec=self.settings.AUDIO_CODEC,
                bitrate=self.settings.VIDEO_BITRATE,
                verbose=False,
                logger=None,
            )
            final.close()
            for r in resized:
                r.close()
            for c in clips:
                c.close()
            if progress_callback:
                progress_callback(100, "完成")
            return output_path
        except Exception:
            # 确保释放
            for r in resized:
                try:
                    r.close()
                except Exception:
                    pass
            for c in clips:
                try:
                    c.close()
                except Exception:
                    pass
            raise
