# technical_analyzer.py
import talib
import numpy as np
import pandas as pd
from typing import Dict

class TechnicalAnalyzer:
    """
    技术分析工具类 - 只进行技术指标计算
    """
    
    def __init__(self):
        pass
    
    def calculate_indicators(self, df: pd.DataFrame, indicators_config: Dict = None) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            df: 包含OHLC数据的DataFrame
            indicators_config: 指标配置字典
            
        Returns:
            添加了技术指标的DataFrame
        """
        if df.empty:
            return df
        
        # 验证数据格式
        required_columns = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"数据必须包含以下列: {required_columns}")
            
        df = df.sort_values('date').reset_index(drop=True)
        config = indicators_config or self._get_default_config()
        
        # 计算指标
        df = self._calculate_all_indicators(df, config)
        
        return df
    
    def _get_default_config(self) -> Dict:
        """获取默认指标配置"""
        return {
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2,
            'stoch_k_period': 14,
            'stoch_d_period': 3,
            'ema_periods': [5, 10, 20, 50, 200]
        }
    
    def _calculate_all_indicators(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """计算所有技术指标"""
        df = self._calculate_momentum_indicators(df, config)
        df = self._calculate_trend_indicators(df, config)
        df = self._calculate_volatility_indicators(df, config)
        return df
    
    def _calculate_momentum_indicators(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """计算动量指标"""
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
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
    
    def _calculate_trend_indicators(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """计算趋势指标"""
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
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
    
    def _calculate_volatility_indicators(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """计算波动率指标"""
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
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
    
    def generate_signals(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        生成交易信号
        
        Returns:
            包含各种指标信号的字典
        """
        if df.empty:
            return {"error": "数据为空"}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        signals = {
            'timestamp': latest.get('date', pd.Timestamp.now()),
            'price': latest['close'],
            'rsi': self._analyze_rsi(latest),
            'macd': self._analyze_macd(latest, prev),
            'bollinger_bands': self._analyze_bollinger_bands(latest),
            'stochastic': self._analyze_stochastic(latest),
            'moving_averages': self._analyze_moving_averages(latest, df),
            'trend': self._analyze_trend(df),
            'volatility': self._analyze_volatility(latest)
        }
        
        # 生成综合信号
        signals['composite_signal'] = self._generate_composite_signal(signals)
        
        return signals
    
    def _analyze_rsi(self, data: pd.Series) -> Dict:
        """分析RSI信号"""
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
        """分析MACD信号"""
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
        """分析布林带信号"""
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
        """分析随机指标"""
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
        """分析移动平均线"""
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
        """分析趋势"""
        if len(df) < 20:
            return {"direction": "未知", "strength": 0}
        
        x = np.arange(len(df))
        y = df['close'].values
        slope = np.polyfit(x, y, 1)[0]
        
        price_range = df['close'].max() - df['close'].min()
        strength = 0 if price_range == 0 else min(100, abs(slope) * len(df) / price_range * 100)
        
        return {
            "direction": "上涨" if slope > 0 else "下跌" if slope < 0 else "横盘",
            "strength": round(strength, 1)
        }
    
    def _analyze_volatility(self, data: pd.Series) -> Dict:
        """分析波动率"""
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
        """生成综合交易信号"""
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