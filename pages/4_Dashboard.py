"""
Page 4 — Agri Risk Intelligence Panel (Internal Dashboard)
============================================================
Insurance-facing internal view. Not linked from the farmer flow.
Access directly via sidebar navigation or URL /4_Dashboard.

Shows portfolio-level risk segmentation, geographic distribution,
crop-wise margin analysis, and cost pressure breakdown.

Data source priority:
  1. Real database (stub)
  2. Live usage log (from logger.py)
  3. Synthetic/simulated data (for demonstration)
"""

import streamlit as st
import pandas as pd
from core.data_service import get_portfolio_data, compute_risk_segments
from core.crop_data import get_crop_display_name

st.set_page_config(page_title="Risk Intelligence Panel | FRO", page_icon="📈", layout="wide")

# ── Auth notice (placeholder) ──────────────────────────────────────────────────
st.sidebar.warning("⚠️ Internal view. Not for farmer distribution.")

st.title("📈 Agri Risk Intelligence Panel")
st.caption("Internal advisory dashboard — for insurance risk analysis only.")

# ── Load data ──────────────────────────────────────────────────────────────────
with st.spinner("Loading portfolio data..."):
    portfolio = get_portfolio_data()

events  = portfolio["events"]
source  = portfolio["source"]
n_total = portfolio["count"]

# ── Data source disclaimer ─────────────────────────────────────────────────────
if source == "synthetic":
    st.warning(
        "📊 **Simulated dataset** — 150 synthetic farmers generated for demonstration. "
        "Patterns are realistic but not from real usage. "
        "This panel will automatically switch to real data as farmers use the app."
    )
elif source == "live_log":
    st.success(f"✅ **Live data** — {n_total} real usage events from app log.")
else:
    st.success(f"✅ **Database** — {n_total} records loaded.")

st.divider()

# ── Section 1: Portfolio Overview ─────────────────────────────────────────────
st.subheader("📊 Portfolio Overview")

margins       = [e.get("margin_per_acre", 0) for e in events]
avg_margin    = round(sum(margins) / len(margins)) if margins else 0
risk_segs     = compute_risk_segments(events)
llm_used_ct   = sum(1 for e in events if e.get("llm_used"))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Analyses",      f"{n_total:,}")
col2.metric("Avg Margin / Acre",   f"Rs.{avg_margin:,}")
col3.metric("High-Risk Farmers",   f"{risk_segs['high_pct']}%",
            delta=f"{risk_segs['high']} farmers", delta_color="inverse")
col4.metric("AI Advisory Used",    f"{llm_used_ct}")

st.divider()

# ── Section 2: Risk Segmentation ──────────────────────────────────────────────
st.subheader("🚦 Risk Segmentation")
st.caption("Low: margin >Rs.10k/acre  |  Medium: Rs.5k–10k  |  High: <Rs.5k (risk flag)")

seg_data = pd.DataFrame({
    "Risk Level": ["🟢 Low Risk",   "🟡 Medium Risk", "🔴 High Risk"],
    "Farmers":    [risk_segs["low"], risk_segs["medium"], risk_segs["high"]],
    "% of Portfolio": [f"{risk_segs['low_pct']}%", f"{risk_segs['medium_pct']}%", f"{risk_segs['high_pct']}%"],
    "Margin Threshold": [">Rs.10,000/acre", "Rs.5,000–10,000/acre", "<Rs.5,000/acre"],
})
st.dataframe(seg_data, use_container_width=True, hide_index=True)

# Bar chart
chart_data = pd.DataFrame({
    "Risk Level": ["Low", "Medium", "High"],
    "Count": [risk_segs["low"], risk_segs["medium"], risk_segs["high"]],
})
st.bar_chart(chart_data.set_index("Risk Level"))

st.divider()

# ── Section 3: State-wise Risk ─────────────────────────────────────────────────
st.subheader("🗺️ State-wise Risk Distribution")

state_data = {}
for e in events:
    state = e.get("state", "Unknown")
    if state not in state_data:
        state_data[state] = {"total": 0, "high_risk": 0, "margins": []}
    state_data[state]["total"] += 1
    if e.get("risk_flag"):
        state_data[state]["high_risk"] += 1
    mpa = e.get("margin_per_acre", 0)
    if mpa:
        state_data[state]["margins"].append(mpa)

state_rows = []
for state, d in sorted(state_data.items(), key=lambda x: x[1]["high_risk"], reverse=True):
    avg_m = round(sum(d["margins"]) / len(d["margins"])) if d["margins"] else 0
    risk_pct = round(d["high_risk"] / d["total"] * 100, 1) if d["total"] > 0 else 0
    risk_label = "🔴 High" if risk_pct > 50 else ("🟡 Medium" if risk_pct > 25 else "🟢 Low")
    state_rows.append({
        "State":           state,
        "Analyses":        d["total"],
        "High-Risk %":     f"{risk_pct}%",
        "Avg Margin/Acre": f"Rs.{avg_m:,}",
        "Risk Level":      risk_label,
    })
