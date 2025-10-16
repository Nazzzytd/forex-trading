import yaml
from pathlib import Path
from typing import Dict, Any  # 添加导入
from ..core.config_loader import ConfigLoader

class BuildCommand:
    """构建命令 - 生成工具配置"""
    
    def __init__(self):
        self.config_loader = ConfigLoader()
    
    def execute(self, tool_file: str, force: bool = False):
        """执行构建命令"""
        tool_path = Path(tool_file)
        
        if not tool_path.exists():
            print(f"❌ 工具文件不存在: {tool_file}")
            return
        
        print(f"🔨 构建工具: {tool_path.name}")
        
        # 加载工具定义
        tool_def = self.config_loader.load_config(tool_path)
        tool_name = tool_def["name"]
        tool_dir = tool_path.parent
        
        # 生成 parameter.yaml
        self._generate_parameter_file(tool_def, tool_dir, tool_name, force)
        
        # 生成 server.yaml
        self._generate_server_file(tool_def, tool_dir, tool_name, force)
        
        print(f"✅ 工具构建完成: {tool_name}")
    
    def _generate_parameter_file(self, tool_def: Dict[str, Any], tool_dir: Path, 
                               tool_name: str, force: bool):
        """生成参数配置文件"""
        param_file = tool_dir / f"{tool_name}_parameter.yaml"
        
        if param_file.exists() and not force:
            print(f"⚠️  参数文件已存在: {param_file} (使用 --force 重新生成)")
            return
        
        parameters = tool_def.get("parameters", {})
        param_config = {}
        
        for param_name, param_def in parameters.items():
            # 保留环境变量引用
            default_value = param_def.get("default")
            if isinstance(default_value, str) and default_value.startswith("${"):
                param_config[param_name] = default_value
            else:
                param_config[param_name] = default_value
        
        with open(param_file, 'w', encoding='utf-8') as f:
            yaml.dump(param_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 生成参数配置: {param_file}")
    
    def _generate_server_file(self, tool_def: Dict[str, Any], tool_dir: Path, 
                            tool_name: str, force: bool):
        """生成服务器配置文件"""
        server_file = tool_dir / f"{tool_name}_server.yaml"
        
        if server_file.exists() and not force:
            print(f"⚠️  服务器文件已存在: {server_file} (使用 --force 重新生成)")
            return
        
        server_config = {
            "server_type": tool_name,
            "name": f"{tool_name}_server",
            "port": self._find_available_port(),
            "workers": 1,
            "timeout": 300,
            "log_level": "INFO",
            "description": tool_def.get("description", "")
        }
        
        with open(server_file, 'w', encoding='utf-8') as f:
            yaml.dump(server_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 生成服务配置: {server_file}")
    
    def _find_available_port(self) -> int:
        """查找可用端口（简化实现）"""
        # 在实际实现中应该检查端口是否被占用
        return 8000