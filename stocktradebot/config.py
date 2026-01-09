"""
配置管理模块
支持多周期多指标的监控任务
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
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


@dataclass
class UserConfig:
    """用户配置"""
    chat_id: int
    tasks: list[MonitorTask] = field(default_factory=list)
    enabled: bool = True


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.users_file = self.data_dir / "users.json"
        self.users: dict[int, UserConfig] = {}
        self._load()
    
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
                        self.users[chat_id] = UserConfig(
                            chat_id=chat_id,
                            tasks=tasks,
                            enabled=user_data.get("enabled", True)
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
                "enabled": user_config.enabled
            }
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_user(self, chat_id: int) -> UserConfig:
        """获取用户配置，不存在则创建"""
        if chat_id not in self.users:
            self.users[chat_id] = UserConfig(chat_id=chat_id)
            self._save()
        return self.users[chat_id]
    
    def add_task(self, chat_id: int, symbol: str, name: str, period: str, indicator: str) -> tuple[bool, str]:
        """
        添加监控任务
        
        Returns:
            (成功, 消息)
        """
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
                return False, f"任务已存在: {task_id}"
        
        new_task = MonitorTask(
            task_id=task_id,
            symbol=symbol,
            name=name,
            period=period,
            indicator=indicator.upper()
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


# 全局配置函数（延迟加载）
def get_bot_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")

def get_poll_interval() -> int:
    return int(os.environ.get("POLL_INTERVAL", DEFAULT_POLL_INTERVAL))
