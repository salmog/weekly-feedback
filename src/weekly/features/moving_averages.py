import pandas as pd

from weekly.features.base import FeatureCalculator
from weekly.features.registry import register_feature


@register_feature
class SMA20(FeatureCalculator):
    @property
    def name(self) -> str:
        return "sma_20"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 20

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(window=20).mean()


@register_feature
class SMA50(FeatureCalculator):
    @property
    def name(self) -> str:
        return "sma_50"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 50

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(window=50).mean()


@register_feature
class SMA200(FeatureCalculator):
    @property
    def name(self) -> str:
        return "sma_200"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 200

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(window=200).mean()


@register_feature
class EMA12(FeatureCalculator):
    @property
    def name(self) -> str:
        return "ema_12"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 12

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].ewm(span=12, adjust=False).mean()


@register_feature
class EMA20(FeatureCalculator):
    @property
    def name(self) -> str:
        return "ema_20"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 20

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].ewm(span=20, adjust=False).mean()


@register_feature
class EMA26(FeatureCalculator):
    @property
    def name(self) -> str:
        return "ema_26"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 26

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].ewm(span=26, adjust=False).mean()


@register_feature
class DistFromSMA20(FeatureCalculator):
    @property
    def name(self) -> str:
        return "dist_from_sma_20"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 20

    def compute(self, df: pd.DataFrame) -> pd.Series:
        sma = df["close"].rolling(window=20).mean()
        return (df["close"] - sma) / sma


@register_feature
class DistFromSMA50(FeatureCalculator):
    @property
    def name(self) -> str:
        return "dist_from_sma_50"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 50

    def compute(self, df: pd.DataFrame) -> pd.Series:
        sma = df["close"].rolling(window=50).mean()
        return (df["close"] - sma) / sma


@register_feature
class DistFromSMA200(FeatureCalculator):
    @property
    def name(self) -> str:
        return "dist_from_sma_200"

    @property
    def dependencies(self) -> list[str]:
        return ["close"]

    @property
    def lookback_periods(self) -> int:
        return 200

    def compute(self, df: pd.DataFrame) -> pd.Series:
        sma = df["close"].rolling(window=200).mean()
        return (df["close"] - sma) / sma
