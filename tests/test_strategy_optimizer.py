"""
策略优化器测试模块
测试 StrategyOptimizer 的各项功能
"""

import pytest
import pandas as pd
from pathlib import Path
from tempfile import gettempdir
from stocktradebot.strategy_optimizer import (
    OptimizationObjective,
    OptimizationMethod,
    OptimizationParameter,
    OptimizationConfig,
    OptimizationResult,
    StrategyOptimizer
)
from stocktradebot.combination_strategies import (
    CombinationStrategies,
    StrategyType,
    StrategyParameter,
    StrategyConfig
)
from stocktradebot.multi_timeframe import TimeframeType
from stocktradebot.signal_aggregator import AggregationStrategy


class TestStrategyOptimizer:
    """测试策略优化器"""

    def setup_method(self):
        """测试设置"""
        self.strategy_manager = CombinationStrategies()
        self.optimizer = StrategyOptimizer(self.strategy_manager)

    def test_initialization(self):
        """测试初始化"""
        assert isinstance(self.optimizer, StrategyOptimizer)
        assert self.optimizer.strategy_manager is self.strategy_manager
        assert len(self.optimizer.results) == 0
        assert self.optimizer.progress is not None

    def test_optimizer_without_manager(self):
        """测试不带策略管理器的初始化"""
        optimizer = StrategyOptimizer()
        assert optimizer.strategy_manager is not None
        assert isinstance(optimizer.strategy_manager, CombinationStrategies)

    def test_optimization_parameter_creation(self):
        """测试优化参数创建"""
        param1 = OptimizationParameter(
            name="window",
            values=[2, 3, 5],
            min_value=2,
            max_value=5,
            step=1
        )

        param2 = OptimizationParameter(
            name="lookback",
            values=[60, 90, 120],
            min_value=30,
            max_value=120,
            step=30
        )

        assert param1.name == "window"
        assert len(param1.values) == 3
        assert param1.min_value == 2
        assert param1.max_value == 5
        assert param1.step == 1

        assert param2.name == "lookback"
        assert len(param2.values) == 3
        assert param2.min_value == 30
        assert param2.max_value == 120
        assert param2.step == 30

    def test_optimization_configuration(self):
        """测试优化配置"""
        config = OptimizationConfig(
            objective=OptimizationObjective.WIN_RATE,
            method=OptimizationMethod.GRID_SEARCH,
            max_workers=2,
            max_trials=50,
            timeout=1800,
            early_stop=True,
            early_stop_rounds=10
        )

        assert config.objective == OptimizationObjective.WIN_RATE
        assert config.method == OptimizationMethod.GRID_SEARCH
        assert config.max_workers == 2
        assert config.max_trials == 50
        assert config.timeout == 1800
        assert config.early_stop is True
        assert config.early_stop_rounds == 10

    def test_create_optimization_parameters(self):
        """测试创建优化参数"""
        params = [
            OptimizationParameter(name="window", values=[2, 3], min_value=1, max_value=5),
            OptimizationParameter(name="lookback", values=[60, 90], min_value=30, max_value=120),
            OptimizationParameter(name="strength_threshold", values=[70, 80])
        ]

        assert len(params) == 3
        assert all(isinstance(p, OptimizationParameter) for p in params)
        assert all(p.name in ["window", "lookback", "strength_threshold"] for p in params)

    def test_parameter_validation(self):
        """测试参数验证"""
        valid_params = [
            OptimizationParameter(name="window", values=[2, 3], min_value=1, max_value=5),
            OptimizationParameter(name="lookback", values=[60, 90], min_value=30, max_value=120)
        ]

        errors = self.optimizer.validate_parameters(valid_params)
        assert len(errors) == 0

        invalid_params = [
            OptimizationParameter(name="", values=[2, 3]),  # 空名称
            OptimizationParameter(name="invalid", values=[]),  # 空值列表
            OptimizationParameter(name="range", values=[1, 6], min_value=2, max_value=5)  # 值超出范围
        ]

        errors = self.optimizer.validate_parameters(invalid_params)
        assert len(errors) > 0
        assert any("参数名称不能为空" in err['error'] for err in errors)
        assert any("参数值列表不能为空" in err['error'] for err in errors)
        assert any("参数值超出范围" in err['error'] for err in errors)

    def test_generate_parameter_grid(self):
        """测试参数网格生成"""
        params = [
            OptimizationParameter(name="window", values=[2, 3]),
            OptimizationParameter(name="lookback", values=[60, 90])
        ]

        grid = self.optimizer._generate_grid(params)
        assert len(grid) == 4
        assert all(isinstance(p, dict) for p in grid)

        expected_params = [
            {"window": 2, "lookback": 60},
            {"window": 2, "lookback": 90},
            {"window": 3, "lookback": 60},
            {"window": 3, "lookback": 90}
        ]

        for expected in expected_params:
            assert any(all(p[k] == v for k, v in expected.items()) for p in grid)

    def test_run_simple_optimization(self):
        """测试简单优化"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="simple_optimization_test"
        )

        df = self._create_test_data()

        optimization_params = [
            OptimizationParameter(name="window", values=[2, 3], min_value=2, max_value=3),
            OptimizationParameter(name="lookback", values=[60, 90], min_value=60, max_value=90)
        ]

        config = OptimizationConfig(
            objective=OptimizationObjective.TOTAL_RETURN,
            method=OptimizationMethod.GRID_SEARCH,
            max_workers=1
        )

        results = self.optimizer.optimize_strategy(strategy, df, config, optimization_params)

        assert len(results) > 0
        assert all(isinstance(r, OptimizationResult) for r in results)

        best_result = results[0]
        assert best_result.score > 0
        assert len(best_result.parameters) == 2
        assert "window" in best_result.parameters
        assert "lookback" in best_result.parameters

    def test_optimization_with_different_objectives(self):
        """测试不同优化目标"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="objective_test"
        )

        df = self._create_test_data()

        optimization_params = [
            OptimizationParameter(name="window", values=[2, 3], min_value=2, max_value=3),
            OptimizationParameter(name="lookback", values=[60], min_value=60, max_value=60)
        ]

        # 测试不同目标的优化
        objectives = [
            OptimizationObjective.TOTAL_RETURN,
            OptimizationObjective.WIN_RATE,
            OptimizationObjective.PROFIT_FACTOR,
            OptimizationObjective.WIN_LOSS_RATIO
        ]

        for objective in objectives:
            config = OptimizationConfig(
                objective=objective,
                method=OptimizationMethod.GRID_SEARCH,
                max_workers=1
            )

            results = self.optimizer.optimize_strategy(strategy, df, config, optimization_params)
            assert len(results) > 0
            assert all(r.score >= 0 for r in results)

    def test_get_best_result(self):
        """测试获取最佳结果"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="best_result_test"
        )

        df = self._create_test_data()

        optimization_params = [
            OptimizationParameter(name="window", values=[2, 3], min_value=2, max_value=3),
            OptimizationParameter(name="lookback", values=[60, 90], min_value=60, max_value=90)
        ]

        config = OptimizationConfig(
            objective=OptimizationObjective.TOTAL_RETURN,
            method=OptimizationMethod.GRID_SEARCH,
            max_workers=1
        )

        results = self.optimizer.optimize_strategy(strategy, df, config, optimization_params)
        best_result = self.optimizer.get_best_result(results)

        assert best_result is not None
        assert best_result == results[0]
        assert all(r.score <= best_result.score for r in results)

    def test_apply_best_parameters(self):
        """测试应用最佳参数"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="apply_params_test"
        )

        df = self._create_test_data()

        optimization_params = [
            OptimizationParameter(name="window", values=[2, 3], min_value=2, max_value=3),
            OptimizationParameter(name="lookback", values=[60], min_value=60, max_value=60)
        ]

        config = OptimizationConfig(
            objective=OptimizationObjective.TOTAL_RETURN,
            method=OptimizationMethod.GRID_SEARCH,
            max_workers=1
        )

        results = self.optimizer.optimize_strategy(strategy, df, config, optimization_params)
        best_result = self.optimizer.get_best_result(results)

        original_params = {p.name: p.value for p in strategy.config.parameters}

        updated_strategy = self.optimizer.apply_best_parameters(strategy, best_result)

        assert updated_strategy is strategy

        updated_params = {p.name: p.value for p in updated_strategy.config.parameters}
        assert updated_params != original_params

        for name, value in best_result.parameters.items():
            assert any(p.name == name and p.value == value for p in updated_strategy.config.parameters)

    def test_result_summary(self):
        """测试结果摘要"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="summary_test"
        )

        df = self._create_test_data()

        optimization_params = [
            OptimizationParameter(name="window", values=[2, 3], min_value=2, max_value=3),
            OptimizationParameter(name="lookback", values=[60, 90], min_value=60, max_value=90)
        ]

        config = OptimizationConfig(
            objective=OptimizationObjective.TOTAL_RETURN,
            method=OptimizationMethod.GRID_SEARCH,
            max_workers=1
        )

        results = self.optimizer.optimize_strategy(strategy, df, config, optimization_params)

        summary = self.optimizer.get_result_summary(results, top_n=2)
        assert len(summary) <= 2
        assert all('rank' in s for s in summary)
        assert all('parameters' in s for s in summary)
        assert all('total_return' in s for s in summary)
        assert all('win_rate' in s for s in summary)

    def test_export_results(self):
        """测试导出结果"""
        strategy = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="export_test"
        )

        df = self._create_test_data()

        optimization_params = [
            OptimizationParameter(name="window", values=[2, 3], min_value=2, max_value=3),
            OptimizationParameter(name="lookback", values=[60], min_value=60, max_value=60)
        ]

        config = OptimizationConfig(
            objective=OptimizationObjective.TOTAL_RETURN,
            method=OptimizationMethod.GRID_SEARCH,
            max_workers=1
        )

        results = self.optimizer.optimize_strategy(strategy, df, config, optimization_params)

        temp_file = Path(gettempdir()) / "optimization_results.csv"
        self.optimizer.export_results(results, str(temp_file))

        assert temp_file.exists()

        imported_df = pd.read_csv(temp_file)
        assert len(imported_df) == len(results)
        assert 'rank' in imported_df.columns
        assert 'score' in imported_df.columns
        assert 'total_trades' in imported_df.columns
        assert 'win_rate' in imported_df.columns
        assert 'total_return' in imported_df.columns

        temp_file.unlink()

    def test_optimal_strategy_creation(self):
        """测试最优策略创建"""
        df = self._create_test_data()

        optimization_params = [
            OptimizationParameter(name="window", values=[2, 3], min_value=2, max_value=3),
            OptimizationParameter(name="lookback", values=[60], min_value=60, max_value=60)
        ]

        config = OptimizationConfig(
            objective=OptimizationObjective.TOTAL_RETURN,
            method=OptimizationMethod.GRID_SEARCH,
            max_workers=1
        )

        optimal_strategy = self.optimizer.get_optimal_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            df=df,
            parameters=optimization_params,
            config=config
        )

        assert optimal_strategy is not None
        assert optimal_strategy.strategy_type == StrategyType.MACD_KDJ
        assert optimal_strategy.strategy_id.startswith("temp_optimal_")

    def test_compare_strategies(self):
        """测试策略比较"""
        strategy1 = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_KDJ,
            strategy_id="compare_test1"
        )

        strategy2 = self.strategy_manager.create_strategy(
            strategy_type=StrategyType.MACD_RSI,
            strategy_id="compare_test2"
        )

        df = self._create_test_data()

        comparisons = self.optimizer.compare_strategies([strategy1, strategy2], df)

        assert len(comparisons) == 2
        assert all(isinstance(c, dict) for c in comparisons)
        assert all(c['strategy_id'] in ["compare_test1", "compare_test2"] for c in comparisons)

        for comparison in comparisons:
            assert 'name' in comparison
            assert 'total_return' in comparison
            assert 'win_rate' in comparison
            assert 'total_trades' in comparison

    def _create_test_data(self) -> pd.DataFrame:
        """创建测试数据"""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        close = []
        current_price = 100.0
        for i in range(200):
            trend = i % 50
            current_price += (trend - 25) / 20
            close.append(current_price)

        high = [p * 1.02 for p in close]
        low = [p * 0.98 for p in close]
        open_ = [p * 0.99 for p in close]
        volume = [10000 + i * 100 for i in range(200)]

        return pd.DataFrame({
            'date': dates,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }).set_index('date')
