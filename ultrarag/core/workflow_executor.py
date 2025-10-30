import time
import re
from typing import Dict, Any, List, Union, Optional
from .server_manager import ServerManager 
import pandas as pd # 导入 pandas 用于处理时间戳

# SimpleMustache 保持最简状态
class SimpleMustache:
    """简单的 Mustache 模板引擎"""
    
    @staticmethod
    def render(template: str, context: Dict) -> str:
        """渲染 Mustache 模板"""
        if not template:
            return template
        template = SimpleMustache._render_variables(template, context)
        template = SimpleMustache._render_condition_blocks(template, context)
        return template
    
    @staticmethod
    def _render_condition_blocks(template: str, context: Dict) -> str:
        pattern = r'{{#(.*?)}}(.*?){{/\1}}'
        
        def replace_condition(match):
            condition_key = match.group(1).strip()
            block_content = match.group(2)
            condition_value = SimpleMustache._get_value(condition_key, context)
            is_truthy = SimpleMustache._is_truthy(condition_value)
            
            if is_truthy:
                return block_content
            else:
                return ""
        
        return re.sub(pattern, replace_condition, template, flags=re.DOTALL)
    
    @staticmethod
    def _render_variables(template: str, context: Dict) -> str:
        pattern = r'{{(.*?)}}'
        
        def replace_variable(match):
            var_key = match.group(1).strip()
            
            if var_key.startswith('#') or var_key.startswith('^') or var_key.startswith('/'):
                return match.group(0)
            
            value = SimpleMustache._get_value(var_key, context)
            
            if value is not None:
                # 核心修正：如果变量是字典，返回其字符串表示，但更好的格式化应该在外部处理
                return str(value)
            else:
                return match.group(0)
        
        return re.sub(pattern, replace_variable, template)
    
    @staticmethod
    def _get_value(key: str, context: Dict) -> Any:
        if not key:
            return None
            
        if key.startswith('$'):
            key = key[1:]
        
        parts = key.split('.')
        current = context
        
        for i, part in enumerate(parts):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    @staticmethod
    def _is_truthy(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.lower() not in ['false', 'no', '0', '']
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True
# --- SimpleMustache 结束 ---


class WorkflowExecutor:
    """工作流执行器 - 最终精简输出版"""
    
    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager
        self.results = {}
        self.tool_mapping = {}
        self.stored_data = {}
        # 假设 ServerManager 已处理 verbose，Executor 保持精简输出
        self.verbose = False 
        self.branch_states = {}
        self.loop_counters = {}
    
    def execute_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流 - 仅打印工作流名称"""
        workflow_name = workflow_config.get("name", "未命名工作流")
        interactive_mode = workflow_config.get('_interactive_mode', False)
        provided_params = workflow_config.get('_provided_params', {})
        
        # 打印工作流名称 (保持不变)
        print(f"📋 {workflow_name}")
        
        self.stored_data = workflow_config.get("variables", {}).copy()
        self.branch_states = {}
        self.loop_counters = {}
        
        # 启动工具服务器 (不打印任何信息)
        tools = workflow_config.get("tools", [])
        for tool_config in tools:
            self._start_tool_server(tool_config)
        
        # 执行工作流步骤
        steps = workflow_config.get("workflow", [])
        result = self._execute_steps(steps, interactive_mode, provided_params)
        
        return self.results

    def _execute_steps(self, steps: List[Dict[str, Any]], interactive_mode: bool = False, 
                     provided_params: Dict = None, context: Dict = None) -> Any:
        """执行步骤序列"""
        context = context or {}
        result = None
        
        for step in steps:
            step_result = self._execute_step(step, interactive_mode, provided_params, context)
            if step_result is not None:
                result = step_result
                
        return result

    def _execute_step(self, step: Dict[str, Any], interactive_mode: bool = False, 
                    provided_params: Dict = None, context: Dict = None) -> Any:
        """执行单个步骤 - 精简步骤名称输出"""
        context = context or {}
        step_name = step.get("step", "未知步骤")
        step_type = step.get("type", "tool")
        
        # 仅输出步骤名称，不换行，末尾留一个空格 (保持不变)
        print(f"🔹 {step_name}", end=" ")
        
        try:
            if step_type == "print":
                return self._execute_print_step(step, context)
            elif step_type == "tool":
                return self._execute_tool_step(step, context)
            elif step_type == "input":
                return self._execute_input_step(step, interactive_mode, provided_params, context)
            elif step_type == "set_variable":
                return self._execute_set_variable_step(step, context)
            elif step_type == "loop":
                return self._execute_loop_step(step, interactive_mode, provided_params, context)
            elif step_type == "branch":
                return self._execute_branch_step(step, interactive_mode, provided_params, context)
            elif step_type == "router":
                return self._execute_router_step(step, interactive_mode, provided_params, context)
            else:
                error_msg = f"未知的步骤类型: {step_type}"
                self.results[step_name] = {"success": False, "error": error_msg}
                print(f"❌ {error_msg}")
                return None
        except Exception as e:
            error_msg = f"步骤执行失败: {str(e)}"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"❌ {error_msg}")
            return None

    # =======================================================
    # ========== 核心格式化方法 - 解决报告输出混乱问题 ==========
    # =======================================================

    def _format_analysis_result(self, data: Dict[str, Any], level=0) -> List[str]:
        """递归格式化嵌套的字典/列表为清晰的文本行"""
        output = []
        indent = "  " * level
        
        # 优先处理 AI 深度分析，如果是纯文本/Markdown，直接返回
        if level == 0 and 'analysis' in data and isinstance(data['analysis'], str):
            return [data['analysis'].strip()]

        for key, value in data.items():
            if key in ('success', 'timestamp', 'analysis_type', 'data_type', 'result'): # 忽略内部元数据
                continue
            
            # 处理字典
            if isinstance(value, dict):
                output.append(f"{indent}🔹 **{key.replace('_', ' ').title()}**:")
                output.extend(self._format_analysis_result(value, level + 1))
            
            # 处理列表
            elif isinstance(value, list):
                output.append(f"{indent}🔹 **{key.replace('_', ' ').title()}**: (共{len(value)}项)")
                for item in value:
                    if isinstance(item, dict):
                        output.append(f"{indent}  -")
                        output.extend(self._format_analysis_result(item, level + 2))
                    else:
                        output.append(f"{indent}  - {item}")
            
            # 处理基本类型
            else:
                # 格式化数值，保留四位小数，并添加千位分隔符
                if isinstance(value, (int, float)):
                    formatted_value = f"{value:,.4f}" if value != int(value) else f"{int(value):,}"
                    output.append(f"{indent}• {key.replace('_', ' ').title()}: {formatted_value}")
                else:
                    output.append(f"{indent}• {key.replace('_', ' ').title()}: {value}")
                    
        return output

    def _format_tool_results_in_message(self, message: str, context: Dict) -> str:
        """在打印消息中，找到模板变量并将其原始字典值替换为格式化后的文本"""
        
        pattern = r'{{(.*?)}}'
        
        def replace_and_format(match):
            var_key = match.group(1).strip()
            
            # 获取变量的原始值
            value = SimpleMustache._get_value(var_key, context)
            
            # 如果原始值是字典，并且不是空字典，则进行格式化
            if isinstance(value, dict) and value:
                # 使用变量名作为标题（去除可能的 $ 前缀）
                title = var_key.split('.')[-1].replace('_', ' ').title()
                
                # 针对 AI 分析，将标题替换为更具描述性的内容
                if 'analysis' in value and isinstance(value['analysis'], str):
                    title = "AI 深度分析"
                    
                # 格式化并返回文本
                formatted_lines = self._format_analysis_result(value)
                
                # 构建最终的输出块 (使用 Markdown 格式)
                header = f"\n\n## {title}"
                separator = "─" * len(title)
                
                return f"{header}\n{separator}\n" + "\n".join(formatted_lines)
            
            # 否则，使用 SimpleMustache 的默认渲染逻辑
            return SimpleMustache.render(match.group(0), context)

        return re.sub(pattern, replace_and_format, message, flags=re.DOTALL)


    # ========== 打印步骤 ==========
    def _execute_print_step(self, step: Dict[str, Any], context: Dict = None) -> Any:
        """执行打印步骤 - 最终输出"""
        try:
            config = step.get("config", {})
            message = config.get("message", "")
            full_context = self._build_full_context(context)
            
            # *** 关键修改：先格式化消息中的字典变量 ***
            resolved_message = self._format_tool_results_in_message(message, full_context)
            
            # 之后再进行一次简单的 Mustache 渲染，处理剩下的简单变量
            resolved_message = SimpleMustache.render(resolved_message, full_context)
            
            # 打印消息
            print(f"\r{resolved_message}") 
            
            result = {"success": True, "result": resolved_message}
            self.results[step.get("step", "print_step")] = result
            
            return result
            
        except Exception as e:
            error_msg = f"打印步骤失败: {str(e)}"
            result = {"success": False, "error": error_msg}
            self.results[step.get("step", "print_step")] = result
            print(f"❌ {error_msg}")
            return result

    # ========== 输入步骤 ==========
    def _execute_input_step(self, step: Dict[str, Any], interactive_mode: bool = False,
                          provided_params: Dict = None, context: Dict = None) -> Any:
        """执行输入步骤 - 确保提示符简洁且输入在一行"""
        try:
            config = step.get("config", {})
            prompt = config.get("prompt", "请输入:")
            var_name = step.get("output")
            default_value = config.get("default", "")
            
            if not var_name:
                error_msg = "输入步骤缺少 output 字段"
                self.results[step.get("step", "input_step")] = {"success": False, "error": error_msg}
                print(f"❌ {error_msg}")
                return None
            
            full_prompt = prompt
            if default_value:
                full_prompt += f" [默认: {default_value}]"
            
            # 使用回车符 \r 覆盖前面的 "🔹 select_currency_pair "
            user_input = input(f"\r{full_prompt}: ").strip()
            
            if not user_input and default_value:
                user_input = default_value
            
            is_valid, validated_value, error_msg = self._validate_input(user_input, config)
            
            if is_valid:
                stored_value = validated_value if validated_value is not None else user_input
                self.stored_data[var_name] = stored_value
                self.results[step.get("step", "input_step")] = {"success": True, "result": stored_value}
                
                print(f"✅ (已保存到: {var_name})") 
                
                return stored_value
            else:
                error_msg = f"输入验证失败: {error_msg}"
                self.results[step.get("step", "input_step")] = {"success": False, "error": error_msg}
                print(f"❌ {error_msg}")
                return None
                
        except KeyboardInterrupt:
            print("\n⚠️  用户取消输入")
            self.results[step.get("step", "input_step")] = {"success": False, "error": "用户取消输入"}
            raise
        except Exception as e:
            error_msg = f"输入步骤失败: {str(e)}"
            self.results[step.get("step", "input_step")] = {"success": False, "error": error_msg}
            print(f"❌ {error_msg}")
            return None

    # ========== 工具步骤 ==========
    def _execute_tool_step(self, step: Dict[str, Any], context: Dict = None) -> Any:
        """执行工具步骤 - 关键修改以应对工具内部输出"""
        step_name = step.get("step", "未知步骤")
        tool_name = step.get("tool")
        inputs = step.get("inputs", {})
        method = step.get("method", "fetch_data")
        
        store_var = step.get("store_result_as") or step.get("output")
        
        if tool_name not in self.tool_mapping:
            error_msg = f"工具未找到: {tool_name}"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"❌ 工具未找到: {tool_name}")
            return None
        
        server_type = self.tool_mapping[tool_name]
        
        try:
            full_context = self._build_full_context(context)
            resolved_inputs = self._resolve_inputs_with_mustache(inputs, full_context)
            
            # 在调用工具之前，先打印一个空的回车，用于覆盖步骤名称 (保持不变)
            print(f"\r🔹 {step_name}...", end="") 
            
            result = self.server_manager.call_tool_method(server_type, method, **resolved_inputs)
            
            self.results[step_name] = {"success": True, "result": result}
            
            if store_var:
                self.stored_data[store_var] = result
            
            self.stored_data[step_name] = result
            
            if result.get("success", False):
                # 打印成功提示，并换行
                print(f"\r✅ {step_name} ({tool_name}: {method})", end="")
                if store_var:
                    print(f" (已保存到: {store_var})")
                else:
                    print("")
                
                # 尝试再次精简 summary data 的打印（如果存在的话）
                self._display_summary_data(result)

            else:
                # 失败时打印错误信息
                print("❌")
                error_msg = result.get("error", "未知错误")
                self.results[step_name] = {"success": False, "error": error_msg}
                print(f"❌ {tool_name} 失败: {error_msg}")
            
            return result
            
        except Exception as e:
            print("❌")
            error_msg = str(e) if e else "未知异常"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"❌ 异常: {error_msg}")
            return None
        finally:
            # 无论成功失败，确保换行，并准备下一个步骤的输出
            if not result or not result.get("success", False):
                print("") # 确保失败时也换行

    # --- 其他辅助方法 ---
    def _start_tool_server(self, tool_config: Dict[str, Any]):
        """启动工具服务器 - 仅调用，不打印任何信息"""
        tool_name = tool_config["name"]
        server_type = tool_config["server_type"]
        self.tool_mapping[tool_name] = server_type
        
        server_config = {
            "server_type": server_type,
            "parameters": tool_config.get("parameters", {})
        }
        # 注意：此处 start_server 应该接收 self.verbose，
        # 但我们假设 ServerManager 已经在其 __init__ 中处理了 verbose 设置。
        self.server_manager.start_server(server_type, server_config)

    def _execute_set_variable_step(self, step: Dict[str, Any], context: Dict = None) -> Any:
        """执行设置变量步骤"""
        step_name = step.get("step", "set_variable_step")
        config = step.get("config", {})
        var_name = config.get("variable")
        value = config.get("value")
        
        if not var_name:
            error_msg = "设置变量步骤缺少 variable 字段"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"❌ {error_msg}")
            return None
        
        full_context = self._build_full_context(context)
        resolved_value = SimpleMustache.render(str(value), full_context) if isinstance(value, str) else value
        self.stored_data[var_name] = resolved_value
        
        print(f"✅ (已保存到: {var_name})")
        
        result = {"success": True, "result": resolved_value}
        self.results[step_name] = result
        return result

    def _display_summary_data(self, result: Dict[str, Any]):
        """在非 verbose 模式下，仅显示关键结果的总结"""
        data_type = result.get("data_type")
        
        if data_type == "realtime" and "data" in result:
            data = result["data"]
            currency_pair = result.get("symbol", result.get("currency_pair", "未知"))
            rate = data.get("exchange_rate")
            change = data.get("percent_change")

            if rate is not None and change is not None:
                # 打印到新行，并精简信息
                print(f"   [结果] 💹 {currency_pair} | 汇率: {rate:.4f} | 涨跌: {change:+.2f}%")
        elif 'analysis' in result and isinstance(result['analysis'], str):
            # 对于分析工具，不打印任何额外的详细数据，让后续的 print 步骤来处理
            pass
        else:
            # 默认不打印，保持简洁
            pass

    # ... (其他辅助方法和执行逻辑保持不变)
    
    def _resolve_inputs_with_mustache(self, inputs: Dict[str, Any], context: Dict) -> Dict[str, Any]:
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and ("{{" in value or "}}" in value):
                pure_var_match = re.match(r'^{{(.*)}}$', value.strip())
                if pure_var_match:
                    var_path = pure_var_match.group(1).strip()
                    resolved_value = SimpleMustache._get_value(var_path, context)
                    if resolved_value is not None:
                        resolved[key] = resolved_value
                    else:
                        resolved[key] = value
                else:
                    resolved_value = SimpleMustache.render(value, context)
                    resolved[key] = resolved_value
            else:
                resolved[key] = value
        return resolved

    def _build_full_context(self, context: Dict = None) -> Dict[str, Any]:
        full_context = {}
        full_context.update(self.stored_data)
        for key, value in self.results.items():
            if isinstance(value, dict) and 'result' in value:
                full_context[key] = value['result']
            else:
                full_context[key] = value
        if context:
            full_context.update(context)
        full_context.update({'stored_data': self.stored_data, 'results': self.results})
        return full_context

    def _execute_loop_step(self, step: Dict[str, Any], interactive_mode: bool = False,
                         provided_params: Dict = None, context: Dict = None) -> Any:
        step_name = step.get("step", "loop_step")
        config = step.get("config", {})
        times = config.get("times", 1)
        loop_steps = config.get("steps", [])
        print(f"\r🔄 {step_name} 循环 {times} 次...", end="")
        final_result = None
        for i in range(times):
            result = self._execute_steps(loop_steps, interactive_mode, provided_params, context)
            if result is not None:
                final_result = result
        print(f"\r✅ {step_name} 循环结束")
        return final_result

    def _execute_branch_step(self, step: Dict[str, Any], interactive_mode: bool = False,
                           provided_params: Dict = None, context: Dict = None) -> Any:
        print("\r🚦 分支步骤 (未执行)")
        return None

    def _execute_router_step(self, step: Dict[str, Any], interactive_mode: bool = False,
                           provided_params: Dict = None, context: Dict = None) -> Any:
        print("\r🎯 路由器步骤 (未执行)")
        return None

    def _validate_input(self, value: str, config: Dict) -> tuple[bool, Any, str]:
        input_type = config.get("type", "string")
        required = config.get("required", False)
        
        if required and not value:
            return False, None, "此字段为必填项"
        
        if not value and not required:
            return True, None, ""
        
        try:
            if input_type == "string":
                min_length = config.get("min_length")
                max_length = config.get("max_length")
                
                if min_length and len(value) < min_length:
                    return False, None, f"输入长度不能少于 {min_length} 个字符"
                if max_length and len(value) > max_length:
                    return False, None, f"输入长度不能超过 {max_length} 个字符"
                
                return True, value, ""
                
            elif input_type == "integer":
                int_value = int(value)
                min_val = config.get("min")
                max_val = config.get("max")
                
                if min_val is not None and int_value < min_val:
                    return False, None, f"数值不能小于 {min_val}"
                if max_val is not None and int_value > max_val:
                    return False, None, f"数值不能大于 {max_val}"
                
                return True, int_value, ""
                
            elif input_type == "float":
                float_value = float(value)
                min_val = config.get("min")
                max_val = config.get("max")
                
                if min_val is not None and float_value < min_val:
                    return False, None, f"数值不能小于 {min_val}"
                if max_val is not None and float_value > max_val:
                    return False, None, f"数值不能大于 {max_val}"
                
                return True, float_value, ""
                
            elif input_type == "choice":
                choices = config.get("choices", [])
                if value not in choices:
                    return False, None, f"请输入有效的选项: {', '.join(choices)}"
                return True, value, ""
                
            else:
                return True, value, ""
                
        except ValueError as e:
            return False, None, f"输入格式错误: {str(e)}"
