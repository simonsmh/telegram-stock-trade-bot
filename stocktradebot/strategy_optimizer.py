"""
策略优化器模块
用于策略参数的网格搜索优化
支持多种优化目标和并行计算
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union, Callable
import logging
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
import pandas as pd

from .combination_strategies import (
    CombinationStrategies,
    CombinationStrategy,
    StrategyType,
    StrategyParameter,
    StrategyConfig,
    StrategyPerformance,
    StrategyStatus
)
from .signal_aggregator import AggregationStrategy
from .multi_timeframe import TimeframeType

logger = logging.getLogger(__name__)


class OptimizationObjective(Enum):
    """优化目标枚举"""
    TOTAL_RETURN = "total_return"
    WIN_RATE = "win_rate"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    PROFIT_FACTOR = "profit_factor"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_LOSS_RATIO = "win_loss_ratio"


class OptimizationMethod(Enum):
    """优化方法枚举"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"


@dataclass
class OptimizationParameter:
    """优化参数配置"""
    name: str
    values: List[Union[int, float]]
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None


@dataclass
class OptimizationResult:
    """优化结果"""
    parameters: Dict[str, Union[int, float]]
    performance: StrategyPerformance
    rank: int = 0
    score: float = 0.0


@dataclass
class OptimizationConfig:
    """优化配置"""
    objective: OptimizationObjective = OptimizationObjective.TOTAL_RETURN
    method: OptimizationMethod = OptimizationMethod.GRID_SEARCH
    max_workers: int = 4
    max_trials: int = 100
    timeout: float = 3600.0
    early_stop: bool = False
    early_stop_rounds: int = 20
    initial_parameters: Dict[str, Union[int, float]] = field(default_factory=dict)
    parameter_bounds: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class OptimizationProgress:
    """优化进度"""
    current_trial: int = 0
    total_trials: int = 0
    best_score: float = 0.0
    best_parameters: Dict = field(default_factory=dict)
    completed_trials: int = 0
    failed_trials: int = 0
    elapsed_time: float = 0.0
    remaining_time: float = 0.0
    status: str = "running"


