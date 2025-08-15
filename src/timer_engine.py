import schedule
import time
import threading
from typing import Callable, List, Dict, Any
from datetime import datetime, timedelta

from data_manager import DataManager

class TimerEngine:
    """Runs in a separate thread to manage and trigger scheduled alarms."""

    def __init__(self, data_manager: DataManager, trigger_callback: Callable[[Dict[str, Any]], None]):
        """
        Initializes the TimerEngine.

        Args:
            data_manager: An instance of DataManager to load alarms.
            trigger_callback: A function to call when an alarm is triggered.
                              It receives the alarm dictionary as an argument.
        """
        self.data_manager = data_manager
        self.trigger_callback = trigger_callback
        self.running = False
        self.thread = None
        self.schedule = schedule
        
        # Countdown timer support
        self.countdown_timers = {}  # Dict to track active countdown timers
        self.countdown_lock = threading.Lock()
        
        # Second-level alarm tracking
        self.second_level_alarms = []  # Alarms that need second-level precision
        self.triggered_alarms = set()  # Track already triggered alarms to avoid duplicates
        
        # Performance settings
        self.check_interval = 1.0  # Default check interval in seconds

    def _run_scheduler(self):
        """The main loop for the scheduler thread."""
        self.running = True
        while self.running:
            # Check both schedule library and our custom second-level alarms
            self.schedule.run_pending()
            self._check_second_level_alarms()
            time.sleep(self.check_interval)

    def start(self):
        """Starts the scheduler thread."""
        if self.running:
            return
        
        self.load_and_schedule_alarms()
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops the scheduler thread."""
        self.running = False
        # No need to join daemon thread

    def _create_job(self, alarm: Dict[str, Any]):
        """Creates a schedule job for a single alarm."""
        if not alarm.get('is_active', False):
            return

        # Check if alarm has seconds specified
        alarm_second = alarm.get('second', 0)
        
        if alarm_second > 0:
            # Use our custom second-level checking for precise timing
            self.second_level_alarms.append(alarm)
            print(f"Added second-level alarm: {alarm['name']} at {alarm.get('hour', 0):02d}:{alarm.get('minute', 0):02d}:{alarm_second:02d}")
        else:
            # Use schedule library for minute-level precision
            job_time = f"{alarm.get('hour', 0):02d}:{alarm.get('minute', 0):02d}"
            days = alarm.get('days', [])
            
            job = None
            if not days: # One-time alarm
                job = self.schedule.every().day.at(job_time)
            else: # Recurring alarm
                for day in days:
                    if hasattr(self.schedule.every(), day.lower()):
                        job = getattr(self.schedule.every(), day.lower()).at(job_time)

            if job:
                # Use a lambda to pass the alarm object to the callback
                job.do(self.trigger_callback, alarm)
    
    def _check_second_level_alarms(self):
        """Check and trigger alarms that require second-level precision."""
        now = datetime.now()
        current_time_key = f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
        current_day = now.strftime('%a').lower()
        
        for alarm in self.second_level_alarms[:]:  # Create a copy to iterate safely
            if not alarm.get('is_active', False):
                continue
                
            alarm_time_key = f"{alarm.get('hour', 0):02d}:{alarm.get('minute', 0):02d}:{alarm.get('second', 0):02d}"
            alarm_id = alarm.get('id', '')
            
            # Create unique trigger key to avoid duplicate triggers
            trigger_key = f"{alarm_id}_{current_time_key}"
            
            if alarm_time_key == current_time_key and trigger_key not in self.triggered_alarms:
                days = alarm.get('days', [])
                should_trigger = False
                
                if not days:
                    # One-time alarm
                    should_trigger = True
                    # Remove from second_level_alarms after triggering
                    self.second_level_alarms.remove(alarm)
                else:
                    # Recurring alarm - check if today matches
                    if current_day in [d.lower() for d in days]:
                        should_trigger = True
                
                if should_trigger:
                    self.triggered_alarms.add(trigger_key)
                    self.trigger_callback(alarm)
                    print(f"Triggered second-level alarm: {alarm['name']} at {current_time_key}")
        
        # Clean up old triggered alarms (keep only current minute to avoid memory buildup)
        current_minute_prefix = f"{now.hour:02d}:{now.minute:02d}:"
        self.triggered_alarms = {key for key in self.triggered_alarms if key.split('_')[1].startswith(current_minute_prefix)}

    def load_and_schedule_alarms(self):
        """Loads all alarms from the data manager and schedules them."""
        self.schedule.clear()
        self.second_level_alarms.clear()  # Clear second-level alarms
        self.triggered_alarms.clear()     # Clear triggered alarms tracking
        
        alarms = self.data_manager.load_alarms()
        for alarm in alarms:
            self._create_job(alarm)
    
    def start_countdown_timer(self, minutes: int, name: str = None) -> str:
        """
        Starts a countdown timer for the specified number of minutes.
        
        Args:
            minutes: Number of minutes for the countdown
            name: Optional name for the timer
            
        Returns:
            timer_id: Unique identifier for the timer
        """
        import uuid
        timer_id = str(uuid.uuid4())
        
        if name is None:
            name = f"{minutes} Minute Timer"
        
        # Create timer data
        timer_data = {
            'id': timer_id,
            'name': name,
            'minutes': minutes,
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(minutes=minutes),
            'type': 'countdown'
        }
        
        with self.countdown_lock:
            self.countdown_timers[timer_id] = timer_data
        
        # Start the countdown thread
        countdown_thread = threading.Thread(
            target=self._run_countdown, 
            args=(timer_id, minutes * 60), 
            daemon=True
        )
        countdown_thread.start()
        
        print(f"Started {minutes}-minute countdown timer: {name}")
        return timer_id
    
    def _run_countdown(self, timer_id: str, total_seconds: int):
        """Runs a countdown timer in a separate thread."""
        remaining = total_seconds
        
        while remaining > 0 and self.running:
            time.sleep(1)
            remaining -= 1
            
            # Check if timer was cancelled
            with self.countdown_lock:
                if timer_id not in self.countdown_timers:
                    return
        
        # Timer finished
        with self.countdown_lock:
            if timer_id in self.countdown_timers:
                timer_data = self.countdown_timers[timer_id]
                # Trigger the callback
                self.trigger_callback(timer_data)
                # Remove the timer
                del self.countdown_timers[timer_id]
    
    def cancel_countdown_timer(self, timer_id: str):
        """Cancels a running countdown timer."""
        with self.countdown_lock:
            if timer_id in self.countdown_timers:
                del self.countdown_timers[timer_id]
                print(f"Cancelled countdown timer: {timer_id}")
    
    def get_active_countdown_timers(self) -> Dict[str, Dict]:
        """Returns a copy of currently active countdown timers."""
        with self.countdown_lock:
            return self.countdown_timers.copy()
    
    def get_countdown_timer_remaining(self, timer_id: str) -> int:
        """Returns remaining seconds for a countdown timer, or -1 if not found."""
        with self.countdown_lock:
            if timer_id in self.countdown_timers:
                timer_data = self.countdown_timers[timer_id]
                now = datetime.now()
                remaining = (timer_data['end_time'] - now).total_seconds()
                return max(0, int(remaining))
        return -1
    
    def update_check_interval(self, interval: float):
        """
        Updates the check interval for performance optimization.
        
        Args:
            interval: New check interval in seconds
        """
        self.check_interval = max(0.1, min(5.0, interval))  # Clamp between 0.1 and 5.0 seconds
        print(f"Timer engine check interval updated to {self.check_interval} seconds")
