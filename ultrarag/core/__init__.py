"""
UltraRAG Core Module - 核心框架组件
"""

# 先导入基础模块，再导入具体类
from . import config_loader
from . import tool_registry
from . import server_manager
from . import workflow_executor

# 然后导入具体的类
from .config_loader import ConfigLoader
from .tool_registry import ToolRegistry
from .server_manager import ServerManager
from .workflow_executor import WorkflowExecutor

__all__ = [
    'ToolRegistry',
    'ServerManager', 
    'WorkflowExecutor',
    'ConfigLoader'
]

# 版本信息
__version__ = "1.0.0"
__author__ = "Forex Trading Agent"

# 包级别的初始化
def init():
    """初始化核心模块"""
    print("🔧 UltraRAG Core 模块已初始化")

# 自动执行初始化
init()