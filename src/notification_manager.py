import platform
from typing import Optional

class NotificationManager:
    """Manages system notifications across different platforms."""
    
    def __init__(self, settings_manager=None):
        self.platform = platform.system().lower()
        self.settings_manager = settings_manager
        self._init_notification_system()
    
    def _init_notification_system(self):
        """Initialize the appropriate notification system for the current platform."""
        try:
            if self.platform == "windows":
                # Try to use plyer for cross-platform notifications
                from plyer import notification
                self.notification_backend = notification
                self.backend_type = "plyer"
            else:
                # For non-Windows platforms, also use plyer
                from plyer import notification
                self.notification_backend = notification
                self.backend_type = "plyer"
        except ImportError:
            print("Warning: plyer not available, notifications will be disabled")
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
            if self.backend_type == "plyer":
                # Use plyer for cross-platform notifications
                kwargs = {
                    'title': title,
                    'message': message,
                    'timeout': timeout
                }
                
                # Add icon if provided and file exists
                if app_icon:
                    import os
                    if os.path.exists(app_icon):
                        kwargs['app_icon'] = app_icon
                
                self.notification_backend.notify(**kwargs)
                print(f"Notification sent: {title} - {message} (timeout: {timeout}s)")
            
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
        
        # Don't use icon for now to avoid path issues
        # The notification will work without icon
        self.show_notification(title, message, timeout=15, app_icon=None)
    
    def is_available(self) -> bool:
        """Check if notifications are available on this system."""
        return self.notification_backend is not None