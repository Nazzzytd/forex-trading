# trading_coordinator.py
from fx_tool import ForexDataTool
from technical_analyzer import TechnicalAnalyzer
from economic_calendar_alpha_vantage import EconomicCalendar  # 修正拼写
import pandas as pd
from typing import Dict
import time

class TradingCoordinator:
    """交易协调器 - 整合数据获取、技术分析和AI分析"""
    
    def __init__(self, api_key: str = None):
        self.data_tool = ForexDataTool(api_key=api_key)
        self.analyzer = TechnicalAnalyzer()
        self.calendar = EconomicCalendar()
        
        # API调用管理
        self.api_call_count = 0
        self.max_daily_calls = 20  # 保守限制
        
        print("✅ TradingCoordinator 初始化成功")
    
    def analyze_currency_pair(self, from_currency: str, to_currency: str, 
                        use_ai: bool = True) -> Dict:
        """完整分析货币对"""
        symbol = f"{from_currency}/{to_currency}"
        
        # 检查API限制
        if self.api_call_count >= self.max_daily_calls:
            return {"error": f"达到API调用限制 ({self.max_daily_calls}次)", "symbol": symbol}
        
        try:
            # 获取数据
            print(f"📊 获取 {symbol} 数据...")
            raw_data = self.data_tool.get_historical_data(from_currency, to_currency)
            self.api_call_count += 1
            
            if raw_data.empty:
                return {"error": "无法获取数据", "symbol": symbol}
            
            # 技术分析
            print("🔧 技术分析...")
            data_with_indicators = self.analyzer.calculate_indicators(raw_data)
            analysis_results = self.analyzer.generate_signals(data_with_indicators, use_ai=use_ai)
            
            # 确保数据结构一致
            if 'technical_analysis' not in analysis_results:
                analysis_results = {
                    'technical_analysis': analysis_results,
                    'timestamp': pd.Timestamp.now().isoformat(),
                    'price': data_with_indicators['close'].iloc[-1]
                }
            
            # 经济日历
            print("📅 获取经济日历...")
            economic_data = self.get_economic_calendar_for_pair(from_currency, to_currency)
            
            return {
                'symbol': symbol,
                'technical_analysis': analysis_results,
                'economic_calendar': economic_data,
                'latest_data': {
                    'price': data_with_indicators['close'].iloc[-1],
                    'date': data_with_indicators['date'].iloc[-1] if 'date' in data_with_indicators.columns else pd.Timestamp.now()
                },
                'summary': self._generate_summary(analysis_results, economic_data),
                'api_calls_remaining': self.max_daily_calls - self.api_call_count
            }
            
        except Exception as e:
            return {"error": f"分析失败: {str(e)}", "symbol": symbol}

    def get_economic_calendar_for_pair(self, from_currency: str, to_currency: str) -> Dict:
        """获取货币对相关的经济日历信息"""
        currency_pair = f"{from_currency}/{to_currency}"
        
        try:
            calendar_data = self.calendar.get_comprehensive_economic_calendar(
                currency_pair=currency_pair, 
                days_ahead=3
            )
            
            if 'error' in calendar_data:
                # 回退到基本事件数据
                events_data = self.calendar.get_economic_events_schedule(days_ahead=3)
                return {
                    'basic_events': events_data,
                    'source': 'fallback'
                }
            
            return calendar_data
            
        except Exception as e:
            return {"error": f"经济日历获取失败: {str(e)}"}

    def _generate_summary(self, analysis_results: Dict, economic_data: Dict) -> str:
        """生成分析摘要"""
        summary_parts = []
        
        # 技术分析摘要
        technical_data = analysis_results.get('technical_analysis', {})
        composite = technical_data.get('composite_signal', {})
        tech_rec = composite.get('recommendation', '未知')
        confidence = composite.get('confidence', 0)
        summary_parts.append(f"技术: {tech_rec} ({confidence}%)")
        
        # AI分析摘要
        ai_analysis = technical_data.get('ai_analysis', {})
        if 'analysis' in ai_analysis:
            ai_text = ai_analysis['analysis'][:30] + "..." if len(ai_analysis['analysis']) > 30 else ai_analysis['analysis']
            summary_parts.append(f"AI: {ai_text}")
        elif 'warning' in ai_analysis:
            summary_parts.append("AI: 不可用")
        elif 'error' in ai_analysis:
            summary_parts.append("AI: 错误")
        
        # 经济日历摘要
        if 'error' not in economic_data:
            if 'economic_events' in economic_data:
                events = economic_data['economic_events'].get('high_impact_events', 0)
                news = economic_data['news_summary'].get('high_impact_news', 0)
                if events > 0 or news > 0:
                    summary_parts.append(f"事件: {events}数据+{news}新闻")
            elif 'basic_events' in economic_data:
                events = economic_data['basic_events'].get('high_impact_events', 0)
                if events > 0:
                    summary_parts.append(f"事件: {events}个")
        
        return " | ".join(summary_parts)

    def get_market_overview(self) -> Dict:
        """获取市场概览 - 减少API调用"""
        # 只分析主要货币对，减少API调用
        pairs = [('EUR', 'USD'), ('GBP', 'USD'), ('USD', 'JPY')]
        
        results = {}
        for from_curr, to_curr in pairs:
            try:
                # 添加延迟避免频繁调用
                if self.api_call_count > 0:
                    time.sleep(1)
                    
                result = self.analyze_currency_pair(from_curr, to_curr, use_ai=False)
                results[f"{from_curr}/{to_curr}"] = result
            except Exception as e:
                results[f"{from_curr}/{to_curr}"] = {"error": str(e)}
        
        return {
            'currency_analysis': results,
            'economic_calendar': self.calendar.get_comprehensive_economic_calendar(days_ahead=3),
            'timestamp': pd.Timestamp.now().isoformat(),
            'api_usage': {
                'calls_used': self.api_call_count,
                'calls_remaining': self.max_daily_calls - self.api_call_count
            }
        }

    def analyze_with_fundamentals(self, from_currency: str, to_currency: str) -> Dict:
        """结合技术面和基本面的深度分析"""
        symbol = f"{from_currency}/{to_currency}"
        
        try:
            # 获取技术分析
            tech_analysis = self.analyze_currency_pair(from_currency, to_currency, use_ai=True)
            if 'error' in tech_analysis:
                return tech_analysis
            
            # 获取基本面分析
            fundamental_analysis = self.calendar.get_comprehensive_economic_calendar(
                currency_pair=symbol, days_ahead=5
            )
            
            return {
                'symbol': symbol,
                'technical_analysis': tech_analysis,  # 整个技术分析结果
                'fundamental_analysis': fundamental_analysis,
                'risk_assessment': self._assess_combined_risk(tech_analysis, fundamental_analysis),
                'trading_recommendation': self._generate_combined_recommendation(tech_analysis, fundamental_analysis),
                'api_info': {
                    'calls_used': self.api_call_count,
                    'calls_remaining': self.max_daily_calls - self.api_call_count
                }
            }
            
        except Exception as e:
            return {"error": f"综合分析失败: {str(e)}", "symbol": symbol}

    def _assess_combined_risk(self, technical_analysis: Dict, fundamental_analysis: Dict) -> Dict:
        """评估综合风险"""
        # 技术风险
        technical_data = technical_analysis.get('technical_analysis', {})
        composite = technical_data.get('composite_signal', {})
        confidence = composite.get('confidence', 50)
        tech_risk = 'high' if confidence < 40 else 'low' if confidence > 70 else 'medium'
        
        # 基本面风险
        fundamental_risk = 'medium'
        if 'error' not in fundamental_analysis:
            if 'integrated_analysis' in fundamental_analysis:
                risk_info = fundamental_analysis['integrated_analysis'].get('risk_assessment', {})
                fundamental_risk = risk_info.get('risk_level', 'medium')
            else:
                # 从基础事件数据推断风险
                events = fundamental_analysis.get('economic_events', {}).get('high_impact_events', 0)
                fundamental_risk = 'high' if events > 2 else 'medium' if events > 0 else 'low'
        
        # 综合风险
        risk_map = {
            ('high', 'high'): 'very_high', ('high', 'medium'): 'high', ('medium', 'high'): 'high',
            ('medium', 'medium'): 'medium', ('low', 'low'): 'low', ('low', 'medium'): 'medium',
            ('medium', 'low'): 'medium', ('high', 'low'): 'high', ('low', 'high'): 'high'
        }
        
        combined_risk = risk_map.get((tech_risk, fundamental_risk), 'medium')
        
        return {
            'technical_risk': tech_risk,
            'fundamental_risk': fundamental_risk,
            'combined_risk': combined_risk,
            'position_size': 'small' if combined_risk in ['high', 'very_high'] else 'normal'
        }
    
    def _generate_combined_recommendation(self, technical_analysis: Dict, fundamental_analysis: Dict) -> Dict:
        """生成综合交易建议"""
        technical_data = technical_analysis.get('technical_analysis', {})
        composite = technical_data.get('composite_signal', {})
        tech_rec = composite.get('recommendation', '中性')
        
        # 技术面建议
        if any(keyword in tech_rec for keyword in ['买入', '看涨', 'bullish']):
            action = "考虑逢低买入"
        elif any(keyword in tech_rec for keyword in ['卖出', '看跌', 'bearish']):
            action = "考虑逢高卖出"
        else:
            action = "保持观望"
        
        # 基本面影响
        volatility = 'neutral'
        if 'error' not in fundamental_analysis:
            events = fundamental_analysis.get('economic_events', {}).get('high_impact_events', 0)
            volatility = 'high_volatility' if events > 2 else 'moderate_volatility' if events > 0 else 'neutral'
        
        recommendations = [action]
        
        # 基本面建议
        if volatility == 'high_volatility':
            recommendations.extend(["减小仓位", "设置宽止损", "避免重大事件前后交易"])
        elif volatility == 'moderate_volatility':
            recommendations.extend(["关注经济数据发布时间", "注意风险管理"])
        
        return {
            'technical_bias': tech_rec,
            'fundamental_impact': volatility,
            'recommendations': recommendations,
            'confidence': composite.get('confidence', 0)
        }
    
    def reset_api_counter(self):
        """重置API计数器（用于测试）"""
        self.api_call_count = 0
        print("🔄 API计数器已重置")

