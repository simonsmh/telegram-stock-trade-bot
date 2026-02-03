"""
策略组合管理测试模块
测试 CombinationStrategies 的各项功能
"""

import pytest
from datetime import datetime
import pandas as pd
from stocktradebot.combination_strategies import (
    StrategyType,
    StrategyStatus,
    StrategyParameter,
    StrategyConfig,
    CombinationStrategies,
    AggregationStrategy
)
from stocktradebot.multi_timeframe import TimeframeType, TrendType


class TestCombinationStrategies:
    """测试策略组合管理"""

    def setup_method(self):
        """测试设置"""
        self.strategy_manager = CombinationStrategies()

    def test_initialization(self):
        """测试初始化"""
        assert len(self.strategy_manager.strategies) == 0
        assert self.strategy_manager.signal_aggregator is not None
        assert self.strategy_manager.timeframe_analyzer is not None

    def test_get_predefined_strategy_types(self):
        """测试获取预定义策略类型"""
        predefined_types = self.strategy_manager.get_predefined_strategy_types()

        assert len(predefined_types) >= 6
        assert StrategyType.MACD_KDJ in predefined_types
        assert StrategyType.MACD_RSI in predefined_types
        assert StrategyType.KDJ_RSI in predefined_types
        assert StrategyType.MACD_KDJ_RSI in predefined_types

    def test_create_predefined_strategy(self):
        """测试创建预定义策略"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="macd_kdj_strategy"
        )

        assert strategy.strategy_id == "macd_kdj_strategy"
        assert strategy.strategy_type == StrategyType.MACD_KDJ
        assert strategy.status == StrategyStatus.ACTIVE
        assert len(strategy.indicators) == 2
        assert len(strategy.timeframes) == 2
        assert "MACD" in strategy.indicators
        assert "KDJ" in strategy.indicators
        assert TimeframeType.MIN60 in strategy.timeframes
        assert TimeframeType.DAILY in strategy.timeframes

        assert strategy.config.indicator_weights["MACD"] == 0.6
        assert strategy.config.indicator_weights["KDJ"] == 0.4
        assert strategy.config.timeframe_weights[TimeframeType.MIN60] == 0.4
        assert strategy.config.timeframe_weights[TimeframeType.DAILY] == 0.6

    def test_create_custom_strategy(self):
        """测试创建自定义策略"""
        config = StrategyConfig(
            strategy_type=StrategyType.CUSTOM,
            parameters=[
                StrategyParameter(name="window", value=5, min_value=2, max_value=10),
                StrategyParameter(name="lookback", value=60, min_value=30, max_value=120),
                StrategyParameter(name="strength_threshold", value=70)
            ],
            indicator_weights={"MACD": 0.5, "KDJ": 0.3, "RSI": 0.2},
            timeframe_weights={
                TimeframeType.MIN30: 0.4,
                TimeframeType.MIN60: 0.6
            }
        )

        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.CUSTOM,
            strategy_id="custom_strategy",
            name="我的自定义策略",
            description="这是我的自定义策略描述",
            config=config
        )

        assert strategy.strategy_id == "custom_strategy"
        assert strategy.strategy_type == StrategyType.CUSTOM
        assert strategy.name == "我的自定义策略"
        assert strategy.description == "这是我的自定义策略描述"
        assert len(strategy.indicators) == 3
        assert len(strategy.timeframes) == 2
        assert "MACD" in strategy.indicators
        assert "KDJ" in strategy.indicators
        assert "RSI" in strategy.indicators
        assert TimeframeType.MIN30 in strategy.timeframes
        assert TimeframeType.MIN60 in strategy.timeframes

        assert strategy.config.indicator_weights["MACD"] == 0.5
        assert strategy.config.indicator_weights["KDJ"] == 0.3
        assert strategy.config.indicator_weights["RSI"] == 0.2

    def test_create_duplicate_strategy(self):
        """测试创建重复策略"""
        self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="duplicate_strategy"
        )

        with pytest.raises(ValueError):
            self.strategy_manager.create_strategy(
                strategy_type=StrategyType.MACD_KDJ,
                strategy_id="duplicate_strategy"
            )

    def test_get_strategy(self):
        """测试获取策略"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="get_test_strategy"
        )

        retrieved = self.strategy_manager.get_strategy("get_test_strategy")
        assert retrieved == strategy

    def test_remove_strategy(self):
        """测试移除策略"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="remove_test_strategy"
        )

        assert len(self.strategy_manager.strategies) == 1

        self.strategy_manager.remove_strategy("remove_test_strategy")
        assert len(self.strategy_manager.strategies) == 0
        assert self.strategy_manager.get_strategy("remove_test_strategy") is None

    def test_update_strategy(self):
        """测试更新策略"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="update_test_strategy"
        )

        original_name = strategy.name
        original_indicators = list(strategy.indicators)

        new_config = StrategyConfig(
            strategy_type=StrategyType.MACD_KDJ,
            indicator_weights={"MACD": 0.7, "KDJ": 0.3},
            timeframe_weights={
                TimeframeType.MIN60: 0.5,
                TimeframeType.DAILY: 0.5
            }
        )

        updated_strategy = self.strategy_manager.update_strategy(
            strategy_id="update_test_strategy",
            name="更新后的MACD+KDJ策略",
            description="更新后的策略描述",
            config=new_config
        )

        assert updated_strategy.name != original_name
        assert updated_strategy.name == "更新后的MACD+KDJ策略"
        assert updated_strategy.description == "更新后的策略描述"
        assert list(updated_strategy.indicators) == list(new_config.indicator_weights.keys())
        assert updated_strategy.updated_at > strategy.created_at

    def test_list_strategies(self):
        """测试列出策略"""
        self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="list1"
        )

        self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_RSI,
            strategy_id="list2"
        )

        self.strategy_manager.create_strategy(
            strategy_type=StrategyType.CUSTOM,
            strategy_id="list3"
        )

        all_strategies = self.strategy_manager.list_strategies()
        assert len(all_strategies) == 3

        macd_strategies = self.strategy_manager.list_strategies(StrategyType.MACD_KDJ)
        assert len(macd_strategies) == 1
        assert macd_strategies[0].strategy_id == "list1"

    def test_get_strategy_by_type(self):
        """测试按类型获取策略"""
        self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="type_test1"
        )

        self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="type_test2"
        )

        self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_RSI,
            strategy_id="type_test3"
        )

        macd_kdj_strategies = self.strategy_manager.get_strategy_by_type(StrategyType.MACD_KDJ)
        assert len(macd_kdj_strategies) == 2
        assert all(s.strategy_type == StrategyType.MACD_KDJ for s in macd_kdj_strategies)

    def test_strategy_with_different_aggregation_strategies(self):
        """测试不同聚合策略的策略"""
        # 创建使用不同聚合策略的策略
        config1 = StrategyConfig(
            strategy_type=StrategyType.CUSTOM,
            indicator_weights={"MACD": 0.6, "KDJ": 0.4},
            aggregation_strategy=AggregationStrategy.WEIGHTED_VOTE
        )

        config2 = StrategyConfig(
            strategy_type=StrategyType.CUSTOM,
            indicator_weights={"MACD": 0.6, "KDJ": 0.4},
            aggregation_strategy=AggregationStrategy.MAJORITY_VOTE
        )

        strategy1 = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.CUSTOM,
            strategy_id="agg1",
            config=config1
        )

        strategy2 = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.CUSTOM,
            strategy_id="agg2",
            config=config2
        )

        assert strategy1.config.aggregation_strategy == AggregationStrategy.WEIGHTED_VOTE
        assert strategy2.config.aggregation_strategy == AggregationStrategy.MAJORITY_VOTE

    def test_strategy_parameters(self):
        """测试策略参数配置"""
        config = StrategyConfig(
            strategy_type=StrategyType.CUSTOM,
            parameters=[
                StrategyParameter(name="window", value=2, min_value=1, max_value=5),
                StrategyParameter(name="lookback", value=60, min_value=30, max_value=120),
                StrategyParameter(name="strength_threshold", value=70)
            ]
        )

        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.CUSTOM,
            strategy_id="params_test",
            config=config
        )

        assert len(strategy.config.parameters) == 3
        assert any(p.name == "window" for p in strategy.config.parameters)
        assert any(p.name == "lookback" for p in strategy.config.parameters)

        window_param = next(p for p in strategy.config.parameters if p.name == "window")
        assert window_param.value == 2
        assert window_param.min_value == 1
        assert window_param.max_value == 5

    def test_strategy_with_timeframe_weights(self):
        """测试包含不同时间框架权重的策略"""
        config = StrategyConfig(
            strategy_type=StrategyType.CUSTOM,
            timeframe_weights={
                TimeframeType.MIN15: 0.2,
                TimeframeType.MIN30: 0.3,
                TimeframeType.MIN60: 0.5
            },
            indicator_weights={"MACD": 1.0}
        )

        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.CUSTOM,
            strategy_id="timeframe_weights_test",
            config=config
        )

        assert len(strategy.timeframes) == 3
        assert TimeframeType.MIN15 in strategy.timeframes
        assert TimeframeType.MIN30 in strategy.timeframes
        assert TimeframeType.MIN60 in strategy.timeframes

        assert strategy.config.timeframe_weights[TimeframeType.MIN15] == 0.2
        assert strategy.config.timeframe_weights[TimeframeType.MIN30] == 0.3
        assert strategy.config.timeframe_weights[TimeframeType.MIN60] == 0.5

    def test_backtest_empty_strategy(self):
        """测试回测空策略"""
        config = StrategyConfig(
            strategy_type=StrategyType.CUSTOM,
            indicator_weights={},
            timeframe_weights={}
        )

        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.CUSTOM,
            strategy_id="empty_strategy",
            config=config
        )

        df = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=100),
            'close': range(100)
        }).set_index('date')

        performance = self.strategy_manager.backtest_strategy(strategy, df)
        assert performance.total_trades == 0
        assert performance.total_return == 0
        assert performance.win_rate == 0

    def test_backtest_small_data(self):
        """测试小数据回测"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="small_data_strategy"
        )

        df = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=20),
            'close': range(20)
        }).set_index('date')

        performance = self.strategy_manager.backtest_strategy(strategy, df)
        assert performance.total_trades == 0

    def test_backtest_strategy_performance(self):
        """测试回测策略性能计算"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="performance_test_strategy"
        )

        df = self._create_test_data()
        performance = self.strategy_manager.backtest_strategy(strategy, df)

        assert isinstance(performance, type(self.strategy_manager.strategies["performance_test_strategy"].performance))
        assert performance.total_trades >= 0
        assert performance.win_rate >= 0
        assert performance.win_rate <= 100

    def _create_test_data(self) -> pd.DataFrame:
        """创建测试数据"""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        close = []
        current_price = 100.0
        for i in range(200):
            trend = i % 50
            current_price += (trend - 25) / 20
            close.append(current_price)

        return pd.DataFrame({
            'date': dates,
            'close': close
        }).set_index('date')

    def test_strategy_status_updates(self):
        """测试策略状态更新"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="status_test_strategy"
        )

        assert strategy.status == StrategyStatus.ACTIVE

        # 执行回测会改变状态
        df = self._create_test_data()
        performance = self.strategy_manager.backtest_strategy(strategy, df)

        assert strategy.status == StrategyStatus.ACTIVE

    def test_update_strategy_performance(self):
        """测试更新策略性能"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="performance_update_strategy"
        )

        original_performance = strategy.performance

        # 执行回测
        df = self._create_test_data()
        new_performance = self.strategy_manager.backtest_strategy(strategy, df)

        assert new_performance != original_performance
        assert strategy.performance.total_trades >= 0
        assert strategy.performance != original_performance

    def test_strategy_creation_with_all_types(self):
        """测试创建所有类型的策略"""
        strategy_types = self.strategy_manager.get_predefined_strategy_types()

        for strategy_type in strategy_types:
            strategy = self.strategy_manager.create_strategy(
                strategy_type=strategy_type,
                strategy_id=f"{strategy_type.value}_test"
            )

            assert strategy.strategy_id == f"{strategy_type.value}_test"
            assert strategy.strategy_type == strategy_type
            assert strategy.status == StrategyStatus.ACTIVE

        assert len(self.strategy_manager.strategies) == len(strategy_types)
