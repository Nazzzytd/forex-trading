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
        
        # 测试模式
        self.test_mode = not self.alpha_vantage_key or self.alpha_vantage_key.startswith("${")
        
        # API限制管理
        self.api_call_count = 0
        self.daily_limit = 25
        self.enable_detailed_explanations = config.get("enable_detailed_explanations", True)
        self.include_market_expectations = config.get("include_market_expectations", True)
        
        # 测试模式
        self.test_mode = not self.alpha_vantage_key or self.alpha_vantage_key.startswith("${")
        
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
        
        # 货币对映射和经济事件解释
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

    # ==================== 主要公共接口 ====================
    
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

    # ==================== 数据获取层 ====================
    
    def _process_enhanced_news(self, news_feed: List, currency_pair: str) -> Dict:
        """处理增强新闻数据"""
        if not news_feed:
            return self._get_enhanced_simulated_sentiment(currency_pair)
        
        # 分析新闻情绪和主题
        scores = []
        themes = {}
        important_articles = []
        
        for article in news_feed[:10]:
            # 情绪分析
            score = article.get('overall_sentiment_score', 0)
            if score:
                scores.append(score)
            
            # 主题分析
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            content = title + " " + summary
            
            # 检测关键主题
            detected_themes = self._detect_news_themes(content)
            for theme in detected_themes:
                themes[theme] = themes.get(theme, 0) + 1
            
            # 重要文章
            if any(keyword in content for keyword in ['rate', 'inflation', 'employment', 'gdp', 'fed', 'ecb']):
                important_articles.append({
                    'title': article.get('title', '')[:100],
                    'sentiment': article.get('overall_sentiment_label', 'neutral'),
                    'relevance': article.get('relevance_score', '0')
                })
        
        # 计算情绪
        avg_score = sum(scores) / len(scores) if scores else 0
        
        if avg_score > 0.2:
            sentiment = "强烈看涨"
            explanation = "市场情绪积极，多数新闻对经济前景持乐观态度"
        elif avg_score > 0.05:
            sentiment = "温和看涨" 
            explanation = "市场情绪略微积极，但存在不确定性"
        elif avg_score < -0.2:
            sentiment = "强烈看跌"
            explanation = "市场情绪消极，担忧经济前景"
        elif avg_score < -0.05:
            sentiment = "温和看跌"
            explanation = "市场情绪略微消极，存在谨慎情绪"
        else:
            sentiment = "中性"
            explanation = "市场情绪平衡，多空因素交织"
        
        # 主要主题
        key_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "sentiment": sentiment,
            "sentiment_score": round(avg_score, 3),
            "sentiment_explanation": explanation,
            "key_themes": [theme[0] for theme in key_themes],
            "important_articles": important_articles[:3],
            "total_articles": len(news_feed),
            "source": "alpha_vantage"
        }


    def _get_enhanced_events(self, days_ahead: int) -> Dict:
        """
        通过 Alpha Vantage API 获取重要的历史经济指标数据
        专注于已发布的实际数据，而不是未来事件预测
        """
        if self.test_mode or self._is_api_limit_reached() or not self.alpha_vantage_key:
            return self._get_historical_economic_data_fallback()
        
        economic_data_events = []
        
        # 定义要获取的重要经济指标
        indicator_configs = [
            {
                'function': 'CPI',
                'interval': 'monthly',
                'name_zh': '美国消费者物价指数 (CPI)',
                'impact': '高',
                'currency': 'USD',
                'description': '衡量美国通胀水平的核心指标'
            },
            {
                'function': 'FEDERAL_FUNDS_RATE', 
                'interval': 'monthly',
                'name_zh': '美国联邦基金利率',
                'impact': '极高',
                'currency': 'USD',
                'description': '美联储货币政策基准利率'
            },
            {
                'function': 'UNEMPLOYMENT',
                'interval': 'monthly',
                'name_zh': '美国失业率',
                'impact': '高', 
                'currency': 'USD',
                'description': '反映美国劳动力市场状况'
            },
            {
                'function': 'RETAIL_SALES',
                'interval': 'monthly',
                'name_zh': '美国零售销售',
                'impact': '中',
                'currency': 'USD',
                'description': '衡量消费者支出水平'
            },
            {
                'function': 'GDP',
                'interval': 'quarterly',
                'name_zh': '美国国内生产总值 (GDP)',
                'impact': '高',
                'currency': 'USD',
                'description': '衡量美国经济增长的综合指标'
            }
        ]

        successful_indicators = 0
        
        for config in indicator_configs:
            try:
                if self._is_api_limit_reached():
                    break
                    
                self.api_call_count += 1
                    
                params = {
                    'function': config['function'],
                    'apikey': self.alpha_vantage_key,
                }
                
                # 为需要interval参数的指标添加interval
                if config['function'] in ['CPI', 'UNEMPLOYMENT', 'RETAIL_SALES']:
                    params['interval'] = config['interval']
                
                response = requests.get(self.alpha_vantage_base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                # 检查API限制或错误
                if 'Error Message' in data or 'Note' in data:
                    print(f"Alpha Vantage API 返回错误 ({config['function']})")
                    continue
                    
                # 处理返回的数据
                if 'data' in data and data['data']:
                    latest_data = data['data'][0]
                    event = self._create_economic_event_from_data(latest_data, config)
                    economic_data_events.append(event)
                    successful_indicators += 1
                    
            except requests.exceptions.RequestException as e:
                print(f"Alpha Vantage API 调用失败 ({config['function']}): {e}")
                continue
            except (KeyError, IndexError, ValueError) as e:
                print(f"解析 Alpha Vantage 数据失败 ({config['function']}): {e}")
                continue
            except Exception as e:
                print(f"处理经济数据时发生错误 ({config['function']}): {e}")
                continue

        # 如果没有成功获取到数据，使用回退方案
        if not economic_data_events:
            return self._get_historical_economic_data_fallback()
        
        # 按日期排序，最新的在前
        economic_data_events.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return {
            "events": economic_data_events,
            "next_event": economic_data_events[0] if economic_data_events else None,
            "high_impact_count": len([e for e in economic_data_events if e.get("impact") in ["高", "极高"]]),
            "successful_indicators": successful_indicators,
            "total_indicators_attempted": len(indicator_configs),
            "source": "alpha_vantage_historical_data"
        }

    def _create_economic_event_from_data(self, data_point: Dict, config: Dict) -> Dict:
        """从API数据创建经济事件对象"""
        value = data_point.get('value', 'N/A')
        date = data_point.get('date', 'N/A')
        
        # 获取事件的详细解释
        event_name = config['name_zh']
        detailed_explanation = self.detailed_event_explanations.get(event_name, {})
        
        if not detailed_explanation:
            detailed_explanation = {
                "what_is_it": config['description'],
                "why_it_matters": f"该数据影响{config['currency']}汇率和货币政策预期",
                "typical_impact": {
                    "direction": f"数据好于预期利好{config['currency']}，差于预期利空{config['currency']}",
                    "magnitude": f"{config['impact']}波动性",
                    "duration": "影响持续数小时至数天"
                }
            }
        
        return {
            "name": f"{config['name_zh']}",
            "date": date,
            "time": "已发布",
            "impact": config['impact'],
            "currency_impact": [config['currency']],
            "actual_value": value,
            "status": "已发布",
            "detailed_explanation": detailed_explanation,
            "data_source": "Alpha Vantage",
            "importance": "历史实际数据"
        }

    def _get_historical_economic_data_fallback(self) -> Dict:
        """历史经济数据回退方案"""
        # 当无法从API获取数据时，返回基本的经济数据信息
        fallback_events = [
            {
                "name": "美国消费者物价指数 (CPI)",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": "已发布",
                "impact": "高",
                "currency_impact": ["USD"],
                "actual_value": "使用API获取最新数据",
                "status": "需通过API获取",
                "detailed_explanation": self.detailed_event_explanations.get('US CPI Data', {}),
                "data_source": "Alpha Vantage (需要有效API密钥)",
                "importance": "核心通胀指标"
            }
        ]
        
        return {
            "events": fallback_events,
            "next_event": fallback_events[0],
            "high_impact_count": 1,
            "successful_indicators": 0,
            "total_indicators_attempted": 0,
            "source": "fallback_historical_data"
        }

    

    # ==================== 分析处理层 ====================
    
    def _get_detailed_trading_advice(self, news_data: Dict, events_data: Dict, currency_pair: str) -> Dict:
        """获取详细的AI交易建议"""
        if not self.openai_client:
            return self._get_enhanced_basic_advice(news_data, events_data, currency_pair)
        
        try:
            prompt = self._build_detailed_trading_prompt(news_data, events_data, currency_pair)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """你是一个资深的外汇交易分析师。请基于提供的市场数据提供详细的交易分析和建议。

请按以下结构提供分析：
1. 交易建议（做多/做空/观望）及置信度
2. 详细的分析推理（基于新闻情绪和经济事件）
3. 关键影响因素分析
4. 风险因素说明
5. 具体的入场建议
6. 总体总结

请确保分析专业、详细且具有可操作性。"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1200,
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content.strip()
            return self._parse_detailed_ai_response(analysis_text, news_data, events_data)
            
        except Exception:
            return self._get_enhanced_basic_advice(news_data, events_data, currency_pair)

    def _build_detailed_trading_prompt(self, news_data: Dict, events_data: Dict, currency_pair: str) -> str:
        """构建详细交易提示词"""
        base_cur, quote_cur = currency_pair.split('/')
        
        prompt = f"请为 {currency_pair} 提供详细的交易分析：\n\n"
        
        # 市场情绪分析
        prompt += "=== 市场情绪分析 ===\n"
        prompt += f"整体情绪: {news_data.get('sentiment', '中性')}\n"
        prompt += f"情绪得分: {news_data.get('sentiment_score', 0)}\n"
        prompt += f"情绪解释: {news_data.get('sentiment_explanation', '')}\n"
        prompt += f"主要新闻主题: {', '.join(news_data.get('key_themes', []))}\n\n"
        
        # 经济事件分析
        prompt += "=== 经济日历事件 ===\n"
        events = events_data.get("events", [])
        for i, event in enumerate(events[:3], 1):
            prompt += f"{i}. {event['name']} ({event['date']} {event['time']})\n"
            prompt += f"   影响等级: {event['impact']}\n"
            prompt += f"   影响货币: {', '.join(event['currency_impact'])}\n"
            prompt += f"   事件解释: {event['explanation']}\n\n"
        
        prompt += f"高影响事件总数: {events_data.get('high_impact_count', 0)}\n\n"
        
        # 具体分析要求
        prompt += "=== 分析要求 ===\n"
        prompt += f"请详细分析以上信息对 {base_cur} 和 {quote_cur} 的影响：\n"
        prompt += "1. 基于新闻情绪判断市场方向偏好\n"
        prompt += "2. 分析即将发生经济事件的潜在影响\n"
        prompt += "3. 评估风险回报比\n"
        prompt += "4. 提供具体的交易建议和风险管理策略\n"
        
        return prompt

    def _parse_detailed_ai_response(self, text: str, news_data: Dict, events_data: Dict) -> Dict:
        """解析详细的AI响应"""
        lines = text.split('\n')
        
        # 初始化默认值
        analysis = {
            "action": "观望",
            "confidence": "中等", 
            "risk": "medium",
            "timeframe": "短期",
            "position_size": "标准",
            "reasoning": [],
            "key_factors": [],
            "risk_factors": [],
            "entry_suggestions": [],
            "summary": ""
        }
        
        current_section = None
        reasoning_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检测章节
            if '交易建议' in line or '建议' in line:
                current_section = 'action'
            elif '分析' in line or '推理' in line:
                current_section = 'reasoning' 
            elif '因素' in line or '影响' in line:
                current_section = 'factors'
            elif '风险' in line:
                current_section = 'risk'
            elif '入场' in line or '操作' in line:
                current_section = 'entry'
            elif '总结' in line:
                current_section = 'summary'
            
            # 提取交易建议
            if current_section == 'action':
                if any(word in line for word in ['做多', '买入', 'long', 'buy']):
                    analysis["action"] = "做多"
                elif any(word in line for word in ['做空', '卖出', 'short', 'sell']):
                    analysis["action"] = "做空"
                    
                if '高置信' in line or 'high confidence' in line.lower():
                    analysis["confidence"] = "高"
                elif '低置信' in line or 'low confidence' in line.lower():
                    analysis["confidence"] = "低"
            
            # 收集分析推理
            elif current_section == 'reasoning' and len(line) > 10:
                reasoning_lines.append(line)
            
            # 提取关键因素
            elif current_section == 'factors' and ('•' in line or '-' in line or '1.' in line):
                analysis["key_factors"].append(line.strip('•- 123456789.'))
            
            # 提取风险因素  
            elif current_section == 'risk' and len(line) > 5:
                analysis["risk_factors"].append(line)
            
            # 提取入场建议
            elif current_section == 'entry' and len(line) > 5:
                analysis["entry_suggestions"].append(line)
            
            # 提取总结
            elif current_section == 'summary' and len(line) > 20 and not analysis["summary"]:
                analysis["summary"] = line
        
        # 处理分析推理
        if reasoning_lines:
            analysis["reasoning"] = reasoning_lines[:5]  # 限制为5条主要推理
        
        # 如果没有提取到足够信息，使用基于数据的推理
        if not analysis["reasoning"]:
            analysis["reasoning"] = self._generate_data_based_reasoning(news_data, events_data)
        
        if not analysis["key_factors"]:
            analysis["key_factors"] = self._generate_key_factors(news_data, events_data)
            
        if not analysis["risk_factors"]:
            analysis["risk_factors"] = self._generate_risk_factors(events_data)
            
        if not analysis["summary"]:
            analysis["summary"] = self._generate_summary(analysis, news_data, events_data)
        
        return analysis


    # ==================== 输出构建层 ====================
    
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
                "data_type": "历史经济数据",  # 明确说明数据类型
                "period_covered": "最新发布的经济指标",
                "total_events": len(events_data.get('events', [])),
                "high_impact_events": events_data.get("high_impact_count", 0),
                "successful_data_points": events_data.get("successful_indicators", 0),
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

    # ==================== 多货币对分析 ====================
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


    # ==================== 事件解释系统 ====================
    
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


    # ==================== 辅助工具层 ====================
    
    def _process_enhanced_news(self, news_feed: List, currency_pair: str) -> Dict:
        """处理增强新闻数据"""
        if not news_feed:
            return self._get_enhanced_simulated_sentiment(currency_pair)
        
        # 分析新闻情绪和主题
        scores = []
        themes = {}
        important_articles = []
        
        for article in news_feed[:10]:
            # 情绪分析
            score = article.get('overall_sentiment_score', 0)
            if score:
                scores.append(score)
            
            # 主题分析
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            content = title + " " + summary
            
            # 检测关键主题
            detected_themes = self._detect_news_themes(content)
            for theme in detected_themes:
                themes[theme] = themes.get(theme, 0) + 1
            
            # 重要文章
            if any(keyword in content for keyword in ['rate', 'inflation', 'employment', 'gdp', 'fed', 'ecb']):
                important_articles.append({
                    'title': article.get('title', '')[:100],
                    'sentiment': article.get('overall_sentiment_label', 'neutral'),
                    'relevance': article.get('relevance_score', '0')
                })
        
        # 计算情绪
        avg_score = sum(scores) / len(scores) if scores else 0
        
        if avg_score > 0.2:
            sentiment = "强烈看涨"
            explanation = "市场情绪积极，多数新闻对经济前景持乐观态度"
        elif avg_score > 0.05:
            sentiment = "温和看涨" 
            explanation = "市场情绪略微积极，但存在不确定性"
        elif avg_score < -0.2:
            sentiment = "强烈看跌"
            explanation = "市场情绪消极，担忧经济前景"
        elif avg_score < -0.05:
            sentiment = "温和看跌"
            explanation = "市场情绪略微消极，存在谨慎情绪"
        else:
            sentiment = "中性"
            explanation = "市场情绪平衡，多空因素交织"
        
        # 主要主题
        key_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "sentiment": sentiment,
            "sentiment_score": round(avg_score, 3),
            "sentiment_explanation": explanation,
            "key_themes": [theme[0] for theme in key_themes],
            "important_articles": important_articles[:3],
            "total_articles": len(news_feed),
            "source": "alpha_vantage"
        }

    def _detect_news_themes(self, content: str) -> List[str]:
        """检测新闻主题"""
        themes = []
        content_lower = content.lower()
        
        theme_keywords = {
            '货币政策': ['interest rate', 'monetary policy', 'fed', 'ecb', 'central bank', 'rate decision'],
            '通胀': ['inflation', 'cpi', 'price', 'consumer price'],
            '就业': ['employment', 'jobs', 'unemployment', 'nonfarm', 'payroll'],
            '经济增长': ['gdp', 'growth', 'economy', 'economic', 'recession'],
            '地缘政治': ['geopolitical', 'war', 'conflict', 'sanctions', 'trade'],
            '市场情绪': ['sentiment', 'confidence', 'optimism', 'pessimism', 'risk appetite']
        }
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                themes.append(theme)
        
        return themes

    def _get_enhanced_news(self, currency_pair: str) -> Dict:
        """获取增强的新闻数据分析"""
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

    def _generate_data_based_reasoning(self, news_data: Dict, events_data: Dict) -> List[str]:
        """基于数据生成分析推理"""
        reasoning = []
        sentiment = news_data.get("sentiment", "中性")
        high_impact_events = events_data.get("high_impact_count", 0)
        
        reasoning.append(f"市场情绪分析: {sentiment}，表明市场整体偏向{sentiment.replace('看', '')}方")
        
        if high_impact_events > 0:
            reasoning.append(f"近期有{high_impact_events}个高影响经济事件，可能引发市场波动")
        
        key_themes = news_data.get("key_themes", [])
        if key_themes:
            reasoning.append(f"新闻主题集中在{', '.join(key_themes)}，这些因素将影响汇率走势")
        
        return reasoning

    def _generate_key_factors(self, news_data: Dict, events_data: Dict) -> List[str]:
        """生成关键影响因素"""
        factors = []
        
        # 基于情绪
        sentiment = news_data.get("sentiment", "中性")
        if "看涨" in sentiment:
            factors.append("积极的市场情绪支撑汇率上行")
        elif "看跌" in sentiment:
            factors.append("消极的市场情绪对汇率构成压力")
        
        # 基于事件
        events = events_data.get("events", [])
        for event in events[:2]:
            factors.append(f"{event['name']}可能影响{', '.join(event['currency_impact'])}走势")
        
        return factors

    def _generate_risk_factors(self, events_data: Dict) -> List[str]:
        """生成风险因素"""
        risks = []
        high_impact_events = events_data.get("high_impact_count", 0)
        
        if high_impact_events > 0:
            risks.append(f"{high_impact_events}个高影响经济事件可能引发市场剧烈波动")
            risks.append("事件结果的不确定性增加了交易风险")
        
        risks.append("全球经济和政治因素可能影响预期走势")
        risks.append("技术面与基本面可能出现背离")
        
        return risks

    def _generate_summary(self, analysis: Dict, news_data: Dict, events_data: Dict) -> str:
        """生成分析总结"""
        action = analysis["action"]
        confidence = analysis["confidence"]
        risk = analysis["risk"]
        
        sentiment = news_data.get("sentiment", "中性")
        high_impact_events = events_data.get("high_impact_count", 0)
        
        summary = f"基于{sentiment}的市场情绪"
        if high_impact_events > 0:
            summary += f"和{high_impact_events}个高影响事件"
        
        summary += f"，建议{action}操作，置信度{confidence}，风险等级{risk}。"
        summary += "请根据个人风险承受能力调整仓位。"
        
        return summary

    def _get_enhanced_basic_advice(self, news_data: Dict, events_data: Dict, currency_pair: str) -> Dict:
        """增强的基础建议"""
        sentiment = news_data.get("sentiment", "中性")
        high_impact_events = events_data.get("high_impact_count", 0)
        
        # 基于情绪和事件的决策逻辑
        if "看涨" in sentiment and high_impact_events == 0:
            action, confidence, risk = "做多", "中等", "low"
        elif "看涨" in sentiment and high_impact_events > 0:
            action, confidence, risk = "做多", "中等", "medium"
        elif "看跌" in sentiment and high_impact_events == 0:
            action, confidence, risk = "做空", "中等", "low"
        elif "看跌" in sentiment and high_impact_events > 0:
            action, confidence, risk = "做空", "中等", "medium"
        else:
            action, confidence, risk = "观望", "低", "low"
        
        return {
            "action": action,
            "confidence": confidence,
            "risk": risk,
            "timeframe": "短期",
            "position_size": "轻仓" if risk == "high" else "标准",
            "reasoning": self._generate_data_based_reasoning(news_data, events_data),
            "key_factors": self._generate_key_factors(news_data, events_data),
            "risk_factors": self._generate_risk_factors(events_data),
            "entry_suggestions": ["等待合适的技术位入场", "设置止损保护"],
            "summary": self._generate_summary({"action": action, "confidence": confidence, "risk": risk}, 
                                            news_data, events_data)
        }

    def _get_enhanced_simulated_sentiment(self, currency_pair: str) -> Dict:
        """增强的模拟情绪数据"""
        import random
        sentiments = ["强烈看涨", "温和看涨", "中性", "温和看跌", "强烈看跌"]
        weights = [0.2, 0.25, 0.3, 0.15, 0.1]  # 略微偏向看涨
        
        sentiment = random.choices(sentiments, weights=weights)[0]
        score = round(random.uniform(-0.5, 0.5), 3)
        
        # 根据情绪生成解释
        explanations = {
            "强烈看涨": "市场情绪积极，经济数据强劲推动乐观情绪",
            "温和看涨": "市场略微乐观，但存在一些不确定性", 
            "中性": "市场情绪平衡，多空因素交织",
            "温和看跌": "市场略显谨慎，担忧经济前景",
            "强烈看跌": "市场情绪消极，风险厌恶情绪上升"
        }
        
        themes_pool = ['货币政策', '通胀', '就业', '经济增长', '地缘政治']
        selected_themes = random.sample(themes_pool, min(3, len(themes_pool)))
        
        return {
            "sentiment": sentiment,
            "sentiment_score": score,
            "sentiment_explanation": explanations.get(sentiment, "市场情绪中性"),
            "key_themes": selected_themes,
            "important_articles": [],
            "total_articles": random.randint(8, 20),
            "source": "simulated"
        }


    def _get_volatility_outlook(self, events_data: Dict) -> str:
        """获取波动率展望"""
        high_impact = events_data.get("high_impact_count", 0)
        
        if high_impact >= 2:
            return "高波动性预期"
        elif high_impact == 1:
            return "中等波动性预期"
        else:
            return "低波动性预期"

    def _get_critical_levels(self, currency_pair: str) -> Dict:
        """获取关键技术水平"""
        pass

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

    def _is_api_limit_reached(self) -> bool:
        """检查API限制"""
        return self.api_call_count >= self.daily_limit