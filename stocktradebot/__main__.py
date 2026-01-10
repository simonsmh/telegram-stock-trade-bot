"""
Stock Trade Bot - 主程序入口
股票/期货技术指标监控Telegram Bot
"""

import os
import sys
import asyncio
import logging


from stocktradebot.config import (
    ConfigManager,
    get_bot_token,
    get_poll_interval,
    PERIOD_TYPES,
    MonitorTask,
)
from stocktradebot.stock_data import DataFetcher
from stocktradebot.indicators import TechnicalIndicators
from stocktradebot.bot import StockBot
import pandas as pd

# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class StockMonitor:
    """股票/期货监控器"""

    def __init__(self, bot: StockBot, config: ConfigManager):
        self.bot = bot
        self.config = config
        self.data_fetcher = DataFetcher()

    def get_data_for_task(self, task: MonitorTask) -> pd.DataFrame:
        """根据任务获取对应的数据"""
        symbol = task.symbol
        period = task.period

        # 判断品种类型
        if symbol.upper().startswith("AU") or symbol.upper().startswith("AG"):
            # 贵金属
            if period == "daily":
                # 日线数据 - 使用现货历史数据
                return self.data_fetcher.get_gold_spot_daily(symbol)
            else:
                # 分钟K线数据 - 使用期货合约（现货只有当天数据，不够用）
                # Au99.99 -> AU2606, Ag99.99 -> AG2606
                futures_symbol = "AU2606" if "AU" in symbol.upper() else "AG2606"
                period_min = str(PERIOD_TYPES[period]["minutes"])
                return self.data_fetcher.get_futures_minute(futures_symbol, period_min)
        else:
            # 股票
            if period == "daily":
                return self.data_fetcher.get_stock_history(symbol)
            else:
                # 股票分钟数据
                period_min = str(PERIOD_TYPES[period]["minutes"])
                return self.data_fetcher.get_stock_minute(symbol, period_min)

        return None

    def detect_signal(self, task: MonitorTask, df: pd.DataFrame) -> str:
        """检测指定指标的信号"""
        if df is None or len(df) < 30:
            return None

        indicator = task.indicator
        params = getattr(task, "params", {}) or {}
        # 统一使用 window 参数
        window = params.get("window", params.get("order", 2))

        if indicator == "MACD":
            macd_df = TechnicalIndicators.calculate_macd(df)
            if len(macd_df) < 2:
                return None

            prev_dif = macd_df["dif"].iloc[-2]
            prev_dea = macd_df["dea"].iloc[-2]
            curr_dif = macd_df["dif"].iloc[-1]
            curr_dea = macd_df["dea"].iloc[-1]

            # 金叉
            if prev_dif <= prev_dea and curr_dif > curr_dea:
                return "MACD_GOLDEN"
            # 死叉
            if prev_dif >= prev_dea and curr_dif < curr_dea:
                return "MACD_DEATH"

        elif indicator == "KDJ":
            kdj_df = TechnicalIndicators.calculate_kdj(df)
            if len(kdj_df) < 2:
                return None

            prev_k = kdj_df["k"].iloc[-2]
            prev_d = kdj_df["d"].iloc[-2]
            curr_k = kdj_df["k"].iloc[-1]
            curr_d = kdj_df["d"].iloc[-1]

            # 金叉
            if prev_k <= prev_d and curr_k > curr_d:
                return "KDJ_GOLDEN"
            # 死叉
            if prev_k >= prev_d and curr_k < curr_d:
                return "KDJ_DEATH"

        elif indicator == "MA":
            ma_dict = TechnicalIndicators.calculate_ma(df, [5, 10])
            if len(ma_dict[5]) < 2:
                return None

            prev_ma5 = ma_dict[5].iloc[-2]
            prev_ma10 = ma_dict[10].iloc[-2]
            curr_ma5 = ma_dict[5].iloc[-1]
            curr_ma10 = ma_dict[10].iloc[-1]

            # 金叉
            if prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10:
                return "MA_GOLDEN"
            # 死叉
            if prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10:
                return "MA_DEATH"

        elif indicator == "RSI":
            rsi_df = TechnicalIndicators.calculate_rsi(df)
            if len(rsi_df) < 2:
                return None

            prev_rsi = rsi_df["rsi"].iloc[-2]
            curr_rsi = rsi_df["rsi"].iloc[-1]

            # 超卖向上突破
            if prev_rsi <= 30 and curr_rsi > 30:
                return "RSI_GOLDEN"
            # 超买向下跌破
            if prev_rsi >= 70 and curr_rsi < 70:
                return "RSI_DEATH"

        elif indicator == "MACD_DIV":
            divergences = TechnicalIndicators.detect_macd_divergence(
                df, lookback=60, window=window
            )
            current_idx = len(df) - 1
            # 检查是否有最近确认的背离
            # 背离确认时刻 = peak2_idx + window
            for div in divergences:
                confirm_idx = div.peak2_idx + window
                if confirm_idx == current_idx:
                    return (
                        "MACD_DIV_BULLISH"
                        if div.divergence_type == "底背离"
                        else "MACD_DIV_BEARISH"
                    )

        elif indicator == "KDJ_DIV":
            divergences = TechnicalIndicators.detect_kdj_divergence(
                df, lookback=60, window=window
            )
            current_idx = len(df) - 1
            for div in divergences:
                confirm_idx = div.peak2_idx + window
                if confirm_idx == current_idx:
                    return (
                        "KDJ_DIV_BULLISH"
                        if div.divergence_type == "底背离"
                        else "KDJ_DIV_BEARISH"
                    )

        elif indicator == "MACD_COMBO":
            divergences = TechnicalIndicators.detect_macd_divergence(
                df, lookback=60, window=window
            )
            current_idx = len(df) - 1

            # 检查当前是否金叉/死叉
            macd_df = TechnicalIndicators.calculate_macd(df)
            is_golden = (
                macd_df["dif"].iloc[-2] <= macd_df["dea"].iloc[-2]
                and macd_df["dif"].iloc[-1] > macd_df["dea"].iloc[-1]
            )
            is_death = (
                macd_df["dif"].iloc[-2] >= macd_df["dea"].iloc[-2]
                and macd_df["dif"].iloc[-1] < macd_df["dea"].iloc[-1]
            )

            if not (is_golden or is_death):
                return None

            # 检查背离有效性
            for div in divergences:
                # 只有背离还在有效期内（假设背离确认后10个周期内有效）才算 Combo
                if div.peak2_idx <= current_idx <= div.peak2_idx + 10:
                    if is_golden and div.divergence_type == "底背离":
                        return "MACD_COMBO_BULLISH"
                    if is_death and div.divergence_type == "顶背离":
                        return "MACD_COMBO_BEARISH"

        elif indicator == "KDJ_COMBO":
            divergences = TechnicalIndicators.detect_kdj_divergence(
                df, lookback=60, window=window
            )
            current_idx = len(df) - 1

            kdj_df = TechnicalIndicators.calculate_kdj(df)
            is_golden = (
                kdj_df["k"].iloc[-2] <= kdj_df["d"].iloc[-2]
                and kdj_df["k"].iloc[-1] > kdj_df["d"].iloc[-1]
            )
            is_death = (
                kdj_df["k"].iloc[-2] >= kdj_df["d"].iloc[-2]
                and kdj_df["k"].iloc[-1] < kdj_df["d"].iloc[-1]
            )

            if not (is_golden or is_death):
                return None

            for div in divergences:
                if div.peak2_idx <= current_idx <= div.peak2_idx + 10:
                    if is_golden and div.divergence_type == "底背离":
                        return "KDJ_COMBO_BULLISH"
                    if is_death and div.divergence_type == "顶背离":
                        return "KDJ_COMBO_BEARISH"

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

        # 显示格式: 名称 - 代码
        display_name = (
            f"{task.name}"
            if task.name == task.symbol
            else f"{task.name} - {task.symbol}"
        )
        msg = f"{emoji} **{display_name}**\n\n"
        msg += f"🔔 {indicator} {signal_name}\n"
        msg += f"💰 价格: {price:.2f}\n"
        msg += f"⏰ {time_str}\n"
        msg += f"📊 周期: {period_name}\n"

        # 若有额外参数，显示之
        params = getattr(task, "params", {}) or {}
        if params.get("window"):
            msg += f"⚙️ 参数: Window={params['window']}\n"

        # 添加指标详情
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
        """检查单个任务"""
        try:
            # 获取数据
            df = self.get_data_for_task(task)
            if df is None:
                return

            # 检测信号
            signal = self.detect_signal(task, df)

            if signal and signal != task.last_signal:
                # 新信号，发送通知
                message = self.format_signal_message(task, signal, df)
                await self.bot.send_alert(chat_id, message)

                # 更新最后信号状态
                self.config.update_task_signal(chat_id, task.task_id, signal)
                logger.info(
                    f"发送信号 chat_id={chat_id}, task={task.task_id}, signal={signal}"
                )

        except Exception as e:
            logger.error(f"检查任务失败 {task.task_id}: {e}")

    async def poll_all(self):
        """轮询所有任务"""
        logger.info("开始轮询检查...")
        tasks = self.config.get_all_tasks()

        for chat_id, task in tasks:
            await self.check_task(chat_id, task)
            await asyncio.sleep(0.5)  # 避免请求过快

        logger.info(f"轮询完成，检查了 {len(tasks)} 个任务")


