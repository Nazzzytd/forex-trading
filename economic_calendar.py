# economic_calendar.py
import requests
import json
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import config


class EconomicCalendar:
    """
    经济日历工具 - 获取外汇新闻和重要经济数据发布信息，并利用OpenAI进行分析
    """

    def __init__(self):
        self.newsapi_key = getattr(config, 'newsapi_key', None)
        self.openai_api_key = getattr(config, 'openai_api_key', None)
        self.openai_base_url = getattr(config, 'openai_base_url', None)
        self.alpha_vantage_key = getattr(config, 'alpha_api_key', None)
        
        # 配置OpenAI客户端
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
            if self.openai_base_url:
                openai.api_base = self.openai_base_url
        
        # 重要经济数据发布事件
        self.economic_events = {
            'us': [
                {
                    'name': 'Nonfarm Payrolls',
                    'frequency': 'monthly',
                    'importance': 'high',
                    'source': 'BLS',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'GBP/USD', 'USD/JPY']
                },
                {
                    'name': 'CPI Inflation',
                    'frequency': 'monthly', 
                    'importance': 'high',
                    'source': 'BLS',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'USD/JPY']
                },
                {
                    'name': 'Federal Funds Rate',
                    'frequency': '8_times_year',
                    'importance': 'high',
                    'source': 'Federal Reserve',
                    'typical_time': '14:00 EST',
                    'currency_impact': ['USD', 'All majors']
                },
                {
                    'name': 'GDP Growth Rate',
                    'frequency': 'quarterly',
                    'importance': 'high',
                    'source': 'BEA',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'USD/JPY']
                },
                {
                    'name': 'Retail Sales',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'Census Bureau',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD']
                },
                {
                    'name': 'ISM Manufacturing PMI',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'ISM',
                    'typical_time': '10:00 EST',
                    'currency_impact': ['USD']
                }
            ],
            'eu': [
                {
                    'name': 'ECB Interest Rate',
                    'frequency': '8_times_year',
                    'importance': 'high',
                    'source': 'ECB',
                    'typical_time': '12:45 GMT',
                    'currency_impact': ['EUR', 'EUR/USD', 'EUR/GBP']
                },
                {
                    'name': 'Eurozone CPI',
                    'frequency': 'monthly',
                    'importance': 'high',
                    'source': 'Eurostat',
                    'typical_time': '10:00 GMT',
                    'currency_impact': ['EUR', 'EUR/USD']
                },
                {
                    'name': 'German ZEW Economic Sentiment',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'ZEW',
                    'typical_time': '10:00 GMT',
                    'currency_impact': ['EUR', 'EUR/USD']
                }
            ],
            'uk': [
                {
                    'name': 'Bank of England Rate',
                    'frequency': '8_times_year',
                    'importance': 'high',
                    'source': 'BOE',
                    'typical_time': '12:00 GMT',
                    'currency_impact': ['GBP', 'GBP/USD', 'EUR/GBP']
                },
                {
                    'name': 'UK CPI Inflation',
                    'frequency': 'monthly',
                    'importance': 'high',
                    'source': 'ONS',
                    'typical_time': '07:00 GMT',
                    'currency_impact': ['GBP', 'GBP/USD']
                }
            ],
            'jp': [
                {
                    'name': 'Bank of Japan Rate',
                    'frequency': '8_times_year',
                    'importance': 'high',
                    'source': 'BOJ',
                    'typical_time': '时间 varies',
                    'currency_impact': ['JPY', 'USD/JPY', 'EUR/JPY']
                }
            ]
        }

        # 外汇交易相关事件关键词映射
        self.event_keywords = {
            'central_bank_decision': [
                'interest rate decision', 'federal reserve', 'fed meeting', 'ecb decision',
                'bank of england', 'boe meeting', 'bank of japan', 'boj meeting',
                'rba decision', 'boc meeting', 'monetary policy', 'central bank'
            ],
            'inflation_data': [
                'cpi', 'consumer price index', 'inflation data', 'core cpi',
                'pce price index', 'inflation report'
            ],
            'employment_data': [
                'nonfarm payrolls', 'nfp', 'unemployment rate', 'jobless claims',
                'employment change', 'adp employment', 'wage growth'
            ],
            'gdp_growth': [
                'gdp growth', 'gross domestic product', 'economic growth',
                'preliminary gdp', 'final gdp'
            ],
            'retail_sales': [
                'retail sales', 'core retail sales', 'consumer spending'
            ],
            'manufacturing_pmi': [
                'manufacturing pmi', 'services pmi', 'composite pmi',
                'ism manufacturing', 'ism services'
            ]
        }
        
        # 主要货币对国家映射
        self.currency_pairs = {
            'EUR/USD': ['euro', 'eurozone', 'ecb', 'european central bank', 'us dollar', 'fed'],
            'GBP/USD': ['british pound', 'sterling', 'bank of england', 'boe', 'uk economy'],
            'USD/JPY': ['japanese yen', 'bank of japan', 'boj', 'japan economy'],
            'USD/CHF': ['swiss franc', 'swiss national bank', 'snb'],
            'AUD/USD': ['australian dollar', 'reserve bank of australia', 'rba'],
            'USD/CAD': ['canadian dollar', 'bank of canada', 'boc', 'oil prices'],
            'NZD/USD': ['new zealand dollar', 'reserve bank of new zealand', 'rbnz']
        }

    def get_economic_events_schedule(self, days_ahead: int = 7, country: str = None) -> Dict:
        """
        获取经济数据发布日程
        """
        try:
            # 优先使用Alpha Vantage API获取真实数据
            if self.alpha_vantage_key:
                events = self._get_alpha_vantage_economic_events(days_ahead, country)
            else:
                # 如果没有Alpha Vantage密钥，使用模拟数据
                events = self._get_simulated_economic_events(days_ahead, country)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'timeframe': f'next_{days_ahead}_days',
                'country_filter': country,
                'total_events': len(events),
                'high_impact_events': len([e for e in events if e.get('importance') == 'high']),
                'events': events
            }
            
        except Exception as e:
            return {"error": f"获取经济事件日程失败: {str(e)}"}

    def _get_alpha_vantage_economic_events(self, days_ahead: int, country: str = None) -> List[Dict]:
        """使用Alpha Vantage API获取经济事件数据"""
        try:
            url = "https://www.alphavantage.co/query"
            
            # 设置时间范围
            today = datetime.now().date()
            end_date = today + timedelta(days=days_ahead)
            
            params = {
                'function': 'ECONOMIC_CALENDAR',
                'apikey': self.alpha_vantage_key,
                'time_from': today.strftime('%Y%m%dT0000'),
                'time_to': end_date.strftime('%Y%m%dT2359')
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查API响应
            if 'data' not in data:
                print(f"Alpha Vantage API返回异常数据: {data}")
                # 回退到模拟数据
                return self._get_simulated_economic_events(days_ahead, country)
            
            events = []
            for event in data['data']:
                # 过滤国家
                event_country = event.get('country', '').upper()
                if country and self._standardize_country_code(country) != event_country:
                    continue
                    
                # 标准化事件格式
                standardized_event = self._standardize_alpha_vantage_event(event)
                if standardized_event:
                    events.append(standardized_event)
            
            # 如果没有获取到事件，使用模拟数据
            if not events:
                return self._get_simulated_economic_events(days_ahead, country)
                
            return events
            
        except Exception as e:
            print(f"Alpha Vantage API调用失败: {str(e)}，使用模拟数据")
            return self._get_simulated_economic_events(days_ahead, country)

    def _standardize_country_code(self, country: str) -> str:
        """标准化国家代码"""
        country_mapping = {
            'us': 'US',
            'united states': 'US',
            'usa': 'US',
            'uk': 'UK',
            'united kingdom': 'UK',
            'gb': 'UK',
            'eu': 'EU',
            'eurozone': 'EU',
            'europe': 'EU',
            'jp': 'JP',
            'japan': 'JP',
            'ca': 'CA',
            'canada': 'CA',
            'au': 'AU',
            'australia': 'AU',
            'nz': 'NZ',
            'new zealand': 'NZ',
            'ch': 'CH',
            'switzerland': 'CH',
            'cn': 'CN',
            'china': 'CN'
        }
        return country_mapping.get(country.lower(), country.upper())

    def _standardize_alpha_vantage_event(self, event: Dict) -> Optional[Dict]:
        """标准化Alpha Vantage事件格式"""
        try:
            # 重要性映射
            importance_mapping = {
                'high': 'high',
                'medium': 'medium',
                'low': 'low'
            }
            
            # 国家代码映射
            country_mapping = {
                'US': 'us',
                'UK': 'uk',
                'EU': 'eu',
                'JP': 'jp',
                'CA': 'ca',
                'AU': 'au',
                'NZ': 'nz',
                'CH': 'ch',
                'CN': 'cn'
            }
            
            event_name = event.get('event', 'Unknown Event')
            event_country = event.get('country', '')
            
            standardized = {
                'name': event_name,
                'country': country_mapping.get(event_country, event_country.lower()),
                'importance': importance_mapping.get(event.get('importance', 'low'), 'low'),
                'date': event.get('date', ''),
                'time': event.get('time', ''),
                'currency_impact': self._get_currency_impact_for_event(event_country, event_name),
                'previous': event.get('previous', 'N/A'),
                'forecast': event.get('estimate', 'N/A'),
                'actual': event.get('actual', 'N/A'),
                'source': 'Alpha Vantage',
                'volatility_expected': 'high' if importance_mapping.get(event.get('importance', 'low')) == 'high' else 'medium',
                'original_data': event  # 保留原始数据用于调试
            }
            
            return standardized
            
        except Exception as e:
            print(f"标准化Alpha Vantage事件失败: {str(e)}")
            return None

    def _get_currency_impact_for_event(self, country: str, event_name: str) -> List[str]:
        """根据国家和事件名称获取影响的货币对"""
        currency_mapping = {
            'US': ['USD', 'EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'USD/CAD', 'AUD/USD'],
            'UK': ['GBP', 'GBP/USD', 'EUR/GBP', 'GBP/JPY', 'GBP/CHF'],
            'EU': ['EUR', 'EUR/USD', 'EUR/GBP', 'EUR/JPY', 'EUR/CHF'],
            'JP': ['JPY', 'USD/JPY', 'EUR/JPY', 'GBP/JPY', 'AUD/JPY'],
            'CA': ['CAD', 'USD/CAD', 'CAD/JPY', 'EUR/CAD'],
            'AU': ['AUD', 'AUD/USD', 'AUD/JPY', 'AUD/NZD', 'EUR/AUD'],
            'NZ': ['NZD', 'NZD/USD', 'AUD/NZD', 'NZD/JPY'],
            'CH': ['CHF', 'USD/CHF', 'EUR/CHF', 'GBP/CHF'],
            'CN': ['CNY', 'USD/CNY', 'EUR/CNY', 'GBP/CNY']
        }
        
        country_upper = country.upper()
        base_currencies = currency_mapping.get(country_upper, [country_upper])
        
        # 对于重要事件，扩大影响范围
        important_keywords = ['interest rate', 'inflation', 'gdp', 'employment', 'nonfarm', 'cpi', 'retail sales']
        if any(keyword in event_name.lower() for keyword in important_keywords):
            if country_upper == 'US':
                return ['All majors', 'USD pairs']
            elif country_upper in ['EU', 'UK', 'JP']:
                return base_currencies + ['Related pairs']
            else:
                return base_currencies + ['Regional currencies']
        
        return base_currencies

    def _get_simulated_economic_events(self, days_ahead: int, country: str = None) -> List[Dict]:
        """模拟经济事件数据（备用方案）"""
        events = []
        today = datetime.now()
        
        # 预定义的重要事件模板
        event_templates = [
            {
                'name': 'US Nonfarm Payrolls',
                'country': 'us',
                'importance': 'high',
                'currency_impact': ['USD', 'EUR/USD', 'GBP/USD', 'USD/JPY'],
                'previous': '199K',
                'forecast': '185K',
                'source': 'Bureau of Labor Statistics'
            },
            {
                'name': 'US CPI Inflation',
                'country': 'us', 
                'importance': 'high',
                'currency_impact': ['USD', 'EUR/USD', 'USD/JPY'],
                'previous': '3.2%',
                'forecast': '3.1%',
                'source': 'BLS'
            },
            {
                'name': 'Federal Reserve Interest Rate Decision',
                'country': 'us',
                'importance': 'high', 
                'currency_impact': ['USD', 'All majors'],
                'previous': '5.50%',
                'forecast': '5.50%',
                'source': 'Federal Reserve'
            },
            {
                'name': 'ECB Monetary Policy Statement',
                'country': 'eu',
                'importance': 'high',
                'currency_impact': ['EUR', 'EUR/USD', 'EUR/GBP'],
                'previous': '4.50%',
                'forecast': '4.50%',
                'source': 'European Central Bank'
            },
            {
                'name': 'Bank of England MPC Vote',
                'country': 'uk',
                'importance': 'high',
                'currency_impact': ['GBP', 'GBP/USD', 'EUR/GBP'],
                'previous': '6-2-1',
                'forecast': '7-1-1', 
                'source': 'Bank of England'
            }
        ]
        
        # 为未来几天生成事件
        for i in range(min(days_ahead, 7)):
            event_date = today + timedelta(days=i)
            
            # 每天添加1-3个事件
            daily_events = event_templates[:3] if i % 2 == 0 else event_templates[3:]
            
            for template in daily_events:
                if country and template['country'] != country:
                    continue
                    
                event = template.copy()
                event['date'] = event_date.strftime('%Y-%m-%d')
                event['time'] = self._get_typical_event_time(template['name'])
                event['volatility_expected'] = 'high' if template['importance'] == 'high' else 'medium'
                event['actual'] = 'N/A'
                
                events.append(event)
        
        return events

    def _get_typical_event_time(self, event_name: str) -> str:
        """获取典型事件发布时间"""
        time_mapping = {
            'US Nonfarm Payrolls': '08:30 EST',
            'US CPI Inflation': '08:30 EST',
            'Federal Reserve Interest Rate Decision': '14:00 EST',
            'ECB Monetary Policy Statement': '12:45 GMT',
            'Bank of England MPC Vote': '12:00 GMT'
        }
        return time_mapping.get(event_name, '09:00 EST')

    def get_forex_news(self, days_back: int = 1, currency_pair: str = None) -> Dict:
        """获取外汇交易相关新闻"""
        if not self.newsapi_key:
            return {"error": "NewsAPI密钥未配置"}

        try:
            base_query = "forex OR currency OR exchange rate OR central bank OR interest rate"
            
            if currency_pair and currency_pair in self.currency_pairs:
                pair_keywords = self.currency_pairs[currency_pair]
                additional_query = " OR ".join(pair_keywords)
                query = f"({base_query}) AND ({additional_query})"
            else:
                query = base_query

            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'from': from_date.strftime('%Y-%m-%d'),
                'to': to_date.strftime('%Y-%m-%d'),
                'language': 'en',
                'sortBy': 'publishedAt',
                'apiKey': self.newsapi_key,
                'pageSize': 50,
                'domains': 'bloomberg.com,reuters.com,forexlive.com,dailyfx.com,investing.com,fxstreet.com'
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get('status') == 'ok':
                return self._process_forex_news_data(data.get('articles', []))
            else:
                return {"error": f"NewsAPI错误: {data.get('message', '未知错误')}"}
                
        except Exception as e:
            return {"error": f"获取外汇新闻失败: {str(e)}"}

    def _identify_event_type(self, content: str) -> str:
        """识别事件类型"""
        content_lower = content.lower()
        
        for event_type, keywords in self.event_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return event_type
        
        return 'other'

    def _identify_affected_pairs(self, content: str) -> List[str]:
        """识别受影响的货币对"""
        content_lower = content.lower()
        affected_pairs = []
        
        for pair, keywords in self.currency_pairs.items():
            if any(keyword in content_lower for keyword in keywords):
                affected_pairs.append(pair)
        
        return affected_pairs if affected_pairs else ['Multiple pairs']

    def _assess_forex_importance(self, event_type: str, title: str) -> str:
        """评估外汇新闻重要性"""
        high_impact_keywords = [
            'rate decision', 'interest rate', 'nonfarm payrolls', 'nfp', 
            'cpi', 'inflation', 'gdp', 'federal reserve', 'ecb', 'boe', 'boj'
        ]
        
        title_lower = title.lower()
        if any(keyword in title_lower for keyword in high_impact_keywords):
            return 'high'
        elif event_type in ['central_bank_decision', 'inflation_data', 'employment_data']:
            return 'medium'
        else:
            return 'low'

    def _assess_trading_impact(self, event_type: str, importance: str) -> str:
        """评估交易影响"""
        if importance == 'high':
            return 'High volatility expected, adjust position sizes'
        elif importance == 'medium':
            return 'Moderate volatility, trade with caution'
        else:
            return 'Low impact, normal trading conditions'

    def _process_forex_news_data(self, articles: List) -> Dict:
        """处理外汇新闻数据"""
        processed_articles = []
        
        for article in articles:
            title = article.get('title', '')
            description = article.get('description', '')
            content = f"{title} {description}"
            
            event_type = self._identify_event_type(content)
            affected_pairs = self._identify_affected_pairs(content)
            importance = self._assess_forex_importance(event_type, title)
            trading_impact = self._assess_trading_impact(event_type, importance)
            
            processed_article = {
                'title': title,
                'description': description,
                'published_at': article.get('publishedAt', ''),
                'source': article.get('source', {}).get('name', ''),
                'url': article.get('url', ''),
                'event_type': event_type,
                'affected_currency_pairs': affected_pairs,
                'importance': importance,
                'trading_impact': trading_impact,
                'content_preview': description[:200] + '...' if description else '',
                'volatility_expected': 'high' if importance == 'high' else 'medium'
            }
            processed_articles.append(processed_article)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_articles': len(processed_articles),
            'articles': processed_articles,
            'high_impact_count': len([a for a in processed_articles if a['importance'] == 'high'])
        }

    def get_comprehensive_economic_calendar(self, currency_pair: str = None, days_ahead: int = 3) -> Dict:
        """
        获取综合经济日历（新闻 + 经济数据发布）
        """
        try:
            # 获取新闻数据
            news_data = self.get_forex_news(days_back=2, currency_pair=currency_pair)
            
            # 获取经济事件日程
            events_schedule = self.get_economic_events_schedule(days_ahead=days_ahead)
            
            # 使用OpenAI进行综合分析
            analysis_result = self.analyze_economic_calendar_with_openai(
                news_data, events_schedule, currency_pair
            )
            
            return {
                'currency_pair': currency_pair,
                'timeframe': f'next_{days_ahead}_days',
                'news_summary': {
                    'total_articles': news_data.get('total_articles', 0),
                    'high_impact_news': news_data.get('high_impact_count', 0)
                },
                'economic_events': {
                    'total_events': events_schedule.get('total_events', 0),
                    'high_impact_events': events_schedule.get('high_impact_events', 0)
                },
                'integrated_analysis': analysis_result,
                'trading_recommendations': self._generate_trading_recommendations(
                    news_data, events_schedule, currency_pair
                )
            }
            
        except Exception as e:
            return {"error": f"获取综合经济日历失败: {str(e)}"}

    def analyze_economic_calendar_with_openai(self, news_data: Dict, events_data: Dict, currency_pair: str = None) -> Dict:
        """使用OpenAI分析经济日历"""
        if not self.openai_api_key:
            return {"error": "OpenAI API密钥未配置"}
        
        if 'error' in news_data or 'error' in events_data:
            return {"error": "数据获取失败"}

        try:
            prompt = self._build_economic_calendar_prompt(news_data, events_data, currency_pair)
            
            api_params = {
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "system",
                        "content": """你是一个专业的外汇交易策略师。基于新闻事件和经济数据发布日程，
                        提供具体的交易策略和风险管理建议。重点关注高影响事件的时间安排和市场预期。"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.3
            }
            
            if self.openai_base_url:
                response = self._custom_openai_call(api_params)
            else:
                response = openai.ChatCompletion.create(**api_params)
            
            analysis_text = response.choices[0].message.content.strip()
            
            return {
                'currency_pair': currency_pair,
                'analysis': analysis_text,
                'key_events_timeline': self._extract_events_timeline(events_data),
                'risk_assessment': self._assess_calendar_risk(news_data, events_data)
            }
            
        except Exception as e:
            return {"error": f"经济日历分析失败: {str(e)}"}

    def _build_economic_calendar_prompt(self, news_data: Dict, events_data: Dict, currency_pair: str) -> str:
        """构建经济日历分析提示词"""
        
        prompt_parts = [
            f"请分析以下外汇市场信息，为{currency_pair if currency_pair else '主要货币对'}提供交易策略：",
            "",
            "=== 近期新闻事件 ==="
        ]
        
        # 添加高影响新闻
        high_impact_news = [a for a in news_data.get('articles', []) if a.get('importance') == 'high']
        for i, article in enumerate(high_impact_news[:3], 1):
            prompt_parts.append(f"{i}. {article.get('title', '')}")
            prompt_parts.append(f"   影响: {article.get('trading_impact', '')}")
            prompt_parts.append(f"   时间: {article.get('published_at', '')}")
        
        prompt_parts.append("")
        prompt_parts.append("=== 即将发布的经济数据 ===")
        
        # 添加即将发布的经济事件
        upcoming_events = events_data.get('events', [])
        high_impact_events = [e for e in upcoming_events if e.get('importance') == 'high']
        
        for i, event in enumerate(high_impact_events[:5], 1):
            prompt_parts.append(f"{i}. {event.get('name', '')}")
            prompt_parts.append(f"   时间: {event.get('date', '')} {event.get('time', '')}")
            prompt_parts.append(f"   预期: {event.get('forecast', 'N/A')} | 前值: {event.get('previous', 'N/A')}")
            prompt_parts.append(f"   影响货币: {', '.join(event.get('currency_impact', []))}")
        
        prompt_parts.extend([
            "",
            "请提供：",
            "1. 关键交易时间窗口分析",
            "2. 具体入场/出场点位建议", 
            "3. 事件驱动的交易策略",
            "4. 风险管理建议（仓位大小、止损设置）",
            "5. 重点关注的经济数据及其预期影响",
            "",
            "请用专业交易员的语言，提供具体可执行的建议。"
        ])
        
        return "\n".join(prompt_parts)

    def _custom_openai_call(self, api_params: Dict) -> Any:
        """自定义OpenAI API调用"""
        import requests
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        
        url = f"{self.openai_base_url}/chat/completions"
        response = requests.post(url, headers=headers, json=api_params, timeout=30)
        response.raise_for_status()
        
        return response.json()

    def _extract_events_timeline(self, events_data: Dict) -> List[Dict]:
        """提取事件时间线"""
        events = events_data.get('events', [])
        timeline = []
        
        for event in events[:10]:  # 限制前10个事件
            timeline.append({
                'name': event.get('name'),
                'date': event.get('date'),
                'time': event.get('time'),
                'importance': event.get('importance'),
                'currency_impact': event.get('currency_impact', [])
            })
        
        return timeline

    def _assess_calendar_risk(self, news_data: Dict, events_data: Dict) -> Dict:
        """评估日历风险"""
        high_impact_news = news_data.get('high_impact_count', 0)
        high_impact_events = events_data.get('high_impact_events', 0)
        
        total_high_impact = high_impact_news + high_impact_events
        
        if total_high_impact >= 3:
            risk_level = 'high'
        elif total_high_impact >= 1:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'high_impact_events_count': total_high_impact,
            'recommended_position_size': 'small' if risk_level == 'high' else 'normal',
            'trading_advice': 'avoid trading around high impact events' if risk_level == 'high' else 'trade with caution'
        }

    def _generate_trading_recommendations(self, news_data: Dict, events_data: Dict, currency_pair: str) -> Dict:
        """生成交易建议"""
        high_impact_events = events_data.get('high_impact_events', 0)
        
        return {
            'trading_bias': 'cautious' if high_impact_events > 0 else 'normal',
            'recommended_actions': [
                'Monitor high impact economic events',
                'Adjust position sizes based on volatility',
                'Set wider stops during news events'
            ],
            'key_events_to_watch': [e.get('name') for e in events_data.get('events', []) 
                                  if e.get('importance') == 'high'][:3]
        }


# 使用示例
if __name__ == "__main__":
    calendar = EconomicCalendar()
    
    # 获取综合经济日历
    comprehensive_calendar = calendar.get_comprehensive_economic_calendar("EUR/USD", 3)
    print("综合经济日历:", json.dumps(comprehensive_calendar, indent=2, ensure_ascii=False))
    
    # 获取经济事件日程
    events_schedule = calendar.get_economic_events_schedule(5, 'us')
    print("经济事件日程:", json.dumps(events_schedule, indent=2, ensure_ascii=False))