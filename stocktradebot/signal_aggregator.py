"""
信号聚合器模块
用于将多个技术指标的信号进行聚合和权重计算
支持多种聚合策略，提供统一的信号输出
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型枚举"""
    BULLISH = "BULLISH"      # 看涨信号
    BEARISH = "BEARISH"      # 看跌信号
    NEUTRAL = "NEUTRAL"      # 中性信号
    WEAK_BULLISH = "WEAK_BULLISH"  # 弱看涨
    WEAK_BEARISH = "WEAK_BEARISH"  # 弱看跌


class AggregationStrategy(Enum):
    """信号聚合策略"""
    WEIGHTED_VOTE = "weighted_vote"    # 加权投票
    MAJORITY_VOTE = "majority_vote"    # 多数投票
    AVERAGE_STRENGTH = "average_strength"  # 平均强度
    STRONG_SIGNAL_ONLY = "strong_signal_only"  # 仅强信号


@dataclass
class IndicatorSignal:
    """单个指标的信号"""
    indicator_name: str
    signal_type: SignalType
    strength: float  # 信号强度 (0-100)
    confidence: float  # 置信度 (0-100)
    parameters: Dict = field(default_factory=dict)


@dataclass
class AggregatedSignal:
    """聚合后的信号"""
    signal_type: SignalType
    strength: float  # 聚合强度 (0-100)
    confidence: float  # 聚合置信度 (0-100)
    indicator_signals: List[IndicatorSignal] = field(default_factory=list)
    vote_counts: Dict[SignalType, int] = field(default_factory=dict)
    weight_distribution: Dict[str, float] = field(default_factory=dict)


