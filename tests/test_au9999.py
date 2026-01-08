"""快速回测沪金60分钟线MACD"""
import akshare as ak
import pandas as pd
from indicators import TechnicalIndicators

# 获取当前可用的期货合约
symbol = "AU2606"  # 2026年06月交割的黄金期货

print(f"获取 {symbol} 60分钟数据...")
try:
    df = ak.futures_zh_minute_sina(symbol=symbol, period="60")
    df["date"] = pd.to_datetime(df["datetime"])
    
    print(f"数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"共 {len(df)} 根K线\n")
    
    # 计算MACD
    macd_df = TechnicalIndicators.calculate_macd(df)
    
    # 检测今天(2026-01-07)的信号
    today = "2026-01-07"
    print(f"今天({today})的MACD交叉信号:")
    print("-" * 40)
    
    found = False
    for i in range(1, len(df)):
        date_str = df['date'].iloc[i].strftime("%Y-%m-%d")
        if date_str != today:
            continue
            
        prev_dif = macd_df["dif"].iloc[i-1]
        prev_dea = macd_df["dea"].iloc[i-1]
        curr_dif = macd_df["dif"].iloc[i]
        curr_dea = macd_df["dea"].iloc[i]
        time_str = df['date'].iloc[i].strftime("%Y-%m-%d %H:%M")
        
        if prev_dif <= prev_dea and curr_dif > curr_dea:
            print(f"📈 金叉 @ {time_str}")
            print(f"   DIF: {curr_dif:.4f}, DEA: {curr_dea:.4f}, MACD: {macd_df['macd'].iloc[i]:.4f}")
            found = True
        if prev_dif >= prev_dea and curr_dif < curr_dea:
            print(f"📉 死叉 @ {time_str}")
            print(f"   DIF: {curr_dif:.4f}, DEA: {curr_dea:.4f}, MACD: {macd_df['macd'].iloc[i]:.4f}")
            found = True
    
    if not found:
        print("今天无MACD交叉信号")
    
    print("\n" + "-" * 40)
    print("当前MACD状态:")
    print(f"最新时间: {df['date'].iloc[-1]}")
    print(f"DIF: {macd_df['dif'].iloc[-1]:.4f}")
    print(f"DEA: {macd_df['dea'].iloc[-1]:.4f}")
    print(f"MACD: {macd_df['macd'].iloc[-1]:.4f}")
    status = "多头(DIF>DEA)" if macd_df['dif'].iloc[-1] > macd_df['dea'].iloc[-1] else "空头(DIF<DEA)"
    print(f"状态: {status}")
    
except Exception as e:
    print(f"获取数据失败: {e}")
