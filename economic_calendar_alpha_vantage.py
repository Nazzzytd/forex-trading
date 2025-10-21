# economic_calendar.py
import requests
import json
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from ultrarag.core.config_loader import ConfigLoader
except ImportError:
    from ...core.config_loader import ConfigLoader

class EconomicCalendar:
    """
    智能经济日历分析工具 - 提供详细的经济事件解释、市场影响分析和交易建议
    """

    def __init__(self, config: Dict = None):
        if config is None:
            try:
                loader = ConfigLoader()
                config_path = os.path.join(os.path.dirname(__file__), "economic_calendar_parameter.yaml")
                config = loader.load_config(config_path)
            except Exception as e:
                print(f"配置加载失败: {e}")
                config = {}
        
        # API密钥配置
        self.alpha_vantage_key = config.get("alpha_api_key") or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.openai_api_key = config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        self.openai_base_url = config.get("openai_base_url") or os.getenv("OPENAI_BASE_URL")
        
        # 配置参数
        self.daily_limit = config.get("daily_api_limit", 25)
        self.enable_detailed_explanations = config.get("enable_detailed_explanations", True)
        self.include_market_expectations = config.get("include_market_expectations", True)
        
        # 测试模式
        self.test_mode = not self.alpha_vantage_key or self.alpha_vantage_key.startswith("${")
        
        # API限制管理
        self.api_call_count = 0
        
        # 配置OpenAI
        if self.openai_api_key and not self.openai_api_key.startswith("${"):
            try:
                self.openai_client = openai.OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url
                )
            except Exception:
                self.openai_client = None
        
        self.alpha_vantage_base_url = "https://www.alphavantage.co/query"
        
        # 货币对映射
        self.currency_to_tickers = {
            'EUR/USD': ['EURUSD', 'EUR', 'USD'],
            'GBP/USD': ['GBPUSD', 'GBP', 'USD'],
            'USD/JPY': ['USDJPY', 'USD', 'JPY'],
            'USD/CHF': ['USDCHF', 'USD', 'CHF'],
            'AUD/USD': ['AUDUSD', 'AUD', 'USD'],
            'USD/CAD': ['USDCAD', 'USD', 'CAD'],
            'NZD/USD': ['NZDUSD', 'NZD', 'USD']
        }

        # 详细经济事件解释词典
        self.detailed_event_explanations = {
            'US Nonfarm Payrolls': {
                'what_is_it': '美国非农就业数据，衡量美国非农业部门就业人数月度变化',
                'why_it_matters': '反映美国劳动力市场健康状况，是美联储货币政策决策的关键指标',
                'typical_impact': {
                    'direction': '数据好于预期利好美元，差于预期利空美元',
                    'magnitude': '高波动性，通常引发50-100点波动',
                    'duration': '影响持续数小时至数天'
                },
                'affected_currencies': ['USD', 'EUR/USD', 'GBP/USD', 'USD/JPY'],
                'market_expectations': {
                    'consensus_forecast': '基于经济学家调查的中位数预期',
                    'previous_value': '参考上月修正值',
                    'deviation_impact': '偏离预期0.1%可能引发显著波动'
                },
                'trading_implications': {
                    'pre_event_strategy': '减少仓位，设置宽止损',
                    'post_event_reaction': '等待数据公布后5-10分钟再入场',
                    'risk_management': '使用事件驱动交易策略，严格控制仓位'
                }
            },
            'US CPI Data': {
                'what_is_it': '美国消费者物价指数，衡量一篮子消费品和服务的价格变化',
                'why_it_matters': '核心通胀指标，直接影响美联储利率决策',
                'typical_impact': {
                    'direction': '通胀高于预期利好美元，低于预期利空美元',
                    'magnitude': '极高波动性，核心CPI尤其重要',
                    'duration': '影响持续至下次美联储会议'
                },
                'affected_currencies': ['USD', '所有主要货币对'],
                'market_expectations': {
                    'consensus_forecast': '关注核心CPI年率预期',
                    'previous_value': '对比上月数据趋势',
                    'deviation_impact': '核心CPI偏离0.1%可能改变市场预期'
                },
                'trading_implications': {
                    'pre_event_strategy': '避免在数据公布前建立新仓位',
                    'post_event_reaction': '关注市场对美联储政策的重新定价',
                    'risk_management': '使用突破策略，关注关键技术水平'
                }
            },
            'Federal Reserve Meeting': {
                'what_is_it': '美联储联邦公开市场委员会议息会议',
                'why_it_matters': '决定美国货币政策走向，影响全球资金流向',
                'typical_impact': {
                    'direction': '鹰派信号利好美元，鸽派信号利空美元',
                    'magnitude': '极高波动性，声明措辞变化关键',
                    'duration': '影响持续数周至数月'
                },
                'affected_currencies': ['USD', '所有货币对', '黄金'],
                'market_expectations': {
                    'consensus_forecast': '关注利率点阵图和通胀预期',
                    'previous_value': '对比上次会议声明变化',
                    'deviation_impact': '声明措辞的任何变化都重要'
                },
                'trading_implications': {
                    'pre_event_strategy': '减少风险暴露，关注技术位',
                    'post_event_reaction': '仔细分析声明和新闻发布会',
                    'risk_management': '分阶段建仓，使用追踪止损'
                }
            },
            'ECB Interest Rate Decision': {
                'what_is_it': '欧洲央行货币政策会议和利率决议',
                'why_it_matters': '决定欧元区货币政策，影响欧元汇率',
                'typical_impact': {
                    'direction': '加息或鹰派利好欧元，降息或鸽派利空欧元',
                    'magnitude': '高波动性，新闻发布会尤其重要',
                    'duration': '影响持续至下次会议'
                },
                'affected_currencies': ['EUR', 'EUR/USD', 'EUR/GBP', 'EUR/JPY'],
                'market_expectations': {
                    'consensus_forecast': '关注利率决定和资产购买计划',
                    'previous_value': '对比通胀和经济展望',
                    'deviation_impact': '拉加德讲话基调变化影响重大'
                },
                'trading_implications': {
                    'pre_event_strategy': '关注欧元区通胀和经济增长数据',
                    'post_event_reaction': '分析货币政策声明和记者会',
                    'risk_management': '设置事件驱动止损单'
                }
            },
            'Bank of England Rate Decision': {
                'what_is_it': '英国央行货币政策委员会利率决议',
                'why_it_matters': '决定英国基准利率，影响英镑汇率',
                'typical_impact': {
                    'direction': '加息利好英镑，降息利空英镑',
                    'magnitude': '高波动性，投票分裂程度重要',
                    'duration': '影响持续数天至数周'
                },
                'affected_currencies': ['GBP', 'GBP/USD', 'EUR/GBP'],
                'market_expectations': {
                    'consensus_forecast': '关注利率投票比例',
                    'previous_value': '对比通胀报告预测',
                    'deviation_impact': '意外投票结果影响显著'
                },
                'trading_implications': {
                    'pre_event_strategy': '分析英国通胀和就业数据',
                    'post_event_reaction': '关注会议纪要和行长讲话',
                    'risk_management': '使用新闻交易策略'
                }
            }
        }

    def get_trading_analysis(self, currency_pair: str = None, days_ahead: int = 3, include_fundamental_analysis: bool = True) -> Dict:
        """
        获取详细的交易分析和经济事件解释
        
        Args:
            currency_pair: 货币对，如 "EUR/USD"。如果为None，则分析所有主要货币对
            days_ahead: 分析未来几天的事件
            include_fundamental_analysis: 是否包含基本面分析
        """
        try:
            # 处理默认货币对
            if currency_pair is None:
                return self._get_multi_currency_analysis(days_ahead, include_fundamental_analysis)
            
            # 验证货币对格式
            if not self._is_valid_currency_pair(currency_pair):
                return {
                    "success": False,
                    "error": f"不支持的货币对: {currency_pair}",
                    "supported_pairs": list(self.currency_to_tickers.keys())
                }
            
            # 获取市场数据
            news_data = self._get_enhanced_news(currency_pair)
            events_data = self._get_enhanced_events(days_ahead)
            
            # 增强AI分析
            analysis = self._get_detailed_trading_advice(news_data, events_data, currency_pair)
            
            # 构建详细输出
            return self._build_detailed_output(news_data, events_data, analysis, currency_pair, include_fundamental_analysis)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"分析失败: {str(e)}",
                "currency_pair": currency_pair,
                "analysis_timestamp": datetime.now().isoformat()
            }

    def _get_multi_currency_analysis(self, days_ahead: int, include_fundamental: bool) -> Dict:
        """获取多货币对分析"""
        major_pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD"]
        
        analyses = {}
        for pair in major_pairs:
            try:
                analysis = self.get_trading_analysis(pair, days_ahead, include_fundamental)
                analyses[pair] = analysis
            except Exception as e:
                analyses[pair] = {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "analysis_type": "multi_currency",
            "currency_pairs_analyzed": list(analyses.keys()),
            "individual_analyses": analyses,
            "summary": self._generate_multi_currency_summary(analyses),
            "analysis_timestamp": datetime.now().isoformat()
        }

    def _is_valid_currency_pair(self, currency_pair: str) -> bool:
        """验证货币对是否支持"""
        return currency_pair in self.currency_to_tickers

    def _generate_multi_currency_summary(self, analyses: Dict) -> Dict:
        """生成多货币对分析摘要"""
        # 实现摘要生成逻辑
        bullish_pairs = []
        bearish_pairs = []
        
        for pair, analysis in analyses.items():
            if analysis.get("success"):
                bias = analysis.get("trading_recommendation", {}).get("overall_bias", "")
                if "做多" in bias:
                    bullish_pairs.append(pair)
                elif "做空" in bias:
                    bearish_pairs.append(pair)
        
        return {
            "bullish_pairs": bullish_pairs,
            "bearish_pairs": bearish_pairs,
            "total_analyzed": len(analyses),
            "market_outlook": "分化" if bullish_pairs and bearish_pairs else "一致"
        }

    def _build_detailed_output(self, news_data: Dict, events_data: Dict, analysis: Dict, currency_pair: str, include_fundamental: bool) -> Dict:
        """构建详细输出结构"""
        base_cur, quote_cur = currency_pair.split('/')
        
        output = {
            "success": True,
            "currency_pair": currency_pair,
            "analysis_timestamp": datetime.now().isoformat(),
            "market_context": {
                "overall_sentiment": news_data.get("sentiment", "中性"),
                "sentiment_score": news_data.get("sentiment_score", 0),
                "key_market_themes": news_data.get("key_themes", []),
                "volatility_outlook": self._get_volatility_outlook(events_data)
            },
            "economic_calendar_analysis": {
                "period_covered": f"未来{len(events_data.get('events', []))}天",
                "total_events": len(events_data.get('events', [])),
                "high_impact_events": events_data.get("high_impact_count", 0),
                "medium_impact_events": self._count_medium_impact_events(events_data),
                "events": self._build_detailed_events_list(events_data.get("events", []))
            },
            "trading_recommendation": {
                "overall_bias": analysis.get("action", "观望"),
                "confidence_level": analysis.get("confidence", "中等"),
                "recommended_actions": self._build_recommended_actions(analysis, currency_pair),
                "key_risk_factors": analysis.get("risk_factors", []),
                "preferred_entry_zones": analysis.get("entry_suggestions", []),
                "critical_levels": self._get_critical_levels(currency_pair)
            },
            "data_sources": {
                "news_source": news_data.get("source", "simulated"),
                "events_source": events_data.get("source", "simulated"),
                "api_usage": {
                    "calls_made": self.api_call_count,
                    "calls_remaining": self.daily_limit - self.api_call_count
                }
            }
        }
        
        # 添加教育性内容
        if include_fundamental:
            output["educational_insights"] = self._get_educational_insights(events_data, currency_pair)
        
        return output

    def _build_detailed_events_list(self, events: List[Dict]) -> List[Dict]:
        """构建详细事件列表"""
        detailed_events = []
        
        for event in events:
            event_name = event.get('name', '')
            detailed_explanation = self.detailed_event_explanations.get(event_name, {})
            
            # 如果没有预定义的详细解释，生成基本解释
            if not detailed_explanation:
                detailed_explanation = self._generate_basic_explanation(event)
            
            detailed_event = {
                "event_name": event_name,
                "event_date": event.get('date', ''),
                "event_time": event.get('time', ''),
                "country": self._get_country_from_event(event_name),
                "importance_level": event.get('impact', '中'),
                "detailed_explanation": detailed_explanation
            }
            detailed_events.append(detailed_event)
        
        return detailed_events

    def _generate_basic_explanation(self, event: Dict) -> Dict:
        """为未知事件生成基本解释"""
        event_name = event.get('name', '')
        currency_impact = event.get('currency_impact', [])
        
        return {
            "what_is_it": f"{event_name} - 重要的经济数据发布",
            "why_it_matters": "该数据影响市场对相关经济体经济状况的判断",
            "typical_impact": {
                "direction": f"数据好于预期利好{currency_impact[0] if currency_impact else '相关货币'}",
                "magnitude": "中等波动性",
                "duration": "影响持续数小时"
            },
            "affected_currencies": currency_impact,
            "market_expectations": {
                "consensus_forecast": "关注市场普遍预期",
                "previous_value": "对比历史数据趋势",
                "deviation_impact": "显著偏离预期可能引发波动"
            },
            "trading_implications": {
                "pre_event_strategy": "减少仓位，等待数据公布",
                "post_event_reaction": "根据实际数据与预期的偏差交易",
                "risk_management": "设置合理止损"
            }
        }

    def _build_recommended_actions(self, analysis: Dict, currency_pair: str) -> List[Dict]:
        """构建推荐操作列表"""
        actions = []
        
        # 短期操作
        actions.append({
            "timeframe": "短期(1-3天)",
            "action": analysis.get("action", "观望"),
            "rationale": "基于当前市场情绪和经济事件分析",
            "risk_level": analysis.get("risk", "medium"),
            "position_sizing": analysis.get("position_size", "标准")
        })
        
        # 事件驱动操作
        if analysis.get("risk_factors"):
            actions.append({
                "timeframe": "事件驱动",
                "action": "谨慎交易",
                "rationale": "高影响事件可能引发剧烈波动",
                "risk_level": "high",
                "position_sizing": "轻仓"
            })
        
        return actions

    def _get_volatility_outlook(self, events_data: Dict) -> str:
        """获取波动率展望"""
        high_impact = events_data.get("high_impact_count", 0)
        
        if high_impact >= 2:
            return "高波动性预期"
        elif high_impact == 1:
            return "中等波动性预期"
        else:
            return "低波动性预期"

    def _count_medium_impact_events(self, events_data: Dict) -> int:
        """计算中等影响事件数量"""
        events = events_data.get("events", [])
        return len([e for e in events if e.get("impact") == "中"])

    def _get_country_from_event(self, event_name: str) -> str:
        """从事件名称获取国家"""
        country_map = {
            'US': '美国',
            'ECB': '欧元区', 
            'Fed': '美国',
            'Bank of England': '英国',
            'BOJ': '日本',
            'CPI': '美国',
            'Nonfarm': '美国'
        }
        
        for key, country in country_map.items():
            if key in event_name:
                return country
        return "全球"

    def _get_critical_levels(self, currency_pair: str) -> Dict:
        """获取关键技术水平（模拟）"""
        # 在实际应用中，这里应该集成技术分析工具
        levels = {
            "EUR/USD": {"support": ["1.0750", "1.0700"], "resistance": ["1.0850", "1.0900"]},
            "GBP/USD": {"support": ["1.2550", "1.2500"], "resistance": ["1.2650", "1.2700"]},
            "USD/JPY": {"support": ["148.00", "147.50"], "resistance": ["149.00", "149.50"]},
            "USD/CHF": {"support": ["0.8800", "0.8750"], "resistance": ["0.8900", "0.8950"]},
            "AUD/USD": {"support": ["0.6550", "0.6500"], "resistance": ["0.6650", "0.6700"]},
            "USD/CAD": {"support": ["1.3450", "1.3400"], "resistance": ["1.3550", "1.3600"]},
            "NZD/USD": {"support": ["0.6050", "0.6000"], "resistance": ["0.6150", "0.6200"]}
        }
        
        return levels.get(currency_pair, {"support": [], "resistance": []})

    def _get_educational_insights(self, events_data: Dict, currency_pair: str) -> Dict:
        """获取教育性见解"""
        high_impact_events = events_data.get("high_impact_count", 0)
        
        return {
            "fundamental_concept": "经济数据对汇率的影响机制",
            "how_to_interpret": "关注数据与预期的偏差，而非绝对值",
            "common_mistakes": [
                "在重大数据公布前重仓交易",
                "忽视数据修正值的重要性",
                "过度交易低影响力事件"
            ],
            "advanced_considerations": [
                "分析数据趋势而非单次发布",
                "关注央行政策预期的变化",
                "结合技术面确认基本面信号"
            ]
        }

    def get_economic_event_details(self, event_name: str, currency_pair: str = None) -> Dict:
        """获取特定经济事件的详细解释"""
        explanation = self.detailed_event_explanations.get(event_name)
        
        if not explanation:
            return {
                "success": False,
                "error": f"未找到事件 '{event_name}' 的详细解释",
                "available_events": list(self.detailed_event_explanations.keys())
            }
        
        return {
            "success": True,
            "event_name": event_name,
            "currency_pair": currency_pair,
            "detailed_explanation": explanation,
            "trading_advice": self._generate_event_specific_advice(event_name, currency_pair)
        }

    def _generate_event_specific_advice(self, event_name: str, currency_pair: str) -> Dict:
        """生成事件特定交易建议"""
        advice_templates = {
            'US Nonfarm Payrolls': {
                'strategy': '突破交易策略',
                'risk_management': '数据公布后等待5分钟再入场',
                'key_levels': '关注前期高点和低点'
            },
            'US CPI Data': {
                'strategy': '趋势跟随策略', 
                'risk_management': '核心CPI数据更重要',
                'key_levels': '关注通胀预期变化'
            },
            'Federal Reserve Meeting': {
                'strategy': '声明驱动交易',
                'risk_management': '关注点阵图变化',
                'key_levels': '技术面与基本面结合'
            }
        }
        
        return advice_templates.get(event_name, {
            'strategy': '谨慎交易',
            'risk_management': '设置合理止损',
            'key_levels': '关注重要技术水平'
        })

    # 保留原有的辅助方法，但调整以适配新格式
    def _get_enhanced_news(self, currency_pair: str) -> Dict:
        """获取增强的新闻数据分析（原有实现）"""
        # 保持原有实现不变
        if self.test_mode or self._is_api_limit_reached():
            return self._get_enhanced_simulated_sentiment(currency_pair)
        
        try:
            tickers = ",".join(self.currency_to_tickers.get(currency_pair, ['EUR', 'USD']))
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.alpha_vantage_key,
                'topics': 'economy_monetary,financial_markets',
                'tickers': tickers,
                'sort': 'LATEST',
                'limit': 15
            }
            
            self.api_call_count += 1
            
            response = requests.get(self.alpha_vantage_base_url, params=params, timeout=10)
            data = response.json()
            
            if 'feed' in data and data['feed']:
                return self._process_enhanced_news(data['feed'], currency_pair)
            else:
                return self._get_enhanced_simulated_sentiment(currency_pair)
                
        except Exception:
            return self._get_enhanced_simulated_sentiment(currency_pair)

    def _get_enhanced_events(self, days_ahead: int) -> Dict:
        """获取增强的经济事件数据（原有实现）"""
        # 保持原有实现不变
        if self.test_mode or self._is_api_limit_reached() or not self.alpha_vantage_key:
            return self._get_simulated_future_events(days_ahead)

        # ... 原有实现代码

    def _get_detailed_trading_advice(self, news_data: Dict, events_data: Dict, currency_pair: str) -> Dict:
        """获取详细的AI交易建议（原有实现）"""
        # 保持原有实现不变
        if not self.openai_client:
            return self._get_enhanced_basic_advice(news_data, events_data, currency_pair)
        
        # ... 原有实现代码

    def _get_simulated_future_events(self, days_ahead: int) -> Dict:
        """模拟未来事件数据（需要补充实现）"""
        # 这里需要实现模拟事件数据的生成
        # 暂时返回空事件列表
        return {
            "events": [],
            "next_event": None,
            "high_impact_count": 0,
            "source": "simulated"
        }

    def _is_api_limit_reached(self) -> bool:
        """检查API限制"""
        return self.api_call_count >= self.daily_limit

    def health_check(self) -> Dict:
        """健康检查"""
        return {
            "success": True,
            "status": "operational",
            "api_remaining": self.daily_limit - self.api_call_count,
            "test_mode": self.test_mode,
            "ai_enabled": self.openai_client is not None,
            "features_enabled": {
                "detailed_explanations": self.enable_detailed_explanations,
                "market_expectations": self.include_market_expectations
            }
        }

    # 保留其他原有的辅助方法...
    # _process_enhanced_news, _detect_news_themes, _build_detailed_trading_prompt, 
    # _parse_detailed_ai_response, _generate_data_based_reasoning, 等等...