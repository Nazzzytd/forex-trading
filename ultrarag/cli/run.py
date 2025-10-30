from pathlib import Path
from typing import Dict, Any
from ..core.config_loader import ConfigLoader
from ..core.tool_registry import ToolRegistry
from ..core.server_manager import ServerManager
from ..core.workflow_executor import WorkflowExecutor

class RunCommand:
    """运行命令 - 执行工作流"""
    
    def __init__(self):
        self.config_loader = ConfigLoader()
    
    def execute(self, workflow_file: str, verbose: bool = False, 
                user_params: Dict = None, interactive: bool = False):
        """执行运行命令 - 增强版支持混合模式"""
        workflow_path = Path(workflow_file)
        
        if not workflow_path.exists():
            print(f"❌ 工作流文件不存在: {workflow_file}")
            return
        
        # 简洁模式：只在详细模式下显示完整信息 (删除冗余的 '▶️ 执行' 提示)
        if verbose:
            print(f"🚀 运行工作流: {workflow_path.name}")
            if interactive:
                print("🔘 模式: 混合模式（命令行参数 + 交互式输入）")
            elif user_params:
                print("🔘 模式: 命令行参数模式")
            else:
                print("🔘 模式: 纯交互式模式")
        else:
            # 简洁模式下，删除所有 CLI 运行提示
            pass 
        
        # 加载工作流配置
        workflow_config = self.config_loader.load_config(workflow_path)
        
        # 初始化框架组件 (新增：传递 verbose 参数)
        tool_registry = ToolRegistry(verbose=verbose) 
        server_manager = ServerManager(tool_registry, verbose=verbose)
        
        # 注册工作流中的工具
        # 在 _register_tools 中，将 verbose 传递给 server_manager.start_server
        self._register_tools(workflow_config, tool_registry, server_manager, verbose)
        
        # 注入用户参数到工作流配置中
        if user_params:
            self._inject_user_parameters(workflow_config, user_params, verbose)
        
        # 设置混合模式标志
        workflow_config['_interactive_mode'] = interactive
        workflow_config['_provided_params'] = user_params or {}
        
        # 创建工作流执行器
        workflow_executor = WorkflowExecutor(server_manager)
        
        # 设置详细模式
        workflow_executor.verbose = verbose
        
        # 执行工作流
        results = workflow_executor.execute_workflow(workflow_config)
        
        # 显示执行结果
        self._display_execution_summary(results, verbose)
    
    def _inject_user_parameters(self, workflow_config: Dict, user_params: Dict, verbose: bool):
        """将用户参数注入到工作流配置中"""
        # 确保variables部分存在
        if 'variables' not in workflow_config:
            workflow_config['variables'] = {}
        
        # 注入用户参数
        workflow_config['variables'].update(user_params)
        
        if verbose:
            print("📝 用户参数已注入:")
            for key, value in user_params.items():
                print(f"   {key}: {value}")
    
    def _register_tools(self, workflow_config: Dict, registry: ToolRegistry, 
                       server_manager: ServerManager, verbose: bool):
        """注册工作流中的工具 (关键修改：传递 verbose 到 start_server，删除冗余的注册信息)"""
        tools = workflow_config.get("tools", [])
        
        for tool_config in tools:
            server_type = tool_config["server_type"]
            tool_name = tool_config["name"]
            
            # 查找工具定义文件
            tool_def_path = Path(f"servers/{server_type}/{server_type}.yaml")
            
            if tool_def_path.exists():
                try:
                    tool_def = self.config_loader.load_config(tool_def_path)
                    
                    # registry.register_tool() 内部已根据 registry.verbose 属性进行打印控制
                    registry.register_tool(tool_def)
                    
                    # 启动工具服务器
                    server_config = {
                        "server_type": server_type,
                        "parameters": tool_config.get("parameters", {})
                    }
                    
                    # 关键修改：将 verbose 参数传递给 start_server
                    server_manager.start_server(server_type, server_config, verbose=verbose)
                    
                    # 仅在 verbose=True 且 ToolRegistry 内部没有打印的情况下，可在此处打印
                    # 但由于 ToolRegistry.register_tool 内部已处理，此处不再重复打印，避免混乱
                    
                except Exception as e:
                    print(f"❌ 注册工具失败 {tool_name}: {e}")
            else:
                if verbose:
                    print(f"⚠️  工具定义文件不存在: {tool_def_path}")
    
    def _display_execution_summary(self, results: Dict, verbose: bool):
        """显示执行摘要 (关键修改：删除简洁模式下的总结输出)"""
        total_steps = len(results)
        successful_steps = sum(1 for r in results.values() if r.get("success"))
        failed_steps = total_steps - successful_steps
        
        if verbose:
            print(f"\n📊 执行统计:")
            print(f"   总步骤: {total_steps}")
            print(f"   成功: {successful_steps}")
            print(f"   失败: {failed_steps}")
        else:
            # 简洁模式下，删除所有总结输出，让 WorkflowExecutor.py 中的 goodbye_message 处理
            pass
        
        if failed_steps > 0:
            print(f"\n❌ 失败的步骤:")
            for step_name, result in results.items():
                if not result.get("success"):
                    error = result.get("error", "未知错误")
                    print(f"   - {step_name}: {error}")