if __name__ == "__main__":
    """主函数"""
    # 检查Token
    token = get_bot_token()
    if not token:
        token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token:
        print("❌ 请设置环境变量 TELEGRAM_BOT_TOKEN")
        print("   Windows: set TELEGRAM_BOT_TOKEN=your_token")
        print("   Linux/Mac: export TELEGRAM_BOT_TOKEN=your_token")
        sys.exit(1)

    # 初始化组件
    config = ConfigManager()
    bot = StockBot(token, config)
    app = bot.build()
    monitor = StockMonitor(bot, config)

    # 使用内置 job_queue 设置定时任务
    async def scheduled_poll(context):
        """定时轮询任务"""
        await monitor.poll_all()

    # post_init 中添加定时任务
    async def post_init_with_jobs(application):
        # 先调用原有的 post_init 设置命令菜单
        await StockBot.post_init(application)
        # 添加定时轮询任务
        application.job_queue.run_repeating(
            scheduled_poll,
            interval=get_poll_interval(),
            first=10,  # 启动10秒后开始第一次轮询
            name="poll_tasks",
        )
        logger.info(f"📋 已添加定时轮询任务，间隔: {get_poll_interval()}秒")

    # 替换 post_init
    app.post_init = post_init_with_jobs

    # 启动 (run_polling 内部会处理事件循环)
    logger.info(f"🚀 Bot启动中... 轮询间隔: {get_poll_interval()}秒")
    app.run_polling()
