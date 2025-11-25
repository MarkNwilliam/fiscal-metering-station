"""API MPMS Chapter 4 meter proving.

Meter proving establishes the *meter factor* (MF) that corrects a meter's
indicated volume to the true volume measured by a reference prover:

    MF_i = V_prover,c / V_meter,i          per run
    MF   = mean of valid runs

API MPMS Ch. 4 requires the proving runs to be repeatable -- classically the
spread (max - min)/mean of the meter factors must be <= the proving limit
(0.05 % for three-run proves). The run-to-run scatter also feeds the Type A
uncertainty term in the GUM budget (flowlib.uncertainty).
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Sequence

from .fluids import Real

DEFAULT_REPEATABILITY_LIMIT = 0.0005  # 0.05 %


@dataclass
class MeterProving:
    """A set of meter proving runs.

    Parameters
    ----------
    prover_volumes : sequence of reference (prover) volumes per run, m3,
        already corrected to operating conditions.
    indicated_volumes : sequence of meter-indicated volumes per run, m3.
    repeatability_limit : maximum allowed (max-min)/mean, default 0.05 %.
    """

    prover_volumes: Sequence[Real]
    indicated_volumes: Sequence[Real]
    repeatability_limit: float = DEFAULT_REPEATABILITY_LIMIT

    def __post_init__(self) -> None:
        if len(self.prover_volumes) != len(self.indicated_volumes):
            raise ValueError("prover and indicated volume lists must be the same length")
        if not self.prover_volumes:
            raise ValueError("at least one proving run is required")
        if any(v <= 0 for v in self.indicated_volumes):
            raise ValueError("indicated volumes must be positive")

    @property
    def meter_factors(self) -> list[float]:
        return [p / i for p, i in zip(self.prover_volumes, self.indicated_volumes)]

    @property
    def average_meter_factor(self) -> float:
        return mean(self.meter_factors)

    @property
    def repeatability(self) -> float:
        """(max - min) / mean of the meter factors."""
        mf = self.meter_factors
        return (max(mf) - min(mf)) / mean(mf)

    @property
    def is_repeatable(self) -> bool:
        return self.repeatability <= self.repeatability_limit

    @property
    def std_dev(self) -> float:
        return pstdev(self.meter_factors)

    def apply(self, indicated_volume: Real) -> float:
        """Correct an indicated volume by the average meter factor."""
        return indicated_volume * self.average_meter_factor


def correct_prover_volume(
    V_cal: Real,
    T_operating: Real,
    T_cal: Real,
    alpha_steel: Real = 1.2e-5,
) -> float:
    """Prover volume corrected from calibration to operating temperature.

    The prover shell expands with temperature (steel thermal expansion),
    so the reference volume changes: V = V_cal * (1 + alpha_steel*(T - T_cal)).
    """
    return V_cal * (1.0 + alpha_steel * (T_operating - T_cal))


def meter_factor(prover_volume: Real, indicated_volume: Real) -> float:
    """Single-run meter factor."""
    if indicated_volume <= 0:
        raise ValueError("indicated volume must be positive")
    return prover_volume / indicated_volume
