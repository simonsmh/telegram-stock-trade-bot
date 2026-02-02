"""
对比测试：单测方式 vs check_task 方式
"""
import sys
import os
import asyncio
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stocktradebot.stock_data import DataFetcher
from stocktradebot.config import ConfigManager, MonitorTask
from stocktradebot.bot import StockBot


async def test_method_1_direct():
    """方法1：单测方式 - 直接调用"""
    print("\n" + "="*60)
    print("方法1: 单测方式 - 直接调用 DataFetcher")
    print("="*60)

    symbol = "601288"
    period = "15"

    print(f"创建 DataFetcher 实例...")
    fetcher = DataFetcher()

    print(f"调用 fetcher.get_stock_minute('{symbol}', '{period}')...")
    start = time.time()

    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, fetcher.get_stock_minute, symbol, period)

    elapsed = time.time() - start

    if df is not None and not df.empty:
        print(f"✅ 成功 ({elapsed:.2f}s): {len(df)} 根K线")
        return True
    else:
        print(f"❌ 失败 ({elapsed:.2f}s): 返回 None/Empty")
        return False


async def test_method_2_monitor():
    """方法2：使用 StockMonitor"""
    print("\n" + "="*60)
    print("方法2: StockMonitor 方式")
    print("="*60)

    # 创建 mock bot
    class MockBot:
        async def send_alert(self, chat_id, message):
            pass

    mock_bot = MockBot()
    config = ConfigManager()

    # 直接导入 StockMonitor
    from stocktradebot.__main__ import StockMonitor
    monitor = StockMonitor(mock_bot, config)

    # 创建任务
    task = MonitorTask(
        task_id="601288_15min_MACD_COMBO",
        symbol="601288",
        name="农业银行",
        period="15min",
        indicator="MACD_COMBO",
        enabled=True,
        last_signal="",
        params={}
    )

    print(f"调用 monitor.get_data_for_task()...")
    start = time.time()

    try:
        df = await monitor.get_data_for_task(task)
        elapsed = time.time() - start

        if df is not None and not df.empty:
            print(f"✅ 成功 ({elapsed:.2f}s): {len(df)} 根K线")
            return True
        else:
            print(f"❌ 失败 ({elapsed:.2f}s): 返回 None/Empty")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


async def test_method_3_check_task():
    """方法3：完整调用 check_task"""
    print("\n" + "="*60)
    print("方法3: 完整 check_task 流程")
    print("="*60)

    class MockBot:
        async def send_alert(self, chat_id, message):
            print(f"  [MockBot] 发送消息: {message[:50]}...")

    mock_bot = MockBot()
    config = ConfigManager()

    from stocktradebot.__main__ import StockMonitor
    monitor = StockMonitor(mock_bot, config)

    task = MonitorTask(
        task_id="601288_15min_MACD_COMBO",
        symbol="601288",
        name="农业银行",
        period="15min",
        indicator="MACD_COMBO",
        enabled=True,
        last_signal="",
        params={}
    )

    print(f"调用 monitor.check_task()...")
    start = time.time()

    try:
        await monitor.check_task(123456789, task)
        elapsed = time.time() - start
        print(f"✅ check_task 完成 ({elapsed:.2f}s)")
        return True
    except Exception as e:
        print(f"❌ check_task 异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有对比测试"""
    print("="*60)
    print("对比测试: 单测方式 vs check_task 方式")
    print("="*60)

    results = {}

    # 方法1: 单测方式
    results["单测方式"] = await test_method_1_direct()

    # 方法2: StockMonitor
    results["StockMonitor"] = await test_method_2_monitor()

    # 方法3: 完整 check_task
    results["check_task"] = await test_method_3_check_task()

    # 汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {name}: {status}")

    # 分析
    print("\n" + "="*60)
    print("差异分析")
    print("="*60)

    if results["单测方式"] and not results["StockMonitor"]:
        print("结论: 单测成功但 StockMonitor 失败")
        print("可能原因:")
        print("  - StockMonitor 实例的 data_fetcher 状态问题")
        print("  - 请求间隔/频率不同")
        print("  - 某些初始化逻辑差异")
    elif not results["单测方式"]:
        print("结论: 所有方式都失败")
        print("说明: akshare 接口当前不可用或限流")
        print("建议: 稍后重试或检查网络连接")
    else:
        print("结论: 所有方式都成功")
        print("说明: 当前环境无法复现问题")
        print("建议: 在实际运行环境中添加详细日志调试")


if __name__ == "__main__":
    asyncio.run(main())
