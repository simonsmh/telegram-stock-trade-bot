"""
Test task status display for 159363_5min_KDJ_COMBO
"""
import sys
sys.path.insert(0, 'd:/Projects/stockTradeBot')

from stocktradebot.stock_data import DataFetcher
from stocktradebot.indicators import TechnicalIndicators


def test_159363_5min_kdj():
    """测试 159363 5分钟 KDJ 信号检测"""
    symbol = "159363"
    period = "5"  # 5分钟
    
    print(f"\n{'='*60}")
    print(f"测试: {symbol} {period}分钟线 KDJ 指标")
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
    
    # 2. 计算 KDJ 指标
    kdj_df = TechnicalIndicators.calculate_kdj(df)
    print(f"\n当前 KDJ 值:")
    print(f"  K: {kdj_df['k'].iloc[-1]:.2f}")
    print(f"  D: {kdj_df['d'].iloc[-1]:.2f}")
    print(f"  J: {kdj_df['j'].iloc[-1]:.2f}")
    
    # 3. 检测 KDJ 金叉死叉信号
    signals = []
    for i in range(1, len(df)):
        prev_k = kdj_df["k"].iloc[i - 1]
        prev_d = kdj_df["d"].iloc[i - 1]
        curr_k = kdj_df["k"].iloc[i]
        curr_d = kdj_df["d"].iloc[i]
        time_str = df["date"].iloc[i].strftime("%Y-%m-%d %H:%M")
        price = df["close"].iloc[i]

        if prev_k <= prev_d and curr_k > curr_d:
            signals.append({"type": "金叉", "time": time_str, "price": price})
        if prev_k >= prev_d and curr_k < curr_d:
            signals.append({"type": "死叉", "time": time_str, "price": price})
    
    print(f"\n{'='*60}")
    print(f"检测到 {len(signals)} 个 KDJ 信号")
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
        
        # 调试 - 打印最后几个 K 和 D 值
        print("\n调试 - 最后 10 根K线的 K/D 值:")
        for i in range(-10, 0):
            k = kdj_df['k'].iloc[i]
            d = kdj_df['d'].iloc[i]
            time_str = df['date'].iloc[i].strftime("%Y-%m-%d %H:%M")
            status = "K>D" if k > d else "K<D"
            print(f"  {time_str}: K={k:.2f}, D={d:.2f} ({status})")


if __name__ == "__main__":
    test_159363_5min_kdj()
    
    # 测试完整的 _get_task_status 逻辑
    print(f"\n\n{'='*60}")
    print("测试完整的 _get_task_status 逻辑")
    print(f"{'='*60}")
    
    from stocktradebot.bot import StockBot
    from stocktradebot.config import ConfigManager
    
    # 创建模拟任务对象
    class MockTask:
        def __init__(self):
            self.symbol = "159363"
            self.period = "5min"
            self.indicator = "KDJ_COMBO"
            self.task_id = "159363_5min_KDJ_COMBO"
            self.params = {"window": 5}
            self.name = "创业板人工智能ETF华宝"
            self.enabled = True
    
    # 创建 bot 实例（不需要真实 token）
    config = ConfigManager()  
    bot = StockBot(token="fake_token", config_manager=config)
    
    task = MockTask()
    status = bot._get_task_status(task)
    
    print(f"任务: {task.task_id}")
    print(f"趋势: {status['trend']}")
    print(f"最近信号: {status['last_signal']}")
    print(f"信号时间: {status['last_signal_time']}")
    print(f"信号价格: {status['last_signal_price']}")
    print(f"当前价格: {status['current_price']}")
    print(f"指标值: {status['indicator_values']}")
    
    # 测试 601288_15min_MACD_COMBO
    print(f"\n\n{'='*60}")
    print("测试 601288_15min_MACD_COMBO")
    print(f"{'='*60}")
    
    class MockTask2:
        def __init__(self):
            self.symbol = "601288"
            self.period = "15min"
            self.indicator = "MACD_COMBO"
            self.task_id = "601288_15min_MACD_COMBO"
            self.params = {"window": 2}
            self.name = "农业银行"
            self.enabled = True
    
    task2 = MockTask2()
    
    # 先测试数据获取
    print(f"\n1. 测试数据获取:")
    df2 = bot._get_backtest_data(task2.symbol, task2.period)
    if df2 is None:
        print(f"❌ 数据获取失败!")
    else:
        print(f"✅ 数据获取成功: {len(df2)} 根K线")
        print(f"数据范围: {df2['date'].iloc[0]} ~ {df2['date'].iloc[-1]}")
    
    # 测试完整状态获取
    print(f"\n2. 测试 _get_task_status:")
    status2 = bot._get_task_status(task2)
    
    print(f"任务: {task2.task_id}")
    print(f"趋势: {status2['trend']}")
    print(f"最近信号: {status2['last_signal']}")
    print(f"信号时间: {status2['last_signal_time']}")
    print(f"信号价格: {status2['last_signal_price']}")
    print(f"当前价格: {status2['current_price']}")
    print(f"指标值: {status2['indicator_values']}")
