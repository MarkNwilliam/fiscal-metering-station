"""End-to-end demo: a fiscal liquid (crude) transfer on a Coriolis meter.

Pipeline of a real custody-transfer batch:

1.  Prove the meter -> meter factor + repeatability check (API MPMS Ch.4)
2.  Compute live mass/volume flow + density (Coriolis signals)
3.  Compensate volume to base conditions (simplified API 11.1)
4.  Build a GUM uncertainty budget and the expanded (k=2) statement
5.  Issue a tamper-evident custody transfer ticket

Run:  python examples/example_run.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flowlib.compensation import compensate_liquid_volume
from flowlib.coriolis import CoriolisMeter
from flowlib.fluids import LiquidFluid
from flowlib.proving import MeterProving, correct_prover_volume
from flowlib.ticket import CustodyTicket
from flowlib.uncertainty import UncertaintyBudget


def main() -> None:
    print("=" * 62)
    print("FISCAL CUSTODY TRANSFER BATCH -- CRUDE OIL (CORIOLIS RUN)")
    print("=" * 62)

    # ---- 1. Meter proving (API MPMS Ch.4) -------------------------------
    # Prover calibrated at 15 degC; operating at 30 degC -> steel expansion.
    v_cal = 1.0
    prover_volumes = [
        correct_prover_volume(v_cal, T_operating=30.0, T_cal=15.0)
        for _ in range(3)
    ]
    # Small run-to-run scatter in the meter's indicated volumes.
    indicated = [1.00042, 1.00038, 1.00045]
    proving = MeterProving(prover_volumes, indicated)
    print(f"\n--- METER PROVING (API MPMS Ch.4) ---")
    for i, mf in enumerate(proving.meter_factors, 1):
        print(f"  Run {i}: meter factor = {mf:.6f}")
    print(f"  Average meter factor : {proving.average_meter_factor:.6f}")
    print(f"  Repeatability        : {proving.repeatability*1e2:.4f} %  "
          f"({'PASS' if proving.is_repeatable else 'FAIL'})")

    # ---- 2. Coriolis live flow ------------------------------------------
    crude = LiquidFluid(rho0=850.0, T0=15.0, alpha=0.00085, kappa=1.0e-5,
                        name="crude oil")
    meter = CoriolisMeter(K=0.02, A=1.2e6, B=50.0)
    phase, freq = 25.0, 40.0          # raw meter signals
    qm = meter.mass_flow(phase)
    rho = meter.density(freq)
    qv = meter.volume_flow(phase, freq)
    T, P = 30.0, 4.0                   # degC, bar gauge
    rho_calc = crude.density(T, P)
    print(f"\n--- CORIOLIS LIVE FLOW ---")
    print(f"  Mass flow           : {qm*3600:,.1f} kg/h")
    print(f"  Density (frequency) : {rho:,.1f} kg/m3")
    print(f"  Density (fluid mod.) : {rho_calc:,.1f} kg/m3")
    print(f"  Volume flow         : {qv*3600:,.2f} m3/h")

    # ---- 3. Batch totals + base compensation -----------------------------
    hours = 8.0
    V_indicated = qv * 3600.0 * hours
    V_corrected = proving.apply(V_indicated)
    V_base = compensate_liquid_volume(V_corrected, crude, T, P)
    print(f"\n--- BATCH TOTALS ({hours:.0f} h run) ---")
    print(f"  Indicated volume    : {V_indicated:,.2f} m3")
    print(f"  MF-corrected volume : {V_corrected:,.2f} m3")
    print(f"  Base-condition vol. : {V_base:,.2f} m3 (15 C, 0 bar g)")

    # ---- 4. GUM uncertainty budget ---------------------------------------
    ua = proving.std_dev / proving.average_meter_factor
    budget = UncertaintyBudget(type_a_std_uncertainty=ua * 100.0)
    budget.add("Mass-flow calibration (k-factor)", 0.05, "normal", 1.0)
    budget.add("Density (tube frequency)", 0.1, "rectangular", 0.5)
    budget.add("Temperature (avg, 0.5 C)", 0.05, "rectangular", 1.0)
    budget.add("Pressure (0.1 % of reading)", 0.1, "rectangular", 0.2)
    budget.add("Flow computer / A-D", 0.05, "rectangular", 1.0)
    U = budget.expanded_uncertainty
    print(f"\n--- GUM UNCERTAINTY BUDGET (k={budget.coverage_factor:.0f}) ---")
    for row in budget.table():
        print(f"  {row['source']:<52} {row['u (%)']:>7.4f} %")

    # ---- 5. Custody ticket -----------------------------------------------
    ticket = CustodyTicket(
        batch_id="B-2026-0810-01",
        meter_id="CMF-400-RUN-A",
        fluid=crude.name,
        start_reading=0.0,
        end_reading=V_indicated,
        meter_factor=proving.average_meter_factor,
        density=rho,
        avg_temperature=T,
        avg_pressure=P,
        expanded_uncertainty=U,
    )
    print("\n" + ticket.to_text())
    assert ticket.verify()
    print("  VERIFIED: integrity hash matches -- ticket untampered.")


if __name__ == "__main__":
    main()
