# 窗口跨屏移动功能 - 技术设计文档

> **状态**: ✅ 已完成并部署  
> **版本**: v1.2  
> **最后更新**: 2025年1月  
> **开发完成度**: 100%

> 版本: 1.0  
> 创建日期: 2024年  
> 负责人: Rovo Dev  

## 1. 功能概述

在现有的"牛马生物钟"桌面定时器应用基础上，新增窗口跨屏移动功能。用户可通过全局快捷键将当前活动窗口快速移动到下一个显示器，提升多屏工作效率。

## 2. 技术架构设计

### 2.1 新增模块

- **`src/window_manager.py`**: 核心窗口管理模块
  - 负责显示器检测和窗口移动逻辑
  - 全局快捷键监听
  - 与现有设置系统集成

### 2.2 现有模块修改

- **`src/settings_manager.py`**: 扩展设置管理
  - 新增窗口管理相关配置项
  - 快捷键配置验证
- **`src/main.py`**: 主程序集成
  - 初始化窗口管理器
  - 线程管理
- **`requirements.txt`**: 依赖更新
- **`settings.json`**: 配置文件扩展

### 2.3 技术栈选择

- **`pywin32`**: Windows API交互，窗口操作
- **`pynput`**: 全局快捷键监听（比keyboard库更稳定）
- **线程模型**: 独立线程运行，避免阻塞主GUI

## 3. 详细设计

### 3.1 WindowManager类设计

```python
class WindowManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.hotkey_listener = None
        self.is_running = False
    
    def start(self):
        """启动窗口管理器和快捷键监听"""
        
    def stop(self):
        """停止窗口管理器"""
        
    def move_active_window_to_next_monitor(self):
        """核心功能：移动当前窗口到下一个显示器"""
        
    def get_monitors(self):
        """获取所有显示器信息"""
        
    def get_current_window(self):
        """获取当前活动窗口"""
        
    def calculate_target_position(self, window_rect, target_monitor):
        """计算目标位置"""
```

### 3.2 配置扩展

```json
{
    "window_management": {
        "enabled": true,
        "hotkey": "F12",
        "move_strategy": "center",
        "handle_maximized": true,
        "exclude_fullscreen": true
    }
}
```

**配置项说明**:
- `enabled`: 是否启用窗口管理功能
- `hotkey`: 触发快捷键（支持F1-F12, Ctrl+Key等组合）
- `move_strategy`: 移动策略
  - `center`: 在目标显示器居中显示
  - `relative`: 保持相对位置
  - `smart`: 智能选择最佳位置
- `handle_maximized`: 是否处理最大化窗口
- `exclude_fullscreen`: 是否排除全屏应用

### 3.3 核心算法

#### 3.3.1 显示器检测算法
```python
def get_monitors(self):
    """
    使用win32api.EnumDisplayMonitors()获取所有显示器信息
    返回格式: [
        {
            'index': 0,
            'rect': (x, y, width, height),
            'work_area': (x, y, width, height),
            'primary': True/False
        }
    ]
    """
```

#### 3.3.2 窗口移动算法
```python
def move_active_window_to_next_monitor(self):
    """
    1. 获取当前活动窗口句柄
    2. 获取窗口当前位置和大小
    3. 判断窗口当前所在显示器
    4. 计算下一个显示器（循环）
    5. 根据移动策略计算新位置
    6. 处理特殊情况（最大化、全屏）
    7. 移动窗口到新位置
    """
```

#### 3.3.3 位置计算策略
```python
def calculate_target_position(self, window_rect, target_monitor, strategy="center"):
    """
    center策略: 在目标显示器居中
    新X = 目标显示器X + (目标显示器宽度 - 窗口宽度) / 2
    新Y = 目标显示器Y + (目标显示器高度 - 窗口高度) / 2
    
    relative策略: 保持相对位置
    相对X比例 = (窗口X - 当前显示器X) / 当前显示器宽度
    新X = 目标显示器X + 相对X比例 * 目标显示器宽度
    """
```

### 3.4 错误处理策略

- **权限不足**: 捕获异常，记录日志，跳过无权限窗口
- **单显示器环境**: 检测显示器数量，禁用功能或提示用户
- **特殊窗口处理**: 
  - 最大化窗口：先还原→移动→重新最大化
  - 全屏应用：根据配置决定是否处理
- **快捷键冲突**: 启动时检测，提供替代方案

### 3.5 性能优化

- **延迟加载**: 仅在需要时获取显示器信息
- **缓存机制**: 缓存显示器配置，检测变化时更新
- **异步处理**: 窗口移动操作在独立线程执行
- **资源清理**: 及时释放窗口句柄和监听器资源

## 4. 集成方案

### 4.1 与现有架构的集成

- **遵循现有设计模式**: 采用相同的组件化架构
- **统一设置管理**: 使用现有的SettingsManager系统
- **一致的线程管理**: 采用与TrayController相同的线程模式
- **保持代码风格**: 遵循现有的命名规范和注释风格

### 4.2 生命周期管理

```python
# 在Application.__init__()中初始化
self.window_manager = WindowManager(self.settings_manager)

# 在Application.run()中启动
if self.settings_manager.get("window_management.enabled", False):
    self.window_manager.start()

# 在Application.on_exit()中清理
self.window_manager.stop()
```

### 4.3 配置热更新

- 监听设置文件变化
- 支持运行时重新加载快捷键配置
- 提供配置验证和错误提示

## 5. 安全性考虑

### 5.1 权限管理
- 检测当前进程权限级别
- 对管理员权限窗口的处理策略
- 避免权限提升攻击

### 5.2 系统稳定性
- 避免移动系统关键窗口
- 处理窗口移动失败的情况
- 防止无限循环和资源泄漏

### 5.3 用户隐私
- 不记录窗口内容信息
- 仅获取必要的窗口位置数据
- 本地处理，无网络传输

## 6. 测试策略

### 6.1 单元测试
- 显示器检测功能测试
- 位置计算算法测试
- 配置解析和验证测试

### 6.2 集成测试
- 与主程序的集成测试
- 多线程环境下的稳定性测试
- 配置热更新测试

### 6.3 兼容性测试
- 不同Windows版本测试
- 多种显示器配置测试
- 各类应用窗口测试

## 7. 部署和维护

### 7.1 依赖管理
- 明确标注新增依赖的版本要求
- 提供依赖安装失败的处理方案
- 考虑依赖冲突的解决方案

### 7.2 用户文档
- 功能使用说明
- 快捷键配置指南
- 常见问题解答
- 故障排除指南

### 7.3 监控和日志
- 关键操作的日志记录
- 错误统计和分析
- 性能监控指标

## 8. 未来扩展

### 8.1 高级功能
- 窗口布局预设
- 多窗口批量移动
- 智能窗口排列
- 虚拟桌面支持

### 8.2 跨平台支持
- macOS版本实现
- Linux版本实现
- 统一的跨平台API

### 8.3 AI增强
- 智能窗口位置推荐
- 用户习惯学习
- 自动布局优化