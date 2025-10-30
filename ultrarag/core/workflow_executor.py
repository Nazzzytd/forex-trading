import time
import re
from typing import Dict, Any, List, Union, Optional
from .server_manager import ServerManager

class SimpleMustache:
    """简单的 Mustache 模板引擎"""
    
    @staticmethod
    def render(template: str, context: Dict) -> str:
        """渲染 Mustache 模板"""
        if not template:
            return template
            
        print(f"   🔍 Mustache 渲染模板: '{template}'")  # 调试
        
        # 先处理变量，再处理条件块（这样条件块中的变量也能被解析）
        template = SimpleMustache._render_variables(template, context)
        template = SimpleMustache._render_condition_blocks(template, context)
        
        print(f"   ✅ Mustache 渲染结果: '{template}'")  # 调试
        
        return template
    
    @staticmethod
    def _render_condition_blocks(template: str, context: Dict) -> str:
        """处理条件块"""
        # 使用非贪婪匹配，支持多行
        pattern = r'{{#(.*?)}}(.*?){{/\1}}'
        
        def replace_condition(match):
            condition_key = match.group(1).strip()
            block_content = match.group(2)
            
            print(f"   🔍 处理条件块: {condition_key}")  # 调试
            
            # 检查条件是否为真
            condition_value = SimpleMustache._get_value(condition_key, context)
            is_truthy = SimpleMustache._is_truthy(condition_value)
            
            print(f"   🔍 条件值: {condition_value} -> {is_truthy}")  # 调试
            
            if is_truthy:
                return block_content
            else:
                return ""
        
        # 使用 DOTALL 标志支持多行
        return re.sub(pattern, replace_condition, template, flags=re.DOTALL)
    
    @staticmethod
    def _render_variables(template: str, context: Dict) -> str:
        """处理变量 - 修复版本"""
        pattern = r'{{(.*?)}}'
        
        def replace_variable(match):
            var_key = match.group(1).strip()
            
            # 跳过条件块标记
            if var_key.startswith('#') or var_key.startswith('^') or var_key.startswith('/'):
                return match.group(0)
            
            print(f"   🔍 处理变量: {var_key}")  # 调试
            
            value = SimpleMustache._get_value(var_key, context)
            
            if value is not None:
                result = str(value)
                print(f"   ✅ 变量解析: {var_key} -> {result}")  # 调试
                return result
            else:
                print(f"   ⚠️  变量未找到: {var_key}")  # 调试
                return match.group(0)  # 保持原样
        
        return re.sub(pattern, replace_variable, template)
    
    @staticmethod
    def _get_value(key: str, context: Dict) -> Any:
        """从上下文中获取值，支持点符号 - 增强调试"""
        if not key:
            return None
            
        print(f"   🔍 查找变量路径: '{key}'")  # 调试
        
        # 处理 $ 开头的用户输入变量
        if key.startswith('$'):
            key = key[1:]
        
        # 支持点符号路径
        parts = key.split('.')
        current = context
        
        for i, part in enumerate(parts):
            print(f"   🔍 查找部分 {i+1}/{len(parts)}: '{part}'")  # 调试
            
            if isinstance(current, dict) and part in current:
                current = current[part]
                print(f"   ✅ 找到: '{part}' -> {type(current).__name__}")  # 调试
            else:
                print(f"   ❌ 未找到: '{part}'")  # 调试
                print(f"   📋 当前对象键: {list(current.keys()) if isinstance(current, dict) else '非字典'}")  # 调试
                return None
        
        return current
    
    @staticmethod
    def _is_truthy(value: Any) -> bool:
        """检查值是否为真"""
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

