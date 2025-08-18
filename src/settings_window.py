import tkinter as tk
from tkinter import ttk, messagebox
from settings_manager import SettingsManager
import os
from PIL import Image, ImageTk

# Import UI constants from gui.py
SPACING = {
    'xs': 4,    # 4px - 最小间距
    'sm': 8,    # 8px - 基础单位
    'md': 16,   # 16px - 标准间距
    'lg': 24,   # 24px - 大间距
    'xl': 32,   # 32px - 超大间距
}

COLORS = {
    'bg_primary': '#F5F5F7',      # 浅灰色背景
    'bg_secondary': '#FFFFFF',     # 白色背景
    'bg_card': '#FFFFFF',          # 卡片背景
    'accent': '#007AFF',           # 蓝色强调色
    'text_primary': '#1D1D1F',     # 主要文字颜色
    'text_secondary': '#6E6E73',   # 次要文字颜色
    'border': '#E5E5EA',           # 边框颜色
    'border_light': '#F2F2F7',     # 浅边框颜色
    'success': '#34C759',          # 成功/激活颜色
    'warning': '#FF9500',          # 警告颜色
    'danger': '#FF3B30',           # 危险/删除颜色
    'shadow': '#00000010'          # 阴影颜色
}

class SettingsWindow:
    """Settings window for the application."""
    
    def __init__(self, parent, settings_manager: SettingsManager, on_settings_changed=None):
        self.parent = parent
        self.settings_manager = settings_manager
        self.on_settings_changed = on_settings_changed
        self.window = None
        
    def show(self):
        """Shows the settings window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus()
            return
            
        self.window = tk.Toplevel(self.parent)
        self.window.title("应用设置")
        self.window.geometry("500x650")  # 设置合适的高度
        self.window.configure(bg=COLORS['bg_primary'])
        self.window.resizable(False, False)
        
        # Center the window
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Center on parent window
        self.window.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        self._create_widgets()
        
    def _create_title_with_image(self, parent):
        """Create title area with background image."""
        try:
            # Load and resize the image
            image_path = os.path.join("assets", "notification.png")
            if os.path.exists(image_path):
                # Open and resize image to fit the settings window width
                original_image = Image.open(image_path)
                original_width, original_height = original_image.size
                
                # Scale to fit settings window (approximately 450px wide)
                target_width = 450
                target_height = int((target_width / original_width) * original_height)
                
                # Limit height to not take too much space
                if target_height > 200:
                    target_height = 200
                    target_width = int((target_height / original_height) * original_width)
                
                resized_image = original_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                self.title_photo = ImageTk.PhotoImage(resized_image)
                
                # Create image label
                image_label = tk.Label(parent, image=self.title_photo, bg=COLORS['bg_primary'])
                image_label.pack(pady=(0, SPACING['lg']))
                
                print(f"Settings title image loaded: {target_width}x{target_height}")
            else:
                # Fallback to text title if image not found
                title_label = tk.Label(parent, text="牛马生物钟设置", 
                                      font=('Segoe UI', 16, 'bold'),
                                      fg=COLORS['text_primary'], bg=COLORS['bg_primary'])
                title_label.pack(pady=(0, SPACING['lg']))
                print(f"Image not found, using text title: {image_path}")
        except Exception as e:
            # Fallback to text title if image loading fails
            title_label = tk.Label(parent, text="牛马生物钟设置", 
                                  font=('Segoe UI', 16, 'bold'),
                                  fg=COLORS['text_primary'], bg=COLORS['bg_primary'])
            title_label.pack(pady=(0, SPACING['lg']))
            print(f"Failed to load title image: {e}")

    def _create_widgets(self):
        """Creates the settings window widgets."""
        # Main container
        main_frame = tk.Frame(self.window, bg='#F5F5F7')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['md'], pady=SPACING['md'])
        
        # Title with background image
        self._create_title_with_image(main_frame)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.configure(height=280)  # 设置固定高度
        notebook.pack(fill=tk.X, pady=(0, SPACING['md']))  # 移除expand=True，只水平填充
        
        # Notification settings tab
        self._create_notification_tab(notebook)
        
        # UI settings tab
        self._create_ui_tab(notebook)
        
        # Timer settings tab
        self._create_timer_tab(notebook)
        
        # Performance settings tab
        self._create_performance_tab(notebook)
        
        # Visual effects settings tab
        self._create_visual_effects_tab(notebook)
        
        # Buttons frame
        buttons_frame = tk.Frame(main_frame, bg='#F5F5F7')
        buttons_frame.pack(fill=tk.X, pady=(SPACING['md'], 0))
        
        # Reset to defaults button
        reset_btn = tk.Button(buttons_frame, text="恢复默认设置",
                             font=('Segoe UI', 9),
                             fg='#6E6E73', bg='#F2F2F7',
                             relief='flat', cursor='hand2',
                             padx=SPACING['md'], pady=SPACING['sm'],
                             command=self._reset_to_defaults)
        reset_btn.pack(side=tk.LEFT)
        
        # Close button
        close_btn = tk.Button(buttons_frame, text="关闭",
                             font=('Segoe UI', 9, 'bold'),
                             fg='white', bg='#007AFF',
                             relief='flat', cursor='hand2',
                             padx=SPACING['md'], pady=SPACING['sm'],
                             command=self.window.destroy)
        close_btn.pack(side=tk.RIGHT)
        
    def _create_notification_tab(self, notebook):
        """Creates the notification settings tab."""
        frame = tk.Frame(notebook, bg='#FFFFFF')
        notebook.add(frame, text="通知设置")
        
        # Content frame with padding
        content = tk.Frame(frame, bg=COLORS['bg_secondary'])
        content.pack(fill=tk.BOTH, expand=True, padx=SPACING['md'], pady=SPACING['md'])
        
        # Notifications enabled
        self.notifications_enabled_var = tk.BooleanVar(
            value=self.settings_manager.get("notifications.enabled", True)
        )
        notifications_cb = tk.Checkbutton(content, text="启用系统通知",
                                        variable=self.notifications_enabled_var,
                                        font=('Segoe UI', 10),
                                        bg=COLORS['bg_secondary'],
                                        fg=COLORS['text_primary'],
                                        command=self._save_notification_settings)
        notifications_cb.pack(anchor="w", pady=(0, SPACING['md']))
        
        # Notification timeout (disabled - Windows controls this)
        timeout_frame = tk.Frame(content, bg=COLORS['bg_secondary'])
        timeout_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        tk.Label(timeout_frame, text="通知显示时长 (由Windows系统控制):",
                font=('Segoe UI', 10),
                fg=COLORS['text_secondary'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.timeout_var = tk.StringVar(value="系统控制")
        timeout_label = tk.Label(timeout_frame, textvariable=self.timeout_var,
                                font=('Segoe UI', 9),
                                fg=COLORS['text_secondary'], bg=COLORS['bg_secondary'])
        timeout_label.pack(side=tk.RIGHT)
        
        # Sound enabled (placeholder for future implementation)
        self.sound_enabled_var = tk.BooleanVar(
            value=self.settings_manager.get("notifications.sound_enabled", False)
        )
        sound_cb = tk.Checkbutton(content, text="启用通知声音 (暂未实现)",
                                 variable=self.sound_enabled_var,
                                 font=('Segoe UI', 10),
                                 bg=COLORS['bg_secondary'],
                                 fg=COLORS['text_secondary'],
                                 state='disabled',
                                 command=self._save_notification_settings)
        sound_cb.pack(anchor="w", pady=(0, SPACING['md']))
        
        # Windows notification explanation
        info_text = """Windows通知说明：
