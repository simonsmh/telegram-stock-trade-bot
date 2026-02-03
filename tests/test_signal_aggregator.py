"""
信号聚合器测试模块
测试 SignalAggregator 的各项功能
"""

import pytest
from stocktradebot.signal_aggregator import (
    SignalType,
    AggregationStrategy,
    IndicatorSignal,
    SignalAggregator
)


class TestSignalAggregator:
    """测试信号聚合器"""

    def test_initialization(self):
        """测试初始化"""
        aggregator = SignalAggregator()
        assert aggregator.get_total_weight() == 0
        assert len(aggregator.get_indicator_summary()) == 0
        assert "strategy=weighted_vote" in str(aggregator)

    def test_add_indicator(self):
        """测试添加指标"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 2.0)
        aggregator.add_indicator("KDJ", 1.5)

        assert len(aggregator.get_indicator_summary()) == 2
        assert "MACD" in aggregator.get_indicator_summary()
        assert "KDJ" in aggregator.get_indicator_summary()
        assert aggregator.get_indicator_summary()["MACD"] == 2.0
        assert aggregator.get_indicator_summary()["KDJ"] == 1.5

    def test_add_indicator_with_invalid_weight(self):
        """测试添加无效权重的指标"""
        aggregator = SignalAggregator()
        with pytest.raises(ValueError):
            aggregator.add_indicator("MACD", 0)

        with pytest.raises(ValueError):
            aggregator.add_indicator("KDJ", -1)

    def test_remove_indicator(self):
        """测试移除指标"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 2.0)
        aggregator.add_indicator("KDJ", 1.5)
        aggregator.remove_indicator("MACD")

        assert len(aggregator.get_indicator_summary()) == 1
        assert "MACD" not in aggregator.get_indicator_summary()
        assert "KDJ" in aggregator.get_indicator_summary()

    def test_set_weight(self):
        """测试设置指标权重"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 2.0)
        aggregator.set_weight("MACD", 3.0)

        assert aggregator.get_indicator_summary()["MACD"] == 3.0

    def test_set_weight_on_nonexistent_indicator(self):
        """测试设置不存在指标的权重"""
        aggregator = SignalAggregator()
        with pytest.raises(ValueError):
            aggregator.set_weight("nonexistent", 1.0)

    def test_set_invalid_weight(self):
        """测试设置无效权重"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 1.0)

        with pytest.raises(ValueError):
            aggregator.set_weight("MACD", 0)

        with pytest.raises(ValueError):
            aggregator.set_weight("MACD", -1)

    def test_weighted_vote_aggregation(self):
        """测试加权投票聚合策略"""
        aggregator = SignalAggregator(strategy=AggregationStrategy.WEIGHTED_VOTE)
        aggregator.add_indicator("MACD", 3.0)
        aggregator.add_indicator("KDJ", 1.0)
        aggregator.add_indicator("MA", 2.0)

        signals = [
            IndicatorSignal(
                indicator_name="MACD",
                signal_type=SignalType.BULLISH,
                strength=90,
                confidence=85,
                parameters={"fast": 12, "slow": 26}
            ),
            IndicatorSignal(
                indicator_name="KDJ",
                signal_type=SignalType.BULLISH,
                strength=80,
                confidence=75,
                parameters={"n": 9, "m1": 3, "m2": 3}
            ),
            IndicatorSignal(
                indicator_name="MA",
                signal_type=SignalType.BULLISH,
                strength=85,
                confidence=80,
                parameters={"periods": [5, 10]}
            )
        ]

        result = aggregator.aggregate(signals)

        assert result.signal_type in [SignalType.BULLISH, SignalType.WEAK_BULLISH]
        assert result.strength > 60
        assert result.confidence >= 80
        assert len(result.indicator_signals) == 3
        assert result.vote_counts[SignalType.BULLISH] == 3

    def test_weighted_vote_with_conflicting_signals(self):
        """测试加权投票处理冲突信号"""
        aggregator = SignalAggregator(strategy=AggregationStrategy.WEIGHTED_VOTE)
        aggregator.add_indicator("MACD", 3.0)
        aggregator.add_indicator("KDJ", 1.0)

        signals = [
            IndicatorSignal(
                indicator_name="MACD",
                signal_type=SignalType.BULLISH,
                strength=90,
                confidence=85
            ),
            IndicatorSignal(
                indicator_name="KDJ",
                signal_type=SignalType.BEARISH,
                strength=70,
                confidence=65
            )
        ]

        result = aggregator.aggregate(signals)

        assert result.signal_type in [SignalType.BULLISH, SignalType.WEAK_BULLISH]
        assert result.strength > 30
        assert result.vote_counts[SignalType.BULLISH] == 1
        assert result.vote_counts[SignalType.BEARISH] == 1

    def test_majority_vote_aggregation(self):
        """测试多数投票聚合策略"""
        aggregator = SignalAggregator(strategy=AggregationStrategy.MAJORITY_VOTE)
        aggregator.add_indicator("MACD", 1.0)
        aggregator.add_indicator("KDJ", 1.0)
        aggregator.add_indicator("MA", 1.0)
        aggregator.add_indicator("RSI", 1.0)

        signals = [
            IndicatorSignal(indicator_name="MACD", signal_type=SignalType.BULLISH, strength=85, confidence=80),
            IndicatorSignal(indicator_name="KDJ", signal_type=SignalType.BULLISH, strength=75, confidence=70),
            IndicatorSignal(indicator_name="MA", signal_type=SignalType.BEARISH, strength=80, confidence=75),
            IndicatorSignal(indicator_name="RSI", signal_type=SignalType.BULLISH, strength=90, confidence=85)
        ]

        result = aggregator.aggregate(signals)

        assert result.signal_type == SignalType.BULLISH
        assert result.vote_counts[SignalType.BULLISH] == 3
        assert result.vote_counts[SignalType.BEARISH] == 1
        assert result.strength > 70

    def test_average_strength_aggregation(self):
        """测试平均强度聚合策略"""
        aggregator = SignalAggregator(strategy=AggregationStrategy.AVERAGE_STRENGTH)
        aggregator.add_indicator("MACD", 1.0)
        aggregator.add_indicator("KDJ", 1.0)

        signals = [
            IndicatorSignal(indicator_name="MACD", signal_type=SignalType.BULLISH, strength=90, confidence=85),
            IndicatorSignal(indicator_name="KDJ", signal_type=SignalType.WEAK_BULLISH, strength=60, confidence=70)
        ]

        result = aggregator.aggregate(signals)
        assert result.signal_type in [SignalType.BULLISH, SignalType.WEAK_BULLISH]
        assert result.strength > 50

    def test_strong_signal_only_strategy(self):
        """测试仅强信号聚合策略"""
        aggregator = SignalAggregator(strategy=AggregationStrategy.STRONG_SIGNAL_ONLY)
        aggregator.add_indicator("MACD", 1.0)
        aggregator.add_indicator("KDJ", 1.0)
        aggregator.add_indicator("RSI", 1.0)

        signals = [
            IndicatorSignal(indicator_name="MACD", signal_type=SignalType.BULLISH, strength=85, confidence=80),
            IndicatorSignal(indicator_name="KDJ", signal_type=SignalType.WEAK_BULLISH, strength=60, confidence=70),
            IndicatorSignal(indicator_name="RSI", signal_type=SignalType.BULLISH, strength=90, confidence=85)
        ]

        result = aggregator.aggregate(signals)
        assert result.signal_type == SignalType.BULLISH
        assert len([s for s in result.indicator_signals if s.strength > 70 and s.confidence > 70]) >= 2

    def test_no_signals(self):
        """测试无信号的情况"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 1.0)
        aggregator.add_indicator("KDJ", 1.0)

        result = aggregator.aggregate([])

        assert result.signal_type == SignalType.NEUTRAL
        assert result.strength == 0
        assert result.confidence == 0
        assert len(result.indicator_signals) == 0

    def test_invalid_signals(self):
        """测试无效信号的情况"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 1.0)

        signals = [
            IndicatorSignal(indicator_name="invalid_indicator", signal_type=SignalType.BULLISH, strength=80, confidence=75)
        ]

        result = aggregator.aggregate(signals)

        assert result.signal_type == SignalType.NEUTRAL
        assert result.strength == 0
        assert result.confidence == 0

    def test_clear_indicators(self):
        """测试清除指标"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 1.0)
        aggregator.add_indicator("KDJ", 1.0)
        aggregator.clear_indicators()

        assert len(aggregator.get_indicator_summary()) == 0
        assert aggregator.get_total_weight() == 0

    def test_various_signal_strengths(self):
        """测试不同强度的信号"""
        aggregator = SignalAggregator(strategy=AggregationStrategy.WEIGHTED_VOTE)
        aggregator.add_indicator("MACD", 1.0)
        aggregator.add_indicator("KDJ", 1.0)
        aggregator.add_indicator("MA", 1.0)

        signals = [
            IndicatorSignal(indicator_name="MACD", signal_type=SignalType.BULLISH, strength=95, confidence=90),
            IndicatorSignal(indicator_name="KDJ", signal_type=SignalType.WEAK_BULLISH, strength=50, confidence=60),
            IndicatorSignal(indicator_name="MA", signal_type=SignalType.NEUTRAL, strength=0, confidence=50)
        ]

        result = aggregator.aggregate(signals)
        assert result.signal_type in [SignalType.BULLISH, SignalType.WEAK_BULLISH]
        assert 30 < result.strength < 95

    def test_weight_distribution(self):
        """测试权重分布"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 3.0)
        aggregator.add_indicator("KDJ", 1.0)

        signals = [
            IndicatorSignal(indicator_name="MACD", signal_type=SignalType.BULLISH, strength=80, confidence=75),
            IndicatorSignal(indicator_name="KDJ", signal_type=SignalType.BULLISH, strength=70, confidence=65)
        ]

        result = aggregator.aggregate(signals)

        assert "MACD" in result.weight_distribution
        assert "KDJ" in result.weight_distribution
        assert result.weight_distribution["MACD"] > result.weight_distribution["KDJ"]

    def test_get_total_weight(self):
        """测试获取总权重"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 2.0)
        aggregator.add_indicator("KDJ", 1.5)
        aggregator.add_indicator("MA", 0.5)

        assert aggregator.get_total_weight() == 4.0

    def test_indicator_summary(self):
        """测试指标摘要"""
        aggregator = SignalAggregator()
        aggregator.add_indicator("MACD", 2.0)
        aggregator.add_indicator("KDJ", 1.5)

        summary = aggregator.get_indicator_summary()
        assert isinstance(summary, dict)
        assert len(summary) == 2
        assert summary["MACD"] == 2.0
        assert summary["KDJ"] == 1.5

    def test_multiple_strategies_comparison(self):
        """测试不同策略的比较"""
        aggregator1 = SignalAggregator(strategy=AggregationStrategy.WEIGHTED_VOTE)
        aggregator1.add_indicator("MACD", 3.0)
        aggregator1.add_indicator("KDJ", 1.0)

        aggregator2 = SignalAggregator(strategy=AggregationStrategy.MAJORITY_VOTE)
        aggregator2.add_indicator("MACD", 3.0)
        aggregator2.add_indicator("KDJ", 1.0)

        signals = [
            IndicatorSignal(indicator_name="MACD", signal_type=SignalType.BULLISH, strength=90, confidence=85),
            IndicatorSignal(indicator_name="KDJ", signal_type=SignalType.BEARISH, strength=70, confidence=65)
        ]

        result1 = aggregator1.aggregate(signals)
        result2 = aggregator2.aggregate(signals)

        assert result1.signal_type in [SignalType.BULLISH, SignalType.WEAK_BULLISH]
        assert result2.signal_type == SignalType.BULLISH
        assert result1.strength > 0
