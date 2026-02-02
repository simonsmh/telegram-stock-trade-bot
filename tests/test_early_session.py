"""
Test data fetching during early trading session
模拟早盘时段数据获取测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, time
from stocktradebot.stock_data import DataFetcher


def is_early_session():
    """检查当前是否在早盘时段（9:30-10:30）"""
    now = datetime.now().time()
    return time(9, 30) <= now <= time(10, 30)


def is_trading_hours():
    """检查当前是否在交易时段"""
    now = datetime.now().time()
    # 上午盘 9:30-11:30，下午盘 13:00-15:00
    morning = time(9, 30) <= now <= time(11, 30)
    afternoon = time(13, 0) <= now <= time(15, 0)
    return morning or afternoon


def test_with_retry(symbol, period, max_retries=3, delay=5):
    """带重试的数据获取测试"""
    import time as time_module

    fetcher = DataFetcher()

    for attempt in range(max_retries):
        print(f"  尝试 {attempt + 1}/{max_retries}...")
        df = fetcher.get_stock_minute(symbol, period)

        if df is not None and not df.empty:
            print(f"  ✅ 成功: {len(df)} 根K线")
            return True, df

        print(f"  ❌ 失败，等待 {delay} 秒后重试...")
        time_module.sleep(delay)

    return False, None


def test_601288_early_session():
    """测试 601288 早盘数据获取"""
    symbol = "601288"
    period = "15"

    print(f"\n{'='*60}")
    print(f"测试: {symbol} {period}分钟线 早盘数据获取")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"是否早盘时段: {is_early_session()}")
    print(f"是否交易时段: {is_trading_hours()}")
    print(f"{'='*60}")

    # 直接获取
    print("\n1. 直接获取...")
    fetcher = DataFetcher()
    df = fetcher.get_stock_minute(symbol, period)

    if df is not None and not df.empty:
        print(f"✅ 直接获取成功: {len(df)} 根K线")
        print(f"数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
        return True
    else:
        print("❌ 直接获取失败")

    # 重试获取
    print("\n2. 重试获取...")
    success, df = test_with_retry(symbol, period, max_retries=3, delay=5)

    if success:
        print(f"✅ 重试后成功")
        return True
    else:
        print("❌ 重试后仍失败")

    return False


def test_multiple_symbols():
    """测试多个品种"""
    test_cases = [
        ("601288", "15"),   # 股票 - 日志中失败
        ("159792", "5"),    # ETF - 日志中失败
        ("159363", "5"),    # ETF - 日志中失败
        ("000001", "15"),   # 股票 - 额外测试
    ]

    print(f"\n{'='*80}")
    print(f"批量测试多个品种")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"是否早盘时段: {is_early_session()}")
    print(f"是否交易时段: {is_trading_hours()}")
    print(f"{'='*80}")

    results = {}
    fetcher = DataFetcher()

    for symbol, period in test_cases:
        print(f"\n测试: {symbol} {period}分钟...")
        df = fetcher.get_stock_minute(symbol, period)

        if df is not None and not df.empty:
            print(f"  ✅ 成功: {len(df)} 根K线")
            results[f"{symbol}_{period}min"] = True
        else:
            print(f"  ❌ 失败: 返回 None/Empty")
            results[f"{symbol}_{period}min"] = False

    # 汇总
    print(f"\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}")

    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {name}: {status}")

    success_count = sum(1 for v in results.values() if v)
    print(f"\n总计: {success_count}/{len(results)} 个成功")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='测试早盘数据获取')
    parser.add_argument('--single', action='store_true', help='只测试单个品种 601288')
    parser.add_argument('--multi', action='store_true', help='测试多个品种')
    parser.add_argument('--retry', type=int, default=0, help='重试次数')

    args = parser.parse_args()

    if args.single or (not args.single and not args.multi):
        # 测试单个品种
        if args.retry > 0:
            test_with_retry("601288", "15", max_retries=args.retry)
        else:
            test_601288_early_session()

    if args.multi:
        # 测试多个品种
        test_multiple_symbols()
