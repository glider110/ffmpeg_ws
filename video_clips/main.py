"""
Video Clips 主界面（PySimpleGUIQt 版）
实现五个剪辑任务 + 文件列表 + 收藏/清除收藏。
剪辑逻辑完全复用现有 modules，不做修改。
"""
from typing import List, Optional, Dict
import os
import threading
import traceback
import queue
from queue import Queue

import PySimpleGUIQt as sg

from config.settings import Settings
from modules.frame_extractor import FrameExtractor
from modules.video_splitter import VideoSplitter
from modules.grid_composer import GridComposer
from modules.duration_composer import DurationComposer
from modules.audio_mixer import AudioMixer
from modules.sliding_strip_composer import SlidingStripComposer
from utils.video_utils import VideoUtils


class QtVideoClipsApp:
    def __init__(self):
        self.settings = Settings()
        self.settings.ensure_dirs()

        # 收藏集合
        self.favorites = set()

        # 后台任务
        self.worker_thread: Optional[threading.Thread] = None
        self.cancel_flag = threading.Event()
        self._queue: Queue = Queue()

        # 业务模块
        self.extractor = FrameExtractor()
        self.splitter = VideoSplitter()
        self.gridder = GridComposer()
        self.dcomposer = DurationComposer()
        self.mixer = AudioMixer()
        self.vutils = VideoUtils()
        self.scomposer = SlidingStripComposer()

        # 文件/收藏数据（用于 Table 展示）
        # 每项: { path, name, duration_s, duration_str, size, size_str, resolution, format }
        self.file_items: List[Dict] = []
        self.fav_items: List[Dict] = []

        self.window = self._build_window()
        # 初始化滑块数值标签
        try:
            self._init_slider_labels()
        except Exception:
            pass

    # ---------- UI ----------
    def _build_window(self) -> sg.Window:
        # 使用浅色主题并统一背景色，避免在 Qt 后端出现黑底
        sg.theme('LightGrey1')
        base_font = ("Noto Sans CJK SC", max(11, getattr(self.settings, 'BASE_FONT_SIZE', 11)))
        bg = '#f6f6f6'
        try:
            sg.set_options(background_color=bg)
        except Exception:
            pass

        # 左侧：文件 + 收藏
        left_col = [
            [sg.Text('文件列表', font=base_font)],
            [
                sg.Button('添加文件', key='-ADD-FILES-'),
                sg.Button('添加文件夹', key='-ADD-FOLDER-'),
                sg.Button('删除选中', key='-DEL-'),
                sg.Button('清空', key='-CLEAR-'),
            ],
            [sg.Table(values=[["", "", "", "", ""]], headings=['文件名', '时长', '大小', '分辨率', '格式'],
                      key='-FILE-TABLE-',
                      auto_size_columns=False,
                      col_widths=[20, 8, 10, 10, 8],
                      justification='left',
                      select_mode=sg.TABLE_SELECT_MODE_EXTENDED,
                      num_rows=12, font=base_font,
                      background_color='white', text_color='#222')],
            [sg.Text('收藏列表', font=base_font)],
            [
                sg.Button('收藏选中', key='-FAV-ADD-'),
                sg.Button('取消收藏', key='-FAV-DEL-'),
                sg.Button('清空收藏', key='-FAV-CLEAR-'),
            ],
            [sg.Table(values=[["", "", "", "", ""]], headings=['文件名', '时长', '大小', '分辨率', '格式'],
                      key='-FAV-TABLE-',
                      auto_size_columns=False,
                      col_widths=[20, 8, 10, 10, 8],
                      justification='left',
                      select_mode=sg.TABLE_SELECT_MODE_EXTENDED,
                      num_rows=8, font=base_font,
                      background_color='white', text_color='#222')],
        ]

        # Tabs 右侧
        tab_extract = [
            [sg.Text('抽帧间隔(秒)'), 
             sg.Slider((1, 20), default_value=self.settings.DEFAULT_FRAME_INTERVAL, resolution=1, orientation='h', key='-EX-INTERVAL-', size=(30, 20), enable_events=True), 
             sg.Text(f"{self.settings.DEFAULT_FRAME_INTERVAL:.0f} 秒", key='-EX-INTERVAL-L-')],
            [sg.Text('图片格式'), sg.Combo(['png', 'jpg'], default_value='png', key='-EX-FORMAT-', readonly=True),
             sg.Text('方法'), sg.Combo(['auto', 'ffmpeg', 'moviepy', 'cv2'], default_value='ffmpeg', key='-EX-METHOD-', readonly=True)],
            [sg.Text('输出目录'), sg.Input(os.path.join(self.settings.OUTPUT_DIR, 'frames'), key='-EX-OUT-', size=(38, 1)), sg.Button('选择', key='-EX-OUT-SEL-')],
            [sg.Button('开始抽帧', key='-RUN-EXTRACT-')]
        ]

        tab_split = [
            [sg.Text('每段时长(秒)'), sg.Slider((3, 60), default_value=self.settings.DEFAULT_SEGMENT_DURATION, resolution=1, orientation='h', key='-SP-DUR-', size=(30, 20), enable_events=True), sg.Text('', key='-SP-DUR-L-')],
            [sg.Text('方法'), sg.Combo(['equal', 'random'], default_value='ffmpeg', key='-SP-METHOD-', readonly=True),
             sg.Text('重叠(秒)'), sg.Input('0.0', key='-SP-OVER-', size=(6, 1))],
            [sg.Text('随机: 数量'), sg.Input('8', key='-SP-R-N-', size=(6, 1)), sg.Text('最小秒'), sg.Input('5', key='-SP-R-MIN-', size=(6, 1)), sg.Text('最大秒'), sg.Input('10', key='-SP-R-MAX-', size=(6, 1))],
            [sg.Text('输出目录'), sg.Input(os.path.join(self.settings.OUTPUT_DIR, 'segments'), key='-SP-OUT-', size=(38, 1)), sg.Button('选择', key='-SP-OUT-SEL-')],
            [sg.Button('开始切割', key='-RUN-SPLIT-')]
        ]

        tab_grid = [
            [sg.Text('布局'), sg.Combo(list(self.settings.GRID_LAYOUTS.keys()), default_value='2×2', key='-GD-LAYOUT-', readonly=True),
             sg.Text('方法'), sg.Combo(['moviepy', 'ffmpeg'], default_value='moviepy', key='-GD-METHOD-', readonly=True)],
            [sg.Text('目标时长(秒，可留空)'), sg.Input('', key='-GD-DUR-', size=(10, 1)), sg.Checkbox('同步裁剪到最短', key='-GD-SYNC-', default=True)],
            [sg.Text('输出尺寸(WxH)'), sg.Input('1920x1080', key='-GD-SIZE-', size=(12, 1))],
            [sg.Text('输出文件'), sg.Input(os.path.join(self.settings.OUTPUT_DIR, 'grid_videos', 'grid_2x2.mp4'), key='-GD-OUT-', size=(38, 1)), sg.Button('选择', key='-GD-OUT-SEL-')],
            [sg.Button('创建宫格视频', key='-RUN-GRID-')]
        ]

        tab_duration = [
            [sg.Text('目标时长(秒)'), sg.Combo([10, 15, 20, 30, 60], default_value=15, key='-DU-DUR-', readonly=False)],
            [sg.Text('选择策略'), sg.Combo(['random', 'balanced', 'shortest', 'longest'], default_value='random', key='-DU-STRAT-', readonly=True)],
            [sg.Text('转场类型'), sg.Combo(['crossfade', 'fade', 'cut'], default_value='crossfade', key='-DU-TRAN-', readonly=True),
             sg.Text('转场秒'), sg.Input('0.5', key='-DU-TRAN-S-', size=(6, 1)), sg.Checkbox('精确裁剪', key='-DU-EXACT-', default=True)],
            [sg.Text('输出文件'), sg.Input(os.path.join(self.settings.OUTPUT_DIR, 'duration_videos', 'composed_15s.mp4'), key='-DU-OUT-', size=(38, 1)), sg.Button('选择', key='-DU-OUT-SEL-')],
            [sg.Button('开始组合', key='-RUN-DURATION-')]
        ]

        tab_audio = [
            [sg.Text('方法'), sg.Combo(['moviepy', 'ffmpeg'], default_value='moviepy', key='-AU-METHOD-', readonly=True)],
            [sg.Text('音乐音量'), sg.Input('0.3', key='-AU-MVOL-', size=(6, 1))],
            [sg.Text('视频音量'), sg.Input('0.7', key='-AU-VVOL-', size=(6, 1))],
            [sg.Text('淡入(秒)'), sg.Input('1.0', key='-AU-FIN-', size=(6, 1)), sg.Text('淡出(秒)'), sg.Input('1.0', key='-AU-FOUT-', size=(6, 1)), sg.Text('音乐偏移(秒)'), sg.Input('0', key='-AU-OFF-', size=(6, 1))],
            [sg.Text('音乐文件(可选)'), sg.Input('', key='-AU-MUSIC-', size=(38, 1)), sg.Button('选择', key='-AU-MUSIC-SEL-')],
            [sg.Checkbox('对每个选择视频批量处理', key='-AU-BATCH-', default=True)],
            [sg.Button('开始配音', key='-RUN-AUDIO-')]
        ]

        tab_sliding = [
            [sg.Text('输出尺寸(WxH)'), sg.Input('1920x1080', key='-SLI-SIZE-', size=(12, 1))],
            [sg.Text('转场Δt(秒)'), sg.Input('0.4', key='-SLI-DELTA-', size=(6, 1))],
            [sg.Text('输出文件'), sg.Input(os.path.join(self.settings.OUTPUT_DIR, 'sliding_1x3.mp4'), key='-SLI-OUT-', size=(38, 1)), sg.Button('选择', key='-SLI-OUT-SEL-')],
            [sg.Button('开始滑动合成', key='-RUN-SLIDING-')]
        ]

        right_col = [
            [sg.TabGroup([[
                sg.Tab('抽帧', tab_extract, background_color=bg),
                sg.Tab('切割', tab_split, background_color=bg),
                sg.Tab('宫格', tab_grid, background_color=bg),
                sg.Tab('时长', tab_duration, background_color=bg),
                sg.Tab('配音', tab_audio, background_color=bg),
                sg.Tab('1x3滑动', tab_sliding, background_color=bg),
            ]], key='-TABS-', background_color=bg)],
            [sg.ProgressBar(100, orientation='h', size=(45, 20), key='-PROG-', bar_color=('blue', '#e6e6e6')),
             sg.Button('停止', key='-STOP-')],
            [sg.Multiline(size=(90, 12), key='-LOG-', autoscroll=True, disabled=True, background_color='white', text_color='#222')],
        ]

        layout = [[sg.Column(left_col, background_color=bg), sg.Column(right_col, background_color=bg)]]

        return sg.Window('视频剪辑工具（PySimpleGUIQt）', layout, finalize=True, font=base_font, background_color=bg)

    # ---------- 通用 ----------
    def _log(self, text: str):
        if threading.current_thread() is not threading.main_thread():
            # 在线程中，将日志推送到队列，由主线程消费
            try:
                self._queue.put((
                    'log', text
                ))
                return
            except Exception:
                pass
        try:
            self.window['-LOG-'].print(text)
        except Exception:
            prev = self.window['-LOG-'].get()
            self.window['-LOG-'].update(prev + text + '\n')

    def _set_progress(self, value: float, message: str = ''):
        value = max(0, min(100, int(value)))
        self.window['-PROG-'].update(value)
        if message:
            self._log(message)

    def _init_slider_labels(self):
        # 初始化分段时长与抽帧间隔滑块的显示
        try:
            val = float(self.window['-SP-DUR-'].get())
        except Exception:
            val = float(getattr(self.settings, 'DEFAULT_SEGMENT_DURATION', 8))
        try:
            self.window['-SP-DUR-L-'].update(f"{val:.0f}")
        except Exception:
            pass
        # 抽帧间隔
        try:
            ex_val = float(self.window['-EX-INTERVAL-'].get())
        except Exception:
            ex_val = float(getattr(self.settings, 'DEFAULT_FRAME_INTERVAL', 1.0))
        try:
            self.window['-EX-INTERVAL-L-'].update(f"{ex_val:.0f} 秒")
        except Exception:
            pass

    def _progress_callback_factory(self, prefix=''):
        def cb(percent, message):
            # 通过队列传递进度
            try:
                self._queue.put(('progress', (percent, f"{prefix}{message}")))
            except Exception:
                pass
        return cb

    def _get_selected_files(self, values: Optional[dict] = None) -> List[str]:
        """获取当前选择的文件（兼容 PySimpleGUI 与 PySimpleGUIQt）。
        优先使用文件列表选中；否则使用收藏选中；都没有则返回全部文件列表。
        """
        def rows_to_paths(rows: List[int], items: List[Dict]) -> List[str]:
            paths: List[str] = []
            for idx in rows:
                if 0 <= idx < len(items):
                    paths.append(items[idx]['path'])
            return paths

        if values is None:
            return [it['path'] for it in self.file_items]

        file_sel_rows = values.get('-FILE-TABLE-', []) or []
        fav_sel_rows = values.get('-FAV-TABLE-', []) or []

        paths = rows_to_paths(file_sel_rows, self.file_items)
        if not paths:
            paths = rows_to_paths(fav_sel_rows, self.fav_items)
        if not paths:
            paths = [it['path'] for it in self.file_items]
        return paths

    # ---------- 文件表与收藏表 辅助 ----------
    def _format_seconds(self, sec: float) -> str:
        try:
            sec = float(sec)
        except Exception:
            return '--:--'
        if sec <= 0:
            return '--:--'
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"

    def _gather_info(self, path: str) -> Dict:
        info = self.vutils.get_video_info(path) or {}
        name = os.path.basename(path)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        size_str = self._format_file_size(size)
        duration = float(info.get('duration', 0.0)) if info else 0.0
        duration_str = self._format_seconds(duration)
        if info and 'video' in info:
            w = info['video'].get('width', 0)
            h = info['video'].get('height', 0)
        else:
            w = h = 0
        resolution = f"{w}x{h}" if w and h else '-'
        fmt = info.get('format_name') if info else None
        if not fmt:
            fmt = os.path.splitext(name)[1].lstrip('.').lower() or '-'
        return {
            'path': path,
            'name': name,
            'size': size,
            'size_str': size_str,
            'duration_s': duration,
            'duration_str': duration_str,
            'resolution': resolution,
            'format': fmt,
        }

    def _format_file_size(self, size_bytes: int) -> str:
        if size_bytes <= 0:
            return '0 B'
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        size = float(size_bytes)
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        return f"{size:.1f} {units[i]}"

    def _refresh_file_table(self):
        values = [[it['name'], it['duration_str'], it['size_str'], it['resolution'], it['format']] for it in self.file_items]
        if not values:
            values = [["", "", "", "", ""]]
        self.window['-FILE-TABLE-'].update(values)

    def _refresh_fav_table(self):
        values = [[it['name'], it['duration_str'], it['size_str'], it['resolution'], it['format']] for it in self.fav_items]
        if not values:
            values = [["", "", "", "", ""]]
        self.window['-FAV-TABLE-'].update(values)

    # ---------- 任务 ----------
    def run_extract(self, values):
        files = self._get_selected_files(values)
        if not files:
            self._log('请选择至少一个视频文件用于抽帧')
            return
        interval = float(values['-EX-INTERVAL-'] or 1.0)
        fmt = values['-EX-FORMAT-']
        method = values['-EX-METHOD-']
        outdir_root = values['-EX-OUT-']

        def work():
            try:
                for fp in files:
                    if self.cancel_flag.is_set():
                        break
                    name = os.path.splitext(os.path.basename(fp))[0]
                    outdir = os.path.join(outdir_root, name)
                    os.makedirs(outdir, exist_ok=True)
                    self._log(f'抽帧: {fp} -> {outdir}')
                    result = self.extractor.extract_frames(
                        video_path=fp,
                        output_dir=outdir,
                        interval=interval,
                        image_format=fmt,
                        method=method,
                        progress_callback=self._progress_callback_factory(f"[{name}] ")
                    )
                    self._queue.put(('log', f'完成抽帧 {len(result)} 张: {name}'))
                self._queue.put(('done', None))
            except Exception:
                self._queue.put(('error', traceback.format_exc()))

        self._start_worker(work)

    def run_split(self, values):
        files = self._get_selected_files(values)
        if not files:
            self._log('请选择至少一个视频文件用于切割')
            return
        seg_dur = float(values['-SP-DUR-'])
        method = values['-SP-METHOD-']
        try:
            overlap = float(values['-SP-OVER-'] or 0.0)
        except Exception:
            overlap = 0.0
        outdir_root = values['-SP-OUT-']
        r_n = int(values['-SP-R-N-'] or 8)
        r_min = float(values['-SP-R-MIN-'] or 5)
        r_max = float(values['-SP-R-MAX-'] or 10)

        def work():
            try:
                for fp in files:
                    if self.cancel_flag.is_set():
                        break
                    name = os.path.splitext(os.path.basename(fp))[0]
                    outdir = os.path.join(outdir_root, name)
                    os.makedirs(outdir, exist_ok=True)
                    self._log(f'切割: {fp} -> {outdir} ({method})')
                    if method == 'ffmpeg':
                        result = self.splitter.split_video_ffmpeg(fp, segment_duration=seg_dur, overlap=overlap, output_dir=outdir)
                    elif method == 'random':
                        result = self.splitter.split_video_random(fp, num_segments=r_n, min_duration=r_min, max_duration=r_max, output_dir=outdir, progress_callback=self._progress_callback_factory(f"[{name}] "))
                    else:
                        result = self.splitter.split_video_equal(fp, segment_duration=seg_dur, output_dir=outdir, overlap=overlap, progress_callback=self._progress_callback_factory(f"[{name}] "))
                    self._queue.put(('log', f'完成切割 {len(result)} 段: {name}'))
                self._queue.put(('done', None))
            except Exception:
                self._queue.put(('error', traceback.format_exc()))

        self._start_worker(work)

    def run_grid(self, values):
        files = self._get_selected_files(values)
        if len(files) < 2:
            self._log('请选择至少两个视频用于宫格组合')
            return
        layout = values['-GD-LAYOUT-']
        method = values['-GD-METHOD-']
        dur_text = values['-GD-DUR-'].strip()
        duration = float(dur_text) if dur_text else None
        sync = bool(values['-GD-SYNC-'])
        size_text = values['-GD-SIZE-']
        try:
            w, h = map(int, size_text.lower().replace('x', ' ').split())
            target_size = (w, h)
        except Exception:
            target_size = (1920, 1080)
        out_file = values['-GD-OUT-']

        def work():
            try:
                self._log(f'宫格: {layout}, {method}, 输出: {out_file}')
                if method == 'ffmpeg':
                    result = self.gridder.create_grid_ffmpeg(files, layout=layout, output_path=out_file, duration=duration)
                else:
                    result = self.gridder.create_grid_moviepy(files, layout=layout, output_path=out_file, duration=duration, sync=sync, target_size=target_size, progress_callback=self._progress_callback_factory('[grid] '))
                self._queue.put(('log', f'宫格创建成功: {result}'))
                self._queue.put(('done', None))
            except Exception:
                self._queue.put(('error', traceback.format_exc()))

        self._start_worker(work)

    def run_duration(self, values):
        files = self._get_selected_files(values)
        if len(files) < 1:
            self._log('请选择至少一个视频片段用于时长组合')
            return
        target = float(values['-DU-DUR-'])
        strategy = values['-DU-STRAT-']
        tran = values['-DU-TRAN-']
        tran_s = float(values['-DU-TRAN-S-'] or 0.5)
        exact = bool(values['-DU-EXACT-'])
        out_file = values['-DU-OUT-']

        def work():
            try:
                self._log(f'时长组合: {target}s, {strategy}, {tran} -> {out_file}')
                result = self.dcomposer.compose_duration_video(
                    video_paths=files,
                    target_duration=target,
                    output_path=out_file,
                    strategy=strategy,
                    transition_type=tran,
                    transition_duration=tran_s,
                    trim_to_exact=exact,
                    progress_callback=self._progress_callback_factory('[duration] ')
                )
                self._queue.put(('log', f'时长组合成功: {result}'))
                self._queue.put(('done', None))
            except Exception:
                self._queue.put(('error', traceback.format_exc()))

        self._start_worker(work)

    def run_audio(self, values):
        files = self._get_selected_files(values)
        if len(files) < 1:
            self._log('请选择至少一个视频用于配音')
            return
        method = values['-AU-METHOD-']
        try:
            mvol = float(values['-AU-MVOL-'] or 0.3)
        except Exception:
            mvol = 0.3
        try:
            vvol = float(values['-AU-VVOL-'] or 0.7)
        except Exception:
            vvol = 0.7
        fin = float(values['-AU-FIN-'] or 1.0)
        fout = float(values['-AU-FOUT-'] or 1.0)
        offset = float(values['-AU-OFF-'] or 0)
        music_file = values['-AU-MUSIC-'].strip() or None
        batch = bool(values['-AU-BATCH-'])

        def work():
            try:
                if batch and len(files) > 1 and music_file is None:
                    self._log('批量配音：将为每个视频选择音乐')
                    results = self.mixer.batch_add_music(
                        video_paths=files,
                        music_volume=mvol,
                        video_volume=vvol,
                        unique_music=True,
                        progress_callback=self._progress_callback_factory('[batch-audio] ')
                    )
                    self._queue.put(('log', f'批量配音完成: {len(results)} 个输出'))
                else:
                    for fp in files:
                        if self.cancel_flag.is_set():
                            break
                        self._log(f'为 {os.path.basename(fp)} 添加音乐...')
                        if method == 'ffmpeg':
                            out_path = self.mixer.add_music_to_video_ffmpeg(
                                video_path=fp,
                                music_path=music_file,
                                music_volume=mvol,
                                video_volume=vvol,
                                fade_duration=max(fin, fout),
                                music_start_offset=offset
                            )
                        else:
                            out_path = self.mixer.add_music_to_video_moviepy(
                                video_path=fp,
                                music_path=music_file,
                                music_volume=mvol,
                                video_volume=vvol,
                                fade_in_duration=fin,
                                fade_out_duration=fout,
                                music_start_offset=offset,
                                progress_callback=self._progress_callback_factory('[audio] ')
                            )
                        self._queue.put(('log', f'完成：{out_path}'))
                self._queue.put(('done', None))
            except Exception:
                self._queue.put(('error', traceback.format_exc()))

        self._start_worker(work)

    def run_sliding(self, values):
        files = self._get_selected_files(values)
        if len(files) < 1:
            self._log('请选择至少一个视频用于 1x3 滑动合成')
            return
        size_text = (values.get('-SLI-SIZE-') or '1920x1080').strip()
        try:
            w, h = map(int, size_text.lower().replace('x', ' ').split())
            target_size = (w, h)
        except Exception:
            target_size = (1920, 1080)
        # slider 直接是 float
        try:
            delta = float(values.get('-SLI-DELTA-', 0.4) or 0.4)
        except Exception:
            delta = 0.4
        out_file = values.get('-SLI-OUT-') or os.path.join(self.settings.OUTPUT_DIR, 'sliding_1x3.mp4')

        def work():
            try:
                self._log(f'1x3滑动合成: 输出 {out_file}, 尺寸 {target_size}, Δt={delta}s')
                result = self.scomposer.compose_1x3_sliding(
                    video_paths=files,
                    output_path=out_file,
                    output_size=target_size,
                    transition_duration=delta,
                    progress_callback=self._progress_callback_factory('[sliding] ')
                )
                self._queue.put(('log', f'滑动合成成功: {result}'))
                self._queue.put(('done', None))
            except Exception:
                self._queue.put(('error', traceback.format_exc()))

        self._start_worker(work)

    # ---------- 线程 ----------
    def _start_worker(self, target):
        if self.worker_thread and self.worker_thread.is_alive():
            self._log('已有任务在执行中，请先停止或等待完成')
            return
        self.cancel_flag.clear()
        self._set_progress(0)
        self.window['-LOG-'].update('')
        self.worker_thread = threading.Thread(target=target, daemon=True)
        self.worker_thread.start()

    def _stop_worker(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.cancel_flag.set()
            self._log('请求停止任务，可能需要等待当前操作完成...')

    # ---------- 事件循环 ----------
    def run(self):
        while True:
            event, values = self.window.read(timeout=200)
            if event in (sg.WIN_CLOSED, 'Exit'):
                break

            # 文件与收藏
            if event == '-ADD-FILES-':
                try:
                    paths = sg.popup_get_file('选择文件（可多选）', multiple_files=True, no_window=True)
                except TypeError:
                    paths = sg.popup_get_file('选择文件', no_window=True)
                if paths:
                    if isinstance(paths, (list, tuple)):
                        candidates = list(paths)
                    else:
                        candidates = [p for p in str(paths).split(';')]
                    for p in candidates:
                        if p and os.path.isfile(p):
                            if all(it['path'] != p for it in self.file_items):
                                try:
                                    self.file_items.append(self._gather_info(p))
                                except Exception:
                                    self.file_items.append(self._gather_info(p))
                    self._refresh_file_table()

            elif event == '-ADD-FOLDER-':
                try:
                    folder = sg.popup_get_folder('选择文件夹', no_window=True)
                except TypeError:
                    folder = sg.popup_get_folder('选择文件夹')
                if folder and os.path.isdir(folder):
                    for root, _, files in os.walk(folder):
                        for f in files:
                            if any(f.lower().endswith(ext) for ext in self.settings.SUPPORTED_VIDEO_FORMATS):
                                p = os.path.join(root, f)
                                if all(it['path'] != p for it in self.file_items):
                                    self.file_items.append(self._gather_info(p))
                    self._refresh_file_table()

            elif event == '-DEL-':
                sel_rows: List[int] = values.get('-FILE-TABLE-', []) or []
                if sel_rows:
                    # 删除选中行（从后往前）
                    for idx in sorted(sel_rows, reverse=True):
                        if 0 <= idx < len(self.file_items):
                            # 同步移出收藏
                            path = self.file_items[idx]['path']
                            self.fav_items = [it for it in self.fav_items if it['path'] != path]
                            del self.file_items[idx]
                    self._refresh_file_table()
                    self._refresh_fav_table()

            elif event == '-CLEAR-':
                self.file_items.clear()
                self._refresh_file_table()

            elif event == '-FAV-ADD-':
                sel_rows: List[int] = values.get('-FILE-TABLE-', []) or []
                for idx in sel_rows:
                    if 0 <= idx < len(self.file_items):
                        item = self.file_items[idx]
                        if all(it['path'] != item['path'] for it in self.fav_items):
                            self.fav_items.append(item)
                self._refresh_fav_table()

            elif event == '-FAV-DEL-':
                sel_rows: List[int] = values.get('-FAV-TABLE-', []) or []
                if sel_rows:
                    for idx in sorted(sel_rows, reverse=True):
                        if 0 <= idx < len(self.fav_items):
                            del self.fav_items[idx]
                    self._refresh_fav_table()

            elif event == '-FAV-CLEAR-':
                self.fav_items.clear()
                self._refresh_fav_table()

            # 参数联动（分段时长与抽帧间隔）
            if event == '-SP-DUR-':
                self.window['-SP-DUR-L-'].update(f"{values['-SP-DUR-']:.0f}")
            elif event == '-EX-INTERVAL-':
                try:
                    self.window['-EX-INTERVAL-L-'].update(f"{float(values['-EX-INTERVAL-']):.0f} 秒")
                except Exception:
                    self.window['-EX-INTERVAL-L-'].update("")

            # 选择对话
            if event == '-EX-OUT-SEL-':
                try:
                    folder = sg.popup_get_folder('选择输出目录', no_window=True, default_path=values['-EX-OUT-'] or self.settings.OUTPUT_DIR)
                except TypeError:
                    folder = sg.popup_get_folder('选择输出目录', default_path=values['-EX-OUT-'] or self.settings.OUTPUT_DIR)
                if folder:
                    self.window['-EX-OUT-'].update(folder)
            elif event == '-SP-OUT-SEL-':
                try:
                    folder = sg.popup_get_folder('选择输出目录', no_window=True, default_path=values['-SP-OUT-'] or self.settings.OUTPUT_DIR)
                except TypeError:
                    folder = sg.popup_get_folder('选择输出目录', default_path=values['-SP-OUT-'] or self.settings.OUTPUT_DIR)
                if folder:
                    self.window['-SP-OUT-'].update(folder)
            elif event == '-GD-OUT-SEL-':
                try:
                    fname = sg.popup_get_file('选择输出文件', no_window=True, save_as=True, default_extension='.mp4', file_types=(('MP4', '*.mp4'),))
                except TypeError:
                    fname = sg.popup_get_file('选择输出文件', save_as=True, default_extension='.mp4', file_types=(('MP4', '*.mp4'),))
                if fname:
                    self.window['-GD-OUT-'].update(fname)
            elif event == '-DU-OUT-SEL-':
                try:
                    fname = sg.popup_get_file('选择输出文件', no_window=True, save_as=True, default_extension='.mp4', file_types=(('MP4', '*.mp4'),))
                except TypeError:
                    fname = sg.popup_get_file('选择输出文件', save_as=True, default_extension='.mp4', file_types=(('MP4', '*.mp4'),))
                if fname:
                    self.window['-DU-OUT-'].update(fname)
            elif event == '-SLI-OUT-SEL-':
                try:
                    fname = sg.popup_get_file('选择输出文件', no_window=True, save_as=True, default_extension='.mp4', file_types=(('MP4', '*.mp4'),))
                except TypeError:
                    fname = sg.popup_get_file('选择输出文件', save_as=True, default_extension='.mp4', file_types=(('MP4', '*.mp4'),))
                if fname:
                    self.window['-SLI-OUT-'].update(fname)
            elif event == '-AU-MUSIC-SEL-':
                # 兼容 PySimpleGUIQt：使用空格分隔的扩展名模式，并提供默认路径到音频目录
                start_path = values.get('-AU-MUSIC-') or getattr(self.settings, 'MUSIC_DIR', None)
                try:
                    fname = sg.popup_get_file(
                        '选择音乐文件',
                        no_window=True,
                        default_path=start_path,
                        file_types=(
                            ("音频", "*.mp3 *.MP3 *.wav *.WAV *.m4a *.M4A"),
                            ("所有文件", "*.*"),
                        ),
                    )
                except TypeError:
                    fname = sg.popup_get_file(
                        '选择音乐文件',
                        default_path=start_path,
                        file_types=(
                            ("音频", "*.mp3 *.MP3 *.wav *.WAV *.m4a *.M4A"),
                            ("所有文件", "*.*"),
                        ),
                    )
                if fname:
                    self.window['-AU-MUSIC-'].update(fname)

            # 运行任务
            if event == '-RUN-EXTRACT-':
                self.run_extract(values)
            elif event == '-RUN-SPLIT-':
                self.run_split(values)
            elif event == '-RUN-GRID-':
                self.run_grid(values)
            elif event == '-RUN-DURATION-':
                self.run_duration(values)
            elif event == '-RUN-AUDIO-':
                self.run_audio(values)
            elif event == '-RUN-SLIDING-':
                self.run_sliding(values)
            elif event == '-STOP-':
                self._stop_worker()

            # 后台回传（队列轮询）
            try:
                while True:
                    item = self._queue.get_nowait()
                    kind = item[0]
                    if kind == 'progress':
                        percent, message = item[1]
                        self._set_progress(percent, message)
                    elif kind == 'log':
                        self._log(item[1])
                    elif kind == 'error':
                        self._log('发生错误:\n' + item[1])
                        self._set_progress(0)
                        self.worker_thread = None
                    elif kind == 'done':
                        self._set_progress(100, '处理完成')
                        self.worker_thread = None
                    self._queue.task_done()
            except queue.Empty:
                pass

        self.window.close()


def main():
    app = QtVideoClipsApp()
    app.run()


if __name__ == '__main__':
    main()

"""
Video Clips 主界面
集成所有功能模块的GUI界面
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import Settings
from modules.frame_extractor import FrameExtractor
from modules.video_splitter import VideoSplitter
from modules.grid_composer import GridComposer
from modules.duration_composer import DurationComposer
from modules.audio_mixer import AudioMixer
from utils.file_handler import FileHandler
from utils.video_utils import VideoUtils


class VideoClipsGUI:
    def open_favorites_window(self):
        """打开收藏文件列表新窗口，支持剪辑操作"""
        fav_win = tk.Toplevel(self.root)
        fav_win.title("收藏文件列表")
        fav_win.geometry("700x400")
        columns = ('文件名', '大小', '时长', '分辨率', '状态')
        fav_tree = ttk.Treeview(fav_win, columns=columns, show='tree headings', height=15)
        fav_tree.heading('#0', text='路径')
        for col in columns:
            fav_tree.heading(col, text=col)
            fav_tree.column(col, width=100)
        fav_tree.column('#0', width=200)
        fav_tree.pack(fill=tk.BOTH, expand=True)
        # 填充收藏文件
        for file_path in self.favorites:
            # 查找主列表对应项，获取values
            for item in self.file_tree.get_children():
                if self.file_tree.item(item, 'text') == file_path:
                    values = self.file_tree.item(item, 'values')
                    fav_tree.insert('', 'end', text=file_path, values=values)
                    break
        # 剪辑按钮
        def process_selected():
            selected_files = [fav_tree.item(item, 'text') for item in fav_tree.selection()]
            if not selected_files:
                messagebox.showinfo("提示", "请先选择要剪辑的文件！")
                return
            # 使用主流程进行处理
            self.current_files = selected_files
            try:
                self.update_file_count()
            except Exception:
                pass
            fav_win.destroy()
            # 走统一的开始处理逻辑（内部会开线程并更新进度/状态）
            self.start_processing()
        btn = ttk.Button(fav_win, text="剪辑选中收藏文件", command=process_selected)
        btn.pack(pady=8)
    def delete_selected_file(self):
        """删除主文件列表选中的文件"""
        selected = self.file_tree.selection()
        for item in selected:
            file_path = self.file_tree.item(item, 'text')
            if file_path in self.current_files:
                self.current_files.remove(file_path)
            self.file_tree.delete(item)
        self.file_count_label.config(text=f"文件数: {len(self.current_files)}")
    def create_file_panel(self, parent):
        # 文件列表和收藏列表整体容器
        list_container = ttk.Frame(parent)
        list_container.pack(fill=tk.BOTH, expand=True)

        # 文件列表
        file_frame = ttk.LabelFrame(list_container, text="文件列表", padding=5)
        file_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # 操作按钮
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="清空列表", command=self.clear_file_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_selected_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="收藏/取消收藏", command=self.toggle_favorite_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="打开收藏文件窗口", command=self.open_favorites_window).pack(side=tk.LEFT, padx=2)

        # 创建主文件列表
        columns = ('文件名', '大小', '时长', '分辨率', '状态')
        self.file_tree = ttk.Treeview(file_frame, columns=columns, show='tree headings', height=8)
        self.file_tree.heading('#0', text='路径')
        for col in columns:
            self.file_tree.heading(col, text=col)
        self.file_tree.column('#0', width=200)
        self.file_tree.column('文件名', width=150)
        self.file_tree.column('大小', width=80)
        self.file_tree.column('时长', width=80)
        self.file_tree.column('分辨率', width=100)
        self.file_tree.column('状态', width=100)
        file_scrolly = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        file_scrollx = ttk.Scrollbar(file_frame, orient=tk.HORIZONTAL, command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=file_scrolly.set, xscrollcommand=file_scrollx.set)
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        file_scrollx.pack(side=tk.BOTTOM, fill=tk.X)

        # 收藏文件列表
        fav_frame = ttk.LabelFrame(list_container, text="收藏文件列表", padding=5)
        fav_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.fav_tree = ttk.Treeview(fav_frame, columns=columns, show='tree headings', height=5)
        self.fav_tree.heading('#0', text='路径')
        for col in columns:
            self.fav_tree.heading(col, text=col)
        self.fav_tree.column('#0', width=200)
        self.fav_tree.column('文件名', width=150)
        self.fav_tree.column('大小', width=80)
        self.fav_tree.column('时长', width=80)
        self.fav_tree.column('分辨率', width=100)
        self.fav_tree.column('状态', width=100)
        fav_scrolly = ttk.Scrollbar(fav_frame, orient=tk.VERTICAL, command=self.fav_tree.yview)
        fav_scrollx = ttk.Scrollbar(fav_frame, orient=tk.HORIZONTAL, command=self.fav_tree.xview)
        self.fav_tree.configure(yscrollcommand=fav_scrolly.set, xscrollcommand=fav_scrollx.set)
        self.fav_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fav_scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        fav_scrollx.pack(side=tk.BOTTOM, fill=tk.X)

    def toggle_favorite_file(self):
        """收藏或取消收藏选中的文件，并同步到收藏列表"""
        selected = self.file_tree.selection()
        for item in selected:
            file_path = self.file_tree.item(item, 'text')
            if file_path in self.favorites:
                self.favorites.remove(file_path)
                self.file_tree.set(item, '状态', '')
                # 从收藏列表移除
                for fav_item in self.fav_tree.get_children():
                    if self.fav_tree.item(fav_item, 'text') == file_path:
                        self.fav_tree.delete(fav_item)
                        break
            else:
                self.favorites.add(file_path)
                self.file_tree.set(item, '状态', '★收藏')
                # 添加到收藏列表
                values = self.file_tree.item(item, 'values')
                self.fav_tree.insert('', 'end', text=file_path, values=values)

    def get_selected_files(self):
        """获取当前选中的文件（主列表和收藏列表）"""
        files = []
        # 主列表选中
        for item in self.file_tree.selection():
            files.append(self.file_tree.item(item, 'text'))
        # 收藏列表选中
        for item in self.fav_tree.selection():
            files.append(self.fav_tree.item(item, 'text'))
        return files

    def start_processing(self):
        """开始处理时，支持主列表和收藏列表选中的文件"""
        self.current_files = self.get_selected_files()
        self.is_processing = True
        self.update_progress(0, "开始处理...")
        function = self.function_var.get()
        threading.Thread(target=self.run_processing, args=(function,), daemon=True).start()
    def __init__(self):
        self.favorites = set()  # 收藏的文件路径集合
        self.settings = Settings()
        self.settings.ensure_dirs()
        # 初始化功能模块
        self.frame_extractor = FrameExtractor()
        self.video_splitter = VideoSplitter()
        self.grid_composer = GridComposer()
        self.duration_composer = DurationComposer()
        self.audio_mixer = AudioMixer()
        self.file_handler = FileHandler()
        self.video_utils = VideoUtils()
        
        # GUI状态变量
        self.current_files = []
        self.current_function = None
        self.is_processing = False
        
        # 创建主窗口
        self.setup_main_window()
        
        # 创建界面组件
        self.create_menu()
        self.create_toolbar()
        self.create_main_panels()
        self.create_status_bar()
        
        # 绑定事件
        self.bind_events()
    
    def setup_main_window(self):
        """设置主窗口"""
        self.root = tk.Tk()
        self.root.title("Video Clips - 智能视频剪辑工具 v1.0")
        self.root.geometry(f"{self.settings.WINDOW_WIDTH}x{self.settings.WINDOW_HEIGHT}")
        self.root.minsize(800, 600)
        
        # 设置中文字体
        self.setup_fonts()
        
        # 设置窗口居中
        self.center_window()
        
        # 设置主题样式
        self.style = ttk.Style()
        self.style.theme_use('clam')  # 使用现代主题
        
        # 配置ttk样式的字体
        self.configure_ttk_fonts()
        # 配置更柔和的前景色
        self.configure_colors()
    
    def setup_fonts(self):
        """设置中文字体"""
        import tkinter.font as tkFont
        
        # 设置DPI感知
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass  # 非Windows系统或者没有相关API
        
        # 优先选择现代中文无衬线字体（更清爽）
        font_candidates = [
            "Noto Sans CJK SC",    # Noto 思源黑体 (常见)
            "Source Han Sans SC",  # 思源黑体（另一命名）
            "Noto Sans SC",        # Noto Sans SC
            "PingFang SC",         # 苹方（macOS 常见）
            "Microsoft YaHei",     # 微软雅黑（Windows 常见）
            "HarmonyOS Sans SC",   # 鸿蒙 Sans（可选）
            "WenQuanYi Micro Hei", # 文泉驿微米黑（Linux 常见）
            "sarasa gothic sc",    # 更纱黑体
            "LXGW WenKai",         # 霞鹜文楷（可读性佳）
            "song ti",             # 宋体（退而求其次）
            "fangsong ti",         # 仿宋体（退而求其次）
            "Liberation Sans",     # 通用备用
            "DejaVu Sans",         # 通用备用
            "Arial",               # 最终备用
        ]
        
        # 检测可用字体（支持不区分大小写与模糊匹配）
        try:
            available_fonts = list(tkFont.families())
            fonts_lower_map = {name.lower(): name for name in available_fonts}
            selected_font = None

            # 先按候选清单精确/忽略大小写匹配
            for font in font_candidates:
                key = font.lower()
                if key in fonts_lower_map:
                    selected_font = fonts_lower_map[key]
                    break

            # 若未命中，进行模糊匹配（关键词包含）
            if selected_font is None:
                fuzzy_keys = [
                    ("noto", "sc"),
                    ("source han sans", "sc"),
                    ("wenquanyi", "micro"),
                    ("pingfang", "sc"),
                    ("microsoft", "yahei"),
                    ("sarasa", "gothic", "sc"),
                    ("lxgw", "wenkai"),
                ]
                for fname in available_fonts:
                    low = fname.lower()
                    for keys in fuzzy_keys:
                        if all(k in low for k in keys):
                            selected_font = fname
                            break
                    if selected_font:
                        break

            # 如果匹配到宋体/仿宋体，但系统也有更柔和的文泉驿黑体，则优先替换为文泉驿
            if selected_font and selected_font.lower() in ("song ti", "fangsong ti"):
                if "wenquanyi micro hei" in fonts_lower_map:
                    selected_font = fonts_lower_map["wenquanyi micro hei"]
        except Exception:
            selected_font = None
        
        # 如果没有找到合适字体，直接使用已安装的中文字体
        if selected_font is None:
            # 直接指定为Linux下的中文字体
            selected_font = "Noto Sans CJK SC"
            print(f"字体检测失败，强制使用: {selected_font}")
        else:
            print(f"检测到字体: {selected_font}")
        
        # 如果还是None，使用系统默认并警告
        if selected_font is None:
            try:
                selected_font = tkFont.nametofont("TkDefaultFont").actual()['family']
                print(f"使用系统默认字体: {selected_font}")
            except:
                selected_font = "Liberation Sans"
                print(f"使用备用字体: {selected_font}")
        
        print(f"最终使用字体: {selected_font}")
        
        # 获取系统DPI缩放比例
        try:
            dpi = self.root.winfo_fpixels('1i')
            scale_factor = max(1.0, dpi / 96.0)  # 96 DPI是标准，最小为1.0
        except:
            scale_factor = 1.0
        # 叠加用户自定义 UI 缩放
        scale_factor *= getattr(self.settings, 'UI_SCALE', 1.0)
        # 将 Tk 的缩放设置为与 DPI 一致，避免小字号发糊
        try:
            self.root.tk.call('tk', 'scaling', scale_factor)
        except Exception:
            pass
        
        # 根据DPI调整字体大小
        # 基础字号 = 用户基准字号 * 缩放
        base_size = max(self.settings.BASE_FONT_SIZE, int(self.settings.BASE_FONT_SIZE * scale_factor))
        
        # 创建不同大小的字体
        self.default_font = tkFont.Font(family=selected_font, size=base_size)
        self.title_font = tkFont.Font(family=selected_font, size=base_size + 2, weight='normal')
        self.heading_font = tkFont.Font(family=selected_font, size=base_size + 1, weight='normal')
        self.small_font = tkFont.Font(family=selected_font, size=max(8, base_size - 1))
        self.large_font = tkFont.Font(family=selected_font, size=base_size + 3)
        
        # 设置tk的默认字体
        self.root.option_add('*Font', self.default_font.name)
        self.root.option_add('*Dialog.msg.font', self.default_font.name)
        self.root.option_add('*Dialog.dtl.font', self.small_font.name)
        
    def configure_ttk_fonts(self):
        """配置ttk组件的字体"""
        # 配置ttk样式
        self.style.configure('TLabel', font=self.default_font)
        self.style.configure('TButton', font=self.default_font)
        self.style.configure('TCheckbutton', font=self.default_font)
        self.style.configure('TRadiobutton', font=self.default_font)
        self.style.configure('TEntry', font=self.default_font)
        self.style.configure('TCombobox', font=self.default_font)
        self.style.configure('TSpinbox', font=self.default_font)
        self.style.configure('TScale', font=self.default_font)
        
        # 框架和容器
        self.style.configure('TLabelFrame', font=self.heading_font)
        self.style.configure('TLabelFrame.Label', font=self.heading_font)
        
        # Notebook标签字体
        self.style.configure('TNotebook.Tab', font=self.default_font, padding=[8, 4])
        
        # Treeview字体
        self.style.configure('Treeview', font=self.default_font, rowheight=int(self.default_font['size'] * 1.8))
        self.style.configure('Treeview.Heading', font=self.heading_font)
        
        # 特殊样式
        self.style.configure('Title.TLabel', font=self.title_font)
        self.style.configure('Small.TLabel', font=self.small_font)
        self.style.configure('Large.TLabel', font=self.large_font)
        
        # 进度条样式
        self.style.configure('TProgressbar', thickness=20)

    def configure_colors(self):
        """配置全局前景颜色，减轻纯黑带来的“墨迹感”"""
        palette = {
            'fg_primary': '#333333',   # 主文本颜色（深灰）
            'fg_heading': '#222222',   # 标题略深
            'fg_secondary': '#555555', # 次级文字
            'fg_disabled': '#888888',  # 禁用文字
            'bg_panel': '#f6f6f6',     # 面板浅灰
            'bg_base': '#ffffff',      # 基础白
            'bg_heading': '#ededed',   # 标题栏浅灰
        }
        # 保存以便其他位置复用
        self._palette = palette
        # 常用控件
        self.style.configure('TLabel', foreground=palette['fg_primary'], background=palette['bg_panel'])
        self.style.configure('TButton', foreground=palette['fg_primary'])
        self.style.configure('TRadiobutton', foreground=palette['fg_primary'], background=palette['bg_panel'])
        self.style.configure('TCheckbutton', foreground=palette['fg_primary'], background=palette['bg_panel'])
        self.style.configure('TEntry', foreground=palette['fg_primary'])
        self.style.configure('TCombobox', foreground=palette['fg_primary'])
        self.style.configure('TSpinbox', foreground=palette['fg_primary'])
        self.style.configure('TScale', foreground=palette['fg_primary'], background=palette['bg_panel'])
        # 容器和标题
        self.style.configure('TFrame', background=palette['bg_panel'])
        self.style.configure('TLabelframe', background=palette['bg_panel'])
        self.style.configure('TLabelFrame.Label', foreground=palette['fg_heading'], background=palette['bg_panel'])
        self.style.configure('TNotebook.Tab', foreground=palette['fg_primary'])
        # 列表
        self.style.configure('Treeview', foreground=palette['fg_primary'], background=palette['bg_base'], fieldbackground=palette['bg_base'])
        self.style.configure('Treeview.Heading', foreground=palette['fg_heading'], background=palette['bg_heading'])

    def center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.settings.WINDOW_WIDTH // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.settings.WINDOW_HEIGHT // 2)
        self.root.geometry(f"{self.settings.WINDOW_WIDTH}x{self.settings.WINDOW_HEIGHT}+{x}+{y}")
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root, font=self.default_font)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0, font=self.default_font)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="选择视频文件", command=self.select_video_files)
        file_menu.add_command(label="选择文件夹", command=self.select_folder)
        file_menu.add_separator()
        file_menu.add_command(label="清空文件列表", command=self.clear_file_list)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0, font=self.default_font)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="清理临时文件", command=self.cleanup_temp_files)
        tools_menu.add_command(label="打开输出目录", command=self.open_output_dir)
        tools_menu.add_command(label="视频信息分析", command=self.analyze_videos)
        tools_menu.add_separator()
        tools_menu.add_command(label="打开收藏文件窗口", command=self.open_favorites_window)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0, font=self.default_font)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar_frame = ttk.Frame(self.root)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 文件选择按钮
        ttk.Button(toolbar_frame, text="📁 选择视频", 
                  command=self.select_video_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="📂 选择文件夹", 
                  command=self.select_folder).pack(side=tk.LEFT, padx=2)
        
        # 分隔符
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 快速功能按钮
        ttk.Button(toolbar_frame, text="抽帧",
                  command=lambda: self.switch_function('frame_extract')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="切割",
                  command=lambda: self.switch_function('video_split')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="宫格",
                  command=lambda: self.switch_function('grid_compose')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="组合",
                  command=lambda: self.switch_function('duration_compose')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="配音",
                  command=lambda: self.switch_function('audio_mix')).pack(side=tk.LEFT, padx=2)
        
        # 右侧按钮
        ttk.Button(toolbar_frame, text="清理",
                  command=self.cleanup_temp_files).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar_frame, text="分析",
                  command=self.analyze_videos).pack(side=tk.RIGHT, padx=2)
    
    def create_main_panels(self):
        """创建主要面板"""
        # 创建主容器
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧面板 - 功能选择和参数设置
        left_panel = ttk.Frame(main_container)
        main_container.add(left_panel, weight=1)
        
        # 右侧面板 - 文件列表和预览
        right_panel = ttk.Frame(main_container)
        main_container.add(right_panel, weight=2)
        
        # 创建左侧面板内容
        self.create_function_panel(left_panel)
        
        # 创建右侧面板内容
        self.create_file_panel(right_panel)
    
    def create_function_panel(self, parent):
        """创建功能面板"""
        # 功能选择
        function_frame = ttk.LabelFrame(parent, text="功能选择", padding=10)
        function_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.function_var = tk.StringVar(value='frame_extract')
        
        functions = [
            ('frame_extract', '[抽帧] 视频抽帧'),
            ('video_split', '[切割] 视频切割'),
            ('grid_compose', '[宫格] 宫格组合'),
            ('duration_compose', '[时长] 时长组合'),
            ('audio_mix', '[音乐] 音乐配对')
        ]
        
        for value, text in functions:
            ttk.Radiobutton(function_frame, text=text, variable=self.function_var,
                           value=value, command=self.on_function_change).pack(anchor=tk.W, pady=2)
        
        # 参数设置面板
        self.params_frame = ttk.LabelFrame(parent, text="参数设置", padding=10)
        self.params_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 初始化参数面板
        self.create_frame_extract_params()
        
        # 执行控制
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(control_frame, text="开始处理", 
                                      command=self.start_processing, style='Accent.TButton')
        self.start_button.pack(fill=tk.X, pady=(0, 5))
        
        self.stop_button = ttk.Button(control_frame, text="停止处理", 
                                     command=self.stop_processing, state='disabled')
        self.stop_button.pack(fill=tk.X)
    
    def create_file_panel(self, parent):
        # 文件列表
        file_frame = ttk.LabelFrame(parent, text="文件列表", padding=5)
        file_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 操作按钮
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="清空列表", command=self.clear_file_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_selected_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="收藏/取消收藏", command=self.toggle_favorite_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="打开收藏文件窗口", command=self.open_favorites_window).pack(side=tk.LEFT, padx=2)

        # 创建Treeview用于显示文件
        columns = ('文件名', '大小', '时长', '分辨率', '状态')
        self.file_tree = ttk.Treeview(file_frame, columns=columns, show='tree headings', height=15)

        # 设置列标题
        self.file_tree.heading('#0', text='路径')
        for col in columns:
            self.file_tree.heading(col, text=col)
        
        # 设置列宽
        self.file_tree.column('#0', width=200)
        self.file_tree.column('文件名', width=150)
        self.file_tree.column('大小', width=80)
        self.file_tree.column('时长', width=80)
        self.file_tree.column('分辨率', width=100)
        self.file_tree.column('状态', width=100)

        # 添加滚动条
        file_scrolly = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        file_scrollx = ttk.Scrollbar(file_frame, orient=tk.HORIZONTAL, command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=file_scrolly.set, xscrollcommand=file_scrollx.set)

        # 布局
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        file_scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 预览面板
        preview_frame = ttk.LabelFrame(parent, text="处理进度", padding=5)
        preview_frame.pack(fill=tk.X)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(preview_frame, variable=self.progress_var, 
                                          maximum=100, length=300)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # 状态文本
        self.status_text = tk.Text(preview_frame, height=6, wrap=tk.WORD, font=self.default_font)
        status_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scroll.set)
        
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def toggle_favorite_file(self):
        """收藏或取消收藏选中的文件"""
        selected = self.file_tree.selection()
        for item in selected:
            file_path = self.file_tree.item(item, 'text')
            if file_path in self.favorites:
                self.favorites.remove(file_path)
                self.file_tree.set(item, '状态', '')
            else:
                self.favorites.add(file_path)
                self.file_tree.set(item, '状态', '★收藏')
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_bar, text="就绪", foreground=getattr(self, '_palette', {}).get('fg_secondary', '#555555'))
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.file_count_label = ttk.Label(self.status_bar, text="文件数: 0", foreground=getattr(self, '_palette', {}).get('fg_secondary', '#555555'))
        self.file_count_label.pack(side=tk.RIGHT, padx=5)
    
    def bind_events(self):
        """绑定事件"""
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 文件树双击事件
        self.file_tree.bind('<Double-1>', self.on_file_double_click)
        
        # 文件树右键菜单
        self.file_tree.bind('<Button-3>', self.show_file_context_menu)
    
    def on_function_change(self):
        """功能选择改变事件"""
        function = self.function_var.get()
        
        # 清空参数面板
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        # 根据选择的功能创建对应的参数面板
        if function == 'frame_extract':
            self.create_frame_extract_params()
        elif function == 'video_split':
            self.create_video_split_params()
        elif function == 'grid_compose':
            self.create_grid_compose_params()
        elif function == 'duration_compose':
            self.create_duration_compose_params()
        elif function == 'audio_mix':
            self.create_audio_mix_params()
    
    def create_frame_extract_params(self):
        """创建视频抽帧参数面板"""
        # 抽帧间隔
        ttk.Label(self.params_frame, text="抽帧间隔 (秒):").pack(anchor=tk.W)
        self.frame_interval_var = tk.DoubleVar(value=1.0)
        interval_frame = ttk.Frame(self.params_frame)
        interval_frame.pack(fill=tk.X, pady=(0, 10))
        self.frame_interval_scale = ttk.Scale(interval_frame, from_=0.5, to=10.0, variable=self.frame_interval_var,
                 orient=tk.HORIZONTAL)
        self.frame_interval_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.frame_interval_label = ttk.Label(interval_frame, text=f"{self.frame_interval_var.get():.1f} 秒")
        self.frame_interval_label.pack(side=tk.LEFT, padx=8)
        def update_interval_label(*args):
            self.frame_interval_label.config(text=f"{self.frame_interval_var.get():.1f} 秒")
        self.frame_interval_var.trace_add('write', update_interval_label)
        
        # 图片格式
        ttk.Label(self.params_frame, text="输出格式:").pack(anchor=tk.W)
        self.frame_format_var = tk.StringVar(value='png')
        format_frame = ttk.Frame(self.params_frame)
        format_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Radiobutton(format_frame, text='PNG', variable=self.frame_format_var, 
                       value='png').pack(side=tk.LEFT)
        ttk.Radiobutton(format_frame, text='JPG', variable=self.frame_format_var, 
                       value='jpg').pack(side=tk.LEFT, padx=(20, 0))
        
        # 提取方法
        ttk.Label(self.params_frame, text="提取方法:").pack(anchor=tk.W)
        self.frame_method_var = tk.StringVar(value='cv2')
        method_frame = ttk.Frame(self.params_frame)
        method_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Radiobutton(method_frame, text='OpenCV', variable=self.frame_method_var,
                       value='cv2').pack(side=tk.LEFT)
        ttk.Radiobutton(method_frame, text='FFmpeg', variable=self.frame_method_var,
                       value='ffmpeg').pack(side=tk.LEFT, padx=(20, 0))
        ttk.Radiobutton(method_frame, text='MoviePy', variable=self.frame_method_var,
                       value='moviepy').pack(side=tk.LEFT, padx=(20, 0))
    
    def create_video_split_params(self):
        """创建视频切割参数面板"""
        # 切割时长
        ttk.Label(self.params_frame, text="切割时长 (秒):").pack(anchor=tk.W)
        self.split_duration_var = tk.DoubleVar(value=8.0)
        split_duration_frame = ttk.Frame(self.params_frame)
        split_duration_frame.pack(fill=tk.X, pady=(0, 10))
        self.split_duration_scale = ttk.Scale(split_duration_frame, from_=5.0, to=30.0, variable=self.split_duration_var,
                 orient=tk.HORIZONTAL)
        self.split_duration_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.split_duration_label = ttk.Label(split_duration_frame, text=f"{self.split_duration_var.get():.1f} 秒")
        self.split_duration_label.pack(side=tk.LEFT, padx=8)
        def update_split_duration_label(*args):
            self.split_duration_label.config(text=f"{self.split_duration_var.get():.1f} 秒")
        self.split_duration_var.trace_add('write', update_split_duration_label)
        
        # 切割方法
        ttk.Label(self.params_frame, text="切割方法:").pack(anchor=tk.W)
        self.split_method_var = tk.StringVar(value='equal')
        method_frame = ttk.Frame(self.params_frame)
        method_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Radiobutton(method_frame, text='等时长', variable=self.split_method_var,
                       value='equal').pack(side=tk.LEFT)
        ttk.Radiobutton(method_frame, text='随机时长', variable=self.split_method_var,
                       value='random').pack(side=tk.LEFT, padx=(20, 0))
        
        # 重叠时间
        ttk.Label(self.params_frame, text="重叠时间 (秒):").pack(anchor=tk.W)
        self.split_overlap_var = tk.DoubleVar(value=0.0)
        split_overlap_frame = ttk.Frame(self.params_frame)
        split_overlap_frame.pack(fill=tk.X, pady=(0, 10))
        self.split_overlap_scale = ttk.Scale(split_overlap_frame, from_=0.0, to=5.0, variable=self.split_overlap_var,
                 orient=tk.HORIZONTAL)
        self.split_overlap_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.split_overlap_label = ttk.Label(split_overlap_frame, text=f"{self.split_overlap_var.get():.1f} 秒")
        self.split_overlap_label.pack(side=tk.LEFT, padx=8)
        def update_split_overlap_label(*args):
            self.split_overlap_label.config(text=f"{self.split_overlap_var.get():.1f} 秒")
        self.split_overlap_var.trace_add('write', update_split_overlap_label)
    
    def create_grid_compose_params(self):
        """创建宫格组合参数面板"""
        # 宫格布局
        ttk.Label(self.params_frame, text="宫格布局:").pack(anchor=tk.W)
        self.grid_layout_var = tk.StringVar(value='2×2')
        layout_combo = ttk.Combobox(self.params_frame, textvariable=self.grid_layout_var,
                                   values=list(self.settings.GRID_LAYOUTS.keys()),
                                   state='readonly')
        layout_combo.pack(fill=tk.X, pady=(0, 10))
        
        # 视频时长
        ttk.Label(self.params_frame, text="输出时长 (秒):").pack(anchor=tk.W)
        self.grid_duration_var = tk.DoubleVar(value=8.0)
        grid_duration_frame = ttk.Frame(self.params_frame)
        grid_duration_frame.pack(fill=tk.X, pady=(0, 10))
        self.grid_duration_scale = ttk.Scale(grid_duration_frame, from_=5.0, to=30.0, variable=self.grid_duration_var,
                 orient=tk.HORIZONTAL)
        self.grid_duration_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.grid_duration_label = ttk.Label(grid_duration_frame, text=f"{self.grid_duration_var.get():.1f} 秒")
        self.grid_duration_label.pack(side=tk.LEFT, padx=8)
        def update_grid_duration_label(*args):
            self.grid_duration_label.config(text=f"{self.grid_duration_var.get():.1f} 秒")
        self.grid_duration_var.trace_add('write', update_grid_duration_label)
        
        # 选择策略
        ttk.Label(self.params_frame, text="选择策略:").pack(anchor=tk.W)
        self.grid_selection_var = tk.StringVar(value='random')
        selection_combo = ttk.Combobox(self.params_frame, textvariable=self.grid_selection_var,
                                      values=['random', 'first', 'duration'],
                                      state='readonly')
        selection_combo.pack(fill=tk.X, pady=(0, 10))
    
    def create_duration_compose_params(self):
        """创建时长组合参数面板"""
        # 目标时长
        ttk.Label(self.params_frame, text="目标时长 (秒):").pack(anchor=tk.W)
        self.duration_target_var = tk.DoubleVar(value=15.0)
        duration_target_frame = ttk.Frame(self.params_frame)
        duration_target_frame.pack(fill=tk.X, pady=(0, 10))
        self.duration_target_scale = ttk.Scale(duration_target_frame, from_=10.0, to=60.0, variable=self.duration_target_var,
                 orient=tk.HORIZONTAL)
        self.duration_target_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.duration_target_label = ttk.Label(duration_target_frame, text=f"{self.duration_target_var.get():.1f} 秒")
        self.duration_target_label.pack(side=tk.LEFT, padx=8)
        def update_duration_target_label(*args):
            self.duration_target_label.config(text=f"{self.duration_target_var.get():.1f} 秒")
        self.duration_target_var.trace_add('write', update_duration_target_label)
        
        # 组合策略
        ttk.Label(self.params_frame, text="组合策略:").pack(anchor=tk.W)
        self.duration_strategy_var = tk.StringVar(value='random')
        strategy_combo = ttk.Combobox(self.params_frame, textvariable=self.duration_strategy_var,
                                     values=['random', 'shortest', 'longest', 'balanced'],
                                     state='readonly')
        strategy_combo.pack(fill=tk.X, pady=(0, 10))
        
        # 转场类型
        ttk.Label(self.params_frame, text="转场类型:").pack(anchor=tk.W)
        self.duration_transition_var = tk.StringVar(value='crossfade')
        transition_combo = ttk.Combobox(self.params_frame, textvariable=self.duration_transition_var,
                                       values=['crossfade', 'fade', 'cut'],
                                       state='readonly')
        transition_combo.pack(fill=tk.X, pady=(0, 10))
    
    def create_audio_mix_params(self):
        """创建音乐配对参数面板"""
        # 音乐音量
        ttk.Label(self.params_frame, text="音乐音量:").pack(anchor=tk.W)
        self.music_volume_var = tk.DoubleVar(value=0.3)
        music_volume_frame = ttk.Frame(self.params_frame)
        music_volume_frame.pack(fill=tk.X, pady=(0, 10))
        self.music_volume_scale = ttk.Scale(music_volume_frame, from_=0.0, to=1.0, variable=self.music_volume_var,
                 orient=tk.HORIZONTAL)
        self.music_volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.music_volume_label = ttk.Label(music_volume_frame, text=f"{self.music_volume_var.get():.2f}")
        self.music_volume_label.pack(side=tk.LEFT, padx=8)
        def update_music_volume_label(*args):
            self.music_volume_label.config(text=f"{self.music_volume_var.get():.2f}")
        self.music_volume_var.trace_add('write', update_music_volume_label)
        
        # 视频音量
        ttk.Label(self.params_frame, text="视频音量:").pack(anchor=tk.W)
        self.video_volume_var = tk.DoubleVar(value=0.7)
        video_volume_frame = ttk.Frame(self.params_frame)
        video_volume_frame.pack(fill=tk.X, pady=(0, 10))
        self.video_volume_scale = ttk.Scale(video_volume_frame, from_=0.0, to=1.0, variable=self.video_volume_var,
                 orient=tk.HORIZONTAL)
        self.video_volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.video_volume_label = ttk.Label(video_volume_frame, text=f"{self.video_volume_var.get():.2f}")
        self.video_volume_label.pack(side=tk.LEFT, padx=8)
        def update_video_volume_label(*args):
            self.video_volume_label.config(text=f"{self.video_volume_var.get():.2f}")
        self.video_volume_var.trace_add('write', update_video_volume_label)
        
        # 淡入淡出
        ttk.Label(self.params_frame, text="淡入时长 (秒):").pack(anchor=tk.W)
        self.fade_in_var = tk.DoubleVar(value=1.0)
        fade_in_frame = ttk.Frame(self.params_frame)
        fade_in_frame.pack(fill=tk.X, pady=(0, 10))
        self.fade_in_scale = ttk.Scale(fade_in_frame, from_=0.0, to=5.0, variable=self.fade_in_var,
                 orient=tk.HORIZONTAL)
        self.fade_in_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.fade_in_label = ttk.Label(fade_in_frame, text=f"{self.fade_in_var.get():.1f} 秒")
        self.fade_in_label.pack(side=tk.LEFT, padx=8)
        def update_fade_in_label(*args):
            self.fade_in_label.config(text=f"{self.fade_in_var.get():.1f} 秒")
        self.fade_in_var.trace_add('write', update_fade_in_label)
        
        ttk.Label(self.params_frame, text="淡出时长 (秒):").pack(anchor=tk.W)
        self.fade_out_var = tk.DoubleVar(value=1.0)
        fade_out_frame = ttk.Frame(self.params_frame)
        fade_out_frame.pack(fill=tk.X, pady=(0, 10))
        self.fade_out_scale = ttk.Scale(fade_out_frame, from_=0.0, to=5.0, variable=self.fade_out_var,
                 orient=tk.HORIZONTAL)
        self.fade_out_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.fade_out_label = ttk.Label(fade_out_frame, text=f"{self.fade_out_var.get():.1f} 秒")
        self.fade_out_label.pack(side=tk.LEFT, padx=8)
        def update_fade_out_label(*args):
            self.fade_out_label.config(text=f"{self.fade_out_var.get():.1f} 秒")
        self.fade_out_var.trace_add('write', update_fade_out_label)
    
    def switch_function(self, function):
        """切换功能"""
        self.function_var.set(function)
        self.on_function_change()
    
    def select_video_files(self):
        """选择视频文件"""
        file_types = [
            ('视频文件', '*.mp4 *.avi *.mov *.mkv *.MOV'),
            ('所有文件', '*.*')
        ]
        
        files = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=file_types
        )
        
        if files:
            self.add_files_to_list(files)
    
    def select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择包含视频的文件夹")
        
        if folder:
            video_files = self.file_handler.get_video_files(folder, recursive=True)
            if video_files:
                self.add_files_to_list(video_files)
                self.log_message(f"从文件夹 {folder} 添加了 {len(video_files)} 个视频文件")
            else:
                messagebox.showwarning("警告", "选择的文件夹中没有找到视频文件")
    
    def add_files_to_list(self, files):
        """添加文件到列表"""
        for file_path in files:
            if file_path not in self.current_files:
                self.current_files.append(file_path)
                
                # 获取文件信息
                file_info = self.get_file_info(file_path)
                
                # 添加到树形视图
                self.file_tree.insert('', 'end', 
                                     text=file_path,
                                     values=(
                                         file_info['filename'],
                                         file_info['size'],
                                         file_info['duration'],
                                         file_info['resolution'],
                                         '就绪'
                                     ))
        
        self.update_file_count()
    
    def get_file_info(self, file_path):
        """获取文件信息"""
        try:
            info = self.video_utils.get_video_info(file_path)
            if info:
                return {
                    'filename': os.path.basename(file_path),
                    'size': self.file_handler.format_file_size(info.get('filesize', 0)),
                    'duration': f"{info.get('duration', 0):.1f}s",
                    'resolution': f"{info['video']['width']}x{info['video']['height']}"
                }
        except:
            pass
        
        return {
            'filename': os.path.basename(file_path),
            'size': self.file_handler.format_file_size(self.file_handler.get_file_size(file_path)),
            'duration': '未知',
            'resolution': '未知'
        }
    
    def clear_file_list(self):
        """清空文件列表"""
        self.current_files.clear()
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        self.update_file_count()
        self.log_message("文件列表已清空")
    
    def update_file_count(self):
        """更新文件计数"""
        count = len(self.current_files)
        self.file_count_label.config(text=f"文件数: {count}")
    
    def log_message(self, message):
        """记录消息到状态文本框"""
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_progress(self, value, message=""):
        """更新进度条"""
        self.progress_var.set(value)
        if message:
            self.log_message(message)
        self.root.update_idletasks()
    
    def start_processing(self):
        """开始处理"""
        if not self.current_files:
            messagebox.showwarning("警告", "请先选择要处理的视频文件")
            return
        
        if self.is_processing:
            messagebox.showwarning("警告", "正在处理中，请等待完成")
            return
        
        # 获取当前选择的功能
        function = self.function_var.get()
        
        # 启动处理线程
        self.is_processing = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        self.processing_thread = threading.Thread(target=self.process_files, args=(function,))
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def stop_processing(self):
        """停止处理"""
        self.is_processing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.log_message("处理已停止")
    
    def process_files(self, function):
        """处理文件的主函数"""
        try:
            if function == 'frame_extract':
                self.process_frame_extract()
            elif function == 'video_split':
                self.process_video_split()
            elif function == 'grid_compose':
                self.process_grid_compose()
            elif function == 'duration_compose':
                self.process_duration_compose()
            elif function == 'audio_mix':
                self.process_audio_mix()
            
            self.log_message("所有处理完成！")
            
        except Exception as e:
            self.log_message(f"处理过程中发生错误: {str(e)}")
            messagebox.showerror("错误", f"处理失败: {str(e)}")
        
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.start_button.config(state='normal'))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))
    
    def process_frame_extract(self):
        """处理视频抽帧"""
        interval = self.frame_interval_var.get()
        format_type = self.frame_format_var.get()
        method = self.frame_method_var.get()
        
        total_files = len(self.current_files)
        
        for i, file_path in enumerate(self.current_files):
            if not self.is_processing:
                break
                
            try:
                self.log_message(f"正在处理: {os.path.basename(file_path)}")
                
                def progress_callback(percent, message):
                    overall_progress = (i / total_files) * 100 + (percent / total_files)
                    self.root.after(0, lambda: self.update_progress(overall_progress, message))
                
                result = self.frame_extractor.extract_frames(
                    file_path,
                    interval=interval,
                    image_format=format_type,
                    method=method,
                    progress_callback=progress_callback
                )
                
                self.log_message(f"完成抽帧: {len(result)} 张图片")
                
            except Exception as e:
                self.log_message(f"抽帧失败 {os.path.basename(file_path)}: {str(e)}")
        
        self.update_progress(100, "抽帧处理完成")
    
    def process_video_split(self):
        """处理视频切割"""
        duration = self.split_duration_var.get()
        overlap = self.split_overlap_var.get()
        total_files = len(self.current_files)
        for i, file_path in enumerate(self.current_files):
            if not self.is_processing:
                break
            try:
                self.log_message(f"正在切割: {os.path.basename(file_path)}")
                def progress_callback(percent, message):
                    overall_progress = (i / total_files) * 100 + (percent / total_files)
                    self.root.after(0, lambda: self.update_progress(overall_progress, message))
                result = self.video_splitter.split_video_ffmpeg(
                    file_path,
                    segment_duration=duration,
                    overlap=overlap,
                    output_dir=None
                )
                self.log_message(f"完成切割: {len(result)} 个片段")
            except Exception as e:
                self.log_message(f"切割失败 {os.path.basename(file_path)}: {str(e)}")
        self.update_progress(100, "视频切割完成")
    
    def process_grid_compose(self):
        """处理宫格组合"""
        layout = self.grid_layout_var.get()
        duration = self.grid_duration_var.get()
        selection = self.grid_selection_var.get()
        
        try:
            self.log_message(f"创建 {layout} 宫格视频...")
            
            def progress_callback(percent, message):
                self.root.after(0, lambda: self.update_progress(percent, message))
            
            result = self.grid_composer.create_grid_video(
                self.current_files,
                layout=layout,
                duration=duration,
                selection_method=selection,
                progress_callback=progress_callback
            )
            
            self.log_message(f"宫格视频创建成功: {os.path.basename(result)}")
            
        except Exception as e:
            self.log_message(f"宫格组合失败: {str(e)}")
    
    def process_duration_compose(self):
        """处理时长组合"""
        target_duration = self.duration_target_var.get()
        strategy = self.duration_strategy_var.get()
        transition = self.duration_transition_var.get()
        
        try:
            self.log_message(f"组合 {target_duration}秒 视频...")
            
            def progress_callback(percent, message):
                self.root.after(0, lambda: self.update_progress(percent, message))
            
            result = self.duration_composer.compose_duration_video(
                self.current_files,
                target_duration=target_duration,
                strategy=strategy,
                transition_type=transition,
                progress_callback=progress_callback
            )
            
            self.log_message(f"时长组合视频创建成功: {os.path.basename(result)}")
            
        except Exception as e:
            self.log_message(f"时长组合失败: {str(e)}")
    
    def process_audio_mix(self):
        """处理音乐配对"""
        music_volume = self.music_volume_var.get()
        video_volume = self.video_volume_var.get()
        fade_in = self.fade_in_var.get()
        fade_out = self.fade_out_var.get()
        
        total_files = len(self.current_files)
        
        for i, file_path in enumerate(self.current_files):
            if not self.is_processing:
                break
            try:
                self.log_message(f"正在配音: {os.path.basename(file_path)}")

                def progress_callback(percent, message):
                    overall_progress = (i / total_files) * 100 + (percent / total_files)
                    self.root.after(0, lambda: self.update_progress(overall_progress, message))

                result = self.audio_mixer.add_music_to_video(
                    file_path,
                    music_volume=music_volume,
                    video_volume=video_volume,
                    fade_in_duration=fade_in,
                    fade_out_duration=fade_out,
                    progress_callback=progress_callback
                )

                self.log_message(f"完成配音: {os.path.basename(result)}")

            except Exception as e:
                self.log_message(f"配音失败 {os.path.basename(file_path)}: {str(e)}")
        
        self.update_progress(100, "音乐配对完成")
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            count = self.file_handler.cleanup_temp_files()
            self.log_message(f"清理了 {count} 个临时文件")
            messagebox.showinfo("完成", f"清理了 {count} 个临时文件")
        except Exception as e:
            messagebox.showerror("错误", f"清理失败: {str(e)}")
    
    def open_output_dir(self):
        """打开输出目录"""
        try:
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                os.startfile(self.settings.OUTPUT_DIR)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", self.settings.OUTPUT_DIR])
            else:  # Linux
                subprocess.run(["xdg-open", self.settings.OUTPUT_DIR])
        except Exception as e:
            messagebox.showerror("错误", f"打开目录失败: {str(e)}")
    
    def analyze_videos(self):
        """分析视频文件"""
        if not self.current_files:
            messagebox.showwarning("警告", "请先选择视频文件")
            return
        
        try:
            self.log_message("开始分析视频文件...")
            results = self.video_utils.batch_analyze_videos(self.current_files)
            
            # 显示分析结果
            analysis_text = f"""
视频分析结果:
总文件数: {results['total']}
有效文件数: {results['valid']}
无效文件数: {results['invalid']}
总时长: {results['total_duration']:.1f}秒
平均时长: {results['avg_duration']:.1f}秒
时长范围: {results['min_duration']:.1f}s - {results['max_duration']:.1f}s
总大小: {self.file_handler.format_file_size(results['total_size'])}

分辨率分布: {results['resolutions']}
格式分布: {results['formats']}
编码器分布: {results['codecs']}
            """
            
            self.log_message(analysis_text)
            messagebox.showinfo("分析结果", analysis_text)
            
        except Exception as e:
            messagebox.showerror("错误", f"分析失败: {str(e)}")
    
    def on_file_double_click(self, event):
        """文件双击事件"""
        selection = self.file_tree.selection()
        if selection:
            item = self.file_tree.item(selection[0])
            file_path = item['text']
            self.log_message(f"双击文件: {os.path.basename(file_path)}")
    
    def show_file_context_menu(self, event):
        """显示文件右键菜单"""
        # 这里可以添加右键菜单功能
        pass
    
    def show_help(self):
        """显示帮助信息（自定义窗口，避免系统 MessageBox 中文显示不清晰）"""
        help_text = (
            "Video Clips - 智能视频剪辑工具\n\n"
            "功能说明:\n"
            "1. 视频抽帧: 从视频中提取静态图片\n"
            "2. 视频切割: 将长视频切割为短片段\n"
            "3. 宫格组合: 将多个视频组合成宫格布局\n"
            "4. 时长组合: 将短片段组合成指定时长的视频\n"
            "5. 音乐配对: 为视频添加背景音乐\n\n"
            "使用方法:\n"
            "1. 选择视频文件或文件夹\n"
            "2. 选择要使用的功能\n"
            "3. 调整相关参数\n"
            "4. 点击“开始处理”\n\n"
            "注意事项:\n"
            "- 确保系统已安装 FFmpeg\n"
            "- 处理大文件时可能需要较长时间\n"
            "- 可在处理中途点击“停止处理”\n"
        )

        win = tk.Toplevel(self.root)
        win.title("使用说明")
        win.geometry("640x460")
        win.transient(self.root)
        win.grab_set()

        # 容器
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # 文本 + 滚动条
        text = tk.Text(frame, wrap=tk.WORD, font=self.default_font, spacing1=2, spacing2=2, spacing3=2)
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.insert(tk.END, help_text)
        text.configure(state='disabled')

        # 底部按钮
        btn_frame = ttk.Frame(win, padding=(10, 0, 10, 10))
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="关闭", command=win.destroy).pack(anchor=tk.E)
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
Video Clips v1.0
智能视频剪辑工具

开发者: AI Assistant
技术栈: Python, tkinter, MoviePy, OpenCV, FFmpeg

© 2024 All Rights Reserved
        """
        
        messagebox.showinfo("关于", about_text)
    
    def on_closing(self):
        """窗口关闭事件"""
        if self.is_processing:
            result = messagebox.askyesno("确认", "正在处理中，确定要退出吗？")
            if not result:
                return
            
            self.is_processing = False
        
        # 清理临时文件
        try:
            self.file_handler.cleanup_temp_files()
        except:
            pass
        
        self.root.destroy()
    
    def show_message(self, title: str, message: str, msg_type: str = "info"):
        """显示自定义字体的消息框"""
        # 创建自定义消息框窗口
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 设置窗口大小和位置
        dialog_width = 400
        dialog_height = 200
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog_width // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog_height // 2)
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 图标和消息
        icon_text = {"info": "[信息]", "warning": "[警告]", "error": "[错误]", "question": "[询问]"}.get(msg_type, "[信息]")
        
        icon_frame = ttk.Frame(main_frame)
        icon_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(icon_frame, text=icon_text, font=self.large_font).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(icon_frame, text=message, font=self.default_font, wraplength=300).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def close_dialog():
            dialog.destroy()
            
        ttk.Button(button_frame, text="确定", command=close_dialog).pack(side=tk.RIGHT)
        
        # 等待对话框关闭
        dialog.wait_window()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    try:
        app = VideoClipsGUI()
        app.run()
    except Exception as e:
        print(f"启动GUI失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()