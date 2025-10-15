# main.py
from trading_coordinator import TradingCoordinator
import json

def debug_market_overview():
    """调试市场概览数据"""
    try:
        coordinator = TradingCoordinator()
        print("🔍 调试市场概览...")
        
        market_overview = coordinator.get_market_overview()
        results = market_overview['currency_analysis']
        
        for pair, result in results.items():
            print(f"\n{pair}:")
            if 'error' in result:
                print(f"  ❌ 错误: {result['error']}")
            else:
                print(f"  ✅ 有数据")
                print(f"  Keys: {list(result.keys())}")
                if 'technical_analysis' in result:
                    tech_data = result['technical_analysis']
                    print(f"  Technical Keys: {list(tech_data.keys())}")
                    if 'technical_analysis' in tech_data:
                        tech = tech_data['technical_analysis']
                        print(f"  RSI: {tech.get('rsi', {}).get('value', 'N/A')}")
                    else:
                        print("  ❌ 缺少 technical_analysis 嵌套数据")
                else:
                    print("  ❌ 缺少 technical_analysis 数据")
                        
    except Exception as e:
        print(f"调试失败: {e}")

def main():
    """主函数 - 演示完整的外汇交易分析系统"""
    try:
        coordinator = TradingCoordinator()
        
        print("=" * 60)
        print("🚀 外汇交易分析系统")
        print("=" * 60)
        
        # 1. 完整分析 EUR/USD
        print("\n1. 📊 完整分析 EUR/USD:")
        eur_analysis = coordinator.analyze_with_fundamentals('EUR', 'USD')
        
        if 'error' in eur_analysis:
            print(f"❌ 分析失败: {eur_analysis['error']}")
        else:
            # 显示基本信息
            tech_data = eur_analysis['technical_analysis']
            latest_data = tech_data.get('latest_data', {})
            price = latest_data.get('price', 'N/A')
            date = latest_data.get('date', 'N/A')
            
            print(f"✅ 当前价格: {price}")
            print(f"📅 分析时间: {date}")
            
            # 技术指标
            technical = tech_data['technical_analysis']
            print("\n🔧 技术指标:")
            print(f"   RSI: {technical['rsi']['value']} - {technical['rsi']['signal']}")
            print(f"   MACD: {technical['macd']['signal']} - {technical['macd']['crossover_type']}")
            print(f"   布林带: {technical['bollinger_bands']['signal']}")
            print(f"   趋势: {technical['trend']['direction']} (强度: {technical['trend']['strength']}%)")
            
            # 综合建议
            composite = technical['composite_signal']
            print(f"\n🎯 综合建议: {composite['recommendation']}")
            print(f"   置信度: {composite['confidence']}%")
            print(f"   看涨信号: {composite['bullish_signals']} | 看跌信号: {composite['bearish_signals']}")
            
            # AI分析
            ai_analysis = technical.get('ai_analysis', {})
            if 'analysis' in ai_analysis:
                print(f"\n🤖 AI分析:")
                print("-" * 40)
                print(ai_analysis['analysis'])
                print("-" * 40)
            elif 'warning' in ai_analysis:
                print("⚠️ AI分析: 功能暂不可用")
            elif 'error' in ai_analysis:
                print(f"❌ AI分析错误: {ai_analysis['error']}")
            
            # 经济日历
            print("\n📅 经济日历:")
            fundamental = eur_analysis['fundamental_analysis']
            if 'error' not in fundamental:
                events = fundamental.get('economic_events', {}).get('high_impact_events', 0)
                news = fundamental.get('news_summary', {}).get('high_impact_news', 0)
                print(f"   高影响事件: {events}个数据 + {news}个新闻")
                
                # 显示关键事件
                integrated_analysis = fundamental.get('integrated_analysis', {})
                if 'key_events_timeline' in integrated_analysis:
                    print("\n   关键事件时间线:")
                    for event in integrated_analysis['key_events_timeline'][:3]:
                        print(f"     • {event['name']} - {event['date']} {event['time']}")
            else:
                print("   经济日历数据暂不可用")
            
            # 风险和建议
            risk = eur_analysis['risk_assessment']
            rec = eur_analysis['trading_recommendation']
            print(f"\n⚠️ 风险分析:")
            print(f"   技术面风险: {risk['technical_risk']}")
            print(f"   基本面风险: {risk['fundamental_risk']}")
            print(f"   综合风险等级: {risk['combined_risk']}")
            print(f"   建议仓位: {risk['position_size']}")
            
            print(f"\n💡 交易建议:")
            for suggestion in rec['recommendations']:
                print(f"   • {suggestion}")
            
            print(f"\n📝 分析摘要: {tech_data['summary']}")
        
        # 2. 市场概览
        print("\n2. 🌍 市场概览:")
        market_overview = coordinator.get_market_overview()
        
        successful_pairs = []
        for pair, result in results.items():
            if 'error' not in result and 'technical_analysis' in result:
                tech_data = result['technical_analysis']
                
                # 修复：检查两种可能的数据结构
                if 'technical_analysis' in tech_data:
                    # 嵌套结构：tech_data['technical_analysis']['rsi']
                    tech = tech_data['technical_analysis']
                    rsi = tech['rsi']['value']
                else:
                    # 直接结构：tech_data['rsi']
                    tech = tech_data
                    rsi = tech['rsi']['value']
                
                price = result.get('latest_data', {}).get('price', 'N/A')
                
                if rsi is not None:
                    if rsi > 70:
                        status = "🔥超买"
                    elif rsi < 30:
                        status = "🧊超卖"
                    else:
                        status = "⚡正常"
                    print(f"   {status} {pair}: RSI={rsi:.1f} | 价格={price}")
                    successful_pairs.append((pair, rsi, price))
                else:
                    print(f"   ⚠️  {pair}: RSI数据不可用 | 价格={price}")
            else:
                print(f"   ❌ {pair}: 分析失败 - {result.get('error', '未知错误')}")
            
            # 经济日历摘要
            calendar = market_overview['economic_calendar']
            if 'error' not in calendar:
                events = calendar.get('economic_events', {}).get('high_impact_events', 0)
                news = calendar.get('news_summary', {}).get('high_impact_news', 0)
                print(f"\n📅 经济日历摘要:")
                print(f"   未来3天高影响事件: {events}个经济数据 + {news}个新闻")
                
                # 显示风险等级
                risk_info = calendar.get('integrated_analysis', {}).get('risk_assessment', {})
                if risk_info:
                    risk_level = risk_info.get('risk_level', 'unknown')
                    position_size = risk_info.get('recommended_position_size', 'normal')
                    print(f"   市场风险等级: {risk_level} | 建议仓位: {position_size}")
        
        # 3. 超买/超卖分析
        print("\n3. ⚠️ 超买/超卖分析:")
        overbought = []
        oversold = []
        
        if 'currency_analysis' in market_overview:
            for pair, result in market_overview['currency_analysis'].items():
                if 'error' not in result and 'technical_analysis' in result:
                    tech_data = result['technical_analysis']
                    if 'technical_analysis' in tech_data:
                        tech = tech_data['technical_analysis']
                        rsi = tech['rsi']['value']
                        
                        if rsi is not None:
                            if rsi > 70:
                                overbought.append((pair, rsi, result.get('latest_data', {}).get('price', 'N/A')))
                            elif rsi < 30:
                                oversold.append((pair, rsi, result.get('latest_data', {}).get('price', 'N/A')))
        
        if overbought:
            print("   🚨 超买货币对:")
            for pair, rsi, price in overbought:
                print(f"      📛 {pair}: RSI={rsi:.1f} | 价格={price}")
        
        if oversold:
            print("   💰 超卖货币对 (潜在买入机会):")
            for pair, rsi, price in oversold:
                print(f"      💎 {pair}: RSI={rsi:.1f} | 价格={price}")
        
        if not overbought and not oversold:
            print("   ✅ 当前无显著超买/超卖货币对")
        
        # 4. 系统状态
        print("\n4. 📊 系统状态:")
        if 'currency_analysis' in market_overview:
            total = len(market_overview['currency_analysis'])
            success = sum(1 for r in market_overview['currency_analysis'].values() 
                         if 'error' not in r and 'technical_analysis' in r)
            print(f"   ✅ 成功分析: {success}/{total} 个货币对")
            
            # 平均RSI
            rsi_values = []
            for result in market_overview['currency_analysis'].values():
                if 'error' not in result and 'technical_analysis' in result:
                    tech_data = result['technical_analysis']
                    if 'technical_analysis' in tech_data:
                        rsi_value = tech_data['technical_analysis']['rsi']['value']
                        if rsi_value is not None:
                            rsi_values.append(rsi_value)
            
            if rsi_values:
                avg_rsi = sum(rsi_values) / len(rsi_values)
                sentiment = "🐂牛市" if avg_rsi > 55 else "🐻熊市" if avg_rsi < 45 else "🔄震荡"
                print(f"   📈 市场平均RSI: {avg_rsi:.1f} - 整体情绪: {sentiment}")
            else:
                print("   📈 市场平均RSI: 数据不足")
        
        print("\n" + "=" * 60)
        print("🎉 分析完成！建议结合技术面、基本面和风险管理策略进行交易决策。")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 系统错误: {str(e)}")

