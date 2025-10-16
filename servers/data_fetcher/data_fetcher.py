import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import json
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from ultrarag.core.config_loader import ConfigLoader
except ImportError:
    from ...core.config_loader import ConfigLoader

class DataFetcher:
    def __init__(self, config: Dict = None):
        """
        UltraRAG 风格的外汇数据获取组件 - 使用真实 Twelve Data API
        """
        if config is None:
            loader = ConfigLoader()
            config_path = os.path.join(os.path.dirname(__file__), "data_fetcher_parameter.yaml")
            config = loader.load_config(config_path)
        
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("未找到 Twelve Data API 密钥")
            
        if self.api_key.startswith("${") and self.api_key.endswith("}"):
            raise ValueError(f"API 密钥未正确解析: {self.api_key}")
            
        self.base_url = "https://api.twelvedata.com"
        self.last_request_time = 0
        self.min_request_interval = config.get("min_request_interval", 7.5)
        self.daily_request_count = 0
        self.max_daily_requests = config.get("max_daily_requests", 800)
        self.default_timeframe = config.get("default_timeframe", "1h")
        self.supported_pairs = config.get("supported_pairs", [])
        self.cache_enabled = config.get("cache_enabled", True)
        self.cache_duration = config.get("cache_duration", 300)
        self._cache = {}

    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """向 Twelve Data API 发送请求，包含速率限制"""
        if self.daily_request_count >= self.max_daily_requests:
            raise Exception(f"已达到每日API调用限制 ({self.max_daily_requests}次)")
        
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        url = f"{self.base_url}/{endpoint}"
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=15)
            self.last_request_time = time.time()
            self.daily_request_count += 1
            
            if response.status_code == 200:
                data = response.json()
                
                if 'code' in data and data['code'] != 200:
                    error_msg = data.get('message', 'Unknown error')
                    if 'rate limit' in error_msg.lower():
                        time.sleep(60)
                        return self._make_request(endpoint, params)
                    else:
                        raise Exception(f"API错误: {error_msg}")
                
                return data
                
            elif response.status_code == 429:
                time.sleep(60)
                return self._make_request(endpoint, params)
            else:
                raise Exception(f"HTTP错误 {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")

    def fetch_data(self, currency_pair: str, data_type: str = "realtime", 
                  interval: str = None, output_size: int = 100) -> Dict:
        """
        获取真实的外汇数据 - 使用 Twelve Data API
        """
        if interval is None:
            interval = self.default_timeframe
            
        try:
            if data_type == "realtime":
                result = self._get_real_time_data(currency_pair)
            elif data_type == "historical":
                result = self._get_historical_data(currency_pair, interval, output_size)
            elif data_type == "intraday":
                result = self._get_intraday_data(currency_pair, interval, output_size)
            else:
                raise ValueError(f"不支持的数据类型: {data_type}")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e) if e else "未知错误",  # 确保错误信息不为空
                "currency_pair": currency_pair,
                "data_type": data_type
            }

    def _get_real_time_data(self, currency_pair: str) -> Dict:
        """获取实时报价数据"""
        params = {
            'symbol': currency_pair,
            'format': 'JSON'
        }
        
        data = self._make_request('quote', params)
        
        if 'close' not in data:
            raise Exception("未找到实时报价数据")
        
        quote_data = self._parse_quote_data(data, currency_pair)
        
        return {
            "success": True,
            "data_type": "realtime",
            "currency_pair": currency_pair,
            "data": quote_data,
            "metadata": {
                "source": "twelvedata",
                "retrieved_at": datetime.now().isoformat(),
                "api_requests_used": self.daily_request_count
            }
        }

    def _parse_quote_data(self, quote_data: Dict, currency_pair: str) -> Dict:
        """解析报价数据"""
        from_currency, to_currency = currency_pair.split('/')
        
        return {
            'from_currency': from_currency,
            'to_currency': to_currency,
            'exchange_rate': float(quote_data.get('close', 0)),
            'open': float(quote_data.get('open', 0)),
            'high': float(quote_data.get('high', 0)),
            'low': float(quote_data.get('low', 0)),
            'previous_close': float(quote_data.get('previous_close', 0)),
            'change': float(quote_data.get('change', 0)),
            'percent_change': float(quote_data.get('percent_change', 0)),
            'volume': int(quote_data.get('volume', 0)),
            'timestamp': quote_data.get('datetime', ''),
            'time_zone': quote_data.get('timezone', 'UTC')
        }

    def _get_historical_data(self, currency_pair: str, interval: str, output_size: int) -> Dict:
        """获取历史数据"""
        params = {
            'symbol': currency_pair,
            'interval': interval,
            'outputsize': min(output_size, 5000),
            'format': 'JSON'
        }
        
        data = self._make_request('time_series', params)
        
        if 'values' not in data:
            error_msg = data.get('message', '未知错误')
            raise Exception(f"获取历史数据失败: {error_msg}")
        
        df = self._parse_historical_data(data['values'], currency_pair)
        historical_data = df.to_dict('records')
        
        return {
            "success": True,
            "data_type": "historical",
            "currency_pair": currency_pair,
            "interval": interval,
            "data": historical_data,
            "summary": {
                "record_count": len(historical_data),
                "date_range": {
                    "start": historical_data[0]['datetime'] if historical_data else None,
                    "end": historical_data[-1]['datetime'] if historical_data else None
                },
                "price_stats": {
                    "close_mean": df['close'].mean(),
                    "close_std": df['close'].std(),
                    "volume_mean": df['volume'].mean() if 'volume' in df.columns else 0
                }
            },
            "metadata": {
                "source": "twelvedata",
                "retrieved_at": datetime.now().isoformat(),
                "api_requests_used": self.daily_request_count
            }
        }

    def _parse_historical_data(self, historical_data: List[Dict], currency_pair: str) -> pd.DataFrame:
        """解析历史数据为DataFrame"""
        records = []
        for item in historical_data:
            record = {
                'datetime': item.get('datetime'),
                'open': float(item.get('open', 0)),
                'high': float(item.get('high', 0)),
                'low': float(item.get('low', 0)),
                'close': float(item.get('close', 0)),
                'volume': int(item.get('volume', 0))
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
        df['symbol'] = currency_pair
        
        return df

    def _get_intraday_data(self, currency_pair: str, interval: str, output_size: int) -> Dict:
        """获取日内数据"""
        historical_result = self._get_historical_data(currency_pair, interval, output_size)
        historical_result["data_type"] = "intraday"
        return historical_result

    def batch_fetch(self, queries: List[Dict]) -> List[Dict]:
        """批量获取数据"""
        results = []
        for query in queries:
            result = self.fetch_data(**query)
            results.append(result)
        return results

    def get_usage_stats(self) -> Dict:
        """获取使用统计"""
        try:
            return {
                "success": True,
                "daily_requests_used": self.daily_request_count,
                "daily_requests_remaining": self.max_daily_requests - self.daily_request_count,
                "supported_pairs": self.supported_pairs,
                "status": "active",
                "last_request_time": datetime.fromtimestamp(self.last_request_time).strftime('%Y-%m-%d %H:%M:%S') if self.last_request_time > 0 else "从未请求"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e) if e else "获取使用统计失败"
            }

    def health_check(self) -> Dict:
        """健康检查"""
        try:
            test_result = self.fetch_data("EUR/USD", "realtime")
            api_working = test_result.get("success", False)
            
            return {
                "success": True,  # 添加 success 字段
                "status": "healthy" if api_working else "degraded",
                "api_connected": api_working,
                "api_requests_used": self.daily_request_count,
                "message": "服务正常运行" if api_working else "API 连接异常"
            }
        except Exception as e:
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e) if e else "健康检查失败",
                "api_connected": False
            }