# trading_coordinator.py
from fx_tool import ForexDataTool
from technical_analyzer import TechnicalAnalyzer
from economic_calendar import EconomicCalendar
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
        
        # 技术分析工具（已集成AI功能）
        self.analyzer = TechnicalAnalyzer()
        
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
            
            # 2. 计算技术指标并生成信号（包含AI分析）
            print("🔧 计算技术指标和生成信号...")
            data_with_indicators = self.analyzer.calculate_indicators(raw_data)
            analysis_results = self.analyzer.generate_signals(data_with_indicators, use_ai=use_ai)
            
            # 3. 添加symbol信息
            analysis_results['symbol'] = symbol
            
            # 4. 编译完整报告
            report = {
                'symbol': symbol,
                'technical_analysis': analysis_results,
                'latest_data': {
                    'price': data_with_indicators['close'].iloc[-1],
                    'date': data_with_indicators['date'].iloc[-1]
                },
                'summary': self._generate_summary(analysis_results)
            }
            
            return report
            
        except Exception as e:
            error_msg = f"分析过程中出错: {str(e)}"
            print(error_msg)
            return {"error": error_msg, "symbol": symbol}
    
    def _generate_summary(self, analysis_results: Dict) -> str:
        """生成分析摘要"""
        # 修复：直接从analysis_results获取composite_signal，而不是嵌套在technical_analysis中
        composite = analysis_results.get('composite_signal', {})
        tech_recommendation = composite.get('recommendation', '未知')
        confidence = composite.get('confidence', 0)
        
        summary_parts = [f"技术分析: {tech_recommendation} (置信度: {confidence}%)"]
        
        # AI分析摘要
        ai_analysis = analysis_results.get('ai_analysis', {})
        if 'analysis' in ai_analysis:
            # 截取AI分析的前50个字符作为摘要
            ai_text = ai_analysis['analysis'][:50] + "..." if len(ai_analysis['analysis']) > 50 else ai_analysis['analysis']
            summary_parts.append(f"🤖 AI: {ai_text}")
        elif 'warning' in ai_analysis:
            summary_parts.append("🤖 AI分析暂不可用")
        elif 'error' in ai_analysis:
            summary_parts.append("🤖 AI分析错误")
        
        return " | ".join(summary_parts)