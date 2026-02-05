"""
ISF furnace simulation package.

Provides simple, steady‑state mass‑balance style models for an
Imperial Smelting Furnace (zinc/lead plant).
"""

from .model import (
    Stream,
    ISFFeed,
    ISFOperatingConditions,
    ISFRecoveryParameters,
    ISFSimulationResult,
    ISFFurnace,
    ISFOperatingLimits,
    ISFComplianceResult,
    evaluate_sop_compliance,
)

__all__ = [
    "Stream",
    "ISFFeed",
    "ISFOperatingConditions",
    "ISFRecoveryParameters",
    "ISFSimulationResult",
    "ISFFurnace",
    "ISFOperatingLimits",
    "ISFComplianceResult",
    "evaluate_sop_compliance",
]

