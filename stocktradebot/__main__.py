"""
Stock Trade Bot - 主程序入口
股票/期货技术指标监控Telegram Bot
"""

import os
import sys
import asyncio
import logging
import traceback
from datetime import datetime

import pytz

from stocktradebot.config import (
    ConfigManager,
    get_bot_token,
    get_poll_interval,
    PERIOD_TYPES,
    MonitorTask,
)
from stocktradebot.stock_data import DataFetcher
from stocktradebot.crypto_data import CryptoDataFetcher
from stocktradebot.indicators import TechnicalIndicators
from stocktradebot.bot import StockBot
from telegram.helpers import escape_markdown
import pandas as pd

# 配置日志 - 支持环境变量开关
ENABLE_LOG_FILE = os.environ.get("ENABLE_LOG_FILE", "false").lower() == "true"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# 配置日志基础设置
log_handlers = [logging.StreamHandler()]

if ENABLE_LOG_FILE:
    log_file = f"stock_bot_{datetime.now().strftime('%Y%m%d')}.log"
    log_handlers.append(logging.FileHandler(log_file))
    print(f"📝 日志文件已启用: {log_file}")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL),
    handlers=log_handlers
)
logger = logging.getLogger(__name__)


def is_a_share_trading_time() -> bool:
    """
    检查当前是否为A股交易时间（北京时间）

    交易时间：
    - 周一至周五
    - 上午 9:30 - 11:30
    - 下午 13:00 - 15:00

    Returns:
        bool: 如果在交易时间返回True，否则返回False
    """
    # 获取北京时间
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)

    # 检查是否为工作日（0=周一, 6=周日）
    if now.weekday() >= 5:  # 周六或周日
        return False

    # 获取当前时间（小时:分钟）
    current_time = now.time()

    # 检查是否在上午交易时段 9:30 - 11:30
    morning_start = now.replace(hour=9, minute=30, second=0, microsecond=0).time()
    morning_end = now.replace(hour=11, minute=30, second=0, microsecond=0).time()

    # 检查是否在下午交易时段 13:00 - 15:00
    afternoon_start = now.replace(hour=13, minute=0, second=0, microsecond=0).time()
    afternoon_end = now.replace(hour=15, minute=0, second=0, microsecond=0).time()

    if morning_start <= current_time <= morning_end:
        return True
    if afternoon_start <= current_time <= afternoon_end:
        return True

    return False


def is_a_share_or_etf(symbol: str) -> bool:
    """
    判断是否为A股或ETF

    Args:
        symbol: 股票代码（如 000001, 510300, AAPL）

    Returns:
        bool: 如果是A股或ETF返回True，否则返回False
    """
    # ETF判断：以5或1开头的6位数字
    if len(symbol) == 6 and symbol.isdigit():
        if symbol.startswith('5') or symbol.startswith('1'):
            return True

    # A股判断：6位数字代码（包括0、3、6开头的）
    if len(symbol) == 6 and symbol.isdigit():
        return True

    return False


