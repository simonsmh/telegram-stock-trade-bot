"""
Test backtest for 159792 5min MACD_COMBO Window=2
"""
import sys
sys.path.insert(0, 'd:/Projects/stockTradeBot')

from stocktradebot.stock_data import DataFetcher
from stocktradebot.indicators import TechnicalIndicators


def test_159792_5min_macd():
    """测试 159792 5分钟 MACD 回测"""
    symbol = "159792"
    period = "5"  # 5分钟
    window = 2
    
    print(f"\n{'='*60}")
    print(f"测试: {symbol} {period}分钟线 MACD_COMBO Window={window}")
    print(f"{'='*60}")
    
    # 1. 获取数据
    fetcher = DataFetcher()
    df = fetcher.get_stock_minute(symbol, period)
    
    if df is None:
        print(f"❌ 获取数据失败")
        return
    
    print(f"✅ 获取数据成功: {len(df)} 根K线")
    print(f"数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"最新价: {df['close'].iloc[-1]}")
    
    # 2. 计算 MACD 指标
    macd_df = TechnicalIndicators.calculate_macd(df)
    print(f"\n当前 MACD 值:")
    print(f"  DIF: {macd_df['dif'].iloc[-1]:.4f}")
    print(f"  DEA: {macd_df['dea'].iloc[-1]:.4f}")
    print(f"  MACD: {macd_df['macd'].iloc[-1]:.4f}")
    
    # 3. 检测 MACD 金叉死叉信号
    signals = []
    for i in range(1, len(df)):
        prev_dif = macd_df["dif"].iloc[i - 1]
        prev_dea = macd_df["dea"].iloc[i - 1]
        curr_dif = macd_df["dif"].iloc[i]
        curr_dea = macd_df["dea"].iloc[i]
        time_str = df["date"].iloc[i].strftime("%Y-%m-%d %H:%M")
        price = df["close"].iloc[i]

        if prev_dif <= prev_dea and curr_dif > curr_dea:
            signals.append({"type": "金叉", "time": time_str, "price": price, "index": i})
        if prev_dif >= prev_dea and curr_dif < curr_dea:
            signals.append({"type": "死叉", "time": time_str, "price": price, "index": i})
    
    print(f"\n{'='*60}")
    print(f"检测到 {len(signals)} 个 MACD 信号")
    print(f"{'='*60}")
    
    if signals:
        # 显示最近10个信号
        print("\n最近10个信号:")
        for sig in signals[-10:]:
            emoji = "🟢" if sig["type"] == "金叉" else "🔴"
            print(f"  {emoji} {sig['type']} - {sig['time']} 价格: {sig['price']:.4f}")
        
        # 最近信号
        last_sig = signals[-1]
        print(f"\n{'='*60}")
        print(f"最近信号:")
        print(f"  类型: {last_sig['type']}")
        print(f"  时间: {last_sig['time']}")
        print(f"  价格: {last_sig['price']:.4f}")
        print(f"  趋势: {'多头' if last_sig['type'] == '金叉' else '空头'}")
        print(f"{'='*60}")
    else:
        print("❌ 未检测到任何信号!")
        
        # 调试 - 打印最后几个 DIF 和 DEA 值
        print("\n调试 - 最后 10 根K线的 DIF/DEA 值:")
        for i in range(-10, 0):
            dif = macd_df['dif'].iloc[i]
            dea = macd_df['dea'].iloc[i]
            time_str = df['date'].iloc[i].strftime("%Y-%m-%d %H:%M")
            status = "DIF>DEA" if dif > dea else "DIF<DEA"
            print(f"  {time_str}: DIF={dif:.4f}, DEA={dea:.4f} ({status})")
    
    # 4. 检测 MACD 背离信号
    print(f"\n{'='*60}")
    print(f"检测 MACD 背离信号 (Window={window})")
    print(f"{'='*60}")
    
    divergences = TechnicalIndicators.detect_macd_divergence(df, lookback=len(df), window=window)
    
    print(f"\n检测到 {len(divergences)} 个背离信号")
    
    if divergences:
        print("\n所有背离信号:")
        for div in divergences:
            emoji = "🟢" if div.divergence_type == "底背离" else "🔴"
            time_str = df["date"].iloc[div.peak2_idx].strftime("%Y-%m-%d %H:%M")
            price = df["close"].iloc[div.peak2_idx]
            print(f"  {emoji} {div.divergence_type} - {time_str} 价格: {price:.4f}")
        
        # 最近背离
        last_div = divergences[-1]
        last_div_time = df["date"].iloc[last_div.peak2_idx].strftime("%Y-%m-%d %H:%M")
        last_div_price = df["close"].iloc[last_div.peak2_idx]
        print("\n最近背离:")
        print(f"  类型: {last_div.divergence_type}")
        print(f"  时间: {last_div_time}")
        print(f"  价格: {last_div_price:.4f}")
    else:
        print("❌ 未检测到任何背离信号!")
    
    # 5. 测试 MACD_COMBO (金叉死叉 + 背离)
    print(f"\n{'='*60}")
    print("MACD_COMBO 组合信号")
    print(f"{'='*60}")
    
    combo_signals = []
    
    # 遍历所有金叉死叉信号
    for sig in signals:
        sig_index = sig["index"]
        sig_type = sig["type"]
        
        # 检查该位置是否有对应的背离信号
        for div in divergences:
            div_index = div.peak2_idx
            div_type = div.divergence_type
            
            # 金叉 + 底背离 或 死叉 + 顶背离
            if sig_index == div_index:
                if (sig_type == "金叉" and div_type == "底背离") or \
                   (sig_type == "死叉" and div_type == "顶背离"):
                    combo_signals.append({
                        "type": sig_type,
                        "divergence": div_type,
                        "time": sig["time"],
                        "price": sig["price"],
                        "index": sig_index
                    })
    
    print(f"\n检测到 {len(combo_signals)} 个组合信号")
    
    if combo_signals:
        print("\n所有组合信号:")
        for combo in combo_signals:
            emoji = "🟢" if combo["type"] == "金叉" else "🔴"
            print(f"  {emoji} {combo['type']} + {combo['divergence']} - {combo['time']} 价格: {combo['price']:.4f}")
    else:
        print("❌ 未检测到任何组合信号!")
        print("\n可能原因:")
        print(f"  - 金叉/死叉信号数: {len(signals)}")
        print(f"  - 背离信号数: {len(divergences)}")
        print("  - 两者在同一位置没有重合")


if __name__ == "__main__":
    test_159792_5min_macd()
