"""fiscal-metering-station.

A standards-oriented toolkit for fiscal / custody-transfer flow
measurement: orifice (ISO 5167 / AGA-3) and Coriolis flow computation,
API MPMS Chapter 4 meter proving, GUM uncertainty analysis and tamper-evident
custody transfer tickets.

Modules
-------
fluids       : fluid density models (liquid thermal/compression, gas EOS)
orifice      : ISO 5167:2003 orifice-plate mass flow (Reader-Harris-Gallagher)
coriolis     : Coriolis mass flow, density from tube frequency, volume flow
compensation: temperature/pressure compensation to base conditions
proving      : API MPMS Ch.4 meter proving (meter factor, repeatability)
uncertainty  : GUM uncertainty budget (Type A + Type B, expanded k=2)
ticket       : custody transfer ticket and audit report with integrity hash
"""

from .orifice import orifice_mass_flow, discharge_coefficient, expansibility
from .proving import MeterProving, meter_factor
from .uncertainty import UncertaintyBudget
from .fluids import LiquidFluid, GasFluid
from .ticket import CustodyTicket

__version__ = "0.1.0"
__all__ = [
    "orifice_mass_flow",
    "discharge_coefficient",
    "expansibility",
    "MeterProving",
    "meter_factor",
    "UncertaintyBudget",
    "LiquidFluid",
    "GasFluid",
    "CustodyTicket",
]