class StockMonitor:
    """股票/期货/加密货币监控器"""

    def __init__(self, bot: StockBot, config: ConfigManager):
        self.bot = bot
        self.config = config
        self.data_fetcher = DataFetcher()
        self.crypto_fetcher = CryptoDataFetcher()
        self.running_tasks = set()

    async def get_data_for_task(self, task: MonitorTask) -> pd.DataFrame:
        """根据任务获取对应的数据"""
        symbol = task.symbol
        period = task.period
        logger.debug(f"开始获取 {task.task_id} 的数据，品种: {symbol}, 周期: {period}")

        try:
            if StockBot._is_crypto_symbol(symbol):
                period_map = {
                    "daily": "daily",
                    "240min": "4H",
                    "120min": "2H",
                    "60min": "1H",
                    "30min": "30m",
                    "15min": "15m",
                    "5min": "5m",
                    "1min": "1m",
                }
                bar = period_map.get(period, "1H")
                logger.debug(f"加密货币数据获取: 品种={symbol}, 周期={bar}")
                df = self.crypto_fetcher.get_crypto_history(symbol, days=300, period=bar)
                
            elif symbol.upper().startswith("AU") or symbol.upper().startswith("AG"):
                if period == "daily":
                    logger.debug(f"贵金属日线数据获取: 品种={symbol}")
                    df = self.data_fetcher.get_gold_spot_daily(symbol)
                else:
                    futures_symbol = "AU2606" if "AU" in symbol.upper() else "AG2606"
                    period_min = str(PERIOD_TYPES[period]["minutes"])
                    logger.debug(f"贵金属分钟数据获取: 品种={futures_symbol}, 周期={period_min}分钟")
                    df = self.data_fetcher.get_futures_minute(futures_symbol, period_min)
                    
            else:
                if period == "daily":
                    logger.debug(f"股票日线数据获取: 品种={symbol}")
                    df = self.data_fetcher.get_stock_history(symbol)
                else:
                    period_min = str(PERIOD_TYPES[period]["minutes"])
                    logger.debug(f"股票分钟数据获取: 品种={symbol}, 周期={period_min}分钟")
                    df = self.data_fetcher.get_stock_minute(symbol, period_min)

            if df is not None and len(df) > 0:
                logger.debug(f"成功获取 {task.task_id} 的数据，共 {len(df)} 条")
            else:
                logger.warning(f"未获取到 {task.task_id} 的数据")
                
            return df

        except Exception as e:
            logger.error(f"获取 {task.task_id} 数据失败: {str(e)}")
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def _detect_signal_at_index(self, df: pd.DataFrame, indicator: str, params: dict, idx: int) -> str:
        """
        在指定索引位置检测信号（用于回溯检测）

        Args:
            df: 完整的K线数据
            indicator: 指标名称
            params: 参数
            idx: 要检测的索引位置

        Returns:
            信号类型字符串或None
        """
        if df is None or len(df) < 30 or idx < 1 or idx >= len(df):
            return None

        window = params.get("window", params.get("order", 2))

        try:
            if indicator == "MACD":
                macd_df = TechnicalIndicators.calculate_macd(df)
                if idx >= len(macd_df):
                    return None
                prev_dif = macd_df["dif"].iloc[idx - 1]
                prev_dea = macd_df["dea"].iloc[idx - 1]
                curr_dif = macd_df["dif"].iloc[idx]
                curr_dea = macd_df["dea"].iloc[idx]

                if prev_dif <= prev_dea and curr_dif > curr_dea:
                    return "MACD_GOLDEN"
                if prev_dif >= prev_dea and curr_dif < curr_dea:
                    return "MACD_DEATH"

            elif indicator == "KDJ":
                kdj_df = TechnicalIndicators.calculate_kdj(df)
                if idx >= len(kdj_df):
                    return None
                prev_k = kdj_df["k"].iloc[idx - 1]
                prev_d = kdj_df["d"].iloc[idx - 1]
                curr_k = kdj_df["k"].iloc[idx]
                curr_d = kdj_df["d"].iloc[idx]

                if prev_k <= prev_d and curr_k > curr_d:
                    return "KDJ_GOLDEN"
                if prev_k >= prev_d and curr_k < curr_d:
                    return "KDJ_DEATH"

            elif indicator == "MA":
                ma_dict = TechnicalIndicators.calculate_ma(df, [5, 10])
                if len(ma_dict[5]) <= idx:
                    return None
                prev_ma5 = ma_dict[5].iloc[idx - 1]
                prev_ma10 = ma_dict[10].iloc[idx - 1]
                curr_ma5 = ma_dict[5].iloc[idx]
                curr_ma10 = ma_dict[10].iloc[idx]

                if prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10:
                    return "MA_GOLDEN"
                if prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10:
                    return "MA_DEATH"

            elif indicator == "RSI":
                rsi_df = TechnicalIndicators.calculate_rsi(df)
                if idx >= len(rsi_df):
                    return None
                prev_rsi = rsi_df["rsi"].iloc[idx - 1]
                curr_rsi = rsi_df["rsi"].iloc[idx]

                if prev_rsi <= 30 and curr_rsi > 30:
                    return "RSI_GOLDEN"
                if prev_rsi >= 70 and curr_rsi < 70:
                    return "RSI_DEATH"

            elif indicator == "MACD_DIV":
                # 背离检测需要检查确认点
                divergences = TechnicalIndicators.detect_macd_divergence(df, lookback=60, window=window)
                for div in divergences:
                    confirm_idx = div.peak2_idx + window
                    if confirm_idx == idx:
                        return "MACD_DIV_BULLISH" if div.divergence_type == "底背离" else "MACD_DIV_BEARISH"

            elif indicator == "KDJ_DIV":
                divergences = TechnicalIndicators.detect_kdj_divergence(df, lookback=60, window=window)
                for div in divergences:
                    confirm_idx = div.peak2_idx + window
                    if confirm_idx == idx:
                        return "KDJ_DIV_BULLISH" if div.divergence_type == "底背离" else "KDJ_DIV_BEARISH"

            elif indicator == "MACD_COMBO":
                # 在指定索引检测MACD组合信号
                if idx < 10:  # 需要足够的历史数据
                    return None

                divergences = TechnicalIndicators.detect_macd_divergence(
                    df.iloc[:idx+1], lookback=60, window=window
                )

                if not divergences:
                    return None

                macd_df = TechnicalIndicators.calculate_macd(df.iloc[:idx+1])

                # 检查当前bar是否是金叉
                if idx >= len(macd_df):
                    return None

                is_golden = (
                    macd_df["dif"].iloc[idx - 1] <= macd_df["dea"].iloc[idx - 1]
                    and macd_df["dif"].iloc[idx] > macd_df["dea"].iloc[idx]
                )
                is_death = (
                    macd_df["dif"].iloc[idx - 1] >= macd_df["dea"].iloc[idx - 1]
                    and macd_df["dif"].iloc[idx] < macd_df["dea"].iloc[idx]
                )

                # 检查是否有相关的背离
                for div in divergences:
                    # 背离的第二个极值点应该在这个bar之前不久
                    if div.peak2_idx <= idx <= div.peak2_idx + 10:
                        if is_golden and div.divergence_type == "底背离":
                            return "MACD_COMBO_BULLISH"
                        if is_death and div.divergence_type == "顶背离":
                            return "MACD_COMBO_BEARISH"

                return None

            elif indicator == "KDJ_COMBO":
                # 在指定索引检测KDJ组合信号
                if idx < 10:
                    return None

                divergences = TechnicalIndicators.detect_kdj_divergence(
                    df.iloc[:idx+1], lookback=60, window=window
                )

                if not divergences:
                    return None

                kdj_df = TechnicalIndicators.calculate_kdj(df.iloc[:idx+1])

                if idx >= len(kdj_df):
                    return None

                is_golden = (
                    kdj_df["k"].iloc[idx - 1] <= kdj_df["d"].iloc[idx - 1]
                    and kdj_df["k"].iloc[idx] > kdj_df["d"].iloc[idx]
                )
                is_death = (
                    kdj_df["k"].iloc[idx - 1] >= kdj_df["d"].iloc[idx - 1]
                    and kdj_df["k"].iloc[idx] < kdj_df["d"].iloc[idx]
                )

                for div in divergences:
                    if div.peak2_idx <= idx <= div.peak2_idx + 10:
                        if is_golden and div.divergence_type == "底背离":
                            return "KDJ_COMBO_BULLISH"
                        if is_death and div.divergence_type == "顶背离":
                            return "KDJ_COMBO_BEARISH"

                return None

        except Exception as e:
            logger.error(f"在索引 {idx} 检测 {indicator} 信号失败: {e}")

        return None

    def detect_signals_in_backfill_period(
        self,
        df: pd.DataFrame,
        task: MonitorTask,
        last_alert_time: datetime
    ) -> list[dict]:
        """
        检测从上次提醒时间到现在这段时间内产生的所有信号

        Args:
            df: 包含足够历史数据的K线数据
            task: 监控任务
            last_alert_time: 上次提醒时间

        Returns:
            检测到的信号列表，每个信号包含signal_type和timestamp
        """
        signals = []

        if df is None or len(df) < 30:
            return signals

        # 确保日期列为datetime类型
        if "date" not in df.columns:
            return signals

        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"])

        # 找到上次提醒时间对应的索引位置
        last_alert_idx = None
        for i in range(len(df)):
            if df["date"].iloc[i] >= last_alert_time:
                last_alert_idx = i
                break

        if last_alert_idx is None:
            # 所有数据都在上次提醒时间之前，检查最新的几个bar
            last_alert_idx = max(0, len(df) - 10)

        # 获取任务参数
        params = getattr(task, "params", {}) or {}

        # 从上一次提醒时间的位置开始，检查每个bar是否产生信号
        for idx in range(last_alert_idx, len(df)):
            signal = self._detect_signal_at_index(df, task.indicator, params, idx)
            if signal:
                signal_time = df["date"].iloc[idx]
                # 确保信号时间在上次提醒时间之后
                if signal_time > last_alert_time:
                    signals.append({
                        "signal_type": signal,
                        "timestamp": signal_time,
                        "idx": idx
                    })

        return signals

    async def detect_signal(self, task: MonitorTask, df: pd.DataFrame) -> str:
        """检测指定指标的信号"""
        if df is None or len(df) < 30:
            logger.debug(f"{task.task_id} 数据不足，无法检测信号，数据长度: {len(df) if df is not None else 0}")
            return None

        indicator = task.indicator
        params = getattr(task, "params", {}) or {}
        window = params.get("window", params.get("order", 2))

        try:
            logger.debug(f"开始检测 {task.task_id} 的信号，指标: {indicator}, 参数: {params}")
            
            if indicator == "MACD":
                macd_df = TechnicalIndicators.calculate_macd(df)
                if len(macd_df) < 2:
                    return None

                prev_dif = macd_df["dif"].iloc[-2]
                prev_dea = macd_df["dea"].iloc[-2]
                curr_dif = macd_df["dif"].iloc[-1]
                curr_dea = macd_df["dea"].iloc[-1]

                if prev_dif <= prev_dea and curr_dif > curr_dea:
                    logger.debug(f"{task.task_id} 检测到 MACD 金叉信号")
                    return "MACD_GOLDEN"
                if prev_dif >= prev_dea and curr_dif < curr_dea:
                    logger.debug(f"{task.task_id} 检测到 MACD 死叉信号")
                    return "MACD_DEATH"

            elif indicator == "KDJ":
                kdj_df = TechnicalIndicators.calculate_kdj(df)
                if len(kdj_df) < 2:
                    return None

                prev_k = kdj_df["k"].iloc[-2]
                prev_d = kdj_df["d"].iloc[-2]
                curr_k = kdj_df["k"].iloc[-1]
                curr_d = kdj_df["d"].iloc[-1]

                if prev_k <= prev_d and curr_k > curr_d:
                    logger.debug(f"{task.task_id} 检测到 KDJ 金叉信号")
                    return "KDJ_GOLDEN"
                if prev_k >= prev_d and curr_k < curr_d:
                    logger.debug(f"{task.task_id} 检测到 KDJ 死叉信号")
                    return "KDJ_DEATH"

            elif indicator == "MA":
                ma_dict = TechnicalIndicators.calculate_ma(df, [5, 10])
                if len(ma_dict[5]) < 2:
                    return None

                prev_ma5 = ma_dict[5].iloc[-2]
                prev_ma10 = ma_dict[10].iloc[-2]
                curr_ma5 = ma_dict[5].iloc[-1]
                curr_ma10 = ma_dict[10].iloc[-1]

                if prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10:
                    logger.debug(f"{task.task_id} 检测到 MA 金叉信号")
                    return "MA_GOLDEN"
                if prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10:
                    logger.debug(f"{task.task_id} 检测到 MA 死叉信号")
                    return "MA_DEATH"

            elif indicator == "RSI":
                rsi_df = TechnicalIndicators.calculate_rsi(df)
                if len(rsi_df) < 2:
                    return None

                prev_rsi = rsi_df["rsi"].iloc[-2]
                curr_rsi = rsi_df["rsi"].iloc[-1]

                if prev_rsi <= 30 and curr_rsi > 30:
                    logger.debug(f"{task.task_id} 检测到 RSI 超卖向上突破信号")
                    return "RSI_GOLDEN"
                if prev_rsi >= 70 and curr_rsi < 70:
                    logger.debug(f"{task.task_id} 检测到 RSI 超买向下跌破信号")
                    return "RSI_DEATH"

            elif indicator == "MACD_DIV":
                divergences = TechnicalIndicators.detect_macd_divergence(
                    df, lookback=60, window=window
                )
                current_idx = len(df) - 1
                for div in divergences:
                    confirm_idx = div.peak2_idx + window
                    if confirm_idx == current_idx:
                        signal_type = "MACD_DIV_BULLISH" if div.divergence_type == "底背离" else "MACD_DIV_BEARISH"
                        logger.debug(f"{task.task_id} 检测到 MACD 背离信号: {signal_type}")
                        return signal_type

            elif indicator == "KDJ_DIV":
                divergences = TechnicalIndicators.detect_kdj_divergence(
                    df, lookback=60, window=window
                )
                current_idx = len(df) - 1
                for div in divergences:
                    confirm_idx = div.peak2_idx + window
                    if confirm_idx == current_idx:
                        signal_type = "KDJ_DIV_BULLISH" if div.divergence_type == "底背离" else "KDJ_DIV_BEARISH"
                        logger.debug(f"{task.task_id} 检测到 KDJ 背离信号: {signal_type}")
                        return signal_type

            elif indicator == "MACD_COMBO":
                divergences = TechnicalIndicators.detect_macd_divergence(
                    df, lookback=60, window=window
                )

                macd_df = TechnicalIndicators.calculate_macd(df)
                
                check_range = min(3, len(df) - 1)
                
                for offset in range(check_range):
                    idx = len(df) - 1 - offset
                    if idx < 1:
                        continue
                        
                    is_golden = (
                        macd_df["dif"].iloc[idx - 1] <= macd_df["dea"].iloc[idx - 1]
                        and macd_df["dif"].iloc[idx] > macd_df["dea"].iloc[idx]
                    )
                    is_death = (
                        macd_df["dif"].iloc[idx - 1] >= macd_df["dea"].iloc[idx - 1]
                        and macd_df["dif"].iloc[idx] < macd_df["dea"].iloc[idx]
                    )

                    if not (is_golden or is_death):
                        continue

                    for div in divergences:
                        if div.peak2_idx <= idx <= div.peak2_idx + 10:
                            if is_golden and div.divergence_type == "底背离":
                                logger.debug(f"{task.task_id} 检测到 MACD 底背离+金叉组合信号")
                                return "MACD_COMBO_BULLISH"
                            if is_death and div.divergence_type == "顶背离":
                                logger.debug(f"{task.task_id} 检测到 MACD 顶背离+死叉组合信号")
                                return "MACD_COMBO_BEARISH"

            elif indicator == "KDJ_COMBO":
                divergences = TechnicalIndicators.detect_kdj_divergence(
                    df, lookback=60, window=window
                )

                kdj_df = TechnicalIndicators.calculate_kdj(df)
                
                check_range = min(3, len(df) - 1)
                
                for offset in range(check_range):
                    idx = len(df) - 1 - offset
                    if idx < 1:
                        continue
                        
                    is_golden = (
                        kdj_df["k"].iloc[idx - 1] <= kdj_df["d"].iloc[idx - 1]
                        and kdj_df["k"].iloc[idx] > kdj_df["d"].iloc[idx]
                    )
                    is_death = (
                        kdj_df["k"].iloc[idx - 1] >= kdj_df["d"].iloc[idx - 1]
                        and kdj_df["k"].iloc[idx] < kdj_df["d"].iloc[idx]
                    )

                    if not (is_golden or is_death):
                        continue

                    for div in divergences:
                        if div.peak2_idx <= idx <= div.peak2_idx + 10:
                            if is_golden and div.divergence_type == "底背离":
                                logger.debug(f"{task.task_id} 检测到 KDJ 底背离+金叉组合信号")
                                return "KDJ_COMBO_BULLISH"
                            if is_death and div.divergence_type == "顶背离":
                                logger.debug(f"{task.task_id} 检测到 KDJ 顶背离+死叉组合信号")
                                return "KDJ_COMBO_BEARISH"

            logger.debug(f"{task.task_id} 未检测到信号")
            return None
            
        except Exception as e:
            logger.error(f"检测 {task.task_id} 信号失败: {str(e)}")
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def format_signal_message(
        self, task: MonitorTask, signal: str, df: pd.DataFrame
    ) -> str:
        """格式化信号消息"""
        period_name = PERIOD_TYPES.get(task.period, {}).get("name", task.period)
        time_str = (
            df["date"].iloc[-1].strftime("%Y-%m-%d %H:%M")
            if "date" in df.columns
            else ""
        )
        price = df["close"].iloc[-1] if "close" in df.columns else 0

        if "GOLDEN" in signal or "BULLISH" in signal:
            emoji = "📈"
            signal_name = "金叉买入"
            if "DIV" in signal:
                signal_name = "底背离确认"
            if "COMBO" in signal:
                signal_name = "底背离+金叉"
        else:
            emoji = "📉"
            signal_name = "死叉卖出"
            if "DIV" in signal:
                signal_name = "顶背离确认"
            if "COMBO" in signal:
                signal_name = "顶背离+死叉"

        indicator = task.indicator

        display_name = (
            f"{task.name}"
            if task.name == task.symbol
            else f"{task.name} - {task.symbol}"
        )
        
        escaped_display_name = escape_markdown(display_name, version=1)
        escaped_indicator = escape_markdown(indicator, version=1)
        escaped_period_name = escape_markdown(period_name, version=1)
        
        msg = f"{emoji} *{escaped_display_name}*\n\n"
        msg += f"🔔 {escaped_indicator} {signal_name}\n"
        msg += f"💰 价格: {price:.2f}\n"
        msg += f"⏰ {time_str}\n"
        msg += f"📊 周期: {escaped_period_name}\n"

        params = getattr(task, "params", {}) or {}
        if params.get("window"):
            msg += f"⚙️ 参数: Window={params['window']}\n"

        if "MACD" in indicator:
            macd_df = TechnicalIndicators.calculate_macd(df)
            msg += f"\nDIF: {macd_df['dif'].iloc[-1]:.4f}\n"
            msg += f"DEA: {macd_df['dea'].iloc[-1]:.4f}\n"
            msg += f"MACD: {macd_df['macd'].iloc[-1]:.4f}"
        elif "KDJ" in indicator:
            kdj_df = TechnicalIndicators.calculate_kdj(df)
            msg += f"\nK: {kdj_df['k'].iloc[-1]:.2f}\n"
            msg += f"D: {kdj_df['d'].iloc[-1]:.2f}\n"
            msg += f"J: {kdj_df['j'].iloc[-1]:.2f}"
        elif indicator == "MA":
            ma_dict = TechnicalIndicators.calculate_ma(df, [5, 10])
            msg += f"\nMA5: {ma_dict[5].iloc[-1]:.2f}\n"
            msg += f"MA10: {ma_dict[10].iloc[-1]:.2f}"
        elif indicator == "RSI":
            rsi_df = TechnicalIndicators.calculate_rsi(df)
            msg += f"\nRSI: {rsi_df['rsi'].iloc[-1]:.2f}"

        return msg

    async def check_task(self, chat_id: int, task: MonitorTask):
        """检查单个任务（支持信号回溯检测）"""
        if task.task_id in self.running_tasks:
            logger.warning(f"{task.task_id} 任务正在执行中，跳过本次检查")
            return

        self.running_tasks.add(task.task_id)

        try:
            logger.info(f"开始检查任务: {task.task_id}")

            df = await self.get_data_for_task(task)
            if df is None or len(df) < 30:
                logger.warning(f"任务 {task.task_id} 数据获取失败或数据不足，跳过")
                return

            # 确保日期列为datetime类型
            if "date" not in df.columns:
                logger.warning(f"任务 {task.task_id} 数据缺少date列，跳过")
                return

            if not pd.api.types.is_datetime64_any_dtype(df["date"]):
                df["date"] = pd.to_datetime(df["date"])

            # 检查是否有上次提醒时间，如果有则进行回溯检测
            missed_signals = []
            if task.last_alert_time:
                try:
                    last_alert_time = pd.to_datetime(task.last_alert_time)
                    # 确保时区一致
                    if last_alert_time.tzinfo is None and df["date"].iloc[0].tzinfo is not None:
                        last_alert_time = last_alert_time.replace(tzinfo=df["date"].iloc[0].tzinfo)

                    # 检测上次提醒到现在这段时间内的所有信号
                    missed_signals = self.detect_signals_in_backfill_period(
                        df, task, last_alert_time
                    )

                    if missed_signals:
                        logger.info(f"任务 {task.task_id} 检测到 {len(missed_signals)} 个遗漏信号")
                except Exception as e:
                    logger.error(f"回溯检测失败 {task.task_id}: {e}")

            # 发送遗漏的信号（如果有）
            for missed_signal in missed_signals:
                signal_type = missed_signal["signal_type"]
                signal_time = missed_signal["timestamp"]

                # 格式化消息
                # 暂时修改df的最后一行为信号时间的数据，用于格式化消息
                signal_idx = missed_signal.get("idx", len(df) - 1)
                if 0 <= signal_idx < len(df):
                    # 创建一个新的DataFrame片段用于格式化消息
                    msg_df_slice = df.iloc[:signal_idx+1].copy()
                    message = self.format_signal_message(task, signal_type, msg_df_slice)
                    message += f"\n\n⚠️ *补发消息* - 该信号在 {signal_time.strftime('%Y-%m-%d %H:%M')} 产生"

                    await self.bot.send_alert(chat_id, message)
                    logger.info(f"补发信号 chat_id={chat_id}, task={task.task_id}, signal={signal_type}@{signal_time}")

            # 检测当前最新信号
            signal = await self.detect_signal(task, df)

            if signal:
                signal_time = df["date"].iloc[-1]
                signal_time_str = signal_time.strftime("%Y-%m-%d %H:%M")
                signal_with_time = f"{signal}@{signal_time_str}"

                # 检查是否已经发送过这个信号（包括回溯检测中的信号）
                already_sent = False
                for missed in missed_signals:
                    if missed["signal_type"] == signal and missed["timestamp"] == signal_time:
                        already_sent = True
                        break

                # 同时检查last_signal（去重）
                if not already_sent and signal_with_time != task.last_signal:
                    message = self.format_signal_message(task, signal, df)
                    await self.bot.send_alert(chat_id, message)

                    # 更新最后信号和最后提醒时间
                    self.config.update_task_signal(chat_id, task.task_id, signal_with_time)
                    self.config.update_task_alert_time(chat_id, task.task_id, signal_time.isoformat())
                    logger.info(
                        f"发送信号 chat_id={chat_id}, task={task.task_id}, signal={signal_with_time}"
                    )
                elif already_sent:
                    # 已经通过回溯发送过了，只更新状态
                    self.config.update_task_signal(chat_id, task.task_id, signal_with_time)
                    self.config.update_task_alert_time(chat_id, task.task_id, signal_time.isoformat())
            else:
                # 没有检测到信号，只更新最后提醒时间
                current_time = df["date"].iloc[-1]
                self.config.update_task_alert_time(chat_id, task.task_id, current_time.isoformat())

        except Exception as e:
            logger.error(f"检查任务失败 {task.task_id}: {e}")
            logger.error(f"详细错误: {traceback.format_exc()}")
        finally:
            self.running_tasks.remove(task.task_id)
            logger.debug(f"任务 {task.task_id} 检查完成")

    async def poll_all(self):
        """轮询所有任务"""
        logger.info("开始轮询检查...")
        tasks = self.config.get_all_tasks()
        logger.debug(f"当前任务总数: {len(tasks)}")

        # 检查是否为A股交易时间
        is_trading_time = is_a_share_trading_time()
        if not is_trading_time:
            logger.debug("当前不在A股交易时间")

        semaphore = asyncio.Semaphore(5)

        async def task_wrapper(chat_id, task):
            async with semaphore:
                # 检查是否为A股/ETF且不在交易时间
                if is_a_share_or_etf(task.symbol) and not is_trading_time:
                    logger.debug(f"跳过非交易时间检测: {task.task_id} ({task.symbol})")
                    return
                await self.check_task(chat_id, task)
                await asyncio.sleep(0.5)

        await asyncio.gather(*[task_wrapper(chat_id, task) for chat_id, task in tasks])

        logger.info(f"轮询完成，检查了 {len(tasks)} 个任务")


