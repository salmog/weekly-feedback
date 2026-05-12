import numpy as np
import pandas as pd

from weekly.features.base import FeatureCalculator
from weekly.features.registry import register_feature


@register_feature
class BodyRatio(FeatureCalculator):
    @property
    def name(self) -> str:
        return "body_ratio"

    @property
    def dependencies(self) -> list[str]:
        return ["open", "high", "low", "close"]

    def compute(self, df: pd.DataFrame) -> pd.Series:
        body = (df["close"] - df["open"]).abs()
        candle_range = df["high"] - df["low"]
        return (body / candle_range).replace([np.inf, -np.inf], 0.0)


@register_feature
class UpperWickRatio(FeatureCalculator):
    @property
    def name(self) -> str:
        return "upper_wick_ratio"

    @property
    def dependencies(self) -> list[str]:
        return ["open", "high", "low", "close"]

    def compute(self, df: pd.DataFrame) -> pd.Series:
        upper_body = pd.concat([df["open"], df["close"]], axis=1).max(axis=1)
        upper_wick = df["high"] - upper_body
        candle_range = df["high"] - df["low"]
        return (upper_wick / candle_range).replace([np.inf, -np.inf], 0.0)


@register_feature
class LowerWickRatio(FeatureCalculator):
    @property
    def name(self) -> str:
        return "lower_wick_ratio"

    @property
    def dependencies(self) -> list[str]:
        return ["open", "high", "low", "close"]

    def compute(self, df: pd.DataFrame) -> pd.Series:
        lower_body = pd.concat([df["open"], df["close"]], axis=1).min(axis=1)
        lower_wick = lower_body - df["low"]
        candle_range = df["high"] - df["low"]
        return (lower_wick / candle_range).replace([np.inf, -np.inf], 0.0)


@register_feature
class CandleDirection(FeatureCalculator):
    @property
    def name(self) -> str:
        return "candle_direction"

    @property
    def dependencies(self) -> list[str]:
        return ["open", "close"]

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return np.sign(df["close"] - df["open"]).astype(float)


@register_feature
class GapPercent(FeatureCalculator):
    @property
    def name(self) -> str:
        return "gap_percent"

    @property
    def dependencies(self) -> list[str]:
        return ["open", "close"]

    @property
    def lookback_periods(self) -> int:
        return 1

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return (df["open"] - df["close"].shift(1)) / df["close"].shift(1)


@register_feature
class ClosePositionInRange(FeatureCalculator):
    """Where close sits within the day's range (0=low, 1=high)."""

    @property
    def name(self) -> str:
        return "close_position"

    @property
    def dependencies(self) -> list[str]:
        return ["high", "low", "close"]

    def compute(self, df: pd.DataFrame) -> pd.Series:
        candle_range = df["high"] - df["low"]
        return ((df["close"] - df["low"]) / candle_range).replace([np.inf, -np.inf], 0.5)


@register_feature
class TrendClassification(FeatureCalculator):
    """Simple trend: +1 if close > SMA50, -1 if close < SMA50, 0 otherwise."""

    @property
    def name(self) -> str:
        return "trend_sma50"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 50

    def compute(self, df: pd.DataFrame) -> pd.Series:
        sma = df["close"].rolling(window=50).mean()
        return np.sign(df["close"] - sma).astype(float)