• 通知显示时长由Windows系统设置控制，无法通过应用调整
• 可在Windows设置 > 系统 > 通知中调整系统通知行为
• 应用只能控制是否发送通知，不能控制显示时长"""
        
        info_label = tk.Label(content, text=info_text,
                             font=('Segoe UI', 9),
                             fg=COLORS['text_secondary'], bg=COLORS['bg_secondary'],
                             justify=tk.LEFT, wraplength=400)
        info_label.pack(anchor="w", pady=(SPACING['lg'], 0))
        
    def _create_ui_tab(self, notebook):
        """Creates the UI settings tab."""
        frame = tk.Frame(notebook, bg=COLORS['bg_secondary'])
        notebook.add(frame, text="界面设置")
        
        content = tk.Frame(frame, bg=COLORS['bg_secondary'])
        content.pack(fill=tk.BOTH, expand=True, padx=SPACING['md'], pady=SPACING['md'])
        
        # Minimize to tray
        self.minimize_to_tray_var = tk.BooleanVar(
            value=self.settings_manager.get("ui.minimize_to_tray", True)
        )
        minimize_cb = tk.Checkbutton(content, text="关闭窗口时最小化到系统托盘",
                                   variable=self.minimize_to_tray_var,
                                   font=('Segoe UI', 10),
                                   bg=COLORS['bg_secondary'],
                                   fg=COLORS['text_primary'],
                                   command=self._save_ui_settings)
        minimize_cb.pack(anchor="w", pady=(0, SPACING['md']))
        
        # Start minimized
        self.start_minimized_var = tk.BooleanVar(
            value=self.settings_manager.get("ui.start_minimized", False)
        )
        start_minimized_cb = tk.Checkbutton(content, text="启动时最小化到托盘",
                                          variable=self.start_minimized_var,
                                          font=('Segoe UI', 10),
                                          bg=COLORS['bg_secondary'],
                                          fg=COLORS['text_primary'],
                                          command=self._save_ui_settings)
        start_minimized_cb.pack(anchor="w", pady=(0, SPACING['md']))
        
        # Auto start (placeholder)
        self.auto_start_var = tk.BooleanVar(
            value=self.settings_manager.get("ui.auto_start", False)
        )
        auto_start_cb = tk.Checkbutton(content, text="开机自启动 (暂未实现)",
                                     variable=self.auto_start_var,
                                     font=('Segoe UI', 10),
                                     bg=COLORS['bg_secondary'],
                                     fg=COLORS['text_secondary'],
                                     state='disabled',
                                     command=self._save_ui_settings)
        auto_start_cb.pack(anchor="w", pady=(0, SPACING['md']))
        
        # Theme selection (placeholder)
        theme_frame = tk.Frame(content, bg=COLORS['bg_secondary'])
        theme_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        tk.Label(theme_frame, text="主题 (暂未实现):",
                font=('Segoe UI', 10),
                fg=COLORS['text_secondary'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.theme_var = tk.StringVar(value=self.settings_manager.get("ui.theme", "light"))
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var,
                                  values=["light", "dark"], state='disabled',
                                  width=10)
        theme_combo.pack(side=tk.RIGHT)
        
    def _create_timer_tab(self, notebook):
        """Creates the timer settings tab."""
        frame = tk.Frame(notebook, bg=COLORS['bg_secondary'])
        notebook.add(frame, text="计时器设置")
        
        content = tk.Frame(frame, bg=COLORS['bg_secondary'])
        content.pack(fill=tk.BOTH, expand=True, padx=SPACING['md'], pady=SPACING['md'])
        
        # Default timer durations
        timers = [
            ("默认专注时长 (分钟):", "timers.default_pomodoro", 25),
            ("默认短休息时长 (分钟):", "timers.default_short_break", 5),
            ("默认长休息时长 (分钟):", "timers.default_long_break", 15)
        ]
        
        self.timer_vars = {}
        
        for label_text, setting_key, default_value in timers:
            timer_frame = tk.Frame(content, bg=COLORS['bg_secondary'])
            timer_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
            
            tk.Label(timer_frame, text=label_text,
                    font=('Segoe UI', 10),
                    fg=COLORS['text_primary'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT)
            
            var = tk.StringVar(value=str(self.settings_manager.get(setting_key, default_value)))
            self.timer_vars[setting_key] = var
            
            spin = tk.Spinbox(timer_frame, from_=1, to=120, textvariable=var,
                             width=5, font=('Segoe UI', 9),
                             command=self._save_timer_settings)
            spin.pack(side=tk.RIGHT)
            spin.bind('<KeyRelease>', lambda e: self._save_timer_settings())
        
        # Auto start breaks (placeholder)
        self.auto_start_breaks_var = tk.BooleanVar(
            value=self.settings_manager.get("timers.auto_start_breaks", False)
        )
        auto_breaks_cb = tk.Checkbutton(content, text="自动开始休息计时器 (暂未实现)",
                                       variable=self.auto_start_breaks_var,
                                       font=('Segoe UI', 10),
                                       bg=COLORS['bg_secondary'],
                                       fg=COLORS['text_secondary'],
                                       state='disabled',
                                       command=self._save_timer_settings)
        auto_breaks_cb.pack(anchor="w", pady=(SPACING['lg'], 0))
        
    def _create_performance_tab(self, notebook):
        """Creates the performance settings tab."""
        frame = tk.Frame(notebook, bg=COLORS['bg_secondary'])
        notebook.add(frame, text="性能设置")
        
        content = tk.Frame(frame, bg=COLORS['bg_secondary'])
        content.pack(fill=tk.BOTH, expand=True, padx=SPACING['md'], pady=SPACING['md'])
        
        # Check interval
        interval_frame = tk.Frame(content, bg=COLORS['bg_secondary'])
        interval_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        tk.Label(interval_frame, text="定时器检查间隔 (秒):",
                font=('Segoe UI', 10),
                fg=COLORS['text_primary'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.check_interval_var = tk.StringVar(
            value=str(self.settings_manager.get("performance.check_interval", 1.0))
        )
        interval_spin = tk.Spinbox(interval_frame, from_=0.1, to=5.0, increment=0.1,
                                  textvariable=self.check_interval_var,
                                  width=5, font=('Segoe UI', 9),
                                  command=self._save_performance_settings)
        interval_spin.pack(side=tk.RIGHT)
        interval_spin.bind('<KeyRelease>', lambda e: self._save_performance_settings())
        
        # Low power mode
        self.low_power_mode_var = tk.BooleanVar(
            value=self.settings_manager.get("performance.low_power_mode", False)
        )
        low_power_cb = tk.Checkbutton(content, text="低功耗模式 (增加检查间隔以节省CPU)",
                                     variable=self.low_power_mode_var,
                                     font=('Segoe UI', 10),
                                     bg=COLORS['bg_secondary'],
                                     fg=COLORS['text_primary'],
                                     command=self._save_performance_settings)
        low_power_cb.pack(anchor="w", pady=(0, SPACING['md']))
        
        # Performance info
        info_text = """性能优化说明：
