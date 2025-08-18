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
        """Get DPI for a specific monitor using simple heuristic detection."""
        try:
            monitor_info = win32api.GetMonitorInfo(hmonitor)
            device_name = monitor_info['Device']
            monitor_rect = monitor_info['Monitor']
            width = monitor_rect[2] - monitor_rect[0]
            height = monitor_rect[3] - monitor_rect[1]
            
            # 简单的启发式检测（经过验证，足够准确）
            if width == 2560 and height == 1440:
                # 2560x1440通常是100%缩放
                estimated_dpi = 96
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
            self.logger.debug(f"DPI detection failed: {e}")
            # 最终回退：100%缩放
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
        Uses simplified relative positioning for reliable results.
        
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
        
        # 使用工作区域，但要考虑DPI缩放来计算真实的物理比例
        current_work_area = current_monitor['work_area']
        target_work_area = target_monitor['work_area']
        
        current_x, current_y, current_right, current_bottom = current_work_area
        target_x, target_y, target_right, target_bottom = target_work_area
        
        # 获取逻辑尺寸
        current_logical_width = current_right - current_x
        current_logical_height = current_bottom - current_y
        target_logical_width = target_right - target_x
        target_logical_height = target_bottom - target_y
        
        # 获取DPI缩放因子
        current_scale = current_monitor.get('scale_factor', (1.0, 1.0))[0]
        target_scale = target_monitor.get('scale_factor', (1.0, 1.0))[0]
        
        # 计算物理尺寸（用于比例计算）
        current_physical_width = current_logical_width * current_scale
        current_physical_height = current_logical_height * current_scale
        target_physical_width = target_logical_width * target_scale
        target_physical_height = target_logical_height * target_scale
        
        self.logger.debug(f"Current monitor: logical={current_logical_width}x{current_logical_height}, physical={current_physical_width:.0f}x{current_physical_height:.0f}, scale={current_scale:.2f}")
        self.logger.debug(f"Target monitor: logical={target_logical_width}x{target_logical_height}, physical={target_physical_width:.0f}x{target_physical_height:.0f}, scale={target_scale:.2f}")
        self.logger.debug(f"Original window: pos=({x}, {y}), size={original_width}x{original_height}")
        
        # 计算相对位置（使用逻辑坐标）
        relative_x_ratio = (x - current_x) / current_logical_width if current_logical_width > 0 else 0.5
        relative_y_ratio = (y - current_y) / current_logical_height if current_logical_height > 0 else 0.5
        
        # 计算窗口的物理大小
        window_physical_width = original_width * current_scale
        window_physical_height = original_height * current_scale
        
        # 计算相对大小（使用物理尺寸比例，保持真实的屏幕占比）
        relative_width_ratio = window_physical_width / current_physical_width if current_physical_width > 0 else 0.5
        relative_height_ratio = window_physical_height / current_physical_height if current_physical_height > 0 else 0.5
        
        self.logger.debug(f"Window physical size: {window_physical_width:.0f}x{window_physical_height:.0f}")
        self.logger.debug(f"Relative position: x={relative_x_ratio:.1%}, y={relative_y_ratio:.1%}")
        self.logger.debug(f"Relative ratios: width={relative_width_ratio:.1%}, height={relative_height_ratio:.1%}")
        
        # 应用物理比例到目标显示器，然后转换回逻辑尺寸
        target_physical_scaled_width = relative_width_ratio * target_physical_width
        target_physical_scaled_height = relative_height_ratio * target_physical_height
        
        new_width = int(target_physical_scaled_width / target_scale)
        new_height = int(target_physical_scaled_height / target_scale)
        
        # 计算位置（使用逻辑坐标）
        new_x = target_x + int(relative_x_ratio * target_logical_width)
        new_y = target_y + int(relative_y_ratio * target_logical_height)
        
        self.logger.debug(f"Calculated target: pos=({new_x}, {new_y}), size={new_width}x{new_height}")
        
        # 合理性检查和边界限制
        new_width = max(300, min(new_width, target_logical_width - 40))
        new_height = max(200, min(new_height, target_logical_height - 40))
        
        # 确保位置在工作区域内
        new_x = max(target_x + 10, min(new_x, target_right - new_width - 10))
        new_y = max(target_y + 10, min(new_y, target_bottom - new_height - 10))
        
        self.logger.debug(f"Final target: pos=({new_x}, {new_y}), size={new_width}x{new_height}")
        
        return (new_x, new_y, new_width, new_height)
    
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
                self.logger.debug("Using ultimate simple strategy: restore -> recursive call -> maximize")
                
                # 1. 恢复到普通窗口
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.05)  # 减少到50ms
                
                # 2. 递归调用自己，现在是普通窗口了，会使用已经正确的普通窗口逻辑
                success = self.move_active_window_to_next_monitor()
                
                # 3. 移动成功后重新最大化
                if success:
                    time.sleep(0.03)  # 减少到30ms
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    self._log_important("Maximized window moved successfully!")
                else:
                    # 移动失败，恢复最大化状态
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                
                return success
            else:
                self.logger.debug(f"Window is not maximized, using normal move")
            
            # 使用经过验证的最优策略
            self.logger.debug("Moving window using verified strategy")
            
            # 主要移动操作
            win32gui.SetWindowPos(
                hwnd, 0, new_x, new_y, new_width, new_height,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
            )
            
            # 验证并修正结果
            try:
                current_rect = win32gui.GetWindowRect(hwnd)
                actual_width = current_rect[2] - current_rect[0]
                actual_height = current_rect[3] - current_rect[1]
                
                # 检查位置是否正确
                tolerance = 10
                position_ok = (abs(current_rect[0] - new_x) <= tolerance and 
                              abs(current_rect[1] - new_y) <= tolerance)
                
                if position_ok:
                    # 如果大小被Windows调整，尝试修正
                    size_tolerance = 50
                    if (abs(actual_width - new_width) > size_tolerance or 
                        abs(actual_height - new_height) > size_tolerance):
                        self.logger.debug(f"Size auto-adjusted by Windows: {actual_width}x{actual_height}, correcting to {new_width}x{new_height}")
                        win32gui.SetWindowPos(
                            hwnd, 0, current_rect[0], current_rect[1], new_width, new_height,
                            win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
                        )
                    
                    self._log_important("Window moved successfully!")
                    return True
                else:
                    self.logger.debug(f"Position incorrect. Expected: ({new_x}, {new_y}), Actual: ({current_rect[0]}, {current_rect[1]})")
                    return False
            except Exception as e:
                self.logger.debug(f"Could not verify window position: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to move window: {e}")
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