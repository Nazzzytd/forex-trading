"""
UltraRAG Framework - Forex Trading Agent 版本

一个用于构建和运行 RAG 增强工具的强大框架。
"""

from .core import ToolRegistry, ServerManager, WorkflowExecutor, ConfigLoader
from .servers import discover_tools, list_available_tools

__version__ = "1.0.0"
__author__ = "Forex Trading Agent"
__description__ = "UltraRAG Framework for Forex Trading Agent"

__all__ = [
    'ToolRegistry',
    'ServerManager',
    'WorkflowExecutor', 
    'ConfigLoader',
    'discover_tools',
    'list_available_tools'
]

def get_version():
    """获取框架版本"""
    return __version__

def info():
    """显示框架信息"""
    return f"""
UltraRAG Framework {__version__}
{__description__}

核心组件:
  • ToolRegistry - 工具注册和管理
  • ServerManager - 服务器生命周期管理  
  • WorkflowExecutor - 工作流执行引擎
  • ConfigLoader - 配置和环境变量管理

可用命令:
  • ultrarag build <tool.yaml> - 构建工具
  • ultrarag run <workflow.yaml> - 运行工作流
  • ultrarag list - 列出可用工具
"""