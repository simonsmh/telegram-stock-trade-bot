"""
技术指标计算模块
计算MA、MACD、KDJ等技术指标
"""
import pandas as pd
import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class MAData:
    """均线数据"""
    ma5: float
    ma10: float
    ma20: float
    ma60: float
    price: float


@dataclass
class MACDData:
    """MACD数据"""
    dif: float  # 快线
    dea: float  # 慢线
    macd: float  # 柱状图 (DIF - DEA) * 2
    prev_dif: float
    prev_dea: float


@dataclass
class KDJData:
    """KDJ数据"""
    k: float
    d: float
    j: float
    prev_k: float
    prev_d: float


class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_ma(df: pd.DataFrame, periods: list[int] = [5, 10, 20, 60]) -> dict[int, pd.Series]:
        """
        计算移动平均线
        
        Args:
            df: 包含close列的DataFrame
            periods: 均线周期列表
        
        Returns:
            各周期均线的字典
        """
        result = {}
        for period in periods:
            result[period] = df["close"].rolling(window=period).mean()
        return result
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        计算MACD指标
        
        Args:
            df: 包含close列的DataFrame
            fast: 快速EMA周期
            slow: 慢速EMA周期
            signal: 信号线周期
        
        Returns:
            包含DIF, DEA, MACD列的DataFrame
        """
        close = df["close"]
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd = (dif - dea) * 2
        
        result = pd.DataFrame({
            "dif": dif,
            "dea": dea,
            "macd": macd
        })
        return result
    
    @staticmethod
    def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """
        计算KDJ指标
        
        Args:
            df: 包含high, low, close列的DataFrame
            n: RSV周期
            m1: K线平滑周期
            m2: D线平滑周期
        
        Returns:
            包含K, D, J列的DataFrame
        """
        low_min = df["low"].rolling(window=n).min()
        high_max = df["high"].rolling(window=n).max()
        
        rsv = (df["close"] - low_min) / (high_max - low_min) * 100
        rsv = rsv.fillna(50)
        
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        result = pd.DataFrame({
            "k": k,
            "d": d,
            "j": j
        })
        return result
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算RSI指标
        
        Args:
            df: 包含close列的DataFrame
            period: RSI周期，默认14
        
        Returns:
            包含rsi列的DataFrame
        """
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)
        
        return pd.DataFrame({"rsi": rsi})
    
    @staticmethod
    def get_latest_indicators(df: pd.DataFrame) -> dict:
        """
        获取最新的所有指标数据
        
        Args:
            df: K线数据DataFrame
        
        Returns:
            包含所有指标的字典
        """
        if df is None or len(df) < 60:
            return None
        
        # 均线
        ma_dict = TechnicalIndicators.calculate_ma(df)
        latest_ma = MAData(
            ma5=ma_dict[5].iloc[-1],
            ma10=ma_dict[10].iloc[-1],
            ma20=ma_dict[20].iloc[-1],
            ma60=ma_dict[60].iloc[-1],
            price=df["close"].iloc[-1]
        )
        
        # MACD
        macd_df = TechnicalIndicators.calculate_macd(df)
        latest_macd = MACDData(
            dif=macd_df["dif"].iloc[-1],
            dea=macd_df["dea"].iloc[-1],
            macd=macd_df["macd"].iloc[-1],
            prev_dif=macd_df["dif"].iloc[-2],
            prev_dea=macd_df["dea"].iloc[-2]
        )
        
        # KDJ
        kdj_df = TechnicalIndicators.calculate_kdj(df)
        latest_kdj = KDJData(
            k=kdj_df["k"].iloc[-1],
            d=kdj_df["d"].iloc[-1],
            j=kdj_df["j"].iloc[-1],
            prev_k=kdj_df["k"].iloc[-2],
            prev_d=kdj_df["d"].iloc[-2]
        )
        
        # 成交量对比
        if "volume" in df.columns:
            vol_ma5 = df["volume"].rolling(window=5).mean().iloc[-1]
            current_vol = df["volume"].iloc[-1]
            volume_ratio = current_vol / vol_ma5 if vol_ma5 > 0 else 1
        else:
            volume_ratio = 1
        
        return {
            "ma": latest_ma,
            "macd": latest_macd,
            "kdj": latest_kdj,
            "volume_ratio": volume_ratio,
            "close": df["close"].iloc[-1],
            "prev_close": df["close"].iloc[-2]
        }