# 测试函数
def test_trading_coordinator():
    """测试交易协调器"""
    coordinator = TradingCoordinator()
    
    print("🚀 测试交易协调器...")
    
    # 测试单个货币对分析
    print("\n1. 测试单个货币对分析...")
    result = coordinator.analyze_currency_pair('EUR', 'USD', use_ai=True)
    
    if 'error' in result:
        print(f"❌ 分析失败: {result['error']}")
    else:
        print(f"✅ 分析成功: {result['symbol']}")
        print(f"📝 摘要: {result['summary']}")
    
    # 测试市场概览
    print("\n2. 测试市场概览...")
    overview = coordinator.get_market_overview()
    print(f"✅ 市场概览生成成功")
    print(f"📊 分析货币对数量: {len(overview['currency_analysis'])}")
    
    # 测试综合分析
    print("\n3. 测试综合分析...")
    fundamental_result = coordinator.analyze_with_fundamentals('GBP', 'USD')
    
    if 'error' in fundamental_result:
        print(f"❌ 综合分析失败: {fundamental_result['error']}")
    else:
        print(f"✅ 综合分析成功")
        risk = fundamental_result['risk_assessment']
        print(f"⚠️  风险等级: {risk['combined_risk']} (技术: {risk['technical_risk']}, 基本面: {risk['fundamental_risk']})")
    
    print(f"\n📊 最终API使用: {coordinator.api_call_count}/{coordinator.max_daily_calls}")

if __name__ == "__main__":
    test_trading_coordinator()