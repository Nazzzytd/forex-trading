from pathlib import Path
from typing import Dict, Any  # 添加这行导入
from ..core.config_loader import ConfigLoader
from ..core.tool_registry import ToolRegistry
from ..core.server_manager import ServerManager
from ..core.workflow_executor import WorkflowExecutor

class RunCommand:
    """运行命令 - 执行工作流"""
    
    def __init__(self):
        self.config_loader = ConfigLoader()
    
    def execute(self, workflow_file: str, verbose: bool = False):
        """执行运行命令"""
        workflow_path = Path(workflow_file)
        
        if not workflow_path.exists():
            print(f"❌ 工作流文件不存在: {workflow_file}")
            return
        
        print(f"🚀 运行工作流: {workflow_path.name}")
        
        # 加载工作流配置
        workflow_config = self.config_loader.load_config(workflow_path)
        
        # 初始化框架组件
        tool_registry = ToolRegistry()
        server_manager = ServerManager(tool_registry)
        workflow_executor = WorkflowExecutor(server_manager)
        
        # 注册工作流中的工具
        self._register_tools(workflow_config, tool_registry)
        
        # 执行工作流
        results = workflow_executor.execute_workflow(workflow_config)
        
        # 显示执行结果
        self._display_execution_summary(results)
    
    def _register_tools(self, workflow_config: Dict, registry: ToolRegistry):
        """注册工作流中的工具"""
        tools = workflow_config.get("tools", [])
        
        for tool_config in tools:
            server_type = tool_config["server_type"]
            tool_def_path = Path(f"servers/{server_type}/{server_type}.yaml")
            
            if tool_def_path.exists():
                tool_def = self.config_loader.load_config(tool_def_path)
                registry.register_tool(tool_def)
            else:
                print(f"⚠️  工具定义文件不存在: {tool_def_path}")
    
    def _display_execution_summary(self, results: Dict):
        """显示执行摘要"""
        total_steps = len(results)
        successful_steps = sum(1 for r in results.values() if r.get("success"))
        failed_steps = total_steps - successful_steps
        
        print(f"\n📊 执行统计:")
        print(f"   总步骤: {total_steps}")
        print(f"   成功: {successful_steps}")
        print(f"   失败: {failed_steps}")
        
        if failed_steps > 0:
            print(f"\n❌ 失败的步骤:")
            for step_name, result in results.items():
                if not result.get("success"):
                    error = result.get("error", "未知错误")
                    print(f"   - {step_name}: {error}")