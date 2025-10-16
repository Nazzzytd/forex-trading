import os
import yaml
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class ConfigLoader:
    """配置加载器 - 支持环境变量解析"""
    
    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path
        self._load_env()
    
    def _load_env(self):
        """加载环境变量"""
        if os.path.exists(self.env_path):
            load_dotenv(self.env_path)
            print(f"✅ 已加载环境变量: {self.env_path}")
        else:
            print(f"⚠️  未找到环境变量文件: {self.env_path}")
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件并解析环境变量"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if config is None:
            config = {}
            
        return self._resolve_env_vars(config)
    
    def _resolve_env_vars(self, config: Any) -> Any:
        """递归解析环境变量"""
        if isinstance(config, dict):
            return {k: self._resolve_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._replace_env_vars(config)
        else:
            return config
    
    def _replace_env_vars(self, value: str) -> str:
        """替换字符串中的环境变量"""
        def replace_match(match):
            var_expr = match.group(1)
            if ':' in var_expr:
                var_name, default = var_expr.split(':', 1)
            else:
                var_name, default = var_expr, None
            
            env_value = os.getenv(var_name)
            if env_value is not None:
                return env_value
            elif default is not None:
                return default
            else:
                raise ValueError(f"环境变量 {var_name} 未设置")
        
        return re.sub(r'\$\{([^}]+)\}', replace_match, value)

# 确保类被正确导出
__all__ = ['ConfigLoader']