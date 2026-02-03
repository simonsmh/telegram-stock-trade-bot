"""
多时间框架分析器模块
用于分析不同时间框架的信号，提供趋势确认和综合分析
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class TimeframeType(Enum):
    """时间框架类型枚举"""
    MIN1 = "1min"
    MIN5 = "5min"
    MIN15 = "15min"
    MIN30 = "30min"
    MIN60 = "60min"
    MIN120 = "120min"
    MIN240 = "240min"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TrendType(Enum):
    """趋势类型枚举"""
    BULLISH = "BULLISH"          # 看涨趋势
    BEARISH = "BEARISH"          # 看跌趋势
    SIDEWAYS = "SIDEWAYS"        # 横盘整理
    CONFLICTING = "CONFLICTING"  # 冲突趋势
    UNCERTAIN = "UNCERTAIN"      # 趋势不明


@dataclass
class TimeframeSignal:
    """时间框架信号"""
    timeframe: TimeframeType
    trend: TrendType
    strength: float  # 趋势强度 (0-100)
    confidence: float  # 置信度 (0-100)
    signal_count: int  # 信号数量
    parameters: Dict = field(default_factory=dict)


@dataclass
class MultiTimeframeAnalysis:
    """多时间框架分析结果"""
    overall_trend: TrendType
    confirmation_score: float  # 趋势确认分数 (0-100)
    timeframe_signals: List[TimeframeSignal] = field(default_factory=list)
    timeframe_weights: Dict[TimeframeType, float] = field(default_factory=dict)
    correlation_matrix: Dict[str, float] = field(default_factory=dict)
    dominant_timeframe: Optional[TimeframeType] = None
    signal_summary: Dict[TrendType, int] = field(default_factory=dict)


class MultiTimeframeAnalyzer:
    """多时间框架分析器"""

    # 默认时间框架权重（越高的时间框架权重越大）
    DEFAULT_WEIGHTS = {
        TimeframeType.MIN1: 0.5,
        TimeframeType.MIN5: 1.0,
        TimeframeType.MIN15: 1.5,
        TimeframeType.MIN30: 2.0,
        TimeframeType.MIN60: 3.0,
        TimeframeType.MIN120: 4.0,
        TimeframeType.MIN240: 5.0,
        TimeframeType.DAILY: 6.0,
        TimeframeType.WEEKLY: 7.0,
        TimeframeType.MONTHLY: 8.0
    }

    def __init__(self, custom_weights: Dict[TimeframeType, float] = None):
        """
        初始化多时间框架分析器

        Args:
            custom_weights: 自定义时间框架权重
        """
        self.timeframe_weights = custom_weights or self.DEFAULT_WEIGHTS.copy()
        self.analyzed_timeframes: Dict[TimeframeType, TimeframeSignal] = {}
        logger.debug("多时间框架分析器初始化")

    def add_timeframe_signal(self, signal: TimeframeSignal):
        """
        添加时间框架信号

        Args:
            signal: 时间框架信号
        """
        self.analyzed_timeframes[signal.timeframe] = signal
        logger.debug(f"添加时间框架信号: {signal.timeframe.value}, 趋势: {signal.trend.value}, 强度: {signal.strength}")

    def remove_timeframe_signal(self, timeframe: TimeframeType):
        """
        移除时间框架信号

        Args:
            timeframe: 时间框架类型
        """
        if timeframe in self.analyzed_timeframes:
            del self.analyzed_timeframes[timeframe]
            logger.debug(f"移除时间框架信号: {timeframe.value}")

    def clear_all_signals(self):
        """清除所有时间框架信号"""
        self.analyzed_timeframes.clear()
        logger.debug("已清除所有时间框架信号")

    def set_timeframe_weight(self, timeframe: TimeframeType, weight: float):
        """
        设置时间框架权重

        Args:
            timeframe: 时间框架类型
            weight: 权重值
        """
        if weight <= 0:
            raise ValueError("权重必须大于0")

        self.timeframe_weights[timeframe] = weight
        logger.debug(f"设置时间框架权重: {timeframe.value} = {weight}")

    def analyze(self) -> MultiTimeframeAnalysis:
        """
        执行多时间框架分析

        Returns:
            分析结果
        """
        if not self.analyzed_timeframes:
            logger.warning("没有可分析的时间框架信号")
            return MultiTimeframeAnalysis(
                overall_trend=TrendType.UNCERTAIN,
                confirmation_score=0,
                timeframe_signals=[],
                timeframe_weights={},
                correlation_matrix={},
                dominant_timeframe=None,
                signal_summary={}
            )

        logger.debug(f"开始分析 {len(self.analyzed_timeframes)} 个时间框架")

        # 计算信号摘要
        signal_summary = self._calculate_signal_summary()

        # 计算趋势确认分数
        confirmation_score = self._calculate_confirmation_score()

        # 确定整体趋势
        overall_trend = self._determine_overall_trend(signal_summary, confirmation_score)

        # 计算时间框架权重分布
        timeframe_weights = self._get_active_timeframe_weights()

        # 确定主导时间框架
        dominant_timeframe = self._find_dominant_timeframe()

        # 计算相关性矩阵
        correlation_matrix = self._calculate_correlation()

        # 构建分析结果
        result = MultiTimeframeAnalysis(
            overall_trend=overall_trend,
            confirmation_score=confirmation_score,
            timeframe_signals=list(self.analyzed_timeframes.values()),
            timeframe_weights=timeframe_weights,
            correlation_matrix=correlation_matrix,
            dominant_timeframe=dominant_timeframe,
            signal_summary=signal_summary
        )

        logger.debug(f"分析完成: 整体趋势={result.overall_trend.value}, 确认分数={result.confirmation_score:.1f}")
        return result

    def _calculate_signal_summary(self) -> Dict[TrendType, int]:
        """
        计算信号摘要

        Returns:
            不同趋势类型的信号数量
        """
        summary = {
            TrendType.BULLISH: 0,
            TrendType.BEARISH: 0,
            TrendType.SIDEWAYS: 0,
            TrendType.CONFLICTING: 0,
            TrendType.UNCERTAIN: 0
        }

        for signal in self.analyzed_timeframes.values():
            summary[signal.trend] += 1

        return summary

    def _calculate_confirmation_score(self) -> float:
        """
        计算趋势确认分数

        Returns:
            确认分数 (0-100)
        """
        if not self.analyzed_timeframes:
            return 0.0

        # 统计不同趋势类型的加权总和
        trend_scores = {
            TrendType.BULLISH: 0.0,
            TrendType.BEARISH: 0.0,
            TrendType.SIDEWAYS: 0.0,
            TrendType.CONFLICTING: 0.0,
            TrendType.UNCERTAIN: 0.0
        }

        total_weight = 0.0

        for timeframe, signal in self.analyzed_timeframes.items():
            weight = self.timeframe_weights.get(timeframe, 1.0)
            trend_scores[signal.trend] += weight * signal.confidence
            total_weight += weight * 100  # 最大置信度为100

        # 计算各个趋势的得分占比
        trend_percentages = {}
        for trend, score in trend_scores.items():
            trend_percentages[trend] = (score / total_weight) * 100 if total_weight > 0 else 0

        # 确认分数基于主要趋势的集中度
        bullish_pct = trend_percentages[TrendType.BULLISH]
        bearish_pct = trend_percentages[TrendType.BEARISH]
        sideways_pct = trend_percentages[TrendType.SIDEWAYS]

        if bullish_pct > bearish_pct and bullish_pct > sideways_pct:
            return bullish_pct
        elif bearish_pct > bullish_pct and bearish_pct > sideways_pct:
            return bearish_pct
        elif sideways_pct > bullish_pct and sideways_pct > bearish_pct:
            return sideways_pct
        else:
            return max(bullish_pct, bearish_pct, sideways_pct)

    def _determine_overall_trend(self, signal_summary: Dict[TrendType, int], confirmation_score: float) -> TrendType:
        """
        确定整体趋势

        Args:
            signal_summary: 信号摘要
            confirmation_score: 确认分数

        Returns:
            整体趋势类型
        """
        bullish_count = signal_summary[TrendType.BULLISH]
        bearish_count = signal_summary[TrendType.BEARISH]
        sideways_count = signal_summary[TrendType.SIDEWAYS]
        uncertain_count = signal_summary[TrendType.UNCERTAIN]
        conflicting_count = signal_summary[TrendType.CONFLICTING]

        total_signals = sum(signal_summary.values())

        # 如果有大量不确定或冲突信号，返回不确定
        if uncertain_count + conflicting_count >= total_signals * 0.5:
            return TrendType.UNCERTAIN

        # 如果确认分数较低，返回不确定
        if confirmation_score < 30:
            return TrendType.UNCERTAIN

        # 判断主要趋势
        if bullish_count > bearish_count and bullish_count > sideways_count:
            return TrendType.BULLISH
        elif bearish_count > bullish_count and bearish_count > sideways_count:
            return TrendType.BEARISH
        elif sideways_count > bullish_count and sideways_count > bearish_count:
            return TrendType.SIDEWAYS
        else:
            # 趋势平衡，需要看强度
            if confirmation_score < 50:
                return TrendType.UNCERTAIN
            else:
                # 看加权平均强度
                return self._get_weighted_trend()

    def _get_weighted_trend(self) -> TrendType:
        """
        获取加权平均趋势

        Returns:
            加权平均趋势
        """
        bullish_score = 0.0
        bearish_score = 0.0
        sideways_score = 0.0
        total_weight = 0.0

        for timeframe, signal in self.analyzed_timeframes.items():
            weight = self.timeframe_weights.get(timeframe, 1.0)
            strength = signal.strength
            confidence = signal.confidence

            total_weight += weight

            if signal.trend == TrendType.BULLISH:
                bullish_score += weight * strength * confidence
            elif signal.trend == TrendType.BEARISH:
                bearish_score += weight * strength * confidence
            elif signal.trend == TrendType.SIDEWAYS:
                sideways_score += weight * strength * confidence

        if bullish_score > bearish_score and bullish_score > sideways_score:
            return TrendType.BULLISH
        elif bearish_score > bullish_score and bearish_score > sideways_score:
            return TrendType.BEARISH
        elif sideways_score > bullish_score and sideways_score > bearish_score:
            return TrendType.SIDEWAYS
        else:
            return TrendType.UNCERTAIN

    def _find_dominant_timeframe(self) -> Optional[TimeframeType]:
        """
        找到主导时间框架（权重最高且信号强度高的时间框架）

        Returns:
            主导时间框架
        """
        if not self.analyzed_timeframes:
            return None

        max_score = 0.0
        dominant = None

        for timeframe, signal in self.analyzed_timeframes.items():
            weight = self.timeframe_weights.get(timeframe, 1.0)
            score = weight * signal.strength * signal.confidence

            if score > max_score:
                max_score = score
                dominant = timeframe

        return dominant

    def _calculate_correlation(self) -> Dict[str, float]:
        """
        计算时间框架间的相关性

        Returns:
            相关性字典
        """
        correlation = {}
        timeframes = list(self.analyzed_timeframes.keys())

        for i, tf1 in enumerate(timeframes):
            for j, tf2 in enumerate(timeframes):
                if i < j:
                    key = f"{tf1.value}_{tf2.value}"
                    correlation[key] = self._calculate_pair_correlation(tf1, tf2)

        return correlation

    def _calculate_pair_correlation(self, tf1: TimeframeType, tf2: TimeframeType) -> float:
        """
        计算两个时间框架间的相关性

        Args:
            tf1: 第一个时间框架
            tf2: 第二个时间框架

        Returns:
            相关性分数 (0-100)
        """
        signal1 = self.analyzed_timeframes[tf1]
        signal2 = self.analyzed_timeframes[tf2]

        # 趋势方向相同则相关性高
        if signal1.trend == signal2.trend:
            # 基于强度和置信度的一致性
            strength_consistency = 1 - abs(signal1.strength - signal2.strength) / 100
            confidence_consistency = 1 - abs(signal1.confidence - signal2.confidence) / 100
            return (strength_consistency + confidence_consistency) * 50
        else:
            return 0

    def _get_active_timeframe_weights(self) -> Dict[TimeframeType, float]:
        """
        获取活跃时间框架的权重分布

        Returns:
            活跃时间框架的权重
        """
        weights = {}
        total_weight = 0.0

        for timeframe, signal in self.analyzed_timeframes.items():
            weight = self.timeframe_weights.get(timeframe, 1.0)
            weights[timeframe] = weight
            total_weight += weight

        # 归一化权重
        normalized = {}
        if total_weight > 0:
            for timeframe, weight in weights.items():
                normalized[timeframe] = (weight / total_weight) * 100

        return normalized

    def get_timeframe_summary(self) -> List[Dict]:
        """
        获取时间框架摘要

        Returns:
            时间框架摘要列表
        """
        summary = []
        for timeframe, signal in self.analyzed_timeframes.items():
            summary.append({
                "timeframe": timeframe.value,
                "trend": signal.trend.value,
                "strength": signal.strength,
                "confidence": signal.confidence,
                "signal_count": signal.signal_count,
                "weight": self.timeframe_weights.get(timeframe, 1.0)
            })
        return summary

    def get_trend_confirmation(self, target_trend: TrendType) -> float:
        """
        获取特定趋势的确认度

        Args:
            target_trend: 目标趋势

        Returns:
            确认度 (0-100)
        """
        if not self.analyzed_timeframes:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for timeframe, signal in self.analyzed_timeframes.items():
            weight = self.timeframe_weights.get(timeframe, 1.0)

            if signal.trend == target_trend:
                score = weight * signal.strength * signal.confidence
                total_score += score

            total_weight += weight * 100 * 100  # 最大强度和置信度

        confirmation = (total_score / total_weight) * 100 if total_weight > 0 else 0

        return min(confirmation, 100)

    def is_trend_confirmed(self, trend: TrendType, minimum_score: float = 60) -> bool:
        """
        检查趋势是否得到确认

        Args:
            trend: 要检查的趋势
            minimum_score: 最低确认分数

        Returns:
            是否确认
        """
        confirmation_score = self.get_trend_confirmation(trend)
        return confirmation_score >= minimum_score

    def get_signal_count_by_trend(self, trend: TrendType) -> int:
        """
        获取特定趋势的信号数量

        Args:
            trend: 趋势类型

        Returns:
            信号数量
        """
        count = 0
        for signal in self.analyzed_timeframes.values():
            if signal.trend == trend:
                count += 1
        return count

    def __str__(self):
        """字符串表示"""
        active_timeframes = len(self.analyzed_timeframes)
        return f"MultiTimeframeAnalyzer(active_timeframes={active_timeframes})"

    def __repr__(self):
        """详细表示"""
        return self.__str__()