st.dataframe(pd.DataFrame(state_rows), use_container_width=True, hide_index=True)

st.divider()

# ── Section 4: Crop-wise Risk ─────────────────────────────────────────────────
st.subheader("🌾 Crop-wise Margin Analysis")

crop_data_agg = {}
for e in events:
    crop = e.get("crop", "unknown")
    if crop not in crop_data_agg:
        crop_data_agg[crop] = {"total": 0, "high_risk": 0, "margins": []}
    crop_data_agg[crop]["total"] += 1
    if e.get("risk_flag"):
        crop_data_agg[crop]["high_risk"] += 1
    mpa = e.get("margin_per_acre", 0)
    if mpa:
        crop_data_agg[crop]["margins"].append(mpa)

crop_rows = []
for crop, d in sorted(crop_data_agg.items(), key=lambda x: x[1]["total"], reverse=True):
    avg_m    = round(sum(d["margins"]) / len(d["margins"])) if d["margins"] else 0
    risk_pct = round(d["high_risk"] / d["total"] * 100, 1) if d["total"] > 0 else 0
    risk_label = "🔴 High" if risk_pct > 50 else ("🟡 Medium" if risk_pct > 25 else "🟢 Low")
    crop_rows.append({
        "Crop":             get_crop_display_name(crop, "en"),
        "Analyses":         d["total"],
        "Avg Margin/Acre":  f"Rs.{avg_m:,}",
        "High-Risk %":      f"{risk_pct}%",
        "Risk Assessment":  risk_label,
    })
st.dataframe(pd.DataFrame(crop_rows), use_container_width=True, hide_index=True)

st.divider()

# ── Section 5: Cost Pressure ──────────────────────────────────────────────────
st.subheader("💸 Cost Pressure Indicators")
st.caption("Based on computed cost-to-revenue ratios across all analyses.")

cost_ratios = []
for e in events:
    rev  = e.get("gross_revenue", 0)
    cost = e.get("total_cost", 0)
    if rev > 0:
        cost_ratios.append(round(cost / rev * 100, 1))

if cost_ratios:
    avg_cost_ratio = round(sum(cost_ratios) / len(cost_ratios), 1)
    above_80 = sum(1 for r in cost_ratios if r > 80)
    above_80_pct = round(above_80 / len(cost_ratios) * 100, 1)

    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Avg Cost/Revenue Ratio", f"{avg_cost_ratio}%",
               help="Above 80% = financially stressed")
    cc2.metric("Farmers with Cost > 80% of Revenue",
               f"{above_80_pct}%", delta=f"{above_80} farmers", delta_color="inverse")
    cc3.metric("Financially Comfortable (<60% cost ratio)",
               f"{round(sum(1 for r in cost_ratios if r < 60)/len(cost_ratios)*100,1)}%")

st.divider()

# ── Section 6: Intervention Suggestions ───────────────────────────────────────
st.subheader("💡 Portfolio Intervention Suggestions")
st.caption("Strategic recommendations based on current portfolio risk profile.")

high_risk_states = [r["State"] for r in state_rows if "High" in r.get("Risk Level", "")][:3]
high_risk_crops  = [r["Crop"]  for r in crop_rows  if "High" in r.get("Risk Assessment", "")][:3]

st.markdown(f"""
**Based on current portfolio analysis ({n_total} farmers):**

1. **Intercropping promotion** — High-risk zones ({', '.join(high_risk_states) if high_risk_states else 'identified states'}) show low income diversification. 
   Intercropping advisory adoption can reduce claim probability by improving net margin buffer.

2. **Cost-reduction advisory** — {risk_segs['high_pct']}% of analyzed farmers have margin below Rs. 5,000/acre. 
   Priority intervention: fertilizer and irrigation cost reduction (largest reducible categories).

3. **Crop-specific risk** — {', '.join(high_risk_crops) if high_risk_crops else 'Selected crops'} show highest risk concentration. 
   Consider adjusted premium pricing or advisory-linked coverage for these crops.

4. **Drip irrigation subsidy linkage** — Farmers using rainfed or borewell irrigation show higher cost pressure. 
   Linking insurance products to drip adoption incentives could reduce risk at the portfolio level.

5. **Pre-season advisory outreach** — Rule-based risk indicator is strongest before sowing. 
   Advisory intervention at farm-details stage reduces input overspend and yield risk.
""")

st.divider()
st.caption(
    f"Data source: **{'Simulated (demo)' if source == 'synthetic' else 'Live app usage'}** | "
    f"Total records: {n_total} | "
    "This is a rule-based risk indicator, not a certified actuarial model. "
    "Verify with licensed actuaries before underwriting decisions."
)
