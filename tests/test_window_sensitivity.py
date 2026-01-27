"""
Test different Window values for 159792 5min MACD_COMBO
"""
import sys
sys.path.insert(0, 'd:/Projects/stockTradeBot')

from stocktradebot.stock_data import DataFetcher
from stocktradebot.indicators import TechnicalIndicators


def test_window_sensitivity():
    """测试不同Window值对背离检测的影响"""
    symbol = "159792"
    period = "5"  # 5分钟
    
    print(f"\n{'='*60}")
    print(f"测试不同Window值对 {symbol} MACD背离检测的影响")
    print(f"{'='*60}")
    
    # 获取数据
    fetcher = DataFetcher()
    df = fetcher.get_stock_minute(symbol, period)
    
    if df is None:
        print(f"❌ 获取数据失败")
        return
    
    print(f"✅ 数据: {len(df)} 根K线")
    print(f"范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}\n")
    
    # 测试不同的Window值
    test_windows = [2, 3, 5, 7, 10]
    
    for window in test_windows:
        print(f"\n{'='*60}")
        print(f"Window = {window}")
        print(f"{'='*60}")
        
        # 检测背离
        divergences = TechnicalIndicators.detect_macd_divergence(
            df, lookback=len(df), window=window
        )
        
        print(f"检测到 {len(divergences)} 个背离信号")
        
        if divergences:
            # 显示前5个背离
            print(f"\n前5个背离信号:")
            for i, div in enumerate(divergences[:5], 1):
                time_str = df["date"].iloc[div.peak2_idx].strftime("%Y-%m-%d %H:%M")
                price = df["close"].iloc[div.peak2_idx]
                print(f"  {i}. {div.divergence_type} - {time_str} 价格: {price:.4f} 强度: {div.strength:.1f}")
            
            # 显示最后5个背离
            if len(divergences) > 5:
                print(f"\n最后5个背离信号:")
                for i, div in enumerate(divergences[-5:], len(divergences)-4):
                    time_str = df["date"].iloc[div.peak2_idx].strftime("%Y-%m-%d %H:%M")
                    price = df["close"].iloc[div.peak2_idx]
                    print(f"  {i}. {div.divergence_type} - {time_str} 价格: {price:.4f} 强度: {div.strength:.1f}")
        else:
            print("  ❌ 未检测到任何背离")
    
    # 推荐
    print(f"\n\n{'='*60}")
    print("结论与建议")
    print(f"{'='*60}")
    print("\n对于5分钟K线数据:")
    print("- Window=2: 窗口太小，可能错过很多背离信号")
    print("- Window=3-5: 适中，能检测到较明显的背离")
    print("- Window=7-10: 窗口较大，只检测非常明显的背离")
    print("\n建议:")
    print("- 短周期(1min, 5min): 使用 Window=3 或 5")
    print("- 中周期(15min, 30min): 使用 Window=5 或 7")
    print("- 长周期(60min, daily): 使用 Window=5 或 10")


if __name__ == "__main__":
    test_window_sensitivity()
