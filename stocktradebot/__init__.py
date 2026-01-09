"""
Stock Trade Bot - 股票/期货技术指标监控
"""
from .config import ConfigManager, PERIOD_TYPES, INDICATOR_TYPES
from .stock_data import DataFetcher
from .indicators import TechnicalIndicators
from .signals import SignalDetector
from .bot import StockBot

__version__ = "0.1.0"
__all__ = [
    "ConfigManager",
    "PERIOD_TYPES",
    "INDICATOR_TYPES",
    "DataFetcher",
    "TechnicalIndicators",
    "SignalDetector",
    "StockBot",
]
