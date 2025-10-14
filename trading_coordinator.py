# trading_coordinator.py
from fx_tool import ForexDataTool
from technical_analyzer import TechnicalAnalyzer
from openai import OpenAI
import pandas as pd
from typing import Dict, List
from config import config

class TradingCoordinator:
    """
    交易协调器 - 整合数据获取、技术分析和AI分析
    """
    
    def __init__(self, api_key: str = None):
        # 金融数据工具
        self.data_tool = ForexDataTool(api_key=api_key)
        
        # 技术分析工具
        self.analyzer = TechnicalAnalyzer()
        
        # AI分析工具
        self.ai_enabled = False
        self.openai_client = None
        
        if config.openai_api_key and config.openai_base_url:
            try:
                self.openai_client = OpenAI(
                    api_key=config.openai_api_key,
                    base_url=config.openai_base_url
                )
                self.ai_enabled = True
                print("✅ OpenAI客户端初始化成功")
            except Exception as e:
                print(f"❌ OpenAI客户端初始化失败: {e}")
        else:
            print("⚠️ OpenAI配置不完整，AI分析功能不可用")
        
        print("✅ TradingCoordinator 初始化成功")
    
    def analyze_currency_pair(self, from_currency: str, to_currency: str, 
                            interval: str = 'daily', use_ai: bool = True) -> Dict:
        """
        完整分析货币对
        
        Args:
            use_ai: 是否使用AI分析
        """
        symbol = f"{from_currency}/{to_currency}"
        
        try:
            # 1. 获取数据
            print(f"📊 获取 {symbol} 数据...")
            raw_data = self.data_tool.get_historical_data(from_currency, to_currency, interval)
            
            if raw_data.empty:
                return {"error": "无法获取数据", "symbol": symbol}
            
            # 2. 计算技术指标
            print("🔧 计算技术指标...")
            data_with_indicators = self.analyzer.calculate_indicators(raw_data)
            
            # 3. 生成交易信号
            print("📈 生成交易信号...")
            technical_signals = self.analyzer.generate_signals(data_with_indicators)
            
            # 4. AI分析（可选）
            ai_analysis = {}
            if use_ai and self.ai_enabled:
                print("🤖 进行AI深度分析...")
                ai_analysis = self._generate_ai_analysis(technical_signals, symbol, data_with_indicators)
            elif use_ai and not self.ai_enabled:
                ai_analysis = {"warning": "AI分析功能不可用"}
            
            # 5. 编译完整报告
            report = {
                'symbol': symbol,
                'technical_analysis': technical_signals,
                'ai_analysis': ai_analysis,
                'latest_data': {
                    'price': data_with_indicators['close'].iloc[-1],
                    'date': data_with_indicators['date'].iloc[-1]
                },
                'summary': self._generate_summary(technical_signals, ai_analysis)
            }
            
            return report
            
        except Exception as e:
            error_msg = f"分析过程中出错: {str(e)}"
            print(error_msg)
            return {"error": error_msg, "symbol": symbol}
    
    def _generate_ai_analysis(self, signals: Dict, symbol: str, data: pd.DataFrame) -> Dict:
        """使用OpenAI进行深度技术分析"""
        try:
            # 构建详细的技术分析上下文
            technical_context = self._create_detailed_technical_context(signals, symbol, data)
            
            prompt = f"""
            你是一个资深的外汇交易分析师。请基于以下详细的技术分析数据，提供专业的交易分析：

            {technical_context}

            请从以下角度提供分析：
            1. 当前市场状态评估（趋势、动量、波动性）
            2. 各技术指标的协同性分析
            3. 关键支撑位和阻力位识别
            4. 交易机会评估和风险提示
            5. 具体的交易策略建议（入场点、止损点、目标位）

            请用专业、客观的语言，避免情绪化表达。
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是专业的外汇交易分析师，擅长技术分析和风险管理。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return {
                "analysis": response.choices[0].message.content,
                "timestamp": pd.Timestamp.now()
            }
            
        except Exception as e:
            return {"error": f"AI分析失败: {str(e)}"}
    
    def _create_detailed_technical_context(self, signals: Dict, symbol: str, data: pd.DataFrame) -> str:
        """创建详细的技术分析上下文"""
        context = []
        
        # 基础信息
        context.append(f"交易品种: {symbol}")
        context.append(f"当前价格: {signals.get('price', 0):.4f}")
        context.append(f"分析时间: {signals.get('timestamp', '未知')}")
        context.append("")
        
        # 详细技术指标
        context.append("=== 技术指标详情 ===")
        
        # RSI分析
        rsi = signals.get('rsi', {})
        context.append(f"RSI: {rsi.get('value', 'N/A')} - 信号: {rsi.get('signal', '未知')} - 强度: {rsi.get('strength', 0)}%")
        
        # MACD分析
        macd = signals.get('macd', {})
        context.append(f"MACD: {macd.get('signal', '未知')} - 交叉: {macd.get('crossover_type', '无')}")
        
        # 布林带分析
        bb = signals.get('bollinger_bands', {})
        context.append(f"布林带: {bb.get('signal', '未知')} - 位置: {bb.get('position', 0):.3f}")
        if bb.get('squeeze'):
            context.append("  * 布林带收缩，预期波动加大")
        
        # 趋势分析
        trend = signals.get('trend', {})
        context.append(f"趋势方向: {trend.get('direction', '未知')} - 强度: {trend.get('strength', 0)}%")
        
        # 移动平均线
        ma = signals.get('moving_averages', {})
        context.append(f"均线排列: {ma.get('alignment', '未知')}")
        
        # 综合信号
        composite = signals.get('composite_signal', {})
        context.append(f"综合建议: {composite.get('recommendation', '未知')} - 置信度: {composite.get('confidence', 0)}%")
        
        return "\n".join(context)
    
    def _generate_summary(self, technical_signals: Dict, ai_analysis: Dict) -> str:
        """生成分析摘要"""
        composite = technical_signals['composite_signal']
        tech_recommendation = composite['recommendation']
        confidence = composite['confidence']
        
        summary_parts = [f"技术分析: {tech_recommendation} (置信度: {confidence}%)"]
        
        # AI分析摘要
        if 'analysis' in ai_analysis:
            summary_parts.append("🤖 AI分析可用")
        elif 'warning' in ai_analysis:
            summary_parts.append("🤖 AI分析暂不可用")
        
        return " | ".join(summary_parts)