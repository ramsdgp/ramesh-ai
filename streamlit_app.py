from __future__ import annotations

import pandas as pd
import streamlit as st

from isf_simulation import (
    ISFFeed,
    ISFFurnace,
    ISFOperatingConditions,
    ISFOperatingLimits,
    evaluate_sop_compliance,
)


st.set_page_config(
    page_title="ISF Furnace – Zinc Plant Simulator",
    layout="wide",
)

st.title("Imperial Smelting Furnace (ISF) – Zinc Production Simulator")
st.caption("Steady‑state mass balance with SOP (ISF‑SOP‑001) compliance checks.")


@st.cache_data
def default_feed() -> ISFFeed:
    return ISFFeed(
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
        feed_rate_tph=80.0,
    )


limits = ISFOperatingLimits()

with st.sidebar:
    st.header("Feed & Operating Conditions")

    st.subheader("Sinter Feed")
    feed_rate = st.number_input("Feed rate (t/h)", min_value=10.0, max_value=200.0, value=80.0, step=5.0)

    st.markdown("**Feed composition (wt%)**")
    zn = st.slider("Zn", 10.0, 60.0, 40.0, 1.0)
    pb = st.slider("Pb", 0.0, 20.0, 8.0, 0.5)
    fe = st.slider("Fe", 0.0, 30.0, 15.0, 0.5)
    s = st.slider("S", 0.0, 20.0, 10.0, 0.5)
    si = st.slider("Si", 0.0, 30.0, 12.0, 0.5)
    ca = st.slider("Ca", 0.0, 20.0, 8.0, 0.5)
    mg = st.slider("Mg", 0.0, 10.0, 3.0, 0.5)
    o = st.slider("O", 0.0, 10.0, 4.0, 0.5)

    total_wt = zn + pb + fe + s + si + ca + mg + o
    if abs(total_wt - 100.0) > 1e-6:
        st.warning(f"Current sum of wt% = {total_wt:.1f}. Values will be normalised internally.")

    elements_wtfrac = {
        "Zn": zn / total_wt,
        "Pb": pb / total_wt,
        "Fe": fe / total_wt,
        "S": s / total_wt,
        "Si": si / total_wt,
        "Ca": ca / total_wt,
        "Mg": mg / total_wt,
        "O": o / total_wt,
    }

    st.subheader("Coke & Key Temperatures")
    coke_rate = st.number_input("Coke rate (kg/h)", min_value=5_000.0, max_value=40_000.0, value=18_000.0, step=1_000.0)

    sinter_preheat_temp = st.number_input(
        "Sinter preheat temperature (°C)",
        min_value=600.0,
        max_value=900.0,
        value=limits.sinter_preheat_temp_target_C,
        step=5.0,
    )
    blast_pressure = st.number_input(
        "Blast pressure (bar)",
        min_value=1.0,
        max_value=3.0,
        value=2.0,
        step=0.05,
    )
    reduction_zone_temp = st.number_input(
        "Reduction zone temperature (°C)",
        min_value=1100.0,
        max_value=1400.0,
        value=1250.0,
        step=10.0,
    )
    lead_splash_temp = st.number_input(
        "Lead splash temperature (°C)",
        min_value=400.0,
        max_value=600.0,
        value=500.0,
        step=5.0,
    )

feed = ISFFeed(elements_wtfrac=elements_wtfrac, feed_rate_tph=feed_rate)
op = ISFOperatingConditions(
    coke_rate_kgph=coke_rate,
    zn_production_target_tph=30.0,
    coke_LHV_MJ_per_kg=28.0,
    sinter_preheat_temp_C=sinter_preheat_temp,
    blast_pressure_bar=blast_pressure,
    reduction_zone_temp_C=reduction_zone_temp,
    lead_splash_temp_C=lead_splash_temp,
)

furnace = ISFFurnace()
result = furnace.simulate(feed, op)
compliance = evaluate_sop_compliance(result, limits)


def stream_to_df(name: str, elements: dict[str, float]) -> pd.DataFrame:
    total = sum(elements.values())
    rows = []
    for el, m in sorted(elements.items()):
        wt_pct = 100.0 * m / total if total > 0 else 0.0
        rows.append({"Element": el, "Mass (kg/h)": m, "Wt %": wt_pct})
    df = pd.DataFrame(rows)
    df.attrs["name"] = name
    return df