class WorkflowExecutor:
    """工作流执行器 - 增强版支持复杂流水线"""
    
    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager
        self.results = {}
        self.tool_mapping = {}
        self.stored_data = {}
        self.verbose = True  # 默认详细模式
        self.branch_states = {}  # 分支状态管理
        self.loop_counters = {}  # 循环计数器
    
    def execute_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流 - 增强版支持混合模式和复杂流水线"""
        workflow_name = workflow_config.get("name", "未命名工作流")
        interactive_mode = workflow_config.get('_interactive_mode', False)
        provided_params = workflow_config.get('_provided_params', {})
        
        if self.verbose:
            print(f"🚀 执行工作流: {workflow_name}")
            if interactive_mode:
                print("   🔘 混合模式: 已提供参数将跳过交互输入")
        else:
            print(f"📋 {workflow_name}")
        
        # 初始化存储数据，包含工作流变量
        self.stored_data = workflow_config.get("variables", {}).copy()
        self.branch_states = {}  # 重置分支状态
        self.loop_counters = {}  # 重置循环计数器
        
        # 启动所有工具服务器
        tools = workflow_config.get("tools", [])
        for tool_config in tools:
            self._start_tool_server(tool_config)
        
        # 执行工作流步骤
        steps = workflow_config.get("workflow", [])
        result = self._execute_steps(steps, interactive_mode, provided_params)
        
        if self.verbose:
            print(f"✅ 工作流执行完成")
        
        return self.results

    def _execute_steps(self, steps: List[Dict[str, Any]], interactive_mode: bool = False, 
                     provided_params: Dict = None, context: Dict = None) -> Any:
        """执行步骤序列 - 支持复杂流水线"""
        context = context or {}
        result = None
        
        for step in steps:
            step_result = self._execute_step(step, interactive_mode, provided_params, context)
            if step_result is not None:
                result = step_result
                
        return result

    def _execute_step(self, step: Dict[str, Any], interactive_mode: bool = False, 
                    provided_params: Dict = None, context: Dict = None) -> Any:
        """执行单个步骤 - 增强版支持复杂流水线"""
        context = context or {}
        step_name = step.get("step", "未知步骤")
        step_type = step.get("type", "tool")
        
        if self.verbose:
            print(f"\n🔹 {step_name}")
        
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
                if self.verbose:
                    print(f"   ❌ {error_msg}")
                else:
                    print(f"❌ {step_name}: {error_msg}")
                return None
        except Exception as e:
            error_msg = f"步骤执行失败: {str(e)}"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"❌ {step_name}: {error_msg}")
            return None

    # ========== 打印步骤 ==========
    def _execute_print_step(self, step: Dict[str, Any], context: Dict = None) -> Any:
        """执行打印步骤 - 支持完整的 Mustache 语法"""
        try:
            config = step.get("config", {})
            message = config.get("message", "")
            
            # 构建完整的上下文
            full_context = self._build_full_context(context)
            
            if self.verbose:
                print(f"   📝 渲染消息模板")
                print(f"   🔍 原始消息: {message}")
                print(f"   📋 可用上下文: {list(full_context.keys())}")
            
            # 使用 Mustache 渲染模板
            resolved_message = SimpleMustache.render(message, full_context)
            
            if self.verbose and message != resolved_message:
                print(f"   ✅ 渲染后消息: {resolved_message}")
            
            # 输出消息
            print(resolved_message)
            
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
        """执行输入步骤 - 修复变量存储问题"""
        try:
            config = step.get("config", {})
            prompt = config.get("prompt", "请输入:")
            var_name = step.get("output")  # 获取输出变量名
            default_value = config.get("default", "")
            
            if not var_name:
                error_msg = "输入步骤缺少 output 字段"
                self.results[step.get("step", "input_step")] = {
                    "success": False,
                    "error": error_msg
                }
                print(f"❌ {error_msg}")
                return None
            
            # 获取用户输入
            full_prompt = prompt
            if default_value:
                full_prompt += f" [默认: {default_value}]"
            full_prompt += ": "
            
            user_input = input(f"   {full_prompt}").strip()
            
            # 如果用户没有输入，使用默认值
            if not user_input and default_value:
                user_input = default_value
                if self.verbose:
                    print(f"   💡 使用默认值: {default_value}")
            
            # 验证输入
            is_valid, validated_value, error_msg = self._validate_input(user_input, config)
            
            if is_valid:
                # 存储用户输入到 stored_data
                stored_value = validated_value if validated_value is not None else user_input
                self.stored_data[var_name] = stored_value
                
                # 同时存储到 results
                self.results[step.get("step", "input_step")] = {
                    "success": True, 
                    "result": stored_value
                }
                
                if self.verbose:
                    print(f"   ✅ 输入已保存到 stored_data: {var_name} = {stored_value}")
                    print(f"   📋 当前 stored_data 键: {list(self.stored_data.keys())}")
                
                return stored_value
            else:
                error_msg = f"输入验证失败: {error_msg}"
                self.results[step.get("step", "input_step")] = {
                    "success": False,
                    "error": error_msg
                }
                print(f"   ❌ {error_msg}")
                return None
                
        except KeyboardInterrupt:
            print("\n⚠️  用户取消输入")
            self.results[step.get("step", "input_step")] = {
                "success": False,
                "error": "用户取消输入"
            }
            raise
        except Exception as e:
            error_msg = f"输入步骤失败: {str(e)}"
            self.results[step.get("step", "input_step")] = {
                "success": False,
                "error": error_msg
            }
            print(f"❌ {error_msg}")
            return None

    # ========== 工具步骤 ==========
    def _execute_tool_step(self, step: Dict[str, Any], context: Dict = None) -> Any:
        """执行工具步骤 - 修复变量解析"""
        step_name = step.get("step", "未知步骤")
        tool_name = step.get("tool")
        inputs = step.get("inputs", {})
        method = step.get("method", "fetch_data")
        
        store_var = step.get("store_result_as") or step.get("output")
        
        if self.verbose:
            print(f"   🔧 执行工具步骤: {step_name}")
            print(f"   📦 存储变量: {store_var}")
            print(f"   🔍 原始输入: {inputs}")
            print(f"   📋 当前 stored_data 键: {list(self.stored_data.keys())}")
    
        if tool_name not in self.tool_mapping:
            error_msg = f"工具未找到: {tool_name}"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"❌ {error_msg}")
            return None
        
        server_type = self.tool_mapping[tool_name]
        
        try:
            # 构建完整上下文
            full_context = self._build_full_context(context)
            
            # 处理输入数据中的变量引用
            resolved_inputs = self._resolve_inputs_with_mustache(inputs, full_context)
            
            if self.verbose:
                print(f"   ✅ 解析后输入: {resolved_inputs}")
            
            result = self.server_manager.call_tool_method(server_type, method, **resolved_inputs)
            
            # 存储结果
            self.results[step_name] = {"success": True, "result": result}
            
            if store_var:
                self.stored_data[store_var] = result
                if self.verbose:
                    print(f"   💾 存储到 stored_data['{store_var}']")
            
            self.stored_data[step_name] = result
            
            if result.get("success", False):
                if self.verbose:
                    print(f"   ✅ 成功")
                    self._display_detailed_data(result)
                else:
                    print(" ✅")
            else:
                if not self.verbose:
                    print(" ❌")
                error_msg = result.get("error", "未知错误")
                self.results[step_name] = {"success": False, "error": error_msg}
                print(f"   ❌ 失败: {error_msg}")
            
            return result
            
        except Exception as e:
            if not self.verbose:
                print(" ❌")
            error_msg = str(e) if e else "未知异常"
            self.results[step_name] = {"success": False, "error": error_msg}
            print(f"   ❌ 异常: {error_msg}")
            return None

    def _resolve_inputs_with_mustache(self, inputs: Dict[str, Any], context: Dict) -> Dict[str, Any]:
        """使用 Mustache 解析输入数据中的变量引用 - 增强版支持对象引用"""
        resolved = {}
        
        if self.verbose:
            print(f"   🔍 开始解析输入:")
            print(f"   📋 可用上下文键: {list(context.keys())}")
        
        for key, value in inputs.items():
            if isinstance(value, str) and ("{{" in value or "}}" in value):
                if self.verbose:
                    print(f"   🔍 解析输入 {key}: {value}")
                
                # 检查是否是纯变量引用（没有其他文本）
                pure_var_match = re.match(r'^{{(.*)}}$', value.strip())
                if pure_var_match:
                    # 纯变量引用，直接获取对象
                    var_path = pure_var_match.group(1).strip()
                    resolved_value = SimpleMustache._get_value(var_path, context)
                    if resolved_value is not None:
                        resolved[key] = resolved_value
                        if self.verbose:
                            print(f"   ✅ 纯变量引用: {key} = '{value}' -> {type(resolved_value).__name__}")
                    else:
                        # 变量未找到，保持原样
                        resolved[key] = value
                        if self.verbose:
                            print(f"   ⚠️  变量未找到: {key} = '{value}'")
                else:
                    # 混合文本，使用 Mustache 渲染
                    resolved_value = SimpleMustache.render(value, context)
                    resolved[key] = resolved_value
                    if self.verbose:
                        if value != resolved_value:
                            print(f"   ✅ 模板渲染: {key} = '{value}' -> '{resolved_value}'")
                        else:
                            print(f"   ⚠️  渲染失败，保持原样: {key} = '{value}'")
            else:
                resolved[key] = value
        
        return resolved

    def _build_full_context(self, context: Dict = None) -> Dict[str, Any]:
        """构建完整的上下文，包含所有可用数据"""
        full_context = {}
        
        # 添加存储的数据（优先级最高）
        full_context.update(self.stored_data)
        
        # 添加步骤结果
        for key, value in self.results.items():
            if isinstance(value, dict) and 'result' in value:
                # 展开 result 字段
                full_context[key] = value['result']
            else:
                full_context[key] = value
        
        # 添加上下文
        if context:
            full_context.update(context)
        
        # 添加特殊访问器
        full_context.update({
            'stored_data': self.stored_data,
            'results': self.results
        })
        
        if self.verbose:
            print(f"   📋 完整上下文构建完成:")
            print(f"   🔑 存储数据: {list(self.stored_data.keys())}")
            print(f"   🔑 步骤结果: {list(self.results.keys())}")
            for key in ['technical_data', 'economic_data', 'currency_pair']:
                if key in full_context:
                    print(f"   💡 {key}: {type(full_context[key]).__name__}")
        
        return full_context

    # ========== 其他步骤类型（简化版） ==========
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
        
        # 解析值中的变量引用
        full_context = self._build_full_context(context)
        resolved_value = SimpleMustache.render(str(value), full_context) if isinstance(value, str) else value
        
        # 存储变量
        self.stored_data[var_name] = resolved_value
        
        if self.verbose:
            print(f"   💾 设置变量: {var_name} = {resolved_value}")
        
        result = {"success": True, "result": resolved_value}
        self.results[step_name] = result
        return result

    # ========== 复杂流水线功能（简化版） ==========
    def _execute_loop_step(self, step: Dict[str, Any], interactive_mode: bool = False,
                         provided_params: Dict = None, context: Dict = None) -> Any:
        """执行循环步骤"""
        # 简化实现 - 先保证基本功能
        step_name = step.get("step", "loop_step")
        config = step.get("config", {})
        times = config.get("times", 1)
        loop_steps = config.get("steps", [])
        
        if self.verbose:
            print(f"   🔄 开始循环: {times} 次")
        
        final_result = None
        for i in range(times):
            if self.verbose:
                print(f"   🔄 循环迭代 {i+1}/{times}")
            result = self._execute_steps(loop_steps, interactive_mode, provided_params, context)
            if result is not None:
                final_result = result
        
        return final_result

    def _execute_branch_step(self, step: Dict[str, Any], interactive_mode: bool = False,
                           provided_params: Dict = None, context: Dict = None) -> Any:
        """执行分支步骤"""
        # 简化实现
        step_name = step.get("step", "branch_step")
        if self.verbose:
            print(f"   🚦 分支步骤: {step_name}")
        return None

    def _execute_router_step(self, step: Dict[str, Any], interactive_mode: bool = False,
                           provided_params: Dict = None, context: Dict = None) -> Any:
        """执行路由器步骤"""
        # 简化实现
        step_name = step.get("step", "router_step")
        if self.verbose:
            print(f"   🎯 路由器步骤: {step_name}")
        return None

    # ========== 其他现有方法保持不变 ==========
    def _start_tool_server(self, tool_config: Dict[str, Any]):
        """启动工具服务器"""
        tool_name = tool_config["name"]
        server_type = tool_config["server_type"]
        self.tool_mapping[tool_name] = server_type
        
        if self.verbose:
            server_config = {
                "server_type": server_type,
                "parameters": tool_config.get("parameters", {})
            }
            self.server_manager.start_server(server_type, server_config)
            print(f"   ✅ 启动工具服务器: {tool_name}")

    def _validate_input(self, value: str, config: Dict) -> tuple[bool, Any, str]:
        """验证用户输入"""
        # 保持原有实现
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

    def _display_detailed_data(self, result: Dict[str, Any]):
        """显示详细数据"""
        # 保持原有实现
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