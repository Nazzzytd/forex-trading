# economic_calendar_alpha_vantage.py
import requests
import json
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import config


class EconomicCalendar:
    """
    经济日历工具 - 使用Alpha Vantage获取外汇新闻和重要经济数据发布信息，并利用OpenAI进行分析
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
        
        # Alpha Vantage相关配置
        self.alpha_vantage_base_url = "https://www.alphavantage.co/query"
        
        # 外汇相关主题
        self.forex_topics = "forex,economic_indicator,currency,central_banks,monetary_policy"
        
        # 货币对到股票代码的映射（用于新闻过滤）
        self.currency_to_tickers = {
            'EUR/USD': ['EURUSD', 'EUR', 'USD'],
            'GBP/USD': ['GBPUSD', 'GBP', 'USD'],
            'USD/JPY': ['USDJPY', 'USD', 'JPY'],
            'USD/CHF': ['USDCHF', 'USD', 'CHF'],
            'AUD/USD': ['AUDUSD', 'AUD', 'USD'],
            'USD/CAD': ['USDCAD', 'USD', 'CAD'],
            'NZD/USD': ['NZDUSD', 'NZD', 'USD'],
            'EUR/GBP': ['EURGBP', 'EUR', 'GBP'],
            'EUR/JPY': ['EURJPY', 'EUR', 'JPY']
        }

        # 重要经济数据发布事件
        self.economic_events = {
            'us': [
                {
                    'name': 'Nonfarm Payrolls',
                    'frequency': 'monthly',
                    'importance': 'high',
                    'source': 'BLS',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'GBP/USD', 'USD/JPY'],
                    'typical_day': 1,
                    'av_ticker': 'NFP'  # Alpha Vantage中的标识
                },
                {
                    'name': 'CPI Inflation',
                    'frequency': 'monthly', 
                    'importance': 'high',
                    'source': 'BLS',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'USD/JPY'],
                    'typical_day': 12,
                    'av_ticker': 'CPI'
                },
                {
                    'name': 'Federal Funds Rate',
                    'frequency': '8_times_year',
                    'importance': 'high',
                    'source': 'Federal Reserve',
                    'typical_time': '14:00 EST',
                    'currency_impact': ['USD', 'All majors'],
                    'typical_day': 15,
                    'av_ticker': 'FED'
                },
                {
                    'name': 'GDP Growth Rate',
                    'frequency': 'quarterly',
                    'importance': 'high',
                    'source': 'BEA',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD', 'EUR/USD', 'USD/JPY'],
                    'typical_day': 25,
                    'av_ticker': 'GDP'
                },
                {
                    'name': 'Retail Sales',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'Census Bureau',
                    'typical_time': '08:30 EST',
                    'currency_impact': ['USD'],
                    'typical_day': 15,
                    'av_ticker': 'RETAIL'
                },
                {
                    'name': 'ISM Manufacturing PMI',
                    'frequency': 'monthly',
                    'importance': 'medium',
                    'source': 'ISM',
                    'typical_time': '10:00 EST',
                    'currency_impact': ['USD'],
                    'typical_day': 1,
                    'av_ticker': 'PMI'
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
                    'typical_day': 10,
                    'av_ticker': 'ECB'
                },
                {
                    'name': 'Eurozone CPI',
                    'frequency': 'monthly',
                    'importance': 'high',
                    'source': 'Eurostat',
                    'typical_time': '10:00 GMT',
                    'currency_impact': ['EUR', 'EUR/USD'],
                    'typical_day': 18,
                    'av_ticker': 'EURO_CPI'
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
                    'typical_day': 5,
                    'av_ticker': 'BOE'
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
                    'typical_day': 20,
                    'av_ticker': 'BOJ'
                }
            ]
        }

        # 外汇交易相关事件关键词映射
        self.event_keywords = {
            'central_bank_decision': [
                'interest rate decision', 'federal reserve', 'fed meeting', 'ecb decision',
                'bank of england', 'boe meeting', 'bank of japan', 'boj meeting',
                'monetary policy', 'central bank', 'rate hike', 'rate cut'
            ],
            'inflation_data': [
                'cpi', 'consumer price index', 'inflation data', 'core cpi',
                'pce price index', 'inflation report', 'price pressure'
            ],
            'employment_data': [
                'nonfarm payrolls', 'nfp', 'unemployment rate', 'jobless claims',
                'employment change', 'adp employment', 'wage growth', 'jobs report'
            ],
            'gdp_growth': [
                'gdp growth', 'gross domestic product', 'economic growth',
                'preliminary gdp', 'final gdp', 'recession', 'expansion'
            ],
            'retail_sales': [
                'retail sales', 'core retail sales', 'consumer spending',
                'consumer confidence', 'spending data'
            ],
            'manufacturing_pmi': [
                'manufacturing pmi', 'services pmi', 'composite pmi',
                'ism manufacturing', 'ism services', 'purchasing managers'
            ]
        }

    def get_alpha_vantage_news_sentiment(self, topics: str = None, tickers: str = None, limit: int = 50) -> Dict:
        """
        使用Alpha Vantage获取市场新闻和情绪数据
        """
        if not self.alpha_vantage_key:
            return {"error": "Alpha Vantage API密钥未配置"}
        
        try:
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.alpha_vantage_key,
                'sort': 'LATEST',
                'limit': limit
            }
            
            # 添加主题和股票代码过滤
            if topics:
                params['topics'] = topics
            if tickers:
                params['tickers'] = tickers
            
            response = requests.get(self.alpha_vantage_base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if 'feed' not in data:
                print(f"Alpha Vantage新闻API返回异常: {data}")
                return self._get_simulated_news()
            
            return self._process_alpha_vantage_news(data['feed'])
            
        except Exception as e:
            print(f"Alpha Vantage新闻获取失败: {str(e)}")
            return self._get_simulated_news()

    def _process_alpha_vantage_news(self, news_feed: List) -> Dict:
        """处理Alpha Vantage新闻数据"""
        processed_articles = []
        
        for article in news_feed[:30]:  # 限制前30条
            try:
                # 提取基本信息
                title = article.get('title', '')
                summary = article.get('summary', '')
                published = article.get('time_published', '')
                source = article.get('source', 'Unknown')
                url = article.get('url', '')
                
                # 情绪分析数据
                sentiment_info = article.get('overall_sentiment_score', 0)
                sentiment_label = article.get('overall_sentiment_label', 'neutral')
                relevance_score = article.get('relevance_score', '0')
                
                # 相关股票和主题
                ticker_sentiment = article.get('ticker_sentiment', [])
                topics = [item['topic'] for item in article.get('topics', [])]
                
                # 提取相关货币对
                related_currencies = self._extract_currencies_from_tickers(ticker_sentiment)
                
                # 识别事件类型
                event_type = self._identify_event_type(title + " " + summary)
                
                # 评估重要性
                importance = self._assess_news_importance(sentiment_label, event_type, title, float(relevance_score))
                
                # 计算交易影响
                trading_impact = self._assess_trading_impact_from_sentiment(sentiment_label, importance, sentiment_info)
                
                processed_articles.append({
                    'title': title,
                    'summary': summary,
                    'published_at': published,
                    'source': source,
                    'url': url,
                    'sentiment_score': sentiment_info,
                    'sentiment_label': sentiment_label,
                    'relevance_score': relevance_score,
                    'related_tickers': [item['ticker'] for item in ticker_sentiment],
                    'ticker_sentiment': ticker_sentiment,
                    'topics': topics,
                    'event_type': event_type,
                    'affected_currency_pairs': related_currencies,
                    'importance': importance,
                    'trading_impact': trading_impact,
                    'volatility_expected': 'high' if importance == 'high' else 'medium',
                    'content_preview': summary[:150] + '...' if len(summary) > 150 else summary
                })
                
            except Exception as e:
                print(f"处理新闻文章时出错: {e}")
                continue
        
        # 计算整体市场情绪
        overall_sentiment = self._calculate_overall_sentiment(processed_articles)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_articles': len(processed_articles),
            'articles': processed_articles,
            'overall_sentiment': overall_sentiment,
            'high_impact_count': len([a for a in processed_articles if a['importance'] == 'high']),
            'bullish_count': len([a for a in processed_articles if a['sentiment_label'] == 'bullish']),
            'bearish_count': len([a for a in processed_articles if a['sentiment_label'] == 'bearish']),
            'source': 'Alpha Vantage'
        }

    def _extract_currencies_from_tickers(self, ticker_sentiment: List) -> List[str]:
        """从股票代码中提取相关货币对"""
        currencies = set()
        
        for item in ticker_sentiment:
            ticker = item.get('ticker', '')
            # 常见的货币对和货币代码
            if ticker in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']:
                currencies.add(ticker)
            elif ticker in ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']:
                # 找到包含该货币的货币对
                for pair in self.currency_to_tickers.keys():
                    if ticker in pair:
                        currencies.add(pair)
        
        return list(currencies) if currencies else ['Multiple pairs']

    def _calculate_overall_sentiment(self, articles: List) -> Dict:
        """计算整体市场情绪"""
        if not articles:
            return {'score': 0, 'label': 'neutral', 'strength': 'weak'}
        
        scores = [a['sentiment_score'] for a in articles if a.get('sentiment_score') is not None]
        if not scores:
            return {'score': 0, 'label': 'neutral', 'strength': 'weak'}
        
        avg_score = sum(scores) / len(scores)
        
        # 确定情绪标签和强度
        if avg_score >= 0.35:
            label = 'bullish'
            strength = 'strong' if avg_score >= 0.6 else 'moderate'
        elif avg_score <= -0.35:
            label = 'bearish'
            strength = 'strong' if avg_score <= -0.6 else 'moderate'
        else:
            label = 'neutral'
            strength = 'weak'
        
        return {
            'score': round(avg_score, 3),
            'label': label,
            'strength': strength,
            'description': f"整体市场情绪{label}，强度{strength}"
        }

    def _assess_news_importance(self, sentiment_label: str, event_type: str, title: str, relevance_score: float) -> str:
        """评估新闻重要性"""
        # 高影响关键词
        high_impact_keywords = [
            'rate decision', 'interest rate', 'nonfarm payrolls', 'nfp', 
            'cpi', 'inflation', 'gdp', 'federal reserve', 'ecb', 'boe', 'boj',
            'emergency', 'crisis', 'recession', 'stimulus', 'quantitative easing'
        ]
        
        title_lower = title.lower()
        
        # 基于多个因素评估重要性
        score = 0
        
        # 情绪强度
        if sentiment_label in ['bullish', 'bearish']:
            score += 2
        
        # 事件类型
        if event_type in ['central_bank_decision', 'inflation_data', 'employment_data']:
            score += 2
        
        # 关键词匹配
        if any(keyword in title_lower for keyword in high_impact_keywords):
            score += 2
        
        # 相关性分数
        score += relevance_score
        
        if score >= 4:
            return 'high'
        elif score >= 2:
            return 'medium'
        else:
            return 'low'

    def _assess_trading_impact_from_sentiment(self, sentiment_label: str, importance: str, sentiment_score: float) -> str:
        """基于情绪评估交易影响"""
        sentiment_strength = "强烈" if abs(sentiment_score) >= 0.5 else "温和"
        
        if importance == 'high':
            if sentiment_label == 'bearish':
                return f'高负面影响预期，{sentiment_strength}看跌情绪，建议避险头寸'
            elif sentiment_label == 'bullish':
                return f'高正面影响预期，{sentiment_strength}看涨情绪，建议风险头寸'
            else:
                return f'高影响事件，{sentiment_strength}中性情绪，密切监控'
        elif importance == 'medium':
            return '中等影响，谨慎交易，注意风险管理'
        else:
            return '低影响，正常交易环境'

    def get_forex_specific_news(self, currency_pair: str = None, days_back: int = 1) -> Dict:
        """获取特定货币对相关的外汇新闻"""
        if currency_pair and currency_pair in self.currency_to_tickers:
            tickers = ",".join(self.currency_to_tickers[currency_pair])
            return self.get_alpha_vantage_news_sentiment(topics=self.forex_topics, tickers=tickers)
        else:
            return self.get_alpha_vantage_news_sentiment(topics=self.forex_topics)

    def get_economic_events_schedule(self, days_ahead: int = 7, country: str = None) -> Dict:
        """获取经济数据发布日程"""
        try:
            # 尝试使用Alpha Vantage获取真实经济日历数据
            real_events = self._get_alpha_vantage_economic_calendar(days_ahead, country)
            if real_events:
                return real_events
            
            # 回退到模拟数据
            events = self._get_realistic_simulated_events(days_ahead, country)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'timeframe': f'next_{days_ahead}_days',
                'country_filter': country,
                'total_events': len(events),
                'high_impact_events': len([e for e in events if e.get('importance') == 'high']),
                'events': events,
                'source': 'simulated_data'
            }
            
        except Exception as e:
            return {"error": f"获取经济事件日程失败: {str(e)}"}

    def _get_alpha_vantage_economic_calendar(self, days_ahead: int, country: str = None) -> Optional[Dict]:
        """使用Alpha Vantage获取经济日历数据"""
        if not self.alpha_vantage_key:
            return None
        
        try:
            # 设置时间范围
            today = datetime.now().date()
            end_date = today + timedelta(days=days_ahead)
            
            params = {
                'function': 'ECONOMIC_CALENDAR',
                'apikey': self.alpha_vantage_key,
                'time_from': today.strftime('%Y%m%dT0000'),
                'time_to': end_date.strftime('%Y%m%dT2359')
            }
            
            response = requests.get(self.alpha_vantage_base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' not in data:
                return None
            
            events = []
            for event in data['data']:
                standardized_event = self._standardize_alpha_vantage_event(event)
                if standardized_event:
                    events.append(standardized_event)
            
            if events:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'timeframe': f'next_{days_ahead}_days',
                    'country_filter': country,
                    'total_events': len(events),
                    'high_impact_events': len([e for e in events if e.get('importance') == 'high']),
                    'events': events,
                    'source': 'Alpha Vantage'
                }
            
        except Exception as e:
            print(f"Alpha Vantage经济日历获取失败: {str(e)}")
        
        return None

    def _standardize_alpha_vantage_event(self, event: Dict) -> Optional[Dict]:
        """标准化Alpha Vantage事件格式"""
        try:
            event_name = event.get('event', 'Unknown Event')
            event_country = event.get('country', '')
            
            # 重要性映射
            importance_mapping = {
                'high': 'high',
                'medium': 'medium', 
                'low': 'low'
            }
            
            standardized = {
                'name': event_name,
                'country': event_country.lower(),
                'importance': importance_mapping.get(event.get('importance', 'low'), 'low'),
                'date': event.get('date', ''),
                'time': event.get('time', ''),
                'currency_impact': self._get_currency_impact_for_event(event_country, event_name),
                'previous': event.get('previous', 'N/A'),
                'forecast': event.get('estimate', 'N/A'),
                'actual': event.get('actual', 'N/A'),
                'source': 'Alpha Vantage',
                'volatility_expected': 'high' if importance_mapping.get(event.get('importance', 'low')) == 'high' else 'medium'
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
            'CH': ['CHF', 'USD/CHF', 'EUR/CHF', 'GBP/CHF']
        }
        
        country_upper = country.upper()
        base_currencies = currency_mapping.get(country_upper, [country_upper])
        
        # 对于重要事件，扩大影响范围
        important_keywords = ['interest rate', 'inflation', 'gdp', 'employment', 'nonfarm', 'cpi']
        if any(keyword in event_name.lower() for keyword in important_keywords):
            if country_upper == 'US':
                return ['All majors', 'USD pairs']
            elif country_upper in ['EU', 'UK', 'JP']:
                return base_currencies + ['Related pairs']
        
        return base_currencies

    # 保留原有的模拟数据生成方法
    def _get_realistic_simulated_events(self, days_ahead: int, country: str = None) -> List[Dict]:
        """生成更真实的经济事件数据（备用）"""
        # ... [原有的模拟数据生成代码]
        events = []
        # 实现细节...
        return events

    def get_comprehensive_economic_calendar(self, currency_pair: str = None, days_ahead: int = 3) -> Dict:
        """获取综合经济日历（Alpha Vantage新闻 + 经济数据发布）"""
        try:
            # 获取Alpha Vantage新闻数据
            news_data = self.get_forex_specific_news(currency_pair)
            
            # 获取经济事件日程
            events_schedule = self.get_economic_events_schedule(days_ahead=days_ahead)
            
            # 使用OpenAI进行深度分析
            analysis_result = self.analyze_economic_calendar_with_openai(
                news_data, events_schedule, currency_pair
            )
            
            return {
                'currency_pair': currency_pair,
                'timeframe': f'next_{days_ahead}_days',
                'news_summary': {
                    'total_articles': news_data.get('total_articles', 0),
                    'high_impact_news': news_data.get('high_impact_count', 0),
                    'overall_sentiment': news_data.get('overall_sentiment', {}),
                    'bullish_count': news_data.get('bullish_count', 0),
                    'bearish_count': news_data.get('bearish_count', 0)
                },
                'economic_events': {
                    'total_events': events_schedule.get('total_events', 0),
                    'high_impact_events': events_schedule.get('high_impact_events', 0),
                    'source': events_schedule.get('source', 'unknown')
                },
                'integrated_analysis': analysis_result,
                'trading_recommendations': self._generate_trading_recommendations(
                    news_data, events_schedule, currency_pair
                ),
                'key_events_timeline': self._extract_events_timeline(events_schedule),
                'market_sentiment_analysis': self._analyze_market_sentiment(news_data)
            }
            
        except Exception as e:
            return {"error": f"获取综合经济日历失败: {str(e)}"}

    def analyze_economic_calendar_with_openai(self, news_data: Dict, events_data: Dict, currency_pair: str = None) -> Dict:
        """使用OpenAI深度分析经济日历"""
        if not self.openai_api_key:
            return self._get_simplified_analysis(news_data, events_data, currency_pair)
        
        if 'error' in news_data or 'error' in events_data:
            return {"error": "数据获取失败"}

        try:
            prompt = self._build_enhanced_economic_calendar_prompt(news_data, events_data, currency_pair)
            
            client = openai.OpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url if self.openai_base_url else None
            )
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """你是一个资深的外汇交易策略师和风险管理专家。基于提供的市场新闻、情绪数据和经济事件日程，提供专业的交易分析和具体的风险管理建议。重点关注：
                        1. 市场情绪与基本面数据的协同性
                        2. 高影响事件的时间安排和预期影响
                        3. 具体的入场/出场策略和仓位管理
                        4. 风险控制措施"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.3,
                timeout=30
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            return {
                'currency_pair': currency_pair,
                'analysis': analysis_text,
                'key_events_timeline': self._extract_events_timeline(events_data),
                'risk_assessment': self._assess_calendar_risk(news_data, events_data),
                'sentiment_analysis': news_data.get('overall_sentiment', {}),
                'status': 'openai_analysis'
            }
            
        except Exception as e:
            print(f"OpenAI深度分析失败: {str(e)}")
            return self._get_simplified_analysis(news_data, events_data, currency_pair)

    def _build_enhanced_economic_calendar_prompt(self, news_data: Dict, events_data: Dict, currency_pair: str) -> str:
        """构建增强版经济日历分析提示词"""
        
        prompt_parts = [
            f"请分析以下外汇市场信息，为{currency_pair if currency_pair else '主要货币对'}提供专业的交易策略：",
            "",
            "=== 市场情绪分析 ==="
        ]
        
        # 添加市场情绪数据
        sentiment = news_data.get('overall_sentiment', {})
        prompt_parts.append(f"整体市场情绪: {sentiment.get('label', 'unknown')} (强度: {sentiment.get('strength', 'unknown')})")
        prompt_parts.append(f"情绪分数: {sentiment.get('score', 0)}")
        prompt_parts.append(f"看涨文章: {news_data.get('bullish_count', 0)}篇")
        prompt_parts.append(f"看跌文章: {news_data.get('bearish_count', 0)}篇")
        
        prompt_parts.append("")
        prompt_parts.append("=== 重要新闻摘要 ===")
        
        # 添加高影响新闻
        high_impact_news = [a for a in news_data.get('articles', []) if a.get('importance') == 'high']
        for i, article in enumerate(high_impact_news[:3], 1):
            prompt_parts.append(f"{i}. {article.get('title', '')}")
            prompt_parts.append(f"   情绪: {article.get('sentiment_label', 'neutral')} (分数: {article.get('sentiment_score', 0)})")
            prompt_parts.append(f"   影响: {article.get('trading_impact', '')}")
        
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
            "请提供详细分析：",
            "1. 市场情绪与技术面/基本面的协同性分析",
            "2. 关键交易时间窗口和催化剂事件",
            "3. 具体的入场/出场点位建议",
            "4. 仓位管理和风险控制策略",
            "5. 突发事件应对计划",
            "",
            "请用专业交易员的语言，提供具体可执行的建议。"
        ])
        
        return "\n".join(prompt_parts)

    def _analyze_market_sentiment(self, news_data: Dict) -> Dict:
        """分析市场情绪"""
        sentiment = news_data.get('overall_sentiment', {})
        high_impact_news = news_data.get('high_impact_count', 0)
        
        analysis = {
            'current_sentiment': sentiment.get('label', 'neutral'),
            'sentiment_strength': sentiment.get('strength', 'weak'),
            'sentiment_score': sentiment.get('score', 0),
            'high_impact_news_count': high_impact_news,
            'market_bias': self._determine_market_bias(sentiment, high_impact_news)
        }
        
        return analysis

    def _determine_market_bias(self, sentiment: Dict, high_impact_news: int) -> str:
        """确定市场偏向"""
        sentiment_label = sentiment.get('label', 'neutral')
        sentiment_strength = sentiment.get('strength', 'weak')
        
        if high_impact_news >= 3:
            return 'high_volatility'
        elif sentiment_label == 'bullish' and sentiment_strength == 'strong':
            return 'bullish_strong'
        elif sentiment_label == 'bearish' and sentiment_strength == 'strong':
            return 'bearish_strong'
        elif sentiment_label == 'bullish':
            return 'bullish'
        elif sentiment_label == 'bearish':
            return 'bearish'
        else:
            return 'neutral'

    # 保留其他辅助方法 (_get_simulated_news, _identify_event_type, 等)
    # ... [其他原有方法的实现]

