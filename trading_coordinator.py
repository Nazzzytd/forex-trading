# trading_coordinator.py
from fx_tool import ForexDataTool
from technical_analyzer import TechnicalAnalyzer
from economic_calendar import EconomicCalendar
import pandas as pd
from typing import Dict

class TradingCoordinator:
    """交易协调器 - 整合数据获取、技术分析和AI分析"""
    
    def __init__(self, api_key: str = None):
        self.data_tool = ForexDataTool(api_key=api_key)
        self.analyzer = TechnicalAnalyzer()
        self.calendar = EconomicCalendar()
        print("✅ TradingCoordinator 初始化成功")
    
    def analyze_currency_pair(self, from_currency: str, to_currency: str, 
                        use_ai: bool = True) -> Dict:
        """完整分析货币对"""
        symbol = f"{from_currency}/{to_currency}"
        
        try:
            # 获取数据
            print(f"📊 获取 {symbol} 数据...")
            raw_data = self.data_tool.get_historical_data(from_currency, to_currency)
            
            if raw_data.empty:
                return {"error": "无法获取数据", "symbol": symbol}
            
            # 技术分析
            print("🔧 技术分析...")
            data_with_indicators = self.analyzer.calculate_indicators(raw_data)
            analysis_results = self.analyzer.generate_signals(data_with_indicators, use_ai=use_ai)
            
            # 修复：确保数据结构一致
            # 如果 analysis_results 没有嵌套的 technical_analysis，就创建一致的结构
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
                'technical_analysis': analysis_results,  # 这里已经是正确结构了
                'economic_calendar': economic_data,
                'latest_data': {
                    'price': data_with_indicators['close'].iloc[-1],
                    'date': data_with_indicators['date'].iloc[-1] if 'date' in data_with_indicators else pd.Timestamp.now()
                },
                'summary': self._generate_summary(analysis_results, economic_data)
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
                return {'basic_events': events_data}
            
            return calendar_data
            
        except Exception as e:
            return {"error": f"经济日历获取失败: {str(e)}"}
    
    def _generate_summary(self, analysis_results: Dict, economic_data: Dict) -> str:
        """生成分析摘要"""
        summary_parts = []
        
        # 技术分析摘要
        composite = analysis_results.get('composite_signal', {})
        tech_rec = composite.get('recommendation', '未知')
        confidence = composite.get('confidence', 0)
        summary_parts.append(f"技术: {tech_rec} ({confidence}%)")
        
        # AI分析摘要
        ai_analysis = analysis_results.get('ai_analysis', {})
        if 'analysis' in ai_analysis:
            ai_text = ai_analysis['analysis'][:30] + "..." if len(ai_analysis['analysis']) > 30 else ai_analysis['analysis']
            summary_parts.append(f"AI: {ai_text}")
        
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
        pairs = [('EUR', 'USD'), ('GBP', 'USD'), ('USD', 'JPY')]  # 减少到3个
        
        results = {}
        for from_curr, to_curr in pairs:
            try:
                result = self.analyze_currency_pair(from_curr, to_curr, use_ai=False)
                results[f"{from_curr}/{to_curr}"] = result
            except Exception as e:
                results[f"{from_curr}/{to_curr}"] = {"error": str(e)}
        
        return {
            'currency_analysis': results,
            'economic_calendar': self.calendar.get_comprehensive_economic_calendar(days_ahead=3),
            'timestamp': pd.Timestamp.now().isoformat()
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
            
            # 修复：确保返回正确的数据结构
            return {
                'symbol': symbol,
                'technical_analysis': tech_analysis,  # 这里应该是整个tech_analysis，不是tech_analysis['technical_analysis']
                'fundamental_analysis': fundamental_analysis,
                'risk_assessment': self._assess_combined_risk(tech_analysis, fundamental_analysis),
                'trading_recommendation': self._generate_combined_recommendation(tech_analysis, fundamental_analysis)
            }
            
        except Exception as e:
            return {"error": f"综合分析失败: {str(e)}", "symbol": symbol}

    def _assess_combined_risk(self, technical_analysis: Dict, fundamental_analysis: Dict) -> Dict:
        """评估综合风险"""
        # 技术风险
        composite = technical_analysis['technical_analysis'].get('composite_signal', {})
        confidence = composite.get('confidence', 50)
        tech_risk = 'high' if confidence < 40 else 'low' if confidence > 70 else 'medium'
        
        # 基本面风险
        fundamental_risk = 'medium'
        if 'error' not in fundamental_analysis:
            risk_info = fundamental_analysis.get('integrated_analysis', {})
            fundamental_risk = risk_info.get('risk_assessment', {}).get('risk_level', 'medium')
        
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
        tech_rec = technical_analysis['technical_analysis'].get('composite_signal', {}).get('recommendation', '中性')
        
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
            recommendations.extend(["减小仓位", "设置宽止损"])
        elif volatility == 'moderate_volatility':
            recommendations.extend(["关注经济数据", "注意风险管理"])
        
        return {
            'technical_bias': tech_rec,
            'fundamental_impact': volatility,
            'recommendations': recommendations
        }