from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np


ElementMass = Dict[str, float]  # kg/h of each element


@dataclass
class Stream:
    """Generic stream with element-wise mass flows (kg/h)."""

    name: str
    elements_kgph: ElementMass

    def total_mass_flow(self) -> float:
        return float(sum(self.elements_kgph.values()))

    def element(self, symbol: str) -> float:
        return float(self.elements_kgph.get(symbol, 0.0))


@dataclass
class ISFFeed:
    """
    ISF feed description (sinter or mixture of feeds).

    elements_wtfrac: mass fractions of elements in the feed (must sum to ~1.0).
    feed_rate_tph: feed rate in tonnes per hour.
    """

    elements_wtfrac: Dict[str, float]
    feed_rate_tph: float

    def to_stream(self, name: str = "Feed") -> Stream:
        total_kgph = self.feed_rate_tph * 1000.0
        elements_kgph = {
            el: wtfrac * total_kgph for el, wtfrac in self.elements_wtfrac.items()
        }
        return Stream(name=name, elements_kgph=elements_kgph)


@dataclass
class ISFOperatingConditions:
    """
    Operating conditions relevant for simple KPIs and SOP checks.

    coke_rate_kgph: total coke consumption (kg/h).
    zn_production_target_tph: expected zinc metal production (for KPIs only).
    coke_LHV_MJ_per_kg: lower heating value of coke (MJ/kg).

    Optional measured operating parameters can be provided for SOP compliance
    checks (temperatures, pressures, etc.).
    """

    coke_rate_kgph: float
    zn_production_target_tph: float
    coke_LHV_MJ_per_kg: float = 28.0

    # Optional measured operating parameters (from SOP)
    sinter_preheat_temp_C: float | None = None
    blast_pressure_bar: float | None = None
    reduction_zone_temp_C: float | None = None
    lead_splash_temp_C: float | None = None


@dataclass
class ISFRecoveryParameters:
    """
    Simple recovery and distribution parameters.

    Values represent fractions (0–1) of each element reporting to each product.
    """

    zn_to_metal: float = 0.92
    zn_to_slag: float = 0.05
    zn_to_gas: float = 0.03

    pb_to_metal: float = 0.95
    pb_to_slag: float = 0.03
    pb_to_gas: float = 0.02

    fe_to_slag: float = 0.98
    fe_to_metal: float = 0.0
    fe_to_gas: float = 0.02

    s_to_gas: float = 0.97  # as SO2, etc.
    s_to_slag: float = 0.03

    gangue_to_slag: float = 0.995  # Si, Ca, Mg, Al etc.


@dataclass
class ISFSimulationResult:
    feed: Stream
    coke: Stream
    metal: Stream
    slag: Stream
    gas: Stream
    operating: ISFOperatingConditions
    recoveries: ISFRecoveryParameters

    def kpi_zinc_recovery(self) -> float:
        feed_zn = self.feed.element("Zn")
        if feed_zn <= 0.0:
            return 0.0
        return 100.0 * self.metal.element("Zn") / feed_zn

    def kpi_coke_rate_GJ_per_tZn(self) -> float:
        zn_tph = self.metal.element("Zn") / 1000.0
        if zn_tph <= 0.0:
            return 0.0
        GJ_per_h = (self.operating.coke_rate_kgph * self.operating.coke_LHV_MJ_per_kg) / 1000.0
        return GJ_per_h / zn_tph

    def zn_metal_production_tph(self) -> float:
        """
        Actual zinc metal production rate based on the simulated metal stream.
        """
        return self.metal.element("Zn") / 1000.0


@dataclass
class ISFOperatingLimits:
    """
    SOP-based operating limits for key ISF parameters.

    Defaults are derived from ISF-SOP-001.
    """

    # Temperatures and pressures (Section 4)
    sinter_preheat_temp_target_C: float = 800.0
    sinter_preheat_temp_tol_C: float = 10.0

    blast_pressure_min_bar: float = 1.8
    blast_pressure_max_bar: float = 2.2

    lead_splash_temp_min_C: float = 450.0
    lead_splash_temp_max_C: float = 550.0

    # Slag and product specs (Sections 4.4, 5.2)
    slag_to_feed_ratio_target: float = 0.12  # 12 %
    slag_to_feed_ratio_tol: float = 0.03    # allow approx. 9–15 %

    residual_zn_in_slag_max_wtfrac: float = 0.02  # <2 % Zn in slag
    zinc_product_purity_min_wtfrac: float = 0.995  # ≥99.5 % Zn


