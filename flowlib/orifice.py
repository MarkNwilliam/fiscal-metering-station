"""Orifice-plate flow computation per ISO 5167:2003 / AGA-3.

Implements the Reader-Harris-Gallagher (RHG) discharge coefficient for
concentric square-edged orifice plates (corner, flange, and D-D/2 taps),
the ISO 5167-2 expansibility factor for compressible flow, and the iterative
mass-flow solution (C depends on the Reynolds number, which depends on flow).

Mass flow:
    qm = C / sqrt(1 - beta^4) * epsilon * (pi/4) d^2 * sqrt(2 dP rho)
"""
from __future__ import annotations

from math import pi, sqrt

from .fluids import LiquidFluid, Real

VALID_TAPS = ("corner", "flange", "D_D/2")


def tapping_geometry(D: Real, taps: str) -> tuple[float, float]:
    """Dimensionless upstream/downstream tap locations (L1, L2').

    D is the pipe internal diameter in millimetres.
    """
    D = float(D)
    if taps == "corner":
        return 0.0, 0.0
    if taps == "flange":
        l = 25.4 / D  # mm upstream and downstream of the faces
        return l, l
    if taps == "D_D/2":
        return 1.0, 0.5
    raise ValueError(f"taps must be one of {VALID_TAPS}, got {taps!r}")


def discharge_coefficient(
    beta: Real,
    Re_D: Real,
    D: Real,
    taps: str = "corner",
) -> float:
    """Reader-Harris-Gallagher discharge coefficient, ISO 5167:2003."""
    beta = float(beta)
    Re_D = float(Re_D)
    if not (0.1 <= beta <= 0.75):
        raise ValueError(f"beta must be in [0.10, 0.75], got {beta}")
    L1, L2p = tapping_geometry(D, taps)
    A = (19000.0 * beta / Re_D) ** 0.8
    M2p = 2.0 * L2p / (1.0 - beta)
    term1 = 0.5961 + 0.0261 * beta**2 - 0.216 * beta**8
    term2 = 0.000521 * (1.0e6 * beta / Re_D) ** 0.7
    term3 = (0.0188 + 0.0063 * A) * beta**3.5 * (1.0e6 / Re_D) ** 0.3
    term4 = (
        0.043
        + 0.080 * _exp(-10.0 * L1)
        - 0.123 * _exp(-7.0 * L1)
    ) * (1.0 - 0.11 * A) * (beta**4 / (1.0 - beta**4))
    term5 = 0.031 * (M2p - 0.8 * M2p**1.1) * beta**1.3
    return term1 + term2 + term3 + term4 - term5


def expansibility(
    beta: Real,
    P1: Real,
    P2: Real,
    kappa: Real,
) -> float:
    """ISO 5167-2 expansibility factor for compressible flow.

    Returns 1.0 for incompressible (liquid) service. Valid for P2/P1 >= 0.75.
    """
    beta = float(beta)
    r = P2 / P1
    if r >= 1.0:
        return 1.0
    if r < 0.75:
        raise ValueError("expansibility outside validity range (P2/P1 < 0.75)")
    return 1.0 - (0.351 + 0.256 * beta**4 + 0.93 * beta**8) * (1.0 - r ** (1.0 / kappa))


def reynolds_from_flow(qm: Real, D: Real, mu: Real) -> float:
    """Reynolds number from mass flow: Re_D = 4 qm / (pi D mu)."""
    return 4.0 * qm / (pi * D * mu)


def orifice_mass_flow(
    D: Real,
    d: Real,
    dP: Real,
    rho: Real,
    mu: Real,
    taps: str = "corner",
    P1: Real | None = None,
    P2: Real | None = None,
    kappa: Real = 1.3,
    epsilon: Real | None = None,
    max_iter: int = 200,
    tol: float = 1e-9,
) -> float:
    """Mass flow through a square-edged orifice plate, kg/s.

    Parameters
    ----------
    D, d : pipe and orifice bore diameters, m.
    dP : differential pressure across the plate, Pa.
    rho : fluid density at upstream conditions, kg/m3.
    mu : dynamic viscosity, Pa.s.
    taps : tapping type, one of 'corner' | 'flange' | 'D_D/2'.
    P1, P2 : absolute upstream/downstream pressures, Pa (only needed for
        compressible flow when epsilon is not given directly).
    kappa : isentropic exponent for compressible flow.
    epsilon : optionally override the expansibility factor.
    """
    D = float(D)
    d = float(d)
    if D <= 0 or d <= 0 or d >= D:
        raise ValueError("require 0 < d < D")
    beta = d / D
    if epsilon is not None:
        eps = float(epsilon)
    else:
        if P1 is None or P2 is None:
            eps = 1.0
        else:
            eps = expansibility(beta, P1, P2, kappa)

    # Iterate: C(Re_D) -> qm -> Re_D(qm)
    qm = 0.0
    Re_D = 1.0e5
    area = (pi / 4.0) * d * d
    K0 = sqrt(2.0 * dP * rho)
    for _ in range(max_iter):
        C = discharge_coefficient(beta, Re_D, D * 1000.0, taps)
        qm_new = (C / sqrt(1.0 - beta**4)) * eps * area * K0
        Re_new = reynolds_from_flow(qm_new, D, mu)
        if abs(Re_new - Re_D) <= tol * max(1.0, abs(Re_D)):
            return qm_new
        Re_D = Re_new
    return qm_new  # type: ignore[possibly-undefined]


def _exp(x: Real) -> float:
    from math import exp

    return exp(x)
