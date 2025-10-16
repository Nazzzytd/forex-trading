import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, Type, Optional  # 确保导入类型
import yaml

class ToolRegistry:
    """工具注册表 - 管理所有可用工具"""
    
    def __init__(self):
        self.tools = {}
        self.tool_definitions = {}
    
    def register_tool(self, tool_def: Dict[str, Any]):
        """注册工具定义"""
        tool_name = tool_def["name"]
        self.tool_definitions[tool_name] = tool_def
        print(f"✅ 注册工具: {tool_name}")
    
    def load_tool_class(self, tool_name: str) -> Type:
        """加载工具类"""
        if tool_name not in self.tool_definitions:
            raise ValueError(f"工具未注册: {tool_name}")
        
        tool_def = self.tool_definitions[tool_name]
        class_file = tool_def["class"]["file"]
        class_name = tool_def["class"]["name"]
        
        # 构建完整路径
        tool_dir = Path(f"servers/{tool_name}")
        module_path = tool_dir / class_file
        
        if not module_path.exists():
            raise FileNotFoundError(f"工具类文件不存在: {module_path}")
        
        # 动态加载模块
        spec = importlib.util.spec_from_file_location(tool_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[tool_name] = module
        spec.loader.exec_module(module)
        
        # 获取工具类
        tool_class = getattr(module, class_name)
        return tool_class
    
    def create_tool_instance(self, tool_name: str, config: Dict[str, Any]):
        """创建工具实例"""
        tool_class = self.load_tool_class(tool_name)
        return tool_class(config)
    
    def get_tool_definition(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具定义"""
        return self.tool_definitions.get(tool_name)
    
    def list_tools(self) -> list:
        """列出所有注册的工具"""
        return list(self.tool_definitions.keys())