@dataclass
class ISFComplianceResult:
    """Summary of how a simulation compares to SOP limits."""

    # Calculated ratios
    slag_to_feed_ratio: float
    slag_to_feed_within_limit: bool

    residual_zn_in_slag_wtfrac: float
    residual_zn_in_slag_within_limit: bool

    zinc_product_purity_wtfrac: float
    zinc_product_purity_within_spec: bool

    # Optional checks using measured operating data
    sinter_preheat_temp_within_spec: bool | None
    blast_pressure_within_spec: bool | None
    lead_splash_temp_within_spec: bool | None


def evaluate_sop_compliance(
    result: ISFSimulationResult,
    limits: ISFOperatingLimits | None = None,
) -> ISFComplianceResult:
    """
    Compare a simulation result and (optional) measured conditions
    against SOP-based limits (ISF-SOP-001, sections 4–5).
    """
    limits = limits or ISFOperatingLimits()

    feed_mass = result.feed.total_mass_flow()
    slag_mass = result.slag.total_mass_flow()
    slag_to_feed_ratio = slag_mass / feed_mass if feed_mass > 0.0 else 0.0

    slag_zn = result.slag.element("Zn")
    residual_zn_in_slag_wtfrac = slag_zn / slag_mass if slag_mass > 0.0 else 0.0

    metal_mass = result.metal.total_mass_flow()
    metal_zn = result.metal.element("Zn")
    zinc_product_purity_wtfrac = metal_zn / metal_mass if metal_mass > 0.0 else 0.0

    slag_to_feed_within_limit = abs(slag_to_feed_ratio - limits.slag_to_feed_ratio_target) <= limits.slag_to_feed_ratio_tol
    residual_zn_in_slag_within_limit = residual_zn_in_slag_wtfrac <= limits.residual_zn_in_slag_max_wtfrac
    zinc_product_purity_within_spec = zinc_product_purity_wtfrac >= limits.zinc_product_purity_min_wtfrac

    # Optional measured operating data checks
    op = result.operating

    if op.sinter_preheat_temp_C is not None:
        low = limits.sinter_preheat_temp_target_C - limits.sinter_preheat_temp_tol_C
        high = limits.sinter_preheat_temp_target_C + limits.sinter_preheat_temp_tol_C
        sinter_ok: bool | None = low <= op.sinter_preheat_temp_C <= high
    else:
        sinter_ok = None

    if op.blast_pressure_bar is not None:
        blast_ok: bool | None = limits.blast_pressure_min_bar <= op.blast_pressure_bar <= limits.blast_pressure_max_bar
    else:
        blast_ok = None

    if op.lead_splash_temp_C is not None:
        lead_ok: bool | None = limits.lead_splash_temp_min_C <= op.lead_splash_temp_C <= limits.lead_splash_temp_max_C
    else:
        lead_ok = None

    return ISFComplianceResult(
        slag_to_feed_ratio=slag_to_feed_ratio,
        slag_to_feed_within_limit=slag_to_feed_within_limit,
        residual_zn_in_slag_wtfrac=residual_zn_in_slag_wtfrac,
        residual_zn_in_slag_within_limit=residual_zn_in_slag_within_limit,
        zinc_product_purity_wtfrac=zinc_product_purity_wtfrac,
        zinc_product_purity_within_spec=zinc_product_purity_within_spec,
        sinter_preheat_temp_within_spec=sinter_ok,
        blast_pressure_within_spec=blast_ok,
        lead_splash_temp_within_spec=lead_ok,
    )

    def zn_metal_production_tph(self) -> float:
        """
        Actual zinc metal production rate based on the simulated metal stream.
        """
        return self.metal.element("Zn") / 1000.0


