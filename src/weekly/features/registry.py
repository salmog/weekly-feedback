from __future__ import annotations

import pandas as pd

from weekly.features.base import FeatureCalculator


class FeatureRegistry:
    _instance: FeatureRegistry | None = None

    def __init__(self) -> None:
        self._features: dict[str, FeatureCalculator] = {}

    @classmethod
    def get_instance(cls) -> FeatureRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, calculator: FeatureCalculator) -> None:
        if calculator.name in self._features:
            raise ValueError(f"Feature '{calculator.name}' already registered")
        self._features[calculator.name] = calculator

    def get(self, name: str) -> FeatureCalculator:
        return self._features[name]

    def get_all(self) -> list[FeatureCalculator]:
        return list(self._features.values())

    def list_names(self) -> list[str]:
        return list(self._features.keys())

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all features and return EAV-format DataFrame with columns: date, feature_name, value."""
        records: list[pd.DataFrame] = []
        for calc in self._features.values():
            missing = [d for d in calc.dependencies if d not in df.columns]
            if missing:
                continue
            values = calc.compute(df)
            feat_df = pd.DataFrame(
                {"date": df["date"].values, "feature_name": calc.name, "value": values.values}
            )
            records.append(feat_df)
        if not records:
            return pd.DataFrame(columns=["date", "feature_name", "value"])
        return pd.concat(records, ignore_index=True)


def register_feature(cls: type[FeatureCalculator]) -> type[FeatureCalculator]:
    FeatureRegistry.get_instance().register(cls())
    return cls
