"""
Test time-related data fetching issue
测试时间相关的数据获取问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, time, timezone, timedelta
from stocktradebot.stock_data import DataFetcher


def analyze_time():
    """分析当前时间情况"""
    print(f"\n{'='*60}")
    print("时间分析")
    print(f"{'='*60}")

    # 系统本地时间 (JST)
    now_local = datetime.now()
    print(f"系统本地时间 (JST): {now_local.strftime('%Y-%m-%d %H:%M:%S')}")

    # UTC 时间
    now_utc = datetime.now(timezone.utc)
    print(f"UTC 时间: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")

    # 北京时间 (CST)
    cst_tz = timezone(timedelta(hours=8))
    now_cst = datetime.now(cst_tz)
    print(f"北京时间 (CST): {now_cst.strftime('%Y-%m-%d %H:%M:%S')}")

    # 日志中的时间分析
    log_time_str = "2026-02-02 10:29:47"  # 用户日志中的时间
    log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S")

    print(f"\n日志中的时间: {log_time_str}")
    print(f"  - 假设为 JST: 对应 UTC {log_time - timedelta(hours=9)}")
    print(f"  - 假设为 CST: 对应 UTC {log_time - timedelta(hours=8)}")

    # apscheduler 时间
    scheduler_time_str = "2026-02-02 12:47:47 UTC"
    print(f"\napscheduler 调度时间: {scheduler_time_str}")

    # 时间差分析
    print(f"\n时间关系分析:")
    print(f"  - 如果日志时间是 JST 10:29，对应 UTC 01:29")
    print(f"  - 但 apscheduler 在 UTC 12:47 执行")
    print(f"  - 两者相差约 11 小时 18 分钟，对不上")
    print(f"\n可能原因:")
    print(f"  1. 日志和调度器来自不同的系统/容器")
    print(f"  2. 系统时间被手动修改过")
    print(f"  3. 日志时间是昨天的？")


def test_data_fetching_at_current_time():
    """在测试当前时间点获取数据"""
    print(f"\n{'='*60}")
    print("当前时间点数据获取测试")
    print(f"{'='*60}")

    now = datetime.now()
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # 判断当前属于哪个时段
    current_time = now.time()

    # 北京时间 = 日本时间 - 1小时
    beijing_now = now - timedelta(hours=1)
    print(f"对应北京时间: {beijing_now.strftime('%Y-%m-%d %H:%M:%S')}")

    # 判断北京时段
    beijing_time = beijing_now.time()
    if time(9, 30) <= beijing_time <= time(11, 30):
        print("北京时段: 上午交易时段 (9:30-11:30)")
    elif time(13, 0) <= beijing_time <= time(15, 0):
        print("北京时段: 下午交易时段 (13:00-15:00)")
    elif time(0, 0) <= beijing_time <= time(9, 30):
        print("北京时段: 盘前时段 (00:00-9:30)")
    else:
        print("北京时段: 盘后时段 (15:00-24:00)")

    # 测试数据获取
    print(f"\n测试数据获取...")
    test_symbols = ["601288", "159792", "159363"]

    fetcher = DataFetcher()
    results = []

    for symbol in test_symbols:
        print(f"  [{symbol}] 获取中...")
        df = fetcher.get_stock_minute(symbol, "15")

        if df is not None and not df.empty:
            print(f"    ✅ 成功: {len(df)} 根K线")
            results.append(True)
        else:
            print(f"    ❌ 失败: 返回 None/Empty")
            results.append(False)

    success_rate = sum(results) / len(results)
    print(f"\n成功率: {sum(results)}/{len(results)} ({success_rate*100:.0f}%)")

    # 分析结果
    if all(results):
        print("✅ 所有品种数据获取成功")
        print("说明: 当前时段 akshare 数据接口正常")
    elif not any(results):
        print("❌ 所有品种数据获取失败")
        print("说明: 可能是 akshare 接口问题或非交易时段")
    else:
        print("⚠️ 部分品种数据获取失败")
        print("说明: 可能是部分品种数据延迟或接口不稳定")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='测试时间相关问题')
    parser.add_argument('--time-analysis', action='store_true', help='只分析时间关系')
    parser.add_argument('--fetch-test', action='store_true', help='只测试数据获取')

    args = parser.parse_args()

    if args.time_analysis:
        analyze_time()
    elif args.fetch_test:
        test_data_fetching_at_current_time()
    else:
        # 默认执行全部
        analyze_time()
        test_data_fetching_at_current_time()
