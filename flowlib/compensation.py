"""Volume compensation to base conditions.

Custody transfer is billed on volume (or mass) corrected to *base*
conditions -- typically 15 degC / 1.01325 bar absolute. This module applies
the linearised liquid correction (a simplified API MPMS Ch. 11.1 form) and a
real-gas standard-volume conversion:

Liquid:
    V_base = V_flowing * CTPL * CPL
    CTPL = 1 / (1 + alpha * (T - T_base))          thermal
    CPL  = 1 - kappa * (P - P_base)                pressure

Gas:
    V_base = qm * t / rho_base(T_base, P_base)     mass is invariant
"""
from __future__ import annotations

from .fluids import GasFluid, LiquidFluid, Real


def liquid_ctpl(alpha: Real, T: Real, T_base: Real) -> float:
    """Thermal volume correction factor (simplified API 11.1 form)."""
    return 1.0 / (1.0 + alpha * (T - T_base))


def liquid_cpl(kappa: Real, P: Real, P_base: Real) -> float:
    """Pressure volume correction factor (linearised)."""
    return 1.0 - kappa * (P - P_base)


def compensate_liquid_volume(
    V_flowing: Real,
    fluid: LiquidFluid,
    T: Real,
    P: Real,
    T_base: Real = 15.0,
    P_base: Real = 0.0,
) -> float:
    """Volume corrected to base conditions, same units as V_flowing."""
    return (
        V_flowing
        * liquid_ctpl(fluid.alpha, T, T_base)
        * liquid_cpl(fluid.kappa, P, P_base)
    )


def compensate_gas_mass_to_base_volume(
    qm: Real,
    t: Real,
    fluid: GasFluid,
    T_base: Real = 288.15,
    P_base: Real = 1.01325e5,
) -> float:
    """Standard (base-condition) volume of a gas stream, m3.

    qm in kg/s, t in seconds. Density evaluated at base conditions.
    """
    rho_base = fluid.density(T_base, P_base)
    if rho_base <= 0:
        raise ValueError("invalid base density")
    return qm * t / rho_base
