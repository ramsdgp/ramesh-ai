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
    page_title="ISF Zinc Operations Dashboard",
    layout="wide",
)

# Global HTML/CSS template for page chrome and KPI styling,
# inspired by the ISF Zinc Operations web dashboard.
st.markdown(
    """
    <style>
    body {
        background-color: #020617;
    }
    .page-header {
        padding: 0.75rem 0 1.25rem 0;
        border-bottom: 1px solid #1f2937;
        margin-bottom: 1rem;
    }
    .page-header h1 {
        margin-bottom: 0.15rem;
        font-size: 1.8rem;
        color: #e5e7eb;
    }
    .page-header p {
        color: #9ca3af;
        font-size: 0.95rem;
        margin-bottom: 0;
    }

    .kpi-card {
        background: #020617;
        border-radius: 0.75rem;
        padding: 0.75rem 1rem;
        border: 1px solid #1f2937;
        margin-bottom: 0.75rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.45);
    }
    .kpi-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #9ca3af;
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        font-size: 1.4rem;
        font-weight: 600;
        color: #f9fafb;
    }

    .section-title {
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        color: #e5e7eb;
    }

    .stage-card {
        background: #020617;
        border-radius: 0.75rem;
        padding: 0.75rem 1rem;
        border: 1px solid #1f2937;
        margin-bottom: 0.75rem;
    }
    .stage-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #e5e7eb;
        margin-bottom: 0.15rem;
    }
    .stage-temp {
        font-size: 0.95rem;
        color: #e5e7eb;
    }
    .stage-status-normal {
        font-size: 0.8rem;
        color: #22c55e;
    }
    .stage-status-alert {
        font-size: 0.8rem;
        color: #f97316;
    }

    .footer-note {
        margin-top: 2rem;
        font-size: 0.8rem;
        color: #6b7280;
    }
    </style>

    <div class="page-header">
        <h1>⚡ ISF Zinc Operations</h1>
        <p>Imperial Smelting Furnace – real‑time style monitoring with SOP (ISF‑SOP‑001) checks.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


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
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-title">Zinc recovery to metal (%)</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="kpi-value">{result.kpi_zinc_recovery():.1f}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-title">Today&#39;s Zn output (t/h)</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="kpi-value">{result.zn_metal_production_tph():.2f}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-title">Overall energy intensity (GJ/t Zn)</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="kpi-value">{result.kpi_coke_rate_GJ_per_tZn():.2f}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-title">Slag‑to‑feed ratio</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="kpi-value">{compliance.slag_to_feed_ratio:.3f}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-title">Zn in slag (wt%)</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="kpi-value">{compliance.residual_zn_in_slag_wtfrac*100.0:.2f}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-title">Zn product purity (wt%)</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="kpi-value">{compliance.zinc_product_purity_wtfrac*100.0:.2f}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Process flow status section (Sintering / Smelting / Condensation / Slag)
st.markdown('<h3 class="section-title">Process Flow Status</h3>', unsafe_allow_html=True)
pf_col1, pf_col2, pf_col3, pf_col4 = st.columns(4)

def status_class(ok: bool | None) -> str:
    if ok is None:
        return "stage-status-alert"
    return "stage-status-normal" if ok else "stage-status-alert"

with pf_col1:
    st.markdown(
        f"""
        <div class="stage-card">
            <div class="stage-title">Sintering</div>
            <div class="stage-temp">{op.sinter_preheat_temp_C:.0f}°C</div>
            <div class="{status_class(compliance.sinter_preheat_temp_within_spec)}">
                {"Normal" if compliance.sinter_preheat_temp_within_spec else "Check"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with pf_col2:
    st.markdown(
        f"""
        <div class="stage-card">
            <div class="stage-title">Smelting</div>
            <div class="stage-temp">{op.reduction_zone_temp_C:.0f}°C</div>
            <div class="{status_class(True)}">
                Normal
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with pf_col3:
    st.markdown(
        f"""
        <div class="stage-card">
            <div class="stage-title">Condensation</div>
            <div class="stage-temp">{op.lead_splash_temp_C:.0f}°C</div>
            <div class="{status_class(compliance.lead_splash_temp_within_spec)}">
                {"Normal" if compliance.lead_splash_temp_within_spec else "Check"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with pf_col4:
    st.markdown(
        f"""
        <div class="stage-card">
            <div class="stage-title">Slag Management</div>
            <div class="stage-temp">Slag/Feed {compliance.slag_to_feed_ratio*100.0:.1f}%</div>
            <div class="{status_class(compliance.slag_to_feed_within_limit)}">
                {"Normal" if compliance.slag_to_feed_within_limit else "Check"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<h3 class="section-title">SOP Compliance (ISF‑SOP‑001)</h3>', unsafe_allow_html=True)

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

st.markdown(
    '<h3 class="section-title">Stream Mass Balance (Elemental, kg/h)</h3>',
    unsafe_allow_html=True,
)

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

st.markdown(
    '<div class="footer-note">'
    "This simulator is for educational and conceptual purposes only, "
    "not detailed plant design."
    "</div>",
    unsafe_allow_html=True,
)
