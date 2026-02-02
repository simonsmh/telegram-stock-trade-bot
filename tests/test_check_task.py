"""
Test check_task method directly
直接执行 check_task 方法测试
"""
import sys
import os
import asyncio
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stocktradebot.config import ConfigManager, MonitorTask
from stocktradebot.bot import StockBot
from stocktradebot.__main__ import StockMonitor

# 设置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


async def test_check_task_directly():
    """直接测试 check_task 方法"""
    print("\n" + "="*60)
    print("直接测试 check_task 方法")
    print("="*60)

    # 创建 mock 对象
    config = ConfigManager()

    # 创建一个测试任务
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

    print(f"\n测试任务:")
    print(f"  task_id: {task.task_id}")
    print(f"  symbol: {task.symbol}")
    print(f"  period: {task.period}")
    print(f"  indicator: {task.indicator}")

    # 直接调用 get_data_for_task
    print("\n" + "-"*60)
    print("步骤1: 直接调用 get_data_for_task")
    print("-"*60)

    # 创建 mock bot
    class MockBot:
        async def send_alert(self, chat_id, message):
            print(f"[MockBot] send_alert called: chat_id={chat_id}")

    mock_bot = MockBot()
    monitor = StockMonitor(mock_bot, config)

    try:
        df = await monitor.get_data_for_task(task)
        if df is not None and not df.empty:
            print(f"✅ 数据获取成功: {len(df)} 条")
            print(f"   数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
        else:
            print(f"❌ 数据获取失败: df is None or empty")
    except Exception as e:
        print(f"❌ 数据获取异常: {e}")
        import traceback
        traceback.print_exc()

    # 调用 check_task 完整流程
    print("\n" + "-"*60)
    print("步骤2: 调用完整 check_task 流程")
    print("-"*60)

    chat_id = 123456789  # mock chat_id

    try:
        await monitor.check_task(chat_id, task)
        print("✅ check_task 执行完成")
    except Exception as e:
        print(f"❌ check_task 异常: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_check_task_directly())