if __name__ == "__main__":
    """主函数"""
    logger.info("🚀 股票交易机器人启动")
    
    token = get_bot_token()
    if not token:
        token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token:
        logger.error("❌ 未设置 TELEGRAM_BOT_TOKEN 环境变量")
        print("❌ 请设置环境变量 TELEGRAM_BOT_TOKEN")
        print("   Windows: set TELEGRAM_BOT_TOKEN=your_token")
        print("   Linux/Mac: export TELEGRAM_BOT_TOKEN=your_token")
        sys.exit(1)

    try:
        config = ConfigManager()
        logger.debug("配置管理器初始化成功")
        
        bot = StockBot(token, config)
        logger.debug("Bot 实例创建成功")
        
        app = bot.build()
        logger.debug("Bot 应用构建成功")
        
        monitor = StockMonitor(bot, config)
        logger.debug("监控器实例创建成功")

        async def scheduled_poll(context):
            """定时轮询任务"""
            try:
                logger.debug("定时轮询任务启动")
                await monitor.poll_all()
            except Exception as e:
                logger.error(f"定时轮询任务失败: {e}")
                logger.error(f"详细错误: {traceback.format_exc()}")

        async def post_init_with_jobs(application):
            await StockBot.post_init(application)
            application.job_queue.run_repeating(
                scheduled_poll,
                interval=get_poll_interval(),
                first=10,
                name="poll_tasks",
            )
            logger.info(f"📋 已添加定时轮询任务，间隔: {get_poll_interval()}秒")

        app.post_init = post_init_with_jobs

        logger.info(f"Bot启动中... 轮询间隔: {get_poll_interval()}秒")
        app.run_polling()
        
    except Exception as e:
        logger.critical(f"Bot启动失败: {e}")
        logger.critical(f"详细错误: {traceback.format_exc()}")
        sys.exit(1)
