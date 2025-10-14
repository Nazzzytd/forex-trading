import requests
import pandas as pd
from datetime import datetime
import time
import os
from typing import Dict, List, Optional, Union
import json
from config import config

class ForexDataTool:
    def __init__(self, api_key: str = None):
        """
        初始化外汇数据工具
        
        Args:
            api_key: Alpha Vantage API密钥，如果为None则使用config中的配置
        """
        self.api_key = api_key or config.alpha_api_key
        if not self.api_key:
            raise ValueError("未找到Alpha Vantage API密钥")
        
        self.base_url = "https://www.alphavantage.co/query"
        self.last_request_time = 0
        self.min_request_interval = 12  # API限制
        
    def _make_request(self, params: Dict) -> Dict:
        """
        向Alpha Vantage API发送请求，包含速率限制
        """
        # 速率限制控制
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        
        # 添加API密钥到参数中
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 检查API错误
            if 'Error Message' in data:
                raise Exception(f"API错误: {data['Error Message']}")
            if 'Note' in data:
                print(f"API提示: {data['Note']}")  # 通常是速率限制提示
            if 'Information' in data: # 有时速率限制是这个键
                print(f"API信息: {data['Information']}")
            
            self.last_request_time = time.time()
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {str(e)}")
    
    def get_real_time_quote(self, from_currency: str, to_currency: str) -> Dict:
        """
        获取实时外汇报价
        """
        params = {
            'function': 'CURRENCY_EXCHANGE_RATE',
            'from_currency': from_currency.upper(),
            'to_currency': to_currency.upper()
        }
        
        data = self._make_request(params)
        
        if 'Realtime Currency Exchange Rate' not in data:
            print("API返回的完整响应内容（可能为速率限制提示）：", data) 
            raise Exception("未找到实时汇率数据")
        
        return self._parse_quote_data(data['Realtime Currency Exchange Rate'])
    
    def _parse_quote_data(self, quote_data: Dict) -> Dict:
        """
        解析报价数据
        """
        return {
            'from_currency': quote_data.get('1. From_Currency Code'),
            'to_currency': quote_data.get('3. To_Currency Code'),
            'exchange_rate': float(quote_data.get('5. Exchange Rate', 0)),
            'bid_price': float(quote_data.get('8. Bid Price', 0)),
            'ask_price': float(quote_data.get('9. Ask Price', 0)),
            'last_refreshed': quote_data.get('6. Last Refreshed'),
            'time_zone': quote_data.get('7. Time Zone'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_historical_data(self, from_currency: str, to_currency: str, 
                           interval: str = 'daily', output_size: str = 'compact') -> pd.DataFrame:
        """
        获取历史外汇数据
        """
        # 映射间隔参数
        interval_map = {
            'daily': 'FX_DAILY',
            'weekly': 'FX_WEEKLY',
            'monthly': 'FX_MONTHLY'
        }
        
        if interval not in interval_map:
            raise ValueError("间隔必须是 'daily', 'weekly' 或 'monthly'")
        
        params = {
            'function': interval_map[interval],
            'from_symbol': from_currency.upper(),
            'to_symbol': to_currency.upper(),
            'outputsize': output_size
        }
        
        data = self._make_request(params)
        
        # 检查是否有数据
        time_series_key = f'Time Series FX ({interval.capitalize()})'
        if time_series_key not in data:
            error_msg = data.get('Error Message', '未知错误')
            raise Exception(f"获取历史数据失败: {error_msg}")
        
        return self._parse_historical_data(data[time_series_key])
    
    def _parse_historical_data(self, historical_data: Dict) -> pd.DataFrame:
        """
        解析历史数据为DataFrame
        """
        records = []
        for date, values in historical_data.items():
            record = {
                'date': date,
                'open': float(values.get('1. open', 0)),
                'high': float(values.get('2. high', 0)),
                'low': float(values.get('3. low', 0)),
                'close': float(values.get('4. close', 0))
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    
    def get_currency_intraday(self, from_currency: str, to_currency: str, 
                             interval: str = '5min') -> pd.DataFrame:
        """
        获取日内数据
        """
        valid_intervals = ['1min', '5min', '15min', '30min', '60min']
        if interval not in valid_intervals:
            raise ValueError(f"间隔必须是 {valid_intervals} 之一")
        
        params = {
            'function': 'FX_INTRADAY',
            'from_symbol': from_currency.upper(),
            'to_symbol': to_currency.upper(),
            'interval': interval,
            'outputsize': 'compact'
        }
        
        data = self._make_request(params)
        
        time_series_key = f'Time Series FX ({interval})'
        if time_series_key not in data:
            error_msg = data.get('Error Message', '未知错误')
            raise Exception(f"获取日内数据失败: {error_msg}")
        
        return self._parse_historical_data(data[time_series_key])
    
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
        # 创建外汇数据工具实例，会自动从.env文件读取API密钥
        fx_tool = ForexDataTool()
        print("API密钥已成功加载")
        
        # 测试实时报价
        print("获取实时汇率...")
        quote = fx_tool.get_real_time_quote('USD', 'JPY')
        print(f"实时报价: 1 {quote['from_currency']} = {quote['exchange_rate']} {quote['to_currency']}")
        print(f"买入价: {quote['bid_price']}, 卖出价: {quote['ask_price']}")
        print(f"最后更新: {quote['last_refreshed']}")
        print()
        
        # 测试历史数据
        print("获取历史数据...")
        historical_data = fx_tool.get_historical_data('EUR', 'USD', 'daily', 'compact')
        print(f"获取到 {len(historical_data)} 条历史数据")
        print("最近5条数据:")
        print(historical_data.tail())
        print()
        
        # 保存示例数据
        fx_tool.save_data_to_csv(historical_data, 'eur_usd_daily.csv')
        print("测试完成!")
        
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main()