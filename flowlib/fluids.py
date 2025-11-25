"""Fluid density models used for flow computation and compensation.

Liquids use a linearised density model (simplified API MPMS Ch. 11.1 form):
volume expands with temperature and compresses with pressure.

    rho(T, P) = rho0 * (1 - alpha*(T - T0) + kappa*(P - P0))

Gases use the Redlich-Kwong (1949) equation of state (documented stand-in
for the full AGA-8 / API MPMS Ch. 14.2 detail, which real fiscal gas
meters run on). Density follows the real-gas law rho = p*M/(Z*R*T) with
Z taken as the largest real root of the RK cubic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

R_GAS = 8.314462618  # J/(mol K)

Real = Union[float, int]


@dataclass(frozen=True)
class LiquidFluid:
    """Liquid density model.

    Parameters
    ----------
    rho0 : float
        Density at reference conditions, kg/m3.
    T0 : float
        Reference temperature, degC.
    P0 : float
        Reference pressure, bar gauge.
    alpha : float
        Volumetric thermal expansion coefficient, 1/degC.
    kappa : float
        Isothermal compressibility coefficient, 1/bar.
    name : str
        Fluid name for reporting.
    """

    rho0: float
    T0: float = 15.0
    P0: float = 0.0
    alpha: float = 0.00085
    kappa: float = 1.0e-5
    name: str = "liquid"

    def density(self, T: Real, P: Real) -> float:
        return self.rho0 * (1.0 - self.alpha * (T - self.T0) + self.kappa * (P - self.P0))


@dataclass(frozen=True)
class GasFluid:
    """Real-gas density via the Redlich-Kwong equation of state.

    Parameters
    ----------
    Tc : float
        Critical temperature, K.
    Pc : float
        Critical pressure, Pa (absolute).
    M : float
        Molar mass, kg/kmol.
    name : str
        Fluid name for reporting.
    """

    Tc: float
    Pc: float
    M: float
    name: str = "gas"

    def z_factor(self, T: Real, P_abs: Real) -> float:
        """Compressibility factor Z from the Redlich-Kwong cubic (largest real root)."""
        a = 0.42748 * R_GAS**2 * self.Tc**2.5 / self.Pc
        b = 0.08664 * R_GAS * self.Tc / self.Pc
        A = a * P_abs / (R_GAS**2 * T**2.5)
        B = b * P_abs / (R_GAS * T)
        coeffs = (1.0, -1.0, A - B - B * B, -A * B)
        roots = _real_roots_of_cubic(*coeffs)
        return max(roots)

    def density(self, T: Real, P_abs: Real) -> float:
        """Density at temperature T (K) and absolute pressure P (Pa), kg/m3."""
        z = self.z_factor(T, P_abs)
        return P_abs * self.M / (1000.0 * z * R_GAS * T)


def _real_roots_of_cubic(a: Real, b: Real, c: Real, d: Real) -> list[float]:
    """Real roots of a x^3 + b x^2 + c x + d = 0 (depressed-cubic method)."""
    a, b, c, d = float(a), float(b), float(c), float(d)
    if abs(a) < 1e-15:
        return _real_roots_of_quadratic(b, c, d)
    p = (3 * a * c - b * b) / (3 * a * a)
    q = (2 * b * b * b - 9 * a * b * c + 27 * a * a * d) / (27 * a * a * a)
    disc = (q / 2.0) ** 2 + (p / 3.0) ** 3
    if disc > 0:
        u = (-q / 2.0 + disc**0.5) ** (1.0 / 3.0)
        v = (-q / 2.0 - disc**0.5) ** (1.0 / 3.0)
        return [u + v - b / (3 * a)]
    if disc == 0:
        u = (-q / 2.0) ** (1.0 / 3.0)
        r1 = 2 * u - b / (3 * a)
        r2 = -u - b / (3 * a)
        return [r1, r2]
    phi = _acos3(-q / (2.0 * (-disc) ** 0.5))
    base = 2.0 * (-disc) ** 0.5
    return [
        base * _cos(phi) - b / (3 * a),
        base * _cos(phi + 2.0 * 3.141592653589793 / 3.0) - b / (3 * a),
        base * _cos(phi + 4.0 * 3.141592653589793 / 3.0) - b / (3 * a),
    ]


def _real_roots_of_quadratic(a: Real, b: Real, c: Real) -> list[float]:
    disc = b * b - 4 * a * c
    if disc < 0:
        return []
    if disc == 0:
        return [-b / (2 * a)]
    return [(-b + disc**0.5) / (2 * a), (-b - disc**0.5) / (2 * a)]


def _acos3(x: Real) -> float:
    from math import acos

    return acos(max(-1.0, min(1.0, x)))


def _cos(x: Real) -> float:
    from math import cos

    return cos(x)
