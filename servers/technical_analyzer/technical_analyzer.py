import talib
import numpy as np
import pandas as pd
from typing import Dict, List, Optional,Any 
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from ultrarag.core.config_loader import ConfigLoader
    from openai import OpenAI
except ImportError:
    from ...core.config_loader import ConfigLoader
    from openai import OpenAI

class TechnicalAnalyzer:
    """
    UltraRAG 风格的技术分析工具 - 集成技术指标计算和AI分析
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化技术分析工具
        """
        if config is None:
            # 自动加载配置
            loader = ConfigLoader()
            config_path = os.path.join(os.path.dirname(__file__), "technical_analyzer_parameter.yaml")
            config = loader.load_config(config_path)
        
        self.ai_enabled = False
        self.openai_client = None
        
        # 从配置中获取 OpenAI 设置
        openai_api_key = config.get("openai_api_key")
        openai_base_url = config.get("openai_base_url", "https://api.openai.com/v1")
        
        # 技术指标配置
        self.indicators_config = {
            'rsi_period': config.get("rsi_period", 14),
            'macd_fast': config.get("macd_fast", 12),
            'macd_slow': config.get("macd_slow", 26),
            'macd_signal': config.get("macd_signal", 9),
            'bb_period': config.get("bb_period", 20),
            'bb_std': config.get("bb_std", 2),
            'stoch_k_period': config.get("stoch_k_period", 14),
            'stoch_d_period': config.get("stoch_d_period", 3),
            'ema_periods': config.get("ema_periods", [5, 10, 20, 50, 200])
        }
        
        # 初始化 OpenAI 客户端
        if openai_api_key and not openai_api_key.startswith("${"):
            try:
                self.openai_client = OpenAI(
                    api_key=openai_api_key,
                    base_url=openai_base_url
                )
                self.ai_enabled = True
                print("✅ TechnicalAnalyzer AI功能已启用")
            except Exception as e:
                print(f"❌ TechnicalAnalyzer AI初始化失败: {e}")
        else:
            print("⚠️ TechnicalAnalyzer AI功能不可用 - 请检查 OPENAI_API_KEY 配置")
        
        print(f"✅ Technical Analyzer 初始化完成")
        print(f"   AI分析: {'启用' if self.ai_enabled else '禁用'}")

    def calculate_indicators(self, data: Any, symbol: str = "UNKNOWN") -> Dict:
        """
        计算技术指标
        """
        try:
            print(f"🔧 计算技术指标: {symbol}")
            
            # 智能数据提取
            processed_data = self._extract_data_from_response(data)
            
            if processed_data is None:
                return {
                    "success": False,
                    "error": f"无法从输入数据中提取OHLC数据",
                    "symbol": symbol
                }
            
            # 转换为 DataFrame
            try:
                df = pd.DataFrame(processed_data)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"DataFrame 创建失败: {str(e)}",
                    "symbol": symbol
                }
            
            # 验证数据格式
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    "success": False,
                    "error": f"数据缺少必要列: {missing_columns}",
                    "symbol": symbol
                }
            
            # 确保日期列存在
            if 'datetime' not in df.columns and 'date' not in df.columns:
                df = df.reset_index().rename(columns={'index': 'datetime'})
                df['datetime'] = pd.to_datetime(df['datetime'])
            elif 'date' in df.columns:
                df = df.rename(columns={'date': 'datetime'})
                df['datetime'] = pd.to_datetime(df['datetime'])
            
            # 排序并重置索引
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # 确保数据类型正确
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 计算指标
            df_with_indicators = self._calculate_all_indicators(df, self.indicators_config)
            
            # 转换为字典格式返回
            result_data = df_with_indicators.to_dict('records')
            
            # 计算统计信息
            calculated_indicators = [col for col in df_with_indicators.columns 
                                if col not in ['datetime', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
            
            return {
                "success": True,
                "symbol": symbol,
                "data": result_data,
                "indicators_calculated": calculated_indicators,
                "record_count": len(result_data),
                "latest_timestamp": result_data[-1]['datetime'] if result_data else None,
                "available_indicators_count": len(calculated_indicators),
                "price_summary": {
                    "current_price": float(df_with_indicators['close'].iloc[-1]),
                    "price_change": float(df_with_indicators['close'].iloc[-1] - df_with_indicators['close'].iloc[0]),
                    "price_change_pct": float((df_with_indicators['close'].iloc[-1] - df_with_indicators['close'].iloc[0]) / df_with_indicators['close'].iloc[0] * 100)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"计算技术指标时发生错误: {str(e)}",
                "symbol": symbol
            }

    def _extract_data_from_response(self, data: Any) -> Optional[List[Dict]]:
        """从各种数据格式中提取OHLC数据"""
        
        # 如果数据是字符串，尝试解析为JSON
        if isinstance(data, str):
            try:
                import json
                parsed_data = json.loads(data)
                return self._extract_data_from_response(parsed_data)
            except json.JSONDecodeError:
                return None
        
        # 如果已经是数据列表，直接返回
        if isinstance(data, list):
            return data
        
        # 处理 data_fetcher 的完整响应
        if isinstance(data, dict):
            # 情况1: 直接包含 data 字段
            if 'data' in data and isinstance(data['data'], list):
                return data['data']
            
            # 情况2: 包含 result.data 结构
            if 'result' in data and isinstance(data['result'], dict):
                result = data['result']
                if 'data' in result and isinstance(result['data'], list):
                    return result['data']
            
            # 情况3: 响应本身就是数据字典（单个数据点）
            if all(key in data for key in ['open', 'high', 'low', 'close']):
                return [data]
        
        return None


    def generate_signals(self, data: List[Dict], symbol: str = "UNKNOWN", 
                        use_ai: bool = False) -> Dict:
        """
        生成交易信号
        """
        try:
            print(f"📈 开始生成交易信号: {symbol}, 使用AI: {use_ai}")
            
            # 先计算技术指标
            indicators_result = self.calculate_indicators(data, symbol)
            if not indicators_result["success"]:
                return indicators_result
            
            # 从结果中获取数据
            result_data = indicators_result["data"]
            if not result_data:
                return {
                    "success": False,
                    "error": "计算指标后数据为空",
                    "symbol": symbol
                }
            
            # 重新创建DataFrame用于信号生成
            df = pd.DataFrame(result_data)
            
            if df.empty or len(df) < 2:
                return {
                    "success": False,
                    "error": "数据不足，至少需要2个数据点",
                    "symbol": symbol,
                    "data_points": len(df)
                }
            
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            signals = {
                "success": True,
                "symbol": symbol,
                "timestamp": str(latest.get('datetime', pd.Timestamp.now())),
                "price": float(latest['close']),
                "rsi": self._analyze_rsi(latest),
                "macd": self._analyze_macd(latest, prev),
                "bollinger_bands": self._analyze_bollinger_bands(latest),
                "stochastic": self._analyze_stochastic(latest),
                "moving_averages": self._analyze_moving_averages(latest, df),
                "trend": self._analyze_trend(df),
                "volatility": self._analyze_volatility(latest)
            }
            
            # 生成综合信号
            signals["composite_signal"] = self._generate_composite_signal(signals)
            
            # AI分析
            if use_ai and self.ai_enabled:
                print("🤖 开始AI分析...")
                signals["ai_analysis"] = self._generate_ai_analysis(signals, df)
            elif use_ai and not self.ai_enabled:
                signals["ai_analysis"] = {"warning": "AI分析功能不可用"}
            
            return signals
            
        except Exception as e:
            return {
                "success": False,
                "error": f"生成交易信号时发生错误: {str(e)}",
                "symbol": symbol
            }

    def health_check(self) -> Dict:
        """健康检查"""
        try:
            # 创建测试数据
            test_data = [
                {
                    'datetime': '2024-01-01',
                    'open': 1.1000, 'high': 1.1050, 
                    'low': 1.0950, 'close': 1.1020, 'volume': 1000
                },
                {
                    'datetime': '2024-01-02', 
                    'open': 1.1020, 'high': 1.1080,
                    'low': 1.0980, 'close': 1.1050, 'volume': 1200
                },
                {
                    'datetime': '2024-01-03',
                    'open': 1.1050, 'high': 1.1120,
                    'low': 1.1020, 'close': 1.1080, 'volume': 1500
                }
            ]
            
            # 测试指标计算
            test_result = self.calculate_indicators(test_data, "TEST")
            
            return {
                "success": True,
                "status": "healthy" if test_result["success"] else "degraded",
                "ai_enabled": self.ai_enabled,
                "indicators_working": test_result["success"],
                "test_symbol": "TEST",
                "calculated_indicators": test_result.get("available_indicators_count", 0),
                "error": test_result.get("error") if not test_result["success"] else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e),
                "ai_enabled": self.ai_enabled
            }

    def get_analysis_config(self) -> Dict:
        """获取当前分析配置"""
        return {
            "success": True,
            "indicators_config": self.indicators_config,
            "ai_enabled": self.ai_enabled,
            "available_indicators": [
                "RSI", "MACD", "Bollinger Bands", "Stochastic", 
                "Moving Averages", "ATR", "Trend Analysis"
            ]
        }

    # 以下技术指标计算方法保持不变...
    def _calculate_all_indicators(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """计算所有技术指标"""
        try:
            df = self._calculate_momentum_indicators(df, config)
            df = self._calculate_trend_indicators(df, config)
            df = self._calculate_volatility_indicators(df, config)
            return df
        except Exception as e:
            print(f"❌ 计算技术指标时出错: {e}")
            return df

    def _calculate_momentum_indicators(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """计算动量指标"""
        try:
            highs = df['high'].values.astype(float)
            lows = df['low'].values.astype(float)
            closes = df['close'].values.astype(float)
            
            # RSI
            if len(closes) >= config['rsi_period']:
                df['RSI'] = talib.RSI(closes, timeperiod=config['rsi_period'])
            
            # 随机指标
            if len(closes) >= config['stoch_k_period']:
                stoch_k, stoch_d = talib.STOCH(highs, lows, closes,
                                             fastk_period=config['stoch_k_period'],
                                             slowk_period=config['stoch_d_period'],
                                             slowd_period=config['stoch_d_period'])
                df['Stoch_K'] = stoch_k
                df['Stoch_D'] = stoch_d
            
            return df
        except Exception as e:
            print(f"❌ 计算动量指标时出错: {e}")
            return df

    def _calculate_trend_indicators(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """计算趋势指标"""
        try:
            closes = df['close'].values.astype(float)
            
            # MACD
            if len(closes) >= config['macd_slow']:
                macd, macd_signal, macd_hist = talib.MACD(closes,
                                                        fastperiod=config['macd_fast'],
                                                        slowperiod=config['macd_slow'],
                                                        signalperiod=config['macd_signal'])
                df['MACD'] = macd
                df['MACD_Signal'] = macd_signal
                df['MACD_Histogram'] = macd_hist
            
            # 移动平均线
            for period in config['ema_periods']:
                if len(closes) >= period:
                    df[f'EMA_{period}'] = talib.EMA(closes, timeperiod=period)
            
            return df
        except Exception as e:
            print(f"❌ 计算趋势指标时出错: {e}")
            return df

    def _calculate_volatility_indicators(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """计算波动率指标"""
        try:
            highs = df['high'].values.astype(float)
            lows = df['low'].values.astype(float)
            closes = df['close'].values.astype(float)
            
            # 布林带
            if len(closes) >= config['bb_period']:
                upper, middle, lower = talib.BBANDS(closes,
                                                  timeperiod=config['bb_period'],
                                                  nbdevup=config['bb_std'],
                                                  nbdevdn=config['bb_std'])
                df['BB_Upper'] = upper
                df['BB_Middle'] = middle
                df['BB_Lower'] = lower
                df['BB_Width'] = (upper - lower) / middle
                df['BB_Position'] = (closes - lower) / (upper - lower)
            
            # ATR
            if len(closes) >= 14:
                df['ATR'] = talib.ATR(highs, lows, closes, timeperiod=14)
            
            return df
        except Exception as e:
            print(f"❌ 计算波动率指标时出错: {e}")
            return df

    # 以下信号分析方法保持不变...
    def _analyze_rsi(self, data: pd.Series) -> Dict:
        rsi = data.get('RSI', np.nan)
        if np.isnan(rsi):
            return {"value": None, "signal": "无数据", "strength": 0}
        
        analysis = {"value": round(rsi, 2), "signal": "中性", "strength": 0}
        
        if rsi > 70:
            analysis.update({"signal": "超买", "strength": min(100, (rsi - 70) / 30 * 100)})
        elif rsi < 30:
            analysis.update({"signal": "超卖", "strength": min(100, (30 - rsi) / 30 * 100)})
        elif rsi > 55:
            analysis.update({"signal": "偏多", "strength": (rsi - 50) / 20 * 50})
        elif rsi < 45:
            analysis.update({"signal": "偏空", "strength": (50 - rsi) / 20 * 50})
            
        return analysis

    def _analyze_macd(self, current: pd.Series, previous: pd.Series) -> Dict:
        macd = current.get('MACD', np.nan)
        signal = current.get('MACD_Signal', np.nan)
        
        if np.isnan(macd) or np.isnan(signal):
            return {"signal": "无数据", "crossover": False}
        
        prev_macd = previous.get('MACD', np.nan)
        prev_signal = previous.get('MACD_Signal', np.nan)
        
        golden_cross = (prev_macd <= prev_signal and macd > signal)
        death_cross = (prev_macd >= prev_signal and macd < signal)
        
        return {
            "signal": "看涨" if macd > signal else "看跌",
            "crossover": golden_cross or death_cross,
            "crossover_type": "金叉" if golden_cross else "死叉" if death_cross else "无"
        }

    def _analyze_bollinger_bands(self, data: pd.Series) -> Dict:
        price = data.get('close', np.nan)
        upper = data.get('BB_Upper', np.nan)
        position = data.get('BB_Position', np.nan)
        
        if np.isnan(price) or np.isnan(upper):
            return {"signal": "无数据", "squeeze": False}
        
        is_squeeze = data.get('BB_Width', np.nan) < 0.05
        
        signal = "中性"
        if price >= upper:
            signal = "超买/上轨阻力"
        elif price <= data.get('BB_Lower', np.nan):
            signal = "超卖/下轨支撑"
        elif position > 0.7:
            signal = "接近上轨"
        elif position < 0.3:
            signal = "接近下轨"
            
        return {
            "signal": signal,
            "squeeze": is_squeeze,
            "position": round(position, 3)
        }

    def _analyze_stochastic(self, data: pd.Series) -> Dict:
        k = data.get('Stoch_K', np.nan)
        d = data.get('Stoch_D', np.nan)
        
        if np.isnan(k) or np.isnan(d):
            return {"signal": "无数据", "k": None, "d": None}
        
        signal = "中性"
        if k > 80 and d > 80:
            signal = "超买"
        elif k < 20 and d < 20:
            signal = "超卖"
        elif k > d:
            signal = "看涨"
        elif k < d:
            signal = "看跌"
            
        return {
            "signal": signal,
            "k": round(k, 2),
            "d": round(d, 2)
        }

    def _analyze_moving_averages(self, data: pd.Series, df: pd.DataFrame) -> Dict:
        ema_5 = data.get('EMA_5', np.nan)
        ema_20 = data.get('EMA_20', np.nan)
        ema_50 = data.get('EMA_50', np.nan)
        
        if np.isnan(ema_5) or np.isnan(ema_20):
            return {"signal": "无数据", "trend": "未知"}
        
        if ema_5 > ema_20 and ema_20 > ema_50:
            trend = "强烈上涨"
            strength = "强"
        elif ema_5 > ema_20:
            trend = "上涨"
            strength = "中等"
        elif ema_5 < ema_20 and ema_20 < ema_50:
            trend = "强烈下跌"
            strength = "强"
        elif ema_5 < ema_20:
            trend = "下跌"
            strength = "中等"
        else:
            trend = "震荡"
            strength = "弱"
            
        return {
            "signal": trend,
            "strength": strength,
            "alignment": "多头排列" if ema_5 > ema_20 > ema_50 else 
                        "空头排列" if ema_5 < ema_20 < ema_50 else "混合排列"
        }

    def _analyze_trend(self, df: pd.DataFrame) -> Dict:
        if len(df) < 20:
            return {"direction": "未知", "strength": 0}
        
        x = np.arange(len(df))
        y = df['close'].values.astype(float)
        slope = np.polyfit(x, y, 1)[0]
        
        price_range = df['close'].max() - df['close'].min()
        strength = 0 if price_range == 0 else min(100, abs(slope) * len(df) / price_range * 100)
        
        return {
            "direction": "上涨" if slope > 0 else "下跌" if slope < 0 else "横盘",
            "strength": round(strength, 1)
        }

    def _analyze_volatility(self, data: pd.Series) -> Dict:
        atr = data.get('ATR', np.nan)
        
        volatility = "未知"
        if not np.isnan(atr):
            if atr > 0.02:
                volatility = "高波动"
            elif atr < 0.005:
                volatility = "低波动"
            else:
                volatility = "中等波动"
        
        return {
            "level": volatility,
            "atr": round(atr, 5) if not np.isnan(atr) else None
        }

    def _generate_composite_signal(self, signals: Dict) -> Dict:
        bullish_signals = 0
        bearish_signals = 0
        
        # RSI信号
        rsi_signal = signals['rsi']['signal']
        if rsi_signal in ['超卖', '偏多']:
            bullish_signals += 1
        elif rsi_signal in ['超买', '偏空']:
            bearish_signals += 1
        
        # MACD信号
        macd_signal = signals['macd']['signal']
        if macd_signal == '看涨':
            bullish_signals += 1
        elif macd_signal == '看跌':
            bearish_signals += 1
        
        # 布林带信号
        bb_signal = signals['bollinger_bands']['signal']
        if '超卖' in bb_signal or '下轨' in bb_signal:
            bullish_signals += 1
        elif '超买' in bb_signal or '上轨' in bb_signal:
            bearish_signals += 1
        
        # 趋势信号
        trend = signals['moving_averages']['signal']
        if '上涨' in trend:
            bullish_signals += 1
        elif '下跌' in trend:
            bearish_signals += 1
        
        total_signals = bullish_signals + bearish_signals
        if total_signals == 0:
            confidence = 0
            recommendation = "无明确信号"
        else:
            confidence = abs(bullish_signals - bearish_signals) / total_signals * 100
            recommendation = "买入" if bullish_signals > bearish_signals else "卖出" if bearish_signals > bullish_signals else "观望"
        
        return {
            "recommendation": recommendation,
            "confidence": round(confidence, 1),
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals
        }

    def _generate_ai_analysis(self, signals: Dict, df: pd.DataFrame) -> Dict:
        try:
            technical_context = self._create_detailed_technical_context(signals, df)
            
            prompt = f"""
            你是一个资深的外汇交易分析师。请基于以下详细的技术分析数据，提供专业的交易分析：

            {technical_context}

            请从以下角度提供详细分析：
            
            1. **当前市场状态评估**
            - 整体趋势方向和强度
            - 市场动量状况
            - 波动性水平评估
            
            2. **关键技术指标分析**
            - RSI指标的当前状态和超买超卖情况
            - MACD的金叉死叉信号和趋势确认
            - 布林带的位置和挤压状态
            - 移动平均线的排列方式
            
            3. **多时间框架协同分析**
            - 各指标之间的协同性
            - 是否存在背离现象
            - 指标信号的强度一致性
            
            4. **关键价位识别**
            - 重要支撑位和阻力位
            - 突破关键价位的可能性
            - 潜在的入场点和出场点
            
            5. **交易机会评估**
            - 当前是否存在明确的交易机会
            - 机会的质量和风险回报比
            - 适合的交易策略（趋势跟踪、反转等）
            
            6. **风险管理建议**
            - 建议的止损位置
            - 合理的目标价位
            - 仓位管理建议
            
            7. **市场情绪和风险提示**
            - 当前市场情绪分析
            - 需要关注的风险因素
            - 重要的经济事件提醒

            请用专业、客观的语言，提供具体的数据支持和逻辑推理，避免模糊表述。
            分析要具体、可操作，包含具体的价格点位建议。
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """你是一位经验丰富的外汇交易分析师，擅长技术分析和风险管理。
                    你的分析应该：
                    - 基于具体数据，避免空泛描述
                    - 提供明确的交易建议和具体价位
                    - 考虑风险管理和资金保护
                    - 分析要逻辑清晰，有理有据"""},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,  # 增加token数量以获得更详细的分析
                temperature=0.3
            )
            
            return {
                "analysis": response.choices[0].message.content,
                "timestamp": str(pd.Timestamp.now()),
                "analysis_type": "comprehensive_technical_analysis"
            }
            
        except Exception as e:
            return {"error": f"AI分析失败: {str(e)}"}

    def _create_detailed_technical_context(self, signals: Dict, df: pd.DataFrame) -> str:
        context = []
        
        # 基础信息
        symbol = signals.get('symbol', '未知')
        context.append(f"=== {symbol} 技术分析报告 ===")
        context.append(f"分析时间: {signals.get('timestamp', '未知')}")
        context.append(f"当前价格: {signals.get('price', 0):.5f}")
        context.append("")
        
        # 数据统计
        if not df.empty:
            price_change = df['close'].iloc[-1] - df['close'].iloc[0]
            price_change_pct = (price_change / df['close'].iloc[0]) * 100
            highest_high = df['high'].max()
            lowest_low = df['low'].min()
            avg_volume = df['volume'].mean() if 'volume' in df.columns else 0
            
            context.append("📈 价格统计:")
            context.append(f"  分析周期: {len(df)} 个交易日")
            context.append(f"  价格变化: {price_change:.4f} ({price_change_pct:+.2f}%)")
            context.append(f"  期间最高: {highest_high:.5f}")
            context.append(f"  期间最低: {lowest_low:.5f}")
            if avg_volume > 0:
                context.append(f"  平均交易量: {avg_volume:,.0f}")
            context.append("")
        
        # 详细技术指标
        context.append("🔍 技术指标详情:")
        
        # RSI分析
        rsi = signals.get('rsi', {})
        context.append(f"  RSI: {rsi.get('value', 'N/A')} - 信号: {rsi.get('signal', '未知')}")
        
        # MACD分析
        macd = signals.get('macd', {})
        context.append(f"  MACD: {macd.get('signal', '未知')} - 交叉类型: {macd.get('crossover_type', '无')}")
        
        # 布林带分析
        bb = signals.get('bollinger_bands', {})
        context.append(f"  布林带: {bb.get('signal', '未知')} - 位置: {bb.get('position', 0):.3f}")
        if bb.get('squeeze'):
            context.append("  * 布林带收缩 - 预期波动加大")
        
        # 趋势分析
        trend = signals.get('trend', {})
        context.append(f"  趋势方向: {trend.get('direction', '未知')} - 强度: {trend.get('strength', 0)}%")
        
        # 移动平均线
        ma = signals.get('moving_averages', {})
        context.append(f"  均线排列: {ma.get('alignment', '未知')} - 强度: {ma.get('strength', '未知')}")
        
        # 波动率分析
        volatility = signals.get('volatility', {})
        context.append(f"  波动率: {volatility.get('level', '未知')} - ATR: {volatility.get('atr', 'N/A')}")
        
        # 综合信号
        composite = signals.get('composite_signal', {})
        context.append("")
        context.append("🎯 综合交易信号:")
        context.append(f"  建议: {composite.get('recommendation', '未知')}")
        context.append(f"  置信度: {composite.get('confidence', 0)}%")
        context.append(f"  看涨信号数: {composite.get('bullish_signals', 0)}")
        context.append(f"  看跌信号数: {composite.get('bearish_signals', 0)}")
        
        # 添加价格水平信息
        if not df.empty:
            context.append("")
            context.append("💰 关键价格水平:")
            context.append(f"  当前价格: {df['close'].iloc[-1]:.5f}")
            context.append(f"  近期高点: {df['high'].tail(10).max():.5f}")
            context.append(f"  近期低点: {df['low'].tail(10).min():.5f}")
            context.append(f"  20周期均价: {df['close'].tail(20).mean():.5f}")
        
        return "\n".join(context)