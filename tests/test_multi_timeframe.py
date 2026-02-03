"""
多时间框架分析器测试模块
测试 MultiTimeframeAnalyzer 的各项功能
"""

import pytest
from stocktradebot.multi_timeframe import (
    TimeframeType,
    TrendType,
    TimeframeSignal,
    MultiTimeframeAnalyzer
)


class TestMultiTimeframeAnalyzer:
    """测试多时间框架分析器"""

    def test_initialization(self):
        """测试初始化"""
        analyzer = MultiTimeframeAnalyzer()
        assert len(analyzer.analyzed_timeframes) == 0

    def test_add_timeframe_signal(self):
        """测试添加时间框架信号"""
        analyzer = MultiTimeframeAnalyzer()

        signal1 = TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=90,
            signal_count=3,
            parameters={"period": "60min"}
        )

        signal2 = TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=90,
            confidence=85,
            signal_count=2,
            parameters={"period": "daily"}
        )

        analyzer.add_timeframe_signal(signal1)
        analyzer.add_timeframe_signal(signal2)

        assert len(analyzer.analyzed_timeframes) == 2
        assert TimeframeType.MIN60 in analyzer.analyzed_timeframes
        assert TimeframeType.DAILY in analyzer.analyzed_timeframes

    def test_remove_timeframe_signal(self):
        """测试移除时间框架信号"""
        analyzer = MultiTimeframeAnalyzer()

        signal = TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=90,
            signal_count=3
        )

        analyzer.add_timeframe_signal(signal)
        analyzer.remove_timeframe_signal(TimeframeType.MIN60)

        assert len(analyzer.analyzed_timeframes) == 0
        assert TimeframeType.MIN60 not in analyzer.analyzed_timeframes

    def test_clear_all_signals(self):
        """测试清除所有信号"""
        analyzer = MultiTimeframeAnalyzer()

        signal1 = TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=90,
            signal_count=3
        )

        signal2 = TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=90,
            confidence=85,
            signal_count=2
        )

        analyzer.add_timeframe_signal(signal1)
        analyzer.add_timeframe_signal(signal2)
        analyzer.clear_all_signals()

        assert len(analyzer.analyzed_timeframes) == 0

    def test_set_timeframe_weight(self):
        """测试设置时间框架权重"""
        analyzer = MultiTimeframeAnalyzer()
        original_weight = analyzer.timeframe_weights[TimeframeType.DAILY]

        analyzer.set_timeframe_weight(TimeframeType.DAILY, 10.0)
        assert analyzer.timeframe_weights[TimeframeType.DAILY] == 10.0

        analyzer.set_timeframe_weight(TimeframeType.DAILY, original_weight)
        assert analyzer.timeframe_weights[TimeframeType.DAILY] == original_weight

    def test_set_invalid_weight(self):
        """测试设置无效权重"""
        analyzer = MultiTimeframeAnalyzer()

        with pytest.raises(ValueError):
            analyzer.set_timeframe_weight(TimeframeType.DAILY, 0)

        with pytest.raises(ValueError):
            analyzer.set_timeframe_weight(TimeframeType.DAILY, -1)

    def test_analyze_bullish_trend_confirmation(self):
        """测试看涨趋势确认"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=90,
            confidence=85,
            signal_count=2
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN240,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=90,
            signal_count=3
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BULLISH,
            strength=80,
            confidence=80,
            signal_count=4
        ))

        result = analyzer.analyze()

        assert result.overall_trend == TrendType.BULLISH
        assert result.confirmation_score > 70
        assert result.dominant_timeframe == TimeframeType.DAILY
        assert result.signal_summary[TrendType.BULLISH] == 3

    def test_analyze_bearish_trend_confirmation(self):
        """测试看跌趋势确认"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BEARISH,
            strength=88,
            confidence=82,
            signal_count=2
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN240,
            trend=TrendType.BEARISH,
            strength=92,
            confidence=88,
            signal_count=3
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BEARISH,
            strength=75,
            confidence=70,
            signal_count=4
        ))

        result = analyzer.analyze()

        assert result.overall_trend == TrendType.BEARISH
        assert result.confirmation_score > 70
        assert result.signal_summary[TrendType.BEARISH] == 3

    def test_analyze_conflicting_trends(self):
        """测试冲突趋势"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=90,
            confidence=85,
            signal_count=2
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BEARISH,
            strength=85,
            confidence=90,
            signal_count=3
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN15,
            trend=TrendType.SIDEWAYS,
            strength=70,
            confidence=75,
            signal_count=1
        ))

        result = analyzer.analyze()

        assert result.overall_trend == TrendType.UNCERTAIN
        assert result.confirmation_score < 50
        assert result.signal_summary[TrendType.BULLISH] == 1
        assert result.signal_summary[TrendType.BEARISH] == 1
        assert result.signal_summary[TrendType.SIDEWAYS] == 1

    def test_analyze_single_timeframe(self):
        """测试单个时间框架分析"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=90,
            signal_count=3
        ))

        result = analyzer.analyze()

        assert result.overall_trend == TrendType.BULLISH
        assert result.confirmation_score > 80
        assert result.dominant_timeframe == TimeframeType.MIN60
        assert result.signal_summary[TrendType.BULLISH] == 1

    def test_analyze_no_timeframes(self):
        """测试无时间框架分析"""
        analyzer = MultiTimeframeAnalyzer()
        result = analyzer.analyze()

        assert result.overall_trend == TrendType.UNCERTAIN
        assert result.confirmation_score == 0
        assert result.dominant_timeframe is None
        assert len(result.timeframe_signals) == 0

    def test_get_trend_confirmation(self):
        """测试获取趋势确认度"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=90,
            confidence=85,
            signal_count=2
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN240,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=90,
            signal_count=3
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BEARISH,
            strength=75,
            confidence=70,
            signal_count=4
        ))

        bullish_confirmation = analyzer.get_trend_confirmation(TrendType.BULLISH)
        bearish_confirmation = analyzer.get_trend_confirmation(TrendType.BEARISH)

        assert bullish_confirmation > bearish_confirmation
        assert 50 < bullish_confirmation < 100
        assert 0 < bearish_confirmation < 50

    def test_is_trend_confirmed(self):
        """测试趋势确认检查"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=90,
            confidence=85,
            signal_count=2
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN240,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=90,
            signal_count=3
        ))

        assert analyzer.is_trend_confirmed(TrendType.BULLISH)
        assert not analyzer.is_trend_confirmed(TrendType.BEARISH)
        assert not analyzer.is_trend_confirmed(TrendType.SIDEWAYS)

    def test_get_signal_count_by_trend(self):
        """测试按趋势获取信号数量"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=90,
            confidence=85,
            signal_count=2
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN240,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=90,
            signal_count=3
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BEARISH,
            strength=75,
            confidence=70,
            signal_count=4
        ))

        assert analyzer.get_signal_count_by_trend(TrendType.BULLISH) == 2
        assert analyzer.get_signal_count_by_trend(TrendType.BEARISH) == 1
        assert analyzer.get_signal_count_by_trend(TrendType.SIDEWAYS) == 0

    def test_get_timeframe_summary(self):
        """测试获取时间框架摘要"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=90,
            confidence=85,
            signal_count=2
        ))

        summary = analyzer.get_timeframe_summary()

        assert len(summary) == 1
        assert summary[0]["timeframe"] == "daily"
        assert summary[0]["trend"] == "BULLISH"
        assert summary[0]["strength"] == 90
        assert summary[0]["confidence"] == 85
        assert summary[0]["signal_count"] == 2
        assert summary[0]["weight"] > 0

    def test_correlation_calculation(self):
        """测试相关性计算"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=90,
            confidence=85,
            signal_count=2
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN240,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=90,
            signal_count=3
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BEARISH,
            strength=75,
            confidence=70,
            signal_count=4
        ))

        result = analyzer.analyze()

        assert "daily_240min" in result.correlation_matrix
        assert "daily_60min" in result.correlation_matrix
        assert "240min_60min" in result.correlation_matrix

        assert result.correlation_matrix["daily_240min"] > 70
        assert result.correlation_matrix["daily_60min"] < 30
        assert result.correlation_matrix["240min_60min"] < 30

    def test_weighted_trend_calculation(self):
        """测试加权趋势计算"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN15,
            trend=TrendType.BULLISH,
            strength=95,
            confidence=90,
            signal_count=5
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BEARISH,
            strength=80,
            confidence=85,
            signal_count=2
        ))

        result = analyzer.analyze()

        assert result.overall_trend == TrendType.BEARISH
        assert result.dominant_timeframe == TimeframeType.DAILY

    def test_dominant_timeframe(self):
        """测试主导时间框架确定"""
        analyzer = MultiTimeframeAnalyzer()

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN15,
            trend=TrendType.BULLISH,
            strength=95,
            confidence=90,
            signal_count=5
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.MIN60,
            trend=TrendType.BULLISH,
            strength=85,
            confidence=85,
            signal_count=3
        ))

        analyzer.add_timeframe_signal(TimeframeSignal(
            timeframe=TimeframeType.DAILY,
            trend=TrendType.BULLISH,
            strength=80,
            confidence=80,
            signal_count=2
        ))

        result = analyzer.analyze()
        assert result.dominant_timeframe == TimeframeType.DAILY
