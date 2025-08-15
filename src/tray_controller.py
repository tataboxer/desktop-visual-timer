import pystray
from PIL import Image, UnidentifiedImageError
import threading
import time
from typing import Callable

class TrayController:
    """Manages the system tray icon and its interactions."""

    def __init__(self, show_window_callback: Callable, exit_callback: Callable, cancel_alarm_callback: Callable = None, timer_engine = None, settings_manager = None):
        """
        Initializes the TrayController.

        Args:
            show_window_callback: Function to call to show the main GUI window.
            exit_callback: Function to call when exiting the application.
            cancel_alarm_callback: Function to call when cancelling an alarm.
            timer_engine: Reference to timer engine for quick timers.
            settings_manager: Reference to settings manager for timer durations.
        """
        self.show_window_callback = show_window_callback
        self.exit_callback = exit_callback
        self.cancel_alarm_callback = cancel_alarm_callback
        self.timer_engine = timer_engine
        self.settings_manager = settings_manager

        self.icon = None
        self.flashing_thread = None
        self.is_flashing = False
        self.current_alarm = None  # To keep track of the currently flashing alarm
        

        # Load icons
        try:
            import os
            # Get the directory of the current script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to the project root
            project_root = os.path.dirname(current_dir)
            
            # 使用64x64图标 - 这是系统托盘的最佳实践
            icon_path = os.path.join(project_root, "assets", "icon_64.png")
            icon_alert_path = os.path.join(project_root, "assets", "icon_alert_64.png")
            
            if os.path.exists(icon_path) and os.path.exists(icon_alert_path):
                self.icon_default = Image.open(icon_path)
                self.icon_alert = Image.open(icon_alert_path)
                print("✅ 使用64x64图标 - 系统托盘标准尺寸")
            else:
                raise FileNotFoundError("找不到64x64图标文件")
                
        except (FileNotFoundError, UnidentifiedImageError) as e:
            # Create dummy images if files are not found or are invalid
            print(f"注意: 无法加载图标文件 ({e})。创建临时彩色图标。")
            self.icon_default = Image.new('RGB', (64, 64), color = 'blue')
            self.icon_alert = Image.new('RGB', (64, 64), color = 'red')


    def _show_and_stop_flashing(self):
        """Shows the window and stops the flashing."""
        if self.is_flashing:
            self.stop_flashing()
        self.show_window_callback()

    def _cancel_alarm(self):
        """Cancels the currently flashing alarm."""
        if self.is_flashing:
            self.stop_flashing()
        # Call the cancel alarm callback if provided
        if self.cancel_alarm_callback and self.current_alarm:
            self.cancel_alarm_callback(self.current_alarm)
        print("Alarm cancelled")
    
    def _start_quick_timer(self, minutes: int, name: str):
        """Starts a quick countdown timer from the tray menu."""
        if self.timer_engine:
            self.timer_engine.start_countdown_timer(minutes, name)
            print(f"Started {name} for {minutes} minutes from tray menu")

    def _create_menu(self):
        """Creates the menu for the tray icon."""
        if self.is_flashing:
            # When an alarm is flashing, make "Cancel Alarm" the default action
            return pystray.Menu(
                pystray.MenuItem("Cancel Alarm", self._cancel_alarm, default=True),
                pystray.MenuItem("Show", self._show_and_stop_flashing),
                pystray.MenuItem("Exit", self._on_exit)
            )
        else:
            # Normal menu when no alarm is flashing
            # Get timer durations from settings
            if self.settings_manager:
                pomodoro_minutes = self.settings_manager.get("timers.default_pomodoro", 25)
                long_break_minutes = self.settings_manager.get("timers.default_long_break", 15)
                short_break_minutes = self.settings_manager.get("timers.default_short_break", 5)
            else:
                # Fallback to defaults
                pomodoro_minutes = 25
                long_break_minutes = 15
                short_break_minutes = 5
            
            quick_timer_menu = pystray.Menu(
                pystray.MenuItem(f"🍅 Focus {pomodoro_minutes} min", lambda: self._start_quick_timer(pomodoro_minutes, "Pomodoro Focus")),
                pystray.MenuItem(f"🚶 Break {long_break_minutes} min", lambda: self._start_quick_timer(long_break_minutes, "Long Break")),
                pystray.MenuItem(f"☕ Break {short_break_minutes} min", lambda: self._start_quick_timer(short_break_minutes, "Short Break"))
            )
            
            return pystray.Menu(
                pystray.MenuItem("Show/Hide Window", self._show_and_stop_flashing, default=True),
                pystray.MenuItem("Quick Timers", quick_timer_menu),
                pystray.MenuItem("Exit", self._on_exit)
            )

    def _on_exit(self):
        """Handles the exit action from the menu."""
        self.stop()
        self.exit_callback()

    def run(self):
        """Creates and runs the system tray icon. This is a blocking call."""
        self.icon = pystray.Icon(
            "DesktopVisualTimer",
            self.icon_default,
            "Desktop Visual Timer",
            self._create_menu()
        )
        # pystray uses default menu items for left-click actions
        # No need to set click handlers - they don't exist in pystray API
        self.icon.run()

    def stop(self):
        """Stops the system tray icon."""
        if self.is_flashing:
            self.stop_flashing()
        
        if self.icon:
            self.icon.stop()

    def _flash_icon(self):
        """The loop that handles the icon flashing animation."""
        while self.is_flashing:
            self.icon.icon = self.icon_alert
            time.sleep(0.5)
            if not self.is_flashing:
                break
            self.icon.icon = self.icon_default
            time.sleep(0.5)
        # Restore default icon when stopping
        self.icon.icon = self.icon_default

    def start_flashing(self, alarm: dict = None):
        """Starts the icon flashing in a separate thread."""
        if self.is_flashing:
            return
        self.is_flashing = True
        self.current_alarm = alarm  # Save the current alarm
        # Update the menu to show cancel option
        if self.icon:
            self.icon.menu = self._create_menu()
        self.flashing_thread = threading.Thread(target=self._flash_icon, daemon=True)
        self.flashing_thread.start()

    def stop_flashing(self):
        """Stops the icon flashing."""
        self.is_flashing = False
        # Update the menu to remove cancel option
        if self.icon:
            self.icon.menu = self._create_menu()
        # The thread will stop on its own after the next cycle
