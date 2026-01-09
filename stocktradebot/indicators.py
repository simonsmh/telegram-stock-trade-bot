"""
技术指标计算模块
计算MA、MACD、KDJ等技术指标
"""
import pandas as pd
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


@dataclass
class DivergenceData:
    """背离数据"""
    divergence_type: str  # "顶背离" | "底背离" | None
    indicator_name: str  # "MACD" | "KDJ"
    price_peak1: float  # 第一个价格极值点
    price_peak2: float  # 第二个价格极值点
    indicator_peak1: float  # 第一个指标极值点
    indicator_peak2: float  # 第二个指标极值点
    peak1_idx: int  # 第一个极值点索引
    peak2_idx: int  # 第二个极值点索引
    strength: float  # 背离强度 (0-100)


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
    
    @staticmethod
    def find_peaks(series: pd.Series, order: int = 5) -> tuple[list, list]:
        """
        找出序列中的局部高点和低点
        
        Args:
            series: 数据序列
            order: 比较的邻近点数量
        
        Returns:
            (高点索引列表, 低点索引列表)
        """
        peaks = []
        valleys = []
        
        for i in range(order, len(series) - order):
            # 检查是否为局部高点
            is_peak = True
            for j in range(1, order + 1):
                if series.iloc[i] <= series.iloc[i - j] or series.iloc[i] <= series.iloc[i + j]:
                    is_peak = False
                    break
            if is_peak:
                peaks.append(i)
            
            # 检查是否为局部低点
            is_valley = True
            for j in range(1, order + 1):
                if series.iloc[i] >= series.iloc[i - j] or series.iloc[i] >= series.iloc[i + j]:
                    is_valley = False
                    break
            if is_valley:
                valleys.append(i)
        
        return peaks, valleys
    
    @staticmethod
    def detect_macd_divergence(df: pd.DataFrame, lookback: int = 60) -> list[DivergenceData]:
        """
        检测MACD背离
        
        Args:
            df: K线数据DataFrame
            lookback: 回溯周期数
        
        Returns:
            检测到的背离列表
        """
        if len(df) < lookback:
            return []
        
        # 只分析最近的数据
        df_subset = df.tail(lookback).reset_index(drop=True)
        macd_df = TechnicalIndicators.calculate_macd(df_subset)
        
        # 使用MACD柱状图 (而非DIF) 进行背离检测
        macd_series = macd_df["macd"]
        price_series = df_subset["close"]
        
        # 找出高点和低点
        price_peaks, price_valleys = TechnicalIndicators.find_peaks(price_series, order=3)
        macd_peaks, macd_valleys = TechnicalIndicators.find_peaks(macd_series, order=3)
        
        divergences = []
        
        # 检测顶背离：价格创新高，但MACD未创新高
        if len(price_peaks) >= 2 and len(macd_peaks) >= 2:
            # 取最近两个高点
            p1, p2 = price_peaks[-2], price_peaks[-1]
            
            # 找到对应时间范围内的MACD高点
            m_peaks_in_range = [m for m in macd_peaks if m >= p1 - 5 and m <= p2 + 5]
            if len(m_peaks_in_range) >= 2:
                m1, m2 = m_peaks_in_range[-2], m_peaks_in_range[-1]
                
                price_higher = price_series.iloc[p2] > price_series.iloc[p1]
                macd_lower = macd_series.iloc[m2] < macd_series.iloc[m1]
                
                if price_higher and macd_lower:
                    # 计算背离强度
                    price_diff_pct = (price_series.iloc[p2] - price_series.iloc[p1]) / price_series.iloc[p1] * 100
                    macd_diff_pct = (macd_series.iloc[m1] - macd_series.iloc[m2]) / abs(macd_series.iloc[m1]) * 100 if macd_series.iloc[m1] != 0 else 0
                    strength = min(100, (price_diff_pct + macd_diff_pct) * 10)
                    
                    divergences.append(DivergenceData(
                        divergence_type="顶背离",
                        indicator_name="MACD",
                        price_peak1=price_series.iloc[p1],
                        price_peak2=price_series.iloc[p2],
                        indicator_peak1=macd_series.iloc[m1],
                        indicator_peak2=macd_series.iloc[m2],
                        peak1_idx=p1 + len(df) - lookback,
                        peak2_idx=p2 + len(df) - lookback,
                        strength=strength
                    ))
        
        # 检测底背离：价格创新低，但MACD未创新低
        if len(price_valleys) >= 2 and len(macd_valleys) >= 2:
            # 取最近两个低点
            p1, p2 = price_valleys[-2], price_valleys[-1]
            
            # 找到对应时间范围内的MACD低点
            m_valleys_in_range = [m for m in macd_valleys if m >= p1 - 5 and m <= p2 + 5]
            if len(m_valleys_in_range) >= 2:
                m1, m2 = m_valleys_in_range[-2], m_valleys_in_range[-1]
                
                price_lower = price_series.iloc[p2] < price_series.iloc[p1]
                macd_higher = macd_series.iloc[m2] > macd_series.iloc[m1]
                
                if price_lower and macd_higher:
                    # 计算背离强度
                    price_diff_pct = (price_series.iloc[p1] - price_series.iloc[p2]) / price_series.iloc[p1] * 100
                    macd_diff_pct = (macd_series.iloc[m2] - macd_series.iloc[m1]) / abs(macd_series.iloc[m1]) * 100 if macd_series.iloc[m1] != 0 else 0
                    strength = min(100, (price_diff_pct + macd_diff_pct) * 10)
                    
                    divergences.append(DivergenceData(
                        divergence_type="底背离",
                        indicator_name="MACD",
                        price_peak1=price_series.iloc[p1],
                        price_peak2=price_series.iloc[p2],
                        indicator_peak1=macd_series.iloc[m1],
                        indicator_peak2=macd_series.iloc[m2],
                        peak1_idx=p1 + len(df) - lookback,
                        peak2_idx=p2 + len(df) - lookback,
                        strength=strength
                    ))
        
        return divergences
    
    @staticmethod
    def detect_kdj_divergence(df: pd.DataFrame, lookback: int = 60) -> list[DivergenceData]:
        """
        检测KDJ背离（使用J值）
        
        Args:
            df: K线数据DataFrame
            lookback: 回溯周期数
        
        Returns:
            检测到的背离列表
        """
        if len(df) < lookback:
            return []
        
        # 只分析最近的数据
        df_subset = df.tail(lookback).reset_index(drop=True)
        kdj_df = TechnicalIndicators.calculate_kdj(df_subset)
        
        # 使用J值进行背离检测
        j_series = kdj_df["j"]
        price_series = df_subset["close"]
        
        # 找出高点和低点
        price_peaks, price_valleys = TechnicalIndicators.find_peaks(price_series, order=3)
        j_peaks, j_valleys = TechnicalIndicators.find_peaks(j_series, order=3)
        
        divergences = []
        
        # 检测顶背离：价格创新高，但J值未创新高
        if len(price_peaks) >= 2 and len(j_peaks) >= 2:
            p1, p2 = price_peaks[-2], price_peaks[-1]
            
            j_peaks_in_range = [j for j in j_peaks if j >= p1 - 5 and j <= p2 + 5]
            if len(j_peaks_in_range) >= 2:
                j1, j2 = j_peaks_in_range[-2], j_peaks_in_range[-1]
                
                price_higher = price_series.iloc[p2] > price_series.iloc[p1]
                j_lower = j_series.iloc[j2] < j_series.iloc[j1]
                
                if price_higher and j_lower:
                    price_diff_pct = (price_series.iloc[p2] - price_series.iloc[p1]) / price_series.iloc[p1] * 100
                    j_diff_pct = (j_series.iloc[j1] - j_series.iloc[j2]) / abs(j_series.iloc[j1]) * 100 if j_series.iloc[j1] != 0 else 0
                    strength = min(100, (price_diff_pct + j_diff_pct) * 5)
                    
                    divergences.append(DivergenceData(
                        divergence_type="顶背离",
                        indicator_name="KDJ",
                        price_peak1=price_series.iloc[p1],
                        price_peak2=price_series.iloc[p2],
                        indicator_peak1=j_series.iloc[j1],
                        indicator_peak2=j_series.iloc[j2],
                        peak1_idx=p1 + len(df) - lookback,
                        peak2_idx=p2 + len(df) - lookback,
                        strength=strength
                    ))
        
        # 检测底背离：价格创新低，但J值未创新低
        if len(price_valleys) >= 2 and len(j_valleys) >= 2:
            p1, p2 = price_valleys[-2], price_valleys[-1]
            
            j_valleys_in_range = [j for j in j_valleys if j >= p1 - 5 and j <= p2 + 5]
            if len(j_valleys_in_range) >= 2:
                j1, j2 = j_valleys_in_range[-2], j_valleys_in_range[-1]
                
                price_lower = price_series.iloc[p2] < price_series.iloc[p1]
                j_higher = j_series.iloc[j2] > j_series.iloc[j1]
                
                if price_lower and j_higher:
                    price_diff_pct = (price_series.iloc[p1] - price_series.iloc[p2]) / price_series.iloc[p1] * 100
                    j_diff_pct = (j_series.iloc[j2] - j_series.iloc[j1]) / abs(j_series.iloc[j1]) * 100 if j_series.iloc[j1] != 0 else 0
                    strength = min(100, (price_diff_pct + j_diff_pct) * 5)
                    
                    divergences.append(DivergenceData(
                        divergence_type="底背离",
                        indicator_name="KDJ",
                        price_peak1=price_series.iloc[p1],
                        price_peak2=price_series.iloc[p2],
                        indicator_peak1=j_series.iloc[j1],
                        indicator_peak2=j_series.iloc[j2],
                        peak1_idx=p1 + len(df) - lookback,
                        peak2_idx=p2 + len(df) - lookback,
                        strength=strength
                    ))
        
        return divergences
    
    @staticmethod
    def detect_all_divergences(df: pd.DataFrame, lookback: int = 60) -> dict:
        """
        检测所有背离
        
        Returns:
            {"macd": [...], "kdj": [...]}
        """
        return {
            "macd": TechnicalIndicators.detect_macd_divergence(df, lookback),
            "kdj": TechnicalIndicators.detect_kdj_divergence(df, lookback)
        }

