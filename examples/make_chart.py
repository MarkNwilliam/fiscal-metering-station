"""Generate docs/fiscal_metering_station.png: RHG Cd vs Reynolds + proving repeatability."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flowlib.orifice import discharge_coefficient
from flowlib.proving import MeterProving

out = Path(__file__).resolve().parents[1] / "docs"

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))

re_range = np.logspace(4, 7, 80)
for beta in (0.25, 0.45, 0.65):
    cd = [discharge_coefficient(beta, re, D=100.0, taps="corner") for re in re_range]
    ax1.plot(re_range, cd, label=f"beta = {beta}")
ax1.set_xscale("log")
ax1.set_xlabel("Reynolds number (Re)")
ax1.set_ylabel("Reader-Harris-Gallagher Cd")
ax1.set_title("ISO 5167 / AGA-3 orifice discharge coefficient (corner taps, D=100 mm)")
ax1.legend(fontsize=9)
ax1.grid(alpha=0.3, which="both")

# proving: 3 runs with ~0.02 % run-to-run scatter around MF 1.0000
prover = MeterProving(prover_volumes=[0.9999, 1.0001, 1.0000], indicated_volumes=[1.0, 1.0, 1.0])
factors = prover.meter_factors
repeatability_pct = prover.repeatability * 100
passed = prover.repeatability <= prover.repeatability_limit

names = [f"run {i+1}" for i in range(len(factors))]
bars = ax2.bar(names, factors, width=0.5, color="#0b3d63")
ax2.axhline(1.0, color="#b3261e", ls="--", lw=1)
ax2.text(2.2, 1.00005, "target MF = 1.0000", ha="right", fontsize=8)
for b, f in zip(bars, factors):
    ax2.text(b.get_x() + b.get_width() / 2, f + 0.00002, f"{f:.5f}", ha="center", fontsize=8)
ax2.set_ylim(0.9995, 1.0006)
ax2.set_ylabel("meter factor")
ax2.set_title(f"API MPMS Ch.4 proving: repeatability {repeatability_pct:.3f} % "
              f"({'PASS' if passed else 'FAIL'} vs 0.05 % limit)")
ax2.grid(axis="y", alpha=0.3)

fig.suptitle("Fiscal Metering Station — validated ISO 5167 flow + API MPMS Ch.4 proving", fontsize=12)
fig.tight_layout()
p = out / "fiscal_metering_station.png"
fig.savefig(p, dpi=150)
print(f"wrote {p}")
