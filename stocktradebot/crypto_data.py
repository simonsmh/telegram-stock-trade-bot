"""
加密货币数据获取模块
使用OKEx API获取加密货币数据
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CryptoDataFetcher:
    """加密货币数据获取器"""

    def __init__(self):
        self.base_url = "https://www.okx.com/api/v5"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
        )

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """
        标准化加密货币代码

        Args:
            symbol: 原始代码，如 "BTC", "ETH", "BTC-USDT"

        Returns:
            标准化后的代码，如 "BTC-USDT"
        """
        symbol = symbol.upper().strip()

        # 如果已经包含分隔符，直接返回
        if "-" in symbol:
            return symbol

        # 常见币种映射到USDT交易对
        common_pairs = {
            "BTC": "BTC-USDT",
            "ETH": "ETH-USDT",
            "LTC": "LTC-USDT",
            "BCH": "BCH-USDT",
            "XRP": "XRP-USDT",
            "ADA": "ADA-USDT",
            "DOT": "DOT-USDT",
            "LINK": "LINK-USDT",
            "UNI": "UNI-USDT",
            "SOL": "SOL-USDT",
            "DOGE": "DOGE-USDT",
            "SHIB": "SHIB-USDT",
            "MATIC": "MATIC-USDT",
            "AVAX": "AVAX-USDT",
        }

        return common_pairs.get(symbol, f"{symbol}-USDT")

    def get_crypto_realtime(self, symbol: str) -> Optional[dict]:
        """
        获取加密货币实时行情

        Args:
            symbol: 加密货币代码，如 "BTC-USDT" 或 "BTC"

        Returns:
            包含实时行情的字典
        """
        try:
            inst_id = self.normalize_symbol(symbol)
            url = f"{self.base_url}/market/ticker"
            params = {"instId": inst_id}

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "0" or not data.get("data"):
                logger.error(f"OKEx API错误: {data}")
                return None

            ticker_data = data["data"][0]

            return {
                "symbol": inst_id,
                "name": inst_id.split("-")[0],  # 取基础币种名称
                "price": float(ticker_data["last"]),
                "change_pct": float(ticker_data["sodUtc8"])
                if ticker_data.get("sodUtc8")
                else 0,
                "volume": float(ticker_data["vol24h"])
                if ticker_data.get("vol24h")
                else 0,
                "amount": float(ticker_data["volCcy24h"])
                if ticker_data.get("volCcy24h")
                else 0,
                "high": float(ticker_data["high24h"])
                if ticker_data.get("high24h")
                else 0,
                "low": float(ticker_data["low24h"]) if ticker_data.get("low24h") else 0,
                "open": float(ticker_data["open24h"])
                if ticker_data.get("open24h")
                else 0,
                "prev_close": float(ticker_data["open24h"])
                if ticker_data.get("open24h")
                else 0,
            }

        except Exception as e:
            logger.error(f"获取加密货币实时数据失败 {symbol}: {e}")
            return None

    def get_crypto_history(
        self, symbol: str, days: int = 120, period: str = "daily"
    ) -> Optional[pd.DataFrame]:
        """
        获取加密货币历史K线数据

        Args:
            symbol: 加密货币代码，如 "BTC-USDT" 或 "BTC"
            days: 获取天数
            period: 周期，可选 "daily", "hourly", "minutely"

        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            inst_id = self.normalize_symbol(symbol)

            # 周期映射
            period_map = {
                "daily": "1D",
                "hourly": "1H",
                "minutely": "1m",
                "weekly": "1W",
                "monthly": "1M",
            }

            bar = period_map.get(period, "1D")

            url = f"{self.base_url}/market/candles"
            params = {
                "instId": inst_id,
                "bar": bar,
                "limit": min(days, 300),  # OKEx限制最多300条
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "0" or not data.get("data"):
                logger.error(f"OKEx API错误: {data}")
                return None

            # 解析K线数据
            candles = data["data"]
            if not candles:
                return None

            # 转换为DataFrame
            df_data = []
            for candle in candles:
                # OKEx返回格式: [timestamp, open, high, low, close, volume, volume_currency, volume_currency_quote, confirm]
                df_data.append(
                    {
                        "date": pd.to_datetime(int(candle[0]), unit="ms"),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                        "amount": float(candle[6]) if len(candle) > 6 else 0,
                    }
                )

            df = pd.DataFrame(df_data)
            df = df.sort_values("date").reset_index(drop=True)

            return df

        except Exception as e:
            logger.error(f"获取加密货币历史数据失败 {symbol}: {e}")
            return None

    def get_crypto_minute(
        self, symbol: str, period: str = "60"
    ) -> Optional[pd.DataFrame]:
        """
        获取加密货币分钟K线数据

        Args:
            symbol: 加密货币代码
            period: 周期（分钟），可选 "1", "5", "15", "30", "60"

        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            # 分钟周期映射
            minute_map = {
                "1": "1m",
                "5": "5m",
                "15": "15m",
                "30": "30m",
                "60": "1H",
                "240": "4H",
            }

            bar = minute_map.get(period, "1H")
            return self.get_crypto_history(symbol, days=100, period=bar)

        except Exception as e:
            logger.error(f"获取加密货币分钟数据失败 {symbol}: {e}")
            return None

    @staticmethod
    def get_supported_symbols() -> dict[str, dict]:
        """
        获取支持的加密货币列表

        Returns:
            支持的币种信息字典
        """
        return {
            "BTC-USDT": {"name": "Bitcoin", "type": "crypto"},
            "ETH-USDT": {"name": "Ethereum", "type": "crypto"},
            "LTC-USDT": {"name": "Litecoin", "type": "crypto"},
            "BCH-USDT": {"name": "Bitcoin Cash", "type": "crypto"},
            "XRP-USDT": {"name": "Ripple", "type": "crypto"},
            "ADA-USDT": {"name": "Cardano", "type": "crypto"},
            "DOT-USDT": {"name": "Polkadot", "type": "crypto"},
            "LINK-USDT": {"name": "Chainlink", "type": "crypto"},
            "UNI-USDT": {"name": "Uniswap", "type": "crypto"},
            "SOL-USDT": {"name": "Solana", "type": "crypto"},
            "DOGE-USDT": {"name": "Dogecoin", "type": "crypto"},
            "SHIB-USDT": {"name": "Shiba Inu", "type": "crypto"},
            "MATIC-USDT": {"name": "Polygon", "type": "crypto"},
            "AVAX-USDT": {"name": "Avalanche", "type": "crypto"},
        }

    def get_realtime(self, symbol: str) -> Optional[dict]:
        """获取实时行情（通用方法）"""
        return self.get_crypto_realtime(symbol)

    def get_history(
        self, symbol: str, days: int = 120, period: str = "daily"
    ) -> Optional[pd.DataFrame]:
        """获取历史数据（通用方法）"""
        return self.get_crypto_history(symbol, days, period)
