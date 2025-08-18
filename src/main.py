import threading
import time

from data_manager import DataManager
from timer_engine import TimerEngine
from tray_controller import TrayController
from gui import AppGUI
from notification_manager import NotificationManager
from settings_manager import SettingsManager
from screen_effects import ScreenEffectsManager
from window_manager import WindowManager, WindowManagerError

class Application:
    """The main application class that orchestrates all components."""

    def __init__(self):
        # Order of initialization is important
        self.data_manager = DataManager()
        self.settings_manager = SettingsManager()
        self.notification_manager = NotificationManager(self.settings_manager)
        self.screen_effects = ScreenEffectsManager(self.settings_manager)
        
        # The tray controller needs callbacks to control the GUI and exit.
        self.tray_controller = TrayController(
            show_window_callback=self.show_gui,
            exit_callback=self.on_exit,
            cancel_alarm_callback=self._cancel_alarm,
            timer_engine=None,  # Will be set after timer_engine is created
            settings_manager=self.settings_manager
        )
        
        # The engine needs a callback to trigger the tray notification.
        self.timer_engine = TimerEngine(
            data_manager=self.data_manager,
            trigger_callback=self._on_alarm_triggered
        )
        
        # Set timer_engine reference in tray controller for quick timers
        self.tray_controller.timer_engine = self.timer_engine
        
        # The GUI needs access to the data and engine to manage alarms.
        self.gui = AppGUI(
            data_manager=self.data_manager,
            timer_engine=self.timer_engine,
            settings_manager=self.settings_manager
        )
        
        # Set tray controller reference in GUI for menu updates
        self.gui.tray_controller = self.tray_controller
        
        # Initialize window manager if enabled
        self.window_manager = None
        try:
            if self.settings_manager.get_window_management_setting("enabled", True):
                self.window_manager = WindowManager(self.settings_manager)
                print("Window manager initialized successfully")
                
                # Print real monitor information
                self._print_monitor_info()
            else:
                print("Window management disabled in settings")
        except WindowManagerError as e:
            print(f"Window manager initialization failed: {e}")
            print("Window management features will be unavailable")
        except Exception as e:
            print(f"Unexpected error initializing window manager: {e}")
            print("Window management features will be unavailable")

    def run(self):
        """Starts the application."""
        # Start the timer engine in its own thread
        self.timer_engine.start()

        # Start the tray icon in its own thread so it doesn't block the mainloop
        tray_thread = threading.Thread(target=self.tray_controller.run, daemon=True)
        tray_thread.start()

        # Start window manager if available
        if self.window_manager:
            window_manager_thread = threading.Thread(
                target=self._start_window_manager, 
                daemon=True
            )
            window_manager_thread.start()

        # Start the GUI main loop (this is blocking)
        self.gui.mainloop()

    def show_gui(self):
        """Callback to show the GUI window."""
        self.gui.show_window()
    
    def _on_alarm_triggered(self, alarm):
        """Callback when an alarm or timer is triggered."""
        # Start tray icon flashing
        self.tray_controller.start_flashing(alarm)
        
        # Show screen visual effects first
        try:
            self.screen_effects.show_alarm_effect()
        except Exception as e:
            print(f"Screen effects error: {e}")
        
        # Show system notification after a delay to avoid conflict with screen effects
        alarm_type = alarm.get('type', 'alarm')
        alarm_name = alarm.get('name', 'Unknown')
        
        def show_delayed_notification():
            try:
                if alarm_type == 'countdown':
                    self.notification_manager.show_alarm_notification(alarm_name, 'countdown')
                else:
                    self.notification_manager.show_alarm_notification(alarm_name, 'alarm')
                    
                    # For one-time alarms, automatically remove them after triggering
                    if not alarm.get('days', []):
                        # This is a one-time alarm, schedule it for removal
                        # We don't remove it immediately to allow the user to cancel the flashing
                        # It will be removed when the user cancels or after a timeout
                        print(f"One-time alarm {alarm_name} triggered - will be removed when cancelled")
            except Exception as e:
                print(f"Notification error: {e}")
        
        # Delay notification by 2 seconds to let screen effects show first
        notification_thread = threading.Thread(target=lambda: (time.sleep(2), show_delayed_notification()), daemon=True)
        notification_thread.start()
        
        print(f"Alarm triggered: {alarm_name} (type: {alarm_type})")

    def _start_window_manager(self):
        """Start the window manager in a separate thread."""
        try:
            if self.window_manager and not self.window_manager.start():
                print("Failed to start window manager")
        except Exception as e:
            print(f"Error starting window manager: {e}")

    def on_exit(self):
        """Gracefully stops all components and exits the application."""
        # Stop window manager first
        if self.window_manager:
            try:
                self.window_manager.stop()
                print("Window manager stopped")
            except Exception as e:
                print(f"Error stopping window manager: {e}")
        
        self.timer_engine.stop()
        # The tray_controller is stopped via its own exit menu item.
        # No need to call self.tray_controller.stop() here as it would have been called.
        self.gui.quit()

    def _print_monitor_info(self):
        """Print real monitor information queried from Windows API."""
        if not self.window_manager:
            return
            
        try:
            print("\n=== 显示器配置信息 (真实查询结果) ===")
            monitors = self.window_manager.get_monitors()
            
            for i, monitor in enumerate(monitors):
                # 获取分辨率
                rect = monitor['rect']
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                
                # 获取DPI信息
                dpi = monitor['dpi']
                scale_factor = monitor['scale_factor'][0]
                
                # 获取设备名称和主显示器状态
                device_name = monitor['device_name']
                is_primary = monitor['primary']
                
                print(f"显示器 {i+1}: {device_name}")
                print(f"  分辨率: {width}x{height}")
                print(f"  位置: ({rect[0]}, {rect[1]})")
                print(f"  DPI: {dpi[0]}x{dpi[1]}")
                print(f"  缩放比例: {scale_factor:.2f}x ({int(scale_factor * 100)}%)")
                print(f"  主显示器: {'是' if is_primary else '否'}")
                print(f"  工作区域: {monitor['work_area']}")
                print()
                
            print(f"检测到 {len(monitors)} 个显示器")
            print("=" * 50)
            
        except Exception as e:
            print(f"获取显示器信息失败: {e}")

    def _cancel_alarm(self, alarm):
        """Callback to cancel an alarm."""
        # Stop the flashing
        self.tray_controller.stop_flashing()
        
        # Check if this is a countdown timer
        if alarm.get('type') == 'countdown':
            # This is a countdown timer, remove it from active timers
            self.timer_engine.cancel_countdown_timer(alarm['id'])
            print(f"Countdown timer {alarm.get('name', 'Unknown')} cancelled")
        elif not alarm.get('days', []):
            # This is a one-time alarm, remove it from the list
            self.gui.alarms = [a for a in self.gui.alarms if a['id'] != alarm['id']]
            self.data_manager.save_alarms(self.gui.alarms)
            self.timer_engine.load_and_schedule_alarms()
            self.gui._load_alarms_to_list()
            print(f"One-time alarm {alarm.get('name', 'Unknown')} cancelled and removed")
        else:
            # This is a recurring alarm, just cancel the current occurrence
            print(f"Recurring alarm {alarm.get('name', 'Unknown')} cancelled")

if __name__ == "__main__":
    app = Application()
    app.run()
