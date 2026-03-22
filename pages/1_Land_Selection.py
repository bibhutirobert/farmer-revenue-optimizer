import streamlit as st
from streamlit_folium import st_folium
from utils.map_utils import (
    make_selection_map,
    extract_lat_lng,
    extract_polygon_coords,
    validate_india_bounds,
)
from core.scene_provider import default_scene_provider

st.set_page_config(
    page_title="Land Selection | FRO",
    page_icon="🗺️",
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
        key="lang_radio_map",
    )
    st.session_state["lang"] = "en" if choice == "English" else "hi"
lang = st.session_state["lang"]

with col_title:
    if lang == "hi":
        st.title("🗺️ चरण 1: अपना खेत चुनें")
        st.caption(
            "उपग्रह मानचित्र पर अपने खेत के केंद्र पर **क्लिक करें**, "
            "या बाईं ओर के टूल से **बहुभुज बनाएं**।"
        )
    else:
        st.title("🗺️ Step 1: Select Your Field")
        st.caption(
            "**Click** anywhere on your field on the satellite map, "
            "or use the draw tools (left side of map) to outline your field boundary."
        )

with st.expander(
    "ℹ️ How to use the map" if lang == "en" else "ℹ️ मानचित्र का उपयोग कैसे करें",
    expanded=False,
):
    if lang == "hi":
        st.markdown(
            """
            1. मानचित्र पर **स्क्रॉल** करके अपने गाँव/जिले तक जाएं
            2. अपने खेत के केंद्र पर **क्लिक** करें (सबसे आसान तरीका)
            3. **या** बाईं ओर पॉलीगन टूल से खेत की सीमा बनाएं
            4. **Satellite** और **Street Map** के बीच ऊपर-दाईं ओर स्विच करें
            5. हरे रंग का ✅ संदेश दिखने पर **अगले चरण** पर जाएं
            """
        )
    else:
        st.markdown(
            """
            1. **Scroll** on the map to navigate to your village / district
            2. **Click** on the centre of your field — easiest method
            3. **Or** use the polygon tool on the left side to trace your field boundary
            4. Toggle between **Satellite** and **Street Map** using the layer control (top right of map)
            5. Once you see the green ✅ confirmation, click **Next** below
            """
        )

existing_lat = st.session_state.get("lat")
existing_lng = st.session_state.get("lng")
map_center = [existing_lat, existing_lng] if existing_lat and existing_lng else None
zoom_level = 14 if map_center else 5

folium_map = make_selection_map(center=map_center, zoom=zoom_level)

try:
    map_result = st_folium(
        folium_map,
        use_container_width=True,
        height=520,
        returned_objects=["last_clicked", "all_drawings"],
        key="folium_map_v1",
    )
except Exception as e:
    st.error(
        f"Map failed to load: {e}\n\nTry refreshing the page. If the problem persists, check your internet connection."
        if lang == "en"
        else f"मानचित्र लोड नहीं हो सका: {e}\n\nपृष्ठ ताज़ा करें।"
    )
    map_result = None

lat, lng = extract_lat_lng(map_result)
polygon = extract_polygon_coords(map_result)

if lat is not None and lng is not None:
    if validate_india_bounds(lat, lng):
        st.session_state["lat"] = lat
        st.session_state["lng"] = lng
        st.session_state["polygon"] = polygon
        if lang == "hi":
            st.success(f"✅ स्थान चुना गया — अक्षांश: **{lat:.5f}**, देशांतर: **{lng:.5f}**")
            if polygon:
                st.info(f"📐 बहुभुज भी रिकॉर्ड किया ({len(polygon)} कोने)।")
        else:
            st.success(f"✅ Location selected — Lat: **{lat:.5f}**, Lng: **{lng:.5f}**")
            if polygon:
                st.info(f"📐 Field boundary recorded ({len(polygon)} vertices).")
    else:
        st.warning(
            f"⚠️ Selected coordinates ({lat:.3f}, {lng:.3f}) appear to be outside India. "
            "Please click within India on the map."
            if lang == "en"
            else f"⚠️ चुने गए निर्देशांक ({lat:.3f}, {lng:.3f}) भारत के बाहर हैं। कृपया भारत के अंदर क्लिक करें।"
        )
else:
    stored_lat = st.session_state.get("lat")
    stored_lng = st.session_state.get("lng")
    if stored_lat and stored_lng:
        if lang == "hi":
            st.info(
                f"📍 पहले से चुना गया स्थान: **{stored_lat:.5f}**, **{stored_lng:.5f}** "
                "— नया स्थान चुनने के लिए मानचित्र पर क्लिक करें।"
            )
        else:
            st.info(
                f"📍 Previously selected: **{stored_lat:.5f}**, **{stored_lng:.5f}** "
                "— click the map to change it."
            )
    else:
        if lang == "hi":
            st.warning("👆 ऊपर मानचित्र पर क्लिक करें या बहुभुज बनाएं।")
        else:
            st.warning("👆 Click anywhere on the map above, or draw a polygon around your field.")

with st.expander(
    "🛰️ 3D View (Future Feature — Skyfall-GS)" if lang == "en"
    else "🛰️ 3D दृश्य (भविष्य की सुविधा — Skyfall-GS)"
):
    if st.session_state.get("lat"):
        default_scene_provider.render(
            st,
            lat=st.session_state["lat"],
            lng=st.session_state["lng"],
        )
    else:
        st.write(
            "Select a location first to preview the 3D integration point."
            if lang == "en"
            else "3D पूर्वावलोकन के लिए पहले कोई स्थान चुनें।"
        )

st.divider()
col_back, col_next = st.columns(2)
with col_back:
    if st.button("⬅️ Home" if lang == "en" else "⬅️ होम"):
        st.switch_page("app.py")

with col_next:
    has_location = bool(st.session_state.get("lat") and st.session_state.get("lng"))
    next_label = (
        "Next: Enter Farm Details ➡️" if lang == "en" else "अगला: खेत विवरण दर्ज करें ➡️"
    )
    if st.button(next_label, type="primary", disabled=not has_location):
        st.switch_page("pages/2_Farm_Details.py")
    if not has_location:
        st.caption(
            "Please select a location on the map first."
            if lang == "en"
            else "कृपया पहले मानचित्र पर स्थान चुनें।"
        )
