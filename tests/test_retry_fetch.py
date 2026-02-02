"""
Test data fetching with retry mechanism
带重试机制的数据获取测试
"""
import sys
import os
import asyncio
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stocktradebot.stock_data import DataFetcher


async def fetch_with_retry(symbol, period, max_retries=3, delay=5):
    """
    带重试的数据获取

    Args:
        symbol: 股票代码
        period: 周期
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    fetcher = DataFetcher()

    for attempt in range(max_retries):
        print(f"    [{symbol}] 尝试 {attempt + 1}/{max_retries}...")

        try:
            # 在事件循环中运行同步代码
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, fetcher.get_stock_minute, symbol, period)

            if df is not None and not df.empty:
                print(f"    [{symbol}] ✅ 成功: {len(df)} 根K线")
                return True, df
            else:
                print(f"    [{symbol}] ❌ 返回空数据")

        except Exception as e:
            print(f"    [{symbol}] ❌ 异常: {e}")

        if attempt < max_retries - 1:
            print(f"    [{symbol}] 等待 {delay} 秒后重试...")
            await asyncio.sleep(delay)

    return False, None


async def test_single_with_retry():
    """测试单个品种带重试的获取"""
    symbol = "601288"
    period = "15"

    print(f"\n{'='*60}")
    print(f"测试: 单个品种带重试获取")
    print(f"品种: {symbol}, 周期: {period}分钟")
    print(f"{'='*60}")

    success, df = await fetch_with_retry(symbol, period, max_retries=3, delay=5)

    if success:
        print(f"\n✅ 最终成功: {len(df)} 根K线")
        print(f"数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    else:
        print(f"\n❌ 最终失败: 3次重试后仍无法获取数据")

    return success


async def test_multiple_with_retry():
    """测试多个品种并发带重试的获取"""
    test_cases = [
        ("601288", "15"),   # 日志中失败
        ("159792", "5"),    # 日志中失败
        ("159363", "5"),    # 日志中失败
    ]

    print(f"\n{'='*60}")
    print(f"测试: 多个品种并发带重试获取")
    print(f"{'='*60}")

    # 并发执行（带信号量限制）
    semaphore = asyncio.Semaphore(3)  # 最多3个并发

    async def fetch_with_semaphore(symbol, period):
        async with semaphore:
            return await fetch_with_retry(symbol, period, max_retries=3, delay=3)

    tasks = [
        fetch_with_semaphore(symbol, period)
        for symbol, period in test_cases
    ]

    results = await asyncio.gather(*tasks)

    # 汇总
    print(f"\n{'='*60}")
    print("结果汇总")
    print(f"{'='*60}")

    for (symbol, period), (success, df) in zip(test_cases, results):
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {symbol}_{period}min: {status}")

    success_count = sum(1 for success, _ in results if success)
    print(f"\n总计: {success_count}/{len(test_cases)} 个成功")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='带重试的数据获取测试')
    parser.add_argument('--single', action='store_true', help='测试单个品种')
    parser.add_argument('--multi', action='store_true', help='测试多个品种')

    args = parser.parse_args()

    if args.single or (not args.single and not args.multi):
        asyncio.run(test_single_with_retry())

    if args.multi:
        asyncio.run(test_multiple_with_retry())
