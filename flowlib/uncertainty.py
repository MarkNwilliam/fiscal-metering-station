"""GUM (Guide to the Expression of Uncertainty in Measurement) budget.

A fiscal meter's flow result carries an *expanded uncertainty* (typically
k = 2, ~95 % confidence) that must be declared on the custody ticket. This
module combines:

    Type A  - repeatability of the meter proving runs (statistical);
    Type B  - systematic effects from instrument accuracy, discharge
              coefficient, geometry and fluid properties.

Standard uncertainty for each source:
    normal      : u = nominal / 2        (nominal given at 95 %)
    rectangular : u = nominal / sqrt(3)

Combined:    u_c = sqrt( sum_i (c_i * u_i)^2 )        (RSS)
Expanded:    U   = k * u_c                             (default k = 2)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Sequence

DISTRIBUTION_K = {"normal": 0.5, "rectangular": 1.0 / sqrt(3.0)}


@dataclass(frozen=True)
class UncertaintySource:
    """One Type B uncertainty source.

    Parameters
    ----------
    name : str
    nominal : float
        Relative accuracy in % of reading.
    distribution : 'normal' | 'rectangular'
    sensitivity : float
        Sensitivity coefficient: % change in result per % change in source.
    """

    name: str
    nominal: float
    distribution: str = "rectangular"
    sensitivity: float = 1.0

    def __post_init__(self) -> None:
        if self.distribution not in DISTRIBUTION_K:
            raise ValueError(f"distribution must be one of {tuple(DISTRIBUTION_K)}")
        if self.nominal < 0:
            raise ValueError("nominal accuracy must be non-negative")

    @property
    def standard_uncertainty(self) -> float:
        """Standard uncertainty in % of reading."""
        return self.nominal * DISTRIBUTION_K[self.distribution] * self.sensitivity


@dataclass
class UncertaintyBudget:
    """GUM budget: Type A (proving) + Type B (systematic) sources."""

    sources: Sequence[UncertaintySource] = field(default_factory=list)
    type_a_std_uncertainty: float = 0.0
    coverage_factor: float = 2.0

    def add(
        self,
        name: str,
        nominal: float,
        distribution: str = "rectangular",
        sensitivity: float = 1.0,
    ) -> None:
        self.sources.append(
            UncertaintySource(name, nominal, distribution, sensitivity)
        )

    @property
    def combined_standard_uncertainty(self) -> float:
        rss = self.type_a_std_uncertainty**2 + sum(
            s.standard_uncertainty**2 for s in self.sources
        )
        return sqrt(rss)

    @property
    def expanded_uncertainty(self) -> float:
        return self.coverage_factor * self.combined_standard_uncertainty

    @property
    def dominant_source(self) -> UncertaintySource | None:
        if not self.sources:
            return None
        return max(self.sources, key=lambda s: s.standard_uncertainty)

    def table(self) -> list[dict]:
        """Uncertainty budget rows for reporting."""
        rows = [
            {
                "source": "Meter proving repeatability (Type A)",
                "type": "A",
                "u (%)": round(self.type_a_std_uncertainty, 4),
            }
        ]
        rows.extend(
            {
                "source": s.name,
                "type": "B",
                "u (%)": round(s.standard_uncertainty, 4),
            }
            for s in self.sources
        )
        rows.append(
            {
                "source": f"Combined (u_c) -- U = k={self.coverage_factor:.0f}",
                "type": "C",
                "u (%)": round(self.combined_standard_uncertainty, 4),
            }
        )
        rows.append(
            {
                "source": f"Expanded uncertainty U ({self.coverage_factor:.0f})",
                "type": "E",
                "u (%)": round(self.expanded_uncertainty, 4),
            }
        )
        return rows
