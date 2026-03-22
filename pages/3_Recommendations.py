import streamlit as st
import pandas as pd
from core.recommendation_engine import run
from core.models import RecommendationResult, FarmInput
from utils.pdf_utils import build_pdf_bytes

st.set_page_config(
    page_title="Recommendations | FRO",
    page_icon="📊",
    layout="wide",
)

if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

col_title, col_lang = st.columns([8, 2])
with col_lang:
    choice = st.radio(
        "Language / भाषा",
        ["English", "हिंदी"],
        index=0 if st.session_state["lang"] == "en" else 1,
        horizontal=True,
        key="lang_radio_rec",
    )
    st.session_state["lang"] = "en" if choice == "English" else "hi"
lang = st.session_state["lang"]

farm_input: FarmInput = st.session_state.get("farm_input")
if not farm_input:
    st.error(
        "⚠️ No farm data found. Please complete Steps 1 and 2 first."
        if lang == "en"
        else "⚠️ कोई खेत डेटा नहीं। कृपया पहले चरण 1 और 2 पूरे करें।"
    )
    if st.button("⬅️ Go to Step 1" if lang == "en" else "⬅️ चरण 1 पर जाएं"):
        st.switch_page("pages/1_Land_Selection.py")
    st.stop()


@st.cache_data(show_spinner=False)
def cached_run(
    crop, acreage, yield_qtl, irrigation, state, season,
    lat, lng, seed_cost, fertilizer_cost, pesticide_cost,
    labour_cost, irrigation_cost, other_cost,
) -> RecommendationResult:
    fi = FarmInput(
        crop=crop,
        acreage=acreage,
        current_yield_qtl_per_acre=yield_qtl,
        irrigation_type=irrigation,
        state=state,
        season=season,
        lat=lat,
        lng=lng,
        seed_cost=seed_cost,
        fertilizer_cost=fertilizer_cost,
        pesticide_cost=pesticide_cost,
        labour_cost=labour_cost,
        irrigation_cost=irrigation_cost,
        other_cost=other_cost,
    )
    return run(fi)


with st.spinner(
    "Calculating recommendations..." if lang == "en" else "सिफारिशें तैयार हो रही हैं..."
):
    try:
        result: RecommendationResult = cached_run(
            crop=farm_input.crop,
            acreage=farm_input.acreage,
            yield_qtl=farm_input.current_yield_qtl_per_acre,
            irrigation=farm_input.irrigation_type,
            state=farm_input.state,
            season=farm_input.season,
            lat=farm_input.lat or 0.0,
            lng=farm_input.lng or 0.0,
            seed_cost=farm_input.seed_cost,
            fertilizer_cost=farm_input.fertilizer_cost,
            pesticide_cost=farm_input.pesticide_cost,
            labour_cost=farm_input.labour_cost,
            irrigation_cost=farm_input.irrigation_cost,
            other_cost=farm_input.other_cost,
        )
    except ValueError as e:
        st.error(
            f"Crop data error: {e}. Please go back and select a valid crop."
            if lang == "en"
            else f"फसल डेटा त्रुटि: {e}। वापस जाएं और सही फसल चुनें।"
        )
        if st.button("⬅️ Edit Details" if lang == "en" else "⬅️ विवरण संपादित करें"):
            st.switch_page("pages/2_Farm_Details.py")
        st.stop()
    except Exception as e:
        st.error(
            f"Unexpected error: {e}. Please try again."
            if lang == "en"
            else f"अप्रत्याशित त्रुटि: {e}। कृपया पुनः प्रयास करें।"
        )
        st.stop()

crop_name = result.crop_name_hi if lang == "hi" else result.crop_name_en
season_label = {
    "kharif": "खरीफ" if lang == "hi" else "Kharif",
    "rabi":   "रबी"  if lang == "hi" else "Rabi",
    "zaid":   "जायद" if lang == "hi" else "Zaid",
    "annual": "वार्षिक" if lang == "hi" else "Annual",
}.get(farm_input.season, farm_input.season.title())

