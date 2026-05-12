import pandas as pd

from weekly.features.base import FeatureCalculator
from weekly.features.registry import register_feature


@register_feature
class RelativeVolume20(FeatureCalculator):
    @property
    def name(self) -> str:
        return "relative_volume_20"

    @property
    def dependencies(self) -> list[str]:
        return ["volume"]

    @property
    def lookback_periods(self) -> int:
        return 20

    def compute(self, df: pd.DataFrame) -> pd.Series:
        avg_vol = df["volume"].rolling(20).mean()
        return df["volume"] / avg_vol


@register_feature
class RelativeVolume5(FeatureCalculator):
    @property
    def name(self) -> str:
        return "relative_volume_5"

    @property
    def dependencies(self) -> list[str]:
        return ["volume"]

    @property
    def lookback_periods(self) -> int:
        return 5

    def compute(self, df: pd.DataFrame) -> pd.Series:
        avg_vol = df["volume"].rolling(5).mean()
        return df["volume"] / avg_vol
