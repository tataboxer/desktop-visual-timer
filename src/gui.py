import tkinter as tk
from tkinter import ttk, messagebox
import uuid
from datetime import datetime
import os
from PIL import Image, ImageTk

# UI Design System - 8px Grid System
SPACING = {
    'xs': 4,    # 4px - 最小间距
    'sm': 8,    # 8px - 基础单位
    'md': 16,   # 16px - 标准间距
    'lg': 24,   # 24px - 大间距
    'xl': 32,   # 32px - 超大间距
}

# UI Color Scheme
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

class AppGUI(tk.Tk):
    """The main application GUI, built with tkinter."""

    def __init__(self, data_manager, timer_engine, settings_manager=None):
        super().__init__()
        self.data_manager = data_manager
        self.timer_engine = timer_engine
        self.settings_manager = settings_manager

        self.title("牛马生物钟 v1.0")
        self.geometry("800x550")  # 增加窗口大小
        self.configure(bg=COLORS['bg_primary'])
        self.minsize(750, 500)  # 设置最小尺寸
        
        # Configure style
        self._configure_styles()

        self.alarms = self.data_manager.load_alarms()
        self.selected_alarm_id = None

        self._setup_widgets()
        self._load_alarms_to_list()

        # Check if should start minimized
        if self.settings_manager and self.settings_manager.get("ui.start_minimized", False):
            self.after(100, self.hide_window)  # Hide after GUI is fully loaded

        # Intercept close button
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _configure_styles(self):
        """Configure ttk styles for the application."""
        style = ttk.Style()
        
        # Configure main frame style
        style.configure('Main.TFrame', background=COLORS['bg_primary'])
        style.configure('Card.TFrame', background=COLORS['bg_secondary'], relief='solid', borderwidth=1)
        
        # Configure label styles
        style.configure('Title.TLabel', 
                       background=COLORS['bg_primary'], 
                       foreground=COLORS['text_primary'],
                       font=('Segoe UI', 14, 'bold'))
        style.configure('Subtitle.TLabel', 
                       background=COLORS['bg_secondary'], 
                       foreground=COLORS['text_primary'],
                       font=('Segoe UI', 11, 'bold'))
        style.configure('Body.TLabel', 
                       background=COLORS['bg_secondary'], 
                       foreground=COLORS['text_primary'],
                       font=('Segoe UI', 9))
        style.configure('CurrentTime.TLabel', 
                       background=COLORS['bg_secondary'], 
                       foreground=COLORS['accent'],
                       font=('Segoe UI', 11, 'bold'))
        
        # Configure button styles
        style.configure('Accent.TButton',
                       font=('Segoe UI', 9, 'bold'))
        style.configure('Success.TButton',
                       font=('Segoe UI', 9))
        style.configure('Danger.TButton',
                       font=('Segoe UI', 8))

    def _setup_widgets(self):
        # Main container with proper spacing
        main_container = tk.Frame(self, bg=COLORS['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=SPACING['md'], pady=SPACING['md'])
        
        # Configure grid weights for responsive layout
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=0)
        main_container.grid_columnconfigure(0, weight=2)  # Left panel gets more space
        main_container.grid_columnconfigure(1, weight=1)  # Right panel fixed width
        
        # Left panel - Alarm List (Card style with shadow effect)
        left_card = tk.Frame(main_container, bg=COLORS['bg_card'], relief='solid', 
                           borderwidth=1, bd=1, highlightbackground=COLORS['border'])
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING['sm']))
        
        # Left panel content with proper padding
        left_content = tk.Frame(left_card, bg=COLORS['bg_card'])
        left_content.pack(fill=tk.BOTH, expand=True, padx=SPACING['md'], pady=SPACING['md'])
        
        # Left panel header with proper spacing
        left_header = tk.Frame(left_content, bg=COLORS['bg_card'])
        left_header.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        # Title and buttons with proper alignment
        title_label = tk.Label(left_header, text="闹钟列表", 
                             font=('Segoe UI', 14, 'bold'),
                             fg=COLORS['text_primary'], bg=COLORS['bg_card'])
        title_label.pack(side=tk.LEFT)
        
        # Right side buttons container
        buttons_container = tk.Frame(left_header, bg=COLORS['bg_card'])
        buttons_container.pack(side=tk.RIGHT)
        
        # Settings button
        if self.settings_manager:
            settings_btn = tk.Button(buttons_container, text="⚙",
                                   font=('Segoe UI', 12),
                                   fg=COLORS['text_secondary'], bg=COLORS['bg_card'],
                                   relief='flat', cursor='hand2',
                                   width=3, pady=SPACING['xs'],
                                   command=self._show_settings)
            settings_btn.pack(side=tk.RIGHT, padx=(0, SPACING['sm']))
        
        new_alarm_btn = tk.Button(buttons_container, text="+ 新建闹钟",
                                font=('Segoe UI', 9, 'bold'),
                                fg='white', bg=COLORS['accent'],
                                relief='flat', cursor='hand2',
                                padx=SPACING['md'], pady=SPACING['xs'],
                                command=self._clear_form)
        new_alarm_btn.pack(side=tk.RIGHT)

        # Alarm list container with scrolling (no visible scrollbar)
        alarm_list_container = tk.Frame(left_content, bg=COLORS['bg_card'])
        alarm_list_container.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas for scrolling without visible scrollbar
        self.alarm_canvas = tk.Canvas(alarm_list_container, bg=COLORS['bg_card'], highlightthickness=0)
        self.alarm_list_frame = tk.Frame(self.alarm_canvas, bg=COLORS['bg_card'])
        
        # Configure scrolling
        def _configure_scroll_region(event):
            self.alarm_canvas.configure(scrollregion=self.alarm_canvas.bbox("all"))
        
        def _configure_canvas_width(event):
            # Make the frame width match the canvas width
            canvas_width = event.width
            self.alarm_canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.alarm_list_frame.bind("<Configure>", _configure_scroll_region)
        self.alarm_canvas.bind("<Configure>", _configure_canvas_width)
        
        self.canvas_window = self.alarm_canvas.create_window((0, 0), window=self.alarm_list_frame, anchor="nw")
        self.alarm_canvas.pack(fill="both", expand=True)
        
        # Bind mouse wheel to canvas for scrolling
        def _on_mousewheel(event):
            self.alarm_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel to canvas and its children
        self.alarm_canvas.bind("<MouseWheel>", _on_mousewheel)
        self.alarm_list_frame.bind("<MouseWheel>", _on_mousewheel)

        # Right panel - Edit Alarm (Card style)
        right_card = tk.Frame(main_container, bg=COLORS['bg_card'], relief='solid',
                            borderwidth=1, bd=1, highlightbackground=COLORS['border'])
        right_card.grid(row=0, column=1, sticky="nsew", padx=(SPACING['sm'], 0))
        
        # Right panel content with proper padding
        self.right_content = tk.Frame(right_card, bg=COLORS['bg_card'])
        self.right_content.pack(fill=tk.BOTH, expand=True, padx=SPACING['md'], pady=SPACING['md'])
        
        # Configure grid for form layout
        self.right_content.grid_columnconfigure(0, weight=0)  # Labels column
        self.right_content.grid_columnconfigure(1, weight=1)  # Inputs column
        
        # Right panel header
        header_label = tk.Label(self.right_content, text="编辑闹钟", 
                              font=('Segoe UI', 14, 'bold'),
                              fg=COLORS['text_primary'], bg=COLORS['bg_card'])
        header_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, SPACING['lg']))
        
        # Current Time Display
        current_time_label = tk.Label(self.right_content, text="当前时间:", 
                                    font=('Segoe UI', 9),
                                    fg=COLORS['text_secondary'], bg=COLORS['bg_card'])
        current_time_label.grid(row=1, column=0, sticky="w", pady=(0, SPACING['md']))
        
        self.current_time_label = tk.Label(self.right_content, text="", 
                                         font=('Segoe UI', 11, 'bold'),
                                         fg=COLORS['accent'], bg=COLORS['bg_card'])
        self.current_time_label.grid(row=1, column=1, sticky="w", padx=(SPACING['sm'], 0), pady=(0, SPACING['md']))
        
        # Time setting section
        time_label = tk.Label(self.right_content, text="闹钟时间:", 
                            font=('Segoe UI', 9),
                            fg=COLORS['text_secondary'], bg=COLORS['bg_card'])
        time_label.grid(row=2, column=0, sticky="w", pady=(0, SPACING['md']))
        
        # Time input frame
        time_input_frame = tk.Frame(self.right_content, bg=COLORS['bg_card'])
        time_input_frame.grid(row=2, column=1, sticky="w", padx=(SPACING['sm'], 0), pady=(0, SPACING['md']))
        
        # Set default time to current time
        now = datetime.now()
        self.hour_var = tk.StringVar(value=f"{now.hour:02d}")
        self.minute_var = tk.StringVar(value=f"{now.minute:02d}")
        self.second_var = tk.StringVar(value=f"{now.second:02d}")
        
        # Time spinboxes with proper spacing
        hour_spin = tk.Spinbox(time_input_frame, from_=0, to=23, textvariable=self.hour_var, 
                             width=3, font=('Segoe UI', 9))
        hour_spin.pack(side=tk.LEFT)
        
        tk.Label(time_input_frame, text=":", font=('Segoe UI', 9),
                fg=COLORS['text_primary'], bg=COLORS['bg_card']).pack(side=tk.LEFT, padx=SPACING['xs'])
        
        minute_spin = tk.Spinbox(time_input_frame, from_=0, to=59, textvariable=self.minute_var, 
                               width=3, font=('Segoe UI', 9))
        minute_spin.pack(side=tk.LEFT)
        
        tk.Label(time_input_frame, text=":", font=('Segoe UI', 9),
                fg=COLORS['text_primary'], bg=COLORS['bg_card']).pack(side=tk.LEFT, padx=SPACING['xs'])
        
        second_spin = tk.Spinbox(time_input_frame, from_=0, to=59, textvariable=self.second_var, 
                               width=3, font=('Segoe UI', 9))
        second_spin.pack(side=tk.LEFT)

        # Name section
        name_label = tk.Label(self.right_content, text="标签:", 
                            font=('Segoe UI', 9),
                            fg=COLORS['text_secondary'], bg=COLORS['bg_card'])
        name_label.grid(row=3, column=0, sticky="w", pady=(0, SPACING['md']))
        
        self.name_var = tk.StringVar()
        name_entry = tk.Entry(self.right_content, textvariable=self.name_var, 
                            font=('Segoe UI', 9), width=20)
        name_entry.grid(row=3, column=1, sticky="w", padx=(SPACING['sm'], 0), pady=(0, SPACING['md']))

        # Repeat section
        repeat_label = tk.Label(self.right_content, text="重复:", 
                              font=('Segoe UI', 9),
                              fg=COLORS['text_secondary'], bg=COLORS['bg_card'])
        repeat_label.grid(row=4, column=0, sticky="nw", pady=(0, SPACING['md']))
        
        # Days grid with proper spacing
        days_frame = tk.Frame(self.right_content, bg=COLORS['bg_card'])
        days_frame.grid(row=4, column=1, sticky="w", padx=(SPACING['sm'], 0), pady=(0, SPACING['md']))
        
        self.day_vars = {day: tk.BooleanVar() for day in ["一", "二", "三", "四", "五", "六", "日"]}
        
        for i, (day, var) in enumerate(self.day_vars.items()):
            row = i // 4
            col = i % 4
            cb = tk.Checkbutton(days_frame, text=day, variable=var,
                              font=('Segoe UI', 9), bg=COLORS['bg_card'],
                              fg=COLORS['text_primary'])
            cb.grid(row=row, column=col, sticky="w", padx=(0, SPACING['sm']), pady=SPACING['xs'])

        # Action buttons with proper spacing
        button_frame = tk.Frame(self.right_content, bg=COLORS['bg_card'])
        button_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(SPACING['lg'], 0))
        
        # Right-align buttons
        cancel_button = tk.Button(button_frame, text="取消",
                                font=('Segoe UI', 9),
                                fg=COLORS['text_secondary'], bg=COLORS['bg_card'],
                                relief='flat', cursor='hand2',
                                padx=SPACING['md'], pady=SPACING['xs'],
                                command=self._clear_form)
        cancel_button.pack(side=tk.RIGHT)
        
        save_button = tk.Button(button_frame, text="保存",
                              font=('Segoe UI', 9, 'bold'),
                              fg='white', bg=COLORS['accent'],
                              relief='flat', cursor='hand2',
                              padx=SPACING['md'], pady=SPACING['xs'],
                              command=self._save_alarm)
        save_button.pack(side=tk.RIGHT, padx=(0, SPACING['sm']))
        
        # Store day mapping for later use
        self.day_mapping = {"一": "mon", "二": "tue", "三": "wed", "四": "thu", "五": "fri", "六": "sat", "日": "sun"}
        self.reverse_day_mapping = {v: k for k, v in self.day_mapping.items()}
        
        # Bottom section - Quick Timer (Card style)
        bottom_card = tk.Frame(main_container, bg=COLORS['bg_card'], relief='solid',
                             borderwidth=1, bd=1, highlightbackground=COLORS['border'])
        bottom_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACING['md'], 0))
        
        # Bottom card content with proper padding
        bottom_content = tk.Frame(bottom_card, bg=COLORS['bg_card'])
        bottom_content.pack(fill=tk.X, padx=SPACING['md'], pady=SPACING['md'])
        
        # Quick timer header
        timer_header = tk.Frame(bottom_content, bg=COLORS['bg_card'])
        timer_header.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        timer_title = tk.Label(timer_header, text="快捷计时", 
                             font=('Segoe UI', 14, 'bold'),
                             fg=COLORS['text_primary'], bg=COLORS['bg_card'])
        timer_title.pack(side=tk.LEFT)
        
        # Timer content container
        timer_content = tk.Frame(bottom_content, bg=COLORS['bg_card'])
        timer_content.pack(fill=tk.X)
        
        # Left side - buttons with proper spacing
        self.timer_buttons_frame = tk.Frame(timer_content, bg=COLORS['bg_card'])
        self.timer_buttons_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create timer buttons with dynamic values
        self._create_timer_buttons()
        
        # Right side - active timers display with proper spacing
        self.active_timers_frame = tk.Frame(timer_content, bg=COLORS['bg_card'])
        self.active_timers_frame.pack(side=tk.RIGHT, padx=(SPACING['lg'], 0))
        
        # Start a timer to update active countdown displays
        self._update_countdown_displays()
        
        # Start updating current time
        self._update_current_time()
        
        # Initialize settings window
        self.settings_window = None

    def _load_alarms_to_list(self):
        for widget in self.alarm_list_frame.winfo_children():
            widget.destroy()

        if not self.alarms:
            # Show empty state
            empty_label = ttk.Label(self.alarm_list_frame, text="暂无闹钟\n点击右上角 '+ 新建闹钟' 来添加", 
                                  style='Body.TLabel', justify=tk.CENTER)
            empty_label.pack(expand=True, pady=50)
            return

        for alarm in self.alarms:
            # Create alarm item container with proper spacing
            alarm_item = tk.Frame(self.alarm_list_frame, bg=COLORS['bg_card'], 
                                relief='solid', borderwidth=1, 
                                highlightbackground=COLORS['border_light'])
            alarm_item.pack(fill=tk.X, pady=(0, SPACING['sm']), padx=SPACING['xs'])
            
            # Alarm content with proper padding
            alarm_content = tk.Frame(alarm_item, bg=COLORS['bg_card'])
            alarm_content.pack(fill=tk.X, padx=SPACING['md'], pady=SPACING['md'])
            
            # Top row: time and controls
            top_row = tk.Frame(alarm_content, bg=COLORS['bg_card'])
            top_row.pack(fill=tk.X)
            
            # Time display with better typography
            time_text = f"{alarm['hour']:02d}:{alarm['minute']:02d}:{alarm.get('second', 0):02d}"
            time_label = tk.Label(top_row, text=time_text, 
                                font=('Segoe UI', 16, 'bold'), 
                                fg=COLORS['text_primary'], bg=COLORS['bg_card'])
            time_label.pack(side=tk.LEFT)
            
            # Status and controls with proper spacing
            controls_frame = tk.Frame(top_row, bg=COLORS['bg_card'])
            controls_frame.pack(side=tk.RIGHT)
            
            # Toggle switch button with improved design
            is_active = alarm.get('is_active', True)
            
            if is_active:
                toggle_text = "ON"
                toggle_fg = 'white'
                toggle_bg = COLORS['success']
                toggle_relief = 'flat'
            else:
                toggle_text = "OFF"
                toggle_fg = COLORS['text_secondary']
                toggle_bg = COLORS['border_light']
                toggle_relief = 'flat'
            
            # Create a modern toggle button
            toggle_btn = tk.Button(controls_frame, 
                                 text=toggle_text,
                                 font=('Segoe UI', 8, 'bold'),
                                 fg=toggle_fg,
                                 bg=toggle_bg,
                                 activebackground=toggle_bg,
                                 activeforeground=toggle_fg,
                                 relief=toggle_relief,
                                 borderwidth=0,
                                 width=4,
                                 cursor='hand2',
                                 padx=SPACING['sm'], pady=SPACING['xs'],
                                 command=lambda a_id=alarm['id']: self._toggle_alarm_button(a_id))
            toggle_btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))
            
            # Delete button with better styling
            delete_btn = tk.Button(controls_frame, text="×", 
                                 font=('Segoe UI', 10, 'bold'), 
                                 fg=COLORS['danger'], bg=COLORS['bg_card'],
                                 relief='flat', cursor='hand2',
                                 width=2, padx=SPACING['xs'], pady=SPACING['xs'],
                                 command=lambda a_id=alarm['id']: self._delete_alarm(a_id))
            delete_btn.pack(side=tk.LEFT)
            
            # Bottom row: name and type with proper spacing
            bottom_row = tk.Frame(alarm_content, bg=COLORS['bg_card'])
            bottom_row.pack(fill=tk.X, pady=(SPACING['sm'], 0))
            
            # Alarm name with better typography
            name_text = alarm['name'] or "自备粮草"
            name_label = tk.Label(bottom_row, text=name_text, 
                                font=('Segoe UI', 10), 
                                fg=COLORS['text_primary'], bg=COLORS['bg_card'])
            name_label.pack(side=tk.LEFT)
            
            # Alarm type and repeat info with better styling
            if alarm.get('days', []):
                days_chinese = [self.reverse_day_mapping.get(day, day) for day in alarm['days']]
                type_text = f"重复 • {' '.join(days_chinese)}"
            else:
                type_text = "单次"
            
            type_label = tk.Label(bottom_row, text=type_text, 
                                font=('Segoe UI', 9), 
                                fg=COLORS['text_secondary'], 
                                bg=COLORS['bg_card'])
            type_label.pack(side=tk.RIGHT)
            
            # Make the entire item clickable for editing and scrollable
            def _on_mousewheel(event):
                self.alarm_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            for widget in [alarm_item, alarm_content, top_row, bottom_row, time_label, name_label, controls_frame, toggle_btn, delete_btn, type_label]:
                widget.bind("<Button-1>", lambda e, a=alarm: self._populate_form(a))
                widget.configure(cursor="hand2")
                # Bind mouse wheel to all widgets for smooth scrolling
                widget.bind("<MouseWheel>", _on_mousewheel)

    def _populate_form(self, alarm):
        self.selected_alarm_id = alarm['id']
        self.hour_var.set(f"{alarm['hour']:02d}")
        self.minute_var.set(f"{alarm['minute']:02d}")
        self.second_var.set(f"{alarm.get('second', 0):02d}")
        self.name_var.set(alarm['name'])
        
        # Clear all day selections first
        for var in self.day_vars.values():
            var.set(False)
        
        # Set selected days using the mapping
        alarm_days = alarm.get('days', [])
        for chinese_day, var in self.day_vars.items():
            english_day = self.day_mapping[chinese_day]
            var.set(english_day in alarm_days)

    def _clear_form(self):
        self.selected_alarm_id = None
        # Set default time to current time
        now = datetime.now()
        self.hour_var.set(f"{now.hour:02d}")
        self.minute_var.set(f"{now.minute:02d}")
        self.second_var.set(f"{now.second:02d}")
        self.name_var.set("")
        for var in self.day_vars.values():
            var.set(False)

    def _save_alarm(self):
        # Convert Chinese days to English days
        selected_days = []
        for chinese_day, var in self.day_vars.items():
            if var.get():
                english_day = self.day_mapping[chinese_day]
                selected_days.append(english_day)
        
        alarm_data = {
            "hour": int(self.hour_var.get()),
            "minute": int(self.minute_var.get()),
            "second": int(self.second_var.get()),
            "name": self.name_var.get() or "自备粮草",
            "days": selected_days,
            "is_active": True
        }

        if self.selected_alarm_id:
            # Update existing alarm
            for i, alarm in enumerate(self.alarms):
                if alarm['id'] == self.selected_alarm_id:
                    alarm_data['id'] = self.selected_alarm_id
                    alarm_data['is_active'] = alarm.get('is_active', True)
                    self.alarms[i] = alarm_data
                    break
        else:
            # Create new alarm
            alarm_data['id'] = str(uuid.uuid4())
            self.alarms.append(alarm_data)

        self.data_manager.save_alarms(self.alarms)
        self.timer_engine.load_and_schedule_alarms() # Reschedule all
        self._load_alarms_to_list()
        self._clear_form()

    def _delete_alarm(self, alarm_id):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this alarm?"):
            self.alarms = [a for a in self.alarms if a['id'] != alarm_id]
            self.data_manager.save_alarms(self.alarms)
            self.timer_engine.load_and_schedule_alarms()
            self._load_alarms_to_list()
            self._clear_form()

    def _toggle_alarm_button(self, alarm_id):
        """Toggle alarm status using the custom button."""
        for i, alarm in enumerate(self.alarms):
            if alarm['id'] == alarm_id:
                # Toggle the status
                self.alarms[i]['is_active'] = not alarm.get('is_active', True)
                break
        
        # Save and reload
        self.data_manager.save_alarms(self.alarms)
        self.timer_engine.load_and_schedule_alarms()
        self._load_alarms_to_list()  # Refresh the display
    
    def _toggle_alarm(self, alarm_id, var):
        """Legacy method for checkbox toggle (if still used elsewhere)."""
        for i, alarm in enumerate(self.alarms):
            if alarm['id'] == alarm_id:
                self.alarms[i]['is_active'] = var.get()
                break
        self.data_manager.save_alarms(self.alarms)
        self.timer_engine.load_and_schedule_alarms()

    def show_window(self):
        self.deiconify()

    def hide_window(self):
        self.withdraw()
    
    def _on_window_close(self):
        """Handle window close event based on settings."""
        if self.settings_manager:
            minimize_to_tray = self.settings_manager.get("ui.minimize_to_tray", True)
            if minimize_to_tray:
                self.hide_window()
                return
        
        # If minimize to tray is disabled, actually quit the application
        self.quit()
    
    def _start_quick_timer(self, minutes: int, name: str):
        """Starts a quick countdown timer."""
        timer_id = self.timer_engine.start_countdown_timer(minutes, name)
        messagebox.showinfo("Timer Started", f"Started {name} for {minutes} minutes")
        self._update_countdown_displays()
    
    def _cancel_countdown_timer(self, timer_id: str):
        """Cancels a countdown timer."""
        self.timer_engine.cancel_countdown_timer(timer_id)
        self._update_countdown_displays()
    
    def _update_countdown_displays(self):
        """Updates the display of active countdown timers."""
        # Clear existing displays
        for widget in self.active_timers_frame.winfo_children():
            widget.destroy()
        
        # Get active timers
        active_timers = self.timer_engine.get_active_countdown_timers()
        
        if active_timers:
            # Header for active timers with proper styling
            header_label = tk.Label(self.active_timers_frame, text="活跃计时器", 
                                  font=('Segoe UI', 10, 'bold'), 
                                  fg=COLORS['text_primary'], bg=COLORS['bg_card'])
            header_label.pack(anchor="w", pady=(0, SPACING['sm']))
            
            for timer_id, timer_data in active_timers.items():
                remaining = self.timer_engine.get_countdown_timer_remaining(timer_id)
                if remaining > 0:
                    minutes = remaining // 60
                    seconds = remaining % 60
                    
                    # Timer item with proper spacing
                    timer_item = tk.Frame(self.active_timers_frame, bg=COLORS['bg_card'])
                    timer_item.pack(anchor="w", pady=(0, SPACING['xs']))
                    
                    # Timer info with better formatting
                    timer_name = timer_data['name'][:8] + "..." if len(timer_data['name']) > 8 else timer_data['name']
                    timer_text = f"{timer_name}: {minutes:02d}:{seconds:02d}"
                    timer_label = tk.Label(timer_item, text=timer_text, 
                                         font=('Segoe UI', 9),
                                         fg=COLORS['text_primary'], bg=COLORS['bg_card'])
                    timer_label.pack(side=tk.LEFT)
                    
                    # Cancel button with consistent styling
                    cancel_btn = tk.Button(timer_item, text="×", 
                                         font=('Segoe UI', 8, 'bold'),
                                         fg=COLORS['danger'], bg=COLORS['bg_card'],
                                         relief='flat', cursor='hand2',
                                         width=2, padx=SPACING['xs'],
                                         command=lambda tid=timer_id: self._cancel_countdown_timer(tid))
                    cancel_btn.pack(side=tk.LEFT, padx=(SPACING['sm'], 0))
        
        # Schedule next update
        self.after(1000, self._update_countdown_displays)
    
    def _update_current_time(self):
        """Updates the current time display."""
        now = datetime.now()
        current_time_str = now.strftime("%H:%M:%S")
        self.current_time_label.config(text=current_time_str)
        
        # Schedule next update
        self.after(1000, self._update_current_time)
    
    def _create_timer_buttons(self):
        """Creates timer buttons with values from settings."""
        # Clear existing buttons
        for widget in self.timer_buttons_frame.winfo_children():
            widget.destroy()
        
        # Get timer durations from settings
        if self.settings_manager:
            pomodoro_minutes = self.settings_manager.get("timers.default_pomodoro", 25)
            long_break_minutes = self.settings_manager.get("timers.default_long_break", 15)
            short_break_minutes = self.settings_manager.get("timers.default_short_break", 5)
        else:
            # Fallback to defaults if no settings manager
            pomodoro_minutes = 25
            long_break_minutes = 15
            short_break_minutes = 5
        
        # Pomodoro timer button
        pomodoro_btn = tk.Button(
            self.timer_buttons_frame, 
            text=f"🍅 专注 {pomodoro_minutes}分钟", 
            font=('Segoe UI', 9, 'bold'),
            fg='white', bg=COLORS['success'],
            relief='flat', cursor='hand2',
            padx=SPACING['md'], pady=SPACING['sm'],
            command=lambda: self._start_quick_timer(pomodoro_minutes, f"专注 {pomodoro_minutes}分钟")
        )
        pomodoro_btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))
        
        # Long break button
        long_break_btn = tk.Button(
            self.timer_buttons_frame, 
            text=f"🚶 长休息 {long_break_minutes}分钟", 
            font=('Segoe UI', 9),
            fg='white', bg=COLORS['warning'],
            relief='flat', cursor='hand2',
            padx=SPACING['md'], pady=SPACING['sm'],
            command=lambda: self._start_quick_timer(long_break_minutes, f"长休息 {long_break_minutes}分钟")
        )
        long_break_btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))
        
        # Short break button
        short_break_btn = tk.Button(
            self.timer_buttons_frame, 
            text=f"☕ 短休息 {short_break_minutes}分钟", 
            font=('Segoe UI', 9),
            fg='white', bg=COLORS['accent'],
            relief='flat', cursor='hand2',
            padx=SPACING['md'], pady=SPACING['sm'],
            command=lambda: self._start_quick_timer(short_break_minutes, f"短休息 {short_break_minutes}分钟")
        )
        short_break_btn.pack(side=tk.LEFT)
    
    def _show_settings(self):
        """Shows the settings window."""
        if not self.settings_manager:
            return
            
        try:
            from settings_window import SettingsWindow
            # 只在第一次创建，之后复用
            if not self.settings_window:
                self.settings_window = SettingsWindow(
                    self, 
                    self.settings_manager,
                    self._on_settings_changed
                )
            self.settings_window.show()
        except ImportError:
            messagebox.showerror("错误", "设置窗口模块未找到")
    
    def _on_settings_changed(self, category):
        """Called when settings are changed."""
        if category == "performance":
            # Apply performance settings to timer engine
            if hasattr(self.timer_engine, 'update_check_interval'):
                interval = self.settings_manager.get("performance.check_interval", 1.0)
                self.timer_engine.update_check_interval(interval)
        elif category == "timers":
            # Update timer buttons with new values
            self._create_timer_buttons()
            # Update tray controller menu to reflect new timer durations
            if hasattr(self, 'tray_controller') and self.tray_controller:
                # Force menu recreation by updating the icon menu
                if hasattr(self.tray_controller, 'icon') and self.tray_controller.icon:
                    self.tray_controller.icon.menu = self.tray_controller._create_menu()
        elif category == "notifications":
            # Notification settings are automatically applied through the settings_manager
            # No additional action needed as NotificationManager checks settings on each call
            print("Notification settings updated")
        elif category == "ui":
            # UI settings are applied automatically through the settings checks
            # The _on_window_close method will check the current setting
            print("UI settings updated")