if lang == "hi":
    st.title(f"📊 {crop_name} — सिफारिश रिपोर्ट")
    st.caption(f"{result.acreage:.1f} एकड़ | {farm_input.state} | {season_label} मौसम")
else:
    st.title(f"📊 {crop_name} — Advisory Report")
    st.caption(f"{result.acreage:.1f} acres | {farm_input.state} | {season_label} season")

if result.risk_flag:
    if lang == "hi":
        st.error(
            "⚠️ **चेतावनी:** आपका शुद्ध मार्जिन Rs. 5,000/एकड़ से कम है। "
            "नीचे दिए लागत-कटौती और अंतरफसल सुझाव तत्काल लागू करें।"
        )
    else:
        st.error(
            "⚠️ **Warning:** Net margin is below Rs. 5,000/acre. "
            "Apply the cost-reduction and intercropping suggestions below urgently."
        )
else:
    if lang == "hi":
        st.success("✅ आपका मार्जिन स्वस्थ दिखता है। नीचे दिए सुझाव इसे और बेहतर बना सकते हैं।")
    else:
        st.success("✅ Your margin looks healthy. The suggestions below can make it even stronger.")

narrative = result.narrative_hi if lang == "hi" else result.narrative_en
st.info(narrative)

st.divider()
kc1, kc2, kc3, kc4 = st.columns(4)
kc1.metric("Gross Revenue" if lang == "en" else "सकल आय", f"Rs.{result.gross_revenue:,}")
kc2.metric("Total Cost" if lang == "en" else "कुल लागत", f"Rs.{result.total_cost:,}")
kc3.metric("Net Margin" if lang == "en" else "शुद्ध लाभ", f"Rs.{result.net_margin:,}")
kc4.metric(
    "Potential Savings" if lang == "en" else "संभावित बचत",
    f"Rs.{result.total_reducible_cost:,}",
    delta="Apply all tips" if lang == "en" else "सभी सुझाव अपनाएं",
)

price_label = {"msp": "MSP 2023-24", "frp": "FRP 2023-24", "market": "Market Avg"}.get(
    result.price_type, result.price_type.upper()
)
if lang == "hi":
    st.caption(f"मूल्य आधार: Rs.{result.price_per_quintal:,}/क्विंटल ({price_label})")
    if result.price_type == "market":
        st.caption("⚠️ बाजार भाव अत्यधिक परिवर्तनशील है। यह एक रूढ़िवादी औसत है।")
else:
    st.caption(f"Price basis: Rs.{result.price_per_quintal:,}/quintal ({price_label})")
    if result.price_type == "market":
        st.caption("⚠️ Market prices are highly variable. This is a conservative average.")

st.divider()
st.subheader("💰 Cost Breakdown" if lang == "en" else "💰 लागत विश्लेषण")

cost_rows = []
for item in result.cost_items:
    name = item.name_hi if lang == "hi" else item.name_en
    tip  = item.reduction_tip_hi if lang == "hi" else item.reduction_tip_en
    cost_rows.append({
        ("लागत श्रेणी" if lang == "hi" else "Category"):      name,
        ("कुल (Rs.)"   if lang == "hi" else "Total (Rs.)"):   f"Rs.{item.amount:,}",
        ("बचत संभव"    if lang == "hi" else "Save up to"):    f"Rs.{item.reducible_by:,}",
        ("कैसे बचाएं"  if lang == "hi" else "How to reduce"): tip,
    })

st.dataframe(pd.DataFrame(cost_rows), use_container_width=True, hide_index=True)

col_t1, col_t2, col_t3 = st.columns(3)
col_t1.metric("Total Cost" if lang == "en" else "कुल लागत", f"Rs.{result.total_cost:,}")
col_t2.metric(
    "Total Savings Possible" if lang == "en" else "संभावित बचत",
    f"Rs.{result.total_reducible_cost:,}",
)
optimised = result.net_margin + result.total_reducible_cost
col_t3.metric(
    "Optimised Net Margin" if lang == "en" else "अनुकूलित शुद्ध लाभ",
    f"Rs.{optimised:,}",
)

