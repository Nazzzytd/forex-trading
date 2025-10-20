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
    UltraRAG 经济日历工具 - 使用Alpha Vantage获取外汇新闻和重要经济数据发布信息，并利用OpenAI进行分析
    """

    def __init__(self, config: Dict = None):
        if config is None:
            # 自动加载配置
            try:
                loader = ConfigLoader()
                config_path = os.path.join(os.path.dirname(__file__), "economic_calendar_parameter.yaml")
                config = loader.load_config(config_path)
            except Exception as e:
                print(f"⚠️ 配置文件加载失败: {e}")
                config = {}
        
        # 统一使用 alpha_api_key
        self.alpha_vantage_key = config.get("alpha_api_key")
        
        # 如果配置中没有找到，直接从环境变量获取
        if not self.alpha_vantage_key or self.alpha_vantage_key.startswith("${"):
            self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
            print("🔧 从环境变量直接获取 Alpha Vantage API 密钥")
        
        self.openai_api_key = config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        self.openai_base_url = config.get("openai_base_url") or os.getenv("OPENAI_BASE_URL")
        
        print(f"🔧 最终配置:")
        print(f"   Alpha Vantage Key: {'✅ 已设置' if self.alpha_vantage_key else '❌ 未设置'}")
        print(f"   OpenAI Key: {'✅ 已设置' if self.openai_api_key else '❌ 未设置'}")
        
        # 测试模式检测
        self.test_mode = (self.alpha_vantage_key == "TEST_MODE" or 
                         not self.alpha_vantage_key or 
                         self.alpha_vantage_key.startswith("${"))
        
        if self.test_mode:
            print("🔧 运行在测试模式，将使用模拟数据")
        
        # API使用统计和限制
        self.api_call_count = 0
        self.last_api_call_time = None
        self.daily_limit = 25  # Alpha Vantage 免费版限制
        
        # 缓存机制
        self.news_cache = {}
        self.events_cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        # 配置OpenAI客户端
        if self.openai_api_key and not self.openai_api_key.startswith("${"):
            try:
                self.openai_client = openai.OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url
                )
                print("✅ EconomicCalendar OpenAI功能已启用")
            except Exception as e:
                print(f"❌ EconomicCalendar OpenAI初始化失败: {e}")
                self.openai_client = None
        else:
            print("⚠️ EconomicCalendar OpenAI功能不可用 - 请检查 OPENAI_API_KEY 配置")
            self.openai_client = None
        
        # Alpha Vantage相关配置
        self.alpha_vantage_base_url = "https://www.alphavantage.co/query"
        
        # 外汇相关主题
        self.forex_topics = "economy_monetary,financial_markets"
        
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
                    'av_ticker': 'NFP'
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
                'monetary policy', 'central bank', 'rate hike', 'rate cut', 'fomc'
            ],
            'inflation_data': [
                'cpi', 'consumer price index', 'inflation data', 'core cpi',
                'pce price index', 'inflation report', 'price pressure', 'inflation rate'
            ],
            'employment_data': [
                'nonfarm payrolls', 'nfp', 'unemployment rate', 'jobless claims',
                'employment change', 'adp employment', 'wage growth', 'jobs report',
                'employment report'
            ],
            'gdp_growth': [
                'gdp growth', 'gross domestic product', 'economic growth',
                'preliminary gdp', 'final gdp', 'recession', 'expansion', 'gdp report'
            ]
        }

        print(f"✅ Economic Calendar 初始化完成")
        print(f"   Alpha Vantage: {'✅ 启用' if self.alpha_vantage_key and not self.test_mode else '❌ 禁用/测试模式'}")
        print(f"   OpenAI分析: {'✅ 启用' if self.openai_client else '❌ 禁用'}")
        print(f"   每日API限制: {self.daily_limit} 次调用")
        print(f"   缓存TTL: {self.cache_ttl} 秒")

    def get_news_sentiment(self, topics: str = None, tickers: str = None, limit: int = 50) -> Dict:
        """
        使用Alpha Vantage获取市场新闻和情绪数据
        """
        if not self.alpha_vantage_key:
            return {
                "success": False,
                "error": "Alpha Vantage API密钥未配置",
                "source": "economic_calendar"
            }
        
        # 测试模式直接返回模拟数据
        if self.test_mode:
            print("🔧 测试模式：返回模拟新闻数据")
            return self._get_simulated_news()
        
        # 检查API限制
        if self._is_api_limit_reached():
            print("⚠️ API调用限制已到达，使用模拟数据")
            return self._get_simulated_news()
        
        # 生成缓存键
        cache_key = f"news_{topics}_{tickers}_{limit}"
        if cache_key in self.news_cache:
            cache_time, cached_data = self.news_cache[cache_key]
            if (datetime.now() - cache_time).seconds < self.cache_ttl:
                print("🔍 使用缓存的新闻数据")
                cached_data["source"] = "cached_data"
                return cached_data
        
        try:
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.alpha_vantage_key,
                'sort': 'LATEST',
                'limit': min(limit, 50)
            }
            
            if topics:
                # 支持多个 topics 用逗号分隔
                topic_list = [t.strip() for t in topics.split(',')]
                valid_topics = []
                
                valid_alpha_topics = [
                    'blockchain', 'earnings', 'ipo', 'mergers_and_acquisitions', 
                    'financial_markets', 'economy_fiscal', 'economy_monetary', 
                    'economy_macro', 'energy_transportation', 'finance', 
                    'life_sciences', 'manufacturing', 'real_estate', 'retail_wholesale', 
                    'technology'
                ]
                
                for topic in topic_list:
                    if topic in valid_alpha_topics:
                        valid_topics.append(topic)
                
                if valid_topics:
                    params['topics'] = ",".join(valid_topics[:2])  # Alpha Vantage 限制最多2个topics
            
            if tickers:
                params['tickers'] = tickers
            
            print(f"🔍 发送新闻API请求参数: {params}")
            
            # 记录API调用
            self.api_call_count += 1
            self.last_api_call_time = datetime.now()
            print(f"📊 API调用统计: {self.api_call_count}/{self.daily_limit}")
            
            response = requests.get(self.alpha_vantage_base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查API限制信息
            if 'Information' in data:
                print(f"ℹ️ API信息: {data['Information']}")
            if 'Note' in data:
                print(f"📝 API限制提示: {data['Note']}")
            
            if 'feed' not in data:
                print("⚠️ 未找到新闻数据，使用模拟数据")
                simulated_data = self._get_simulated_news()
                # 缓存模拟数据以避免重复API调用
                self.news_cache[cache_key] = (datetime.now(), simulated_data)
                return simulated_data
            
            processed_data = self._process_news(data['feed'])
            processed_data["success"] = True
            processed_data["api_calls_remaining"] = self.daily_limit - self.api_call_count
            
            # 缓存结果
            self.news_cache[cache_key] = (datetime.now(), processed_data)
            return processed_data
            
        except Exception as e:
            print(f"Alpha Vantage新闻获取失败: {str(e)}")
            simulated_data = self._get_simulated_news()
            self.news_cache[cache_key] = (datetime.now(), simulated_data)
            return simulated_data

    def _is_api_limit_reached(self) -> bool:
        """检查是否达到API限制"""
        # 检查是否是同一天
        if self.last_api_call_time and self.last_api_call_time.date() != datetime.now().date():
            # 新的一天，重置计数器
            self.api_call_count = 0
            print("🔄 新的一天，重置API调用计数器")
            return False
        
        if self.api_call_count >= self.daily_limit:
            print(f"🚫 已达到每日API限制: {self.api_call_count}/{self.daily_limit}")
            return True
        
        return False

    def get_forex_specific_news(self, currency_pair: str = None, days_back: int = 1) -> Dict:
        """获取特定货币对相关的外汇新闻"""
        try:
            if currency_pair and currency_pair in self.currency_to_tickers:
                tickers = ",".join(self.currency_to_tickers[currency_pair])
                result = self.get_news_sentiment(
                    topics=self.forex_topics,
                    tickers=tickers,
                    limit=20
                )
            else:
                result = self.get_news_sentiment(
                    topics=self.forex_topics,
                    limit=20
                )
            
            # 确保返回结果有 success 字段
            if result and "success" not in result:
                result["success"] = True
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取外汇新闻失败: {str(e)}",
                "source": "economic_calendar"
            }

    def get_economic_events_schedule(self, days_ahead: int = 7, country: str = None) -> Dict:
        """获取经济数据发布日程"""
        try:
            # 检查缓存
            cache_key = f"events_{days_ahead}_{country}"
            if cache_key in self.events_cache:
                cache_time, cached_data = self.events_cache[cache_key]
                if (datetime.now() - cache_time).seconds < self.cache_ttl:
                    print("🔍 使用缓存的事件数据")
                    return cached_data
            
            real_events = self._get_economic_calendar(days_ahead, country)
            if real_events:
                real_events["success"] = True
                self.events_cache[cache_key] = (datetime.now(), real_events)
                return real_events
            
            events = self._get_realistic_simulated_events(days_ahead, country)
            result = {
                "success": True,
                'timestamp': datetime.now().isoformat(),
                'timeframe': f'next_{days_ahead}_days',
                'country_filter': country,
                'total_events': len(events),
                'high_impact_events': len([e for e in events if e.get('importance') == 'high']),
                'events': events,
                'source': 'simulated_data'
            }
            
            self.events_cache[cache_key] = (datetime.now(), result)
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取经济事件日程失败: {str(e)}",
                "source": "economic_calendar"
            }

    def get_comprehensive_economic_calendar(self, currency_pair: str = None, days_ahead: int = 3) -> Dict:
        """获取综合经济日历（Alpha Vantage新闻 + 经济数据发布）"""
        try:
            # 验证输入参数
            if days_ahead < 1 or days_ahead > 7:
                return {
                    "success": False,
                    "error": "days_ahead 参数必须在 1-7 范围内",
                    "source": "economic_calendar"
                }
                
            news_data = self.get_forex_specific_news(currency_pair)
            events_schedule = self.get_economic_events_schedule(days_ahead=days_ahead)
            
            # 如果新闻数据获取失败，使用模拟数据
            if not news_data.get("success"):
                print("⚠️ 新闻数据获取失败，使用模拟新闻数据")
                news_data = self._get_simulated_news()
            
            # 如果事件数据获取失败，使用模拟数据
            if not events_schedule.get("success"):
                print("⚠️ 事件数据获取失败，使用模拟事件数据")
                events_schedule = {
                    "success": True,
                    'timestamp': datetime.now().isoformat(),
                    'timeframe': f'next_{days_ahead}_days',
                    'total_events': 3,
                    'high_impact_events': 1,
                    'events': self._get_realistic_simulated_events(days_ahead),
                    'source': 'simulated_data'
                }
            
            analysis_result = self.analyze_economic_calendar_with_openai(
                news_data, events_schedule, currency_pair
            )
            
            return {
                "success": True,
                'currency_pair': currency_pair,
                'timeframe': f'next_{days_ahead}_days',
                'news_summary': {
                    'total_articles': news_data.get('total_articles', 0),
                    'high_impact_news': news_data.get('high_impact_count', 0),
                    'overall_sentiment': news_data.get('overall_sentiment', {}),
                    'bullish_count': news_data.get('bullish_count', 0),
                    'bearish_count': news_data.get('bearish_count', 0),
                    'source': news_data.get('source', 'unknown')
                },
                'economic_events': {
                    'total_events': events_schedule.get('total_events', 0),
                    'high_impact_events': events_schedule.get('high_impact_events', 0),
                    'source': events_schedule.get('source', 'unknown')
                },
                'integrated_analysis': analysis_result,
                'key_events_timeline': self._extract_events_timeline(events_schedule),
                'market_sentiment_analysis': self._analyze_market_sentiment(news_data),
                'api_usage': {
                    'calls_made': self.api_call_count,
                    'calls_remaining': self.daily_limit - self.api_call_count,
                    'test_mode': self.test_mode
                },
                'source': 'economic_calendar'
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取综合经济日历失败: {str(e)}",
                "source": "economic_calendar"
            }

    def health_check(self) -> Dict:
        """健康检查"""
        try:
            # 测试基本功能
            test_news = self.get_forex_specific_news("EUR/USD")
            test_events = self.get_economic_events_schedule(1)
            
            return {
                "success": True,
                "status": "healthy",
                "alpha_vantage_working": test_news.get("success", False) and not self.test_mode,
                "openai_working": self.openai_client is not None,
                "test_mode": self.test_mode,
                "api_usage": {
                    "calls_made": self.api_call_count,
                    "calls_remaining": self.daily_limit - self.api_call_count,
                    "daily_limit": self.daily_limit
                },
                "cache_status": {
                    "news_cache_size": len(self.news_cache),
                    "events_cache_size": len(self.events_cache)
                },
                "test_currency_pair": "EUR/USD",
                "news_articles_count": test_news.get('total_articles', 0) if test_news.get("success") else 0,
                "events_count": test_events.get('total_events', 0) if test_events.get("success") else 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e)
            }

    def get_calendar_config(self) -> Dict:
        """获取当前配置"""
        return {
            "success": True,
            "alpha_vantage_enabled": bool(self.alpha_vantage_key) and not self.test_mode,
            "openai_enabled": self.openai_client is not None,
            "test_mode": self.test_mode,
            "api_limits": {
                "daily_limit": self.daily_limit,
                "calls_made": self.api_call_count,
                "calls_remaining": self.daily_limit - self.api_call_count
            },
            "cache_settings": {
                "news_cache_ttl": self.cache_ttl,
                "news_cache_size": len(self.news_cache),
                "events_cache_size": len(self.events_cache)
            },
            "supported_currency_pairs": list(self.currency_to_tickers.keys()),
            "available_methods": [
                "get_forex_specific_news",
                "get_economic_events_schedule", 
                "get_comprehensive_economic_calendar",
                "health_check"
            ]
        }

    # 其他辅助方法保持不变...
    def _process_news(self, news_feed: List) -> Dict:
        """处理Alpha Vantage新闻数据"""
        processed_articles = []
        
        for article in news_feed[:30]:
            try:
                title = article.get('title', '')
                summary = article.get('summary', '')
                published = article.get('time_published', '')
                source = article.get('source', 'Unknown')
                url = article.get('url', '')
                
                sentiment_info = article.get('overall_sentiment_score', 0)
                sentiment_label = article.get('overall_sentiment_label', 'neutral')
                relevance_score = article.get('relevance_score', '0')
                
                ticker_sentiment = article.get('ticker_sentiment', [])
                topics = [item['topic'] for item in article.get('topics', [])]
                
                related_currencies = self._extract_currencies_from_tickers(ticker_sentiment)
                event_type = self._identify_event_type(title + " " + summary)
                importance = self._assess_news_importance(sentiment_label, event_type, title, float(relevance_score))
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
            if ticker in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']:
                currencies.add(ticker)
            elif ticker in ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']:
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
        high_impact_keywords = [
            'rate decision', 'interest rate', 'nonfarm payrolls', 'nfp', 
            'cpi', 'inflation', 'gdp', 'federal reserve', 'ecb', 'boe', 'boj'
        ]
        
        title_lower = title.lower()
        score = 0
        
        if sentiment_label in ['bullish', 'bearish']:
            score += 2
        
        if event_type in ['central_bank_decision', 'inflation_data', 'employment_data']:
            score += 2
        
        if any(keyword in title_lower for keyword in high_impact_keywords):
            score += 2
        
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

    def _get_simulated_news(self) -> Dict:
        """生成模拟新闻数据作为回退"""
        simulated_articles = [
            {
                'title': 'Federal Reserve Maintains Interest Rates Amid Stable Inflation',
                'summary': 'The Federal Reserve kept interest rates unchanged as inflation remains within target range.',
                'published_at': datetime.now().isoformat(),
                'source': 'Simulated Data',
                'url': '',
                'sentiment_score': 0.1,
                'sentiment_label': 'neutral',
                'relevance_score': '0.8',
                'related_tickers': ['USD', 'EUR'],
                'ticker_sentiment': [],
                'topics': ['central_banks', 'monetary_policy'],
                'event_type': 'central_bank_decision',
                'affected_currency_pairs': ['EUR/USD', 'GBP/USD', 'USD/JPY'],
                'importance': 'high',
                'trading_impact': '高影响事件，密切关注美联储政策',
                'volatility_expected': 'high',
                'content_preview': '美联储维持利率不变...'
            }
        ]
        
        return {
            "success": True,
            'timestamp': datetime.now().isoformat(),
            'total_articles': len(simulated_articles),
            'articles': simulated_articles,
            'overall_sentiment': {'score': 0.18, 'label': 'neutral', 'strength': 'weak'},
            'high_impact_count': 1,
            'bullish_count': 1,
            'bearish_count': 0,
            'source': 'simulated_data'
        }

    def _identify_event_type(self, content: str) -> str:
        """识别事件类型"""
        content_lower = content.lower()
        
        for event_type, keywords in self.event_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return event_type
        
        return 'other'

    def _get_economic_calendar(self, days_ahead: int, country: str = None) -> Optional[Dict]:
        """
        使用新闻情感数据来模拟经济日历
        """
        if not self.alpha_vantage_key or self.test_mode:
            print("⚠️ Alpha Vantage API密钥未配置或测试模式，使用模拟数据")
            return None
        
        try:
            # 使用 NEWS_SENTIMENT 而不是 ECONOMIC_CALENDAR
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.alpha_vantage_key,
                'topics': 'economy_monetary,economy_fiscal,economy_macro,financial_markets',
                'sort': 'LATEST',
                'limit': 20
            }
            
            # 根据国家过滤相关主题
            country_topics = {
                'us': 'federal reserve,interest rates,us economy',
                'eu': 'ecb,european central bank,eurozone',
                'uk': 'bank of england,uk economy,brexit',
                'jp': 'bank of japan,japan economy'
            }
            
            if country and country in country_topics:
                print(f"🔍 获取 {country} 相关经济新闻")
            
            print(f"🔍 发送新闻情感API请求: {params}")
            
            response = requests.get(self.alpha_vantage_base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            print(f"📊 Alpha Vantage 新闻响应键: {list(data.keys())}")
            
            # 检查API限制或错误信息
            if 'Information' in data:
                print(f"ℹ️ API信息: {data['Information']}")
                return None
            if 'Note' in data:
                print(f"📝 API限制提示: {data['Note']}")
                return None
            if 'Error Message' in data:
                print(f"❌ API错误: {data['Error Message']}")
                return None
            
            if 'feed' in data:
                # 处理新闻数据作为经济事件
                events = self._convert_news_to_economic_events(data['feed'], days_ahead)
                print(f"✅ 成功获取 {len(events)} 个经济相关事件")
                return {
                    'events': events,
                    'source': 'alpha_vantage_news'
                }
            else:
                print(f"⚠️ 未找到新闻数据，使用模拟数据")
                return None
            
        except requests.exceptions.Timeout:
            print(f"❌ Alpha Vantage 请求超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Alpha Vantage 网络请求失败: {e}")
            return None
        except Exception as e:
            print(f"❌ Alpha Vantage 新闻获取失败: {e}")
            return None

    def _convert_news_to_economic_events(self, news_feed: List, days_ahead: int) -> List[Dict]:
        """将新闻数据转换为经济事件格式"""
        events = []
        today = datetime.now()
        
        for article in news_feed[:10]:  # 只处理前10篇文章
            try:
                title = article.get('title', '')
                summary = article.get('summary', '')
                published = article.get('time_published', '')
                source = article.get('source', 'Unknown')
                
                # 识别事件类型和重要性 - 修复参数顺序
                event_type = self._identify_event_type(title + " " + summary)
                sentiment_label = article.get('overall_sentiment_label', 'neutral')
                relevance_score = float(article.get('relevance_score', 0))
                
                importance = self._assess_news_importance(
                    sentiment_label,      # 第一个参数
                    event_type,           # 第二个参数  
                    title,                # 第三个参数
                    relevance_score       # 第四个参数
                )
                
                # 提取相关货币对
                ticker_sentiment = article.get('ticker_sentiment', [])
                related_currencies = self._extract_currencies_from_tickers(ticker_sentiment)
                
                # 解析发布时间
                event_date = today
                if published:
                    try:
                        # 尝试解析 Alpha Vantage 的时间格式: 20241020T000000
                        if 'T' in published:
                            date_part = published.split('T')[0]
                            event_date = datetime.strptime(date_part, '%Y%m%d')
                    except:
                        pass
                
                events.append({
                    'event_name': title[:100],  # 限制标题长度
                    'country': self._infer_country_from_content(title + " " + summary),
                    'date': event_date.strftime('%Y-%m-%d'),
                    'time': event_date.strftime('%H:%M'),
                    'importance': importance,
                    'currency_impact': related_currencies if related_currencies else ['Multiple'],
                    'previous_value': 'N/A',
                    'forecast': 'N/A', 
                    'actual': 'N/A',
                    'source': source,
                    'description': summary[:200] + '...' if len(summary) > 200 else summary,
                    'event_type': event_type
                })
                
            except Exception as e:
                print(f"处理新闻文章时出错: {e}")
                continue
        
        return events

    def _infer_country_from_content(self, content: str) -> str:
        """从内容推断国家"""
        content_lower = content.lower()
        
        country_keywords = {
            'us': ['federal reserve', 'fed', 'us ', 'united states', 'dollar', 'wall street'],
            'eu': ['ecb', 'european central bank', 'eurozone', 'euro ', 'brussels'],
            'uk': ['bank of england', 'boe', 'uk ', 'united kingdom', 'pound', 'brexit'],
            'jp': ['bank of japan', 'boj', 'japan', 'yen', 'tokyo']
        }
        
        for country, keywords in country_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return country.upper()
        
        return 'GLOBAL'

    def _get_realistic_simulated_events(self, days_ahead: int, country: str = None) -> List[Dict]:
        """
        生成模拟经济事件数据
        """
        events = []
        today = datetime.now()
        
        for i in range(days_ahead):
            event_date = today + timedelta(days=i)
            
            # 遍历所有国家的事件模板
            for country_code, country_events in self.economic_events.items():
                # 按国家过滤
                if country and country_code != country:
                    continue
                    
                for event_template in country_events:
                    # 检查是否是典型发布日（简化逻辑）
                    if event_date.day == event_template['typical_day']:
                        events.append({
                            'event_name': event_template['name'],
                            'country': country_code.upper(),
                            'date': event_date.strftime('%Y-%m-%d'),
                            'time': event_template['typical_time'],
                            'importance': event_template['importance'],
                            'currency_impact': event_template['currency_impact'],
                            'previous_value': '待发布',
                            'forecast': '待发布',
                            'actual': '待发布',
                            'source': event_template['source']
                        })
        
        # 如果没有找到事件，添加一些默认事件
        if not events:
            default_events = [
                {
                    'event_name': 'US Federal Reserve Meeting',
                    'country': 'US',
                    'date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
                    'time': '14:00 EST',
                    'importance': 'high',
                    'currency_impact': ['USD', 'All majors'],
                    'previous_value': '5.50%',
                    'forecast': '5.50%',
                    'actual': '待发布',
                    'source': 'Federal Reserve'
                },
                {
                    'event_name': 'Eurozone CPI',
                    'country': 'EU',
                    'date': (today + timedelta(days=2)).strftime('%Y-%m-%d'),
                    'time': '10:00 GMT',
                    'importance': 'high',
                    'currency_impact': ['EUR', 'EUR/USD'],
                    'previous_value': '2.4%',
                    'forecast': '2.3%',
                    'actual': '待发布',
                    'source': 'Eurostat'
                }
            ]
            events.extend(default_events)
        
        return events

    # 其他方法保持不变...
    def analyze_economic_calendar_with_openai(self, news_data: Dict, events_data: Dict, currency_pair: str = None) -> Dict:
        """使用OpenAI深度分析经济日历"""
        if not self.openai_client:
            return self._get_simplified_analysis(news_data, events_data, currency_pair)
        
        try:
            # 验证输入数据
            if not news_data or not events_data:
                return {
                    "success": False,
                    "error": "输入数据为空",
                    "source": "economic_calendar"
                }
            
            # 确保数据是字典格式
            if isinstance(news_data, str):
                try:
                    import json
                    news_data = json.loads(news_data)
                except:
                    return {
                        "success": False,
                        "error": "新闻数据格式错误",
                        "source": "economic_calendar"
                    }
            
            if isinstance(events_data, str):
                try:
                    import json
                    events_data = json.loads(events_data)
                except:
                    return {
                        "success": False,
                        "error": "事件数据格式错误",
                        "source": "economic_calendar"
                    }
            
            prompt = self._build_enhanced_economic_calendar_prompt(news_data, events_data, currency_pair)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """你是一个资深的外汇交易策略师和风险管理专家。基于提供的市场新闻、情绪数据和经济事件日程，提供专业的交易分析和具体的风险管理建议。"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                'currency_pair': currency_pair,
                'analysis': analysis_text,
                'key_events_timeline': self._extract_events_timeline(events_data),
                'risk_assessment': self._assess_calendar_risk(news_data, events_data),
                'sentiment_analysis': news_data.get('overall_sentiment', {}),
                'status': 'openai_analysis'
            }
            
        except Exception as e:
            print(f"❌ OpenAI深度分析失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"AI分析失败: {str(e)}",
                "source": "economic_calendar"
            }

    def _build_enhanced_economic_calendar_prompt(self, news_data: Dict, events_data: Dict, currency_pair: str) -> str:
        """构建分析提示词"""
        prompt_parts = []
        
        prompt_parts.append(f"请分析以下外汇市场信息，重点关注{currency_pair if currency_pair else '主要货币对'}的交易机会：")
        prompt_parts.append("")
        
        # 新闻数据部分
        if news_data.get('success'):
            prompt_parts.append("=== 市场新闻和情绪分析 ===")
            prompt_parts.append(f"总文章数: {news_data.get('total_articles', 0)}")
            prompt_parts.append(f"高影响新闻: {news_data.get('high_impact_count', 0)}")
            
            sentiment = news_data.get('overall_sentiment', {})
            prompt_parts.append(f"整体情绪: {sentiment.get('label', 'neutral')} (强度: {sentiment.get('strength', 'weak')})")
            prompt_parts.append(f"看涨文章: {news_data.get('bullish_count', 0)}")
            prompt_parts.append(f"看跌文章: {news_data.get('bearish_count', 0)}")
            
            # 添加重要新闻标题
            important_articles = [article for article in news_data.get('articles', []) 
                                if article.get('importance') == 'high']
            if important_articles:
                prompt_parts.append("重要新闻标题:")
                for article in important_articles[:3]:
                    prompt_parts.append(f"- {article.get('title', '')}")
        else:
            prompt_parts.append("新闻数据获取失败")
        
        prompt_parts.append("")
        
        # 经济事件部分
        if events_data.get('success'):
            prompt_parts.append("=== 经济事件日程 ===")
            prompt_parts.append(f"总事件数: {events_data.get('total_events', 0)}")
            prompt_parts.append(f"高影响事件: {events_data.get('high_impact_events', 0)}")
            
            high_impact_events = [event for event in events_data.get('events', []) 
                                if event.get('importance') == 'high']
            if high_impact_events:
                prompt_parts.append("高影响事件:")
                for event in high_impact_events[:5]:
                    prompt_parts.append(f"- {event.get('event_name', '')} ({event.get('date', '')} {event.get('time', '')})")
        
        prompt_parts.append("")
        prompt_parts.append("请基于以上信息提供：")
        prompt_parts.append("1. 市场情绪分析和趋势判断")
        prompt_parts.append("2. 重要经济事件对汇率的影响预测")
        prompt_parts.append("3. 具体的交易建议和风险管理策略")
        prompt_parts.append("4. 需要重点关注的风险因素")
        
        return "\n".join(prompt_parts)

    def _extract_events_timeline(self, events_data: Dict) -> List[Dict]:
        """提取事件时间线"""
        timeline = []
        
        if events_data.get('success'):
            events = events_data.get('events', [])
            for event in events:
                timeline.append({
                    'event': event.get('event_name', ''),
                    'date': event.get('date', ''),
                    'time': event.get('time', ''),
                    'importance': event.get('importance', 'medium'),
                    'currency_impact': event.get('currency_impact', [])
                })
        
        return timeline

    def _analyze_market_sentiment(self, news_data: Dict) -> Dict:
        """分析市场情绪"""
        if not news_data.get('success'):
            return {'overall': 'unknown', 'confidence': 0}
        
        sentiment = news_data.get('overall_sentiment', {})
        bullish_count = news_data.get('bullish_count', 0)
        bearish_count = news_data.get('bearish_count', 0)
        total_articles = news_data.get('total_articles', 1)
        
        bullish_ratio = bullish_count / total_articles
        bearish_ratio = bearish_count / total_articles
        
        if bullish_ratio > 0.6:
            market_sentiment = 'strongly_bullish'
        elif bullish_ratio > 0.4:
            market_sentiment = 'bullish'
        elif bearish_ratio > 0.6:
            market_sentiment = 'strongly_bearish'
        elif bearish_ratio > 0.4:
            market_sentiment = 'bearish'
        else:
            market_sentiment = 'neutral'
        
        return {
            'overall': market_sentiment,
            'confidence': max(bullish_ratio, bearish_ratio),
            'bullish_articles': bullish_count,
            'bearish_articles': bearish_count,
            'sentiment_score': sentiment.get('score', 0)
        }

    def _get_simplified_analysis(self, news_data: Dict, events_data: Dict, currency_pair: str) -> Dict:
        """简化分析（当OpenAI不可用时使用）"""
        sentiment_analysis = self._analyze_market_sentiment(news_data)
        
        # 基于新闻情绪和事件数量生成简单分析
        if sentiment_analysis['overall'] == 'strongly_bullish':
            recommendation = "强烈看涨"
        elif sentiment_analysis['overall'] == 'bullish':
            recommendation = "看涨"
        elif sentiment_analysis['overall'] == 'strongly_bearish':
            recommendation = "强烈看跌"
        elif sentiment_analysis['overall'] == 'bearish':
            recommendation = "看跌"
        else:
            recommendation = "中性"
        
        high_impact_events = events_data.get('high_impact_events', 0)
        if high_impact_events > 0:
            recommendation += f"，注意{high_impact_events}个高影响事件"
        
        return {
            'currency_pair': currency_pair,
            'analysis': f"基于市场情绪分析，当前建议：{recommendation}。市场情绪：{sentiment_analysis['overall']}，置信度：{sentiment_analysis['confidence']:.2f}",
            'recommendation': recommendation,
            'confidence': sentiment_analysis['confidence'],
            'status': 'simplified_analysis'
        }

    def _assess_calendar_risk(self, news_data: Dict, events_data: Dict) -> Dict:
        """评估日历风险"""
        risk_level = 'low'
        reasons = []
        
        # 基于高影响新闻数量评估风险
        high_impact_news = news_data.get('high_impact_count', 0)
        if high_impact_news >= 3:
            risk_level = 'high'
            reasons.append(f"高影响新闻数量较多: {high_impact_news}")
        elif high_impact_news >= 1:
            risk_level = 'medium'
            reasons.append(f"存在高影响新闻: {high_impact_news}")
        
        # 基于高影响事件数量评估风险
        high_impact_events = events_data.get('high_impact_events', 0)
        if high_impact_events >= 2:
            risk_level = 'high'
            reasons.append(f"高影响事件数量较多: {high_impact_events}")
        elif high_impact_events >= 1 and risk_level != 'high':
            risk_level = 'medium'
            reasons.append(f"存在高影响事件: {high_impact_events}")
        
        return {
            'risk_level': risk_level,
            'reasons': reasons,
            'high_impact_news_count': high_impact_news,
            'high_impact_events_count': high_impact_events
        }