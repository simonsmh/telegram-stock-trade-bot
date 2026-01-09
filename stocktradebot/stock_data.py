"""
股票/期货数据获取模块
使用akshare获取A股和黄金期货数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


class DataFetcher:
    """数据获取器"""

    @staticmethod
    def get_stock_realtime(symbol: str) -> Optional[dict]:
        """
        获取A股实时行情

        Args:
            symbol: 股票代码，如 "000001" 或 "sh000001"

        Returns:
            包含实时行情的字典
        """
        try:
            # 获取实时行情
            df = ak.stock_zh_a_spot_em()
            # 清理代码格式
            code = symbol.replace("sh", "").replace("sz", "").replace(".", "")
            row = df[df["代码"] == code]
            if row.empty:
                return None
            row = row.iloc[0]
            return {
                "symbol": code,
                "name": row["名称"],
                "price": float(row["最新价"]) if pd.notna(row["最新价"]) else 0,
                "change_pct": float(row["涨跌幅"]) if pd.notna(row["涨跌幅"]) else 0,
                "volume": float(row["成交量"]) if pd.notna(row["成交量"]) else 0,
                "amount": float(row["成交额"]) if pd.notna(row["成交额"]) else 0,
                "high": float(row["最高"]) if pd.notna(row["最高"]) else 0,
                "low": float(row["最低"]) if pd.notna(row["最低"]) else 0,
                "open": float(row["今开"]) if pd.notna(row["今开"]) else 0,
                "prev_close": float(row["昨收"]) if pd.notna(row["昨收"]) else 0,
            }
        except Exception as e:
            print(f"获取股票实时数据失败 {symbol}: {e}")
            return None

    @staticmethod
    def get_stock_history(symbol: str, days: int = 120) -> Optional[pd.DataFrame]:
        """
        获取A股/ETF历史K线数据

        Args:
            symbol: 股票或ETF代码
            days: 获取天数

        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            code = symbol.replace("sh", "").replace("sz", "").replace(".", "")

            # 判断是否为ETF (5开头或1开头的6位代码)
            is_etf = code.startswith("5") or code.startswith("1")

            if is_etf:
                df = ak.fund_etf_hist_em(symbol=code, period="daily", adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")

            if df is None or df.empty:
                return None
            # 统一列名
            df = df.rename(
                columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                }
            )
            df["date"] = pd.to_datetime(df["date"])
            df = df.tail(days)
            return df
        except Exception as e:
            print(f"获取历史数据失败 {symbol}: {e}")
            return None

    @staticmethod
    def get_stock_minute(symbol: str, period: str = "60") -> Optional[pd.DataFrame]:
        """
        获取A股/ETF分钟K线数据

        Args:
            symbol: 股票或ETF代码
            period: 周期，可选 "1", "5", "15", "30", "60"

        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            code = symbol.replace("sh", "").replace("sz", "").replace(".", "")

            # 判断是否为ETF (5开头或1开头的6位代码)
            is_etf = code.startswith("5") or code.startswith("1")

            if is_etf:
                df = ak.fund_etf_hist_min_em(symbol=code, period=period, adjust="qfq")
            else:
                df = ak.stock_zh_a_hist_min_em(symbol=code, period=period, adjust="qfq")

            if df is None or df.empty:
                return None
            # 统一列名
            df = df.rename(
                columns={
                    "时间": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                }
            )
            df["date"] = pd.to_datetime(df["date"])
            return df
        except Exception as e:
            print(f"获取分钟数据失败 {symbol}: {e}")
            return None

    @staticmethod
    def get_gold_futures_realtime(symbol: str = "AU0") -> Optional[dict]:
        """
        获取黄金期货实时行情

        Args:
            symbol: 期货合约代码，如 "AU0"(主力), "AU2406" 等

        Returns:
            包含实时行情的字典
        """
        try:
            df = ak.futures_zh_spot()
            row = df[df["symbol"] == symbol]
            if row.empty:
                # 尝试匹配
                row = df[df["symbol"].str.contains(symbol.upper(), case=False)]
            if row.empty:
                return None
            row = row.iloc[0]
            return {
                "symbol": row["symbol"],
                "name": row.get("name", symbol),
                "price": float(row["current_price"])
                if pd.notna(row.get("current_price"))
                else 0,
                "change_pct": float(row.get("change_percent", 0))
                if pd.notna(row.get("change_percent"))
                else 0,
                "volume": float(row.get("volume", 0))
                if pd.notna(row.get("volume"))
                else 0,
                "high": float(row.get("high", 0)) if pd.notna(row.get("high")) else 0,
                "low": float(row.get("low", 0)) if pd.notna(row.get("low")) else 0,
                "open": float(row.get("open", 0)) if pd.notna(row.get("open")) else 0,
            }
        except Exception as e:
            print(f"获取期货实时数据失败 {symbol}: {e}")
            return None

    @staticmethod
    def get_gold_futures_history(
        symbol: str = "AU0", days: int = 120
    ) -> Optional[pd.DataFrame]:
        """
        获取黄金期货历史K线数据

        Args:
            symbol: 期货合约代码
            days: 获取天数

        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            df = ak.futures_zh_daily_sina(symbol=symbol)
            if df.empty:
                return None
            df = df.rename(
                columns={
                    "date": "date",
                    "open": "open",
                    "close": "close",
                    "high": "high",
                    "low": "low",
                    "volume": "volume",
                }
            )
            df["date"] = pd.to_datetime(df["date"])
            df = df.tail(days)
            return df
        except Exception as e:
            print(f"获取期货历史数据失败 {symbol}: {e}")
            return None

    @staticmethod
    def get_futures_minute(symbol: str, period: str = "60") -> Optional[pd.DataFrame]:
        """
        获取期货分钟K线数据

        Args:
            symbol: 期货合约代码，如 "AU2606"
            period: 周期，可选 "1", "5", "15", "30", "60"

        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            df = ak.futures_zh_minute_sina(symbol=symbol, period=period)
            if df.empty:
                return None
            df["date"] = pd.to_datetime(df["datetime"])
            return df
        except Exception as e:
            print(f"获取期货分钟数据失败 {symbol}: {e}")
            return None

    @staticmethod
    def get_gold_spot_daily(symbol: str = "Au99.99") -> Optional[pd.DataFrame]:
        """
        获取上海黄金交易所现货日线数据

        Args:
            symbol: 品种代码，如 "Au99.99" (即AU9999)

        Returns:
            包含OHLC数据的DataFrame
        """
        try:
            df = ak.spot_hist_sge(symbol=symbol)
            if df.empty:
                return None
            df["date"] = pd.to_datetime(df["date"])
            return df
        except Exception as e:
            print(f"获取黄金现货数据失败 {symbol}: {e}")
            return None

    @staticmethod
    def get_gold_spot_minute(symbol: str = "Au99.99") -> Optional[pd.DataFrame]:
        """
        获取上海黄金交易所现货分钟级数据

        Args:
            symbol: 品种代码，如 "Au99.99" (即AU9999)

        Returns:
            包含分钟价格的DataFrame（当日数据）

        Note:
            此接口返回当日分钟级tick数据，非交易时段数据不完整
        """
        try:
            df = ak.spot_quotations_sge(symbol=symbol)
            if df.empty:
                return None

            # 解析更新时间获取日期
            update_time = df["更新时间"].iloc[0]
            date_str = (
                update_time.split(" ")[0]
                .replace("年", "-")
                .replace("月", "-")
                .replace("日", "")
            )

            # 时间列可能是 datetime.time 类型
            df["time_str"] = df["时间"].astype(str)
            df["date"] = pd.to_datetime(date_str + " " + df["time_str"])
            df = df.rename(columns={"现价": "close"})

            return df
        except Exception as e:
            print(f"获取黄金现货分钟数据失败 {symbol}: {e}")
            return None

    def get_futures_realtime(self, symbol: str) -> Optional[dict]:
        """获取期货实时行情（通用方法）"""
        return self.get_gold_futures_realtime(symbol)

    def get_realtime(self, symbol: str, item_type: str = "stock") -> Optional[dict]:
        """获取实时行情（自动判断类型）"""
        if item_type == "futures" or symbol.upper().startswith("AU"):
            return self.get_gold_futures_realtime(symbol)
        return self.get_stock_realtime(symbol)

    def get_history(
        self, symbol: str, item_type: str = "stock", days: int = 120
    ) -> Optional[pd.DataFrame]:
        """获取历史数据（自动判断类型）"""
        if item_type == "futures" or symbol.upper().startswith("AU"):
            return self.get_gold_futures_history(symbol, days)
        return self.get_stock_history(symbol, days)
