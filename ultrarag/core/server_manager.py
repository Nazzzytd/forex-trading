import threading
import time
import requests
from typing import Dict, Any, Optional  # 确保导入类型
from .tool_registry import ToolRegistry

class ServerManager:
    """服务器管理器 - 启动和管理工具服务器"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.servers: Dict[str, Dict] = {}  # 添加类型注解
        self.port_pool = set(range(8000, 8100))
    
    def start_server(self, tool_name: str, server_config: Dict[str, Any]) -> int:
        """启动工具服务器"""
        if tool_name in self.servers:
            print(f"⚠️  服务器已在运行: {tool_name}")
            return self.servers[tool_name]["port"]
        
        # 分配端口
        if not self.port_pool:
            raise RuntimeError("无可用端口")
        
        port = self.port_pool.pop()
        
        # 创建工具实例
        tool_def = self.tool_registry.get_tool_definition(tool_name)
        parameter_config = server_config.get("parameters", {})
        
        tool_instance = self.tool_registry.create_tool_instance(tool_name, parameter_config)
        
        # 启动服务器线程（简化版，实际应该用 HTTP 服务器）
        server_thread = threading.Thread(
            target=self._run_server,
            args=(tool_instance, port, server_config),
            daemon=True
        )
        server_thread.start()
        
        self.servers[tool_name] = {
            "port": port,
            "thread": server_thread,
            "instance": tool_instance,
            "config": server_config
        }
        
        print(f"🚀 启动服务器: {tool_name} (端口: {port})")
        
        # 等待服务器就绪
        time.sleep(1)
        
        return port
    
    def _run_server(self, tool_instance, port: int, config: Dict[str, Any]):
        """运行服务器（简化实现）"""
        # 在实际实现中，这里应该启动一个 HTTP 服务器
        # 如 FastAPI 或 Flask，提供工具方法的 API 端点
        print(f"📡 服务器运行中: 端口 {port}")
        
        # 模拟服务器运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"🛑 停止服务器: 端口 {port}")
    
    def stop_server(self, tool_name: str):
        """停止服务器"""
        if tool_name in self.servers:
            # 在实际实现中，这里应该停止 HTTP 服务器
            server_info = self.servers.pop(tool_name)
            self.port_pool.add(server_info["port"])
            print(f"🛑 停止服务器: {tool_name}")
    
    def call_tool_method(self, tool_name: str, method: str, **kwargs) -> Any:
        """调用工具方法"""
        if tool_name not in self.servers:
            raise ValueError(f"服务器未运行: {tool_name}")
        
        tool_instance = self.servers[tool_name]["instance"]
        
        if not hasattr(tool_instance, method):
            raise ValueError(f"工具方法不存在: {tool_name}.{method}")
        
        method_func = getattr(tool_instance, method)
        return method_func(**kwargs)
    
    def health_check(self, tool_name: str) -> Dict[str, Any]:
        """健康检查"""
        if tool_name not in self.servers:
            return {"status": "stopped"}
        
        try:
            # 尝试调用健康检查方法
            if hasattr(self.servers[tool_name]["instance"], "health_check"):
                return self.call_tool_method(tool_name, "health_check")
            else:
                return {"status": "running"}
        except Exception as e:
            return {"status": "error", "error": str(e)}