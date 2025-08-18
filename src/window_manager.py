"""
Window Manager Module for Cross-Monitor Window Movement

This module provides functionality to move windows between monitors using global hotkeys.
It integrates with the existing settings system and runs as a background service.
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
import traceback

try:
    import win32gui
    import win32api
    import win32con
    import win32process
    import ctypes
    from ctypes import wintypes
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    print("Warning: pywin32 not available. Window management features will be disabled.")

try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("Warning: pynput not available. Hotkey functionality will be disabled.")


class WindowManagerError(Exception):
    """Base exception for window manager errors."""
    pass


class HotkeyConflictError(WindowManagerError):
    """Exception raised when hotkey conflicts are detected."""
    pass


class DisplayConfigError(WindowManagerError):
    """Exception raised when display configuration issues occur."""
    pass


class WindowManager:
    """
    Manages window movement between monitors using global hotkeys.
    
    This class provides the core functionality for detecting monitors,
    capturing active windows, and moving them between displays.
    """
    
    def __init__(self, settings_manager):
        """
        Initialize the WindowManager.
        
        Args:
            settings_manager: Instance of SettingsManager for configuration
        """
        self.settings_manager = settings_manager
        self.is_running = False
        self.hotkey_listener = None
        self.monitors_cache = None
        self.cache_timestamp = 0
        self.cache_duration = 5.0  # Cache monitors info for 5 seconds
        
        # Setup logging
        self.logger = self._setup_logger()
        
        # Check dependencies
        if not PYWIN32_AVAILABLE:
            raise WindowManagerError("pywin32 is required for window management functionality")
        
        if not PYNPUT_AVAILABLE:
            raise WindowManagerError("pynput is required for hotkey functionality")
        
        # Setup DPI awareness
        self._setup_dpi_awareness()
        
        self._log_important("WindowManager initialized successfully")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for window manager."""
        logger = logging.getLogger('WindowManager')
        
        # Only add handler if not already present
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        # Set log level based on debug mode
        debug_mode = self.settings_manager.get_window_management_setting("debug_mode", False)
        logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        
        return logger
    
    def _log_important(self, message: str):
        """Log important messages that should always be shown, regardless of debug mode."""
        # Always print important messages to console
        print(f"WindowManager: {message}")
        # Also log at INFO level for debug mode
        if self.settings_manager.get_window_management_setting("debug_mode", False):
            self.logger.info(message)
    
    def _setup_dpi_awareness(self):
        """Setup DPI awareness for the application."""
        try:
            # Note: DPI awareness should be set early in the process, ideally before any windows are created
            # Since we're setting it after the main window exists, it might not take full effect
            self.logger.debug("Setting up DPI awareness (note: may be too late in process lifecycle)")
            
            # Check current DPI awareness
            try:
                current_process = ctypes.windll.kernel32.GetCurrentProcess()
                awareness = ctypes.windll.shcore.GetProcessDpiAwareness(current_process)
                awareness_names = {0: "DPI_UNAWARE", 1: "SYSTEM_DPI_AWARE", 2: "PER_MONITOR_DPI_AWARE"}
                self.logger.debug(f"Current DPI awareness: {awareness} ({awareness_names.get(awareness, 'UNKNOWN')})")
            except Exception as e:
                self.logger.debug(f"Could not get current DPI awareness: {e}")
            
            # Since we're late in the process, let's try to work with what we have
            # and focus on better DPI detection rather than changing awareness
            self.logger.debug("Skipping DPI awareness change - focusing on better DPI detection")
                
        except Exception as e:
            self.logger.warning(f"DPI awareness setup failed: {e}")
    
    def _get_dpi_for_monitor(self, hmonitor) -> Tuple[int, int]:
        """Get DPI for a specific monitor using Windows API."""
        
        try:
            # 方法1: 尝试使用 GetDpiForMonitor API (Windows 8.1+)
            try:
                # 定义常量
                MDT_EFFECTIVE_DPI = 0
                
                # 定义ctypes结构
                dpi_x = ctypes.c_uint()
                dpi_y = ctypes.c_uint()
                
                # 调用GetDpiForMonitor
                result = ctypes.windll.shcore.GetDpiForMonitor(
                    hmonitor, MDT_EFFECTIVE_DPI, 
                    ctypes.byref(dpi_x), ctypes.byref(dpi_y)
                )
                
                if result == 0:  # S_OK
                    actual_dpi_x = dpi_x.value
                    actual_dpi_y = dpi_y.value
                    self.logger.debug(f"Real DPI detected via GetDpiForMonitor: {actual_dpi_x}x{actual_dpi_y}")
                    return (actual_dpi_x, actual_dpi_y)
                else:
                    self.logger.debug(f"GetDpiForMonitor failed with result: {result}")
                    
            except Exception as e:
                self.logger.debug(f"GetDpiForMonitor API call failed: {e}")
            
            # 方法2: 尝试使用设备上下文获取DPI
            try:
                monitor_info = win32api.GetMonitorInfo(hmonitor)
                device_name = monitor_info['Device']
                
                # 创建设备上下文
                hdc = win32gui.CreateDC(device_name, None, None, None)
                if hdc:
                    try:
                        # 获取逻辑像素密度
                        dpi_x = win32gui.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                        dpi_y = win32gui.GetDeviceCaps(hdc, 90)  # LOGPIXELSY
                        
                        if dpi_x > 0 and dpi_y > 0:
                            self.logger.debug(f"Real DPI detected via device context for {device_name}: {dpi_x}x{dpi_y}")
                            return (dpi_x, dpi_y)
                    finally:
                        win32gui.DeleteDC(hdc)
                        
            except Exception as e:
                self.logger.debug(f"Device context DPI detection failed: {e}")
            
            # 方法3: 启发式检测（改进版，更保守）
            try:
                monitor_info = win32api.GetMonitorInfo(hmonitor)
                device_name = monitor_info['Device']
                monitor_rect = monitor_info['Monitor']
                width = monitor_rect[2] - monitor_rect[0]
                height = monitor_rect[3] - monitor_rect[1]
                
                # 更保守的启发式检测，优先假设100%缩放
                if width == 2560 and height == 1440:
                    # 2560x1440通常是100%缩放，除非是小屏幕
                    estimated_dpi = 96  # 默认100%缩放
                    self.logger.debug(f"2560x1440 detected for {device_name}, assuming 100% scaling: {estimated_dpi} DPI")
                elif width == 1920 and height == 1080:
                    # 1920x1080通常是100%缩放
                    estimated_dpi = 96
                    self.logger.debug(f"1920x1080 detected for {device_name}, assuming 100% scaling: {estimated_dpi} DPI")
                elif width < 1600 and height < 1000:
                    # 小分辨率可能是高DPI缩放的结果
                    estimated_dpi = 168  # 175% scaling
                    self.logger.debug(f"Small resolution detected for {device_name}: {width}x{height}, assuming 175% scaling: {estimated_dpi} DPI")
                elif width == 3440 and height == 1440:
                    # 超宽屏通常是100%缩放
                    estimated_dpi = 96
                    self.logger.debug(f"Ultrawide detected for {device_name}: {width}x{height}, assuming 100% scaling: {estimated_dpi} DPI")
                else:
                    # 其他情况默认100%缩放
                    estimated_dpi = 96
                    self.logger.debug(f"Unknown resolution for {device_name}: {width}x{height}, defaulting to 100% scaling: {estimated_dpi} DPI")
                
                return (estimated_dpi, estimated_dpi)
                
            except Exception as e:
                self.logger.debug(f"Heuristic DPI estimation failed: {e}")
                
        except Exception as e:
            self.logger.debug(f"All DPI detection methods failed: {e}")
            
        # 最终回退：100%缩放
        self.logger.debug("Using ultimate fallback DPI: 96x96 (100% scaling)")
        return (96, 96)
    
    def _get_physical_monitor_info(self, monitor: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Try to get physical monitor information including real resolution."""
        try:
            device_name = monitor['device_name']
            logical_rect = monitor['rect']
            dpi = monitor['dpi']
            scale_factor = monitor['scale_factor'][0]  # Use X scale factor
            
            # Calculate estimated physical resolution
            logical_width = logical_rect[2] - logical_rect[0]
            logical_height = logical_rect[3] - logical_rect[1]
            
            # If we have a scale factor > 1, the physical resolution is likely higher
            if scale_factor > 1.0:
                estimated_physical_width = int(logical_width * scale_factor)
                estimated_physical_height = int(logical_height * scale_factor)
            else:
                estimated_physical_width = logical_width
                estimated_physical_height = logical_height
            
            physical_info = {
                'device_name': device_name,
                'logical_resolution': f"{logical_width}x{logical_height}",
                'estimated_physical_resolution': f"{estimated_physical_width}x{estimated_physical_height}",
                'scale_factor': f"{scale_factor:.2f}x",  # Use 2 decimal places to show 1.75 correctly
                'dpi': f"{dpi[0]}",
                'scaling_percentage': f"{int(scale_factor * 100)}%"
            }
            
            return physical_info
            
        except Exception as e:
            self.logger.debug(f"Failed to get physical monitor info: {e}")
            return None
    
    def _scale_rect_for_dpi(self, rect: Tuple[int, int, int, int], 
                           from_dpi: Tuple[int, int], 
                           to_dpi: Tuple[int, int]) -> Tuple[int, int, int, int]:
        """Scale a rectangle from one DPI to another."""
        if from_dpi == to_dpi:
            return rect
        
        x, y, right, bottom = rect
        width = right - x
        height = bottom - y
        
        # Calculate scaling factors
        scale_x = to_dpi[0] / from_dpi[0]
        scale_y = to_dpi[1] / from_dpi[1]
        
        # Scale the rectangle
        new_width = int(width * scale_x)
        new_height = int(height * scale_y)
        
        return (x, y, x + new_width, y + new_height)
    
    def start(self) -> bool:
        """
        Start the window manager and hotkey listener.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning("WindowManager is already running")
            return True
        
        # Check if window management is enabled
        if not self.settings_manager.get_window_management_setting("enabled", True):
            self.logger.info("Window management is disabled in settings")
            return False
        
        # Check for multi-monitor setup
        if not self.is_multi_monitor_setup():
            self.logger.warning("Single monitor detected. Window management functionality limited.")
            # Still start in case monitors are added later
        
        try:
            # Start hotkey listener
            if self._start_hotkey_listener():
                self.is_running = True
                self._log_important("WindowManager started successfully")
                return True
            else:
                self.logger.error("Failed to start hotkey listener")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start WindowManager: {e}")
            self.logger.debug(traceback.format_exc())
            return False
    
    def stop(self) -> None:
        """Stop the window manager and cleanup resources."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop hotkey listener
        self._stop_hotkey_listener()
        
        # Clear cache
        self.monitors_cache = None
        
        self.logger.info("WindowManager stopped")
    
    def get_monitors(self) -> List[Dict[str, Any]]:
        """
        Get information about all connected monitors.
        
        Returns:
            List of monitor dictionaries with keys:
            - index: Monitor index
            - rect: (x, y, width, height) of monitor
            - work_area: (x, y, width, height) of work area
            - primary: Whether this is the primary monitor
            - device_name: Monitor device name
        """
        current_time = time.time()
        
        # Return cached data if still valid
        if (self.monitors_cache and 
            current_time - self.cache_timestamp < self.cache_duration):
            return self.monitors_cache
        
        monitors = []
        
        try:
            # Enumerate all monitors - EnumDisplayMonitors returns a list directly
            # Each item in the list is a tuple: (hMonitor, hdcMonitor, PyRECT)
            monitor_list = win32api.EnumDisplayMonitors(None, None)
            
            # Process each monitor
            for index, (hmonitor, hdc, rect) in enumerate(monitor_list):
                try:
                    # Get monitor info
                    monitor_info = win32api.GetMonitorInfo(hmonitor)
                    
                    # Get DPI for this monitor
                    dpi_x, dpi_y = self._get_dpi_for_monitor(hmonitor)
                    
                    monitor_data = {
                        'index': index,
                        'handle': hmonitor,
                        'rect': rect,
                        'work_area': monitor_info['Work'],
                        'primary': monitor_info['Flags'] == win32con.MONITORINFOF_PRIMARY,
                        'device_name': monitor_info['Device'],
                        'dpi': (dpi_x, dpi_y),
                        'scale_factor': (dpi_x / 96.0, dpi_y / 96.0)  # 96 DPI is 100% scaling
                    }
                    
                    monitors.append(monitor_data)
                    
                except Exception as e:
                    self.logger.error(f"Error processing monitor {index}: {e}")
            
            # Sort by index to ensure consistent ordering
            monitors.sort(key=lambda m: m['index'])
            
            # Update cache
            self.monitors_cache = monitors
            self.cache_timestamp = current_time
            
            self.logger.debug(f"Found {len(monitors)} monitors")
            for monitor in monitors:
                scale = monitor['scale_factor'][0]
                self.logger.debug(f"Monitor {monitor['index']}: {monitor['dpi'][0]} DPI ({int(scale*100)}% scaling)")
            
        except Exception as e:
            self.logger.error(f"Failed to enumerate monitors: {e}")
            return []
        
        return monitors
    
    def get_current_window(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently active window.
        
        Returns:
            Dictionary with window information or None if no window found:
            - hwnd: Window handle
            - rect: (x, y, width, height) of window
            - title: Window title
            - class_name: Window class name
            - is_maximized: Whether window is maximized
            - is_minimized: Whether window is minimized
            - process_name: Name of the process owning the window
        """
        try:
            # Get foreground window
            hwnd = win32gui.GetForegroundWindow()
            
            if not hwnd or not win32gui.IsWindow(hwnd):
                self.logger.debug("No valid foreground window found")
                return None
            
            # Get window rectangle
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception as e:
                self.logger.debug(f"Failed to get window rect: {e}")
                return None
            
            # Get window title
            try:
                title = win32gui.GetWindowText(hwnd)
            except Exception:
                title = ""
            
            # Get window class name
            try:
                class_name = win32gui.GetClassName(hwnd)
            except Exception:
                class_name = ""
            
            # Check window state
            placement = win32gui.GetWindowPlacement(hwnd)
            is_maximized = placement[1] == win32con.SW_SHOWMAXIMIZED
            is_minimized = placement[1] == win32con.SW_SHOWMINIMIZED
            
            # Debug window state
            state_names = {
                1: "SW_HIDE",
                2: "SW_SHOWMINIMIZED", 
                3: "SW_SHOWMAXIMIZED",
                4: "SW_SHOWNOACTIVATE",
                5: "SW_SHOW",
                6: "SW_MINIMIZE",
                7: "SW_SHOWMINNOACTIVE",
                8: "SW_SHOWNA",
                9: "SW_RESTORE",
                10: "SW_SHOWDEFAULT"
            }
            state_name = state_names.get(placement[1], f"UNKNOWN({placement[1]})")
            self.logger.debug(f"Window state: {state_name}, is_maximized={is_maximized}, is_minimized={is_minimized}")
            
            # Get process name
            process_name = ""
            try:
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                process_handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, process_id)
                process_name = win32process.GetModuleFileNameEx(process_handle, 0).split('\\')[-1]
                win32api.CloseHandle(process_handle)
            except Exception:
                pass
            
            window_info = {
                'hwnd': hwnd,
                'rect': rect,
                'title': title,
                'class_name': class_name,
                'is_maximized': is_maximized,
                'is_minimized': is_minimized,
                'process_name': process_name
            }
            
            self.logger.debug(f"Current window: {title} ({class_name}) - {rect}")
            
            return window_info
            
        except Exception as e:
            self.logger.error(f"Failed to get current window: {e}")
            return None
    
    def calculate_target_position(self, window_rect: Tuple[int, int, int, int], 
                                current_monitor: Dict[str, Any], 
                                target_monitor: Dict[str, Any]) -> Tuple[int, int, int, int]:
        """
        Calculate the target position and size for a window on the target monitor.
        Uses relative positioning strategy for optimal user experience.
        
        Args:
            window_rect: Current window rectangle (x, y, right, bottom)
            current_monitor: Current monitor information
            target_monitor: Target monitor information
            
        Returns:
            New window rectangle (x, y, width, height) - note: width/height, not right/bottom
        """
        x, y, right, bottom = window_rect
        original_width = right - x
        original_height = bottom - y
        
        # Get DPI scaling factors
        current_dpi = current_monitor.get('dpi', (96, 96))
        target_dpi = target_monitor.get('dpi', (96, 96))
        
        # Use physical work areas for consistent relative calculations
        # Convert logical work areas to physical dimensions using DPI scaling
        current_work_area = current_monitor['work_area']
        current_scale = current_monitor['scale_factor'][0]  # X scale factor
        current_x, current_y, current_right, current_bottom = current_work_area
        
        # Calculate physical work area for current monitor
        current_physical_width = int((current_right - current_x) * current_scale)
        current_physical_height = int((current_bottom - current_y) * current_scale)
        
        target_work_area = target_monitor['work_area']
        target_scale = target_monitor['scale_factor'][0]  # X scale factor
        target_x, target_y, target_right, target_bottom = target_work_area
        
        # Calculate physical work area for target monitor
        target_physical_width = int((target_right - target_x) * target_scale)
        target_physical_height = int((target_bottom - target_y) * target_scale)
        
        # Calculate logical dimensions for positioning
        current_logical_width = current_right - current_x
        current_logical_height = current_bottom - current_y
        target_width = target_right - target_x
        target_height = target_bottom - target_y
        
        self.logger.debug(f"Current work area: {current_work_area}, logical size: {current_logical_width}x{current_logical_height}")
        self.logger.debug(f"Target work area: {target_work_area}, logical size: {target_width}x{target_height}")
        
        # Calculate window's relative size using PHYSICAL dimensions for consistency
        # First convert window size from logical to physical pixels for current monitor
        window_physical_width = original_width * current_scale
        window_physical_height = original_height * current_scale
        
        # Then calculate ratio using physical dimensions
        relative_width_ratio = window_physical_width / current_physical_width
        relative_height_ratio = window_physical_height / current_physical_height
        
        
        # Calculate window's relative position using logical dimensions (for positioning)
        relative_x_ratio = (x - current_x) / current_logical_width if current_logical_width > 0 else 0.5
        relative_y_ratio = (y - current_y) / current_logical_height if current_logical_height > 0 else 0.5
        
        # Apply the relative size ratio to target monitor's PHYSICAL dimensions
        # Then convert back to logical dimensions for the actual window size
        target_physical_scaled_width = int(target_physical_width * relative_width_ratio)
        target_physical_scaled_height = int(target_physical_height * relative_height_ratio)
        
        # Convert physical scaled size back to logical size for the target monitor
        scaled_width = int(target_physical_scaled_width / target_scale)
        scaled_height = int(target_physical_scaled_height / target_scale)
        
        # Sanity check: ensure calculated size is reasonable
        if scaled_width <= 0 or scaled_height <= 0:
            self.logger.error(f"ERROR: Calculated negative size! {scaled_width}x{scaled_height}")
            # Fallback to a reasonable size
            scaled_width = max(400, min(original_width, target_width // 2))
            scaled_height = max(300, min(original_height, target_height // 2))
            self.logger.debug(f"Using fallback size: {scaled_width}x{scaled_height}")
        
        # Check for unreasonable ratios (> 150% or < 10%)
        if relative_width_ratio > 1.5 or relative_height_ratio > 1.5:
            self.logger.warning(f"Unusually large ratios detected: {relative_width_ratio:.2%}x{relative_height_ratio:.2%}")
            # Cap the ratios to reasonable values
            relative_width_ratio = min(relative_width_ratio, 1.0)
            relative_height_ratio = min(relative_height_ratio, 1.0)
            scaled_width = int(target_width * relative_width_ratio)
            scaled_height = int(target_height * relative_height_ratio)
            self.logger.debug(f"Capped ratios and recalculated: {scaled_width}x{scaled_height}")
        
        if relative_width_ratio < 0.1 or relative_height_ratio < 0.1:
            self.logger.warning(f"Unusually small ratios detected: {relative_width_ratio:.2%}x{relative_height_ratio:.2%}")
            # Use minimum reasonable size
            scaled_width = max(scaled_width, 400)
            scaled_height = max(scaled_height, 300)
            self.logger.debug(f"Applied minimum size: {scaled_width}x{scaled_height}")
        
        self.logger.debug(f"Physical sizing: {original_width}x{original_height} -> {scaled_width}x{scaled_height}")
        self.logger.debug(f"Relative ratios: width={relative_width_ratio:.1%}, height={relative_height_ratio:.1%}")
        
        if current_dpi != target_dpi:
            self.logger.debug(f"Moving between different DPI monitors: {current_dpi} -> {target_dpi}")
        else:
            self.logger.debug(f"Same DPI monitors: {current_dpi}")
        
        # Use relative positioning strategy (optimal for most use cases)
        # Handle multi-monitor coordinate systems properly
        calculated_x = target_x + int(relative_x_ratio * target_width)
        calculated_y = target_y + int(relative_y_ratio * target_height)
        
        # For multi-monitor setups, don't force coordinates to be positive
        # The target monitor might legitimately have negative coordinates
        # Only ensure the window is within the target monitor's bounds
        new_x = calculated_x
        new_y = calculated_y
        
        self.logger.debug(f"Relative positioning: target_monitor_origin=({target_x}, {target_y})")
        self.logger.debug(f"Relative positioning: calculated=({calculated_x}, {calculated_y}), using as-is")
        
        # Ensure window fits within target monitor work area
        if scaled_width > target_width:
            scaled_width = target_width - 40  # Leave some margin
        
        if scaled_height > target_height:
            scaled_height = target_height - 40  # Leave some margin
        
        # Ensure position is within target monitor bounds
        new_x = max(target_x + 10, min(new_x, target_right - scaled_width - 10))
        new_y = max(target_y + 10, min(new_y, target_bottom - scaled_height - 10))
        
        return (new_x, new_y, scaled_width, scaled_height)
    
    def move_active_window_to_next_monitor(self) -> bool:
        """
        Move the currently active window to the next monitor.
        
        Returns:
            bool: True if window was moved successfully, False otherwise
        """
        self.logger.info("=== F9 pressed: Starting window move operation ===")
        try:
            # Get current window
            self.logger.debug("Step 1: Getting current window info")
            window_info = self.get_current_window()
            if not window_info:
                self.logger.error("No active window found to move")
                return False
            
            self.logger.debug(f"Found window: {window_info['title']} ({window_info['class_name']})")
            
            # Check if we should exclude this window
            self.logger.debug("Step 2: Checking if window should be excluded")
            if self._should_exclude_window(window_info):
                self.logger.error(f"Window excluded: {window_info['title']}")
                return False
            
            self.logger.debug("Window passed exclusion check")
            
            # Get monitors
            monitors = self.get_monitors()
            if len(monitors) < 2:
                self.logger.warning("Cannot move window: less than 2 monitors available")
                return False
            
            # Find current monitor
            current_monitor = self._find_window_monitor(window_info['rect'], monitors)
            if not current_monitor:
                self.logger.error("Could not determine current monitor")
                return False
            
            # Find next monitor
            next_monitor = self._get_next_monitor(current_monitor, monitors)
            if not next_monitor:
                self.logger.error("Could not determine next monitor")
                return False
            
            # Calculate target position and size (using optimized relative positioning)
            new_x, new_y, new_width, new_height = self.calculate_target_position(
                window_info['rect'], current_monitor, next_monitor
            )
            
            # Move the window
            success = self._move_window(window_info, new_x, new_y, new_width, new_height)
            
            if success:
                self._log_important(
                    f"Moved window '{window_info['title']}' from monitor {current_monitor['index']} "
                    f"to monitor {next_monitor['index']}"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to move window: {e}")
            self.logger.debug(traceback.format_exc())
            return False
    
    def _should_exclude_window(self, window_info: Dict[str, Any]) -> bool:
        """Check if a window should be excluded from movement."""
        title = window_info['title']
        class_name = window_info['class_name']
        
        
        # Skip minimized windows
        if window_info['is_minimized']:
            return True
        
        # Check fullscreen exclusion setting
        if self.settings_manager.get_window_management_setting("exclude_fullscreen", True):
            if self._is_fullscreen_window(window_info):
                return True
        
        # Skip certain system windows
        excluded_classes = {
            'Shell_TrayWnd',  # Taskbar
            'DV2ControlHost',  # Windows desktop
            'WorkerW',  # Desktop worker
            'Progman'  # Program manager
        }
        
        if class_name in excluded_classes:
            return True
        
        # Skip windows without title (usually system windows)
        if not title.strip():
            return True
        
        return False
    
    def _is_fullscreen_window(self, window_info: Dict[str, Any]) -> bool:
        """Check if a window is in fullscreen mode (not just maximized)."""
        
        # If window is maximized, it's not fullscreen - it's just maximized
        # We want to distinguish between maximized windows and true fullscreen apps
        if window_info['is_maximized']:
            return False
        
        # Get the monitor containing this window
        monitors = self.get_monitors()
        window_monitor = self._find_window_monitor(window_info['rect'], monitors)
        
        if not window_monitor:
            return False
        
        # Check if window covers the entire monitor (and is not maximized)
        window_rect = window_info['rect']
        monitor_rect = window_monitor['rect']
        
        return (window_rect[0] <= monitor_rect[0] and
                window_rect[1] <= monitor_rect[1] and
                window_rect[2] >= monitor_rect[2] and
                window_rect[3] >= monitor_rect[3])
    
    def _find_window_monitor(self, window_rect: Tuple[int, int, int, int], 
                           monitors: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find which monitor contains the majority of a window."""
        max_overlap = 0
        best_monitor = None
        
        for monitor in monitors:
            overlap = self._calculate_overlap(window_rect, monitor['rect'])
            if overlap > max_overlap:
                max_overlap = overlap
                best_monitor = monitor
        
        return best_monitor
    
    def _calculate_overlap(self, rect1: Tuple[int, int, int, int], 
                          rect2: Tuple[int, int, int, int]) -> int:
        """Calculate the overlap area between two rectangles."""
        x1, y1, x2, y2 = rect1
        a1, b1, a2, b2 = rect2
        
        # Calculate intersection
        left = max(x1, a1)
        top = max(y1, b1)
        right = min(x2, a2)
        bottom = min(y2, b2)
        
        if left < right and top < bottom:
            return (right - left) * (bottom - top)
        
        return 0
    
    def _get_next_monitor(self, current_monitor: Dict[str, Any], 
                         monitors: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get the next monitor in the sequence."""
        current_index = current_monitor['index']
        next_index = (current_index + 1) % len(monitors)
        
        for monitor in monitors:
            if monitor['index'] == next_index:
                return monitor
        
        return None
    
    def _move_window(self, window_info: Dict[str, Any], 
                    new_x: int, new_y: int, new_width: int, new_height: int) -> bool:
        """Move a window to the specified position and size."""
        hwnd = window_info['hwnd']
        
        # Validate window handle
        if not hwnd or not win32gui.IsWindow(hwnd):
            self.logger.error(f"Invalid window handle: {hwnd}")
            return False
        
        # Check if window is still the foreground window
        current_hwnd = win32gui.GetForegroundWindow()
        if current_hwnd != hwnd:
            self.logger.warning(f"Window handle changed: expected {hwnd}, current {current_hwnd}")
            # Update to current window
            hwnd = current_hwnd
            if not hwnd or not win32gui.IsWindow(hwnd):
                self.logger.error("Current foreground window is also invalid")
                return False
        
        try:
            # Handle maximized windows (always enabled for best user experience)
            if window_info['is_maximized']:
                self.logger.info(f"Detected maximized window: {window_info['title']}")
                self.logger.debug("Proceeding with maximized window move")
                return self._move_maximized_window(hwnd, new_x, new_y, new_width, new_height)
            else:
                self.logger.debug(f"Window is not maximized, using normal move")
            
            # Try a simpler approach first - just move without resizing
            self.logger.debug("Trying move-only approach first")
            move_success = win32gui.SetWindowPos(
                hwnd, 0, new_x, new_y, 0, 0,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE | win32con.SWP_NOSIZE
            )
            
            if move_success:
                self.logger.debug(f"Window moved to position ({new_x}, {new_y})")
                
                # Now try to resize separately
                self.logger.debug(f"Now trying to resize to {new_width}x{new_height}")
                resize_success = win32gui.SetWindowPos(
                    hwnd, 0, 0, 0, new_width, new_height,
                    win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE | win32con.SWP_NOMOVE
                )
                
                if resize_success:
                    self.logger.debug("Window resized successfully")
                    return True
                else:
                    import ctypes
                    resize_error = ctypes.windll.kernel32.GetLastError()
                    self.logger.warning(f"Resize failed with error: {resize_error}, but move succeeded")
                    return True  # At least we moved it
            else:
                # Move failed, try the original approach
                import ctypes
                move_error = ctypes.windll.kernel32.GetLastError()
                self.logger.debug(f"Move-only failed with error: {move_error}, trying combined approach")
                
                success = win32gui.SetWindowPos(
                    hwnd, 0, new_x, new_y, new_width, new_height,
                    win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
                )
                
                if success:
                    self.logger.debug(f"Combined move+resize succeeded")
                    return True
                else:
                    error_code = ctypes.windll.kernel32.GetLastError()
                    self.logger.debug(f"SetWindowPos returned error: {error_code}, checking actual result")
                    self.logger.debug(f"Parameters: hwnd={hwnd}, pos=({new_x}, {new_y}), size=({new_width}x{new_height})")
                    
                    # 检查窗口是否实际移动了（即使API返回失败）
                    try:
                        current_rect = win32gui.GetWindowRect(hwnd)
                        self.logger.debug(f"Current window rect after 'failed' move: {current_rect}")
                        
                        # 检查位置是否接近目标位置（允许一些误差）
                        tolerance = 10
                        if (abs(current_rect[0] - new_x) <= tolerance and 
                            abs(current_rect[1] - new_y) <= tolerance):
                            self._log_important("Window moved successfully!")
                            return True
                    except Exception as e:
                        self.logger.debug(f"Could not verify window position: {e}")
                    
                    # Final fallback: try using ShowWindow and MoveWindow
                    self.logger.debug("Trying final fallback with MoveWindow")
                    try:
                        move_result = win32gui.MoveWindow(hwnd, new_x, new_y, new_width, new_height, True)
                        if move_result:
                            self.logger.debug("MoveWindow succeeded as fallback")
                            return True
                        else:
                            move_error = ctypes.windll.kernel32.GetLastError()
                            self.logger.debug(f"MoveWindow returned error: {move_error}, checking actual result")
                            
                            # 再次检查窗口是否实际移动了
                            try:
                                final_rect = win32gui.GetWindowRect(hwnd)
                                self.logger.debug(f"Final window rect: {final_rect}")
                                if (abs(final_rect[0] - new_x) <= tolerance and 
                                    abs(final_rect[1] - new_y) <= tolerance):
                                    self._log_important("Window moved successfully!")
                                    return True
                            except Exception as e:
                                self.logger.debug(f"Could not verify final position: {e}")
                    except Exception as e:
                        self.logger.error(f"MoveWindow exception: {e}")
                    
                    return False
            
            # This line should not be reached due to the logic above
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to move window: {e}")
            return False
    
    def _move_maximized_window(self, hwnd: int, 
                              new_x: int, new_y: int, 
                              width: int, height: int) -> bool:
        """Move a maximized window to a new monitor and re-maximize it there."""
        try:
            self.logger.info(f"Moving maximized window to target monitor at ({new_x}, {new_y})")
            
            # Method 1: Optimized SetWindowPlacement approach
            try:
                self.logger.debug("Method 1: Trying optimized SetWindowPlacement")
                
                # Get current window placement
                placement = win32gui.GetWindowPlacement(hwnd)
                
                # Modify the normal position to be on the target monitor
                normal_rect = placement[4]
                current_width = normal_rect[2] - normal_rect[0]
                current_height = normal_rect[3] - normal_rect[1]
                
                # Set new normal position on target monitor
                new_normal_rect = (new_x, new_y, new_x + current_width, new_y + current_height)
                
                # Create new placement - keep it maximized (SW_SHOWMAXIMIZED = 3)
                new_placement = (
                    placement[0],  # length
                    placement[1],  # flags  
                    3,  # showCmd - keep maximized
                    placement[3],  # ptMinPosition
                    new_normal_rect  # rcNormalPosition
                )
                
                # Set the new placement directly (should move and stay maximized)
                placement_success = win32gui.SetWindowPlacement(hwnd, new_placement)
                
                if placement_success:
                    self.logger.info("✓ Fast SetWindowPlacement method succeeded")
                    return True
                else:
                    self.logger.debug("Fast SetWindowPlacement failed, trying slower method")
                    
            except Exception as e:
                self.logger.debug(f"Fast SetWindowPlacement failed: {e}")
            
            # Method 2: Simplified fallback approach
            self.logger.debug("Method 2: Using simplified approach")
            
            # Step 1: Restore the window (shorter delay)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.15)  # Reduced delay
            
            # Step 2: Simple move strategy only
            temp_width = min(width, 800)
            temp_height = min(height, 600)
            
            try:
                move_success = win32gui.SetWindowPos(
                    hwnd, 0, new_x, new_y, temp_width, temp_height,
                    win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
                )
                
                if move_success:
                    # Quick maximize
                    time.sleep(0.1)  # Minimal delay
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    self.logger.info("✓ Fallback method succeeded")
                    return True
                else:
                    self.logger.debug("SetWindowPos returned failure, checking actual result")
                    # 检查窗口是否实际移动了（即使API返回失败）
                    try:
                        time.sleep(0.1)  # 给窗口一点时间
                        current_rect = win32gui.GetWindowRect(hwnd)
                        self.logger.debug(f"Maximized window rect after 'failed' move: {current_rect}")
                        
                        # 检查窗口是否在目标显示器上（通过检查x坐标范围）
                        if current_rect[0] >= new_x - 100:  # 允许一些误差
                            self._log_important("Maximized window moved successfully!")
                            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)  # 确保最大化
                            return True
                    except Exception as e:
                        self.logger.debug(f"Could not verify maximized window position: {e}")
                    
                    # Restore original state
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    return False
                    
            except Exception as e:
                self.logger.error(f"Fallback method exception: {e}")
                # Restore original state
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                except:
                    pass
                return False
                
        except Exception as e:
            self.logger.error(f"Exception in _move_maximized_window: {e}")
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            except:
                pass
            return False
    
    def is_multi_monitor_setup(self) -> bool:
        """Check if the system has multiple monitors."""
        monitors = self.get_monitors()
        return len(monitors) >= 2
    
    def _start_hotkey_listener(self) -> bool:
        """Start the global hotkey listener."""
        try:
            hotkey_str = self.settings_manager.get_window_management_setting("hotkey", "F12")
            
            # Validate hotkey
            validation = self.settings_manager.validate_hotkey(hotkey_str)
            if not validation['valid']:
                self.logger.error(f"Invalid hotkey configuration: {validation['error']}")
                return False
            
            # Parse hotkey for pynput
            hotkey_combo = self._parse_hotkey_for_pynput(validation['parsed'])
            if not hotkey_combo:
                self.logger.error("Failed to parse hotkey for pynput")
                return False
            
            # Create hotkey listener
            self.hotkey_listener = keyboard.GlobalHotKeys({
                hotkey_combo: self.move_active_window_to_next_monitor
            })
            
            # Start listener in a separate thread
            self.hotkey_listener.start()
            
            self._log_important(f"Hotkey listener started for: {hotkey_str}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start hotkey listener: {e}")
            return False
    
    def _stop_hotkey_listener(self) -> None:
        """Stop the global hotkey listener."""
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
                self.hotkey_listener = None
                self.logger.info("Hotkey listener stopped")
            except Exception as e:
                self.logger.error(f"Error stopping hotkey listener: {e}")
    
    def _parse_hotkey_for_pynput(self, parsed_hotkey: Dict[str, Any]) -> Optional[str]:
        """Convert parsed hotkey to pynput format."""
        try:
            main_key = parsed_hotkey['main_key']
            modifiers = parsed_hotkey['modifiers']
            
            # Convert modifiers to pynput format
            pynput_parts = []
            
            for modifier in modifiers:
                if modifier == 'Ctrl':
                    pynput_parts.append('<ctrl>')
                elif modifier == 'Alt':
                    pynput_parts.append('<alt>')
                elif modifier == 'Shift':
                    pynput_parts.append('<shift>')
                elif modifier == 'Win':
                    pynput_parts.append('<cmd>')  # Windows key
            
            # Convert main key to pynput format
            if main_key.startswith('F') and main_key[1:].isdigit():
                # Function key
                pynput_parts.append(f'<f{main_key[1:]}>')
            elif len(main_key) == 1 and main_key.isalpha():
                # Letter key
                pynput_parts.append(main_key.lower())
            elif len(main_key) == 1 and main_key.isdigit():
                # Number key
                pynput_parts.append(main_key)
            elif main_key == 'Space':
                pynput_parts.append('<space>')
            elif main_key == 'Tab':
                pynput_parts.append('<tab>')
            elif main_key == 'Enter':
                pynput_parts.append('<enter>')
            elif main_key == 'Esc':
                pynput_parts.append('<esc>')
            elif main_key == 'Delete':
                pynput_parts.append('<delete>')
            elif main_key == 'Insert':
                pynput_parts.append('<insert>')
            elif main_key == 'Home':
                pynput_parts.append('<home>')
            elif main_key == 'End':
                pynput_parts.append('<end>')
            elif main_key == 'PageUp':
                pynput_parts.append('<page_up>')
            elif main_key == 'PageDown':
                pynput_parts.append('<page_down>')
            else:
                self.logger.error(f"Unsupported key: {main_key}")
                return None
            
            return '+'.join(pynput_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to parse hotkey for pynput: {e}")
            return None
    
    def detect_hotkey_conflicts(self, hotkey: str) -> List[str]:
        """
        Detect potential hotkey conflicts with common system shortcuts.
        
        Args:
            hotkey: Hotkey string to check
            
        Returns:
            List of potential conflicts
        """
        conflicts = []
        
        # Common system hotkeys that might conflict
        system_hotkeys = {
            'F1': ['Windows Help'],
            'F2': ['Rename file'],
            'F3': ['Find/Search'],
            'F4': ['Address bar', 'Alt+F4 close window'],
            'F5': ['Refresh'],
            'F6': ['Switch between panes'],
            'F10': ['Menu bar'],
            'F11': ['Full screen'],
            'F12': ['Developer tools'],
            'Ctrl+F1': ['Hide/show ribbon'],
            'Ctrl+F4': ['Close tab'],
            'Ctrl+F5': ['Hard refresh'],
            'Alt+F4': ['Close window'],
            'Win+F1': ['Windows feedback'],
        }
        
        if hotkey in system_hotkeys:
            conflicts.extend(system_hotkeys[hotkey])
        
        # Check for common application conflicts
        if 'F12' in hotkey:
            conflicts.append('Browser developer tools')
        
        if 'Ctrl+F' in hotkey:
            conflicts.append('Find function in applications')
        
        return conflicts
    
    def get_alternative_hotkeys(self) -> List[str]:
        """Get a list of recommended alternative hotkeys."""
        return [
            'F12',      # Default
            'Ctrl+F12', # With modifier
            'Alt+F12',  # Alternative modifier
            'F9',       # Less commonly used
            'Ctrl+F9',  # With modifier
            'Alt+F9',   # Alternative
            'Shift+F12', # Shift modifier
            'Ctrl+Alt+M', # Letter combination
        ]
    
    def reload_config(self) -> bool:
        """Reload configuration and restart hotkey listener if needed."""
        try:
            # Update logger level
            debug_mode = self.settings_manager.get_window_management_setting("debug_mode", False)
            self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
            
            # Clear monitor cache to force refresh
            self.monitors_cache = None
            
            # Restart hotkey listener if running
            if self.is_running:
                self._stop_hotkey_listener()
                if self._start_hotkey_listener():
                    self.logger.info("Configuration reloaded successfully")
                    return True
                else:
                    self.logger.error("Failed to restart hotkey listener after config reload")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            return False