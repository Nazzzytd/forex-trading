# servers/analyzer/analyzer.py
import json
import os
import logging
import numpy as np
from typing import Dict, Any, Optional
from openai import OpenAI
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Analyzer:
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 openai_base_url: Optional[str] = None,
                 default_model: str = "gpt-4"):
        """
        初始化综合分析器
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_base_url = openai_base_url or os.getenv("OPENAI_BASE_URL")
        self.default_model = default_model
        self.client = None
        
        # 初始化OpenAI客户端
        if self.openai_api_key:
            try:
                self.client = OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url
                )
                logger.info("✅ Analyzer AI客户端初始化成功")
            except Exception as e:
                logger.error(f"❌ Analyzer AI客户端初始化失败: {e}")
        else:
            logger.warning("⚠️ 未提供OpenAI API密钥，AI功能将不可用")
    
    def comprehensive_analysis(self, 
                             market_data: Dict[str, Any],
                             economic_data: Dict[str, Any], 
                             technical_data: Dict[str, Any],
                             query: str = "分析外汇走势") -> Dict[str, Any]:
        """
        综合所有数据源进行深度分析
        """
        if not self.client:
            return {
                "success": False,
                "error": "AI客户端未初始化，请检查API密钥配置",
                "analysis": None
            }
        
        try:
            # 智能数据提取 - 适配所有工具的实际格式
            analysis_data = self._extract_analysis_data(market_data, economic_data, technical_data)
            
            # 构建分析提示
            prompt = self._build_analysis_prompt(analysis_data, query)
            
            # 调用AI分析
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {
                        "role": "system", 
                        "content": """您是顶级外汇交易分析师，擅长综合技术分析、基本面分析和市场情绪分析。
                        
