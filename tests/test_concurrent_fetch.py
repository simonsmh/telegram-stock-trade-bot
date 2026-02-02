"""
Test concurrent data fetching
测试并发数据获取是否存在限流问题
"""
import sys
import os
import asyncio
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stocktradebot.stock_data import DataFetcher


async def fetch_single(symbol, period, semaphore, fetcher):
    """获取单个品种的数据"""
    async with semaphore:
        print(f"  [{symbol}] 开始获取...")
        start = time.time()

        # 在事件循环中运行同步代码
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, fetcher.get_stock_minute, symbol, period)

        elapsed = time.time() - start

        if df is not None and not df.empty:
            print(f"  [{symbol}] ✅ 成功 ({elapsed:.2f}s): {len(df)} 根K线")
            return True, df
        else:
            print(f"  [{symbol}] ❌ 失败 ({elapsed:.2f}s): 返回 None/Empty")
            return False, None


async def test_concurrent_fetch(symbols, period="15", max_concurrent=5):
    """测试并发获取多个品种"""
    print(f"\n{'='*60}")
    print(f"并发测试: {len(symbols)} 个品种, 周期={period}分钟")
    print(f"并发限制: {max_concurrent}")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    semaphore = asyncio.Semaphore(max_concurrent)
    fetcher = DataFetcher()

    start = time.time()

    # 并发执行所有请求
    tasks = [
        fetch_single(symbol, period, semaphore, fetcher)
        for symbol in symbols
    ]
    results = await asyncio.gather(*tasks)

    elapsed = time.time() - start

    # 汇总结果
    print(f"\n{'='*60}")
    print(f"结果汇总 (总耗时: {elapsed:.2f}s)")
    print(f"{'='*60}")

    success_count = 0
    for symbol, (success, df) in zip(symbols, results):
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {symbol}: {status}")
        if success:
            success_count += 1

    print(f"\n总计: {success_count}/{len(symbols)} 个成功")

    # 分析是否有限流问题
    if success_count < len(symbols):
        print(f"\n⚠️ 警告: {len(symbols) - success_count} 个请求失败")
        print("可能原因:")
        print("  - akshare 接口限流")
        print("  - 并发请求过多")
        print("  - 早盘数据未就绪")

    return results


async def test_sequential_fetch(symbols, period="15"):
    """测试串行获取多个品种（对比用）"""
    print(f"\n{'='*60}")
    print(f"串行测试: {len(symbols)} 个品种, 周期={period}分钟")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    fetcher = DataFetcher()
    results = []

    start = time.time()

    for symbol in symbols:
        print(f"\n[{symbol}] 开始获取...")
        s = time.time()
        df = fetcher.get_stock_minute(symbol, period)
        e = time.time()

        if df is not None and not df.empty:
            print(f"  ✅ 成功 ({e-s:.2f}s): {len(df)} 根K线")
            results.append((True, df))
        else:
            print(f"  ❌ 失败 ({e-s:.2f}s): 返回 None/Empty")
            results.append((False, None))

    elapsed = time.time() - start

    # 汇总
    print(f"\n{'='*60}")
    print(f"结果汇总 (总耗时: {elapsed:.2f}s)")
    print(f"{'='*60}")

    success_count = sum(1 for success, _ in results if success)
    print(f"总计: {success_count}/{len(symbols)} 个成功")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='测试并发数据获取')
    parser.add_argument('--concurrent', action='store_true', help='测试并发模式')
    parser.add_argument('--sequential', action='store_true', help='测试串行模式')
    parser.add_argument('--max-concurrent', type=int, default=5, help='最大并发数')
    parser.add_argument('--period', type=str, default='15', help='数据周期')

    args = parser.parse_args()

    # 测试品种（日志中失败的）
    test_symbols = [
        "601288",   # 股票 - 日志中失败
        "159792",   # ETF - 日志中失败
        "159363",   # ETF - 日志中失败
        "000001",   # 额外测试
        "600000",   # 额外测试
    ]

    if args.concurrent or (not args.concurrent and not args.sequential):
        # 测试并发
        asyncio.run(test_concurrent_fetch(
            test_symbols,
            period=args.period,
            max_concurrent=args.max_concurrent
        ))

    if args.sequential:
        # 测试串行
        asyncio.run(test_sequential_fetch(test_symbols, period=args.period))
