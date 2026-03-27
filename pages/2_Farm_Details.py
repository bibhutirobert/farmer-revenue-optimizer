"""
Page 2 — Farm Details Form (V3)
Pre-fills state, soil type, climate zone, and ranked crops from
geo-intelligence pipeline (session_state from Page 1).
"""
import streamlit as st
from core.models import FarmInput
from core.crop_data import list_crop_keys, get_crop_display_name
from core.soil_service import get_ranked_crops

st.set_page_config(page_title="Farm Details | FRO", page_icon="📋", layout="wide")

if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

col_title, col_lang = st.columns([8, 2])
with col_lang:
    choice = st.radio("Language / भाषा", ["English", "हिंदी"],
                      index=0 if st.session_state["lang"] == "en" else 1,
                      horizontal=True, key="lang_radio_form")
    st.session_state["lang"] = "en" if choice == "English" else "hi"
lang = st.session_state["lang"]

with col_title:
    if lang == "hi":
        st.title("📋 चरण 2: खेत का विवरण")
        lat_disp = st.session_state.get("lat", "N/A")
        lng_disp = st.session_state.get("lng", "N/A")
        st.caption(f"चुना गया स्थान: अक्षांश {lat_disp}, देशांतर {lng_disp}")
    else:
        st.title("📋 Step 2: Farm Details")
        st.caption(f"Location: Lat {st.session_state.get('lat', 'N/A')}, Lng {st.session_state.get('lng', 'N/A')}")

if not st.session_state.get("lat"):
    st.error("No location selected. Please go back to Step 1." if lang == "en"
             else "कोई स्थान नहीं चुना। कृपया चरण 1 पर वापस जाएं।")
    if st.button("⬅️ Go to Map" if lang == "en" else "⬅️ मानचित्र पर जाएं"):
        st.switch_page("pages/1_Land_Selection.py")
    st.stop()

# ── Geo-intelligence pre-fill banner ──────────────────────────────────────────
detected_state = st.session_state.get("detected_state")
detected_soil  = st.session_state.get("detected_soil_name", "")
detected_clim  = st.session_state.get("detected_climate", "")
soil_code      = st.session_state.get("detected_soil_code", "")

if detected_state:
    if lang == "hi":
        st.success(
            f"🌍 **स्वतः पहचाना गया** — राज्य: **{detected_state}** | "
            f"मिट्टी: **{detected_soil}** | जलवायु: **{detected_clim}**\n\n"
            "नीचे दिए विवरण स्वतः भरे गए हैं। जरूरत हो तो बदल सकते हैं।"
        )
    else:
        st.success(
            f"🌍 **Auto-detected from your location** — State: **{detected_state}** | "
            f"Soil: **{detected_soil}** | Climate: **{detected_clim}**\n\n"
            "Form pre-filled below. Override anything if needed."
        )

# ── Previous values helper ─────────────────────────────────────────────────────
prev: FarmInput = st.session_state.get("farm_input")

def prev_val(attr, default):
    return getattr(prev, attr, default) if prev else default

# ── Crop keys and display ──────────────────────────────────────────────────────
crop_keys = list_crop_keys()

# Auto-ranked crops based on soil + season
SEASONS_EN = ["kharif", "rabi", "zaid", "annual"]
SEASONS_HI = ["खरीफ", "रबी", "जायद", "वार्षिक"]
seasons_display = SEASONS_HI if lang == "hi" else SEASONS_EN
prev_season    = prev_val("season", "kharif")
prev_season_idx = SEASONS_EN.index(prev_season) if prev_season in SEASONS_EN else 0

# Season selection first (needed for ranked crops)
col_s1, col_s2 = st.columns(2)
with col_s1:
    season_display = st.selectbox("मौसम" if lang == "hi" else "Season",
                                  seasons_display, index=prev_season_idx)
    selected_season = SEASONS_EN[seasons_display.index(season_display)]

with col_s2:
    IRR_EN = ["rainfed", "canal", "borewell", "drip"]
    IRR_HI = ["वर्षाश्रित", "नहर", "बोरवेल", "ड्रिप"]
    irr_display = IRR_HI if lang == "hi" else IRR_EN
    prev_irr = prev_val("irrigation_type", "borewell")
    prev_irr_idx = IRR_EN.index(prev_irr) if prev_irr in IRR_EN else 0
    sel_irr_disp = st.selectbox("सिंचाई प्रकार" if lang == "hi" else "Irrigation type",
                                 irr_display, index=prev_irr_idx)
    selected_irrigation = IRR_EN[irr_display.index(sel_irr_disp)]

# Compute ranked crops from geo-intelligence
ranked_crops = []
if soil_code and detected_state:
    ranked_crops = get_ranked_crops(soil_code, selected_season, detected_clim, detected_state)

# Build crop display list with ranked crops first
if ranked_crops:
    other_keys = [k for k in crop_keys if k not in ranked_crops]
    ordered_keys = ranked_crops + other_keys
else:
    ordered_keys = crop_keys

if lang == "hi":
    crop_display = [get_crop_display_name(k, "hi") for k in ordered_keys]
    crop_label   = "फसल चुनें (मिट्टी के अनुसार क्रमबद्ध)" if ranked_crops else "फसल चुनें"
else:
    crop_display = [get_crop_display_name(k, "en") for k in ordered_keys]
    crop_label   = "Select crop (ranked by soil suitability)" if ranked_crops else "Select your primary crop"

prev_crop_key = prev_val("crop", ordered_keys[0])
prev_crop_idx = ordered_keys.index(prev_crop_key) if prev_crop_key in ordered_keys else 0

selected_display  = st.selectbox(crop_label, crop_display, index=prev_crop_idx)
selected_crop_key = ordered_keys[crop_display.index(selected_display)]

# Show top-3 soil-matched recommendations as a hint
if ranked_crops and lang == "en":
    top3_names = [get_crop_display_name(k, "en") for k in ranked_crops]
    st.caption(f"Best suited for your soil: {', '.join(top3_names)}")
elif ranked_crops and lang == "hi":
    top3_names = [get_crop_display_name(k, "hi") for k in ranked_crops]
    st.caption(f"आपकी मिट्टी के लिए सर्वोत्तम: {', '.join(top3_names)}")

# ── State, acreage, yield ──────────────────────────────────────────────────────
STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

# Use detected state as default if available
default_state = detected_state if detected_state and detected_state in STATES \
                else prev_val("state", "Maharashtra")
default_state_idx = STATES.index(default_state) if default_state in STATES else 0

col1, col2, col3 = st.columns(3)
with col1:
    state = st.selectbox("राज्य" if lang == "hi" else "State",
                         STATES, index=default_state_idx)
    acreage = st.number_input(
        "कुल खेत क्षेत्र (एकड़)" if lang == "hi" else "Total farm area (acres)",
        min_value=0.1, max_value=1000.0,
        value=float(prev_val("acreage", 2.0)), step=0.5)

with col2:
    current_yield = st.number_input(
        "वर्तमान उपज (क्विंटल/एकड़)" if lang == "hi" else "Current yield (quintals/acre)",
        min_value=0.1, max_value=500.0,
        value=float(prev_val("current_yield_qtl_per_acre", 10.0)), step=0.5)

with col3:
    if detected_soil and lang == "en":
        st.metric("Detected Soil Type", detected_soil)
        st.metric("Climate Zone", detected_clim or "—")
    elif detected_soil and lang == "hi":
        st.metric("पहचानी गई मिट्टी", detected_soil)
        st.metric("जलवायु क्षेत्र", detected_clim or "—")

# ── Optional cost overrides ────────────────────────────────────────────────────
with st.expander("⚙️ Override input costs (optional)" if lang == "en"
                 else "⚙️ इनपुट लागत बदलें (वैकल्पिक)"):
    st.caption("Leave as 0 to use crop-average defaults." if lang == "en"
               else "0 छोड़ें — फसल औसत उपयोग होगा।")
    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        seed_cost        = st.number_input("Seed / बीज (Rs./acre)",        min_value=0, value=0, step=100)
        fertilizer_cost  = st.number_input("Fertilizer / उर्वरक (Rs./acre)", min_value=0, value=0, step=100)
    with oc2:
        pesticide_cost   = st.number_input("Pesticide / कीटनाशक (Rs./acre)", min_value=0, value=0, step=100)
        labour_cost      = st.number_input("Labour / श्रम (Rs./acre)",        min_value=0, value=0, step=100)
    with oc3:
        irrigation_cost  = st.number_input("Irrigation / सिंचाई (Rs./acre)", min_value=0, value=0, step=100)
        other_cost       = st.number_input("Other / अन्य (Rs./acre)",         min_value=0, value=0, step=100)

def zero_to_none(v):
    return None if v == 0 else float(v)

# ── Submit ─────────────────────────────────────────────────────────────────────
st.divider()
col_back, col_submit = st.columns(2)
with col_back:
    if st.button("⬅️ Back to Map" if lang == "en" else "⬅️ मानचित्र पर वापस"):
        st.switch_page("pages/1_Land_Selection.py")
with col_submit:
    if st.button("Calculate Recommendations ➡️" if lang == "en" else "सिफारिशें देखें ➡️",
                 type="primary"):
        farm_input = FarmInput(
            crop=selected_crop_key,
            acreage=acreage,
            current_yield_qtl_per_acre=current_yield,
            irrigation_type=selected_irrigation,
            state=state,
            season=selected_season,
            lat=st.session_state.get("lat"),
            lng=st.session_state.get("lng"),
            soil_type=soil_code or None,
            soil_name=detected_soil or None,
            climate_zone=detected_clim or None,
            seed_cost=zero_to_none(seed_cost),
            fertilizer_cost=zero_to_none(fertilizer_cost),
            pesticide_cost=zero_to_none(pesticide_cost),
            labour_cost=zero_to_none(labour_cost),
            irrigation_cost=zero_to_none(irrigation_cost),
            other_cost=zero_to_none(other_cost),
        )
        st.session_state["farm_input"] = farm_input
        st.switch_page("pages/3_Recommendations.py")