# 使用示例
if __name__ == "__main__":
    print("🔧 Alpha Vantage经济日历系统配置检查:")
    calendar = EconomicCalendar()
    
    print(f"   Alpha Vantage API: {'✅ 已设置' if calendar.alpha_vantage_key else '❌ 未设置'}")
    print(f"   OpenAI API Key: {'✅ 已设置' if calendar.openai_api_key else '❌ 未设置'}")
    
    # 测试Alpha Vantage新闻功能
    print("\n📰 测试Alpha Vantage新闻...")
    news_data = calendar.get_alpha_vantage_news_sentiment()
    if 'error' in news_data:
        print(f"❌ 新闻获取失败: {news_data['error']}")
    else:
        sentiment = news_data.get('overall_sentiment', {})
        print(f"✅ 获取 {news_data['total_articles']} 篇新闻")
        print(f"📊 市场情绪: {sentiment.get('label', 'unknown')} (强度: {sentiment.get('strength', 'unknown')})")
        print(f"🔺 看涨: {news_data.get('bullish_count', 0)}篇")
        print(f"🔻 看跌: {news_data.get('bearish_count', 0)}篇")
    
    # 测试综合经济日历
    print("\n📅 测试综合经济日历...")
    comprehensive_calendar = calendar.get_comprehensive_economic_calendar("EUR/USD", 3)
    if 'error' in comprehensive_calendar:
        print(f"❌ 综合日历失败: {comprehensive_calendar['error']}")
    else:
        print("✅ 综合经济日历生成成功!")
        sentiment_analysis = comprehensive_calendar.get('market_sentiment_analysis', {})
        print(f"📈 市场偏向: {sentiment_analysis.get('market_bias', 'unknown')}")