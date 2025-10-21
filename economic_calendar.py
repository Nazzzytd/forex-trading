# economic_calendar.py
import requests
import json
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import config


class EconomicCalendar:
    """
    经济日历工具 - 利用newapi获取新闻后筛选外汇新闻，获取重要经济数据发布信息，并利用OpenAI进行分析
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
        
        # 重要经济数据发布事件（更真实的分布）
        self.economic_events = {
            'us': [
                {
                    'name': 'Nonfarm Payrolls',
                    'frequency': 'monthly',
                    'importance': 'high',
                    'source': 'BLS',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'GBP/USD', 'USD/JPY'],
                    'typical_day': 1  # 每月第一个周五
                },
                {
                    'name': 'CPI Inflation',
                    'frequency': 'monthly', 
                    'importance': 'high',
                    'source': 'BLS',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'USD/JPY'],
                    'typical_day': 12  # 每月中旬
                },
                {
                    'name': 'Federal Funds Rate',
                    'frequency': '8_times_year',
                    'importance': 'high',
                    'source': 'Federal Reserve',
                    'typical_time': '14:00 EST',
                    'currency_impact': ['USD', 'All majors'],
                    'typical_day': 15  # 月中
                },
                {
                    'name': 'GDP Growth Rate',
                    'frequency': 'quarterly',
                    'importance': 'high',
                    'source': 'BEA',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'USD/JPY'],
                    'typical_day': 25  # 季度末
                },
                {
                    'name': 'Retail Sales',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'Census Bureau',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD'],
                    'typical_day': 15
                },
                {
                    'name': 'ISM Manufacturing PMI',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'ISM',
                    'typical_time': '10:00 EST',
                    'currency_impact': ['USD'],
                    'typical_day': 1
                },
                {
                    'name': 'PPI (Producer Price Index)',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'BLS',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD'],
                    'typical_day': 13
                },
                {
                    'name': 'Unemployment Rate',
                    'frequency': 'monthly',
                    'importance': 'high',
                    'source': 'BLS',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'GBP/USD'],
                    'typical_day': 1
                }
            ],
            'eu': [
                {
                    'name': 'ECB Interest Rate',
                    'frequency': '8_times_year',
                    'importance': 'high',
                    'source': 'ECB',
                    'typical_time': '12:45 GMT',
                    'currency_impact': ['EUR', 'EUR/USD', 'EUR/GBP'],
                    'typical_day': 10
                },
                {
                    'name': 'Eurozone CPI',
                    'frequency': 'monthly',
                    'importance': 'high',
                    'source': 'Eurostat',
                    'typical_time': '10:00 GMT',
                    'currency_impact': ['EUR', 'EUR/USD'],
                    'typical_day': 18
                },
                {
                    'name': 'German ZEW Economic Sentiment',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'ZEW',
                    'typical_time': '10:00 GMT',
                    'currency_impact': ['EUR', 'EUR/USD'],
                    'typical_day': 15
                },
                {
                    'name': 'German Ifo Business Climate',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'Ifo Institute',
                    'typical_time': '09:00 GMT',
                    'currency_impact': ['EUR', 'EUR/USD'],
                    'typical_day': 25
                }
            ],
            'uk': [
                {
                    'name': 'Bank of England Rate',
                    'frequency': '8_times_year',
                    'importance': 'high',
                    'source': 'BOE',
                    'typical_time': '12:00 GMT',
                    'currency_impact': ['GBP', 'GBP/USD', 'EUR/GBP'],
                    'typical_day': 5
                },
                {
                    'name': 'UK CPI Inflation',
                    'frequency': 'monthly',
                    'importance': 'high',
                    'source': 'ONS',
                    'typical_time': '07:00 GMT',
                    'currency_impact': ['GBP', 'GBP/USD'],
                    'typical_day': 18
                },
                {
                    'name': 'UK Retail Sales',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'ONS',
                    'typical_time': '07:00 GMT',
                    'currency_impact': ['GBP', 'GBP/USD'],
                    'typical_day': 20
                }
            ],
            'jp': [
                {
                    'name': 'Bank of Japan Rate',
                    'frequency': '8_times_year',
                    'importance': 'high',
                    'source': 'BOJ',
                    'typical_time': '时间 varies',
                    'currency_impact': ['JPY', 'USD/JPY', 'EUR/JPY'],
                    'typical_day': 20
                },
                {
                    'name': 'Tokyo CPI',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'Statistics Japan',
                    'typical_time': '时间 varies',
                    'currency_impact': ['JPY', 'USD/JPY'],
                    'typical_day': 27
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
            # 使用改进的模拟数据
            events = self._get_realistic_simulated_events(days_ahead, country)
            
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

    def _get_realistic_simulated_events(self, days_ahead: int, country: str = None) -> List[Dict]:
        """生成更真实的经济事件数据"""
        events = []
        today = datetime.now()
        
        # 确保事件不重复且分布合理
        used_events = set()
        
        for i in range(min(days_ahead, 30)):  # 限制最大天数
            event_date = today + timedelta(days=i)
            day_of_month = event_date.day
            weekday = event_date.weekday()  # 0=Monday, 6=Sunday
            
            # 跳过周末（大多数经济数据不在周末发布）
            if weekday >= 5:
                continue
                
            # 为每天选择事件
            daily_events = []
            
            for region, region_events in self.economic_events.items():
                if country and region != country:
                    continue
                    
                for template in region_events:
                    # 检查事件是否已使用（避免重复）
                    event_key = f"{template['name']}_{event_date.strftime('%Y%m')}"
                    if event_key in used_events:
                        continue
                        
                    # 基于频率和典型日期决定是否包含该事件
                    should_include = self._should_include_event(template, day_of_month, i)
                    
                    if should_include and len(daily_events) < 2:  # 每天最多2个事件
                        event = template.copy()
                        event['date'] = event_date.strftime('%Y-%m-%d')
                        event['time'] = self._get_typical_event_time(template['name'])
                        event['volatility_expected'] = 'high' if template['importance'] == 'high' else 'medium'
                        event['actual'] = 'N/A'
                        
                        # 添加预测和前值数据
                        event.update(self._get_event_forecast_data(template['name']))
                        
                        daily_events.append(event)
                        used_events.add(event_key)
                        
                        # 如果是高影响事件，当天不再添加其他高影响事件
                        if template['importance'] == 'high':
                            break
            
            events.extend(daily_events)
        
        return events

    def _should_include_event(self, template: Dict, day_of_month: int, days_from_today: int) -> bool:
        """决定是否包含特定事件"""
        typical_day = template.get('typical_day', 15)
        frequency = template.get('frequency', 'monthly')
        importance = template.get('importance', 'medium')
        
        # 基于频率和日期决定
        if frequency == 'monthly':
            # 每月事件：在典型日期附近几天内
            day_diff = abs(day_of_month - typical_day)
            return day_diff <= 2 and days_from_today <= 14  # 只在未来2周内
            
        elif frequency == 'quarterly':
            # 季度事件：只在特定月份
            current_month = datetime.now().month
            quarter_months = [1, 4, 7, 10]  # 季度初月
            return current_month in quarter_months and day_of_month >= typical_day - 2
            
        elif frequency == '8_times_year':
            # 每年8次（央行会议）
            meeting_months = [1, 3, 5, 7, 9, 11]  # 大致分布
            current_month = datetime.now().month
            return current_month in meeting_months and day_of_month >= typical_day - 1
            
        return False

    def _get_event_forecast_data(self, event_name: str) -> Dict:
        """获取事件的预测数据"""
        forecast_data = {
            'US Nonfarm Payrolls': {'previous': '199K', 'forecast': '185K'},
            'US CPI Inflation': {'previous': '3.2%', 'forecast': '3.1%'},
            'Federal Funds Rate': {'previous': '5.50%', 'forecast': '5.50%'},
            'GDP Growth Rate': {'previous': '2.1%', 'forecast': '2.3%'},
            'Retail Sales': {'previous': '0.6%', 'forecast': '0.4%'},
            'ISM Manufacturing PMI': {'previous': '49.4', 'forecast': '49.8'},
            'Unemployment Rate': {'previous': '3.8%', 'forecast': '3.8%'},
            'PPI (Producer Price Index)': {'previous': '0.3%', 'forecast': '0.2%'},
            'ECB Interest Rate': {'previous': '4.50%', 'forecast': '4.50%'},
            'Eurozone CPI': {'previous': '2.4%', 'forecast': '2.3%'},
            'Bank of England Rate': {'previous': '5.25%', 'forecast': '5.25%'},
            'UK CPI Inflation': {'previous': '2.3%', 'forecast': '2.1%'}
        }
        
        return forecast_data.get(event_name, {'previous': 'N/A', 'forecast': 'N/A'})

    def _get_typical_event_time(self, event_name: str) -> str:
        """获取典型事件发布时间"""
        time_mapping = {
            'US Nonfarm Payrolls': '08:30 EST',
            'US CPI Inflation': '08:30 EST',
            'Federal Funds Rate': '14:00 EST',
            'GDP Growth Rate': '08:30 EST',
            'Retail Sales': '08:30 EST',
            'ISM Manufacturing PMI': '10:00 EST',
            'Unemployment Rate': '08:30 EST',
            'PPI (Producer Price Index)': '08:30 EST',
            'ECB Interest Rate': '12:45 GMT',
            'Eurozone CPI': '10:00 GMT',
            'German ZEW Economic Sentiment': '10:00 GMT',
            'German Ifo Business Climate': '09:00 GMT',
            'Bank of England Rate': '12:00 GMT',
            'UK CPI Inflation': '07:00 GMT',
            'UK Retail Sales': '07:00 GMT',
            'Bank of Japan Rate': '时间 varies',
            'Tokyo CPI': '时间 varies'
        }
        return time_mapping.get(event_name, '09:00 EST')

    def get_forex_news(self, days_back: int = 1, currency_pair: str = None) -> Dict:
        """获取外汇交易相关新闻"""
        if not self.newsapi_key:
            # 返回模拟新闻数据
            return self._get_simulated_forex_news(currency_pair)

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
                print(f"NewsAPI错误，使用模拟数据: {data.get('message', '未知错误')}")
                return self._get_simulated_forex_news(currency_pair)
                
        except Exception as e:
            print(f"获取外汇新闻失败，使用模拟数据: {str(e)}")
            return self._get_simulated_forex_news(currency_pair)

    def _get_simulated_forex_news(self, currency_pair: str = None) -> Dict:
        """模拟外汇新闻数据"""
        base_news = [
            {
                'title': 'Fed Officials Signal Patience on Rate Cuts Amid Inflation Concerns',
                'description': 'Federal Reserve officials emphasize need for more evidence of inflation cooling before considering rate reductions.',
                'importance': 'high',
                'event_type': 'central_bank_decision',
                'affected_pairs': ['USD', 'EUR/USD', 'GBP/USD', 'USD/JPY']
            },
            {
                'title': 'ECB Maintains Hawkish Stance Despite Economic Slowdown',
                'description': 'European Central Bank keeps rates steady while monitoring inflation trends in Eurozone economies.',
                'importance': 'medium',
                'event_type': 'central_bank_decision', 
                'affected_pairs': ['EUR', 'EUR/USD', 'EUR/GBP']
            },
            {
                'title': 'BOE Faces Dilemma as UK Inflation Remains Sticky',
                'description': 'Bank of England weighs growth concerns against persistent inflation pressures.',
                'importance': 'medium',
                'event_type': 'central_bank_decision',
                'affected_pairs': ['GBP', 'GBP/USD', 'EUR/GBP']
            },
            {
                'title': 'US Jobs Data Shows Resilient Labor Market',
                'description': 'Latest employment figures suggest continued strength in the US economy.',
                'importance': 'medium',
                'event_type': 'employment_data',
                'affected_pairs': ['USD', 'EUR/USD', 'GBP/USD']
            }
        ]
        
        # 过滤特定货币对相关的新闻
        if currency_pair:
            filtered_news = [
                news for news in base_news 
                if currency_pair in news['affected_pairs'] or 'All majors' in news['affected_pairs']
            ]
        else:
            filtered_news = base_news
        
        processed_articles = []
        for i, news in enumerate(filtered_news):
            processed_articles.append({
                'title': news['title'],
                'description': news['description'],
                'published_at': (datetime.now() - timedelta(hours=i*3)).isoformat(),
                'source': 'Simulated Financial News',
                'url': f'https://example.com/news/{i}',
                'event_type': news['event_type'],
                'affected_currency_pairs': news['affected_pairs'],
                'importance': news['importance'],
                'trading_impact': 'High volatility expected' if news['importance'] == 'high' else 'Moderate impact',
                'content_preview': news['description'][:200] + '...',
                'volatility_expected': 'high' if news['importance'] == 'high' else 'medium'
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_articles': len(processed_articles),
            'articles': processed_articles,
            'high_impact_count': len([a for a in processed_articles if a['importance'] == 'high'])
        }

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

    def get_comprehensive_economic_calendar(self, currency_pair: str = None, days_ahead: int = 3) -> Dict:
        """
        获取综合经济日历（新闻 + 经济数据发布）
        """
        try:
            # 获取新闻数据
            news_data = self.get_forex_news(days_back=2, currency_pair=currency_pair)
            
            # 获取经济事件日程
            events_schedule = self.get_economic_events_schedule(days_ahead=days_ahead)
            
            # 使用OpenAI进行综合分析（带超时处理）
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
                ),
                'key_events_timeline': self._extract_events_timeline(events_schedule)
            }
            
        except Exception as e:
            return {"error": f"获取综合经济日历失败: {str(e)}"}

    def analyze_economic_calendar_with_openai(self, news_data: Dict, events_data: Dict, currency_pair: str = None) -> Dict:
        """使用OpenAI分析经济日历（修复版）"""
        if not self.openai_api_key:
            return {
                "analysis": "OpenAI API未配置，使用基础分析", 
                "status": "fallback",
                "currency_pair": currency_pair,
                "key_events_timeline": self._extract_events_timeline(events_data),
                "risk_assessment": self._assess_calendar_risk(news_data, events_data)
            }
        
        if 'error' in news_data or 'error' in events_data:
            return {"error": "数据获取失败"}

        try:
            prompt = self._build_economic_calendar_prompt(news_data, events_data, currency_pair)
            
            # 简化分析作为fallback
            simplified_analysis = self._get_simplified_analysis(news_data, events_data, currency_pair)
            
            # 只有在网络稳定时才调用OpenAI
            try:
                # 使用正确的OpenAI API调用方式
                client = openai.OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url if self.openai_base_url else None
                )
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": """你是一个专业的外汇交易策略师。提供简洁的交易策略和风险管理建议。"""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=800,
                    temperature=0.3,
                    timeout=15
                )
                
                analysis_text = response.choices[0].message.content.strip()
                
                return {
                    'currency_pair': currency_pair,
                    'analysis': analysis_text,
                    'key_events_timeline': self._extract_events_timeline(events_data),
                    'risk_assessment': self._assess_calendar_risk(news_data, events_data),
                    'status': 'openai_analysis'
                }
                
            except Exception as e:
                print(f"OpenAI分析失败，使用简化分析: {str(e)}")
                return {
                    'currency_pair': currency_pair,
                    'analysis': simplified_analysis,
                    'key_events_timeline': self._extract_events_timeline(events_data),
                    'risk_assessment': self._assess_calendar_risk(news_data, events_data),
                    'status': 'simplified_analysis'
                }
            
        except Exception as e:
            return {"error": f"经济日历分析失败: {str(e)}"}

    def _get_simplified_analysis(self, news_data: Dict, events_data: Dict, currency_pair: str) -> str:
        """提供简化分析"""
        high_impact_events = events_data.get('high_impact_events', 0)
        high_impact_news = news_data.get('high_impact_count', 0)
        
        analysis_parts = [
            f"【{currency_pair if currency_pair else '主要货币对'}交易分析】",
            f"高影响事件数量: {high_impact_events}个",
            f"重要新闻数量: {high_impact_news}条",
            "",
            "交易建议:"
        ]
        
        if high_impact_events > 2:
            analysis_parts.extend([
                "⚠️ 高风险周期 - 多个高影响事件集中",
                "• 减少仓位规模50%以上",
                "• 避免在数据发布前后15分钟内交易", 
                "• 设置更宽的止损位",
                "• 重点关注: NFP, CPI, 央行决议"
            ])
        elif high_impact_events > 0:
            analysis_parts.extend([
                "🟡 中等风险 - 有高影响事件",
                "• 适度降低仓位规模",
                "• 数据发布时保持谨慎",
                "• 关注实际数据与预期的差异"
            ])
        else:
            analysis_parts.extend([
                "🟢 低风险周期 - 无重大事件",
                "• 正常交易规模",
                "• 关注技术面交易机会",
                "• 仍建议设置合理止损"
            ])
        
        return "\n".join(analysis_parts)

    def _build_economic_calendar_prompt(self, news_data: Dict, events_data: Dict, currency_pair: str) -> str:
        """构建经济日历分析提示词"""
        
        prompt_parts = [
            f"请简要分析以下外汇市场信息，为{currency_pair if currency_pair else '主要货币对'}提供交易策略：",
            "",
            "近期重要新闻:"
        ]
        
        # 添加高影响新闻
        high_impact_news = [a for a in news_data.get('articles', []) if a.get('importance') == 'high']
        for i, article in enumerate(high_impact_news[:2], 1):
            prompt_parts.append(f"{i}. {article.get('title', '')}")
        
        prompt_parts.append("")
        prompt_parts.append("即将发布的经济数据:")
        
        # 添加即将发布的经济事件
        upcoming_events = events_data.get('events', [])
        high_impact_events = [e for e in upcoming_events if e.get('importance') == 'high']
        
        for i, event in enumerate(high_impact_events[:3], 1):
            prompt_parts.append(f"{i}. {event.get('name', '')} - {event.get('date', '')} {event.get('time', '')}")
        
        prompt_parts.extend([
            "",
            "请简要提供：",
            "1. 关键交易时间窗口",
            "2. 风险管理建议", 
            "3. 重点关注的数据",
            "",
            "回复请保持简洁。"
        ])
        
        return "\n".join(prompt_parts)

    def _extract_events_timeline(self, events_data: Dict) -> List[Dict]:
        """提取事件时间线"""
        events = events_data.get('events', [])
        timeline = []
        
        # 按日期分组
        date_groups = {}
        for event in events:
            date = event.get('date')
            if date not in date_groups:
                date_groups[date] = []
            date_groups[date].append(event)
        
        # 为每个日期选择最重要的2个事件
        for date, date_events in list(date_groups.items())[:7]:  # 限制7天
            # 按重要性排序
            sorted_events = sorted(date_events, 
                                 key=lambda x: 0 if x.get('importance') == 'high' else 1)
            
            for event in sorted_events[:2]:  # 每天最多2个事件
                timeline.append({
                    'name': event.get('name'),
                    'date': event.get('date'),
                    'time': event.get('time'),
                    'importance': event.get('importance'),
                    'currency_impact': event.get('currency_impact', [])[:3]  # 限制显示数量
                })
        
        return timeline

    def _assess_calendar_risk(self, news_data: Dict, events_data: Dict) -> Dict:
        """评估日历风险"""
        high_impact_news = news_data.get('high_impact_count', 0)
        high_impact_events = events_data.get('high_impact_events', 0)
        
        total_high_impact = high_impact_news + high_impact_events
        
        if total_high_impact >= 3:
            risk_level = 'high'
            position_size = 'small (25-50% normal)'
            advice = 'Avoid trading around high impact events'
        elif total_high_impact >= 1:
            risk_level = 'medium' 
            position_size = 'reduced (50-75% normal)'
            advice = 'Trade with caution during data releases'
        else:
            risk_level = 'low'
            position_size = 'normal'
            advice = 'Normal trading conditions'
        
        return {
            'risk_level': risk_level,
            'high_impact_events_count': total_high_impact,
            'recommended_position_size': position_size,
            'trading_advice': advice
        }

    def _generate_trading_recommendations(self, news_data: Dict, events_data: Dict, currency_pair: str) -> Dict:
        """生成交易建议"""
        high_impact_events = events_data.get('high_impact_events', 0)
        
        recommendations = {
            'trading_bias': 'cautious' if high_impact_events > 0 else 'normal',
            'recommended_actions': [
                'Monitor economic calendar for event timing',
                'Adjust position sizes based on volatility expectations',
                'Use wider stop losses during high impact events'
            ],
            'key_events_to_watch': []
        }
        
        # 添加具体事件
        events = events_data.get('events', [])
        high_impact_events_list = [e for e in events if e.get('importance') == 'high']
        for event in high_impact_events_list[:3]:
            recommendations['key_events_to_watch'].append({
                'name': event.get('name'),
                'date': event.get('date'),
                'time': event.get('time')
            })
        
        return recommendations


# 使用示例
if __name__ == "__main__":
    print("🔧 配置检查:")
    calendar = EconomicCalendar()
    
    print(f"   Alpha Vantage API: {'✅ 已设置' if calendar.alpha_vantage_key else '❌ 未设置'}")
    print(f"   NewsAPI: {'✅ 已设置' if calendar.newsapi_key else '❌ 未设置'}")
    print(f"   OpenAI API Key: {'✅ 已设置' if calendar.openai_api_key else '❌ 未设置'}")
    print(f"   OpenAI Base URL: {'✅ 已设置' if calendar.openai_base_url else '❌ 未设置'}")
    
    # 获取综合经济日历
    print("\n📊 获取综合经济日历...")
    comprehensive_calendar = calendar.get_comprehensive_economic_calendar("EUR/USD", 3)
    print("综合经济日历分析完成!")
    
    # 显示关键信息
    if 'integrated_analysis' in comprehensive_calendar:
        analysis = comprehensive_calendar['integrated_analysis']
        if 'analysis' in analysis:
            print(f"\n📈 分析结果 ({analysis.get('status', 'unknown')}):")
            print(analysis['analysis'])
    
    # 显示交易建议
    if 'trading_recommendations' in comprehensive_calendar:
        recs = comprehensive_calendar['trading_recommendations']
        print(f"\n💡 交易建议 (偏向: {recs['trading_bias']}):")
        for action in recs['recommended_actions']:
            print(f"   • {action}")
    
    # 获取经济事件日程
    print("\n📅 获取经济事件日程...")
    events_schedule = calendar.get_economic_events_schedule(5, 'us')
    print(f"找到 {events_schedule.get('total_events', 0)} 个事件, 其中 {events_schedule.get('high_impact_events', 0)} 个高影响事件")