class ISFFurnace:
    """
    Simplified steady‑state ISF furnace model.

    This is a lumped, element‑wise mass balance model with
    user‑defined recovery/distribution fractions.
    """

    def __init__(
        self,
        recoveries: ISFRecoveryParameters | None = None,
    ) -> None:
        self.recoveries = recoveries or ISFRecoveryParameters()

    def simulate(
        self,
        feed: ISFFeed,
        op: ISFOperatingConditions,
    ) -> ISFSimulationResult:
        feed_stream = feed.to_stream("Feed")
        coke_stream = self._make_coke_stream(op.coke_rate_kgph)

        total_feed_elements = self._combine_streams([feed_stream, coke_stream])

        metal_elements: ElementMass = {}
        slag_elements: ElementMass = {}
        gas_elements: ElementMass = {}

        # Handle key elements explicitly
        zn = total_feed_elements.get("Zn", 0.0)
        pb = total_feed_elements.get("Pb", 0.0)
        fe = total_feed_elements.get("Fe", 0.0)
        s = total_feed_elements.get("S", 0.0)

        # Zinc
        metal_elements["Zn"] = zn * self.recoveries.zn_to_metal
        slag_elements["Zn"] = zn * self.recoveries.zn_to_slag
        gas_elements["Zn"] = zn * self.recoveries.zn_to_gas

        # Lead
        metal_elements["Pb"] = pb * self.recoveries.pb_to_metal
        slag_elements["Pb"] = pb * self.recoveries.pb_to_slag
        gas_elements["Pb"] = pb * self.recoveries.pb_to_gas

        # Iron
        metal_elements["Fe"] = fe * self.recoveries.fe_to_metal
        slag_elements["Fe"] = fe * self.recoveries.fe_to_slag
        gas_elements["Fe"] = fe * self.recoveries.fe_to_gas

        # Sulphur
        slag_elements["S"] = s * self.recoveries.s_to_slag
        gas_elements["S"] = s * self.recoveries.s_to_gas

        # Treat all other elements (gangue etc.) as going mostly to slag
        gangue_elements = {
            el: m
            for el, m in total_feed_elements.items()
            if el not in {"Zn", "Pb", "Fe", "S", "C", "O"}
        }
        for el, m in gangue_elements.items():
            to_slag = m * self.recoveries.gangue_to_slag
            to_gas = m - to_slag
            slag_elements[el] = slag_elements.get(el, 0.0) + to_slag
            gas_elements[el] = gas_elements.get(el, 0.0) + to_gas

        # Carbon and oxygen from coke → all to gas (CO, CO2)
        c = total_feed_elements.get("C", 0.0)
        o = total_feed_elements.get("O", 0.0)
        gas_elements["C"] = gas_elements.get("C", 0.0) + c
        gas_elements["O"] = gas_elements.get("O", 0.0) + o

        metal_stream = Stream("Metal", metal_elements)
        slag_stream = Stream("Slag", slag_elements)
        gas_stream = Stream("Off‑gas", gas_elements)

        return ISFSimulationResult(
            feed=feed_stream,
            coke=coke_stream,
            metal=metal_stream,
            slag=slag_stream,
            gas=gas_stream,
            operating=op,
            recoveries=self.recoveries,
        )

    @staticmethod
    def _make_coke_stream(coke_rate_kgph: float) -> Stream:
        # Simple fixed coke composition (mass fractions)
        wtfrac = {
            "C": 0.90,
            "S": 0.01,
            "Ash": 0.09,  # goes to slag as gangue
        }
        elements_kgph: ElementMass = {
            "C": wtfrac["C"] * coke_rate_kgph,
            "S": wtfrac["S"] * coke_rate_kgph,
            "Ash": wtfrac["Ash"] * coke_rate_kgph,
        }
        return Stream(name="Coke", elements_kgph=elements_kgph)

    @staticmethod
    def _combine_streams(streams: List[Stream]) -> ElementMass:
        combined: ElementMass = {}
        for s in streams:
            for el, m in s.elements_kgph.items():
                combined[el] = combined.get(el, 0.0) + m
        return combined

