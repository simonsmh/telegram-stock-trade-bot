"""
策略组合管理模块
用于创建、管理和优化多指标组合策略
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union
import logging
import pandas as pd

from .signal_aggregator import SignalType, AggregationStrategy, SignalAggregator, IndicatorSignal
from .multi_timeframe import TimeframeType, TrendType, TimeframeSignal, MultiTimeframeAnalyzer, MultiTimeframeAnalysis
from .indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """策略类型枚举"""
    MACD_KDJ = "macd_kdj"
    MACD_RSI = "macd_rsi"
    KDJ_RSI = "kdj_rsi"
    MACD_MA = "macd_ma"
    KDJ_MA = "kdj_ma"
    MACD_KDJ_RSI = "macd_kdj_rsi"
    CUSTOM = "custom"


class StrategyStatus(Enum):
    """策略状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OPTIMIZING = "optimizing"
    TESTING = "testing"
    ERROR = "error"


@dataclass
class StrategyParameter:
    """策略参数配置"""
    name: str
    value: Union[int, float, str]
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None


@dataclass
class StrategySignal:
    """策略信号"""
    timestamp: pd.Timestamp
    symbol: str
    signal_type: SignalType
    strength: float
    confidence: float
    parameters: Dict = field(default_factory=dict)
    indicators: List[str] = field(default_factory=list)


@dataclass
class StrategyPerformance:
    """策略性能指标"""
    total_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    avg_return: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 1.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    win_loss_ratio: float = 1.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_type: StrategyType
    parameters: List[StrategyParameter] = field(default_factory=list)
    indicator_weights: Dict[str, float] = field(default_factory=dict)
    timeframe_weights: Dict[TimeframeType, float] = field(default_factory=dict)
    aggregation_strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_VOTE
    minimum_strength: float = 50.0
    minimum_confidence: float = 50.0


@dataclass
class CombinationStrategy:
    """组合策略"""
    strategy_id: str
    strategy_type: StrategyType
    name: str
    description: str
    config: StrategyConfig
    status: StrategyStatus = StrategyStatus.ACTIVE
    performance: StrategyPerformance = field(default_factory=StrategyPerformance)
    created_at: pd.Timestamp = field(default_factory=pd.Timestamp.now)
    updated_at: pd.Timestamp = field(default_factory=pd.Timestamp.now)
    indicators: List[str] = field(default_factory=list)
    timeframes: List[TimeframeType] = field(default_factory=list)


