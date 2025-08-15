import tkinter as tk
import threading
import time
from typing import Optional, Callable
import math

class ScreenEffectsManager:
    """管理屏幕视觉提醒效果"""
    
    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager
        self.effect_window = None
        self.effect_thread = None
        self.is_running = False
        
    def show_alarm_effect(self, effect_type: str = "border_flash", duration: float = 5.0):
        """显示闹钟视觉效果
        
        Args:
            effect_type: 效果类型 ("border_flash", "screen_flash", "pulse")
            duration: 效果持续时间（秒）
        """
        if self.is_running:
            self.stop_effect()
        
        # 从设置中获取效果配置
        if self.settings_manager:
            enabled = self.settings_manager.get("visual_effects.enabled", True)
            if not enabled:
                print("Visual effects disabled by settings")
                return
            
            effect_type = self.settings_manager.get("visual_effects.type", effect_type)
            duration = self.settings_manager.get("visual_effects.duration", duration)
            intensity = self.settings_manager.get("visual_effects.intensity", "medium")
        
        self.is_running = True
        self.effect_thread = threading.Thread(
            target=self._run_effect, 
            args=(effect_type, duration, intensity), 
            daemon=True
        )
        self.effect_thread.start()
        
    def stop_effect(self):
        """停止当前效果"""
        self.is_running = False
        if self.effect_window:
            try:
                self.effect_window.destroy()
            except:
                pass
            self.effect_window = None
            
    def _run_effect(self, effect_type: str, duration: float, intensity: str = "medium"):
        """在单独线程中运行效果"""
        try:
            if effect_type == "border_flash":
                self._border_flash_effect(duration, intensity)
            elif effect_type == "screen_flash":
                self._screen_flash_effect(duration, intensity)
        except Exception as e:
            print(f"Screen effect error: {e}")
        finally:
            self.is_running = False
            if self.effect_window:
                try:
                    self.effect_window.destroy()
                except:
                    pass
                self.effect_window = None
    
    def _border_flash_effect(self, duration: float, intensity: str = "medium"):
        """屏幕边缘闪光效果"""
        # 根据强度调整参数
        intensity_settings = {
            "low": {"alpha": 0.2, "border_width": 3, "flash_interval": 0.8, "max_alpha": 0.5},
            "medium": {"alpha": 0.3, "border_width": 5, "flash_interval": 0.5, "max_alpha": 0.7},
            "high": {"alpha": 0.4, "border_width": 8, "flash_interval": 0.3, "max_alpha": 0.9}
        }
        
        settings = intensity_settings.get(intensity, intensity_settings["medium"])
        
        # 创建全屏透明窗口
        self.effect_window = tk.Toplevel()
        self.effect_window.attributes('-fullscreen', True)
        self.effect_window.attributes('-topmost', True)
        self.effect_window.attributes('-alpha', settings["alpha"])
        self.effect_window.configure(bg='red')
        self.effect_window.overrideredirect(True)
        
        # 获取屏幕尺寸
        screen_width = self.effect_window.winfo_screenwidth()
        screen_height = self.effect_window.winfo_screenheight()
        
        # 创建边框效果 - 根据强度调整边框宽度
        border_width = settings["border_width"]
        
        # 上边框
        top_frame = tk.Frame(self.effect_window, bg='red', height=border_width)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        
        # 下边框
        bottom_frame = tk.Frame(self.effect_window, bg='red', height=border_width)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 左边框
        left_frame = tk.Frame(self.effect_window, bg='red', width=border_width)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # 右边框
        right_frame = tk.Frame(self.effect_window, bg='red', width=border_width)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 中间透明区域
        center_frame = tk.Frame(self.effect_window, bg='black')
        center_frame.pack(fill=tk.BOTH, expand=True)
        self.effect_window.attributes('-transparentcolor', 'black')
        
        # 闪烁动画
        start_time = time.time()
        flash_interval = settings["flash_interval"]  # 根据强度调整闪烁频率
        
        while self.is_running and (time.time() - start_time) < duration:
            # 计算闪烁状态
            elapsed = time.time() - start_time
            flash_cycle = (elapsed % flash_interval) / flash_interval
            
            if flash_cycle < 0.5:
                alpha = settings["max_alpha"]  # 使用强度设置的最大透明度
                color = 'red'
            else:
                alpha = settings["alpha"] * 0.5  # 暗淡状态
                color = 'orange'
            
            try:
                self.effect_window.attributes('-alpha', alpha)
                for frame in [top_frame, bottom_frame, left_frame, right_frame]:
                    frame.configure(bg=color)
                self.effect_window.update()
            except:
                break
                
            time.sleep(0.05)
    
    def _screen_flash_effect(self, duration: float, intensity: str = "medium"):
        """全屏闪光效果"""
        # 根据强度调整参数
        intensity_settings = {
            "low": {"base_alpha": 0.05, "max_alpha": 0.2, "flash_interval": 0.5},
            "medium": {"base_alpha": 0.1, "max_alpha": 0.4, "flash_interval": 0.3},
            "high": {"base_alpha": 0.15, "max_alpha": 0.6, "flash_interval": 0.2}
        }
        
        settings = intensity_settings.get(intensity, intensity_settings["medium"])
        
        self.effect_window = tk.Toplevel()
        self.effect_window.attributes('-fullscreen', True)
        self.effect_window.attributes('-topmost', True)
        self.effect_window.attributes('-alpha', settings["base_alpha"])
        self.effect_window.configure(bg='white')
        self.effect_window.overrideredirect(True)
        
        start_time = time.time()
        flash_interval = settings["flash_interval"]
        
        while self.is_running and (time.time() - start_time) < duration:
            elapsed = time.time() - start_time
            flash_cycle = (elapsed % flash_interval) / flash_interval
            
            if flash_cycle < 0.3:
                alpha = settings["max_alpha"]
                color = 'white'
            else:
                alpha = settings["base_alpha"]
                color = 'lightblue'
            
            try:
                self.effect_window.attributes('-alpha', alpha)
                self.effect_window.configure(bg=color)
                self.effect_window.update()
            except:
                break
                
            time.sleep(0.05)
    
    def is_effect_running(self) -> bool:
        """检查是否有效果正在运行"""
        return self.is_running