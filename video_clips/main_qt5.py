"""
Video Clips 主界面（PyQt5 版）
保留所有业务逻辑模块，只迁移 UI 部分
"""
from typing import List, Optional, Dict
import os
import sys
import subprocess
import threading
import traceback
import queue
from queue import Queue

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTableWidget, QTableWidgetItem, QTabWidget, QLabel, QPushButton,
    QSlider, QComboBox, QLineEdit, QCheckBox, QProgressBar, QTextEdit,
    QMenuBar, QMenu, QAction, QSplitter, QHeaderView, QFileDialog, 
    QMessageBox, QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QPalette, QColor

# 暂时注释掉业务逻辑导入，避免冲突
# from config.settings import Settings
# from modules.frame_extractor import FrameExtractor
# from modules.video_splitter import VideoSplitter
# from modules.grid_composer import GridComposer
# from modules.duration_composer import DurationComposer
# from modules.audio_mixer import AudioMixer
# from modules.sliding_strip_composer import SlidingStripComposer
# from utils.video_utils import VideoUtils


class VideoClipsMainWindow(QMainWindow):
    """PyQt5 版主窗口类，保留所有原有业务逻辑"""
    
    def __init__(self):
        super().__init__()
        
        # 暂时简化初始化，避免导入冲突
        # self.settings = Settings()
        # self.settings.ensure_dirs()

        # 收藏集合
        self.favorites = set()

        # 后台任务
        self.worker_thread: Optional[threading.Thread] = None
        self.cancel_flag = threading.Event()
        self._queue: Queue = Queue()

        # 暂时注释掉业务模块初始化
        # self.extractor = FrameExtractor()
        # self.splitter = VideoSplitter()
        # self.gridder = GridComposer()
        # self.dcomposer = DurationComposer()
        # self.mixer = AudioMixer()
        # self.vutils = VideoUtils()
        # self.scomposer = SlidingStripComposer()

        # 文件数据
        self.file_items = []
        self.fav_items = []
        
        # UI 初始化
        self.init_ui()
        
        # 定时器用于处理队列消息
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_queue)
        self.timer.start(100)  # 每100ms检查一次队列
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('🎬 视频剪辑工具（PyQt5 版）✨')
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置淡蓝色主题
        self.setup_light_blue_theme()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板
        self.create_left_panel(splitter)
        
        # 右侧面板
        self.create_right_panel(splitter)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
    
    def setup_light_blue_theme(self):
        """设置淡蓝色主题"""
        # 创建调色板
        palette = QPalette()
        
        # 主要颜色定义
        primary_blue = QColor(240, 248, 255)      # 爱丽丝蓝（Alice Blue）- 主背景
        secondary_blue = QColor(230, 240, 250)    # 浅蓝色 - 次要背景
        accent_blue = QColor(173, 216, 230)       # 浅蓝色 - 强调色
        dark_blue = QColor(70, 130, 180)          # 钢蓝色 - 文字和边框
        selected_blue = QColor(135, 206, 250)     # 天蓝色 - 选中状态
        button_blue = QColor(220, 235, 245)       # 按钮颜色
        
        # 设置窗口背景
        palette.setColor(QPalette.Window, primary_blue)
        palette.setColor(QPalette.WindowText, dark_blue)
        
        # 设置输入框和表格背景
        palette.setColor(QPalette.Base, QColor(255, 255, 255))  # 纯白色
        palette.setColor(QPalette.AlternateBase, secondary_blue)
        
        # 设置按钮
        palette.setColor(QPalette.Button, button_blue)
        palette.setColor(QPalette.ButtonText, dark_blue)
        
        # 设置选中项
        palette.setColor(QPalette.Highlight, selected_blue)
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        
        # 设置文本
        palette.setColor(QPalette.Text, dark_blue)
        palette.setColor(QPalette.BrightText, QColor(0, 0, 0))
        
        # 应用调色板
        self.setPalette(palette)
        
        # 设置全局样式表
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgb(240, 248, 255);
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgb(173, 216, 230);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgb(250, 252, 255);
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: rgb(70, 130, 180);
            }
            
            QPushButton {
                background-color: rgb(220, 235, 245);
                border: 2px solid rgb(173, 216, 230);
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                color: rgb(70, 130, 180);
            }
            
            QPushButton:hover {
                background-color: rgb(200, 225, 240);
                border: 2px solid rgb(135, 206, 250);
            }
            
            QPushButton:pressed {
                background-color: rgb(180, 215, 235);
            }
            
            QTabWidget::pane {
                border: 2px solid rgb(173, 216, 230);
                border-radius: 8px;
                background-color: rgb(250, 252, 255);
            }
            
            QTabBar::tab {
                background-color: rgb(230, 240, 250);
                border: 2px solid rgb(173, 216, 230);
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                padding: 8px 16px;
                margin-right: 2px;
                color: rgb(70, 130, 180);
                font-weight: bold;
            }
            
            QTabBar::tab:selected {
                background-color: rgb(240, 248, 255);
                border-bottom: 2px solid rgb(240, 248, 255);
            }
            
            QTabBar::tab:hover {
                background-color: rgb(220, 235, 245);
            }
            
            QTableWidget {
                background-color: white;
                border: 2px solid rgb(173, 216, 230);
                border-radius: 6px;
                gridline-color: rgb(200, 225, 240);
                selection-background-color: rgb(135, 206, 250);
            }
            
            QHeaderView::section {
                background-color: rgb(230, 240, 250);
                padding: 8px;
                border: 1px solid rgb(173, 216, 230);
                font-weight: bold;
                color: rgb(70, 130, 180);
            }
            
            QLineEdit {
                border: 2px solid rgb(173, 216, 230);
                border-radius: 4px;
                padding: 6px;
                background-color: white;
                color: rgb(70, 130, 180);
            }
            
            QLineEdit:focus {
                border: 2px solid rgb(135, 206, 250);
            }
            
            QComboBox {
                border: 2px solid rgb(173, 216, 230);
                border-radius: 4px;
                padding: 6px;
                background-color: white;
                color: rgb(70, 130, 180);
            }
            
            QComboBox:focus {
                border: 2px solid rgb(135, 206, 250);
            }
            
            QComboBox::drop-down {
                border: none;
                background-color: rgb(220, 235, 245);
                border-radius: 4px;
            }
            
            QSlider::groove:horizontal {
                border: 2px solid rgb(173, 216, 230);
                height: 8px;
                background-color: rgb(230, 240, 250);
                border-radius: 4px;
            }
            
            QSlider::handle:horizontal {
                background-color: rgb(135, 206, 250);
                border: 2px solid rgb(70, 130, 180);
                width: 20px;
                margin: -8px 0;
                border-radius: 10px;
            }
            
            QSlider::handle:horizontal:hover {
                background-color: rgb(100, 180, 220);
            }
            
            QProgressBar {
                border: 2px solid rgb(173, 216, 230);
                border-radius: 6px;
                text-align: center;
                background-color: rgb(230, 240, 250);
                color: rgb(70, 130, 180);
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background-color: rgb(135, 206, 250);
                border-radius: 4px;
            }
            
            QTextEdit {
                border: 2px solid rgb(173, 216, 230);
                border-radius: 6px;
                background-color: white;
                color: rgb(70, 130, 180);
                font-family: 'Consolas', 'Monaco', monospace;
            }
            
            QCheckBox {
                color: rgb(70, 130, 180);
                font-weight: bold;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgb(173, 216, 230);
                border-radius: 4px;
                background-color: white;
            }
            
            QCheckBox::indicator:checked {
                background-color: rgb(135, 206, 250);
                border: 2px solid rgb(70, 130, 180);
            }
            
            QLabel {
                color: rgb(70, 130, 180);
                font-weight: bold;
            }
            
            QMenuBar {
                background-color: rgb(230, 240, 250);
                border-bottom: 2px solid rgb(173, 216, 230);
            }
            
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 16px;
                color: rgb(70, 130, 180);
                font-weight: bold;
            }
            
            QMenuBar::item:selected {
                background-color: rgb(200, 225, 240);
                border-radius: 4px;
            }
            
            QMenu {
                background-color: rgb(245, 250, 255);
                border: 2px solid rgb(173, 216, 230);
                border-radius: 6px;
            }
            
            QMenu::item {
                padding: 8px 24px;
                color: rgb(70, 130, 180);
            }
            
            QMenu::item:selected {
                background-color: rgb(200, 225, 240);
                border-radius: 4px;
            }
            
            QSplitter::handle {
                background-color: rgb(173, 216, 230);
                border: 1px solid rgb(135, 206, 250);
            }
            
            QSplitter::handle:hover {
                background-color: rgb(135, 206, 250);
            }
        """)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('📁 文件')
        
        select_files_action = QAction('📽️ 选择视频文件', self)
        select_files_action.triggered.connect(self.select_video_files)
        file_menu.addAction(select_files_action)
        
        select_folder_action = QAction('📂 选择文件夹', self)
        select_folder_action.triggered.connect(self.select_folder)
        file_menu.addAction(select_folder_action)
        
        file_menu.addSeparator()
        
        clear_files_action = QAction('🗑️ 清空文件列表', self)
        clear_files_action.triggered.connect(self.clear_files)
        file_menu.addAction(clear_files_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('🚪 退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('🔧 工具')
        
        cleanup_action = QAction('🧹 清理临时文件', self)
        cleanup_action.triggered.connect(self.cleanup_temp)
        tools_menu.addAction(cleanup_action)
        
        open_output_action = QAction('📤 打开输出目录', self)
        open_output_action.triggered.connect(self.open_output_dir)
        tools_menu.addAction(open_output_action)
        
        video_info_action = QAction('📊 视频信息分析', self)
        video_info_action.triggered.connect(self.show_video_info)
        tools_menu.addAction(video_info_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('❓ 帮助')
        
        usage_action = QAction('📖 使用说明', self)
        usage_action.triggered.connect(self.show_usage)
        help_menu.addAction(usage_action)
        
        about_action = QAction('ℹ️ 关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_left_panel(self, parent):
        """创建左侧文件列表面板"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 文件操作按钮
        button_layout = QHBoxLayout()
        
        self.add_files_btn = QPushButton('📽️ 添加文件')
        self.add_files_btn.clicked.connect(self.select_video_files)
        button_layout.addWidget(self.add_files_btn)
        
        self.add_folder_btn = QPushButton('📂 添加文件夹')
        self.add_folder_btn.clicked.connect(self.select_folder)
        button_layout.addWidget(self.add_folder_btn)
        
        self.delete_btn = QPushButton('❌ 删除')
        self.delete_btn.clicked.connect(self.delete_selected_files)
        button_layout.addWidget(self.delete_btn)
        
        self.clear_btn = QPushButton('🗑️ 清空')
        self.clear_btn.clicked.connect(self.clear_files)
        button_layout.addWidget(self.clear_btn)
        
        left_layout.addLayout(button_layout)
        
        # 文件列表表格
        file_group = QGroupBox('📁 文件列表')
        file_layout = QVBoxLayout(file_group)
        
        self.file_table = QTableWidget(0, 5)
        self.file_table.setHorizontalHeaderLabels(['📄 文件名', '⏱️ 时长', '💾 大小', '📐 分辨率', '🎞️ 格式'])
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        file_layout.addWidget(self.file_table)
        
        left_layout.addWidget(file_group)
        
        # 收藏操作按钮
        fav_button_layout = QHBoxLayout()
        
        self.fav_add_btn = QPushButton('⭐ 添加到收藏')
        self.fav_add_btn.clicked.connect(self.add_to_favorites)
        fav_button_layout.addWidget(self.fav_add_btn)
        
        self.fav_del_btn = QPushButton('💔 从收藏移除')
        self.fav_del_btn.clicked.connect(self.remove_from_favorites)
        fav_button_layout.addWidget(self.fav_del_btn)
        
        left_layout.addLayout(fav_button_layout)
        
        # 收藏列表表格
        fav_group = QGroupBox('💖 收藏列表')
        fav_layout = QVBoxLayout(fav_group)
        
        self.fav_table = QTableWidget(0, 5)
        self.fav_table.setHorizontalHeaderLabels(['📄 文件名', '⏱️ 时长', '💾 大小', '📐 分辨率', '🎞️ 格式'])
        self.fav_table.horizontalHeader().setStretchLastSection(True)
        self.fav_table.setSelectionBehavior(QTableWidget.SelectRows)
        fav_layout.addWidget(self.fav_table)
        
        left_layout.addWidget(fav_group)
        
        parent.addWidget(left_widget)
    
    # 保持所有原有的辅助方法不变
    def _format_seconds(self, sec: float) -> str:
        """格式化秒数为时间字符串 - 保持原逻辑不变"""
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
        """收集文件信息 - 保持原逻辑不变"""
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
        """格式化文件大小 - 保持原逻辑不变"""
        if size_bytes <= 0:
            return '0 B'
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        size = float(size_bytes)
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        return f"{size:.1f} {units[i]}"
    
    def refresh_file_table(self):
        """刷新文件列表表格"""
        self.file_table.setRowCount(len(self.file_items))
        for i, item in enumerate(self.file_items):
            self.file_table.setItem(i, 0, QTableWidgetItem(item['name']))
            self.file_table.setItem(i, 1, QTableWidgetItem(item['duration_str']))
            self.file_table.setItem(i, 2, QTableWidgetItem(item['size_str']))
            self.file_table.setItem(i, 3, QTableWidgetItem(item['resolution']))
            self.file_table.setItem(i, 4, QTableWidgetItem(item['format']))
    
    def refresh_fav_table(self):
        """刷新收藏列表表格"""
        self.fav_table.setRowCount(len(self.fav_items))
        for i, item in enumerate(self.fav_items):
            self.fav_table.setItem(i, 0, QTableWidgetItem(item['name']))
            self.fav_table.setItem(i, 1, QTableWidgetItem(item['duration_str']))
            self.fav_table.setItem(i, 2, QTableWidgetItem(item['size_str']))
            self.fav_table.setItem(i, 3, QTableWidgetItem(item['resolution']))
            self.fav_table.setItem(i, 4, QTableWidgetItem(item['format']))
    
    def _gather_info(self, path: str) -> Dict:
        """收集文件信息 - 简化版本"""
        name = os.path.basename(path)
        try:
            size = os.path.getsize(path) if os.path.exists(path) else 0
        except:
            size = 0
        size_str = self._format_file_size(size)
        
        # 简化版本，不依赖 VideoUtils
        return {
            'path': path,
            'name': name,
            'size': size,
            'size_str': size_str,
            'duration_s': 0.0,
            'duration_str': '--:--',
            'resolution': '-',
            'format': os.path.splitext(name)[1].lstrip('.').lower() or '-',
        }
    
    # 菜单和按钮事件处理
    def select_video_files(self):
        """选择视频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            '选择视频文件', 
            '', 
            'Video Files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v);;All Files (*)'
        )
        
        for file_path in files:
            if file_path and file_path not in [item['path'] for item in self.file_items]:
                info = self._gather_info(file_path)
                self.file_items.append(info)
        
        self.refresh_file_table()
    
    def select_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, '选择文件夹')
        if folder:
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if os.path.splitext(file)[1].lower() in video_extensions:
                        file_path = os.path.join(root, file)
                        if file_path not in [item['path'] for item in self.file_items]:
                            info = self._gather_info(file_path)
                            self.file_items.append(info)
            
            self.refresh_file_table()
    
    def delete_selected_files(self):
        """删除选中的文件"""
        selected_rows = []
        for item in self.file_table.selectedItems():
            row = item.row()
            if row not in selected_rows:
                selected_rows.append(row)
        
        # 从大到小删除，避免索引变化
        for row in sorted(selected_rows, reverse=True):
            if 0 <= row < len(self.file_items):
                removed_item = self.file_items.pop(row)
                # 如果在收藏中，也要移除
                self.favorites.discard(removed_item['path'])
        
        self.refresh_file_table()
        self._update_fav_items()
        self.refresh_fav_table()
    
    def clear_files(self):
        """清空文件列表"""
        reply = QMessageBox.question(
            self, 
            '确认', 
            '确定要清空所有文件列表吗？', 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.file_items.clear()
            self.fav_items.clear()
            self.favorites.clear()
            self.refresh_file_table()
            self.refresh_fav_table()
    
    def add_to_favorites(self):
        """添加到收藏"""
        selected_rows = []
        for item in self.file_table.selectedItems():
            row = item.row()
            if row not in selected_rows:
                selected_rows.append(row)
        
        for row in selected_rows:
            if 0 <= row < len(self.file_items):
                file_item = self.file_items[row]
                self.favorites.add(file_item['path'])
        
        self._update_fav_items()
        self.refresh_fav_table()
    
    def remove_from_favorites(self):
        """从收藏中移除"""
        selected_rows = []
        for item in self.fav_table.selectedItems():
            row = item.row()
            if row not in selected_rows:
                selected_rows.append(row)
        
        for row in selected_rows:
            if 0 <= row < len(self.fav_items):
                fav_item = self.fav_items[row]
                self.favorites.discard(fav_item['path'])
        
        self._update_fav_items()
        self.refresh_fav_table()
    
    def _update_fav_items(self):
        """更新收藏列表数据"""
        self.fav_items = [item for item in self.file_items if item['path'] in self.favorites]
    
    def process_queue(self):
        """处理队列消息（占位）"""
        try:
            while not self._queue.empty():
                msg_type, data = self._queue.get_nowait()
                # 这里可以处理进度更新等消息
                pass
        except queue.Empty:
            pass
    
    # 菜单事件处理（简化版本）
    def cleanup_temp(self):
        """清理临时文件"""
        QMessageBox.information(self, '🧹 清理临时文件', '临时文件清理功能待实现 🚧')
    
    def open_output_dir(self):
        """打开输出目录"""
        QMessageBox.information(self, '📤 打开输出目录', '打开输出目录功能待实现 🚧')
    
    def show_video_info(self):
        """显示视频信息"""
        QMessageBox.information(self, '📊 视频信息分析', '视频信息分析功能待实现 🚧')
    
    def show_usage(self):
        """显示使用说明"""
        QMessageBox.information(
            self, 
            '📖 使用说明', 
            '🎬 视频剪辑工具 PyQt5 版 ✨\n\n'
            '📽️ 1. 使用"添加文件"或"添加文件夹"导入视频\n'
            '⭐ 2. 选择视频后可添加到收藏列表\n'
            '🔧 3. 使用右侧选项卡进行各种剪辑操作\n\n'
            '💡 注意：这是从 PySimpleGUIQt 迁移的版本'
        )
    
    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(
            self,
            'ℹ️ 关于',
            '🎬 视频剪辑工具 PyQt5 版 ✨\n\n'
            '🔧 从 PySimpleGUIQt 迁移而来\n'
            '🎯 保留所有业务逻辑，只更换 UI 框架\n\n'
            '🐍 PyQt5 版本 🚀'
        )
    
    # 选项卡相关的事件处理方法
    def update_extract_interval_label(self, value):
        """更新抽帧间隔标签"""
        self.extract_interval_label.setText(f'{value} 秒')
    
    def update_split_duration_label(self, value):
        """更新切割时长标签"""
        self.split_duration_label.setText(f'{value} 秒')
    
    def browse_extract_output(self):
        """浏览抽帧输出目录"""
        folder = QFileDialog.getExistingDirectory(self, '📁 选择抽帧输出目录')
        if folder:
            self.extract_output.setText(folder)
    
    def browse_split_output(self):
        """浏览切割输出目录"""
        folder = QFileDialog.getExistingDirectory(self, '📁 选择切割输出目录')
        if folder:
            self.split_output.setText(folder)
    
    def browse_grid_output(self):
        """浏览宫格输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, '💾 选择宫格输出文件', '', 'Video Files (*.mp4 *.avi *.mov);;All Files (*)'
        )
        if file_path:
            self.grid_output.setText(file_path)
    
    def browse_duration_output(self):
        """浏览时长合成输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, '💾 选择时长合成输出文件', '', 'Video Files (*.mp4 *.avi *.mov);;All Files (*)'
        )
        if file_path:
            self.duration_output.setText(file_path)
    
    def browse_music_file(self):
        """浏览音乐文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '🎵 选择音乐文件', '', 'Audio Files (*.mp3 *.wav *.aac *.flac);;All Files (*)'
        )
        if file_path:
            self.audio_music_file.setText(file_path)
    
    def browse_sliding_output(self):
        """浏览滑动合成输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, '💾 选择滑动合成输出文件', '', 'Video Files (*.mp4 *.avi *.mov);;All Files (*)'
        )
        if file_path:
            self.sliding_output.setText(file_path)
    
    # 任务执行方法（占位实现）
    def run_extract(self):
        """运行抽帧任务"""
        selected_files = self.get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, '⚠️ 警告', '请先选择视频文件 📽️')
            return
        
        self.log_message(f'🚀 开始抽帧任务，共 {len(selected_files)} 个文件')
        self.log_message('💡 注意：业务逻辑尚未连接，这只是 UI 演示')
        
        # TODO: 连接到实际的 FrameExtractor
    
    def run_split(self):
        """运行切割任务"""
        selected_files = self.get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, '⚠️ 警告', '请先选择视频文件 📽️')
            return
        
        self.log_message(f'✂️ 开始切割任务，共 {len(selected_files)} 个文件')
        self.log_message('💡 注意：业务逻辑尚未连接，这只是 UI 演示')
        
        # TODO: 连接到实际的 VideoSplitter
    
    def run_grid(self):
        """运行宫格合成任务"""
        selected_files = self.get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, '⚠️ 警告', '请先选择视频文件 📽️')
            return
        
        self.log_message(f'🔲 开始宫格合成任务，共 {len(selected_files)} 个文件')
        self.log_message('💡 注意：业务逻辑尚未连接，这只是 UI 演示')
        
        # TODO: 连接到实际的 GridComposer
    
    def run_duration(self):
        """运行时长合成任务"""
        selected_files = self.get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, '⚠️ 警告', '请先选择视频文件 📽️')
            return
        
        self.log_message(f'⏰ 开始时长合成任务，共 {len(selected_files)} 个文件')
        self.log_message('💡 注意：业务逻辑尚未连接，这只是 UI 演示')
        
        # TODO: 连接到实际的 DurationComposer
    
    def run_audio(self):
        """运行配音任务"""
        selected_files = self.get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, '⚠️ 警告', '请先选择视频文件 📽️')
            return
        
        self.log_message(f'🎤 开始配音任务，共 {len(selected_files)} 个文件')
        self.log_message('💡 注意：业务逻辑尚未连接，这只是 UI 演示')
        
        # TODO: 连接到实际的 AudioMixer
    
    def run_sliding(self):
        """运行滑动合成任务"""
        selected_files = self.get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, '⚠️ 警告', '请先选择视频文件 📽️')
            return
        
        self.log_message(f'🏃 开始滑动合成任务，共 {len(selected_files)} 个文件')
        self.log_message('💡 注意：业务逻辑尚未连接，这只是 UI 演示')
        
        # TODO: 连接到实际的 SlidingStripComposer
    
    def stop_task(self):
        """停止当前任务"""
        self.cancel_flag.set()
        self.log_message('🛑 用户请求停止任务')
    
    def get_selected_files(self):
        """获取选中的文件路径列表"""
        # 优先从文件列表获取选中项
        selected_rows = []
        for item in self.file_table.selectedItems():
            row = item.row()
            if row not in selected_rows:
                selected_rows.append(row)
        
        if selected_rows:
            return [self.file_items[row]['path'] for row in selected_rows if 0 <= row < len(self.file_items)]
        
        # 如果文件列表没有选中，尝试收藏列表
        selected_rows = []
        for item in self.fav_table.selectedItems():
            row = item.row()
            if row not in selected_rows:
                selected_rows.append(row)
        
        if selected_rows:
            return [self.fav_items[row]['path'] for row in selected_rows if 0 <= row < len(self.fav_items)]
        
        # 如果都没有选中，返回所有文件
        return [item['path'] for item in self.file_items]
    
    def log_message(self, message):
        """添加日志消息"""
        self.log_text.append(f'📝 [{threading.current_thread().name}] {message}')
    
    def create_right_panel(self, parent):
        """创建右侧任务面板"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        
        # 创建各个选项卡
        self.create_extract_tab()
        self.create_split_tab()
        self.create_grid_tab()
        self.create_duration_tab()
        self.create_audio_tab()
        self.create_sliding_tab()
        
        right_layout.addWidget(self.tab_widget)
        
        # 进度条和控制按钮
        control_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        control_layout.addWidget(self.progress_bar)
        
        self.stop_btn = QPushButton('🛑 停止')
        self.stop_btn.clicked.connect(self.stop_task)
        control_layout.addWidget(self.stop_btn)
        
        right_layout.addLayout(control_layout)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)
        
        parent.addWidget(right_widget)
    
    def create_extract_tab(self):
        """创建抽帧选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 抽帧间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel('⏱️ 抽帧间隔(秒):'))
        self.extract_interval_slider = QSlider(Qt.Horizontal)
        self.extract_interval_slider.setRange(1, 20)
        self.extract_interval_slider.setValue(5)
        self.extract_interval_slider.valueChanged.connect(self.update_extract_interval_label)
        interval_layout.addWidget(self.extract_interval_slider)
        self.extract_interval_label = QLabel('5 秒')
        interval_layout.addWidget(self.extract_interval_label)
        layout.addLayout(interval_layout)
        
        # 图片格式和方法
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel('🖼️ 图片格式:'))
        self.extract_format = QComboBox()
        self.extract_format.addItems(['png', 'jpg'])
        format_layout.addWidget(self.extract_format)
        
        format_layout.addWidget(QLabel('⚙️ 方法:'))
        self.extract_method = QComboBox()
        self.extract_method.addItems(['auto', 'ffmpeg', 'moviepy', 'cv2'])
        self.extract_method.setCurrentText('ffmpeg')
        format_layout.addWidget(self.extract_method)
        layout.addLayout(format_layout)
        
        # 输出目录
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('📤 输出目录:'))
        self.extract_output = QLineEdit('output/frames')
        output_layout.addWidget(self.extract_output)
        extract_browse = QPushButton('📁 选择')
        extract_browse.clicked.connect(self.browse_extract_output)
        output_layout.addWidget(extract_browse)
        layout.addLayout(output_layout)
        
        # 开始按钮
        self.extract_btn = QPushButton('🚀 开始抽帧')
        self.extract_btn.clicked.connect(self.run_extract)
        layout.addWidget(self.extract_btn)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, '📸 抽帧')
    
    def create_split_tab(self):
        """创建切割选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 每段时长
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel('⏰ 每段时长(秒):'))
        self.split_duration_slider = QSlider(Qt.Horizontal)
        self.split_duration_slider.setRange(3, 60)
        self.split_duration_slider.setValue(10)
        self.split_duration_slider.valueChanged.connect(self.update_split_duration_label)
        duration_layout.addWidget(self.split_duration_slider)
        self.split_duration_label = QLabel('10 秒')
        duration_layout.addWidget(self.split_duration_label)
        layout.addLayout(duration_layout)
        
        # 方法和重叠
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel('⚙️ 方法:'))
        self.split_method = QComboBox()
        self.split_method.addItems(['equal', 'random'])
        method_layout.addWidget(self.split_method)
        
        method_layout.addWidget(QLabel('🔄 重叠(秒):'))
        self.split_overlap = QLineEdit('0.0')
        self.split_overlap.setMaximumWidth(60)
        method_layout.addWidget(self.split_overlap)
        layout.addLayout(method_layout)
        
        # 随机参数
        random_layout = QHBoxLayout()
        random_layout.addWidget(QLabel('🎲 随机: 数量'))
        self.split_random_count = QLineEdit('8')
        self.split_random_count.setMaximumWidth(60)
        random_layout.addWidget(self.split_random_count)
        
        random_layout.addWidget(QLabel('⬇️ 最小秒'))
        self.split_random_min = QLineEdit('5')
        self.split_random_min.setMaximumWidth(60)
        random_layout.addWidget(self.split_random_min)
        
        random_layout.addWidget(QLabel('⬆️ 最大秒'))
        self.split_random_max = QLineEdit('10')
        self.split_random_max.setMaximumWidth(60)
        random_layout.addWidget(self.split_random_max)
        layout.addLayout(random_layout)
        
        # 输出目录
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('📤 输出目录:'))
        self.split_output = QLineEdit('output/segments')
        output_layout.addWidget(self.split_output)
        split_browse = QPushButton('📁 选择')
        split_browse.clicked.connect(self.browse_split_output)
        output_layout.addWidget(split_browse)
        layout.addLayout(output_layout)
        
        # 开始按钮
        self.split_btn = QPushButton('✂️ 开始切割')
        self.split_btn.clicked.connect(self.run_split)
        layout.addWidget(self.split_btn)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, '✂️ 切割')
    
    def create_grid_tab(self):
        """创建宫格选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 布局和方法
        layout_row = QHBoxLayout()
        layout_row.addWidget(QLabel('📐 布局:'))
        self.grid_layout = QComboBox()
        self.grid_layout.addItems(['1×1', '1×2', '2×1', '2×2', '3×3', '4×4'])
        self.grid_layout.setCurrentText('2×2')
        layout_row.addWidget(self.grid_layout)
        
        layout_row.addWidget(QLabel('⚙️ 方法:'))
        self.grid_method = QComboBox()
        self.grid_method.addItems(['moviepy', 'ffmpeg'])
        layout_row.addWidget(self.grid_method)
        layout.addLayout(layout_row)
        
        # 目标时长和同步
        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel('⏰ 目标时长(秒，可留空):'))
        self.grid_duration = QLineEdit()
        self.grid_duration.setMaximumWidth(100)
        duration_row.addWidget(self.grid_duration)
        
        self.grid_sync = QCheckBox('🔄 同步裁剪到最短')
        self.grid_sync.setChecked(True)
        duration_row.addWidget(self.grid_sync)
        layout.addLayout(duration_row)
        
        # 输出尺寸
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel('📏 输出尺寸(WxH):'))
        self.grid_size = QLineEdit('1920x1080')
        size_row.addWidget(self.grid_size)
        layout.addLayout(size_row)
        
        # 输出文件
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('💾 输出文件:'))
        self.grid_output = QLineEdit('output/grid_videos/grid_2x2.mp4')
        output_layout.addWidget(self.grid_output)
        grid_browse = QPushButton('📁 选择')
        grid_browse.clicked.connect(self.browse_grid_output)
        output_layout.addWidget(grid_browse)
        layout.addLayout(output_layout)
        
        # 开始按钮
        self.grid_btn = QPushButton('🔲 创建宫格视频')
        self.grid_btn.clicked.connect(self.run_grid)
        layout.addWidget(self.grid_btn)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, '🔲 宫格')
    
    def create_duration_tab(self):
        """创建时长选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 目标时长
        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel('⏰ 目标时长(秒):'))
        self.duration_target = QComboBox()
        self.duration_target.addItems(['10', '15', '20', '30', '60'])
        self.duration_target.setCurrentText('15')
        self.duration_target.setEditable(True)
        duration_row.addWidget(self.duration_target)
        layout.addLayout(duration_row)
        
        # 选择策略
        strategy_row = QHBoxLayout()
        strategy_row.addWidget(QLabel('🎯 选择策略:'))
        self.duration_strategy = QComboBox()
        self.duration_strategy.addItems(['random', 'balanced', 'shortest', 'longest'])
        strategy_row.addWidget(self.duration_strategy)
        layout.addLayout(strategy_row)
        
        # 转场设置
        transition_row = QHBoxLayout()
        transition_row.addWidget(QLabel('🌈 转场类型:'))
        self.duration_transition = QComboBox()
        self.duration_transition.addItems(['crossfade', 'fade', 'cut'])
        transition_row.addWidget(self.duration_transition)
        
        transition_row.addWidget(QLabel('⚡ 转场秒:'))
        self.duration_transition_sec = QLineEdit('0.5')
        self.duration_transition_sec.setMaximumWidth(60)
        transition_row.addWidget(self.duration_transition_sec)
        
        self.duration_exact = QCheckBox('🎯 精确裁剪')
        self.duration_exact.setChecked(True)
        transition_row.addWidget(self.duration_exact)
        layout.addLayout(transition_row)
        
        # 输出文件
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('💾 输出文件:'))
        self.duration_output = QLineEdit('output/duration_videos/composed_15s.mp4')
        output_layout.addWidget(self.duration_output)
        duration_browse = QPushButton('📁 选择')
        duration_browse.clicked.connect(self.browse_duration_output)
        output_layout.addWidget(duration_browse)
        layout.addLayout(output_layout)
        
        # 开始按钮
        self.duration_btn = QPushButton('🎵 开始组合')
        self.duration_btn.clicked.connect(self.run_duration)
        layout.addWidget(self.duration_btn)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, '⏰ 时长')
    
    def create_audio_tab(self):
        """创建配音选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 方法
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel('⚙️ 方法:'))
        self.audio_method = QComboBox()
        self.audio_method.addItems(['moviepy', 'ffmpeg'])
        method_row.addWidget(self.audio_method)
        layout.addLayout(method_row)
        
        # 音量设置
        volume_row1 = QHBoxLayout()
        volume_row1.addWidget(QLabel('🎵 音乐音量:'))
        self.audio_music_vol = QLineEdit('0.3')
        self.audio_music_vol.setMaximumWidth(60)
        volume_row1.addWidget(self.audio_music_vol)
        
        volume_row1.addWidget(QLabel('📽️ 视频音量:'))
        self.audio_video_vol = QLineEdit('0.7')
        self.audio_video_vol.setMaximumWidth(60)
        volume_row1.addWidget(self.audio_video_vol)
        layout.addLayout(volume_row1)
        
        # 淡入淡出设置
        fade_row = QHBoxLayout()
        fade_row.addWidget(QLabel('🌅 淡入(秒):'))
        self.audio_fade_in = QLineEdit('1.0')
        self.audio_fade_in.setMaximumWidth(60)
        fade_row.addWidget(self.audio_fade_in)
        
        fade_row.addWidget(QLabel('🌇 淡出(秒):'))
        self.audio_fade_out = QLineEdit('1.0')
        self.audio_fade_out.setMaximumWidth(60)
        fade_row.addWidget(self.audio_fade_out)
        
        fade_row.addWidget(QLabel('⏩ 音乐偏移(秒):'))
        self.audio_offset = QLineEdit('0')
        self.audio_offset.setMaximumWidth(60)
        fade_row.addWidget(self.audio_offset)
        layout.addLayout(fade_row)
        
        # 音乐文件
        music_layout = QHBoxLayout()
        music_layout.addWidget(QLabel('🎼 音乐文件(可选):'))
        self.audio_music_file = QLineEdit()
        music_layout.addWidget(self.audio_music_file)
        music_browse = QPushButton('🎵 选择')
        music_browse.clicked.connect(self.browse_music_file)
        music_layout.addWidget(music_browse)
        layout.addLayout(music_layout)
        
        # 批量处理选项
        self.audio_batch = QCheckBox('🔄 对每个选择视频批量处理')
        self.audio_batch.setChecked(True)
        layout.addWidget(self.audio_batch)
        
        # 开始按钮
        self.audio_btn = QPushButton('🎤 开始配音')
        self.audio_btn.clicked.connect(self.run_audio)
        layout.addWidget(self.audio_btn)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, '🎤 配音')
    
    def create_sliding_tab(self):
        """创建1x3滑动选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 输出尺寸
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel('📏 输出尺寸(WxH):'))
        self.sliding_size = QLineEdit('1920x1080')
        size_row.addWidget(self.sliding_size)
        layout.addLayout(size_row)
        
        # 转场时间
        delta_row = QHBoxLayout()
        delta_row.addWidget(QLabel('⚡ 转场Δt(秒):'))
        self.sliding_delta = QLineEdit('0.4')
        self.sliding_delta.setMaximumWidth(60)
        delta_row.addWidget(self.sliding_delta)
        layout.addLayout(delta_row)
        
        # 输出文件
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('💾 输出文件:'))
        self.sliding_output = QLineEdit('output/sliding_1x3.mp4')
        output_layout.addWidget(self.sliding_output)
        sliding_browse = QPushButton('📁 选择')
        sliding_browse.clicked.connect(self.browse_sliding_output)
        output_layout.addWidget(sliding_browse)
        layout.addLayout(output_layout)
        
        # 开始按钮
        self.sliding_btn = QPushButton('🏃 开始滑动合成')
        self.sliding_btn.clicked.connect(self.run_sliding)
        layout.addWidget(self.sliding_btn)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, '🏃 1x3滑动')


class QtVideoClipsApp:
    """应用程序类，保持接口兼容"""
    
    def __init__(self):
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        self.window = VideoClipsMainWindow()
    
    def run(self):
        """运行应用程序"""
        self.window.show()
        return self.app.exec_()


if __name__ == '__main__':
    app = QtVideoClipsApp()
    sys.exit(app.run())