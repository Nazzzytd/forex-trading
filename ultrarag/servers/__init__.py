"""
UltraRAG Servers Module - 工具服务器管理
"""

import os
from pathlib import Path
from typing import Dict, List

# 服务器根目录
SERVERS_ROOT = Path(__file__).parent.parent.parent / "servers"

def discover_tools() -> List[str]:
    """
    自动发现可用的工具
    
    Returns:
        工具名称列表
    """
    tools = []
    
    if not SERVERS_ROOT.exists():
        return tools
    
    for item in SERVERS_ROOT.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # 检查是否有对应的 YAML 定义文件
            yaml_file = item / f"{item.name}.yaml"
            if yaml_file.exists():
                tools.append(item.name)
    
    return tools

def get_tool_path(tool_name: str) -> Path:
    """
    获取工具目录路径
    
    Args:
        tool_name: 工具名称
        
    Returns:
        工具目录路径
    """
    return SERVERS_ROOT / tool_name

def get_tool_definition_path(tool_name: str) -> Path:
    """
    获取工具定义文件路径
    
    Args:
        tool_name: 工具名称
        
    Returns:
        工具定义文件路径
    """
    return get_tool_path(tool_name) / f"{tool_name}.yaml"

def get_tool_parameter_path(tool_name: str) -> Path:
    """
    获取工具参数文件路径
    
    Args:
        tool_name: 工具名称
        
    Returns:
        工具参数文件路径
    """
    return get_tool_path(tool_name) / f"{tool_name}_parameter.yaml"

def get_tool_server_path(tool_name: str) -> Path:
    """
    获取工具服务器配置路径
    
    Args:
        tool_name: 工具名称
        
    Returns:
        工具服务器配置路径
    """
    return get_tool_path(tool_name) / f"{tool_name}_server.yaml"

def list_available_tools() -> Dict[str, Dict]:
    """
    列出所有可用工具的详细信息
    
    Returns:
        工具信息字典
    """
    tools_info = {}
    tool_names = discover_tools()
    
    for tool_name in tool_names:
        tool_info = {
            "name": tool_name,
            "path": str(get_tool_path(tool_name)),
            "definition_exists": get_tool_definition_path(tool_name).exists(),
            "parameter_exists": get_tool_parameter_path(tool_name).exists(),
            "server_config_exists": get_tool_server_path(tool_name).exists(),
        }
        tools_info[tool_name] = tool_info
    
    return tools_info

# 包级别的工具发现
available_tools = discover_tools()

__all__ = [
    'discover_tools',
    'get_tool_path', 
    'get_tool_definition_path',
    'get_tool_parameter_path',
    'get_tool_server_path',
    'list_available_tools',
    'available_tools',
    'SERVERS_ROOT'
]

# 包初始化信息
if available_tools:
    print(f"🔍 发现 {len(available_tools)} 个工具: {', '.join(available_tools)}")
else:
    print("⚠️  未发现任何工具，请运行 'ultrarag build' 构建工具")