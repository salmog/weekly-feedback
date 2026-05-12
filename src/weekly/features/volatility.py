import pandas as pd

from weekly.features.base import FeatureCalculator
from weekly.features.registry import register_feature


@register_feature
class ATR14(FeatureCalculator):
    @property
    def name(self) -> str:
        return "atr_14"

    @property
    def dependencies(self) -> list[str]:
        return ["high", "low", "close"]

    @property
    def lookback_periods(self) -> int:
        return 15

    def compute(self, df: pd.DataFrame) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=14).mean()


@register_feature
class ATRPercent(FeatureCalculator):
    @property
    def name(self) -> str:
        return "atr_percent"

    @property
    def dependencies(self) -> list[str]:
        return ["high", "low", "close"]

    @property
    def lookback_periods(self) -> int:
        return 15

    def compute(self, df: pd.DataFrame) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean()
        return atr / df["close"]


@register_feature
class BollingerBandWidth(FeatureCalculator):
    @property
    def name(self) -> str:
        return "bb_width_20"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 20

    def compute(self, df: pd.DataFrame) -> pd.Series:
        sma = df["close"].rolling(20).mean()
        std = df["close"].rolling(20).std()
        return (4 * std) / sma


@register_feature
class BollingerBandPosition(FeatureCalculator):
    """Where price sits within the Bollinger Bands (0 = lower band, 1 = upper band)."""

    @property
    def name(self) -> str:
        return "bb_position_20"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 20

    def compute(self, df: pd.DataFrame) -> pd.Series:
        sma = df["close"].rolling(20).mean()
        std = df["close"].rolling(20).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        return (df["close"] - lower) / (upper - lower)


@register_feature
class RollingHigh52(FeatureCalculator):
    @property
    def name(self) -> str:
        return "rolling_high_52"

    @property
    def dependencies(self) -> list[str]:
        return ["high"]

    @property
    def lookback_periods(self) -> int:
        return 252

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["high"].rolling(window=252).max()


@register_feature
class RollingLow52(FeatureCalculator):
    @property
    def name(self) -> str:
        return "rolling_low_52"

    @property
    def dependencies(self) -> list[str]:
        return ["low"]

    @property
    def lookback_periods(self) -> int:
        return 252

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["low"].rolling(window=252).min()


@register_feature
class DistFromHigh52(FeatureCalculator):
    @property
    def name(self) -> str:
        return "dist_from_high_52"

    @property
    def dependencies(self) -> list[str]:
        return ["high", "close"]

    @property
    def lookback_periods(self) -> int:
        return 252

    def compute(self, df: pd.DataFrame) -> pd.Series:
        high_52 = df["high"].rolling(window=252).max()
        return (df["close"] - high_52) / high_52


@register_feature
class VolatilityRegime(FeatureCalculator):
    """Ratio of short-term to long-term ATR — >1 means expanding volatility."""

    @property
    def name(self) -> str:
        return "volatility_regime"

    @property
    def dependencies(self) -> list[str]:
        return ["high", "low", "close"]

    @property
    def lookback_periods(self) -> int:
        return 50

    def compute(self, df: pd.DataFrame) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_short = tr.rolling(window=5).mean()
        atr_long = tr.rolling(window=50).mean()
        return atr_short / atr_long
