import streamlit as st
from core.models import FarmInput
from core.crop_data import list_crop_keys, get_crop_display_name

st.set_page_config(page_title="Farm Details | FRO", page_icon="📋", layout="wide")

if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

col_title, col_lang = st.columns([8, 2])
with col_lang:
    choice = st.radio(
        "Language / भाषा",
        ["English", "हिंदी"],
        index=0 if st.session_state["lang"] == "en" else 1,
        horizontal=True,
        key="lang_radio_form",
    )
    st.session_state["lang"] = "en" if choice == "English" else "hi"
lang = st.session_state["lang"]

with col_title:
    if lang == "hi":
        st.title("📋 चरण 2: खेत का विवरण")
        st.caption(
            f"चुना गया स्थान: अक्षांश {st.session_state.get('lat', 'N/A')}, "
            f"देशांतर {st.session_state.get('lng', 'N/A')}"
        )
    else:
        st.title("📋 Step 2: Farm Details")
        st.caption(
            f"Selected location: Lat {st.session_state.get('lat', 'N/A')}, "
            f"Lng {st.session_state.get('lng', 'N/A')}"
        )

if not st.session_state.get("lat"):
    st.error(
        "No location selected. Please go back to Step 1."
        if lang == "en"
        else "कोई स्थान नहीं चुना। कृपया चरण 1 पर वापस जाएं।"
    )
    if st.button("⬅️ Go to Map" if lang == "en" else "⬅️ मानचित्र पर जाएं"):
        st.switch_page("pages/1_Land_Selection.py")
    st.stop()

prev: FarmInput = st.session_state.get("farm_input")


def prev_val(attr, default):
    return getattr(prev, attr, default) if prev else default


crop_keys = list_crop_keys()

if lang == "hi":
    crop_display = [get_crop_display_name(k, "hi") for k in crop_keys]
    crop_label = "फसल चुनें"
else:
    crop_display = [get_crop_display_name(k, "en") for k in crop_keys]
    crop_label = "Select your primary crop"

prev_crop_key = prev_val("crop", crop_keys[0])
prev_crop_idx = crop_keys.index(prev_crop_key) if prev_crop_key in crop_keys else 0

selected_display = st.selectbox(crop_label, crop_display, index=prev_crop_idx)
selected_crop_key = crop_keys[crop_display.index(selected_display)]

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

col1, col2, col3 = st.columns(3)

with col1:
    if lang == "hi":
        acreage = st.number_input(
            "कुल खेत क्षेत्र (एकड़)",
            min_value=0.1, max_value=1000.0,
            value=float(prev_val("acreage", 2.0)), step=0.5,
        )
        state = st.selectbox(
            "राज्य", STATES,
            index=STATES.index(prev_val("state", "Maharashtra"))
            if prev_val("state", "Maharashtra") in STATES else 0,
        )
    else:
        acreage = st.number_input(
            "Total farm area (acres)",
            min_value=0.1, max_value=1000.0,
            value=float(prev_val("acreage", 2.0)), step=0.5,
        )
        state = st.selectbox(
            "State", STATES,
            index=STATES.index(prev_val("state", "Maharashtra"))
            if prev_val("state", "Maharashtra") in STATES else 0,
        )

with col2:
    SEASONS_EN = ["kharif", "rabi", "zaid", "annual"]
    SEASONS_HI = ["खरीफ", "रबी", "जायद", "वार्षिक"]
    seasons_display = SEASONS_HI if lang == "hi" else SEASONS_EN
    prev_season = prev_val("season", "kharif")
    prev_season_idx = SEASONS_EN.index(prev_season) if prev_season in SEASONS_EN else 0

    season_display = st.selectbox(
        "मौसम" if lang == "hi" else "Season",
        seasons_display,
        index=prev_season_idx,
    )
    selected_season = SEASONS_EN[seasons_display.index(season_display)]

    IRR_EN = ["rainfed", "canal", "borewell", "drip"]
    IRR_HI = ["वर्षाश्रित", "नहर", "बोरवेल", "ड्रिप"]
    irr_display = IRR_HI if lang == "hi" else IRR_EN
    prev_irr = prev_val("irrigation_type", "borewell")
    prev_irr_idx = IRR_EN.index(prev_irr) if prev_irr in IRR_EN else 0

    selected_irrigation_display = st.selectbox(
        "सिंचाई प्रकार" if lang == "hi" else "Irrigation type",
        irr_display,
        index=prev_irr_idx,
    )
    selected_irrigation = IRR_EN[irr_display.index(selected_irrigation_display)]

with col3:
    yield_label = (
        "वर्तमान उपज (क्विंटल/एकड़)" if lang == "hi" else "Current yield (quintals/acre)"
    )
    current_yield = st.number_input(
        yield_label,
        min_value=0.1,
        max_value=500.0,
        value=float(prev_val("current_yield_qtl_per_acre", 10.0)),
        step=0.5,
        help=(
            "Your actual farm yield, not the theoretical maximum."
            if lang == "en"
            else "आपकी वास्तविक खेत उपज।"
        ),
    )

with st.expander(
    "⚙️ Override input costs (optional — defaults are crop averages)"
    if lang == "en"
    else "⚙️ इनपुट लागत बदलें (वैकल्पिक — डिफ़ॉल्ट फसल औसत हैं)"
):
    st.caption(
        "Leave as 0 to use crop-average defaults. Enter your actual per-acre cost to get a more accurate result."
        if lang == "en"
        else "0 छोड़ें — फसल औसत उपयोग होगा। सटीक परिणाम के लिए अपनी प्रति एकड़ लागत दर्ज करें।"
    )
    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        seed_cost = st.number_input("Seed cost / बीज लागत (Rs./acre)", min_value=0, value=0, step=100)
        fertilizer_cost = st.number_input("Fertilizer / उर्वरक (Rs./acre)", min_value=0, value=0, step=100)
    with oc2:
        pesticide_cost = st.number_input("Pesticide / कीटनाशक (Rs./acre)", min_value=0, value=0, step=100)
        labour_cost = st.number_input("Labour / श्रम (Rs./acre)", min_value=0, value=0, step=100)
    with oc3:
        irrigation_cost = st.number_input("Irrigation / सिंचाई (Rs./acre)", min_value=0, value=0, step=100)
        other_cost = st.number_input("Other / अन्य (Rs./acre)", min_value=0, value=0, step=100)


def zero_to_none(v):
    return None if v == 0 else float(v)


st.divider()
col_back, col_submit = st.columns(2)
with col_back:
    if st.button("⬅️ Back to Map" if lang == "en" else "⬅️ मानचित्र पर वापस"):
        st.switch_page("pages/1_Land_Selection.py")

with col_submit:
    if st.button(
        "Calculate Recommendations ➡️" if lang == "en" else "सिफारिशें देखें ➡️",
        type="primary",
    ):
        farm_input = FarmInput(
            crop=selected_crop_key,
            acreage=acreage,
            current_yield_qtl_per_acre=current_yield,
            irrigation_type=selected_irrigation,
            state=state,
            season=selected_season,
            lat=st.session_state.get("lat"),
            lng=st.session_state.get("lng"),
            seed_cost=zero_to_none(seed_cost),
            fertilizer_cost=zero_to_none(fertilizer_cost),
            pesticide_cost=zero_to_none(pesticide_cost),
            labour_cost=zero_to_none(labour_cost),
            irrigation_cost=zero_to_none(irrigation_cost),
            other_cost=zero_to_none(other_cost),
        )
        st.session_state["farm_input"] = farm_input
        st.switch_page("pages/3_Recommendations.py")
