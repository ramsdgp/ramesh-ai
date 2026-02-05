from __future__ import annotations

from tabulate import tabulate

from isf_simulation import (
    ISFFeed,
    ISFFurnace,
    ISFOperatingConditions,
    ISFOperatingLimits,
    evaluate_sop_compliance,
)


def print_stream_table(title: str, elements_kgph: dict[str, float]) -> None:
    rows = []
    total = sum(elements_kgph.values())
    for el, m in sorted(elements_kgph.items()):
        wt_pct = 100.0 * m / total if total > 0 else 0.0
        rows.append([el, f"{m:,.1f}", f"{wt_pct:6.2f}"])
    print(f"\n{title}")
    print(tabulate(rows, headers=["Element", "Mass (kg/h)", "Wt %"], tablefmt="github"))
    print(f"Total: {total:,.1f} kg/h\n")


def main() -> None:
    # Example: typical ISF sinter feed (simplified)
    feed = ISFFeed(
        elements_wtfrac={
            "Zn": 0.40,
            "Pb": 0.08,
            "Fe": 0.15,
            "S": 0.10,
            "Si": 0.12,
            "Ca": 0.08,
            "Mg": 0.03,
            "O": 0.04,
        },
        feed_rate_tph=80.0,  # 80 t/h sinter
    )

    # Operating conditions (including SOP-related temperatures/pressures)
    op = ISFOperatingConditions(
        coke_rate_kgph=18_000.0,  # 18 t/h coke
        zn_production_target_tph=30.0,
        coke_LHV_MJ_per_kg=28.0,
        sinter_preheat_temp_C=800.0,
        blast_pressure_bar=2.0,
        reduction_zone_temp_C=1250.0,
        lead_splash_temp_C=500.0,
    )

    furnace = ISFFurnace()
    result = furnace.simulate(feed, op)

    print("=== ISF Furnace Steady‑State Simulation ===")

    print_stream_table("Feed (incl. sinter only)", result.feed.elements_kgph)
    print_stream_table("Coke", result.coke.elements_kgph)
    print_stream_table("Metal product", result.metal.elements_kgph)
    print_stream_table("Slag product", result.slag.elements_kgph)
    print_stream_table("Off‑gas (elemental basis)", result.gas.elements_kgph)

    print("=== KPIs ===")
    print(f"Zinc recovery to metal: {result.kpi_zinc_recovery():5.1f} %")
    print(
        "Coke energy intensity: "
        f"{result.kpi_coke_rate_GJ_per_tZn():5.2f} GJ/t Zn (from coke only)"
    )

    # SOP-based compliance check using ISF-SOP-001 limits
    limits = ISFOperatingLimits()
    compliance = evaluate_sop_compliance(result, limits)

    print("\n=== SOP Compliance Check (ISF-SOP-001) ===")
    print(
        f"Slag-to-feed ratio: {compliance.slag_to_feed_ratio:.3f} "
        f"(target {limits.slag_to_feed_ratio_target:.3f} ± {limits.slag_to_feed_ratio_tol:.3f}) "
        f"-> {'OK' if compliance.slag_to_feed_within_limit else 'OUT OF SPEC'}"
    )
    print(
        f"Residual Zn in slag: {compliance.residual_zn_in_slag_wtfrac*100.0:4.2f} wt% "
        f"(limit {limits.residual_zn_in_slag_max_wtfrac*100.0:4.2f} wt%) "
        f"-> {'OK' if compliance.residual_zn_in_slag_within_limit else 'OUT OF SPEC'}"
    )
    print(
        f"Zinc product purity: {compliance.zinc_product_purity_wtfrac*100.0:5.2f} wt% "
        f"(min {limits.zinc_product_purity_min_wtfrac*100.0:5.2f} wt%) "
        f"-> {'OK' if compliance.zinc_product_purity_within_spec else 'OUT OF SPEC'}"
    )

    if compliance.sinter_preheat_temp_within_spec is not None:
        print(
            f"Sinter preheat temperature within SOP range: "
            f"{'YES' if compliance.sinter_preheat_temp_within_spec else 'NO'}"
        )
    if compliance.blast_pressure_within_spec is not None:
        print(
            f"Blast pressure within SOP range: "
            f"{'YES' if compliance.blast_pressure_within_spec else 'NO'}"
        )
    if compliance.lead_splash_temp_within_spec is not None:
        print(
            f"Lead splash temperature within SOP range: "
            f"{'YES' if compliance.lead_splash_temp_within_spec else 'NO'}"
        )


if __name__ == "__main__":
    main()

