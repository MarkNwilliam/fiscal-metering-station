"""Custody transfer ticket and audit report.

The ticket is the commercial hand-off document: the corrected (billed)
quantity, the meter factor that produced it, the uncertainty statement, and
the conditions it was computed at. Fiscal tickets must be tamper-evident --
every field is folded into an SHA-256 integrity hash, so any post-issue edit
is detectable on verification (the same data-integrity discipline regulated
records demand in WHO-GMP environments).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

INTEGRITY_SALT = "fiscal-metering-station:v1"


@dataclass
class CustodyTicket:
    """A single custody transfer batch ticket.

    Parameters
    ----------
    batch_id : str
    meter_id : str
    fluid : str
    start_reading, end_reading : indicated meter readings, m3.
    meter_factor : average proving meter factor applied.
    density : kg/m3 at flowing conditions (for reporting).
    avg_temperature : degC.
    avg_pressure : bar gauge.
    expanded_uncertainty : % at the stated coverage (usually k=2).
    uncertainty_k : coverage factor used for the uncertainty statement.
    issued_at : ISO timestamp; defaults to now.
    """

    batch_id: str
    meter_id: str
    fluid: str
    start_reading: float
    end_reading: float
    meter_factor: float
    density: float
    avg_temperature: float
    avg_pressure: float
    expanded_uncertainty: float
    uncertainty_k: float = 2.0
    issued_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def indicated_volume(self) -> float:
        return self.end_reading - self.start_reading

    @property
    def corrected_volume(self) -> float:
        return self.indicated_volume * self.meter_factor

    @property
    def corrected_mass(self) -> float:
        return self.corrected_volume * self.density

    def _canonical(self) -> str:
        """Deterministic serialisation of every ticket field."""
        payload = {
            "batch_id": self.batch_id,
            "meter_id": self.meter_id,
            "fluid": self.fluid,
            "start_reading": round(float(self.start_reading), 6),
            "end_reading": round(float(self.end_reading), 6),
            "meter_factor": round(float(self.meter_factor), 9),
            "density": round(float(self.density), 4),
            "avg_temperature": round(float(self.avg_temperature), 4),
            "avg_pressure": round(float(self.avg_pressure), 4),
            "expanded_uncertainty": round(float(self.expanded_uncertainty), 6),
            "uncertainty_k": float(self.uncertainty_k),
            "issued_at": self.issued_at,
            "salt": INTEGRITY_SALT,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @property
    def integrity_hash(self) -> str:
        return hashlib.sha256(self._canonical().encode("utf-8")).hexdigest()

    def verify(self, hash_to_check: str | None = None) -> bool:
        """True if the ticket is untampered (matches its recorded hash)."""
        target = hash_to_check or self.integrity_hash
        return self.integrity_hash == target

    def to_text(self) -> str:
        lines = [
            "=" * 58,
            "CUSTODY TRANSFER TICKET",
            "=" * 58,
            f"Batch ID            : {self.batch_id}",
            f"Meter ID            : {self.meter_id}",
            f"Fluid               : {self.fluid}",
            f"Issued (UTC)        : {self.issued_at}",
            "-" * 58,
            f"Start reading (m3)  : {self.start_reading:,.4f}",
            f"End reading (m3)    : {self.end_reading:,.4f}",
            f"Indicated volume    : {self.indicated_volume:,.4f}",
            f"Meter factor (MF)   : {self.meter_factor:.9f}",
            f"Corrected volume    : {self.corrected_volume:,.4f}",
            f"Density (kg/m3)     : {self.density:,.2f}",
            f"Corrected mass (kg) : {self.corrected_mass:,.2f}",
            "-" * 58,
            f"Avg temperature (C) : {self.avg_temperature:,.2f}",
            f"Avg pressure (bar)  : {self.avg_pressure:,.3f}",
            f"Expanded uncertainty: {self.expanded_uncertainty:.4f} % (k={self.uncertainty_k:.0f})",
            "-" * 58,
            f"Integrity (SHA-256) : {self.integrity_hash[:16]}...",
            "=" * 58,
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "meter_id": self.meter_id,
            "fluid": self.fluid,
            "issued_at": self.issued_at,
            "start_reading": self.start_reading,
            "end_reading": self.end_reading,
            "indicated_volume": self.indicated_volume,
            "meter_factor": self.meter_factor,
            "corrected_volume": self.corrected_volume,
            "density": self.density,
            "corrected_mass": self.corrected_mass,
            "expanded_uncertainty": self.expanded_uncertainty,
            "uncertainty_k": self.uncertainty_k,
            "integrity_hash": self.integrity_hash,
        }
