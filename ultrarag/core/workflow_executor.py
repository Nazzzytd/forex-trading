import time
from typing import Dict, Any, List
from .server_manager import ServerManager

class WorkflowExecutor:
    """工作流执行器"""
    
    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager
        self.results = {}
        self.tool_mapping = {}
        self.stored_data = {}
    
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
        
        # 处理输入数据中的变量引用
        resolved_inputs = self._resolve_inputs(inputs)
        
        if tool_name not in self.tool_mapping:
            error_msg = f"工具未找到: {tool_name}"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"   ❌ {error_msg}")
            return
        
        server_type = self.tool_mapping[tool_name]
        
        try:
            result = self.server_manager.call_tool_method(server_type, method, **resolved_inputs)
            
            # 存储原始结果
            self.results[step_name] = {"success": True, "result": result}
            
            # 检查方法调用是否成功
            if result.get("success", False):
                print(f"   ✅ 成功")
                self._display_detailed_data(result)
                
                # 自动存储步骤结果
                self.stored_data[step_name] = result
                
                # 显式存储配置
                store_as = step.get("store_result_as")
                if store_as:
                    self.stored_data[store_as] = result
                            
            else:
                error_msg = result.get("error", "未知错误")
                print(f"   ❌ 失败: {error_msg}")
                self.results[step_name] = {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = str(e) if e else "未知异常"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"   ❌ 异常: {error_msg}")
    
    def _resolve_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """解析输入数据中的变量引用"""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                # 处理变量引用 {{variable}} 或 {{variable.result.data}}
                var_path = value[2:-2].strip()
                resolved_value = self._resolve_variable_path(var_path)
                if resolved_value is not None:
                    resolved[key] = resolved_value
                    print(f"   🔄 解析变量: {key} -> {var_path}")
                else:
                    resolved[key] = value  # 保持原样
                    print(f"   ⚠️  变量未找到: {var_path}")
            else:
                resolved[key] = value
        return resolved

    def _resolve_variable_path(self, var_path: str) -> Any:
        """解析变量路径 - 简化可靠版本"""
        parts = var_path.split('.')
        
        # 首先尝试从存储数据中查找完整路径
        if var_path in self.stored_data:
            return self.stored_data[var_path]
        
        # 然后尝试步骤名查找
        if parts[0] in self.results:
            step_result = self.results[parts[0]]
            
            # 如果没有子路径，返回整个结果
            if len(parts) == 1:
                return step_result.get('result', step_result)
            
            # 有子路径，从result中查找
            result_data = step_result.get('result', {})
            current_data = result_data
            
            # 遍历子路径
            for part in parts[1:]:
                if isinstance(current_data, dict) and part in current_data:
                    current_data = current_data[part]
                else:
                    print(f"   ⚠️  变量路径未找到: {part} 在 {var_path}")
                    return None
            
            return current_data
        
        print(f"   ⚠️  变量未找到: {var_path}")
        return None

    def _display_detailed_data(self, result: Dict[str, Any]):
        """显示详细数据"""
        data_type = result.get("data_type")
        currency_pair = result.get("symbol", result.get("currency_pair", "未知"))
        
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
                
        elif "indicators_calculated" in result:
            # 技术指标计算结果
            indicators_count = len(result.get("indicators_calculated", []))
            record_count = result.get("record_count", 0)
            symbol = result.get("symbol", "未知")
            
            print(f"     📊 {symbol} 技术指标")
            print(f"       数据点数: {record_count}")
            print(f"       计算指标: {indicators_count} 个")
            if result.get("latest_timestamp"):
                print(f"       最新时间: {result['latest_timestamp']}")
                
        elif "composite_signal" in result:
            # 交易信号结果 - 优化显示格式
            self._display_trading_signals(result)
            
        elif "status" in result:
            # 健康检查或状态信息
            status = result.get("status", "unknown")
            print(f"     🩺 状态: {status}")
            if "ai_enabled" in result:
                print(f"       AI功能: {'启用' if result['ai_enabled'] else '禁用'}")
            if "indicators_working" in result:
                print(f"       指标计算: {'正常' if result['indicators_working'] else '异常'}")
                
        elif "indicators_config" in result:
            # 配置信息
            config = result.get("indicators_config", {})
            ai_enabled = result.get("ai_enabled", False)
            print(f"     ⚙️  分析配置")
            print(f"       AI分析: {'启用' if ai_enabled else '禁用'}")
            print(f"       RSI周期: {config.get('rsi_period', 'N/A')}")
            print(f"       MACD配置: {config.get('macd_fast', 'N/A')}/{config.get('macd_slow', 'N/A')}")

    def _display_trading_signals(self, result: Dict[str, Any]):
        """专门显示交易信号 - 优化格式"""
        symbol = result.get("symbol", "未知")
        price = result.get("price", 0)
        composite = result.get("composite_signal", {})
        
        # 交易信号头部
        print(f"     🎯 {symbol} 交易信号")
        print(f"     {'='*50}")
        
        # 核心交易信息
        recommendation = composite.get('recommendation', '未知')
        confidence = composite.get('confidence', 0)
        
        # 根据建议类型显示不同的表情符号
        if recommendation == "买入":
            signal_emoji = "🟢"
        elif recommendation == "卖出":
            signal_emoji = "🔴"
        else:
            signal_emoji = "🟡"
        
        print(f"     {signal_emoji} 交易建议: {recommendation}")
        print(f"     📊 置信度: {confidence}%")
        print(f"     💰 当前价格: {price:.5f}")
        print()
        
        # 技术指标概览
        print(f"     🔍 技术指标概览:")
        indicators = [
            ("RSI", result.get('rsi', {}).get('value'), result.get('rsi', {}).get('signal')),
            ("MACD", None, result.get('macd', {}).get('signal')),
            ("布林带", result.get('bollinger_bands', {}).get('position'), result.get('bollinger_bands', {}).get('signal')),
            ("趋势", result.get('trend', {}).get('strength'), result.get('trend', {}).get('direction')),
        ]
        
        for name, value, signal in indicators:
            if value is not None:
                if isinstance(value, float):
                    value_str = f"{value:.2f}"
                else:
                    value_str = str(value)
                print(f"        {name}: {value_str} - {signal}")
            else:
                print(f"        {name}: {signal}")
        
        print()
        
        # 信号统计
        bullish = composite.get('bullish_signals', 0)
        bearish = composite.get('bearish_signals', 0)
        print(f"     📈 信号统计:")
        print(f"       看涨信号: {bullish} {'✅' if bullish > bearish else ''}")
        print(f"       看跌信号: {bearish} {'✅' if bearish > bullish else ''}")
        
        # 显示AI分析结果
        if "ai_analysis" in result:
            print()
            self._display_ai_analysis(result["ai_analysis"])

    def _display_ai_analysis(self, ai_analysis: Dict):
        """专门显示AI分析结果 - 优化格式"""
        if "analysis" in ai_analysis:
            print(f"     🤖 AI专业分析")
            print(f"     {'='*50}")
            
            analysis_text = ai_analysis["analysis"]
            
            # 提取关键交易信息
            key_sections = self._extract_trading_insights(analysis_text)
            
            # 显示关键交易要点
            if key_sections:
                print(f"     💡 关键交易要点:")
                for section in key_sections:
                    print(f"       • {section}")
                print()
            
            # 显示完整的AI分析（不截断）
            print(f"     📝 详细分析:")
            
            # 按段落处理，保持原有结构
            paragraphs = analysis_text.split('\n\n')
            
            for i, paragraph in enumerate(paragraphs):
                paragraph = paragraph.strip()
                if paragraph:
                    # 清理标题格式
                    clean_paragraph = paragraph.replace('###', '').strip()
                    
                    # 如果是标题段落，加粗显示
                    if clean_paragraph and len(clean_paragraph) < 50 and ':' not in clean_paragraph:
                        print(f"       🔹 {clean_paragraph}")
                    else:
                        # 普通段落进行换行处理
                        wrapped_lines = self._wrap_text(clean_paragraph, width=55)
                        for line in wrapped_lines:
                            print(f"       {line}")
                    
                    # 段落间空行
                    if i < len(paragraphs) - 1:
                        print()
            
            if "timestamp" in ai_analysis:
                print(f"     ⏰ 分析时间: {ai_analysis['timestamp']}")
            print(f"     {'='*50}")
                    
        elif "error" in ai_analysis:
            print(f"     ❌ AI分析失败: {ai_analysis['error']}")

    def _extract_trading_insights(self, analysis_text: str) -> List[str]:
        """从AI分析中提取关键交易要点"""
        insights = []
        lines = analysis_text.split('\n')
        
        # 寻找关键信息的关键词
        keywords = ['入场点', '止损', '目标', '支撑位', '阻力位', '建议', '机会', '入场', '止损点', '目标位']
        
        for line in lines:
            line = line.strip()
            # 寻找包含关键信息的行，且不是标题行
            if any(keyword in line for keyword in keywords) and len(line) > 10 and not line.startswith('###'):
                # 清理格式
                clean_line = line.replace('###', '').replace('-', '').replace('*', '').strip()
                if clean_line and len(clean_line) <= 80 and clean_line not in insights:
                    insights.append(clean_line)
        
        return insights[:6]  # 返回前6个关键要点

    def _wrap_text(self, text: str, width: int = 55) -> List[str]:
        """文本换行处理"""
        # 如果文本很短，直接返回
        if len(text) <= width:
            return [text]
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines