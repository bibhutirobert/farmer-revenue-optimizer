"""
Page 3 — Recommendations (V4)
Fixes: session_state LLM caching, Noto font check, markdown stripping for PDF.
"""
import streamlit as st
import pandas as pd
from core.recommendation_engine import run
from core.models import RecommendationResult, FarmInput
from core.llm_service import enrich_advisory, is_llm_available
from core.logger import log_recommendation_event
from core.price_service import get_price_label
from utils.pdf_utils import build_pdf_bytes

st.set_page_config(page_title="Recommendations | FRO", page_icon="📊", layout="wide")

if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

col_title, col_lang = st.columns([8, 2])
with col_lang:
    choice = st.radio("Language / भाषा", ["English", "हिंदी"],
                      index=0 if st.session_state["lang"] == "en" else 1,
                      horizontal=True, key="lang_radio_rec")
    st.session_state["lang"] = "en" if choice == "English" else "hi"
lang = st.session_state["lang"]

farm_input: FarmInput = st.session_state.get("farm_input")
if not farm_input:
    st.error("No farm data found. Complete Steps 1 and 2 first." if lang == "en"
             else "खेत डेटा नहीं मिला। पहले चरण 1 और 2 पूरे करें।")
    if st.button("⬅️ Go to Step 1" if lang == "en" else "⬅️ चरण 1 पर जाएं"):
        st.switch_page("pages/1_Land_Selection.py")
    st.stop()


@st.cache_data(show_spinner=False)
def cached_run(crop, acreage, yield_qtl, irrigation, state, season, lat, lng,
               soil_type, soil_name, climate_zone,
               seed_cost, fertilizer_cost, pesticide_cost,
               labour_cost, irrigation_cost, other_cost) -> RecommendationResult:
    fi = FarmInput(
        crop=crop, acreage=acreage, current_yield_qtl_per_acre=yield_qtl,
        irrigation_type=irrigation, state=state, season=season, lat=lat, lng=lng,
        soil_type=soil_type, soil_name=soil_name, climate_zone=climate_zone,
        seed_cost=seed_cost, fertilizer_cost=fertilizer_cost,
        pesticide_cost=pesticide_cost, labour_cost=labour_cost,
        irrigation_cost=irrigation_cost, other_cost=other_cost,
    )
    return run(fi)


with st.spinner("Calculating..." if lang == "en" else "गणना हो रही है..."):
    try:
        result: RecommendationResult = cached_run(
            crop=farm_input.crop, acreage=farm_input.acreage,
            yield_qtl=farm_input.current_yield_qtl_per_acre,
            irrigation=farm_input.irrigation_type, state=farm_input.state,
            season=farm_input.season, lat=farm_input.lat or 0.0,
            lng=farm_input.lng or 0.0,
            soil_type=farm_input.soil_type, soil_name=farm_input.soil_name,
            climate_zone=farm_input.climate_zone,
            seed_cost=farm_input.seed_cost, fertilizer_cost=farm_input.fertilizer_cost,
            pesticide_cost=farm_input.pesticide_cost, labour_cost=farm_input.labour_cost,
            irrigation_cost=farm_input.irrigation_cost, other_cost=farm_input.other_cost,
        )
    except ValueError as e:
        st.error(f"Crop data error: {e}" if lang == "en" else f"फसल डेटा त्रुटि: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error: {e}" if lang == "en" else f"अप्रत्याशित त्रुटि: {e}")
        st.stop()

# ── Log usage event (silent) ──────────────────────────────────────────────────
log_recommendation_event(
    crop=farm_input.crop, state=farm_input.state, season=farm_input.season,
    acreage=farm_input.acreage, gross_revenue=result.gross_revenue,
    total_cost=result.total_cost, net_margin=result.net_margin,
    risk_flag=result.risk_flag, price_source=result.price_source,
    soil_code=result.soil_code, climate_zone=result.climate_zone,
    llm_used=False, irrigation_type=farm_input.irrigation_type,
)

# ── Title ──────────────────────────────────────────────────────────────────────
crop_name   = result.crop_name_hi if lang == "hi" else result.crop_name_en
season_map  = {"kharif": ("Kharif", "खरीफ"), "rabi": ("Rabi", "रबी"),
               "zaid": ("Zaid", "जायद"), "annual": ("Annual", "वार्षिक")}
season_label = season_map.get(farm_input.season, (farm_input.season,)*2)[0 if lang=="en" else 1]

if lang == "hi":
    st.title(f"📊 {crop_name} — सिफारिश रिपोर्ट")
    st.caption(f"{result.acreage:.1f} एकड़ | {farm_input.state} | {season_label}")
    if result.soil_name_en:
        st.caption(f"मिट्टी: {result.soil_name_en} | जलवायु: {result.climate_zone}")
else:
    st.title(f"📊 {crop_name} — Advisory Report")
    st.caption(f"{result.acreage:.1f} acres | {farm_input.state} | {season_label}")
    if result.soil_name_en:
        st.caption(f"Soil: {result.soil_name_en} | Climate: {result.climate_zone}")

# ── Risk banner ────────────────────────────────────────────────────────────────
if result.risk_flag:
    st.error("⚠️ **Warning:** Net margin below Rs. 5,000/acre. Apply cost-reduction tips urgently."
             if lang == "en"
             else "⚠️ **चेतावनी:** शुद्ध मार्जिन Rs. 5,000/एकड़ से कम। तत्काल सुझाव लागू करें।")
else:
    st.success("✅ Margin looks healthy. Suggestions below can make it stronger."
               if lang == "en"
               else "✅ मार्जिन स्वस्थ दिखता है। नीचे दिए सुझाव इसे और बेहतर बना सकते हैं।")

st.info(result.narrative_hi if lang == "hi" else result.narrative_en)

# ── KPIs ───────────────────────────────────────────────────────────────────────
st.divider()
kc1, kc2, kc3, kc4 = st.columns(4)
kc1.metric("Gross Revenue" if lang=="en" else "सकल आय",    f"Rs.{result.gross_revenue:,}")
kc2.metric("Total Cost"    if lang=="en" else "कुल लागत",   f"Rs.{result.total_cost:,}")
kc3.metric("Net Margin"    if lang=="en" else "शुद्ध लाभ",  f"Rs.{result.net_margin:,}")
kc4.metric("Potential Savings" if lang=="en" else "संभावित बचत",
           f"Rs.{result.total_reducible_cost:,}",
           delta="Apply all tips" if lang=="en" else "सभी सुझाव अपनाएं")

# Price provenance
price_label = get_price_label(result.price_source, result.price_updated_at, lang)
price_type_label = {"msp":"MSP 2023-24","frp":"FRP 2023-24","market":"Market Avg","default":"Reference"}.get(result.price_type, result.price_type.upper())
st.caption(f"Price basis: Rs.{result.price_per_quintal:,}/quintal ({price_type_label}) — {price_label}"
           if lang == "en"
           else f"मूल्य आधार: Rs.{result.price_per_quintal:,}/क्विंटल ({price_type_label}) — {price_label}")

# ── Cost breakdown ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("💰 Cost Breakdown" if lang=="en" else "💰 लागत विश्लेषण")
rows = []
for item in result.cost_items:
    rows.append({
        ("Category" if lang=="en" else "श्रेणी"):          item.name_en if lang=="en" else item.name_hi,
        ("Total (Rs.)" if lang=="en" else "कुल (Rs.)"):    f"Rs.{item.amount:,}",
        ("Save up to" if lang=="en" else "बचत संभव"):     f"Rs.{item.reducible_by:,}",
        ("How to reduce" if lang=="en" else "कैसे बचाएं"): item.reduction_tip_en if lang=="en" else item.reduction_tip_hi,
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

col_t1, col_t2, col_t3 = st.columns(3)
col_t1.metric("Total Cost" if lang=="en" else "कुल लागत",         f"Rs.{result.total_cost:,}")
col_t2.metric("Total Savings Possible" if lang=="en" else "संभावित बचत", f"Rs.{result.total_reducible_cost:,}")
col_t3.metric("Optimised Margin" if lang=="en" else "अनुकूलित लाभ",
              f"Rs.{result.net_margin + result.total_reducible_cost:,}")

# ── Low-cost tips ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("🌿 Low-Cost & Ancient Techniques" if lang=="en" else "🌿 कम लागत और प्राचीन तकनीकें")
for tip in (result.low_cost_tips_hi if lang=="hi" else result.low_cost_tips_en):
    st.markdown(f"- {tip}")

# ── Intercropping ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("🌱 Intercropping Opportunities" if lang=="en" else "🌱 अंतरफसल सुझाव")
if result.intercrop_suggestions:
    for sugg in result.intercrop_suggestions:
        name    = sugg.companion_name_hi if lang=="hi" else sugg.companion_name_en
        benefit = sugg.benefit_hi if lang=="hi" else sugg.benefit_en
        with st.expander(f"🌿 {name} — +{sugg.revenue_uplift_percent:.0f}% {'revenue uplift' if lang=='en' else 'राजस्व वृद्धि'}"):
            st.markdown(benefit)
            st.caption(f"{'Row ratio' if lang=='en' else 'पंक्ति अनुपात'}: {sugg.row_ratio}")
else:
    st.info("No intercropping rules for this combination." if lang=="en"
            else "इस संयोजन के लिए अंतरफसल नियम नहीं।")

# ── Seasonal tips ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("📅 Seasonal Tips" if lang=="en" else "📅 मौसमी सुझाव")
for tip in (result.seasonal_tips_hi if lang=="hi" else result.seasonal_tips_en):
    st.markdown(f"- {tip}")

# ── Vertical farming ───────────────────────────────────────────────────────────
st.divider()
st.subheader("🏗️ Vertical Farming & Value Addition" if lang=="en" else "🏗️ ऊर्ध्वाधर खेती / मूल्य संवर्धन")
st.markdown(result.vertical_farming_hi if lang=="hi" else result.vertical_farming_en)

# ── LLM Advisory (V4 — cached, markdown-stripped for PDF) ─────────────────────
import os, re

def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so PDF renders clean plain text."""
    if not text:
        return text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)   # **bold**
    text = re.sub(r'\*(.+?)\*', r'\1', text)         # *italic*
    text = re.sub(r'__(.+?)__', r'\1', text)         # __bold__
    text = re.sub(r'_(.+?)_', r'\1', text)           # _italic_
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # headings
    text = re.sub(r'^\s*[-*]\s+', '- ', text, flags=re.MULTILINE)  # normalise bullets
    text = re.sub(r'^\s*\d+\.\s+', lambda m: m.group().strip() + ' ', text, flags=re.MULTILINE)
    return text.strip()


def _check_hindi_font() -> bool:
    """Check if Noto Sans Devanagari font is available for Hindi PDF."""
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
    return os.path.exists(os.path.join(fonts_dir, "NotoSansDevanagari-Regular.ttf"))


# Generate advisory ONCE and cache in session_state (survives language toggles)
_cache_key = f"llm_cache_{farm_input.crop}_{farm_input.acreage}_{farm_input.state}"
if _cache_key not in st.session_state:
    st.session_state[_cache_key] = {"en": "", "hi": "", "done": False}

_llm_cache = st.session_state[_cache_key]

st.divider()
if is_llm_available():
    st.subheader("🤖 AI-Powered Additional Advisory" if lang=="en"
                 else "🤖 AI-संचालित अतिरिक्त सलाह")
    st.caption(
        "Powered by OpenAI GPT. Based on your computed farm data — not generic advice. "
        "Included in the PDF download below."
        if lang=="en"
        else "OpenAI GPT द्वारा संचालित। आपके गणना किए गए खेत डेटा पर आधारित। "
             "नीचे PDF डाउनलोड में शामिल।"
    )

    # Only call OpenAI if we haven't already for this farm run
    if not _llm_cache["done"]:
        with st.spinner("Generating AI advisory..." if lang=="en"
                        else "AI सलाह तैयार हो रही है..."):
            _llm_cache["en"] = enrich_advisory(
                result=result,
                soil_name=result.soil_name_en or "Alluvial",
                climate_zone=result.climate_zone or "Tropical",
                state=farm_input.state,
                lang="en",
            ) or ""

            if _check_hindi_font():
                _llm_cache["hi"] = enrich_advisory(
                    result=result,
                    soil_name=result.soil_name_en or "Alluvial",
                    climate_zone=result.climate_zone or "Tropical",
                    state=farm_input.state,
                    lang="hi",
                ) or ""

            _llm_cache["done"] = True

    # Read from cache (stable across toggles)
    llm_advisory_en = _llm_cache["en"]
    llm_advisory_hi = _llm_cache["hi"]

    # Display in UI (markdown renders fine on screen)
    llm_ui_output = llm_advisory_hi if lang == "hi" and llm_advisory_hi else llm_advisory_en
    if llm_ui_output:
        st.markdown(llm_ui_output)
        log_recommendation_event(
            crop=farm_input.crop, state=farm_input.state, season=farm_input.season,
            acreage=farm_input.acreage, gross_revenue=result.gross_revenue,
            total_cost=result.total_cost, net_margin=result.net_margin,
            risk_flag=result.risk_flag, price_source=result.price_source,
            soil_code=result.soil_code, climate_zone=result.climate_zone,
            llm_used=True, irrigation_type=farm_input.irrigation_type,
        )
    else:
        st.info(
            "AI advisory temporarily unavailable. Engine recommendations above are complete."
            if lang=="en"
            else "AI सलाह अस्थायी रूप से अनुपलब्ध। ऊपर दी इंजन सिफारिशें पूर्ण हैं।"
        )
else:
    llm_advisory_en = ""
    llm_advisory_hi = ""

# ── PDF Download ───────────────────────────────────────────────────────────────
st.divider()
st.subheader("📄 Download Report" if lang=="en" else "📄 रिपोर्ट डाउनलोड करें")
if llm_advisory_en:
    st.caption(
        "AI advisory is included in the PDF below."
        if lang=="en"
        else "AI सलाह नीचे PDF में शामिल है।"
    )
farm_location = f"Lat {farm_input.lat:.4f}, Lng {farm_input.lng:.4f}" if farm_input.lat else ""

with st.spinner("Generating PDF..." if lang=="en" else "PDF तैयार हो रही है..."):
    try:
        pdf_bytes = build_pdf_bytes(
            result,
            farm_location=farm_location,
            llm_advisory_en=_strip_markdown(llm_advisory_en),
            llm_advisory_hi=_strip_markdown(llm_advisory_hi),
        )
    except Exception as e:
        st.error(f"PDF generation failed: {e}" if lang=="en" else f"PDF निर्माण विफल: {e}")
        pdf_bytes = None

if pdf_bytes:
    st.download_button(
        label="⬇️ Download PDF Report (English + Hindi)" if lang=="en"
              else "⬇️ PDF रिपोर्ट डाउनलोड करें (अंग्रेज़ी + हिंदी)",
        data=pdf_bytes,
        file_name=f"farm_report_{farm_input.crop}_{farm_input.acreage:.1f}acres.pdf",
        mime="application/pdf", type="primary",
    )

# ── Navigation ─────────────────────────────────────────────────────────────────
st.divider()
col_b1, col_b2 = st.columns(2)
with col_b1:
    if st.button("⬅️ Edit Details" if lang=="en" else "⬅️ विवरण संपादित करें"):
        st.switch_page("pages/2_Farm_Details.py")
with col_b2:
    if st.button("🏠 Start Over" if lang=="en" else "🏠 फिर से शुरू करें"):
        for key in ["lat","lng","polygon","farm_input","detected_state",
                    "detected_soil_code","detected_soil_name","detected_climate","detected_sc_data"]:
            st.session_state.pop(key, None)
        st.switch_page("app.py")
