import time
from typing import Dict, Any, List
from .server_manager import ServerManager

class WorkflowExecutor:
    """工作流执行器"""
    
    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager
        self.results = {}
        self.tool_mapping = {}
    
    def execute_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流"""
        workflow_name = workflow_config.get("name", "未命名工作流")
        print(f"🚀 执行工作流: {workflow_name}")
        
        # 启动所有工具服务器
        tools = workflow_config.get("tools", [])
        for tool_config in tools:
            self._start_tool_server(tool_config)
        
        # 执行工作流步骤
        steps = workflow_config.get("workflow", [])
        for step in steps:
            self._execute_step(step)
        
        print(f"✅ 工作流执行完成")
        return self.results
    
    def _start_tool_server(self, tool_config: Dict[str, Any]):
        """启动工具服务器"""
        tool_name = tool_config["name"]
        server_type = tool_config["server_type"]
        self.tool_mapping[tool_name] = server_type
        server_config = {
            "server_type": server_type,
            "parameters": tool_config.get("parameters", {})
        }
        self.server_manager.start_server(server_type, server_config)
    
    def _execute_step(self, step: Dict[str, Any]):
        """执行单个步骤"""
        step_name = step.get("step", "未知步骤")
        tool_name = step.get("tool")
        inputs = step.get("inputs", {})
        method = step.get("method", "fetch_data")
        
        print(f"\n🔹 {step_name}")
        
        if tool_name not in self.tool_mapping:
            error_msg = f"工具未找到: {tool_name}"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"   ❌ {error_msg}")
            return
        
        server_type = self.tool_mapping[tool_name]
        
        try:
            result = self.server_manager.call_tool_method(server_type, method, **inputs)
            self.results[step_name] = {"success": True, "result": result}
            
            # 检查方法调用是否成功
            if result.get("success", False):
                print(f"   ✅ 成功")
                self._display_detailed_data(result)
            else:
                error_msg = result.get("error", "未知错误")
                print(f"   ❌ 失败: {error_msg}")
                self.results[step_name] = {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = str(e) if e else "未知异常"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"   ❌ 异常: {error_msg}")
    
    def _display_detailed_data(self, result: Dict[str, Any]):
        """显示详细数据"""
        data_type = result.get("data_type")
        currency_pair = result.get("currency_pair")
        
        if data_type == "realtime" and "data" in result:
            data = result["data"]
            rate = data.get("exchange_rate", 0)
            change = data.get("percent_change", 0)
            high = data.get("high", 0)
            low = data.get("low", 0)
            volume = data.get("volume", 0)
            
            print(f"     💹 {currency_pair}")
            print(f"       汇率: {rate:.4f}")
            print(f"       涨跌: {change:+.2f}%")
            print(f"       最高: {high:.4f} | 最低: {low:.4f}")
            print(f"       交易量: {volume:,}")
            if data.get('timestamp'):
                print(f"       时间: {data['timestamp']}")
                
        elif data_type in ["historical", "intraday"] and "data" in result:
            data_list = result["data"]
            summary = result.get("summary", {})
            
            print(f"     📊 {currency_pair} ({data_type})")
            print(f"       数据点数: {len(data_list)}")
            print(f"       时间范围: {summary.get('date_range', {}).get('start', 'N/A')} 至 {summary.get('date_range', {}).get('end', 'N/A')}")
            
            # 显示最近3条数据
            if data_list:
                print(f"       最近数据:")
                for i, item in enumerate(data_list[-3:][::-1]):  # 显示最新的3条
                    close = item.get('close', 0)
                    dt = item.get('datetime', 'N/A')
                    print(f"         {dt}: {close:.4f}")
            
            # 显示统计信息
            if "price_stats" in summary:
                stats = summary["price_stats"]
                print(f"       统计: 均值={stats.get('close_mean', 0):.4f}, 标准差={stats.get('close_std', 0):.4f}")
                
        elif "status" in result:
            # 健康检查或状态信息
            status = result.get("status", "unknown")
            print(f"     🩺 状态: {status}")
            if "api_requests_used" in result:
                print(f"       API 请求数: {result['api_requests_used']}")
            if "daily_requests_used" in result:
                remaining = result.get("daily_requests_remaining", 0)
                print(f"       今日剩余: {remaining} 次")
            if "message" in result:
                print(f"       信息: {result['message']}")
                
        elif "daily_requests_used" in result:
            # 使用统计
            used = result.get("daily_requests_used", 0)
            remaining = result.get("daily_requests_remaining", 0)
            print(f"     📈 API 使用统计")
            print(f"       已用: {used} 次")
            print(f"       剩余: {remaining} 次")
            print(f"       进度: {used}/{used + remaining}")

    def _generate_summary(self, results: Dict):
        """生成执行摘要"""
        total_steps = len(results)
        successful_steps = sum(1 for r in results.values() if r.get("success"))
        failed_steps = total_steps - successful_steps
        
        print(f"\n📊 执行统计:")
        print(f"   总步骤: {total_steps} | 成功: {successful_steps} | 失败: {failed_steps}")