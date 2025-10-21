# test_data_compatibility.py
from fx_tool import ForexDataTool
from technical_analyzer import TechnicalAnalyzer
import pandas as pd

def test_data_compatibility():
    """测试 Twelve Data 与 TechnicalAnalyzer 的兼容性"""
    print("🔍 测试数据兼容性...")
    
    try:
        # 1. 获取 Twelve Data 数据
        fx_tool = ForexDataTool()
        print("✅ Twelve Data 工具初始化成功")
        
        # 获取数据
        data = fx_tool.get_historical_data('EUR', 'USD', '1day', 50)
        print(f"📊 获取到 {len(data)} 条数据")
        
        # 检查数据格式
        print("\n📋 数据列信息:")
        print(f"列名: {list(data.columns)}")
        print(f"数据类型:")
        print(data.dtypes)
        print(f"\n前3行数据:")
        print(data.head(3))
        
        # 2. 测试 TechnicalAnalyzer
        analyzer = TechnicalAnalyzer()
        print("\n✅ TechnicalAnalyzer 初始化成功")
        
        # 计算技术指标
        data_with_indicators = analyzer.calculate_indicators(data)
        print(f"📈 成功计算技术指标")
        print(f"添加的指标列: {[col for col in data_with_indicators.columns if col not in data.columns]}")
        
        # 生成交易信号
        signals = analyzer.generate_signals(data_with_indicators, use_ai=False)
        print(f"🎯 成功生成交易信号")
        print(f"信号类型: {list(signals.keys())}")
        
        # 显示关键信号
        print(f"\n📊 关键交易信号:")
        print(f"价格: {signals.get('price', 'N/A')}")
        print(f"RSI: {signals['rsi']['value']} - {signals['rsi']['signal']}")
        print(f"MACD: {signals['macd']['signal']}")
        print(f"综合建议: {signals['composite_signal']['recommendation']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 兼容性测试失败: {e}")
        return False

def compare_data_formats():
    """比较新旧数据格式"""
    print("\n📊 数据格式对比分析...")
    
    # Twelve Data 的典型数据格式
    twelve_data_format = {
        'date': 'datetime64[ns]',  # 日期时间
        'open': 'float64',         # 开盘价
        'high': 'float64',         # 最高价  
        'low': 'float64',          # 最低价
        'close': 'float64',        # 收盘价
        'volume': 'int64',         # 成交量
        'symbol': 'object'         # 货币对符号
    }
    
    # TechnicalAnalyzer 期望的数据格式
    analyzer_expected_format = {
        'date': 'datetime64[ns]',  # 必须
        'open': 'float64',         # 必须
        'high': 'float64',         # 必须
        'low': 'float64',          # 必须  
        'close': 'float64',        # 必须
        'volume': 'float64'        # 可选
    }
    
    print("Twelve Data 格式:", twelve_data_format)
    print("TechnicalAnalyzer 期望格式:", analyzer_expected_format)
    
    # 检查兼容性
    required_columns = ['date', 'open', 'high', 'low', 'close']
    compatible = all(col in twelve_data_format for col in required_columns)
    
    if compatible:
        print("✅ 数据格式兼容")
    else:
        print("❌ 数据格式不兼容，需要修改")

if __name__ == "__main__":
    compare_data_formats()
    test_data_compatibility()