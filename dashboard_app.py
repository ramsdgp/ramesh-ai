from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from isf_simulation import ISFFeed, ISFFurnace, ISFOperatingConditions


st.set_page_config(
    page_title="ISF Furnace Dashboard",
    layout="wide",
)


def run_single_simulation(
    feed_rate_tph: float,
    zn_wtfrac: float,
    pb_wtfrac: float,
    fe_wtfrac: float,
    s_wtfrac: float,
    si_wtfrac: float,
    ca_wtfrac: float,
    mg_wtfrac: float,
    o_wtfrac: float,
    coke_rate_kgph: float,
    zn_target_tph: float,
    coke_lhv_MJ_per_kg: float,
):
    elements_wtfrac = {
        "Zn": zn_wtfrac,
        "Pb": pb_wtfrac,
        "Fe": fe_wtfrac,
        "S": s_wtfrac,
        "Si": si_wtfrac,
        "Ca": ca_wtfrac,
        "Mg": mg_wtfrac,
        "O": o_wtfrac,
    }
    # Normalise in case the user changed values a lot
    total = sum(elements_wtfrac.values())
    if total > 0:
        elements_wtfrac = {k: v / total for k, v in elements_wtfrac.items()}

    feed = ISFFeed(elements_wtfrac=elements_wtfrac, feed_rate_tph=feed_rate_tph)
    op = ISFOperatingConditions(
        coke_rate_kgph=coke_rate_kgph,
        zn_production_target_tph=zn_target_tph,
        coke_LHV_MJ_per_kg=coke_lhv_MJ_per_kg,
    )

    furnace = ISFFurnace()
    result = furnace.simulate(feed, op)

    zn_recovery = result.kpi_zinc_recovery()
    coke_intensity = result.kpi_coke_rate_GJ_per_tZn()
    zn_prod_tph = result.zn_metal_production_tph()

    return result, zn_recovery, coke_intensity, zn_prod_tph


def build_recommendations(
    zn_recovery: float,
    coke_intensity: float,
    zn_prod_tph: float,
    zn_target_tph: float,
):
    recs: list[str] = []

    # Recovery-focused recommendations
    if zn_recovery < 85.0:
        recs.append(
            "Zinc recovery is relatively low. Consider improving feed preparation "
            "(e.g. sinter quality, temperature profile) or adjusting furnace conditions "
            "to increase metal recovery."
        )
    elif zn_recovery < 92.0:
        recs.append(
            "Zinc recovery is moderate. Small improvements in operating practice or "
            "feed quality could push recovery into a higher performance band."
        )
    else:
        recs.append(
            "Zinc recovery is high. Focus on maintaining stable operating conditions "
            "and monitoring for early signs of deterioration."
        )

    # Energy / coke intensity recommendations
    if coke_intensity > 4.5:
        recs.append(
            "Coke energy intensity is high. Investigate opportunities to reduce coke "
            "rate (better air distribution, burden distribution, or heat recovery) "
            "while maintaining metal quality."
        )
    elif coke_intensity > 3.5:
        recs.append(
            "Coke energy intensity is acceptable but could likely be reduced. "
            "Consider optimisation trials with slightly lower coke rates."
        )
    elif coke_intensity > 0.0:
        recs.append(
            "Coke energy intensity is relatively low for the assumed zinc output. "
            "Ensure that this is sustainable and does not compromise furnace stability."
        )

    # Production vs target
    if zn_prod_tph < 0.9 * zn_target_tph:
        recs.append(
            "Simulated zinc production is well below the target. Consider increasing "
            "feed rate, improving recovery, or revisiting the production target."
        )
    elif zn_prod_tph > 1.1 * zn_target_tph:
        recs.append(
            "Simulated zinc production is above the target. This may be acceptable, "
            "but confirm that downstream units can handle the extra throughput."
        )
    else:
        recs.append(
            "Simulated zinc production is close to the target, which indicates a "
            "good match between furnace operation and planning assumptions."
        )

    return recs


