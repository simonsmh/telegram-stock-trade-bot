"""
Telegram Bot 模块
处理用户命令和消息发送
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from .config import ConfigManager, PERIOD_TYPES, INDICATOR_TYPES
from .stock_data import DataFetcher
from .indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class StockBot:
    """股票/期货监控Telegram Bot"""

    def __init__(self, token: str, config_manager: ConfigManager):
        self.token = token
        self.config = config_manager
        self.data_fetcher = DataFetcher()
        self.app: Application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        chat_id = update.effective_chat.id
        self.config.get_user(chat_id)

        welcome_msg = """
🤖 **股票/期货技术指标监控Bot**

欢迎使用！支持多周期、多指标的实时监控，当出现金叉/死叉时自动推送通知。

**快速开始:**
1️⃣ `/add 品种 周期 指标` 添加监控
2️⃣ `/tasks` 查看已添加的任务
3️⃣ 等待信号推送 🔔

**示例:**
• `/add Au99.99 60min MACD` - 沪金60分钟MACD
• `/add Au99.99 60min KDJ` - 沪金60分钟KDJ

**全部命令:**
/add /tasks /remove /backtest /list_type /help
"""
        await update.message.reply_text(welcome_msg, parse_mode="Markdown")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        help_msg = """
📖 **详细使用帮助**

━━━━━ 添加监控任务 ━━━━━
**命令格式:** `/add 品种 周期 指标`

**品种:** `Au99.99` `Ag99.99` 或股票代码
**周期:** `1min` `5min` `15min` `30min` `60min` `120min` `daily`
**指标:** 
• `MACD` `KDJ` `MA` `RSI` - 金叉死叉
• `MACD_DIV` `KDJ_DIV` - 背离信号
• `MACD_COMBO` `KDJ_COMBO` - 背离+金叉确认

━━━━━ 使用示例 ━━━━━
`/add Au99.99 60min MACD` → 普通MACD金叉死叉
`/add Au99.99 60min MACD_COMBO` → MACD背离+金叉确认
`/backtest Au99.99 60min MACD_COMBO` → 背离策略回测

