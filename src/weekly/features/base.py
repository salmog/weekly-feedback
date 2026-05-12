from abc import ABC, abstractmethod

import pandas as pd


class FeatureCalculator(ABC):

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def dependencies(self) -> list[str]: ...

    @property
    def lookback_periods(self) -> int:
        return 0

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series: ...
