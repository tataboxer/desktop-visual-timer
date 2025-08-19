import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
import os

class AlarmPopup:
    """闹钟弹窗类，用于显示闹钟提醒"""
    
    def __init__(self, alarm_data, cancel_callback=None, settings_manager=None):
        self.alarm_data = alarm_data
        self.cancel_callback = cancel_callback
        self.settings_manager = settings_manager
        self.window = None
        self.is_closed = False
        
        # 颜色配置 - 温和的蓝色主题
        self.colors = {
            'bg_primary': '#F0F8FF',       # 淡蓝色背景，温和不刺眼
            'bg_secondary': '#FFFFFF',     # 白色背景
            'text_primary': '#2C3E50',     # 深蓝灰色文字
            'text_secondary': '#5A6C7D',   # 中等蓝灰色文字
            'button_bg': '#3498DB',        # 蓝色按钮背景
            'button_hover': '#2980B9',     # 按钮悬停
            'accent': '#E74C3C',           # 红色强调色（用于关闭按钮）
            'shadow': '#00000020'          # 阴影
        }
    
    def show(self):
        """显示弹窗"""
        # 检查设置中是否启用了通知
        if self.settings_manager:
            notifications_enabled = self.settings_manager.get("notifications.enabled", True)
            if not notifications_enabled:
                print(f"Alarm popup disabled by settings: {self.alarm_data.get('name', 'Unknown')}")
                return
        
        if self.window is not None:
            return  # 已经显示了
            
        self.window = tk.Toplevel()
        self._setup_window()
        self._create_widgets()
        self._center_window()
        
        # 设置窗口属性
        # self.window.attributes('-topmost', True)  # 不再强制置顶
        self.window.focus_force()  # 强制获取焦点
        # self.window.grab_set()  # 不再设置为模态窗口，允许与其他窗口交互
        
        # 播放系统提示音
        self._play_alarm_sound()
        
        # 不再使用闪烁效果，改为静态显示
        
        # 自动关闭定时器（30秒后自动关闭）
        self.window.after(30000, self._auto_close)
    
    def _setup_window(self):
        """设置窗口基本属性"""
        self.window.title("⏰ 闹钟提醒")
        self.window.geometry("480x220")  # 调整为更紧凑的尺寸
        self.window.configure(bg=self.colors['bg_primary'])
        self.window.resizable(False, False)
        
        # 移除窗口装饰（可选，让窗口更现代）
        # self.window.overrideredirect(True)
        
        # 处理窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_widgets(self):
        """创建窗口组件"""
        # 主容器
        main_frame = tk.Frame(self.window, bg=self.colors['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 内容容器 - 左右布局
        content_frame = tk.Frame(main_frame, bg=self.colors['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧图标区域
        left_frame = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        left_frame.pack(side=tk.LEFT, padx=(0, 20), fill=tk.Y)
        
        # 尝试加载notification.png图标
        try:
            from PIL import Image, ImageTk
            icon_path = os.path.join("assets", "notification.png")
            if os.path.exists(icon_path):
                # 加载并调整图标大小 - 放大到128x128像素
                original_image = Image.open(icon_path)
                resized_image = original_image.resize((280, 180), Image.Resampling.LANCZOS)
                self.icon_photo = ImageTk.PhotoImage(resized_image)
                
                icon_label = tk.Label(left_frame, image=self.icon_photo,
                                     bg=self.colors['bg_primary'])
                icon_label.pack(pady=(5, 0))
                print(f"Loaded notification icon: {icon_path}")
            else:
                # 回退到emoji图标
                icon_label = tk.Label(left_frame, text="⏰", 
                                     font=('Segoe UI', 80),  # 进一步放大emoji
                                     fg=self.colors['text_primary'], 
                                     bg=self.colors['bg_primary'])
                icon_label.pack(pady=(5, 0))
                print(f"Icon file not found, using emoji: {icon_path}")
        except Exception as e:
            # 回退到emoji图标
            icon_label = tk.Label(left_frame, text="⏰", 
                                 font=('Segoe UI', 80),  # 进一步放大emoji
                                 fg=self.colors['text_primary'], 
                                 bg=self.colors['bg_primary'])
            icon_label.pack(pady=(5, 0))
            print(f"Failed to load icon, using emoji: {e}")
        
        # 右侧文字区域
        right_frame = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 闹钟类型标题
        alarm_type = self.alarm_data.get('type', 'alarm')
        if alarm_type == 'countdown':
            title_text = "计时器结束！"
        else:
            title_text = "闹钟时间到！"
            
        title_label = tk.Label(right_frame, text=title_text,
                              font=('Segoe UI', 18, 'bold'),
                              fg=self.colors['text_primary'],
                              bg=self.colors['bg_primary'],
                              anchor='w')
        title_label.pack(fill=tk.X, pady=(5, 8))
        
        # 闹钟名称
        alarm_name = self.alarm_data.get('name', '未命名闹钟')
        name_label = tk.Label(right_frame, text=alarm_name,
                             font=('Segoe UI', 14),
                             fg=self.colors['text_secondary'],
                             bg=self.colors['bg_primary'],
                             anchor='w')
        name_label.pack(fill=tk.X, pady=(0, 8))
        
        # 当前时间
        current_time = datetime.now().strftime("%H:%M:%S")
        time_label = tk.Label(right_frame, text=f"当前时间: {current_time}",
                             font=('Segoe UI', 11),
                             fg=self.colors['text_secondary'],
                             bg=self.colors['bg_primary'],
                             anchor='w')
        time_label.pack(fill=tk.X, pady=(0, 15))
        
        # 按钮容器
        button_frame = tk.Frame(right_frame, bg=self.colors['bg_primary'])
        button_frame.pack(fill=tk.X)
        
        # 关闭按钮
        close_btn = tk.Button(button_frame, text="关闭",
                             font=('Segoe UI', 12, 'bold'),
                             fg='white',
                             bg=self.colors['accent'],
                             activebackground='#C0392B',
                             activeforeground='white',
                             relief='flat',
                             cursor='hand2',
                             padx=30, pady=10,
                             command=self._on_close)
        close_btn.pack(side=tk.LEFT)
        
        # 存储组件引用
        self.main_frame = main_frame
    
    def _center_window(self):
        """将窗口居中显示"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        
        # 获取屏幕尺寸
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def _play_alarm_sound(self):
        """播放系统提示音"""
        try:
            import winsound
            # 播放系统默认提示音
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except ImportError:
            # 如果winsound不可用，尝试使用其他方法
            try:
                import os
                os.system('echo \a')  # 系统蜂鸣声
            except:
                pass  # 静默失败
    
    
    def _on_close(self):
        """关闭窗口"""
        if self.is_closed:
            return
            
        self.is_closed = True
        
        # 调用取消回调
        if self.cancel_callback:
            try:
                self.cancel_callback(self.alarm_data)
            except Exception as e:
                print(f"Error calling cancel callback: {e}")
        
        # 关闭窗口
        if self.window:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
            self.window = None
    
    
    def _auto_close(self):
        """自动关闭窗口"""
        if not self.is_closed:
            print(f"Auto-closing alarm popup: {self.alarm_data.get('name', 'Unknown')}")
            self._on_close()
    
    def close(self):
        """外部调用关闭方法"""
        self._on_close()