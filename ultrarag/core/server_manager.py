import threading
import time
import requests
from typing import Dict, Any, Optional
from .tool_registry import ToolRegistry

class ServerManager:
    """服务器管理器 - 启动和管理工具服务器"""
    
    # 1. 构造函数中添加 verbose 参数
    def __init__(self, tool_registry: ToolRegistry, verbose: bool = False):
        self.tool_registry = tool_registry
        self.servers: Dict[str, Dict] = {}
        self.port_pool = set(range(8000, 8100))
        self.verbose = verbose  # 新增 verbose 属性
    
    # 2. 修改 start_server 方法，使其内部根据 self.verbose 决定是否打印
    def start_server(self, tool_name: str, server_config: Dict[str, Any], verbose: Optional[bool] = None) -> int:
        """启动工具服务器"""
        
        # 允许在调用时覆盖实例的 verbose 设置
        is_verbose = verbose if verbose is not None else self.verbose
        
        if tool_name in self.servers:
            if is_verbose:  # 检查 verbose
                print(f"⚠️  服务器已在运行: {tool_name}")
            return self.servers[tool_name]["port"]
        
        # 分配端口
        if not self.port_pool:
            raise RuntimeError("无可用端口")
        
        port = self.port_pool.pop()
        
        # 创建工具实例
        tool_def = self.tool_registry.get_tool_definition(tool_name)
        parameter_config = server_config.get("parameters", {})
        
        tool_instance = self.tool_registry.create_tool_instance(tool_name, parameter_config, verbose=is_verbose)
        
        # 启动服务器线程
        server_thread = threading.Thread(
            target=self._run_server,
            args=(tool_instance, port, server_config, is_verbose),  # 传递 is_verbose
            daemon=True
        )
        server_thread.start()
        
        self.servers[tool_name] = {
            "port": port,
            "thread": server_thread,
            "instance": tool_instance,
            "config": server_config
        }
        
        if is_verbose:  # 检查 verbose
            print(f"🚀 启动服务器: {tool_name} (端口: {port})")
        
        # 等待服务器就绪
        time.sleep(1)
        
        return port
    
    # 3. 修改 _run_server 方法，接收 is_verbose 参数
    def _run_server(self, tool_instance, port: int, config: Dict[str, Any], is_verbose: bool):
        """运行服务器（简化实现）"""
        # 在实际实现中，这里应该启动一个 HTTP 服务器
        if is_verbose:  # 检查 verbose
            print(f"📡 服务器运行中: 端口 {port}")
        
        # 模拟服务器运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            if is_verbose:  # 检查 verbose
                print(f"🛑 停止服务器: 端口 {port}")
    
    def stop_server(self, tool_name: str):
        """停止服务器"""
        if tool_name in self.servers:
            server_info = self.servers.pop(tool_name)
            self.port_pool.add(server_info["port"])
            if self.verbose:  # 检查 verbose
                print(f"🛑 停止服务器: {tool_name}")
    
    # ... 其他方法保持不变 (call_tool_method, health_check, __init__ 等)
    
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
            if hasattr(self.servers[tool_name]["instance"], "health_check"):
                return self.call_tool_method(tool_name, "health_check")
            else:
                return {"status": "running"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# --- 额外步骤：修改 RunCommand.py 来传递 verbose 参数 ---
# (为了让上述修改生效，您还需要修改 RunCommand.py)

# 在 RunCommand.execute 中：
# 1. 实例化 ServerManager 时传递 verbose
# server_manager = ServerManager(tool_registry, verbose=verbose)

# 2. 在 _register_tools 中，将 verbose 传递给 start_server
# server_manager.start_server(server_type, server_config, verbose=verbose)