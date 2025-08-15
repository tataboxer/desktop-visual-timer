import platform
from typing import Optional

class NotificationManager:
    """Manages system notifications across different platforms."""
    
    def __init__(self, settings_manager=None):
        self.platform = platform.system().lower()
        self.settings_manager = settings_manager
        self._init_notification_system()
    
    def _init_notification_system(self):
        """Initialize the notification system using notify-py."""
        try:
            from notifypy import Notify
            self.notification_backend = Notify()
            self.backend_type = "notifypy"
            print("Using notify-py for notifications")
        except ImportError:
            print("Warning: notify-py not available, notifications will be disabled")
            print("Please install notify-py: pip install notify-py")
            self.notification_backend = None
            self.backend_type = "none"
    
    def show_notification(self, title: str, message: str, timeout: int = 10, app_icon: Optional[str] = None):
        """
        Show a system notification.
        
        Args:
            title: The notification title
            message: The notification message
            timeout: How long to show the notification (seconds)
            app_icon: Path to icon file (optional)
        """
        print(f"DEBUG: Using notification backend: {self.backend_type}")
        
        # Check if notifications are enabled in settings
        if self.settings_manager:
            notifications_enabled = self.settings_manager.get("notifications.enabled", True)
            if not notifications_enabled:
                print(f"Notification disabled by settings: {title} - {message}")
                return
        
        if not self.notification_backend:
            print(f"Notification (fallback): {title} - {message}")
            return
        
        try:
            if self.backend_type == "notifypy":
                # Use notify-py for cross-platform notifications with proper app name
                self.notification_backend.application_name = "牛马生物钟"
                self.notification_backend.title = title
                self.notification_backend.message = message
                
                # Add icon if provided and file exists
                if app_icon:
                    import os
                    if os.path.exists(app_icon):
                        self.notification_backend.icon = app_icon
                
                # Send notification (non-blocking)
                self.notification_backend.send(block=False)
                print(f"Notification sent: {title} - {message} (app_name: 牛马生物钟)")
            else:
                # Fallback if notify-py is not available
                print(f"Notification (fallback): {title} - {message}")
            
        except Exception as e:
            print(f"Failed to show notification: {e}")
            print(f"Notification (fallback): {title} - {message}")
    
    def show_alarm_notification(self, alarm_name: str, alarm_type: str = "alarm"):
        """
        Show a notification for an alarm or timer.
        
        Args:
            alarm_name: Name of the alarm/timer
            alarm_type: Type of alarm ("alarm", "countdown", etc.)
        """
        if alarm_type == "countdown":
            title = "⏰ Timer Finished!"
            message = f"Your {alarm_name} timer has finished."
        else:
            title = "🔔 Alarm!"
            message = f"Alarm: {alarm_name}"
        
        # Use custom notification icon
        import os
        icon_path = os.path.join("assets", "notification.png")
        if not os.path.exists(icon_path):
            # Fallback to absolute path if relative doesn't work
            icon_path = os.path.abspath(icon_path)
        
        self.show_notification(title, message, timeout=15, app_icon=icon_path)
    
    def is_available(self) -> bool:
        """Check if notifications are available on this system."""
        return self.notification_backend is not None