def quick_test():
    """快速测试"""
    try:
        coordinator = TradingCoordinator()
        print("🚀 快速测试...")
        
        analysis = coordinator.analyze_with_fundamentals('EUR', 'USD')
        
        if 'error' in analysis:
            print(f"❌ 测试失败: {analysis['error']}")
        else:
            print("✅ 测试成功!")
            tech_data = analysis['technical_analysis']
            technical = tech_data['technical_analysis']
            print(f"货币对: {analysis['symbol']}")
            print(f"价格: {tech_data.get('latest_data', {}).get('price', 'N/A')}")
            print(f"综合建议: {technical['composite_signal']['recommendation']}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_economic_calendar():
    """测试经济日历"""
    try:
        coordinator = TradingCoordinator()
        print("📅 测试经济日历...")
        
        calendar_data = coordinator.calendar.get_comprehensive_economic_calendar("EUR/USD", 3)
        
        if 'error' in calendar_data:
            print(f"❌ 失败: {calendar_data['error']}")
        else:
            print("✅ 经济日历正常!")
            events = calendar_data['economic_events']['high_impact_events']
            news = calendar_data['news_summary']['high_impact_news']
            print(f"事件: {events}个数据 + {news}个新闻")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    import sys
    
    # 现在可以调用调试函数了
    debug_market_overview()
    
    # 如果要运行完整程序，取消下面的注释
    # if len(sys.argv) > 1:
    #     if sys.argv[1] == 'test':
    #         quick_test()
    #     elif sys.argv[1] == 'calendar_test':
    #         test_economic_calendar()
    #     else:
    #         print("用法:")
    #         print("  python main.py              # 完整分析")
    #         print("  python main.py test         # 快速测试")
    #         print("  python main.py calendar_test # 经济日历测试")
    # else:
    #     main()