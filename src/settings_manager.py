import json
import os
from typing import Dict, Any

class SettingsManager:
    """Manages application settings and preferences."""
    
    def __init__(self, file_path: str = "settings.json"):
        """
        Initializes the SettingsManager.
        
        Args:
            file_path (str): The path to the JSON file where settings are stored.
        """
        self.file_path = file_path
        self.default_settings = {
            "notifications": {
                "enabled": True,
                "sound_enabled": False
            },
            "ui": {
                "theme": "light",
                "minimize_to_tray": True,
                "start_minimized": False,
                "auto_start": False
            },
            "timers": {
                "default_pomodoro": 25,
                "default_short_break": 5,
                "default_long_break": 15,
                "auto_start_breaks": False
            },
            "performance": {
                "check_interval": 1.0,  # seconds
                "low_power_mode": False
            },
            "visual_effects": {
                "enabled": True,
                "type": "border_flash",  # border_flash, screen_flash
                "duration": 5.0,  # seconds
                "intensity": "medium"  # low, medium, high
            }
        }
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Loads settings from the JSON file.
        
        Returns:
            A dictionary of settings. Returns default settings if the file
            doesn't exist or is corrupted.
        """
        if not os.path.exists(self.file_path):
            return self.default_settings.copy()
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged_settings = self.default_settings.copy()
                self._deep_update(merged_settings, loaded_settings)
                return merged_settings
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Could not load settings from {self.file_path}, using defaults")
            return self.default_settings.copy()
    
    def save_settings(self) -> None:
        """Saves the current settings to the JSON file."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving settings to {self.file_path}: {e}")
    
    def get(self, key_path: str, default=None):
        """
        Gets a setting value using dot notation.
        
        Args:
            key_path: Dot-separated path to the setting (e.g., "ui.theme")
            default: Default value if key doesn't exist
            
        Returns:
            The setting value or default
        """
        keys = key_path.split('.')
        value = self.settings
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Sets a setting value using dot notation.
        
        Args:
            key_path: Dot-separated path to the setting (e.g., "ui.theme")
            value: Value to set
        """
        keys = key_path.split('.')
        setting_dict = self.settings
        
        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in setting_dict:
                setting_dict[key] = {}
            setting_dict = setting_dict[key]
        
        # Set the final value
        setting_dict[keys[-1]] = value
        self.save_settings()
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """Recursively updates base_dict with values from update_dict."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def reset_to_defaults(self) -> None:
        """Resets all settings to default values."""
        self.settings = self.default_settings.copy()
        self.save_settings()