━━━━━ 管理任务 ━━━━━
`/tasks` 查看任务
`/remove 任务ID` 移除任务
`/backtest 品种 周期 指标` 回测查询
`/optimize 品种` 策略优化
`/list_type` 支持的类型
"""
        await update.message.reply_text(help_msg, parse_mode="Markdown")

    async def list_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /list_type 命令 - 列出支持的周期和指标"""
        msg = "📊 **支持的类型**\n\n"

        msg += "**周期类型:**\n"
        for key, info in PERIOD_TYPES.items():
            msg += f"• `{key}` - {info['name']}\n"

        msg += "\n**指标类型:**\n"
        for key, info in INDICATOR_TYPES.items():
            msg += f"• `{key}` - {info['name']} ({info['description']})\n"

        msg += "\n**支持的品种:**\n"
        msg += "• `Au99.99` - 沪金AU9999\n"
        msg += "• `Ag99.99` - 沪银AG9999\n"
        msg += "• A股股票代码 (如 `000001`)\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    def _parse_extra_params(self, args: list) -> dict:
        """解析额外参数"""
        params = {}
        if not args:
            return params

        for arg in args:
            # 移除在 optimize 推荐输出中可能的括号
            arg = arg.strip("()")
            if "=" in arg:
                key, value = arg.split("=", 1)
                key = key.strip()
                
                # 统一参数名为 window
                if key.lower() == "order":
                    key = "window"
                elif key.lower() == "window":
                    key = "window"
                
                # 尝试转换为数字
                try:
                    if "." in value:
                        params[key] = float(value)
                    else:
                        params[key] = int(value)
                except ValueError:
                    params[key] = value
        return params

    async def add_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /add 命令 - 添加监控任务"""
        chat_id = update.effective_chat.id
        args = context.args

        if len(args) < 3:
            await update.message.reply_text(
                "❌ 参数不足\n用法: /add 品种 周期 指标 [参数]\n"
                "示例: /add Au99.99 60min MACD_DIV Window=5"
            )
            return

        symbol = args[0]
        period = args[1].lower()
        indicator = args[2].upper()

        # 解析额外参数
        params = self._parse_extra_params(args[3:])

        # 验证周期
        if period not in PERIOD_TYPES:
            periods = ", ".join(PERIOD_TYPES.keys())
            await update.message.reply_text(
                f"❌ 不支持的周期: {period}\n支持的周期: {periods}"
            )
            return

        # 验证指标
        if indicator not in INDICATOR_TYPES:
            indicators = ", ".join(INDICATOR_TYPES.keys())
            await update.message.reply_text(
                f"❌ 不支持的指标: {indicator}\n支持的指标: {indicators}"
            )
            return

        await update.message.reply_text(f"⏳ 正在添加 {symbol}...")

        # 获取品种名称
        name = symbol
        if symbol.upper().startswith("AU") or symbol.upper().startswith("AG"):
            pass  # 已经是标准名称
        else:
            # 快速获取股票名称
            try:
                import akshare as ak

                df = ak.stock_individual_info_em(symbol)
                name_row = df[df["item"] == "股票简称"]
                if not name_row.empty:
                    name = name_row["value"].values[0]
            except:
                pass  # 使用代码作为名称

        # 添加任务
        success, msg = self.config.add_task(
            chat_id, symbol, name, period, indicator, params
        )

        if success:
            # 显示格式: 名称 - 代码
            display_name = f"{name}" if name == symbol else f"{name} - {symbol}"
            
            # 格式化参数显示
            params_str = ""
            if params:
                params_list = []
                for k, v in params.items():
                    if k == "window":
                        params_list.append(f"Window={v}")
                    else:
                        params_list.append(f"{k}={v}")
                params_str = f" | 参数: {', '.join(params_list)}"

            await update.message.reply_text(
                f"✅ {msg}\n\n"
                f"📌 **{display_name}**\n"
                f"   周期: {PERIOD_TYPES[period]['name']}\n"
                f"   指标: {INDICATOR_TYPES[indicator]['name']}{params_str}\n"
                f"   任务ID: `{symbol}_{period}_{indicator}`\n\n"
                f"当{PERIOD_TYPES[period]['name']}出现{INDICATOR_TYPES[indicator]['description']}时会推送通知",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(f"❌ {msg}")

    async def remove_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /remove 命令 - 移除任务"""
        chat_id = update.effective_chat.id
        args = context.args

        if not args:
            await update.message.reply_text("❌ 请提供任务ID\n用法: /remove 任务ID")
            return

        task_id = args[0]
        if self.config.remove_task(chat_id, task_id):
            await update.message.reply_text(f"✅ 已移除任务: {task_id}")
        else:
            await update.message.reply_text(f"❌ 未找到任务: {task_id}")

    async def list_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /tasks 命令 - 列出用户任务"""
        chat_id = update.effective_chat.id
        tasks = self.config.get_user_tasks(chat_id)

        if not tasks:
            await update.message.reply_text(
                "📋 暂无监控任务\n使用 /add 品种 周期 指标 添加任务"
            )
            return

        msg = "📋 **我的监控任务**\n\n"
        for i, task in enumerate(tasks, 1):
            status = "✅" if task.enabled else "⏸️"
            period_name = PERIOD_TYPES.get(task.period, {}).get("name", task.period)
            # 显示格式: 名称 - 代码
            display_name = (
                f"{task.name}"
                if task.name == task.symbol
                else f"{task.name} - {task.symbol}"
            )

            params_str = (
                str(task.params) if hasattr(task, "params") and task.params else ""
            )
            if params_str:
                params_list = []
                for k, v in task.params.items():
                    if k == "window":
                        params_list.append(f"Window={v}")
                    else:
                        params_list.append(f"{k}={v}")
                params_str = f" | 参数: {', '.join(params_list)}"

            msg += f"{i}. {status} **{display_name}**\n"
            msg += f"   周期: {period_name} | 指标: {task.indicator}{params_str}\n"
            msg += f"   ID: `{task.task_id}`\n\n"

        msg += "使用 /remove 任务ID 移除任务"
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def backtest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /backtest 命令 - 回测查询最近信号"""
        args = context.args

        if len(args) < 3:
            await update.message.reply_text(
                "📊 回测查询\n\n"
                "用法: /backtest 品种 周期 指标 [参数]\n"
                "示例: /backtest Au99.99 60min MACD\n\n"
                "返回最近5次金叉/死叉信号的时间"
            )
            return

        symbol = args[0]
        period = args[1].lower()
        indicator = args[2].upper()

        # 解析额外参数
        params = self._parse_extra_params(args[3:])

        # 验证参数
        if period not in PERIOD_TYPES:
            await update.message.reply_text(f"❌ 不支持的周期: {period}")
            return
        if indicator not in INDICATOR_TYPES:
            await update.message.reply_text(f"❌ 不支持的指标: {indicator}")
            return

        await update.message.reply_text(
            f"⏳ 正在获取 {symbol} {period} {indicator} 数据..."
        )

        try:
            # 获取数据
            df = self._get_backtest_data(symbol, period)
            if df is None or len(df) < 30:
                await update.message.reply_text("❌ 获取数据失败或数据不足")
                return

            # 检测信号
            signals = self._detect_signals(df, indicator, params)

            # 格式化结果
            period_name = PERIOD_TYPES[period]["name"]
            name = (
                "沪金"
                if "AU" in symbol.upper()
                else ("沪银" if "AG" in symbol.upper() else symbol)
            )
            # 显示格式: 名称 - 代码
            display_name = f"{name}" if name == symbol else f"{name} - {symbol}"
            # 获取指标显示名称（避免下划线导致Markdown解析错误）
            indicator_display = INDICATOR_TYPES.get(indicator, {}).get(
                "name", indicator
            )

            msg = f"📊 **{display_name} {period_name} {indicator_display} 回测**\n\n"
            msg += f"数据范围: {df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d %H:%M')}\n"
            msg += f"共 {len(df)} 根K线\n\n"

            if signals:
                show_count = min(len(signals), 20)
                msg += f"**最近 {show_count} 次信号:**\n"
                for sig in signals[-20:]:  # 最近20个
                    emoji = "📈" if sig["type"] == "金叉" else "📉"
                    price = sig.get("price", 0)
                    div_info = ""
                    if "divergence" in sig:
                        div_info = f" [{sig['divergence']}]"
                    msg += f"{emoji} {sig['type']}{div_info} `{sig['time']}` 💰{price:.4f}\n"

                # 策略统计：金叉买入，死叉卖出
                stats = self._calculate_strategy_stats(signals)
                if stats["total_trades"] > 0:
                    msg += "\n**策略统计 (金叉买/死叉卖):**\n"
                    msg += f"交易次数: {stats['total_trades']}\n"
                    msg += (
                        f"盈利次数: {stats['win_count']} ({stats['win_rate']:.1f}%)\n"
                    )
                    msg += f"平均收益: {stats['avg_return']:.2f}%\n"
                    msg += f"累计收益: {stats['total_return']:.2f}%\n"

                # 当前状态
                msg += "\n**当前状态:**\n"
                msg += sig.get("status", "")
            else:
                msg += "未发现信号"

            await update.message.reply_text(msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"回测失败: {e}")
            await update.message.reply_text(f"❌ 回测失败: {e}")

    def _get_backtest_data(self, symbol: str, period: str):
        """获取回测数据"""
        if symbol.upper().startswith("AU") or symbol.upper().startswith("AG"):
            if period == "daily":
                return self.data_fetcher.get_gold_spot_daily(symbol)
            else:
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

    def _detect_signals(self, df, indicator: str, params: dict = None) -> list:
        """检测历史信号"""
        signals = []
        if params is None:
            params = {}

        # 获取背离检测参数
        window = params.get("window", 2)

        if indicator == "MACD":
            macd_df = TechnicalIndicators.calculate_macd(df)
            for i in range(1, len(df)):
                prev_dif = macd_df["dif"].iloc[i - 1]
                prev_dea = macd_df["dea"].iloc[i - 1]
                curr_dif = macd_df["dif"].iloc[i]
                curr_dea = macd_df["dea"].iloc[i]
                time_str = df["date"].iloc[i].strftime("%Y-%m-%d %H:%M")
                price = df["close"].iloc[i]

                if prev_dif <= prev_dea and curr_dif > curr_dea:
                    signals.append({"type": "金叉", "time": time_str, "price": price})
                if prev_dif >= prev_dea and curr_dif < curr_dea:
                    signals.append({"type": "死叉", "time": time_str, "price": price})

            # 添加当前状态
            if signals:
                status = (
                    "多头"
                    if macd_df["dif"].iloc[-1] > macd_df["dea"].iloc[-1]
                    else "空头"
                )
                signals[-1]["status"] = (
                    f"DIF: {macd_df['dif'].iloc[-1]:.4f}\nDEA: {macd_df['dea'].iloc[-1]:.4f}\n趋势: {status}"
                )

        elif indicator == "KDJ":
            kdj_df = TechnicalIndicators.calculate_kdj(df)
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

            if signals:
                signals[-1]["status"] = (
                    f"K: {kdj_df['k'].iloc[-1]:.2f}\nD: {kdj_df['d'].iloc[-1]:.2f}\nJ: {kdj_df['j'].iloc[-1]:.2f}"
                )

        elif indicator == "MA":
            ma_dict = TechnicalIndicators.calculate_ma(df, [5, 10])
            for i in range(1, len(df)):
                prev_ma5 = ma_dict[5].iloc[i - 1]
                prev_ma10 = ma_dict[10].iloc[i - 1]
                curr_ma5 = ma_dict[5].iloc[i]
                curr_ma10 = ma_dict[10].iloc[i]
                time_str = df["date"].iloc[i].strftime("%Y-%m-%d %H:%M")
                price = df["close"].iloc[i]

                if prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10:
                    signals.append({"type": "金叉", "time": time_str, "price": price})
                if prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10:
                    signals.append({"type": "死叉", "time": time_str, "price": price})

            if signals:
                signals[-1]["status"] = (
                    f"MA5: {ma_dict[5].iloc[-1]:.2f}\nMA10: {ma_dict[10].iloc[-1]:.2f}"
                )

        elif indicator == "RSI":
            rsi_df = TechnicalIndicators.calculate_rsi(df)
            for i in range(1, len(df)):
                prev_rsi = rsi_df["rsi"].iloc[i - 1]
                curr_rsi = rsi_df["rsi"].iloc[i]
                time_str = df["date"].iloc[i].strftime("%Y-%m-%d %H:%M")
                price = df["close"].iloc[i]

                # 超卖区(<30)向上突破 = 买入信号（金叉）
                if prev_rsi <= 30 and curr_rsi > 30:
                    signals.append({"type": "金叉", "time": time_str, "price": price})
                # 超买区(>70)向下跌破 = 卖出信号（死叉）
                if prev_rsi >= 70 and curr_rsi < 70:
                    signals.append({"type": "死叉", "time": time_str, "price": price})

            if signals:
                signals[-1]["status"] = f"RSI: {rsi_df['rsi'].iloc[-1]:.2f}"

        elif indicator == "MACD_DIV":
            # MACD纯背离策略
            divergences = TechnicalIndicators.detect_macd_divergence(
                df, lookback=len(df), window=window
            )
            for div in divergences:
                time_str = df["date"].iloc[div.peak2_idx].strftime("%Y-%m-%d %H:%M")
                price = df["close"].iloc[div.peak2_idx]
                sig_type = "金叉" if div.divergence_type == "底背离" else "死叉"
                signals.append(
                    {
                        "type": sig_type,
                        "time": time_str,
                        "price": price,
                        "divergence": div.divergence_type,
                        "strength": div.strength,
                    }
                )

            if signals:
                signals[-1]["status"] = (
                    f"检测到 {len(divergences)} 处背离 (Window={window})"
                )

        elif indicator == "KDJ_DIV":
            # KDJ纯背离策略
            divergences = TechnicalIndicators.detect_kdj_divergence(
                df, lookback=len(df), window=window
            )
            for div in divergences:
                time_str = df["date"].iloc[div.peak2_idx].strftime("%Y-%m-%d %H:%M")
                price = df["close"].iloc[div.peak2_idx]
                sig_type = "金叉" if div.divergence_type == "底背离" else "死叉"
                signals.append(
                    {
                        "type": sig_type,
                        "time": time_str,
                        "price": price,
                        "divergence": div.divergence_type,
                        "strength": div.strength,
                    }
                )

            if signals:
                signals[-1]["status"] = (
                    f"检测到 {len(divergences)} 处背离 (Window={window})"
                )

        elif indicator == "MACD_COMBO":
            # MACD背离+金叉确认策略
            macd_df = TechnicalIndicators.calculate_macd(df)
            divergences = TechnicalIndicators.detect_macd_divergence(
                df, lookback=len(df), window=window
            )

            # 记录背离位置
            bullish_div_indices = set()
            bearish_div_indices = set()
            for div in divergences:
                if div.divergence_type == "底背离":
                    # 底背离后的范围内等待金叉
                    for idx in range(div.peak2_idx, min(div.peak2_idx + 10, len(df))):
                        bullish_div_indices.add(idx)
                else:
                    # 顶背离后的范围内等待死叉
                    for idx in range(div.peak2_idx, min(div.peak2_idx + 10, len(df))):
                        bearish_div_indices.add(idx)

            # 检测金叉死叉，但只有在背离范围内才计入
            for i in range(1, len(df)):
                prev_dif = macd_df["dif"].iloc[i - 1]
                prev_dea = macd_df["dea"].iloc[i - 1]
                curr_dif = macd_df["dif"].iloc[i]
                curr_dea = macd_df["dea"].iloc[i]
                time_str = df["date"].iloc[i].strftime("%Y-%m-%d %H:%M")
                price = df["close"].iloc[i]

                # 底背离+金叉确认
                if (
                    i in bullish_div_indices
                    and prev_dif <= prev_dea
                    and curr_dif > curr_dea
                ):
                    signals.append(
                        {
                            "type": "金叉",
                            "time": time_str,
                            "price": price,
                            "divergence": "底背离确认",
                        }
                    )
                # 顶背离+死叉确认
                if (
                    i in bearish_div_indices
                    and prev_dif >= prev_dea
                    and curr_dif < curr_dea
                ):
                    signals.append(
                        {
                            "type": "死叉",
                            "time": time_str,
                            "price": price,
                            "divergence": "顶背离确认",
                        }
                    )

            if signals:
                status = (
                    "多头"
                    if macd_df["dif"].iloc[-1] > macd_df["dea"].iloc[-1]
                    else "空头"
                )
                signals[-1]["status"] = (
                    f"DIF: {macd_df['dif'].iloc[-1]:.4f}\nDEA: {macd_df['dea'].iloc[-1]:.4f}\n趋势: {status}"
                )

        elif indicator == "KDJ_COMBO":
            # KDJ背离+金叉确认策略
            kdj_df = TechnicalIndicators.calculate_kdj(df)
            divergences = TechnicalIndicators.detect_kdj_divergence(
                df, lookback=len(df), window=window
            )

            # 记录背离位置
            bullish_div_indices = set()
            bearish_div_indices = set()
            for div in divergences:
                if div.divergence_type == "底背离":
                    for idx in range(div.peak2_idx, min(div.peak2_idx + 10, len(df))):
                        bullish_div_indices.add(idx)
                else:
                    for idx in range(div.peak2_idx, min(div.peak2_idx + 10, len(df))):
                        bearish_div_indices.add(idx)

            # 检测金叉死叉
            for i in range(1, len(df)):
                prev_k = kdj_df["k"].iloc[i - 1]
                prev_d = kdj_df["d"].iloc[i - 1]
                curr_k = kdj_df["k"].iloc[i]
                curr_d = kdj_df["d"].iloc[i]
                time_str = df["date"].iloc[i].strftime("%Y-%m-%d %H:%M")
                price = df["close"].iloc[i]

                if i in bullish_div_indices and prev_k <= prev_d and curr_k > curr_d:
                    signals.append(
                        {
                            "type": "金叉",
                            "time": time_str,
                            "price": price,
                            "divergence": "底背离确认",
                        }
                    )
                if i in bearish_div_indices and prev_k >= prev_d and curr_k < curr_d:
                    signals.append(
                        {
                            "type": "死叉",
                            "time": time_str,
                            "price": price,
                            "divergence": "顶背离确认",
                        }
                    )

            if signals:
                signals[-1]["status"] = (
                    f"K: {kdj_df['k'].iloc[-1]:.2f}\nD: {kdj_df['d'].iloc[-1]:.2f}\nJ: {kdj_df['j'].iloc[-1]:.2f}"
                )

        return signals

    def _calculate_strategy_stats(
        self, df, indicator: str, params: dict = None
    ) -> dict:
        """计算策略统计数据"""
        signals = self._detect_signals(df, indicator, params)
        if not signals:
            return {"win_rate": 0, "trades": 0, "total_return": 0}

        capital = 10000
        position = 0
        trades = 0
        wins = 0
        initial_capital = capital

        for sig in signals:
            if sig["type"] == "金叉" and position == 0:
                position = capital / sig["price"]
                capital = 0
            elif sig["type"] == "死叉" and position > 0:
                amount = position * sig["price"]
                profit = (
                    amount - initial_capital
                )  # 计算单次盈亏基于初始资金是不对的，应该是基于买入时的资金
                # 简化计算：如果卖出价 > 上次买入价（这里没记录）
                # 由于这是简化版，我们统计总回报
                trades += 1
                capital = amount
                position = 0

        # 如果最后持有仓位，按最新价计算
        if position > 0:
            capital = position * df["close"].iloc[-1]

        total_return = (capital - initial_capital) / initial_capital * 100

        # 重新计算胜率（需要更详细的交易记录，这里简化为总回报正即为胜）
        # 为了更准确，我们需要配对买卖信号
        # 重新遍历一次
        capital = 10000
        position = 0
        entry_price = 0
        for sig in signals:
            if sig["type"] == "金叉" and position == 0:
                position = capital / sig["price"]
                entry_price = sig["price"]
                capital = 0
            elif sig["type"] == "死叉" and position > 0:
                train_return = (sig["price"] - entry_price) / entry_price
                if train_return > 0:
                    wins += 1
                capital = position * sig["price"]
                position = 0

        win_rate = (wins / trades * 100) if trades > 0 else 0

        return {"win_rate": win_rate, "trades": trades, "total_return": total_return}

    def setup_handlers(self):
        """设置命令处理器"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("list_type", self.list_type))
        self.app.add_handler(CommandHandler("add", self.add_task))
        self.app.add_handler(CommandHandler("remove", self.remove_task))
        self.app.add_handler(CommandHandler("tasks", self.list_tasks))
        self.app.add_handler(CommandHandler("backtest", self.backtest))
        self.app.add_handler(CommandHandler("optimize", self.optimize))

    async def optimize(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /optimize 命令 - 遍历所有策略找最优"""
        args = context.args

        if not args:
            await update.message.reply_text(
                "🔍 策略优化\n\n"
                "用法: /optimize 品种\n"
                "示例: /optimize Au99.99\n\n"
                "遍历所有周期和指标，找出胜率最高的组合"
            )
            return

        symbol = args[0]
        await update.message.reply_text(
            f"⏳ 正在分析 {symbol} 的所有策略组合，请稍候..."
        )

        # 获取品种名称
        name = symbol
        if symbol.upper().startswith("AU") or symbol.upper().startswith("AG"):
            name = "沪金" if "AU" in symbol.upper() else "沪银"
        else:
            # 尝试获取股票名称
            try:
                import akshare as ak

                df_info = ak.stock_individual_info_em(symbol)
                name_row = df_info[df_info["item"] == "股票简称"]
                if not name_row.empty:
                    name = name_row["value"].iloc[0]
            except Exception:
                pass  # 使用代码作为名称

        results = []
        periods_to_test = ["15min", "30min", "60min", "120min", "240min", "daily"]
        indicators_base = ["MACD", "KDJ", "MA", "RSI"]
        # 背离策略单独测试，需要测试不同的 sensitivities (window)
        indicators_div = ["MACD_DIV", "KDJ_DIV", "MACD_COMBO", "KDJ_COMBO"]
        windows_to_test = [2, 3, 5]

        # 先获取所有数据，找出时间范围的短板
        all_data = {}
        min_start_date = None

        for period in periods_to_test:
            df = self._get_backtest_data(symbol, period)
            if df is not None and len(df) >= 50:
                all_data[period] = df
                start_date = df["date"].iloc[0]
                if min_start_date is None or start_date > min_start_date:
                    min_start_date = start_date

        if not all_data:
            await update.message.reply_text("❌ 无法获取足够数据")
            return

        # 统一截取数据
        for period in all_data:
            df = all_data[period]
            all_data[period] = df[df["date"] >= min_start_date].reset_index(drop=True)

        # 开始测试
        for period, df in all_data.items():
            if len(df) < 30:
                continue

            # 测试基础指标
            for ind in indicators_base:
                stats = self._calculate_strategy_stats(df, ind)
                if stats["trades"] > 0:
                    stats["period"] = period
                    stats["indicator"] = ind
                    results.append(stats)

            # 测试背离指标 (多参数)
            for ind in indicators_div:
                for window in windows_to_test:
                    stats = self._calculate_strategy_stats(
                        df, ind, params={"window": window}
                    )
                    if stats["trades"] > 0:
                        stats["period"] = period
                        # 标记参数
                        stats["indicator"] = f"{ind} (Window={window})"
                        results.append(stats)
        if not results:
            await update.message.reply_text("❌ 未能获取足够数据进行分析")
            return

        # 按累计收益排序
        results.sort(key=lambda x: x["total_return"], reverse=True)

        # 显示格式: 名称 - 代码
        display_name = f"{name}" if name == symbol else f"{name} - {symbol}"
        msg = f"🏆 **{display_name} 策略优化结果**\n\n"
        msg += f"数据起始: {min_start_date.strftime('%Y-%m-%d')}\n\n"
        msg += "按累计收益排序:\n"

        for i, r in enumerate(results[:8], 1):
            emoji = (
                "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
            )
            period_name = PERIOD_TYPES[r["period"]]["name"]
            indicator_name = INDICATOR_TYPES.get(r["indicator"], {}).get(
                "name", r["indicator"]
            )
            msg += f"{emoji} {period_name} {indicator_name}\n"
            msg += f"   胜率:{r['win_rate']:.1f}% 交易:{r['trades']}次 累计:{r['total_return']:.2f}%\n"

        # 最优推荐 - 显示名称和命令
        best = results[0]
        best_indicator_name = INDICATOR_TYPES.get(best["indicator"], {}).get(
            "name", best["indicator"]
        )
        best_period_name = PERIOD_TYPES[best["period"]]["name"]
        msg += f"\n💡 **推荐** {display_name} {best_period_name} {best_indicator_name}"
        msg += f"\n📊 `/backtest {symbol} {best['period']} {best['indicator']}`"
        msg += f"\n📝 `/add {symbol} {best['period']} {best['indicator']}`"

        await update.message.reply_text(msg, parse_mode="Markdown")

    @staticmethod
    async def post_init(application):
        """Bot启动后设置命令菜单"""
        commands = [
            ("start", "开始使用"),
            ("add", "添加监控 (品种 周期 指标)"),
            ("tasks", "查看我的任务"),
            ("remove", "移除任务"),
            ("backtest", "回测查询"),
            ("optimize", "策略优化"),
            ("list_type", "支持的周期和指标"),
            ("help", "帮助信息"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("✅ Bot命令菜单已设置")

    async def send_alert(self, chat_id: int, message: str):
        """发送警报消息"""
        try:
            await self.app.bot.send_message(
                chat_id=chat_id, text=message, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"发送消息失败 chat_id={chat_id}: {e}")

    def build(self) -> Application:
        """构建Application"""
        self.app = (
            Application.builder()
            .token(self.token)
            .post_init(StockBot.post_init)
            .build()
        )
        self.setup_handlers()
        return self.app
