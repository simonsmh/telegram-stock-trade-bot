"""
Test data fetching for problematic symbols
测试日志中报错的数据获取
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stocktradebot.stock_data import DataFetcher
from stocktradebot.config import PERIOD_TYPES


def test_stock_minute_601288():
    """测试 601288 15分钟数据获取 - 日志中失败的案例"""
    symbol = "601288"
    period = "15"

    print(f"\n{'='*60}")
    print(f"测试: {symbol} {period}分钟线")
    print(f"{'='*60}")

    fetcher = DataFetcher()
    df = fetcher.get_stock_minute(symbol, period)

    if df is None or df.empty:
        print(f"❌ 获取数据失败 - 返回 None/Empty")
        print(f"   品种: {symbol}")
        print(f"   周期: {period}分钟")
        print(f"   时间: {__import__('datetime').datetime.now()}")
        return False

    print(f"✅ 获取数据成功: {len(df)} 根K线")
    print(f"数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"最新价: {df['close'].iloc[-1]}")
    return True


def test_etf_minute_159792():
    """测试 159792 5分钟数据获取 - 日志中失败的案例"""
    symbol = "159792"
    period = "5"

    print(f"\n{'='*60}")
    print(f"测试: {symbol} {period}分钟线 (ETF)")
    print(f"{'='*60}")

    fetcher = DataFetcher()
    # ETF 也使用 stock_minute 方法
    df = fetcher.get_stock_minute(symbol, period)

    if df is None or df.empty:
        print(f"❌ 获取数据失败 - 返回 None/Empty")
        return False

    print(f"✅ 获取数据成功: {len(df)} 根K线")
    print(f"数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"最新价: {df['close'].iloc[-1]}")
    return True


def test_etf_minute_159363():
    """测试 159363 5分钟数据获取 - 日志中失败的案例"""
    symbol = "159363"
    period = "5"

    print(f"\n{'='*60}")
    print(f"测试: {symbol} {period}分钟线 (ETF)")
    print(f"{'='*60}")

    fetcher = DataFetcher()
    df = fetcher.get_stock_minute(symbol, period)

    if df is None or df.empty:
        print(f"❌ 获取数据失败 - 返回 None/Empty")
        return False

    print(f"✅ 获取数据成功: {len(df)} 根K线")
    print(f"数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"最新价: {df['close'].iloc[-1]}")
    return True


def test_gold_au9999():
    """测试 au9999 数据获取 - 日志中成功的案例"""
    symbol = "Au99.99"
    period = "15"

    print(f"\n{'='*60}")
    print(f"测试: {symbol} {period}分钟线 (黄金现货)")
    print(f"{'='*60}")

    fetcher = DataFetcher()
    futures_symbol = "AU2606"
    df = fetcher.get_futures_minute(futures_symbol, period)

    if df is None or df.empty:
        print(f"❌ 获取数据失败 - 返回 None/Empty")
        return False

    print(f"✅ 获取数据成功: {len(df)} 根K线")
    if 'date' in df.columns:
        print(f"数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"最新价: {df['close'].iloc[-1]}")
    return True


def test_all_problematic_symbols():
    """测试所有日志中报错的数据获取"""
    print(f"\n{'='*80}")
    print(f"批量测试: 所有日志中报错的数据获取")
    print(f"测试时间: {__import__('datetime').datetime.now()}")
    print(f"{'='*80}")

    results = {
        "601288_15min": test_stock_minute_601288(),
        "159792_5min": test_etf_minute_159792(),
        "159363_5min": test_etf_minute_159363(),
        "au9999_15min": test_gold_au9999(),
    }

    print(f"\n{'='*80}")
    print(f"测试结果汇总")
    print(f"{'='*80}")

    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {name}: {status}")

    success_count = sum(1 for v in results.values() if v)
    print(f"\n总计: {success_count}/{len(results)} 个成功")

    return results


if __name__ == "__main__":
    # 运行单个测试
    # test_stock_minute_601288()
    # test_etf_minute_159792()
    # test_etf_minute_159363()
    # test_gold_au9999()

    # 运行全部测试
    test_all_problematic_symbols()
