import math

import pytest

from flowlib.proving import DEFAULT_REPEATABILITY_LIMIT, MeterProving, correct_prover_volume, meter_factor
from flowlib.ticket import CustodyTicket
from flowlib.uncertainty import UncertaintyBudget, UncertaintySource


class TestMeterProving:
    def test_meter_factor_single_run(self):
        assert meter_factor(10.0, 10.0) == pytest.approx(1.0)
        assert meter_factor(10.0, 10.1) == pytest.approx(10.0 / 10.1)

    def test_average_meter_factor(self):
        p = MeterProving([10.0, 10.001, 9.999], [10.0, 10.0, 10.0])
        assert p.average_meter_factor == pytest.approx(mean([1.0, 1.0001, 0.9999]))
        assert len(p.meter_factors) == 3

    def test_repeatable_proving_passes(self):
        # 0.01% scatter -- well inside the 0.05% limit
        base = 10.0
        p = MeterProving(
            [base * (1 + 5e-5), base, base * (1 - 5e-5)],
            [10.0, 10.0, 10.0],
        )
        assert p.repeatability <= DEFAULT_REPEATABILITY_LIMIT
        assert p.is_repeatable

    def test_non_repeatable_proving_fails(self):
        base = 10.0
        p = MeterProving(
            [base * (1 + 5e-4), base, base * (1 - 5e-4)],
            [10.0, 10.0, 10.0],
        )
        assert not p.is_repeatable

    def test_apply_meter_factor(self):
        p = MeterProving([10.0, 10.001, 9.999], [10.0, 10.0, 10.0])
        corrected = p.apply(123.456)
        assert corrected == pytest.approx(123.456 * p.average_meter_factor)

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            MeterProving([1.0, 2.0], [1.0])

    def test_zero_indicated_volume_raises(self):
        with pytest.raises(ValueError):
            MeterProving([1.0], [0.0])


class TestProverCorrection:
    def test_steel_expansion_increases_prover_volume(self):
        v_cal = 1.0
        v_hot = correct_prover_volume(v_cal, T_operating=40.0, T_cal=15.0)
        assert v_hot > v_cal
        assert v_hot == pytest.approx(1.0 * (1 + 1.2e-5 * 25.0))


class TestUncertaintyBudget:
    def test_rectangular_standard_uncertainty(self):
        s = UncertaintySource("DP", 0.05, "rectangular", 1.0)
        assert s.standard_uncertainty == pytest.approx(0.05 / math.sqrt(3.0))

    def test_normal_standard_uncertainty(self):
        s = UncertaintySource("Cd", 0.5, "normal", 1.0)
        assert s.standard_uncertainty == pytest.approx(0.25)

    def test_sensitivity_scales_contribution(self):
        s = UncertaintySource("dP", 0.1, "rectangular", 0.5)
        assert s.standard_uncertainty == pytest.approx(0.1 / math.sqrt(3.0) * 0.5)

    def test_combined_is_rss_of_parts(self):
        b = UncertaintyBudget(type_a_std_uncertainty=0.02)
        b.add("DP", 0.05, "rectangular", 0.5)
        b.add("Density", 0.1, "rectangular", 0.5)
        ua = 0.02
        ub = math.sqrt((0.05 / math.sqrt(3) * 0.5) ** 2 + (0.1 / math.sqrt(3) * 0.5) ** 2)
        assert b.combined_standard_uncertainty == pytest.approx(math.sqrt(ua**2 + ub**2))

    def test_expanded_is_k_times_combined(self):
        b = UncertaintyBudget(type_a_std_uncertainty=0.05)
        b.add("Cd", 0.5, "normal")
        assert b.expanded_uncertainty == pytest.approx(2.0 * b.combined_standard_uncertainty)

    def test_table_shape(self):
        b = UncertaintyBudget(type_a_std_uncertainty=0.02)
        b.add("DP", 0.05, "rectangular", 0.5)
        rows = b.table()
        assert rows[-1]["source"].startswith("Expanded")


class TestCustodyTicket:
    def make_ticket(self, **kw):
        params = dict(
            batch_id="B-2026-001",
            meter_id="CT-01",
            fluid="Crude oil",
            start_reading=1000.0,
            end_reading=1050.0,
            meter_factor=0.9995,
            density=845.0,
            avg_temperature=28.0,
            avg_pressure=4.5,
            expanded_uncertainty=0.12,
            issued_at="2026-08-10T08:00:00+00:00",
        )
        params.update(kw)
        return CustodyTicket(**params)

    def test_corrected_volume_and_mass(self):
        t = self.make_ticket()
        assert t.indicated_volume == pytest.approx(50.0)
        assert t.corrected_volume == pytest.approx(50.0 * 0.9995)
        assert t.corrected_mass == pytest.approx(50.0 * 0.9995 * 845.0)

    def test_tamper_detection(self):
        t = self.make_ticket()
        original = t.integrity_hash
        assert t.verify(original)
        t.end_reading = 1055.0
        assert not t.verify(original)

    def test_text_ticket_contains_key_fields(self):
        text = self.make_ticket().to_text()
        for token in ("CUSTODY TRANSFER TICKET", "B-2026-001", "Meter factor", "Integrity"):
            assert token in text

    def test_to_dict_roundtrip(self):
        d = self.make_ticket().to_dict()
        assert d["integrity_hash"] == self.make_ticket().integrity_hash


def mean(xs):
    return sum(xs) / len(xs)
