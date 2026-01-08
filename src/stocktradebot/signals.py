"""
信号检测模块
检测金叉/死叉、涨跌幅、成交量异常等信号
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from .indicators import MAData, MACDData, KDJData


class SignalType(Enum):
    """信号类型"""
    MA_GOLDEN_CROSS = "均线金叉"
    MA_DEATH_CROSS = "均线死叉"
    MACD_GOLDEN_CROSS = "MACD金叉"
    MACD_DEATH_CROSS = "MACD死叉"
    KDJ_GOLDEN_CROSS = "KDJ金叉"
    KDJ_DEATH_CROSS = "KDJ死叉"
    PRICE_UP = "价格上涨"
    PRICE_DOWN = "价格下跌"
    VOLUME_SURGE = "成交量放大"


@dataclass
class Signal:
    """信号"""
    signal_type: SignalType
    symbol: str
    name: str
    message: str
    value: float = 0  # 相关数值


class SignalDetector:
    """信号检测器"""
    
    def __init__(self, price_threshold: float = 3.0, volume_threshold: float = 2.0):
        """
        Args:
            price_threshold: 涨跌幅阈值（%）
            volume_threshold: 成交量放大阈值（倍）
        """
        self.price_threshold = price_threshold
        self.volume_threshold = volume_threshold
    
    def detect_ma_cross(self, ma: MAData, prev_ma5: float, prev_ma10: float) -> Optional[Signal]:
        """检测均线金叉/死叉（MA5和MA10）"""
        # 金叉：MA5从下往上穿过MA10
        if prev_ma5 <= prev_ma10 and ma.ma5 > ma.ma10:
            return Signal(
                signal_type=SignalType.MA_GOLDEN_CROSS,
                symbol="",
                name="",
                message=f"📈 MA5上穿MA10，形成金叉\nMA5: {ma.ma5:.2f} > MA10: {ma.ma10:.2f}",
                value=ma.ma5 - ma.ma10
            )
        # 死叉：MA5从上往下穿过MA10
        if prev_ma5 >= prev_ma10 and ma.ma5 < ma.ma10:
            return Signal(
                signal_type=SignalType.MA_DEATH_CROSS,
                symbol="",
                name="",
                message=f"📉 MA5下穿MA10，形成死叉\nMA5: {ma.ma5:.2f} < MA10: {ma.ma10:.2f}",
                value=ma.ma5 - ma.ma10
            )
        return None
    
    def detect_macd_cross(self, macd: MACDData) -> Optional[Signal]:
        """检测MACD金叉/死叉"""
        # 金叉：DIF从下往上穿过DEA
        if macd.prev_dif <= macd.prev_dea and macd.dif > macd.dea:
            return Signal(
                signal_type=SignalType.MACD_GOLDEN_CROSS,
                symbol="",
                name="",
                message=f"📈 MACD金叉\nDIF: {macd.dif:.4f}\nDEA: {macd.dea:.4f}\nMACD: {macd.macd:.4f}",
                value=macd.macd
            )
        # 死叉：DIF从上往下穿过DEA
        if macd.prev_dif >= macd.prev_dea and macd.dif < macd.dea:
            return Signal(
                signal_type=SignalType.MACD_DEATH_CROSS,
                symbol="",
                name="",
                message=f"📉 MACD死叉\nDIF: {macd.dif:.4f}\nDEA: {macd.dea:.4f}\nMACD: {macd.macd:.4f}",
                value=macd.macd
            )
        return None
    
    def detect_kdj_cross(self, kdj: KDJData) -> Optional[Signal]:
        """检测KDJ金叉/死叉"""
        # 金叉：K从下往上穿过D
        if kdj.prev_k <= kdj.prev_d and kdj.k > kdj.d:
            return Signal(
                signal_type=SignalType.KDJ_GOLDEN_CROSS,
                symbol="",
                name="",
                message=f"📈 KDJ金叉\nK: {kdj.k:.2f}\nD: {kdj.d:.2f}\nJ: {kdj.j:.2f}",
                value=kdj.j
            )
        # 死叉：K从上往下穿过D
        if kdj.prev_k >= kdj.prev_d and kdj.k < kdj.d:
            return Signal(
                signal_type=SignalType.KDJ_DEATH_CROSS,
                symbol="",
                name="",
                message=f"📉 KDJ死叉\nK: {kdj.k:.2f}\nD: {kdj.d:.2f}\nJ: {kdj.j:.2f}",
                value=kdj.j
            )
        return None
    
    def detect_price_change(self, current: float, prev_close: float) -> Optional[Signal]:
        """检测价格涨跌幅"""
        if prev_close == 0:
            return None
        change_pct = (current - prev_close) / prev_close * 100
        if change_pct >= self.price_threshold:
            return Signal(
                signal_type=SignalType.PRICE_UP,
                symbol="",
                name="",
                message=f"🚀 价格上涨 {change_pct:.2f}%\n当前价格: {current:.2f}",
                value=change_pct
            )
        if change_pct <= -self.price_threshold:
            return Signal(
                signal_type=SignalType.PRICE_DOWN,
                symbol="",
                name="",
                message=f"💥 价格下跌 {change_pct:.2f}%\n当前价格: {current:.2f}",
                value=change_pct
            )
        return None
    
    def detect_volume_surge(self, volume_ratio: float) -> Optional[Signal]:
        """检测成交量异常放大"""
        if volume_ratio >= self.volume_threshold:
            return Signal(
                signal_type=SignalType.VOLUME_SURGE,
                symbol="",
                name="",
                message=f"📊 成交量放大 {volume_ratio:.2f}倍",
                value=volume_ratio
            )
        return None
    
    def detect_all(self, indicators: dict, symbol: str, name: str, 
                   prev_ma5: float = None, prev_ma10: float = None,
                   enable_ma: bool = True, enable_macd: bool = True,
                   enable_kdj: bool = True, enable_price: bool = True,
                   enable_volume: bool = True) -> list[Signal]:
        """
        检测所有信号
        
        Args:
            indicators: 技术指标数据字典
            symbol: 股票/期货代码
            name: 名称
            prev_ma5, prev_ma10: 前一日均线值（用于检测金叉死叉）
            enable_*: 各类信号的开关
        
        Returns:
            检测到的信号列表
        """
        signals = []
        
        # 均线金叉/死叉
        if enable_ma and prev_ma5 is not None and prev_ma10 is not None:
            signal = self.detect_ma_cross(indicators["ma"], prev_ma5, prev_ma10)
            if signal:
                signal.symbol = symbol
                signal.name = name
                signals.append(signal)
        
        # MACD金叉/死叉
        if enable_macd:
            signal = self.detect_macd_cross(indicators["macd"])
            if signal:
                signal.symbol = symbol
                signal.name = name
                signals.append(signal)
        
        # KDJ金叉/死叉
        if enable_kdj:
            signal = self.detect_kdj_cross(indicators["kdj"])
            if signal:
                signal.symbol = symbol
                signal.name = name
                signals.append(signal)
        
        # 价格涨跌幅
        if enable_price:
            signal = self.detect_price_change(indicators["close"], indicators["prev_close"])
            if signal:
                signal.symbol = symbol
                signal.name = name
                signals.append(signal)
        
        # 成交量异常
        if enable_volume:
            signal = self.detect_volume_surge(indicators["volume_ratio"])
            if signal:
                signal.symbol = symbol
                signal.name = name
                signals.append(signal)
        
        return signals
    
    @staticmethod
    def format_signals(signals: list[Signal]) -> str:
        """格式化信号列表为消息"""
        if not signals:
            return ""
        
        messages = []
        for signal in signals:
            header = f"🔔 【{signal.name}】({signal.symbol})"
            messages.append(f"{header}\n{signal.message}")
        
        return "\n\n".join(messages)