col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Production KPIs")
    st.metric("Zinc recovery to metal (%)", f"{result.kpi_zinc_recovery():.1f}")
    st.metric("Zn metal production (t/h)", f"{result.zn_metal_production_tph():.2f}")

with col2:
    st.subheader("Energy KPI")
    st.metric("Coke energy intensity (GJ/t Zn)", f"{result.kpi_coke_rate_GJ_per_tZn():.2f}")

with col3:
    st.subheader("Slag & Purity")
    st.metric("Slag/Feed mass ratio", f"{compliance.slag_to_feed_ratio:.3f}")
    st.metric("Residual Zn in slag (wt%)", f"{compliance.residual_zn_in_slag_wtfrac*100.0:.2f}")
    st.metric("Zn product purity (wt%)", f"{compliance.zinc_product_purity_wtfrac*100.0:.2f}")


st.markdown("---")
st.subheader("SOP Compliance (ISF‑SOP‑001)")

def status_tag(ok: bool | None) -> str:
    if ok is None:
        return "N/A"
    return "OK" if ok else "OUT OF SPEC"


compliance_rows = [
    {
        "Parameter": "Slag‑to‑feed ratio",
        "Value": f"{compliance.slag_to_feed_ratio:.3f}",
        "Target / Limit": f"{limits.slag_to_feed_ratio_target:.3f} ± {limits.slag_to_feed_ratio_tol:.3f}",
        "Status": status_tag(compliance.slag_to_feed_within_limit),
    },
    {
        "Parameter": "Residual Zn in slag (wt%)",
        "Value": f"{compliance.residual_zn_in_slag_wtfrac*100.0:.2f}",
        "Target / Limit": f"< {limits.residual_zn_in_slag_max_wtfrac*100.0:.2f}",
        "Status": status_tag(compliance.residual_zn_in_slag_within_limit),
    },
    {
        "Parameter": "Zn product purity (wt%)",
        "Value": f"{compliance.zinc_product_purity_wtfrac*100.0:.2f}",
        "Target / Limit": f">= {limits.zinc_product_purity_min_wtfrac*100.0:.2f}",
        "Status": status_tag(compliance.zinc_product_purity_within_spec),
    },
    {
        "Parameter": "Sinter preheat temperature (°C)",
        "Value": f"{op.sinter_preheat_temp_C:.1f}",
        "Target / Limit": f"{limits.sinter_preheat_temp_target_C:.0f} ± {limits.sinter_preheat_temp_tol_C:.0f}",
        "Status": status_tag(compliance.sinter_preheat_temp_within_spec),
    },
    {
        "Parameter": "Blast pressure (bar)",
        "Value": f"{op.blast_pressure_bar:.2f}",
        "Target / Limit": f"{limits.blast_pressure_min_bar:.1f}–{limits.blast_pressure_max_bar:.1f}",
        "Status": status_tag(compliance.blast_pressure_within_spec),
    },
    {
        "Parameter": "Lead splash temperature (°C)",
        "Value": f"{op.lead_splash_temp_C:.1f}",
        "Target / Limit": f"{limits.lead_splash_temp_min_C:.0f}–{limits.lead_splash_temp_max_C:.0f}",
        "Status": status_tag(compliance.lead_splash_temp_within_spec),
    },
]

df_compliance = pd.DataFrame(compliance_rows)
st.table(df_compliance)


st.markdown("---")
st.subheader("Stream Mass Balance (Elemental, kg/h)")

tab_feed, tab_coke, tab_metal, tab_slag, tab_gas = st.tabs(
    ["Feed", "Coke", "Metal", "Slag", "Off‑gas"]
)

with tab_feed:
    st.table(stream_to_df("Feed", result.feed.elements_kgph))
with tab_coke:
    st.table(stream_to_df("Coke", result.coke.elements_kgph))
with tab_metal:
    st.table(stream_to_df("Metal", result.metal.elements_kgph))
with tab_slag:
    st.table(stream_to_df("Slag", result.slag.elements_kgph))
with tab_gas:
    st.table(stream_to_df("Off‑gas", result.gas.elements_kgph))