class SignalAggregator:
    """信号聚合器"""

    def __init__(self, strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_VOTE):
        """
        初始化信号聚合器

        Args:
            strategy: 聚合策略
        """
        self.indicators: Dict[str, float] = {}  # 指标名称: 权重
        self.strategy = strategy
        logger.debug(f"信号聚合器初始化，策略: {strategy.value}")

    def add_indicator(self, indicator_name: str, weight: float = 1.0):
        """
        添加指标到聚合器

        Args:
            indicator_name: 指标名称
            weight: 指标权重 (默认1.0)
        """
        if weight <= 0:
            raise ValueError("权重必须大于0")

        self.indicators[indicator_name] = weight
        logger.debug(f"添加指标: {indicator_name}, 权重: {weight}")

    def remove_indicator(self, indicator_name: str):
        """
        从聚合器中移除指标

        Args:
            indicator_name: 指标名称
        """
        if indicator_name in self.indicators:
            del self.indicators[indicator_name]
            logger.debug(f"移除指标: {indicator_name}")

    def set_weight(self, indicator_name: str, weight: float):
        """
        设置指标权重

        Args:
            indicator_name: 指标名称
            weight: 新权重
        """
        if indicator_name not in self.indicators:
            raise ValueError(f"指标 {indicator_name} 不存在")

        if weight <= 0:
            raise ValueError("权重必须大于0")

        self.indicators[indicator_name] = weight
        logger.debug(f"更新指标权重: {indicator_name} = {weight}")

    def get_total_weight(self) -> float:
        """获取总权重"""
        return sum(self.indicators.values())

    def aggregate(self, signals: List[IndicatorSignal]) -> AggregatedSignal:
        """
        聚合多个指标的信号

        Args:
            signals: 指标信号列表

        Returns:
            聚合后的信号
        """
        if not signals:
            logger.warning("没有信号可聚合")
            return AggregatedSignal(
                signal_type=SignalType.NEUTRAL,
                strength=0,
                confidence=0,
                indicator_signals=[],
                vote_counts={},
                weight_distribution={}
            )

        # 验证输入信号的指标是否已在聚合器中
        valid_signals = []
        for signal in signals:
            if signal.indicator_name in self.indicators:
                valid_signals.append(signal)
            else:
                logger.warning(f"指标 {signal.indicator_name} 未在聚合器中配置，忽略")

        if not valid_signals:
            logger.warning("没有有效的信号可聚合")
            return AggregatedSignal(
                signal_type=SignalType.NEUTRAL,
                strength=0,
                confidence=0,
                indicator_signals=[],
                vote_counts={},
                weight_distribution={}
            )

        logger.debug(f"开始聚合 {len(valid_signals)} 个有效信号")

        if self.strategy == AggregationStrategy.WEIGHTED_VOTE:
            return self._weighted_vote(valid_signals)
        elif self.strategy == AggregationStrategy.MAJORITY_VOTE:
            return self._majority_vote(valid_signals)
        elif self.strategy == AggregationStrategy.AVERAGE_STRENGTH:
            return self._average_strength(valid_signals)
        elif self.strategy == AggregationStrategy.STRONG_SIGNAL_ONLY:
            return self._strong_signal_only(valid_signals)
        else:
            raise ValueError(f"不支持的聚合策略: {self.strategy}")

    def _weighted_vote(self, signals: List[IndicatorSignal]) -> AggregatedSignal:
        """
        加权投票聚合策略

        Args:
            signals: 有效信号列表

        Returns:
            聚合信号
        """
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = self.get_total_weight()

        for signal in signals:
            weight = self.indicators[signal.indicator_name]
            strength = signal.strength / 100
            confidence = signal.confidence / 100

            if signal.signal_type in [SignalType.BULLISH, SignalType.WEAK_BULLISH]:
                score = strength * confidence
                bullish_score += score * weight
            elif signal.signal_type in [SignalType.BEARISH, SignalType.WEAK_BEARISH]:
                score = strength * confidence
                bearish_score += score * weight

        net_score = bullish_score - bearish_score
        normalized_score = net_score / total_weight

        # 确定信号类型
        if normalized_score > 0.6:
            signal_type = SignalType.BULLISH
        elif normalized_score > 0.3:
            signal_type = SignalType.WEAK_BULLISH
        elif normalized_score < -0.6:
            signal_type = SignalType.BEARISH
        elif normalized_score < -0.3:
            signal_type = SignalType.WEAK_BEARISH
        else:
            signal_type = SignalType.NEUTRAL

        # 计算强度和置信度
        strength = min(abs(normalized_score) * 100, 100)
        confidence = self._calculate_confidence(signals)

        # 统计投票
        vote_counts = self._count_votes(signals)

        return AggregatedSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            indicator_signals=signals,
            vote_counts=vote_counts,
            weight_distribution=self._get_weight_distribution(signals)
        )

    def _majority_vote(self, signals: List[IndicatorSignal]) -> AggregatedSignal:
        """
        多数投票聚合策略

        Args:
            signals: 有效信号列表

        Returns:
            聚合信号
        """
        vote_counts = self._count_votes(signals)

        # 确定多数信号
        max_votes = 0
        dominant_signal = SignalType.NEUTRAL

        for signal_type, count in vote_counts.items():
            if count > max_votes:
                max_votes = count
                dominant_signal = signal_type

        # 计算强度和置信度
        strength = (max_votes / len(signals)) * 100
        confidence = self._calculate_confidence(signals)

        return AggregatedSignal(
            signal_type=dominant_signal,
            strength=strength,
            confidence=confidence,
            indicator_signals=signals,
            vote_counts=vote_counts,
            weight_distribution=self._get_weight_distribution(signals)
        )

    def _average_strength(self, signals: List[IndicatorSignal]) -> AggregatedSignal:
        """
        平均强度聚合策略

        Args:
            signals: 有效信号列表

        Returns:
            聚合信号
        """
        total_score = 0.0
        count = 0

        for signal in signals:
            if signal.signal_type == SignalType.BULLISH:
                total_score += signal.strength
            elif signal.signal_type == SignalType.WEAK_BULLISH:
                total_score += signal.strength * 0.5
            elif signal.signal_type == SignalType.BEARISH:
                total_score -= signal.strength
            elif signal.signal_type == SignalType.WEAK_BEARISH:
                total_score -= signal.strength * 0.5

            count += 1

        average_score = total_score / count if count > 0 else 0

        # 确定信号类型
        if average_score > 60:
            signal_type = SignalType.BULLISH
        elif average_score > 30:
            signal_type = SignalType.WEAK_BULLISH
        elif average_score < -60:
            signal_type = SignalType.BEARISH
        elif average_score < -30:
            signal_type = SignalType.WEAK_BEARISH
        else:
            signal_type = SignalType.NEUTRAL

        strength = min(abs(average_score), 100)
        confidence = self._calculate_confidence(signals)
        vote_counts = self._count_votes(signals)

        return AggregatedSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            indicator_signals=signals,
            vote_counts=vote_counts,
            weight_distribution=self._get_weight_distribution(signals)
        )

    def _strong_signal_only(self, signals: List[IndicatorSignal]) -> AggregatedSignal:
        """
        仅强信号聚合策略

        Args:
            signals: 有效信号列表

        Returns:
            聚合信号
        """
        # 过滤强信号
        strong_signals = []
        for signal in signals:
            if signal.signal_type in [SignalType.BULLISH, SignalType.BEARISH] and \
               signal.strength > 70 and signal.confidence > 70:
                strong_signals.append(signal)

        if not strong_signals:
            return AggregatedSignal(
                signal_type=SignalType.NEUTRAL,
                strength=0,
                confidence=0,
                indicator_signals=signals,
                vote_counts=self._count_votes(signals),
                weight_distribution=self._get_weight_distribution(signals)
            )

        # 对强信号使用多数投票
        vote_counts = self._count_votes(strong_signals)

        max_votes = 0
        dominant_signal = SignalType.NEUTRAL

        for signal_type, count in vote_counts.items():
            if count > max_votes:
                max_votes = count
                dominant_signal = signal_type

        strength = (max_votes / len(strong_signals)) * 100
        confidence = self._calculate_confidence(strong_signals)

        return AggregatedSignal(
            signal_type=dominant_signal,
            strength=strength,
            confidence=confidence,
            indicator_signals=signals,
            vote_counts=vote_counts,
            weight_distribution=self._get_weight_distribution(strong_signals)
        )

    def _count_votes(self, signals: List[IndicatorSignal]) -> Dict[SignalType, int]:
        """
        统计信号投票

        Args:
            signals: 信号列表

        Returns:
            信号类型计数
        """
        vote_counts = {
            SignalType.BULLISH: 0,
            SignalType.BEARISH: 0,
            SignalType.NEUTRAL: 0,
            SignalType.WEAK_BULLISH: 0,
            SignalType.WEAK_BEARISH: 0
        }

        for signal in signals:
            vote_counts[signal.signal_type] += 1

        return vote_counts

    def _calculate_confidence(self, signals: List[IndicatorSignal]) -> float:
        """
        计算平均置信度

        Args:
            signals: 信号列表

        Returns:
            平均置信度
        """
        if not signals:
            return 0.0

        total_confidence = sum(signal.confidence for signal in signals)
        return total_confidence / len(signals)

    def _get_weight_distribution(self, signals: List[IndicatorSignal]) -> Dict[str, float]:
        """
        获取指标权重分布

        Args:
            signals: 信号列表

        Returns:
            指标名称到权重的映射
        """
        distribution = {}
        total_weight = self.get_total_weight()

        for signal in signals:
            weight = self.indicators[signal.indicator_name]
            distribution[signal.indicator_name] = (weight / total_weight) * 100

        return distribution

    def get_indicator_summary(self) -> Dict[str, float]:
        """
        获取指标配置摘要

        Returns:
            指标名称到权重的映射
        """
        return self.indicators.copy()

    def clear_indicators(self):
        """清除所有指标配置"""
        self.indicators.clear()
        logger.debug("已清除所有指标配置")

    def __str__(self):
        """字符串表示"""
        indicators_info = ", ".join(
            f"{name}: {weight}" for name, weight in self.indicators.items()
        )
        return f"SignalAggregator(strategy={self.strategy.value}, indicators=[{indicators_info}])"

    def __repr__(self):
        """详细表示"""
        return self.__str__()
