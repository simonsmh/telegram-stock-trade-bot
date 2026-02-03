"""
配置管理模块
支持多周期多指标的监控任务
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


# 支持的周期类型
PERIOD_TYPES = {
    "1min": {"name": "1分钟线", "minutes": 1},
    "5min": {"name": "5分钟线", "minutes": 5},
    "15min": {"name": "15分钟线", "minutes": 15},
    "30min": {"name": "30分钟线", "minutes": 30},
    "60min": {"name": "60分钟线", "minutes": 60},
    "120min": {"name": "120分钟线", "minutes": 120},
    "240min": {"name": "4小时线", "minutes": 240},
    "daily": {"name": "日线", "minutes": 1440},
}

# 支持的指标类型
INDICATOR_TYPES = {
    "MACD": {"name": "MACD指标", "description": "DIF/DEA金叉死叉"},
    "KDJ": {"name": "KDJ指标", "description": "K/D金叉死叉"},
    "MA": {"name": "均线", "description": "MA5/MA10金叉死叉"},
    "RSI": {"name": "RSI指标", "description": "超卖买入/超买卖出"},
    "MACD_DIV": {"name": "MACD背离", "description": "MACD背离信号"},
    "KDJ_DIV": {"name": "KDJ背离", "description": "KDJ背离信号"},
    "MACD_COMBO": {"name": "MACD组合", "description": "背离+金叉确认"},
    "KDJ_COMBO": {"name": "KDJ组合", "description": "背离+金叉确认"},
    "STRATEGY_MACD_KDJ": {"name": "MACD+KDJ策略", "description": "MACD趋势+KDJ动量组合"},
    "STRATEGY_MACD_RSI": {"name": "MACD+RSI策略", "description": "MACD趋势+RSI强度组合"},
    "STRATEGY_KDJ_RSI": {"name": "KDJ+RSI策略", "description": "KDJ动量+RSI强度组合"},
    "STRATEGY_MACD_KDJ_RSI": {"name": "MACD+KDJ+RSI策略", "description": "MACD+KDJ+RSI综合策略"},
    "STRATEGY_MACD_MA": {"name": "MACD+MA策略", "description": "MACD趋势+均线支撑组合"},
    "STRATEGY_KDJ_MA": {"name": "KDJ+MA策略", "description": "KDJ动量+均线趋势组合"},
}

# 支持的品种类型
SYMBOL_TYPES = {
    "Au99.99": {"name": "沪金AU9999", "type": "gold_spot"},
    "Ag99.99": {"name": "沪银AG9999", "type": "silver_spot"},
    # A股需要动态获取
}

# 默认配置
DEFAULT_POLL_INTERVAL = 60  # 秒


@dataclass
class MonitorTask:
    """监控任务"""

    task_id: str  # 任务ID: {symbol}_{period}_{indicator}
    symbol: str  # 品种代码，如 Au99.99、000001
    name: str  # 品种名称
    period: str  # 周期，如 60min、daily
    indicator: str  # 指标，如 MACD、KDJ
    enabled: bool = True
    last_signal: str = ""  # 上次信号状态（用于避免重复推送）
    last_alert_time: str = ""  # 上次提醒时间，ISO格式字符串
    params: dict = field(default_factory=dict)  # 额外参数，如 {"order": 5}


@dataclass
class StrategyConfig:
    """策略配置"""

    strategy_id: str
    name: str
    description: str
    indicator_weights: Dict[str, float] = field(default_factory=dict)
    timeframe_weights: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: "")
    updated_at: str = field(default_factory=lambda: "")


@dataclass
class UserStrategy:
    """用户策略配置"""

    strategy_config: StrategyConfig
    symbols: List[str] = field(default_factory=list)
    periods: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class UserConfig:
    """用户配置"""

    chat_id: int
    tasks: list[MonitorTask] = field(default_factory=list)
    strategies: list[UserStrategy] = field(default_factory=list)
    enabled: bool = True


class ConfigManager:
    """配置管理器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.users_file = self.data_dir / "users.json"
        self.users: dict[int, UserConfig] = {}
        self._load()

    # 预定义策略配置
    PREDEFINED_STRATEGIES = {
        "STRATEGY_MACD_KDJ": {
            "name": "MACD+KDJ策略",
            "description": "MACD趋势+KDJ动量组合策略",
            "indicator_weights": {"MACD": 0.6, "KDJ": 0.4},
            "timeframe_weights": {"60min": 0.4, "daily": 0.6},
            "parameters": {"window": 2, "lookback": 60}
        },
        "STRATEGY_MACD_RSI": {
            "name": "MACD+RSI策略",
            "description": "MACD趋势+RSI强度组合策略",
            "indicator_weights": {"MACD": 0.7, "RSI": 0.3},
            "timeframe_weights": {"30min": 0.3, "60min": 0.7},
            "parameters": {"window": 2, "lookback": 60}
        },
        "STRATEGY_KDJ_RSI": {
            "name": "KDJ+RSI策略",
            "description": "KDJ动量+RSI强度组合策略",
            "indicator_weights": {"KDJ": 0.5, "RSI": 0.5},
            "timeframe_weights": {"15min": 0.4, "60min": 0.6},
            "parameters": {"window": 2, "lookback": 60}
        },
        "STRATEGY_MACD_KDJ_RSI": {
            "name": "MACD+KDJ+RSI策略",
            "description": "MACD+KDJ+RSI综合策略",
            "indicator_weights": {"MACD": 0.5, "KDJ": 0.3, "RSI": 0.2},
            "timeframe_weights": {"60min": 0.4, "daily": 0.6},
            "parameters": {"window": 2, "lookback": 60}
        },
        "STRATEGY_MACD_MA": {
            "name": "MACD+MA策略",
            "description": "MACD趋势+均线支撑组合策略",
            "indicator_weights": {"MACD": 0.6, "MA": 0.4},
            "timeframe_weights": {"60min": 0.4, "daily": 0.6},
            "parameters": {"window": 2, "lookback": 60}
        },
        "STRATEGY_KDJ_MA": {
            "name": "KDJ+MA策略",
            "description": "KDJ动量+均线趋势组合策略",
            "indicator_weights": {"KDJ": 0.5, "MA": 0.5},
            "timeframe_weights": {"30min": 0.3, "60min": 0.7},
            "parameters": {"window": 2, "lookback": 60}
        }
    }

    def _load(self):
        """加载用户配置"""
        if self.users_file.exists():
            try:
                with open(self.users_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for chat_id_str, user_data in data.items():
                        chat_id = int(chat_id_str)
                        tasks = [
                            MonitorTask(**task) for task in user_data.get("tasks", [])
                        ]

                        # 加载策略配置
                        strategies = []
                        for strategy_data in user_data.get("strategies", []):
                            strategy_config = StrategyConfig(**strategy_data.get("strategy_config"))
                            user_strategy = UserStrategy(
                                strategy_config=strategy_config,
                                symbols=strategy_data.get("symbols", []),
                                periods=strategy_data.get("periods", []),
                                enabled=strategy_data.get("enabled", True)
                            )
                            strategies.append(user_strategy)

                        self.users[chat_id] = UserConfig(
                            chat_id=chat_id,
                            tasks=tasks,
                            strategies=strategies,
                            enabled=user_data.get("enabled", True),
                        )
            except Exception as e:
                print(f"加载配置失败: {e}")

    def _save(self):
        """保存用户配置"""
        data = {}
        for chat_id, user_config in self.users.items():
            data[str(chat_id)] = {
                "chat_id": user_config.chat_id,
                "tasks": [asdict(task) for task in user_config.tasks],
                "strategies": [
                    {
                        "strategy_config": asdict(strategy.strategy_config),
                        "symbols": strategy.symbols,
                        "periods": strategy.periods,
                        "enabled": strategy.enabled
                    } for strategy in user_config.strategies
                ],
                "enabled": user_config.enabled,
            }
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_user(self, chat_id: int) -> UserConfig:
        """获取用户配置，不存在则创建"""
        if chat_id not in self.users:
            self.users[chat_id] = UserConfig(chat_id=chat_id)
            self._save()
        return self.users[chat_id]

    def add_task(
        self,
        chat_id: int,
        symbol: str,
        name: str,
        period: str,
        indicator: str,
        params: dict = None,
    ) -> tuple[bool, str]:
        """
        添加监控任务

        Returns:
            (成功, 消息)
        """
        if params is None:
            params = {}

        # 验证周期
        if period not in PERIOD_TYPES:
            return False, f"不支持的周期: {period}"

        # 验证指标
        if indicator.upper() not in INDICATOR_TYPES:
            return False, f"不支持的指标: {indicator}"

        user = self.get_user(chat_id)
        task_id = f"{symbol}_{period}_{indicator.upper()}"

        # 检查是否已存在
        for task in user.tasks:
            if task.task_id == task_id:
                # 如果存在，更新参数？或者拒绝？
                # 这里我们拒绝，如果用户想改参数，可以先由于remove再add
                return False, f"任务已存在: {task_id}"

        new_task = MonitorTask(
            task_id=task_id,
            symbol=symbol,
            name=name,
            period=period,
            indicator=indicator.upper(),
            params=params,
        )
        user.tasks.append(new_task)
        self._save()
        return True, f"已添加任务: {name} {period} {indicator.upper()}"

    def remove_task(self, chat_id: int, task_id: str) -> bool:
        """移除监控任务"""
        user = self.get_user(chat_id)
        for i, task in enumerate(user.tasks):
            if task.task_id == task_id:
                user.tasks.pop(i)
                self._save()
                return True
        return False

    def get_user_tasks(self, chat_id: int) -> list[MonitorTask]:
        """获取用户的所有任务"""
        user = self.get_user(chat_id)
        return user.tasks

    def get_all_tasks(self) -> list[tuple[int, MonitorTask]]:
        """获取所有用户的所有任务"""
        tasks = []
        for chat_id, user in self.users.items():
            if user.enabled:
                for task in user.tasks:
                    if task.enabled:
                        tasks.append((chat_id, task))
        return tasks

    def update_task_signal(self, chat_id: int, task_id: str, signal: str):
        """更新任务的最后信号状态"""
        user = self.get_user(chat_id)
        for task in user.tasks:
            if task.task_id == task_id:
                task.last_signal = signal
                self._save()
                return

    def update_task_alert_time(self, chat_id: int, task_id: str, alert_time: str):
        """更新任务的最后提醒时间"""
        user = self.get_user(chat_id)
        for task in user.tasks:
            if task.task_id == task_id:
                task.last_alert_time = alert_time
                self._save()
                return

    # 策略管理方法
    def add_strategy(self, chat_id: int, strategy_id: str, symbols: List[str],
                    periods: List[str], enabled: bool = True) -> tuple[bool, str]:
        """
        添加策略配置

        Args:
            chat_id: 用户聊天ID
            strategy_id: 策略ID
            symbols: 监控品种列表
            periods: 监控周期列表
            enabled: 是否启用

        Returns:
            (成功, 消息)
        """
        user = self.get_user(chat_id)

        # 检查策略是否已存在
        for strategy in user.strategies:
            if strategy.strategy_config.strategy_id == strategy_id:
                return False, f"策略已存在: {strategy_id}"

        # 获取策略配置
        if strategy_id in self.PREDEFINED_STRATEGIES:
            strategy_config = StrategyConfig(
                strategy_id=strategy_id,
                **self.PREDEFINED_STRATEGIES[strategy_id]
            )
        else:
            return False, f"不支持的策略类型: {strategy_id}"

        # 创建用户策略
        user_strategy = UserStrategy(
            strategy_config=strategy_config,
            symbols=symbols,
            periods=periods,
            enabled=enabled
        )

        user.strategies.append(user_strategy)
        self._save()
        return True, f"已添加策略: {strategy_config.name}"

    def remove_strategy(self, chat_id: int, strategy_id: str) -> bool:
        """
        移除策略配置

        Args:
            chat_id: 用户聊天ID
            strategy_id: 策略ID

        Returns:
            是否成功
        """
        user = self.get_user(chat_id)
        for i, strategy in enumerate(user.strategies):
            if strategy.strategy_config.strategy_id == strategy_id:
                user.strategies.pop(i)
                self._save()
                return True
        return False

    def get_user_strategies(self, chat_id: int) -> List[UserStrategy]:
        """获取用户的所有策略"""
        user = self.get_user(chat_id)
        return user.strategies

    def get_strategy(self, chat_id: int, strategy_id: str) -> Optional[UserStrategy]:
        """获取用户的特定策略"""
        user = self.get_user(chat_id)
        for strategy in user.strategies:
            if strategy.strategy_config.strategy_id == strategy_id:
                return strategy
        return None

    def update_strategy_symbols(self, chat_id: int, strategy_id: str, symbols: List[str]):
        """更新策略的监控品种"""
        strategy = self.get_strategy(chat_id, strategy_id)
        if strategy:
            strategy.symbols = symbols
            self._save()

    def update_strategy_periods(self, chat_id: int, strategy_id: str, periods: List[str]):
        """更新策略的监控周期"""
        strategy = self.get_strategy(chat_id, strategy_id)
        if strategy:
            strategy.periods = periods
            self._save()

    def update_strategy_enabled(self, chat_id: int, strategy_id: str, enabled: bool):
        """更新策略的启用状态"""
        strategy = self.get_strategy(chat_id, strategy_id)
        if strategy:
            strategy.enabled = enabled
            self._save()

    def get_predefined_strategies(self) -> Dict[str, Any]:
        """获取预定义策略配置"""
        return self.PREDEFINED_STRATEGIES.copy()


# 全局配置函数（延迟加载）
def get_bot_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def get_poll_interval() -> int:
    return int(os.environ.get("POLL_INTERVAL", DEFAULT_POLL_INTERVAL))