st.divider()
st.subheader(
    "🌿 Low-Cost & Ancient Farming Techniques"
    if lang == "en"
    else "🌿 कम लागत और प्राचीन तकनीकें"
)
tips = result.low_cost_tips_hi if lang == "hi" else result.low_cost_tips_en
if tips:
    for tip in tips:
        st.markdown(f"- {tip}")
else:
    st.info(
        "No specific tips available for this crop."
        if lang == "en"
        else "इस फसल के लिए विशेष सुझाव उपलब्ध नहीं।"
    )

st.divider()
st.subheader("🌱 Intercropping Opportunities" if lang == "en" else "🌱 अंतरफसल सुझाव")

if result.intercrop_suggestions:
    for sugg in result.intercrop_suggestions:
        name    = sugg.companion_name_hi if lang == "hi" else sugg.companion_name_en
        benefit = sugg.benefit_hi        if lang == "hi" else sugg.benefit_en
        header  = (
            f"🌿 {name} — +{sugg.revenue_uplift_percent:.0f}% revenue uplift"
            if lang == "en"
            else f"🌿 {name} — +{sugg.revenue_uplift_percent:.0f}% राजस्व वृद्धि"
        )
        with st.expander(header):
            st.markdown(benefit)
            st.caption(
                f"Row ratio: {sugg.row_ratio}"
                if lang == "en"
                else f"पंक्ति अनुपात: {sugg.row_ratio}"
            )
else:
    st.info(
        "No intercropping rules found for this crop + season combination. "
        "Try adjusting the season on the previous page."
        if lang == "en"
        else "इस फसल और मौसम के लिए अंतरफसल नियम नहीं मिले। मौसम बदलकर देखें।"
    )

st.divider()
st.subheader("📅 Seasonal Planting Tips" if lang == "en" else "📅 मौसम-वार रोपण सुझाव")
s_tips = result.seasonal_tips_hi if lang == "hi" else result.seasonal_tips_en
for tip in s_tips:
    st.markdown(f"- {tip}")

st.divider()
st.subheader(
    "🏗️ Vertical Farming & Value Addition"
    if lang == "en"
    else "🏗️ ऊर्ध्वाधर खेती / मूल्य संवर्धन"
)
st.markdown(result.vertical_farming_hi if lang == "hi" else result.vertical_farming_en)

st.divider()
st.subheader("📄 Download Report" if lang == "en" else "📄 रिपोर्ट डाउनलोड करें")
if lang == "hi":
    st.caption(
        "नोट: PDF अंग्रेज़ी में है (हिंदी PDF के लिए Devanagari फ़ॉन्ट फ़ाइल आवश्यक है — भविष्य की सुविधा)।"
    )

farm_location = ""
if farm_input.lat and farm_input.lng:
    farm_location = f"Lat {farm_input.lat:.4f}, Lng {farm_input.lng:.4f}"

with st.spinner("Generating PDF..." if lang == "en" else "PDF तैयार हो रही है..."):
    try:
        pdf_bytes = build_pdf_bytes(result, farm_location)
    except Exception as e:
        st.error(
            f"PDF generation failed: {e}. You can still read the report above."
            if lang == "en"
            else f"PDF निर्माण विफल: {e}। ऊपर रिपोर्ट पढ़ें।"
        )
        pdf_bytes = None

if pdf_bytes:
    st.download_button(
        label="⬇️ Download PDF Report" if lang == "en" else "⬇️ PDF रिपोर्ट डाउनलोड करें",
        data=pdf_bytes,
        file_name=f"farm_report_{farm_input.crop}_{farm_input.acreage:.1f}acres.pdf",
        mime="application/pdf",
        type="primary",
    )

st.divider()
col_b1, col_b2 = st.columns(2)
with col_b1:
    if st.button("⬅️ Edit Farm Details" if lang == "en" else "⬅️ विवरण संपादित करें"):
        st.switch_page("pages/2_Farm_Details.py")
with col_b2:
    if st.button("🏠 Start Over" if lang == "en" else "🏠 फिर से शुरू करें"):
        for key in ["lat", "lng", "polygon", "farm_input"]:
            st.session_state.pop(key, None)
        st.switch_page("app.py")
