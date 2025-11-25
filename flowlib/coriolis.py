"""Coriolis flowmeter modelling.

A Coriolis meter measures *mass* flow directly from the phase shift between
two points on a vibrating tube (proportional to mass flow), and derives fluid
density from the tube's natural frequency:

    rho = A / f^2 + B          (density from frequency)
    qm  = directly measured    (mass flow)
    qv  = qm / rho             (volume flow at flowing conditions)

Volume flow must then be compensated to base conditions for custody transfer
(see flowlib.compensation). This module mirrors how a flow computer turns raw
meter signals into the flows that go on a custody ticket.
"""
from __future__ import annotations

from dataclasses import dataclass

from .fluids import Real


@dataclass(frozen=True)
class CoriolisMeter:
    """Simple Coriolis meter model.

    Parameters
    ----------
    K : float
        Mass-flow sensitivity, kg/s per unit phase shift (calibration factor).
    A, B : float
        Density-from-frequency coefficients: rho = A / f^2 + B, kg/m3.
    """

    K: float
    A: float = 0.0
    B: float = 1000.0

    def mass_flow(self, phase: Real) -> float:
        """Mass flow from raw phase-shift signal, kg/s."""
        return self.K * phase

    def density(self, frequency: Real) -> float:
        """Fluid density from tube natural frequency, kg/m3."""
        return self.A / (frequency**2) + self.B

    def volume_flow(self, phase: Real, frequency: Real) -> float:
        """Volume flow at flowing conditions, m3/s."""
        qm = self.mass_flow(phase)
        rho = self.density(frequency)
        if rho <= 0:
            raise ValueError("invalid density from frequency signal")
        return qm / rho