请严格按照以下JSON格式输出分析结果：
{
    "overall_assessment": {
        "market_sentiment": "看涨/看跌/中性",
        "confidence_level": "高/中/低",
        "key_drivers": ["驱动因素1", "驱动因素2"],
        "risk_level": "高/中/低"
    },
    "price_analysis": {
        "current_trend": "上升/下降/震荡",
        "key_support_levels": ["支撑位1", "支撑位2"],
        "key_resistance_levels": ["阻力位1", "阻力位2"],
        "volatility_assessment": "高/中/低"
    },
    "fundamental_analysis": {
        "economic_impact": "重大影响/中等影响/轻微影响",
        "key_events": ["重要事件1", "重要事件2"],
        "central_bank_bias": "鹰派/鸽派/中性"
    },
    "technical_analysis": {
        "indicators_summary": "技术指标汇总",
        "signal_strength": "强/中/弱",
        "trend_confirmation": "确认/未确认/矛盾"
    },
    "trading_recommendation": {
        "bias": "做多/做空/观望",
        "entry_zones": ["入场区域1", "入场区域2"],
        "stop_loss": "止损位",
        "take_profit": ["目标位1", "目标位2"],
        "position_sizing": "建议仓位"
    },
    "risk_management": {
        "key_risks": ["风险1", "风险2"],
        "hedging_suggestions": "对冲建议",
        "monitoring_points": ["监控点1", "监控点2"]
    }
}"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # 解析响应
            analysis_result = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "analysis": analysis_result,
                "metadata": {
                    "model_used": self.default_model,
                    "query": query,
                    "data_sources_used": ["market_data", "economic_data", "technical_data"],
                    "analysis_timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"综合分析失败: {e}")
            return {
                "success": False,
                "error": f"分析生成失败: {str(e)}",
                "analysis": None
            }
    
    def _extract_analysis_data(self, market_data, economic_data, technical_data):
        """智能提取分析所需数据 - 适配所有工具的实际格式"""
        extracted = {
            "market": self._extract_market_data(market_data),
            "economic": self._extract_economic_data(economic_data),
            "technical": self._extract_technical_data(technical_data)
        }
        
        # 记录数据可用性状态
        extracted["data_availability"] = {
            "market_data_available": bool(extracted["market"].get("price")),
            "economic_data_available": bool(extracted["economic"].get("sentiment") or extracted["economic"].get("events")),
            "technical_data_available": bool(extracted["technical"].get("signals") or extracted["technical"].get("indicators")),
            "all_data_available": all([
                extracted["market"].get("price"),
                extracted["economic"].get("sentiment") or extracted["economic"].get("events"),
                extracted["technical"].get("signals") or extracted["technical"].get("indicators")
            ])
        }
        
        return extracted
    
    def _extract_market_data(self, market_data):
        """提取市场数据 - 适配data_fetcher的实际格式"""
        key_data = {}
        
        if not market_data or not market_data.get("success"):
            return key_data
        
        try:
            data_content = market_data.get("data", {})
            
            # 处理实时数据（单个字典）
            if isinstance(data_content, dict) and data_content:
                key_data["price"] = {
                    "exchange_rate": data_content.get("exchange_rate"),
                    "open": data_content.get("open"),
                    "high": data_content.get("high"),
                    "low": data_content.get("low"), 
                    "close": data_content.get("exchange_rate"),  # 实时数据中close就是exchange_rate
                    "volume": data_content.get("volume"),
                    "change": data_content.get("change"),
                    "percent_change": data_content.get("percent_change")
                }
                key_data["currency_info"] = {
                    "from_currency": data_content.get("from_currency"),
                    "to_currency": data_content.get("to_currency"),
                    "pair": market_data.get("currency_pair")
                }
            
            # 处理历史/日内数据（列表格式）
            elif isinstance(data_content, list) and len(data_content) > 0:
                latest = data_content[-1]  # 取最新数据点
                key_data["price"] = {
                    "open": latest.get("open"),
                    "high": latest.get("high"),
                    "low": latest.get("low"),
                    "close": latest.get("close"),
                    "volume": latest.get("volume"),
                    "datetime": latest.get("datetime")
                }
                key_data["summary"] = market_data.get("summary", {})
            
            # 添加元数据
            key_data["metadata"] = {
                "data_type": market_data.get("data_type"),
                "success": market_data.get("success"),
                "source": "data_fetcher"
            }
            
        except Exception as e:
            logger.error(f"提取市场数据失败: {e}")
            key_data["error"] = f"数据提取错误: {str(e)}"
        
        return key_data
    
    def _extract_economic_data(self, economic_data):
        """提取经济数据 - 适配economic_calendar的实际复杂格式"""
        extracted = {}
        
        if not economic_data or not economic_data.get("success"):
            return extracted
        
        try:
            # 处理多货币对分析结果
            if economic_data.get("analysis_type") == "multi_currency":
                extracted["analysis_type"] = "multi_currency"
                extracted["currency_pairs"] = economic_data.get("currency_pairs_analyzed", [])
                extracted["summary"] = economic_data.get("summary", {})
                # 取第一个货币对的详细分析作为代表
                individual_analyses = economic_data.get("individual_analyses", {})
                if individual_analyses:
                    first_pair = list(individual_analyses.keys())[0]
                    representative_data = individual_analyses[first_pair]
                    if representative_data.get("success"):
                        extracted.update(self._extract_single_currency_economic_data(representative_data))
            else:
                # 单货币对分析
                extracted.update(self._extract_single_currency_economic_data(economic_data))
            
        except Exception as e:
            logger.error(f"提取经济数据失败: {e}")
            extracted["error"] = str(e)
        
        return extracted
    
    def _extract_single_currency_economic_data(self, economic_data):
        """提取单货币对经济数据"""
        extracted = {}
        
        try:
            # 提取市场情绪
            market_context = economic_data.get("market_context", {})
            extracted["sentiment"] = {
                "overall": market_context.get("overall_sentiment"),
                "score": market_context.get("sentiment_score"),
                "key_themes": market_context.get("key_market_themes", []),
                "volatility": market_context.get("volatility_outlook")
            }
            
            # 提取经济事件
            calendar_analysis = economic_data.get("economic_calendar_analysis", {})
            extracted["events"] = calendar_analysis.get("events", [])
            extracted["event_summary"] = {
                "total_events": calendar_analysis.get("total_events", 0),
                "high_impact_events": calendar_analysis.get("high_impact_events", 0),
                "period_covered": calendar_analysis.get("period_covered", "")
            }
            
            # 提取交易建议
            trading_rec = economic_data.get("trading_recommendation", {})
            extracted["recommendation"] = {
                "bias": trading_rec.get("overall_bias"),
                "confidence": trading_rec.get("confidence_level"),
                "risk_factors": trading_rec.get("key_risk_factors", []),
                "actions": trading_rec.get("recommended_actions", [])
            }
            
            # 提取关键价格水平
            critical_levels = trading_rec.get("critical_levels", {})
            extracted["key_levels"] = {
                "support": critical_levels.get("support", []),
                "resistance": critical_levels.get("resistance", [])
            }
            
            # 教育性见解
            educational = economic_data.get("educational_insights", {})
            if educational:
                extracted["insights"] = {
                    "fundamental_concept": educational.get("fundamental_concept"),
                    "common_mistakes": educational.get("common_mistakes", [])
                }
            
            # 元数据
            extracted["metadata"] = {
                "success": economic_data.get("success", False),
                "currency_pair": economic_data.get("currency_pair"),
                "analysis_timestamp": economic_data.get("analysis_timestamp"),
                "data_type": "economic_calendar"
            }
            
        except Exception as e:
            logger.error(f"提取单货币经济数据失败: {e}")
            extracted["error"] = str(e)
        
        return extracted
    
    def _extract_technical_data(self, technical_data):
        """提取技术分析数据 - 适配technical_analyzer的实际格式"""
        extracted = {}
        
        if not technical_data or not technical_data.get("success"):
            return extracted
        
        try:
            # 判断数据来源：calculate_indicators 还是 generate_signals
            data_type = self._detect_technical_data_type(technical_data)
            
            if data_type == "indicators":
                # calculate_indicators 返回的数据
                extracted["data_type"] = "technical_indicators"
                extracted["symbol"] = technical_data.get("symbol")
                extracted["record_count"] = technical_data.get("record_count", 0)
                
                # 提取价格摘要
                price_summary = technical_data.get("price_summary", {})
                extracted["price"] = {
                    "current": price_summary.get("current_price"),
                    "change": price_summary.get("price_change"),
                    "change_pct": price_summary.get("price_change_pct")
                }
                
                # 提取技术指标数据
                data_list = technical_data.get("data", [])
                if data_list:
                    latest_data = data_list[-1]  # 取最新数据点
                    extracted["indicators"] = self._extract_indicators_from_data(latest_data)
                
                extracted["available_indicators"] = technical_data.get("indicators_calculated", [])
                
            elif data_type == "signals":
                # generate_signals 返回的数据
                extracted["data_type"] = "trading_signals"
                extracted["symbol"] = technical_data.get("symbol")
                extracted["timestamp"] = technical_data.get("timestamp")
                extracted["price"] = technical_data.get("price")
                
                # 提取各个技术信号
                extracted["signals"] = {
                    "rsi": technical_data.get("rsi", {}),
                    "macd": technical_data.get("macd", {}),
                    "bollinger_bands": technical_data.get("bollinger_bands", {}),
                    "stochastic": technical_data.get("stochastic", {}),
                    "moving_averages": technical_data.get("moving_averages", {}),
                    "trend": technical_data.get("trend", {}),
                    "volatility": technical_data.get("volatility", {})
                }
                
                # 提取综合信号
                composite_signal = technical_data.get("composite_signal", {})
                extracted["composite_signal"] = {
                    "recommendation": composite_signal.get("recommendation"),
                    "confidence": composite_signal.get("confidence"),
                    "bullish_count": composite_signal.get("bullish_signals"),
                    "bearish_count": composite_signal.get("bearish_signals")
                }
                
                # 提取AI分析
                if "ai_analysis" in technical_data:
                    extracted["ai_analysis"] = technical_data["ai_analysis"]
            
            # 添加元数据
            extracted["metadata"] = {
                "success": technical_data.get("success", False),
                "data_type": data_type,
                "source": "technical_analyzer"
            }
            
        except Exception as e:
            logger.error(f"提取技术数据失败: {e}")
            extracted["error"] = str(e)
        
        return extracted
    
    def _detect_technical_data_type(self, data):
        """检测技术数据的类型"""
        if "composite_signal" in data:
            return "signals"  # generate_signals 返回的数据
        elif "data" in data and "indicators_calculated" in data:
            return "indicators"  # calculate_indicators 返回的数据
        else:
            return "unknown"
    
    def _extract_indicators_from_data(self, data_point):
        """从数据点中提取技术指标"""
        indicators = {}
        
        # 定义要提取的技术指标字段
        indicator_fields = [
            'RSI', 'MACD', 'MACD_Signal', 'MACD_Histogram',
            'Stoch_K', 'Stoch_D', 'BB_Upper', 'BB_Middle', 
            'BB_Lower', 'BB_Width', 'BB_Position', 'ATR'
        ]
        
        # 添加EMA指标
        for i in [5, 10, 20, 50, 200]:
            indicator_fields.append(f'EMA_{i}')
        
        for field in indicator_fields:
            if field in data_point:
                value = data_point[field]
                # 处理NaN值
                if value is None or (isinstance(value, float) and np.isnan(value)):
                    indicators[field] = None
                else:
                    indicators[field] = value
        
        return indicators
    
    def _build_analysis_prompt(self, analysis_data, query):
        """构建分析提示 - 适配所有工具的实际数据格式"""
        
        # 数据可用性检查
        availability = analysis_data['data_availability']
        
        prompt = f"""
用户查询: {query}

📊 数据可用性报告:
- 市场数据: {'✅ 可用' if availability['market_data_available'] else '❌ 不可用'}
- 经济数据: {'✅ 可用' if availability['economic_data_available'] else '❌ 不可用'}  
- 技术数据: {'✅ 可用' if availability['technical_data_available'] else '❌ 不可用'}

"""

        # 根据可用数据动态构建提示
        if availability['market_data_available']:
            prompt += f"""
=== 市场数据 ===
{self._format_market_data_for_prompt(analysis_data['market'])}
"""

        if availability['economic_data_available']:
            prompt += f"""
=== 经济日历分析 ===
{self._format_economic_data_for_prompt(analysis_data['economic'])}
"""

        if availability['technical_data_available']:
            prompt += f"""
=== 技术分析 ===
{self._format_technical_data_for_prompt(analysis_data['technical'])}
"""

        prompt += """
请基于以上可用数据，提供专业的综合分析报告。
如果某些数据不可用，请在分析中说明这一限制，并基于现有数据给出最佳分析。
"""

        return prompt
    
    def _format_market_data_for_prompt(self, market_data):
        """格式化市场数据用于提示"""
        if not market_data or not market_data.get("price"):
            return "无有效的市场数据"
        
        lines = []
        price = market_data["price"]
        
        lines.append(f"当前价格: {price.get('exchange_rate') or price.get('close')}")
        if price.get('change'):
            lines.append(f"价格变化: {price['change']} ({price.get('percent_change', 0)}%)")
        if price.get('volume'):
            lines.append(f"交易量: {price['volume']}")
        
        currency_info = market_data.get("currency_info", {})
        if currency_info.get('pair'):
            lines.append(f"货币对: {currency_info['pair']}")
        
        return "\n".join(lines)
    
    def _format_economic_data_for_prompt(self, economic_data):
        """格式化经济数据用于提示"""
        if not economic_data:
            return "无经济数据"
        
        lines = []
        
        # 处理多货币对分析
        if economic_data.get("analysis_type") == "multi_currency":
            lines.append("分析类型: 多货币对综合")
            summary = economic_data.get("summary", {})
            lines.append(f"看涨货币对: {', '.join(summary.get('bullish_pairs', []))}")
            lines.append(f"看跌货币对: {', '.join(summary.get('bearish_pairs', []))}")
            lines.append(f"市场展望: {summary.get('market_outlook', '未知')}")
            return "\n".join(lines)
        
        # 单货币对分析
        sentiment = economic_data.get("sentiment", {})
        if sentiment.get("overall"):
            lines.append(f"市场情绪: {sentiment['overall']} (得分: {sentiment.get('score', 0)})")
        
        event_summary = economic_data.get("event_summary", {})
        if event_summary.get("high_impact_events", 0) > 0:
            lines.append(f"高影响事件: {event_summary['high_impact_events']}个")
        
        recommendation = economic_data.get("recommendation", {})
        if recommendation.get("bias"):
            lines.append(f"交易建议: {recommendation['bias']} (置信度: {recommendation.get('confidence', '未知')})")
        
        # 关键事件
        events = economic_data.get("events", [])[:3]  # 只显示前3个事件
        if events:
            lines.append("重要经济事件:")
            for event in events:
                lines.append(f"  - {event.get('event_name')}: {event.get('actual_value', 'N/A')}")
        
        return "\n".join(lines)
    
    def _format_technical_data_for_prompt(self, technical_data):
        """格式化技术数据用于提示"""
        if not technical_data:
            return "无技术数据"
        
        lines = []
        
        # 基本信息
        data_type = technical_data.get("data_type", "unknown")
        symbol = technical_data.get("symbol", "未知")
        lines.append(f"技术数据类型: {data_type}")
        lines.append(f"交易品种: {symbol}")
        
        if data_type == "trading_signals":
            # 交易信号格式
            signals = technical_data.get("signals", {})
            composite = technical_data.get("composite_signal", {})
            
            lines.append(f"综合建议: {composite.get('recommendation', '未知')}")
            lines.append(f"置信度: {composite.get('confidence', 0)}%")
            
            # 详细信号
            if signals.get("rsi"):
                rsi = signals["rsi"]
                lines.append(f"RSI: {rsi.get('value', 'N/A')} - {rsi.get('signal', '未知')}")
            
            if signals.get("macd"):
                macd = signals["macd"]
                lines.append(f"MACD: {macd.get('signal', '未知')} - {macd.get('crossover_type', '无交叉')}")
                
        elif data_type == "technical_indicators":
            # 技术指标格式
            indicators = technical_data.get("indicators", {})
            lines.append(f"可用指标数: {len(technical_data.get('available_indicators', []))}")
            
            # 显示关键指标
            key_indicators = ['RSI', 'MACD', 'BB_Position', 'Stoch_K']
            for indicator in key_indicators:
                if indicator in indicators and indicators[indicator] is not None:
                    lines.append(f"{indicator}: {indicators[indicator]}")
        
        # AI分析结果
        if "ai_analysis" in technical_data:
            ai_result = technical_data["ai_analysis"]
            if "analysis" in ai_result:
                lines.append("")
                lines.append("🤖 AI技术分析摘要:")
                ai_text = ai_result["analysis"]
                if len(ai_text) > 200:
                    lines.append(ai_text[:200] + "...")
                else:
                    lines.append(ai_text)
        
        return "\n".join(lines)
    
    def quick_analysis(self, data: Dict[str, Any], analysis_type: str = "general") -> Dict[str, Any]:
        """快速分析单个数据源"""
        if not self.client:
            return {"success": False, "error": "AI客户端未初始化"}
        
        try:
            prompt = f"请对以下{analysis_type}数据进行分析: {json.dumps(data, ensure_ascii=False)}"
            
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "您是数据分析专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            return {
                "success": True,
                "analysis": response.choices[0].message.content,
                "type": analysis_type
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = "healthy" if self.client else "degraded"
        ai_status = "available" if self.client else "unavailable"
        
        return {
            "status": status,
            "service": "analyzer",
            "ai_capabilities": ai_status,
            "default_model": self.default_model,
            "timestamp": self._get_timestamp()
        }
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().isoformat()