class StrategyOptimizer:
    """策略优化器"""

    def __init__(self, strategy_manager: CombinationStrategies = None):
        """
        初始化策略优化器

        Args:
            strategy_manager: 策略管理器
        """
        self.strategy_manager = strategy_manager or CombinationStrategies()
        self.results: List[OptimizationResult] = []
        self.progress: OptimizationProgress = OptimizationProgress()
        logger.debug("策略优化器初始化")

    def optimize_strategy(self, strategy: CombinationStrategy, df: pd.DataFrame,
                        config: OptimizationConfig,
                        parameters: List[OptimizationParameter],
                        callback: Optional[Callable[[OptimizationProgress], None]] = None
                        ) -> List[OptimizationResult]:
        """
        优化策略参数

        Args:
            strategy: 策略对象
            df: 历史数据
            config: 优化配置
            parameters: 优化参数配置
            callback: 进度回调函数

        Returns:
            优化结果列表（按得分排序）
        """
        logger.debug(f"开始优化策略: {strategy.strategy_id}, 方法: {config.method.value}")
        strategy.status = StrategyStatus.OPTIMIZING
        self.results = []

        try:
            if config.method == OptimizationMethod.GRID_SEARCH:
                results = self._grid_search(strategy, df, config, parameters, callback)
            elif config.method == OptimizationMethod.RANDOM_SEARCH:
                results = self._random_search(strategy, df, config, parameters, callback)
            else:
                raise ValueError(f"不支持的优化方法: {config.method}")

            # 对结果进行排序
            sorted_results = self._sort_results(results, config.objective)

            strategy.status = StrategyStatus.ACTIVE
            logger.debug(f"策略优化完成: {strategy.strategy_id}, 共 {len(sorted_results)} 个结果")

            return sorted_results

        except Exception as e:
            logger.error(f"策略优化失败 {strategy.strategy_id}: {e}")
            strategy.status = StrategyStatus.ERROR
            raise

    def _grid_search(self, strategy: CombinationStrategy, df: pd.DataFrame,
                   config: OptimizationConfig, parameters: List[OptimizationParameter],
                   callback: Optional[Callable[[OptimizationProgress], None]] = None
                   ) -> List[OptimizationResult]:
        """
        网格搜索优化

        Args:
            strategy: 策略对象
            df: 历史数据
            config: 优化配置
            parameters: 优化参数
            callback: 进度回调

        Returns:
            优化结果
        """
        # 生成参数网格
        parameter_grid = self._generate_grid(parameters)
        logger.debug(f"参数网格大小: {len(parameter_grid)}")

        self.progress.total_trials = len(parameter_grid)
        self.progress.current_trial = 0
        self.progress.completed_trials = 0
        self.progress.failed_trials = 0

        results = []

        if config.max_workers == 1:
            # 单线程执行
            for params in parameter_grid:
                result = self._evaluate_parameters(strategy, df, params)
                if result:
                    results.append(result)
                self._update_progress(callback)
        else:
            # 多线程执行
            with ProcessPoolExecutor(max_workers=config.max_workers) as executor:
                futures = []
                for params in parameter_grid:
                    future = executor.submit(
                        self._evaluate_parameters, strategy, df, params
                    )
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                    except Exception as e:
                        logger.error(f"参数评估失败: {e}")
                        self.progress.failed_trials += 1
                    self._update_progress(callback)

        logger.debug(f"网格搜索完成，有效结果: {len(results)}")
        return results

    def _random_search(self, strategy: CombinationStrategy, df: pd.DataFrame,
                    config: OptimizationConfig, parameters: List[OptimizationParameter],
                    callback: Optional[Callable[[OptimizationProgress], None]] = None
                    ) -> List[OptimizationResult]:
        """
        随机搜索优化

        Args:
            strategy: 策略对象
            df: 历史数据
            config: 优化配置
            parameters: 优化参数
            callback: 进度回调

        Returns:
            优化结果
        """
        import random

        self.progress.total_trials = config.max_trials
        self.progress.current_trial = 0
        self.progress.completed_trials = 0
        self.progress.failed_trials = 0

        results = []
        seen_params = set()

        while len(results) < config.max_trials:
            # 随机生成参数组合
            params = {}
            for param in parameters:
                params[param.name] = random.choice(param.values)

            # 检查是否已尝试过
            param_hash = str(sorted(params.items()))
            if param_hash in seen_params:
                continue

            seen_params.add(param_hash)

            result = self._evaluate_parameters(strategy, df, params)
            if result:
                results.append(result)
            self._update_progress(callback)

        logger.debug(f"随机搜索完成，有效结果: {len(results)}")
        return results

    def _generate_grid(self, parameters: List[OptimizationParameter]) -> List[Dict]:
        """
        生成参数网格

        Args:
            parameters: 参数配置

        Returns:
            参数组合列表
        """
        param_values = []
        param_names = []

        for param in parameters:
            param_names.append(param.name)
            param_values.append(param.values)

        grid = []
        for values in itertools.product(*param_values):
            params = dict(zip(param_names, values))
            grid.append(params)

        return grid

    def _evaluate_parameters(self, strategy: CombinationStrategy, df: pd.DataFrame,
                           params: Dict[str, Union[int, float]]) -> Optional[OptimizationResult]:
        """
        评估参数组合性能

        Args:
            strategy: 策略对象
            df: 历史数据
            params: 参数组合

        Returns:
            优化结果
        """
        try:
            logger.debug(f"评估参数: {params}")

            # 创建临时策略配置
            temp_config = self._create_temp_config(strategy, params)

            # 创建临时策略进行回测
            temp_strategy = self.strategy_manager.create_strategy(
                strategy_type=strategy.strategy_type,
                strategy_id=f"temp_{strategy.strategy_id}",
                name=f"临时优化策略_{strategy.name}",
                config=temp_config
            )

            performance = self.strategy_manager.backtest_strategy(temp_strategy, df)

            result = OptimizationResult(
                parameters=params,
                performance=performance
            )

            self.strategy_manager.remove_strategy(temp_strategy.strategy_id)

            return result

        except Exception as e:
            logger.error(f"参数评估失败 {params}: {e}")
            return None

    def _create_temp_config(self, strategy: CombinationStrategy,
                           params: Dict[str, Union[int, float]]) -> StrategyConfig:
        """
        创建临时策略配置

        Args:
            strategy: 原策略
            params: 参数组合

        Returns:
            临时策略配置
        """
        temp_config = StrategyConfig(
            strategy_type=strategy.strategy_type,
            parameters=strategy.config.parameters.copy(),
            indicator_weights=strategy.config.indicator_weights.copy(),
            timeframe_weights=strategy.config.timeframe_weights.copy(),
            aggregation_strategy=strategy.config.aggregation_strategy,
            minimum_strength=strategy.config.minimum_strength,
            minimum_confidence=strategy.config.minimum_confidence
        )

        # 更新参数
        for param in temp_config.parameters:
            if param.name in params:
                param.value = params[param.name]

        # 处理权重参数
        for name, value in params.items():
            if name.startswith("weight_"):
                indicator = name.replace("weight_", "")
                if indicator in temp_config.indicator_weights:
                    temp_config.indicator_weights[indicator] = value

        return temp_config

    def _sort_results(self, results: List[OptimizationResult],
                     objective: OptimizationObjective) -> List[OptimizationResult]:
        """
        对结果进行排序

        Args:
            results: 结果列表
            objective: 优化目标

        Returns:
            排序后的结果
        """
        if not results:
            return []

        # 计算得分
        for i, result in enumerate(results):
            result.score = self._calculate_score(result.performance, objective)
            result.rank = i + 1

        # 排序
        if objective in [
            OptimizationObjective.TOTAL_RETURN,
            OptimizationObjective.WIN_RATE,
            OptimizationObjective.SHARPE_RATIO,
            OptimizationObjective.SORTINO_RATIO,
            OptimizationObjective.PROFIT_FACTOR,
            OptimizationObjective.WIN_LOSS_RATIO
        ]:
            sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        elif objective == OptimizationObjective.MAX_DRAWDOWN:
            sorted_results = sorted(results, key=lambda x: x.score)
        else:
            sorted_results = sorted(results, key=lambda x: x.score, reverse=True)

        return sorted_results

    def _calculate_score(self, performance: StrategyPerformance,
                       objective: OptimizationObjective) -> float:
        """
        计算得分

        Args:
            performance: 性能指标
            objective: 优化目标

        Returns:
            得分
        """
        if objective == OptimizationObjective.TOTAL_RETURN:
            return performance.total_return
        elif objective == OptimizationObjective.WIN_RATE:
            return performance.win_rate
        elif objective == OptimizationObjective.SHARPE_RATIO:
            return performance.sharpe_ratio
        elif objective == OptimizationObjective.SORTINO_RATIO:
            return performance.sortino_ratio
        elif objective == OptimizationObjective.PROFIT_FACTOR:
            return performance.profit_factor
        elif objective == OptimizationObjective.MAX_DRAWDOWN:
            return -performance.max_drawdown  # 转成负数以便最大化
        elif objective == OptimizationObjective.WIN_LOSS_RATIO:
            return performance.win_loss_ratio
        else:
            return performance.total_return

    def _update_progress(self, callback: Optional[Callable[[OptimizationProgress], None]] = None):
        """
        更新进度

        Args:
            callback: 进度回调
        """
        self.progress.current_trial += 1
        self.progress.completed_trials += 1

        if len(self.results) > 0:
            best_result = max(self.results, key=lambda x: self._calculate_score(
                x.performance, self.progress.objective if hasattr(self.progress, 'objective') else OptimizationObjective.TOTAL_RETURN
            ))
            self.progress.best_score = self._calculate_score(best_result.performance, OptimizationObjective.TOTAL_RETURN)
            self.progress.best_parameters = best_result.parameters

        if callback:
            callback(self.progress)

    def get_best_result(self, results: List[OptimizationResult]) -> Optional[OptimizationResult]:
        """
        获取最佳结果

        Args:
            results: 结果列表

        Returns:
            最佳结果
        """
        if not results:
            return None

        return results[0]

    def apply_best_parameters(self, strategy: CombinationStrategy,
                            result: OptimizationResult) -> CombinationStrategy:
        """
        应用最佳参数到策略

        Args:
            strategy: 策略对象
            result: 优化结果

        Returns:
            更新后的策略
        """
        temp_config = self._create_temp_config(strategy, result.parameters)

        updated_strategy = self.strategy_manager.update_strategy(
            strategy_id=strategy.strategy_id,
            config=temp_config
        )

        # 更新性能指标
        updated_strategy.performance = result.performance
        logger.debug(f"策略参数已更新: {strategy.strategy_id}")

        return updated_strategy

    def get_result_summary(self, results: List[OptimizationResult],
                         top_n: int = 5) -> List[Dict]:
        """
        获取结果摘要

        Args:
            results: 结果列表
            top_n: 显示前N个

        Returns:
            结果摘要列表
        """
        summary = []
        for i, result in enumerate(results[:top_n]):
            summary.append({
                "rank": i + 1,
                "parameters": result.parameters,
                "total_return": result.performance.total_return,
                "win_rate": result.performance.win_rate,
                "total_trades": result.performance.total_trades,
                "max_drawdown": result.performance.max_drawdown,
                "profit_factor": result.performance.profit_factor
            })
        return summary

    def compare_strategies(self, strategies: List[CombinationStrategy], df: pd.DataFrame,
                        initial_capital: float = 10000) -> List[Dict]:
        """
        比较多个策略

        Args:
            strategies: 策略列表
            df: 历史数据
            initial_capital: 初始资金

        Returns:
            比较结果
        """
        comparisons = []

        for strategy in strategies:
            performance = self.strategy_manager.backtest_strategy(
                strategy, df, initial_capital
            )

            comparisons.append({
                "strategy_id": strategy.strategy_id,
                "name": strategy.name,
                "total_return": performance.total_return,
                "win_rate": performance.win_rate,
                "total_trades": performance.total_trades,
                "max_drawdown": performance.max_drawdown,
                "profit_factor": performance.profit_factor,
                "sharpe_ratio": performance.sharpe_ratio
            })

        return comparisons

    def export_results(self, results: List[OptimizationResult], filepath: str):
        """
        导出优化结果到CSV文件

        Args:
            results: 结果列表
            filepath: 文件路径
        """
        data = []
        for result in results:
            row = {
                "rank": result.rank,
                "score": result.score,
                "total_trades": result.performance.total_trades,
                "win_rate": result.performance.win_rate,
                "total_return": result.performance.total_return,
                "avg_return": result.performance.avg_return,
                "max_drawdown": result.performance.max_drawdown,
                "profit_factor": result.performance.profit_factor,
                "sharpe_ratio": result.performance.sharpe_ratio,
                "sortino_ratio": result.performance.sortino_ratio,
                "win_loss_ratio": result.performance.win_loss_ratio
            }
            row.update({f"param_{k}": v for k, v in result.parameters.items()})
            data.append(row)

        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        logger.debug(f"优化结果已导出到: {filepath}")

    def validate_parameters(self, parameters: List[OptimizationParameter]) -> List[Dict]:
        """
        验证参数配置

        Args:
            parameters: 参数配置

        Returns:
            验证结果
        """
        errors = []

        for param in parameters:
            if not param.name:
                errors.append({"parameter": "unknown", "error": "参数名称不能为空"})
                continue

            if not param.values:
                errors.append({"parameter": param.name, "error": "参数值列表不能为空"})
                continue

            if param.min_value is not None and param.max_value is not None:
                if param.min_value > param.max_value:
                    errors.append({"parameter": param.name, "error": "最小值不能大于最大值"})

                invalid_values = [v for v in param.values if v < param.min_value or v > param.max_value]
                if invalid_values:
                    errors.append({
                        "parameter": param.name,
                        "error": f"参数值超出范围 [{param.min_value}, {param.max_value}]: {invalid_values}"
                    })

        return errors

    def get_optimal_strategy(self, strategy_type: StrategyType, df: pd.DataFrame,
                           parameters: List[OptimizationParameter],
                           config: OptimizationConfig) -> Optional[CombinationStrategy]:
        """
        获取最优策略

        Args:
            strategy_type: 策略类型
            df: 历史数据
            parameters: 优化参数
            config: 优化配置

        Returns:
            最优策略
        """
        temp_strategy = self.strategy_manager.create_strategy(
            strategy_type=strategy_type,
            strategy_id=f"temp_optimal_{strategy_type.value}"
        )

        try:
            results = self.optimize_strategy(
                temp_strategy, df, config, parameters
            )

            if results:
                best_result = self.get_best_result(results)
                optimal_strategy = self.apply_best_parameters(temp_strategy, best_result)
                return optimal_strategy

        except Exception as e:
            logger.error(f"获取最优策略失败: {e}")
            self.strategy_manager.remove_strategy(temp_strategy.strategy_id)

        return None

    def __str__(self):
        """字符串表示"""
        return f"StrategyOptimizer(results={len(self.results)})"

    def __repr__(self):
        """详细表示"""
        return self.__str__()
