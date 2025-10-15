#fx_tool.py

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Union
from config import config

class ForexDataTool:
    def __init__(self, api_key: str = None):
        """
        初始化外汇数据工具 - 使用 Twelve Data API
        
        Args:
            api_key: Twelve Data API密钥，如果为None则使用config中的配置
        """
        self.api_key = api_key or getattr(config, 'twelvedata_api_key', None)
        if not self.api_key:
            raise ValueError("未找到 Twelve Data API 密钥")
        
        self.base_url = "https://api.twelvedata.com"
        self.last_request_time = 0
        self.min_request_interval = 7.5  # Twelve Data 免费版限制：8次/分钟
        self.daily_request_count = 0
        self.max_daily_requests = 800  # 免费版每日限制
        
        # Twelve Data 外汇符号格式映射
        self.currency_symbols = {
            'EUR/USD': 'EUR/USD',
            'GBP/USD': 'GBP/USD', 
            'USD/JPY': 'USD/JPY',
            'USD/CHF': 'USD/CHF',
            'AUD/USD': 'AUD/USD',
            'USD/CAD': 'USD/CAD',
            'NZD/USD': 'NZD/USD',
            'EUR/GBP': 'EUR/GBP',
            'EUR/JPY': 'EUR/JPY',
            'GBP/JPY': 'GBP/JPY'
        }
        
        print(f"✅ Twelve Data API 工具初始化完成")
    
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """
        向 Twelve Data API 发送请求，包含速率限制
        """
        # 检查每日限制
        if self.daily_request_count >= self.max_daily_requests:
            raise Exception(f"已达到每日API调用限制 ({self.max_daily_requests}次)")
        
        # 速率限制控制
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        # 构建请求URL和参数
        url = f"{self.base_url}/{endpoint}"
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=15)
            self.last_request_time = time.time()
            self.daily_request_count += 1
            
            if response.status_code == 200:
                data = response.json()
                
                # 检查 Twelve Data API 错误
                if 'code' in data and data['code'] != 200:
                    error_msg = data.get('message', 'Unknown error')
                    if 'rate limit' in error_msg.lower():
                        print("🚫 频率限制触发，等待60秒...")
                        time.sleep(60)
                        return self._make_request(endpoint, params)  # 重试
                    else:
                        raise Exception(f"API错误: {error_msg}")
                
                return data
                
            elif response.status_code == 429:
                print("🚫 频率限制触发，等待60秒...")
                time.sleep(60)
                return self._make_request(endpoint, params)  # 重试
            else:
                raise Exception(f"HTTP错误 {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            raise Exception("请求超时，请检查网络连接")
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {str(e)}")
    
    def get_symbol(self, from_currency: str, to_currency: str) -> str:
        """
        获取 Twelve Data 格式的货币对符号
        """
        pair = f"{from_currency.upper()}/{to_currency.upper()}"
        return self.currency_symbols.get(pair, pair)
    
    def get_real_time_quote(self, from_currency: str, to_currency: str) -> Dict:
        """
        获取实时外汇报价
        """
        symbol = self.get_symbol(from_currency, to_currency)
        
        params = {
            'symbol': symbol,
            'format': 'JSON'
        }
        
        data = self._make_request('quote', params)
        
        if 'close' not in data:
            raise Exception("未找到实时报价数据")
        
        return self._parse_quote_data(data, from_currency, to_currency)
    
    def _parse_quote_data(self, quote_data: Dict, from_currency: str, to_currency: str) -> Dict:
        """
        解析报价数据
        """
        return {
            'from_currency': from_currency.upper(),
            'to_currency': to_currency.upper(),
            'exchange_rate': float(quote_data.get('close', 0)),
            'open': float(quote_data.get('open', 0)),
            'high': float(quote_data.get('high', 0)),
            'low': float(quote_data.get('low', 0)),
            'previous_close': float(quote_data.get('previous_close', 0)),
            'change': float(quote_data.get('change', 0)),
            'percent_change': float(quote_data.get('percent_change', 0)),
            'volume': int(quote_data.get('volume', 0)),
            'timestamp': quote_data.get('datetime', ''),
            'last_refreshed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'time_zone': 'UTC'
        }
    
    def get_historical_data(self, from_currency: str, to_currency: str, 
                           interval: str = '1day', output_size: int = 100) -> pd.DataFrame:
        """
        获取历史外汇数据
        
        Args:
            interval: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 1day, 1week, 1month
            output_size: 1-5000 条记录
        """
        symbol = self.get_symbol(from_currency, to_currency)
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'outputsize': min(output_size, 5000),  # Twelve Data 最大限制
            'format': 'JSON'
        }
        
        data = self._make_request('time_series', params)
        
        # 检查是否有数据
        if 'values' not in data:
            error_msg = data.get('message', '未知错误')
            raise Exception(f"获取历史数据失败: {error_msg}")
        
        return self._parse_historical_data(data['values'], from_currency, to_currency)
    
    def _parse_historical_data(self, historical_data: List[Dict], from_currency: str, to_currency: str) -> pd.DataFrame:
        """
        解析历史数据为DataFrame
        """
        records = []
        for item in historical_data:
            record = {
                'date': item.get('datetime'),
                'open': float(item.get('open', 0)),
                'high': float(item.get('high', 0)),
                'low': float(item.get('low', 0)),
                'close': float(item.get('close', 0)),
                'volume': int(item.get('volume', 0))
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        df['symbol'] = f"{from_currency.upper()}/{to_currency.upper()}"
        
        return df
    
    def get_currency_intraday(self, from_currency: str, to_currency: str, 
                             interval: str = '5min', hours: int = 24) -> pd.DataFrame:
        """
        获取日内数据
        
        Args:
            interval: 1min, 5min, 15min, 30min, 45min, 1h
            hours: 获取多少小时的数据
        """
        # 计算需要的数据点数
        intervals_per_hour = {
            '1min': 60, '5min': 12, '15min': 4, '30min': 2, '45min': 1.33, '1h': 1
        }
        
        output_size = int(hours * intervals_per_hour.get(interval, 1))
        output_size = min(output_size, 5000)  # API限制
        
        return self.get_historical_data(from_currency, to_currency, interval, output_size)
    
    def get_available_currencies(self) -> List[str]:
        """
        获取可用的货币对列表
        """
        try:
            params = {
                'type': 'physical currency',
                'format': 'JSON'
            }
            
            data = self._make_request('forex_pairs', params)
            
            if 'data' in data:
                return [item['symbol'] for item in data['data']]
            else:
                return list(self.currency_symbols.keys())
                
        except Exception as e:
            print(f"获取货币对列表失败: {e}")
            return list(self.currency_symbols.keys())
    
    def get_multiple_quotes(self, pairs: List[str]) -> Dict[str, Dict]:
        """
        批量获取多个货币对的实时报价
        """
        symbols = [self.get_symbol(*pair.split('/')) for pair in pairs]
        symbol_string = ','.join(symbols)
        
        params = {
            'symbol': symbol_string,
            'format': 'JSON'
        }
        
        data = self._make_request('quote', params)
        
        quotes = {}
        for pair, symbol in zip(pairs, symbols):
            if symbol in data:
                from_curr, to_curr = pair.split('/')
                quotes[pair] = self._parse_quote_data(data[symbol], from_curr, to_curr)
        
        return quotes
    
    def get_usage_stats(self) -> Dict:
        """
        获取API使用统计
        """
        return {
            'daily_requests_used': self.daily_request_count,
            'daily_requests_remaining': self.max_daily_requests - self.daily_request_count,
            'last_request_time': datetime.fromtimestamp(self.last_request_time).strftime('%Y-%m-%d %H:%M:%S'),
            'requests_per_minute_limit': 8,
            'daily_limit': self.max_daily_requests
        }
    
    def save_data_to_csv(self, df: pd.DataFrame, filename: str):
        """
        保存数据到CSV文件
        """
        df.to_csv(filename, index=False)
        print(f"数据已保存到: {filename}")

# 使用示例和测试函数
def main():
    """
    主要测试函数
    """
    try:
        # 创建外汇数据工具实例
        fx_tool = ForexDataTool()
        print("Twelve Data API 密钥已成功加载")
        
        # 显示使用统计
        stats = fx_tool.get_usage_stats()
        print(f"API使用统计: {stats['daily_requests_used']}/{stats['daily_limit']} 次")
        
        # 测试实时报价
        print("\n1. 获取实时汇率...")
        quote = fx_tool.get_real_time_quote('EUR', 'USD')
        print(f"实时报价: 1 {quote['from_currency']} = {quote['exchange_rate']:.4f} {quote['to_currency']}")
        print(f"涨跌幅: {quote['percent_change']:.2f}%")
        print(f"最后更新: {quote['last_refreshed']}")
        
        # 测试历史数据
        print("\n2. 获取历史数据...")
        historical_data = fx_tool.get_historical_data('EUR', 'USD', '1day', 30)
        print(f"获取到 {len(historical_data)} 条历史数据")
        print("最近5条数据:")
        print(historical_data[['date', 'open', 'high', 'low', 'close']].tail())
        
        # 测试日内数据
        print("\n3. 获取日内数据...")
        intraday_data = fx_tool.get_currency_intraday('EUR', 'USD', '15min', 24)
        print(f"获取到 {len(intraday_data)} 条日内数据")
        
        # 测试批量报价
        print("\n4. 批量获取报价...")
        pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY']
        quotes = fx_tool.get_multiple_quotes(pairs)
        for pair, quote in quotes.items():
            print(f"   {pair}: {quote['exchange_rate']:.4f} ({quote['percent_change']:+.2f}%)")
        
        # 保存示例数据
        fx_tool.save_data_to_csv(historical_data, 'eur_usd_daily.csv')
        
        # 最终使用统计
        final_stats = fx_tool.get_usage_stats()
        print(f"\n最终使用统计: {final_stats['daily_requests_used']}/{final_stats['daily_limit']} 次")
        print("测试完成!")
        
    except Exception as e:
        print(f"错误: {str(e)}")

def quick_test():
    """
    快速测试函数
    """
    try:
        fx_tool = ForexDataTool()
        
        # 快速测试主要功能
        print("🚀 快速测试 Twelve Data API...")
        
        # 实时报价
        quote = fx_tool.get_real_time_quote('USD', 'JPY')
        print(f"✅ USD/JPY: {quote['exchange_rate']:.2f}")
        
        # 历史数据
        history = fx_tool.get_historical_data('GBP', 'USD', '1day', 10)
        print(f"✅ GBP/USD 历史数据: {len(history)} 条")
        
        # 使用统计
        stats = fx_tool.get_usage_stats()
        print(f"📊 API使用: {stats['daily_requests_used']} 次")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'quick':
        quick_test()
    else:
        main()

# # alpha vantange版本
# import requests
# import pandas as pd
# from datetime import datetime
# import time
# import os
# from typing import Dict, List, Optional, Union
# import json
# from config import config

# class ForexDataTool:
#     def __init__(self, api_key: str = None):
#         """
#         初始化外汇数据工具
        
#         Args:
#             api_key: Alpha Vantage API密钥，如果为None则使用config中的配置
#         """
#         self.api_key = api_key or config.alpha_api_key
#         if not self.api_key:
#             raise ValueError("未找到Alpha Vantage API密钥")
        
#         self.base_url = "https://www.alphavantage.co/query"
#         self.last_request_time = 0
#         self.min_request_interval = 12  # API限制
        
#     def _make_request(self, params: Dict) -> Dict:
#         """
#         向Alpha Vantage API发送请求，包含速率限制
#         """
#         # 速率限制控制
#         current_time = time.time()
#         time_since_last_request = current_time - self.last_request_time
#         if time_since_last_request < self.min_request_interval:
#             time.sleep(self.min_request_interval - time_since_last_request)
        
#         # 添加API密钥到参数中
#         params['apikey'] = self.api_key
        
#         try:
#             response = requests.get(self.base_url, params=params, timeout=10)
#             response.raise_for_status()
#             data = response.json()
            
#             # 检查API错误
#             if 'Error Message' in data:
#                 raise Exception(f"API错误: {data['Error Message']}")
#             if 'Note' in data:
#                 print(f"API提示: {data['Note']}")  # 通常是速率限制提示
#             if 'Information' in data: # 有时速率限制是这个键
#                 print(f"API信息: {data['Information']}")
            
#             self.last_request_time = time.time()
#             return data
            
#         except requests.exceptions.RequestException as e:
#             raise Exception(f"请求失败: {str(e)}")
    
#     def get_real_time_quote(self, from_currency: str, to_currency: str) -> Dict:
#         """
#         获取实时外汇报价
#         """
#         params = {
#             'function': 'CURRENCY_EXCHANGE_RATE',
#             'from_currency': from_currency.upper(),
#             'to_currency': to_currency.upper()
#         }
        
#         data = self._make_request(params)
        
#         if 'Realtime Currency Exchange Rate' not in data:
#             print("API返回的完整响应内容（可能为速率限制提示）：", data) 
#             raise Exception("未找到实时汇率数据")
        
#         return self._parse_quote_data(data['Realtime Currency Exchange Rate'])
    
#     def _parse_quote_data(self, quote_data: Dict) -> Dict:
#         """
#         解析报价数据
#         """
#         return {
#             'from_currency': quote_data.get('1. From_Currency Code'),
#             'to_currency': quote_data.get('3. To_Currency Code'),
#             'exchange_rate': float(quote_data.get('5. Exchange Rate', 0)),
#             'bid_price': float(quote_data.get('8. Bid Price', 0)),
#             'ask_price': float(quote_data.get('9. Ask Price', 0)),
#             'last_refreshed': quote_data.get('6. Last Refreshed'),
#             'time_zone': quote_data.get('7. Time Zone'),
#             'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         }
    
#     def get_historical_data(self, from_currency: str, to_currency: str, 
#                            interval: str = 'daily', output_size: str = 'compact') -> pd.DataFrame:
#         """
#         获取历史外汇数据
#         """
#         # 映射间隔参数
#         interval_map = {
#             'daily': 'FX_DAILY',
#             'weekly': 'FX_WEEKLY',
#             'monthly': 'FX_MONTHLY'
#         }
        
#         if interval not in interval_map:
#             raise ValueError("间隔必须是 'daily', 'weekly' 或 'monthly'")
        
#         params = {
#             'function': interval_map[interval],
#             'from_symbol': from_currency.upper(),
#             'to_symbol': to_currency.upper(),
#             'outputsize': output_size
#         }
        
#         data = self._make_request(params)
        
#         # 检查是否有数据
#         time_series_key = f'Time Series FX ({interval.capitalize()})'
#         if time_series_key not in data:
#             error_msg = data.get('Error Message', '未知错误')
#             raise Exception(f"获取历史数据失败: {error_msg}")
        
#         return self._parse_historical_data(data[time_series_key])
    
#     def _parse_historical_data(self, historical_data: Dict) -> pd.DataFrame:
#         """
#         解析历史数据为DataFrame
#         """
#         records = []
#         for date, values in historical_data.items():
#             record = {
#                 'date': date,
#                 'open': float(values.get('1. open', 0)),
#                 'high': float(values.get('2. high', 0)),
#                 'low': float(values.get('3. low', 0)),
#                 'close': float(values.get('4. close', 0))
#             }
#             records.append(record)
        
#         df = pd.DataFrame(records)
#         df['date'] = pd.to_datetime(df['date'])
#         df = df.sort_values('date').reset_index(drop=True)
        
#         return df
    
#     def get_currency_intraday(self, from_currency: str, to_currency: str, 
#                              interval: str = '5min') -> pd.DataFrame:
#         """
#         获取日内数据
#         """
#         valid_intervals = ['1min', '5min', '15min', '30min', '60min']
#         if interval not in valid_intervals:
#             raise ValueError(f"间隔必须是 {valid_intervals} 之一")
        
#         params = {
#             'function': 'FX_INTRADAY',
#             'from_symbol': from_currency.upper(),
#             'to_symbol': to_currency.upper(),
#             'interval': interval,
#             'outputsize': 'compact'
#         }
        
#         data = self._make_request(params)
        
#         time_series_key = f'Time Series FX ({interval})'
#         if time_series_key not in data:
#             error_msg = data.get('Error Message', '未知错误')
#             raise Exception(f"获取日内数据失败: {error_msg}")
        
#         return self._parse_historical_data(data[time_series_key])
    
#     def save_data_to_csv(self, df: pd.DataFrame, filename: str):
#         """
#         保存数据到CSV文件
#         """
#         df.to_csv(filename, index=False)
#         print(f"数据已保存到: {filename}")

# # 使用示例和测试函数
# def main():
#     """
#     主要测试函数
#     """
#     try:
#         # 创建外汇数据工具实例，会自动从.env文件读取API密钥
#         fx_tool = ForexDataTool()
#         print("API密钥已成功加载")
        
#         # 测试实时报价
#         print("获取实时汇率...")
#         quote = fx_tool.get_real_time_quote('USD', 'JPY')
#         print(f"实时报价: 1 {quote['from_currency']} = {quote['exchange_rate']} {quote['to_currency']}")
#         print(f"买入价: {quote['bid_price']}, 卖出价: {quote['ask_price']}")
#         print(f"最后更新: {quote['last_refreshed']}")
#         print()
        
#         # 测试历史数据
#         print("获取历史数据...")
#         historical_data = fx_tool.get_historical_data('EUR', 'USD', 'daily', 'compact')
#         print(f"获取到 {len(historical_data)} 条历史数据")
#         print("最近5条数据:")
#         print(historical_data.tail())
#         print()
        
#         # 保存示例数据
#         fx_tool.save_data_to_csv(historical_data, 'eur_usd_daily.csv')
#         print("测试完成!")
        
#     except Exception as e:
#         print(f"错误: {str(e)}")

# if __name__ == "__main__":
#     main()