• 检查间隔：定时器检查的频率，较小值更精确但消耗更多CPU
• 低功耗模式：自动调整检查间隔以减少后台资源占用
• 建议设置：正常使用1.0秒，笔记本电池模式2.0秒"""
        
        info_label = tk.Label(content, text=info_text,
                             font=('Segoe UI', 9),
                             fg=COLORS['text_secondary'], bg=COLORS['bg_secondary'],
                             justify=tk.LEFT, wraplength=400)
        info_label.pack(anchor="w", pady=(SPACING['lg'], 0))
        
    def _create_visual_effects_tab(self, notebook):
        """Creates the visual effects settings tab."""
        frame = tk.Frame(notebook, bg=COLORS['bg_secondary'])
        notebook.add(frame, text="视觉效果")
        
        content = tk.Frame(frame, bg=COLORS['bg_secondary'])
        content.pack(fill=tk.BOTH, expand=True, padx=SPACING['md'], pady=SPACING['md'])
        
        # Visual effects enabled
        self.visual_effects_enabled_var = tk.BooleanVar(
            value=self.settings_manager.get("visual_effects.enabled", True)
        )
        effects_cb = tk.Checkbutton(content, text="启用屏幕视觉提醒效果",
                                   variable=self.visual_effects_enabled_var,
                                   font=('Segoe UI', 10),
                                   bg=COLORS['bg_secondary'],
                                   fg=COLORS['text_primary'],
                                   command=self._save_visual_effects_settings)
        effects_cb.pack(anchor="w", pady=(0, SPACING['md']))
        
        # Effect type selection
        type_frame = tk.Frame(content, bg=COLORS['bg_secondary'])
        type_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        tk.Label(type_frame, text="效果类型:",
                font=('Segoe UI', 10),
                fg=COLORS['text_primary'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.effect_type_var = tk.StringVar(
            value=self.settings_manager.get("visual_effects.type", "border_flash")
        )
        effect_types = [
            ("边缘闪光", "border_flash"),
            ("全屏闪烁", "screen_flash")
        ]
        
        type_combo = ttk.Combobox(type_frame, textvariable=self.effect_type_var,
                                 values=[desc for desc, _ in effect_types],
                                 state='readonly', width=15)
        type_combo.pack(side=tk.RIGHT)
        
        # Map display names to internal values
        self.effect_type_mapping = {desc: value for desc, value in effect_types}
        self.reverse_effect_type_mapping = {value: desc for desc, value in effect_types}
        
        # Set current selection
        current_type = self.settings_manager.get("visual_effects.type", "border_flash")
        if current_type in self.reverse_effect_type_mapping:
            type_combo.set(self.reverse_effect_type_mapping[current_type])
        
        type_combo.bind('<<ComboboxSelected>>', lambda e: self._save_visual_effects_settings())
        
        # Color scheme selection
        color_frame = tk.Frame(content, bg=COLORS['bg_secondary'])
        color_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        tk.Label(color_frame, text="配色方案:",
                font=('Segoe UI', 10),
                fg=COLORS['text_primary'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.color_scheme_var = tk.StringVar(
            value=self.settings_manager.get("visual_effects.color_scheme", "classic_red")
        )
        color_schemes = [
            ("经典红色", "classic_red"),
            ("蓝色专业", "blue_professional"),
            ("绿色健康", "green_healthy"),
            ("紫色优雅", "purple_elegant"),
            ("黄色活力", "yellow_energetic")
        ]
        
        color_combo = ttk.Combobox(color_frame, textvariable=self.color_scheme_var,
                                  values=[desc for desc, _ in color_schemes],
                                  state='readonly', width=15)
        color_combo.pack(side=tk.RIGHT)
        
        # Map display names to internal values
        self.color_scheme_mapping = {desc: value for desc, value in color_schemes}
        self.reverse_color_scheme_mapping = {value: desc for desc, value in color_schemes}
        
        # Set current selection
        current_scheme = self.settings_manager.get("visual_effects.color_scheme", "classic_red")
        if current_scheme in self.reverse_color_scheme_mapping:
            color_combo.set(self.reverse_color_scheme_mapping[current_scheme])
        
        color_combo.bind('<<ComboboxSelected>>', lambda e: self._save_visual_effects_settings())
        
        # Effect duration
        duration_frame = tk.Frame(content, bg=COLORS['bg_secondary'])
        duration_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        tk.Label(duration_frame, text="效果持续时间 (秒):",
                font=('Segoe UI', 10),
                fg=COLORS['text_primary'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.effect_duration_var = tk.StringVar(
            value=str(self.settings_manager.get("visual_effects.duration", 5.0))
        )
        duration_spin = tk.Spinbox(duration_frame, from_=1.0, to=30.0, increment=0.5,
                                  textvariable=self.effect_duration_var,
                                  width=8, font=('Segoe UI', 9),
                                  command=self._save_visual_effects_settings)
        duration_spin.pack(side=tk.RIGHT)
        duration_spin.bind('<KeyRelease>', lambda e: self._save_visual_effects_settings())
        
        # Effect intensity
        intensity_frame = tk.Frame(content, bg=COLORS['bg_secondary'])
        intensity_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        tk.Label(intensity_frame, text="效果强度:",
                font=('Segoe UI', 10),
                fg=COLORS['text_primary'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT)
        
        self.effect_intensity_var = tk.StringVar(
            value=self.settings_manager.get("visual_effects.intensity", "medium")
        )
        intensity_combo = ttk.Combobox(intensity_frame, textvariable=self.effect_intensity_var,
                                      values=["低", "中", "高"],
                                      state='readonly', width=10)
        intensity_combo.pack(side=tk.RIGHT)
        
        # Map intensity values
        intensity_mapping = {"低": "low", "中": "medium", "高": "high"}
        reverse_intensity_mapping = {"low": "低", "medium": "中", "high": "高"}
        
        current_intensity = self.settings_manager.get("visual_effects.intensity", "medium")
        if current_intensity in reverse_intensity_mapping:
            intensity_combo.set(reverse_intensity_mapping[current_intensity])
        
        intensity_combo.bind('<<ComboboxSelected>>', lambda e: self._save_visual_effects_settings())
        
        # Store mappings for saving
        self.intensity_mapping = intensity_mapping
        
        # Test button
        test_btn = tk.Button(content, text="测试效果",
                           font=('Segoe UI', 9),
                           fg='white', bg=COLORS['accent'],
                           relief='flat', cursor='hand2',
                           padx=SPACING['md'], pady=SPACING['sm'],
                           command=self._test_visual_effect)
        test_btn.pack(pady=(SPACING['sm'], 0))
        
    def _save_notification_settings(self):
        """Saves notification settings."""
        self.settings_manager.set("notifications.enabled", self.notifications_enabled_var.get())
        self.settings_manager.set("notifications.sound_enabled", self.sound_enabled_var.get())
        if self.on_settings_changed:
            self.on_settings_changed("notifications")
            
    def _save_ui_settings(self):
        """Saves UI settings."""
        self.settings_manager.set("ui.minimize_to_tray", self.minimize_to_tray_var.get())
        self.settings_manager.set("ui.start_minimized", self.start_minimized_var.get())
        self.settings_manager.set("ui.auto_start", self.auto_start_var.get())
        self.settings_manager.set("ui.theme", self.theme_var.get())
        if self.on_settings_changed:
            self.on_settings_changed("ui")
            
    def _save_timer_settings(self):
        """Saves timer settings."""
        try:
            for setting_key, var in self.timer_vars.items():
                self.settings_manager.set(setting_key, int(var.get()))
            self.settings_manager.set("timers.auto_start_breaks", self.auto_start_breaks_var.get())
            if self.on_settings_changed:
                self.on_settings_changed("timers")
        except ValueError:
            pass  # Invalid input, ignore
            
    def _save_performance_settings(self):
        """Saves performance settings."""
        try:
            interval = float(self.check_interval_var.get())
            low_power = self.low_power_mode_var.get()
            
            # Apply low power mode logic
            if low_power and interval < 2.0:
                interval = 2.0
                self.check_interval_var.set("2.0")
            
            self.settings_manager.set("performance.check_interval", interval)
            self.settings_manager.set("performance.low_power_mode", low_power)
            if self.on_settings_changed:
                self.on_settings_changed("performance")
        except ValueError:
            pass  # Invalid input, ignore
            
    def _save_visual_effects_settings(self):
        """Saves visual effects settings."""
        try:
            self.settings_manager.set("visual_effects.enabled", self.visual_effects_enabled_var.get())
            
            # Get effect type from combo box
            selected_type_display = self.effect_type_var.get()
            if selected_type_display in self.effect_type_mapping:
                effect_type = self.effect_type_mapping[selected_type_display]
            else:
                effect_type = selected_type_display  # fallback
            self.settings_manager.set("visual_effects.type", effect_type)
            
            # Get duration
            duration = float(self.effect_duration_var.get())
            self.settings_manager.set("visual_effects.duration", duration)
            
            # Get intensity
            selected_intensity_display = self.effect_intensity_var.get()
            if selected_intensity_display in self.intensity_mapping:
                intensity = self.intensity_mapping[selected_intensity_display]
            else:
                intensity = "medium"  # fallback
            self.settings_manager.set("visual_effects.intensity", intensity)
            
            # Get color scheme
            selected_scheme_display = self.color_scheme_var.get()
            if selected_scheme_display in self.color_scheme_mapping:
                color_scheme = self.color_scheme_mapping[selected_scheme_display]
            else:
                color_scheme = "classic_red"  # fallback
            self.settings_manager.set("visual_effects.color_scheme", color_scheme)
            
            if self.on_settings_changed:
                self.on_settings_changed("visual_effects")
        except ValueError:
            pass  # Invalid input, ignore
    
    def _test_visual_effect(self):
        """Tests the current visual effect settings."""
        try:
            from screen_effects import ScreenEffectsManager
            
            # Create temporary effects manager with current settings
            effects_manager = ScreenEffectsManager(self.settings_manager)
            
            # Get current settings - use the actual duration from settings
            effect_type = self.settings_manager.get("visual_effects.type", "border_flash")
            duration = self.settings_manager.get("visual_effects.duration", 5.0)
            
            # Show test effect
            effects_manager.show_alarm_effect(effect_type, duration)
            
            # Show info message
            messagebox.showinfo("测试效果", f"正在显示 {duration} 秒的视觉效果测试")
            
        except ImportError:
            messagebox.showerror("错误", "视觉效果模块未找到")
        except Exception as e:
            messagebox.showerror("错误", f"测试视觉效果时出错: {e}")
    
    def _reset_to_defaults(self):
        """Resets all settings to defaults."""
        if messagebox.askyesno("确认重置", "确定要将所有设置恢复为默认值吗？"):
            self.settings_manager.reset_to_defaults()
            self.window.destroy()
            messagebox.showinfo("设置重置", "设置已恢复为默认值，请重启应用以使所有更改生效。")