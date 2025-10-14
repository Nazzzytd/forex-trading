# main.py
from trading_coordinator import TradingCoordinator

def main():
    """
    主函数 - 演示完整的外汇交易分析系统
    """
    try:
        # 创建交易协调器
        coordinator = TradingCoordinator()
        
        print("=" * 70)
        print("🚀 外汇交易分析系统 - 技术分析 + AI智能分析")
        print("=" * 70)
        
        # 1. 完整分析 EUR/USD（包含AI分析）
        print("\n1. 📊 完整分析 EUR/USD (包含AI分析):")
        eur_analysis = coordinator.analyze_currency_pair('EUR', 'USD', use_ai=True)
        
        if 'error' in eur_analysis:
            print(f"❌ 分析失败: {eur_analysis['error']}")
        else:
            # 显示技术分析结果
            technical = eur_analysis['technical_analysis']
            print(f"✅ 当前价格: {eur_analysis['latest_data']['price']:.4f}")
            print(f"📅 分析时间: {eur_analysis['latest_data']['date']}")
            print()
            
            # 技术指标详情
            print("🔧 技术指标分析:")
            print(f"   RSI: {technical['rsi']['value']} - {technical['rsi']['signal']}")
            print(f"   MACD: {technical['macd']['signal']} - {technical['macd']['crossover_type']}")
            print(f"   布林带: {technical['bollinger_bands']['signal']}")
            print(f"   随机指标: {technical['stochastic']['signal']} (K:{technical['stochastic']['k']}, D:{technical['stochastic']['d']})")
            print(f"   趋势: {technical['trend']['direction']} (强度: {technical['trend']['strength']}%)")
            print(f"   波动率: {technical['volatility']['level']}")
            print()
            
            # 综合建议
            composite = technical['composite_signal']
            print(f"🎯 综合交易建议: {composite['recommendation']}")
            print(f"   置信度: {composite['confidence']}%")
            print(f"   看涨信号: {composite['bullish_signals']} | 看跌信号: {composite['bearish_signals']}")
            print()
            
            # AI分析结果
            ai_analysis = eur_analysis['ai_analysis']
            if 'analysis' in ai_analysis:
                print("🤖 AI深度分析:")
                print("-" * 40)
                print(ai_analysis['analysis'])
                print("-" * 40)
            elif 'warning' in ai_analysis:
                print("⚠️ AI分析: 功能暂不可用")
            elif 'error' in ai_analysis:
                print(f"❌ AI分析错误: {ai_analysis['error']}")
            
            print(f"\n📝 分析摘要: {eur_analysis['summary']}")
        
        # 2. 监控多个货币对的RSI状态（不包含AI分析，提高速度）
        print("\n2. 📈 多货币对RSI监控 (快速模式):")
        pairs = [
            ('EUR', 'USD'), 
            ('GBP', 'USD'), 
            ('USD', 'JPY'), 
            ('AUD', 'USD'),
            ('USD', 'CHF'),
            ('USD', 'CAD')
        ]
        
        monitoring_results = {}
        for from_curr, to_curr in pairs:
            try:
                # 使用快速模式（不进行AI分析）
                analysis = coordinator.analyze_currency_pair(from_curr, to_curr, use_ai=False)
                monitoring_results[f"{from_curr}/{to_curr}"] = analysis
            except Exception as e:
                monitoring_results[f"{from_curr}/{to_curr}"] = {"error": str(e)}
        
        print("\n   📋 RSI监控结果:")
        print("   " + "-" * 50)
        for pair, result in monitoring_results.items():
            if 'error' in result:
                print(f"   ❌ {pair}: 分析失败 - {result['error']}")
            else:
                technical = result['technical_analysis']
                rsi = technical['rsi']
                price = result['latest_data']['price']
                
                # 根据RSI值添加表情符号
                if rsi['value'] is not None:
                    if rsi['value'] > 70:
                        emoji = "🔥"  # 超买
                    elif rsi['value'] < 30:
                        emoji = "🧊"  # 超卖
                    else:
                        emoji = "⚡"  # 正常
                    
                    status = "超买" if rsi['value'] > 70 else "超卖" if rsi['value'] < 30 else "正常"
                    print(f"   {emoji} {pair}: RSI={rsi['value']:.1f} ({status}) | 价格={price:.4f} | 建议={technical['composite_signal']['recommendation']}")
                else:
                    print(f"   ⚠️  {pair}: RSI数据不可用 | 价格={price:.4f}")
        
        # 3. 特别关注超买/超卖货币对
        print("\n3. ⚠️  特别关注 (超买/超卖):")
        overbought_pairs = []
        oversold_pairs = []
        
        for pair, result in monitoring_results.items():
            if 'error' not in result:
                technical = result['technical_analysis']
                rsi = technical['rsi']
                
                if rsi['value'] is not None:
                    if rsi['value'] > 70:
                        overbought_pairs.append((pair, rsi['value'], result['latest_data']['price']))
                    elif rsi['value'] < 30:
                        oversold_pairs.append((pair, rsi['value'], result['latest_data']['price']))
        
        if overbought_pairs:
            print("   🚨 超买货币对:")
            for pair, rsi_value, price in overbought_pairs:
                print(f"      📛 {pair}: RSI={rsi_value:.1f} | 价格={price:.4f}")
        
        if oversold_pairs:
            print("   💰 超卖货币对 (潜在买入机会):")
            for pair, rsi_value, price in oversold_pairs:
                print(f"      💎 {pair}: RSI={rsi_value:.1f} | 价格={price:.4f}")
        
        if not overbought_pairs and not oversold_pairs:
            print("   ✅ 当前无显著超买/超卖货币对")
        
        # 4. 系统状态总结
        print("\n4. 📊 系统状态总结:")
        total_pairs = len(monitoring_results)
        successful_analysis = sum(1 for result in monitoring_results.values() if 'error' not in result)
        
        print(f"   ✅ 成功分析: {successful_analysis}/{total_pairs} 个货币对")
        print(f"   🤖 AI分析: {'可用' if coordinator.ai_enabled else '不可用'}")
        
        if successful_analysis > 0:
            # 计算平均RSI
            rsi_values = []
            for result in monitoring_results.values():
                if 'error' not in result:
                    rsi_value = result['technical_analysis']['rsi']['value']
                    if rsi_value is not None:
                        rsi_values.append(rsi_value)
            
            if rsi_values:
                avg_rsi = sum(rsi_values) / len(rsi_values)
                market_sentiment = "牛市" if avg_rsi > 55 else "熊市" if avg_rsi < 45 else "震荡"
                print(f"   📈 市场平均RSI: {avg_rsi:.1f} - 整体情绪: {market_sentiment}")
        
        print("\n" + "=" * 70)
        print("🎉 分析完成！建议结合多个时间框架和风险管理策略进行交易决策。")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ 系统错误: {str(e)}")
        print("💡 建议检查网络连接和API密钥配置")

def quick_test():
    """
    快速测试函数 - 用于调试
    """
    try:
        coordinator = TradingCoordinator()
        print("🚀 快速测试模式...")
        
        # 只测试一个货币对
        analysis = coordinator.analyze_currency_pair('EUR', 'USD', use_ai=True)
        
        if 'error' in analysis:
            print(f"❌ 测试失败: {analysis['error']}")
        else:
            print("✅ 测试成功！系统运行正常")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    # 可以选择运行完整分析或快速测试
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        quick_test()
    else:
        main()