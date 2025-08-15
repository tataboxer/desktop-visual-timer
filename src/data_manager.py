import json
import os
from typing import List, Dict, Any

class DataManager:
    """Handles reading and writing alarm data from/to a JSON file."""

    def __init__(self, file_path: str = "alarms.json"):
        """
        Initializes the DataManager.

        Args:
            file_path (str): The path to the JSON file where alarms are stored.
        """
        self.file_path = file_path

    def load_alarms(self) -> List[Dict[str, Any]]:
        """
        Loads alarms from the JSON file.

        Returns:
            A list of alarm dictionaries. Returns an empty list if the file
            doesn't exist or is empty.
        """
        if not os.path.exists(self.file_path):
            return []
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []

    def save_alarms(self, alarms: List[Dict[str, Any]]) -> None:
        """
        Saves a list of alarms to the JSON file.

        Args:
            alarms: A list of alarm dictionaries to save.
        """
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(alarms, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving alarms to {self.file_path}: {e}")

