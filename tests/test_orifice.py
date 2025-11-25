import math

import pytest

from flowlib.fluids import GasFluid, LiquidFluid
from flowlib.orifice import (
    discharge_coefficient,
    expansibility,
    orifice_mass_flow,
)


class TestDischargeCoefficient:
    def test_typical_value_within_iso_band(self):
        # ISO 5167 RHG: C is a weak function of beta, ~0.597-0.61 in-range.
        # Published RHG values for beta=0.25 sit slightly below 0.60, which
        # the equation reproduces -- so the band is wide on purpose.
        for beta in (0.25, 0.5, 0.65):
            for taps in ("corner", "flange", "D_D/2"):
                c = discharge_coefficient(beta, Re_D=1e6, D=100.0, taps=taps)
                assert 0.59 <= c <= 0.62, (beta, taps, c)

    def test_mid_beta_value_close_to_published(self):
        # beta=0.5, flange taps, D=100mm, Re=1e6: RHG ~0.604
        c = discharge_coefficient(0.5, Re_D=1e6, D=100.0, taps="flange")
        assert 0.602 < c < 0.606

    def test_invalid_beta_raises(self):
        with pytest.raises(ValueError):
            discharge_coefficient(0.9, Re_D=1e6, D=100.0)

    def test_invalid_taps_raises(self):
        with pytest.raises(ValueError):
            discharge_coefficient(0.5, Re_D=1e6, D=100.0, taps="nope")


class TestExpansibility:
    def test_liquid_returns_one(self):
        assert expansibility(0.5, 100e3, 100e3, 1.3) == pytest.approx(1.0)

    def test_gas_between_zero_and_one(self):
        eps = expansibility(0.5, 10e5, 9e5, 1.3)
        assert 0.9 < eps < 1.0

    def test_lower_dp_ratio_gives_lower_epsilon(self):
        e1 = expansibility(0.5, 10e5, 9.5e5, 1.3)
        e2 = expansibility(0.5, 10e5, 8e5, 1.3)
        assert e2 < e1

    def test_below_validity_ratio_raises(self):
        with pytest.raises(ValueError):
            expansibility(0.5, 10e5, 6e5, 1.3)


class TestOrificeMassFlow:
    def test_consistency_with_orifice_equation(self):
        # 4" line, 2" bore, water, 1 bar dP
        D, d, dP, rho, mu = 0.1023, 0.05115, 100e3, 998.0, 1.0e-3
        qm = orifice_mass_flow(D, d, dP, rho, mu, taps="flange")
        beta = d / D
        c = discharge_coefficient(beta, 4 * qm / (math.pi * D * mu), D * 1000.0, "flange")
        expected = (c / math.sqrt(1 - beta**4)) * (math.pi / 4) * d**2 * math.sqrt(2 * dP * rho)
        assert qm == pytest.approx(expected, rel=1e-6)

    def test_flow_increases_with_differential_pressure(self):
        q1 = orifice_mass_flow(0.1023, 0.05115, 50e3, 998.0, 1.0e-3)
        q2 = orifice_mass_flow(0.1023, 0.05115, 200e3, 998.0, 1.0e-3)
        assert q2 > q1

    def test_compressible_vs_incompressible(self):
        # Gas expands across the plate: epsilon < 1 reduces flow slightly
        D, d, dP = 0.2, 0.1, 20e3
        rho, mu = 60.0, 1.2e-5
        q_incomp = orifice_mass_flow(D, d, dP, rho, mu)
        q_comp = orifice_mass_flow(D, d, dP, rho, mu, P1=30e5, P2=29.8e5, kappa=1.3)
        assert q_comp < q_incomp

    def test_invalid_geometry_raises(self):
        with pytest.raises(ValueError):
            orifice_mass_flow(0.1, 0.1, 100e3, 998.0, 1.0e-3)


class TestFluids:
    def test_liquid_density_temperature_and_pressure_signs(self):
        f = LiquidFluid(rho0=850.0, alpha=0.00085, kappa=1e-5)
        assert f.density(20, 0) < f.density(15, 0)
        assert f.density(15, 10) > f.density(15, 0)

    def test_gas_density_near_ideal_at_ambient(self):
        methane = GasFluid(Tc=190.6, Pc=4.60e6, M=16.04)
        z = methane.z_factor(T=300.0, P_abs=1.01325e5)
        assert 0.99 < z < 1.0
        rho_ideal = 1.01325e5 * 16.04 / (1000.0 * 8.314462618 * 300.0)
        assert methane.density(300.0, 1.01325e5) == pytest.approx(rho_ideal / z, rel=1e-6)

    def test_gas_density_increases_with_pressure(self):
        methane = GasFluid(Tc=190.6, Pc=4.60e6, M=16.04)
        assert methane.density(300.0, 1e6) > methane.density(300.0, 1e5)
