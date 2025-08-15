import threading

from data_manager import DataManager
from timer_engine import TimerEngine
from tray_controller import TrayController
from gui import AppGUI
from notification_manager import NotificationManager
from settings_manager import SettingsManager
from screen_effects import ScreenEffectsManager

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

    def run(self):
        """Starts the application."""
        # Start the timer engine in its own thread
        self.timer_engine.start()

        # Start the tray icon in its own thread so it doesn't block the mainloop
        tray_thread = threading.Thread(target=self.tray_controller.run, daemon=True)
        tray_thread.start()

        # Start the GUI main loop (this is blocking)
        self.gui.mainloop()

    def show_gui(self):
        """Callback to show the GUI window."""
        self.gui.show_window()
    
    def _on_alarm_triggered(self, alarm):
        """Callback when an alarm or timer is triggered."""
        # Start tray icon flashing
        self.tray_controller.start_flashing(alarm)
        
        # Show screen visual effects
        try:
            self.screen_effects.show_alarm_effect()
        except Exception as e:
            print(f"Screen effects error: {e}")
        
        # Show system notification
        alarm_type = alarm.get('type', 'alarm')
        alarm_name = alarm.get('name', 'Unknown')
        
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
        
        print(f"Alarm triggered: {alarm_name} (type: {alarm_type})")

    def on_exit(self):
        """Gracefully stops all components and exits the application."""
        self.timer_engine.stop()
        # The tray_controller is stopped via its own exit menu item.
        # No need to call self.tray_controller.stop() here as it would have been called.
        self.gui.quit()

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
