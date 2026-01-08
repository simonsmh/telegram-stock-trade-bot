"""
沪金 AU9999 回测工具（使用上海黄金交易所分钟数据）
"""
import akshare as ak
import pandas as pd
from indicators import TechnicalIndicators


def get_au9999_minute_data():
    """
    获取AU9999分钟级实时数据
    使用 spot_quotations_sge 接口
    """
    df = ak.spot_quotations_sge(symbol="Au99.99")
    
    # 解析更新时间获取日期
    update_time = df["更新时间"].iloc[0]  # 如 "2026年01月08日 00:02:51"
    date_str = update_time.split(" ")[0].replace("年", "-").replace("月", "-").replace("日", "")
    
    # 时间列可能是 datetime.time 类型，需要转换为字符串
    df["time_str"] = df["时间"].astype(str)
    df["date"] = pd.to_datetime(date_str + " " + df["time_str"])
    df = df.rename(columns={"现价": "close"})
    
    return df


def resample_to_60min(df: pd.DataFrame) -> pd.DataFrame:
    """将分钟数据重采样为60分钟K线"""
    df = df.set_index("date")
    
    # 重采样为60分钟
    ohlc = df["close"].resample("60min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last"
    }).dropna()
    
    ohlc = ohlc.reset_index()
    return ohlc


def get_au9999_daily():
    """获取AU9999日线历史数据"""
    df = ak.spot_hist_sge(symbol="Au99.99")
    df["date"] = pd.to_datetime(df["date"])
    return df


def detect_macd_signals(df: pd.DataFrame, last_n: int = None):
    """检测MACD金叉/死叉信号"""
    macd_df = TechnicalIndicators.calculate_macd(df)
    
    signals = []
    start = len(df) - last_n if last_n else 1
    
    for i in range(max(1, start), len(df)):
        time_str = df["date"].iloc[i].strftime("%Y-%m-%d %H:%M")
        
        prev_dif = macd_df["dif"].iloc[i-1]
        prev_dea = macd_df["dea"].iloc[i-1]
        curr_dif = macd_df["dif"].iloc[i]
        curr_dea = macd_df["dea"].iloc[i]
        
        if prev_dif <= prev_dea and curr_dif > curr_dea:
            signals.append({
                "type": "金叉",
                "time": time_str,
                "dif": curr_dif,
                "dea": curr_dea,
                "macd": macd_df["macd"].iloc[i]
            })
        
        if prev_dif >= prev_dea and curr_dif < curr_dea:
            signals.append({
                "type": "死叉",
                "time": time_str,
                "dif": curr_dif,
                "dea": curr_dea,
                "macd": macd_df["macd"].iloc[i]
            })
    
    return signals, macd_df


def main():
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "60min"
    
    print("=" * 60)
    print(f"沪金 Au99.99 (AU9999) MACD 回测")
    print("=" * 60)
    
    if mode == "daily":
        print("\n📊 日线回测")
        df = get_au9999_daily()
        signals, macd_df = detect_macd_signals(df, last_n=50)
        signals = signals[-10:]  # 最近10个信号
    else:
        print("\n📊 60分钟线回测（今日分钟数据）")
        print("注：数据来自上海黄金交易所实时行情")
        
        minute_df = get_au9999_minute_data()
        print(f"获取到 {len(minute_df)} 条分钟数据")
        
        if len(minute_df) < 60:
            print("⚠️ 分钟数据不足60条，无法生成60分钟K线")
            print("（可能是非交易时段或刚开盘）")
            print("\n切换到日线模式...")
            df = get_au9999_daily()
            signals, macd_df = detect_macd_signals(df, last_n=50)
            signals = signals[-10:]
        else:
            df = resample_to_60min(minute_df)
            print(f"生成 {len(df)} 根60分钟K线")
            signals, macd_df = detect_macd_signals(df)
    
    print(f"\n数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"共 {len(df)} 根K线\n")
    
    print("-" * 50)
    if signals:
        print(f"发现 {len(signals)} 个MACD交叉信号:\n")
        for sig in signals:
            emoji = "📈" if sig["type"] == "金叉" else "📉"
            print(f"{emoji} {sig['type']} @ {sig['time']}")
            print(f"   DIF: {sig['dif']:.4f}, DEA: {sig['dea']:.4f}, MACD: {sig['macd']:.4f}")
    else:
        print("未发现MACD交叉信号")
    
    print("\n" + "-" * 50)
    print("当前MACD状态:")
    print(f"时间: {df['date'].iloc[-1]}")
    print(f"DIF:  {macd_df['dif'].iloc[-1]:.4f}")
    print(f"DEA:  {macd_df['dea'].iloc[-1]:.4f}")
    print(f"MACD: {macd_df['macd'].iloc[-1]:.4f}")
    status = "多头 📈" if macd_df['dif'].iloc[-1] > macd_df['dea'].iloc[-1] else "空头 📉"
    print(f"趋势: {status}")


if __name__ == "__main__":
    main()