def main():
    st.title("ISF Furnace Dashboard")
    st.markdown(
        "Interactive dashboard on top of the simplified Imperial Smelting Furnace "
        "model. Adjust inputs, run simulations, and view KPI trends and "
        "recommendations."
    )

    with st.sidebar:
        st.header("Feed and operating inputs")

        feed_rate_tph = st.slider("Feed rate (t/h)", 40.0, 120.0, 80.0, 1.0)

        st.subheader("Feed composition (mass fractions)")
        col1, col2 = st.columns(2)
        with col1:
            zn_wtfrac = st.number_input("Zn", 0.0, 1.0, 0.40, 0.01, format="%.2f")
            pb_wtfrac = st.number_input("Pb", 0.0, 1.0, 0.08, 0.01, format="%.2f")
            fe_wtfrac = st.number_input("Fe", 0.0, 1.0, 0.15, 0.01, format="%.2f")
            s_wtfrac = st.number_input("S", 0.0, 1.0, 0.10, 0.01, format="%.2f")
        with col2:
            si_wtfrac = st.number_input("Si", 0.0, 1.0, 0.12, 0.01, format="%.2f")
            ca_wtfrac = st.number_input("Ca", 0.0, 1.0, 0.08, 0.01, format="%.2f")
            mg_wtfrac = st.number_input("Mg", 0.0, 1.0, 0.03, 0.01, format="%.2f")
            o_wtfrac = st.number_input("O", 0.0, 1.0, 0.04, 0.01, format="%.2f")

        st.subheader("Operating conditions")
        coke_rate_kgph = st.slider("Coke rate (kg/h)", 10000.0, 25000.0, 18000.0, 500.0)
        zn_target_tph = st.slider("Zn production target (t/h)", 10.0, 50.0, 30.0, 1.0)
        coke_lhv = st.slider(
            "Coke LHV (MJ/kg)", 20.0, 32.0, 28.0, 0.5, help="Lower heating value of coke"
        )

        st.markdown("---")
        num_scenarios = st.slider(
            "Number of simulation points for sweep",
            min_value=5,
            max_value=25,
            value=11,
            step=2,
            help="Used to generate the KPI vs coke-rate graph.",
        )

    # Run base-case simulation
    base_result, base_zn_rec, base_coke_int, base_zn_prod = run_single_simulation(
        feed_rate_tph=feed_rate_tph,
        zn_wtfrac=zn_wtfrac,
        pb_wtfrac=pb_wtfrac,
        fe_wtfrac=fe_wtfrac,
        s_wtfrac=s_wtfrac,
        si_wtfrac=si_wtfrac,
        ca_wtfrac=ca_wtfrac,
        mg_wtfrac=mg_wtfrac,
        o_wtfrac=o_wtfrac,
        coke_rate_kgph=coke_rate_kgph,
        zn_target_tph=zn_target_tph,
        coke_lhv_MJ_per_kg=coke_lhv,
    )

    # KPI cards
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    with kpi_col1:
        st.metric("Zinc recovery to metal (%)", f"{base_zn_rec:5.1f}")
    with kpi_col2:
        st.metric("Coke energy intensity (GJ/t Zn)", f"{base_coke_int:5.2f}")
    with kpi_col3:
        st.metric("Zn metal production (t/h)", f"{base_zn_prod:5.2f}")

    st.markdown("---")

    # Generate a coke-rate sweep around the selected operating point
    sweep_min = max(5000.0, coke_rate_kgph * 0.6)
    sweep_max = coke_rate_kgph * 1.4
    sweep_rates = np.linspace(sweep_min, sweep_max, num_scenarios)

    records = []
    for rate in sweep_rates:
        _, zn_rec, coke_int, zn_prod = run_single_simulation(
            feed_rate_tph=feed_rate_tph,
            zn_wtfrac=zn_wtfrac,
            pb_wtfrac=pb_wtfrac,
            fe_wtfrac=fe_wtfrac,
            s_wtfrac=s_wtfrac,
            si_wtfrac=si_wtfrac,
            ca_wtfrac=ca_wtfrac,
            mg_wtfrac=mg_wtfrac,
            o_wtfrac=o_wtfrac,
            coke_rate_kgph=float(rate),
            zn_target_tph=zn_target_tph,
            coke_lhv_MJ_per_kg=coke_lhv,
        )
        records.append(
            {
                "Coke rate (kg/h)": float(rate),
                "Zinc recovery (%)": zn_rec,
                "Coke energy intensity (GJ/t Zn)": coke_int,
                "Zn production (t/h)": zn_prod,
            }
        )

    df = pd.DataFrame.from_records(records)

    # Graphs section
    st.subheader("KPI trends vs coke rate")
    graph_col1, graph_col2 = st.columns(2)

    with graph_col1:
        st.caption("Zinc recovery vs coke rate")
        st.line_chart(
            df.set_index("Coke rate (kg/h)")[["Zinc recovery (%)"]],
            height=300,
        )

    with graph_col2:
        st.caption("Coke energy intensity vs coke rate")
        st.line_chart(
            df.set_index("Coke rate (kg/h)")[["Coke energy intensity (GJ/t Zn)"]],
            height=300,
        )

    st.subheader("Simulation table")
    st.dataframe(df.style.format(precision=2), use_container_width=True)

    # Recommendations
    st.subheader("Recommendations")
    recs = build_recommendations(
        zn_recovery=base_zn_rec,
        coke_intensity=base_coke_int,
        zn_prod_tph=base_zn_prod,
        zn_target_tph=zn_target_tph,
    )

    for i, rec in enumerate(recs, start=1):
        st.markdown(f"**{i}.** {rec}")

    st.markdown(
        "<small>This dashboard is based on a simplified steady‑state model and is "
        "intended for educational and conceptual analysis, not detailed plant design.</small>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