class CombinationStrategies:
    """策略组合管理器"""

    # 预定义策略模板
    PREDEFINED_STRATEGIES = {
        StrategyType.MACD_KDJ: {
            "name": "MACD+KDJ组合策略",
            "description": "MACD金叉死叉 + KDJ超买超卖的组合策略",
            "indicators": ["MACD", "KDJ"],
            "timeframes": [TimeframeType.MIN60, TimeframeType.DAILY],
            "indicator_weights": {"MACD": 0.6, "KDJ": 0.4},
            "timeframe_weights": {
                TimeframeType.MIN60: 0.4,
                TimeframeType.DAILY: 0.6
            }
        },
        StrategyType.MACD_RSI: {
            "name": "MACD+RSI组合策略",
            "description": "MACD趋势确认 + RSI超买超卖的组合策略",
            "indicators": ["MACD", "RSI"],
            "timeframes": [TimeframeType.MIN30, TimeframeType.MIN60],
            "indicator_weights": {"MACD": 0.7, "RSI": 0.3},
            "timeframe_weights": {
                TimeframeType.MIN30: 0.3,
                TimeframeType.MIN60: 0.7
            }
        },
        StrategyType.KDJ_RSI: {
            "name": "KDJ+RSI组合策略",
            "description": "KDJ动量指标 + RSI强度指标的组合策略",
            "indicators": ["KDJ", "RSI"],
            "timeframes": [TimeframeType.MIN15, TimeframeType.MIN60],
            "indicator_weights": {"KDJ": 0.5, "RSI": 0.5},
            "timeframe_weights": {
                TimeframeType.MIN15: 0.4,
                TimeframeType.MIN60: 0.6
            }
        },
        StrategyType.MACD_KDJ_RSI: {
            "name": "MACD+KDJ+RSI组合策略",
            "description": "MACD趋势 + KDJ动量 + RSI强度的综合策略",
            "indicators": ["MACD", "KDJ", "RSI"],
            "timeframes": [TimeframeType.MIN60, TimeframeType.DAILY],
            "indicator_weights": {"MACD": 0.5, "KDJ": 0.3, "RSI": 0.2},
            "timeframe_weights": {
                TimeframeType.MIN60: 0.4,
                TimeframeType.DAILY: 0.6
            }
        },
        StrategyType.MACD_MA: {
            "name": "MACD+MA组合策略",
            "description": "MACD趋势确认 + 均线支撑阻力的组合策略",
            "indicators": ["MACD", "MA"],
            "timeframes": [TimeframeType.MIN60, TimeframeType.DAILY],
            "indicator_weights": {"MACD": 0.6, "MA": 0.4},
            "timeframe_weights": {
                TimeframeType.MIN60: 0.4,
                TimeframeType.DAILY: 0.6
            }
        },
        StrategyType.KDJ_MA: {
            "name": "KDJ+MA组合策略",
            "description": "KDJ动量指标 + 均线趋势的组合策略",
            "indicators": ["KDJ", "MA"],
            "timeframes": [TimeframeType.MIN30, TimeframeType.MIN60],
            "indicator_weights": {"KDJ": 0.5, "MA": 0.5},
            "timeframe_weights": {
                TimeframeType.MIN30: 0.3,
                TimeframeType.MIN60: 0.7
            }
        }
    }

    def __init__(self):
        """初始化策略组合管理器"""
        self.strategies: Dict[str, CombinationStrategy] = {}
        self.signal_aggregator = SignalAggregator()
        self.timeframe_analyzer = MultiTimeframeAnalyzer()
        logger.debug("策略组合管理器初始化")

    def create_strategy(self, strategy_type: StrategyType, strategy_id: str,
                       name: Optional[str] = None, description: Optional[str] = None,
                       config: Optional[StrategyConfig] = None) -> CombinationStrategy:
        """
        创建策略

        Args:
            strategy_type: 策略类型
            strategy_id: 策略ID
            name: 策略名称
            description: 策略描述
            config: 策略配置

        Returns:
            创建的策略
        """
        if strategy_id in self.strategies:
            raise ValueError(f"策略ID {strategy_id} 已存在")

        if strategy_type != StrategyType.CUSTOM and strategy_type not in self.PREDEFINED_STRATEGIES:
            raise ValueError(f"不支持的策略类型: {strategy_type}")

        if config is None:
            config = self._create_default_config(strategy_type)

        if name is None:
            name = self.PREDEFINED_STRATEGIES.get(strategy_type, {}).get("name", "自定义策略")

        if description is None:
            description = self.PREDEFINED_STRATEGIES.get(strategy_type, {}).get(
                "description", "自定义组合策略"
            )

        strategy = CombinationStrategy(
            strategy_id=strategy_id,
            strategy_type=strategy_type,
            name=name,
            description=description,
            config=config,
            indicators=config.indicator_weights.keys(),
            timeframes=config.timeframe_weights.keys()
        )

        self.strategies[strategy_id] = strategy
        logger.debug(f"策略创建成功: {strategy_id}")

        return strategy

    def _create_default_config(self, strategy_type: StrategyType) -> StrategyConfig:
        """
        创建默认策略配置

        Args:
            strategy_type: 策略类型

        Returns:
            默认配置
        """
        default_params = [
            StrategyParameter(name="window", value=2),
            StrategyParameter(name="lookback", value=60),
            StrategyParameter(name="strength_threshold", value=70)
        ]

        if strategy_type in self.PREDEFINED_STRATEGIES:
            template = self.PREDEFINED_STRATEGIES[strategy_type]
            config = StrategyConfig(
                strategy_type=strategy_type,
                parameters=default_params,
                indicator_weights=template["indicator_weights"],
                timeframe_weights=template["timeframe_weights"]
            )
        else:
            config = StrategyConfig(
                strategy_type=strategy_type,
                parameters=default_params
            )

        return config

    def get_strategy(self, strategy_id: str) -> Optional[CombinationStrategy]:
        """
        获取策略

        Args:
            strategy_id: 策略ID

        Returns:
            策略对象或None
        """
        return self.strategies.get(strategy_id)

    def remove_strategy(self, strategy_id: str):
        """
        移除策略

        Args:
            strategy_id: 策略ID
        """
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            logger.debug(f"策略移除成功: {strategy_id}")

    def update_strategy(self, strategy_id: str,
                      name: Optional[str] = None,
                      description: Optional[str] = None,
                      config: Optional[StrategyConfig] = None) -> CombinationStrategy:
        """
        更新策略

        Args:
            strategy_id: 策略ID
            name: 新名称
            description: 新描述
            config: 新配置

        Returns:
            更新后的策略
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"策略 {strategy_id} 不存在")

        if name:
            strategy.name = name

        if description:
            strategy.description = description

        if config:
            strategy.config = config
            strategy.indicators = list(config.indicator_weights.keys())
            strategy.timeframes = list(config.timeframe_weights.keys())

        strategy.updated_at = pd.Timestamp.now()
        logger.debug(f"策略更新成功: {strategy_id}")

        return strategy

    def list_strategies(self, strategy_type: Optional[StrategyType] = None) -> List[CombinationStrategy]:
        """
        列出策略

        Args:
            strategy_type: 策略类型（可选）

        Returns:
            策略列表
        """
        if strategy_type:
            return [s for s in self.strategies.values() if s.strategy_type == strategy_type]

        return list(self.strategies.values())

    def backtest_strategy(self, strategy: CombinationStrategy, df: pd.DataFrame,
                        initial_capital: float = 10000) -> StrategyPerformance:
        """
        回测策略

        Args:
            strategy: 策略对象
            df: 历史数据
            initial_capital: 初始资金

        Returns:
            回测结果
        """
        logger.debug(f"开始回测策略: {strategy.strategy_id}")
        strategy.status = StrategyStatus.TESTING

        try:
            signals = self._generate_signals(strategy, df)
            performance = self._calculate_performance(signals, df, initial_capital)

            strategy.performance = performance
            strategy.status = StrategyStatus.ACTIVE
            logger.debug(f"策略回测成功: {strategy.strategy_id}, 总收益率: {performance.total_return:.2f}%")

            return performance

        except Exception as e:
            logger.error(f"策略回测失败 {strategy.strategy_id}: {e}")
            strategy.status = StrategyStatus.ERROR
            raise

    def _generate_signals(self, strategy: CombinationStrategy, df: pd.DataFrame) -> List[StrategySignal]:
        """
        生成策略信号

        Args:
            strategy: 策略对象
            df: 历史数据

        Returns:
            信号列表
        """
        signals = []
        timeframe_analyzer = MultiTimeframeAnalyzer(strategy.config.timeframe_weights)

        for i in range(len(df)):
            window_df = df.iloc[:i+1]
            if len(window_df) < 30:
                continue

            timeframe_signals = self._analyze_timeframes(strategy, window_df)
            for ts in timeframe_signals:
                timeframe_analyzer.add_timeframe_signal(ts)

            if i >= 30:
                analysis = timeframe_analyzer.analyze()
                signal = self._generate_strategy_signal(
                    strategy, analysis, window_df, df.index[i]
                )
                if signal:
                    signals.append(signal)

        return signals

    def _analyze_timeframes(self, strategy: CombinationStrategy, df: pd.DataFrame):
        """
        分析不同时间框架的信号

        Args:
            strategy: 策略对象
            df: 数据

        Returns:
            时间框架信号
        """
        timeframe_signals = []
        indicator_analyzer = SignalAggregator(strategy.config.aggregation_strategy)

        for indicator, weight in strategy.config.indicator_weights.items():
            indicator_analyzer.add_indicator(indicator, weight)

        signals = []

        for indicator in strategy.indicators:
            signal = self._get_indicator_signal(df, indicator)
            if signal:
                signals.append(signal)

        aggregated = indicator_analyzer.aggregate(signals)

        for timeframe in strategy.timeframes:
            trend = self._convert_signal_to_trend(aggregated.signal_type)
            timeframe_signals.append(TimeframeSignal(
                timeframe=timeframe,
                trend=trend,
                strength=aggregated.strength,
                confidence=aggregated.confidence,
                signal_count=len(signals),
                parameters={}
            ))

        return timeframe_signals

    def _get_indicator_signal(self, df: pd.DataFrame, indicator: str) -> Optional[IndicatorSignal]:
        """
        获取指标信号

        Args:
            df: 数据
            indicator: 指标名称

        Returns:
            指标信号
        """
        try:
            if indicator == "MACD":
                return self._calculate_macd_signal(df)
            elif indicator == "KDJ":
                return self._calculate_kdj_signal(df)
            elif indicator == "RSI":
                return self._calculate_rsi_signal(df)
            elif indicator == "MA":
                return self._calculate_ma_signal(df)
            else:
                logger.warning(f"不支持的指标类型: {indicator}")
                return None

        except Exception as e:
            logger.error(f"计算指标信号失败 {indicator}: {e}")
            return None

    def _calculate_macd_signal(self, df: pd.DataFrame) -> IndicatorSignal:
        """计算MACD信号"""
        macd_df = TechnicalIndicators.calculate_macd(df)
        dif = macd_df["dif"].iloc[-1]
        dea = macd_df["dea"].iloc[-1]
        macd = macd_df["macd"].iloc[-1]

        if dif > dea and macd > 0:
            return IndicatorSignal(
                indicator_name="MACD",
                signal_type=SignalType.BULLISH,
                strength=85,
                confidence=90,
                parameters={"dif": dif, "dea": dea, "macd": macd}
            )
        elif dif < dea and macd < 0:
            return IndicatorSignal(
                indicator_name="MACD",
                signal_type=SignalType.BEARISH,
                strength=85,
                confidence=90,
                parameters={"dif": dif, "dea": dea, "macd": macd}
            )
        else:
            return IndicatorSignal(
                indicator_name="MACD",
                signal_type=SignalType.NEUTRAL,
                strength=30,
                confidence=50,
                parameters={"dif": dif, "dea": dea, "macd": macd}
            )

    def _calculate_kdj_signal(self, df: pd.DataFrame) -> IndicatorSignal:
        """计算KDJ信号"""
        kdj_df = TechnicalIndicators.calculate_kdj(df)
        k = kdj_df["k"].iloc[-1]
        d = kdj_df["d"].iloc[-1]
        j = kdj_df["j"].iloc[-1]

        if k > d and k < 20:
            return IndicatorSignal(
                indicator_name="KDJ",
                signal_type=SignalType.BULLISH,
                strength=90,
                confidence=85,
                parameters={"k": k, "d": d, "j": j}
            )
        elif k < d and k > 80:
            return IndicatorSignal(
                indicator_name="KDJ",
                signal_type=SignalType.BEARISH,
                strength=90,
                confidence=85,
                parameters={"k": k, "d": d, "j": j}
            )
        elif k > d:
            return IndicatorSignal(
                indicator_name="KDJ",
                signal_type=SignalType.WEAK_BULLISH,
                strength=60,
                confidence=70,
                parameters={"k": k, "d": d, "j": j}
            )
        elif k < d:
            return IndicatorSignal(
                indicator_name="KDJ",
                signal_type=SignalType.WEAK_BEARISH,
                strength=60,
                confidence=70,
                parameters={"k": k, "d": d, "j": j}
            )
        else:
            return IndicatorSignal(
                indicator_name="KDJ",
                signal_type=SignalType.NEUTRAL,
                strength=30,
                confidence=50,
                parameters={"k": k, "d": d, "j": j}
            )

    def _calculate_rsi_signal(self, df: pd.DataFrame) -> IndicatorSignal:
        """计算RSI信号"""
        rsi_df = TechnicalIndicators.calculate_rsi(df)
        rsi = rsi_df["rsi"].iloc[-1]

        if rsi < 30:
            return IndicatorSignal(
                indicator_name="RSI",
                signal_type=SignalType.BULLISH,
                strength=95,
                confidence=85,
                parameters={"rsi": rsi}
            )
        elif rsi > 70:
            return IndicatorSignal(
                indicator_name="RSI",
                signal_type=SignalType.BEARISH,
                strength=95,
                confidence=85,
                parameters={"rsi": rsi}
            )
        elif rsi > 50:
            return IndicatorSignal(
                indicator_name="RSI",
                signal_type=SignalType.WEAK_BULLISH,
                strength=55,
                confidence=60,
                parameters={"rsi": rsi}
            )
        elif rsi < 50:
            return IndicatorSignal(
                indicator_name="RSI",
                signal_type=SignalType.WEAK_BEARISH,
                strength=55,
                confidence=60,
                parameters={"rsi": rsi}
            )
        else:
            return IndicatorSignal(
                indicator_name="RSI",
                signal_type=SignalType.NEUTRAL,
                strength=30,
                confidence=50,
                parameters={"rsi": rsi}
            )

    def _calculate_ma_signal(self, df: pd.DataFrame) -> IndicatorSignal:
        """计算MA信号"""
        ma_dict = TechnicalIndicators.calculate_ma(df, [5, 10, 20])
        ma5 = ma_dict[5].iloc[-1]
        ma10 = ma_dict[10].iloc[-1]
        ma20 = ma_dict[20].iloc[-1]

        if ma5 > ma10 > ma20:
            return IndicatorSignal(
                indicator_name="MA",
                signal_type=SignalType.BULLISH,
                strength=80,
                confidence=85,
                parameters={"ma5": ma5, "ma10": ma10, "ma20": ma20}
            )
        elif ma5 < ma10 < ma20:
            return IndicatorSignal(
                indicator_name="MA",
                signal_type=SignalType.BEARISH,
                strength=80,
                confidence=85,
                parameters={"ma5": ma5, "ma10": ma10, "ma20": ma20}
            )
        elif ma5 > ma10:
            return IndicatorSignal(
                indicator_name="MA",
                signal_type=SignalType.WEAK_BULLISH,
                strength=60,
                confidence=70,
                parameters={"ma5": ma5, "ma10": ma10, "ma20": ma20}
            )
        elif ma5 < ma10:
            return IndicatorSignal(
                indicator_name="MA",
                signal_type=SignalType.WEAK_BEARISH,
                strength=60,
                confidence=70,
                parameters={"ma5": ma5, "ma10": ma10, "ma20": ma20}
            )
        else:
            return IndicatorSignal(
                indicator_name="MA",
                signal_type=SignalType.NEUTRAL,
                strength=30,
                confidence=50,
                parameters={"ma5": ma5, "ma10": ma10, "ma20": ma20}
            )

    def _convert_signal_to_trend(self, signal_type: SignalType) -> TrendType:
        """将信号类型转换为趋势类型"""
        if signal_type == SignalType.BULLISH:
            return TrendType.BULLISH
        elif signal_type == SignalType.WEAK_BULLISH:
            return TrendType.BULLISH
        elif signal_type == SignalType.BEARISH:
            return TrendType.BEARISH
        elif signal_type == SignalType.WEAK_BEARISH:
            return TrendType.BEARISH
        else:
            return TrendType.SIDEWAYS

    def _generate_strategy_signal(self, strategy: CombinationStrategy,
                                 analysis: MultiTimeframeAnalysis, df: pd.DataFrame,
                                 timestamp: pd.Timestamp) -> Optional[StrategySignal]:
        """
        生成策略信号

        Args:
            strategy: 策略对象
            analysis: 分析结果
            df: 数据
            timestamp: 时间戳

        Returns:
            策略信号
        """
        if (analysis.confirmation_score >= strategy.config.minimum_strength and
            analysis.confirmation_score >= strategy.config.minimum_confidence):

            signal_type = self._convert_trend_to_signal(analysis.overall_trend)
            return StrategySignal(
                timestamp=timestamp,
                symbol="",
                signal_type=signal_type,
                strength=analysis.confirmation_score,
                confidence=analysis.confirmation_score,
                parameters={},
                indicators=list(strategy.config.indicator_weights.keys())
            )

        return None

    def _convert_trend_to_signal(self, trend: TrendType) -> SignalType:
        """将趋势类型转换为信号类型"""
        if trend == TrendType.BULLISH:
            return SignalType.BULLISH
        elif trend == TrendType.BEARISH:
            return SignalType.BEARISH
        elif trend == TrendType.SIDEWAYS:
            return SignalType.NEUTRAL
        else:
            return SignalType.NEUTRAL

    def _calculate_performance(self, signals: List[StrategySignal], df: pd.DataFrame,
                             initial_capital: float) -> StrategyPerformance:
        """
        计算策略性能

        Args:
            signals: 信号列表
            df: 历史数据
            initial_capital: 初始资金

        Returns:
            性能指标
        """
        if not signals:
            return StrategyPerformance()

        # 简单模拟回测
        capital = initial_capital
        position = 0
        trades = []
        entry_price = 0

        for signal in signals:
            price = df.loc[signal.timestamp]["close"] if "close" in df.columns else df["close"].iloc[-1]

            if signal.signal_type == SignalType.BULLISH and position == 0:
                # 买入
                position = capital / price
                entry_price = price
                capital = 0
            elif signal.signal_type == SignalType.BEARISH and position > 0:
                # 卖出
                profit_pct = (price - entry_price) / entry_price * 100
                trades.append(profit_pct)
                capital = position * price
                position = 0

        # 最终结算
        if position > 0 and "close" in df.columns:
            final_price = df["close"].iloc[-1]
            profit_pct = (final_price - entry_price) / entry_price * 100
            trades.append(profit_pct)
            capital = position * final_price
            position = 0

        return self._calculate_statistics(trades, initial_capital, capital)

    def _calculate_statistics(self, trades: List[float], initial_capital: float,
                            final_capital: float) -> StrategyPerformance:
        """
        计算性能统计

        Args:
            trades: 交易记录
            initial_capital: 初始资金
            final_capital: 最终资金

        Returns:
            性能指标
        """
        total_trades = len(trades)

        if total_trades == 0:
            return StrategyPerformance(total_trades=0)

        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t < 0]

        win_count = len(wins)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        avg_return = total_return / total_trades if total_trades > 0 else 0
        max_drawdown = 0.0  # 简化计算
        profit_factor = sum(wins) / abs(sum(losses)) if losses else 0

        performance = StrategyPerformance(
            total_trades=total_trades,
            win_rate=win_rate,
            total_return=total_return,
            avg_return=avg_return,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            sharpe_ratio=0.0,  # 简化计算
            sortino_ratio=0.0,  # 简化计算
            win_loss_ratio=(win_count / len(losses)) if losses else 0,
            best_trade=max(wins) if wins else 0,
            worst_trade=min(losses) if losses else 0,
            avg_win=(sum(wins) / win_count) if win_count > 0 else 0,
            avg_loss=(sum(losses) / len(losses)) if losses else 0
        )

        return performance

    def get_predefined_strategy_types(self) -> List[StrategyType]:
        """获取预定义策略类型"""
        return list(self.PREDEFINED_STRATEGIES.keys())

    def get_strategy_by_type(self, strategy_type: StrategyType) -> List[CombinationStrategy]:
        """按类型获取策略"""
        return [s for s in self.strategies.values() if s.strategy_type == strategy_type]

    def update_strategy_performance(self, strategy_id: str, performance: StrategyPerformance):
        """
        更新策略性能指标

        Args:
            strategy_id: 策略ID
            performance: 新的性能指标
        """
        strategy = self.get_strategy(strategy_id)
        if strategy:
            strategy.performance = performance
            strategy.updated_at = pd.Timestamp.now()

    def __str__(self):
        """字符串表示"""
        return f"CombinationStrategies(count={len(self.strategies)})"

    def __repr__(self):
        """详细表示"""
        return self.__str__()
