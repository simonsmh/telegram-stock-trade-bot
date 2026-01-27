"""
Debug: Compare divergence detection with different lookback values
"""
import sys
sys.path.insert(0, 'd:/Projects/stockTradeBot')

from stocktradebot.stock_data import DataFetcher
from stocktradebot.indicators import TechnicalIndicators


def test_lookback_impact():
    """测试lookback参数对背离检测的影响"""
    symbol = "159792"
    period = "5"
    window = 2
    
    print(f"\n{'='*60}")
    print(f"测试lookback参数对背离检测的影响")
    print(f"Symbol: {symbol}, Period: {period}min, Window: {window}")
    print(f"{'='*60}")
    
    fetcher = DataFetcher()
    df = fetcher.get_stock_minute(symbol, period)
    
    if df is None:
        print("❌ 获取数据失败")
        return
    
    print(f"\n总数据量: {len(df)} 根K线")
    print(f"数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}\n")
    
    # 测试不同的lookback值
    lookback_values = [60, 100, 200, 500, len(df)]
    
    for lookback in lookback_values:
        divergences = TechnicalIndicators.detect_macd_divergence(
            df, lookback=lookback, window=window
        )
        
        print(f"lookback={lookback:4d}: 检测到 {len(divergences):2d} 个背离")
        
        if divergences and len(divergences) <= 3:
            for div in divergences:
                time_str = df["date"].iloc[div.peak2_idx].strftime("%Y-%m-%d %H:%M")
                print(f"  - {div.divergence_type} at {time_str}")
    
    print(f"\n{'='*60}")
    print("结论:")
    print(f"{'='*60}")
    print("lookback参数决定了回溯分析的K线数量")
    print("- lookback越大，能检测到的背离信号越多")
    print("- 默认lookback=60可能对于某些数据不够")
    print(f"- 使用lookback=len(df)可以分析全部历史数据")


if __name__ == "__main__":
    test_lookback_impact()
