"""
Page 1 — Satellite map with search, confirm flow, and auto geo-intelligence.

On confirm:
  1. Reverse geocode → detect state
  2. soil_service → resolve soil type + climate zone
  3. All written to session_state for pre-fill on Page 2
"""

import streamlit as st
from streamlit_folium import st_folium
from utils.map_utils import (
    make_selection_map, extract_lat_lng, extract_polygon_coords,
    validate_india_bounds, geocode_india, reverse_geocode_state,
)
from core.scene_provider import default_scene_provider

st.set_page_config(page_title="Land Selection | FRO", page_icon="🗺️", layout="wide")

if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

col_title, col_lang = st.columns([8, 2])
with col_lang:
    choice = st.radio("Language / भाषा", ["English", "हिंदी"],
                      index=0 if st.session_state["lang"] == "en" else 1,
                      horizontal=True, key="lang_radio_map")
    st.session_state["lang"] = "en" if choice == "English" else "hi"
lang = st.session_state["lang"]

for key in ("lat", "lng", "polygon", "pending_lat", "pending_lng",
            "map_center", "map_zoom", "detected_state",
            "detected_soil_code", "detected_soil_name", "detected_climate"):
    if key not in st.session_state:
        st.session_state[key] = None

with col_title:
    if lang == "hi":
        st.title("🗺️ चरण 1: अपना खेत चुनें")
        st.caption("खोज बॉक्स में पिनकोड / गाँव / जिला टाइप करें, फिर मानचित्र पर अपने खेत पर क्लिक करें।")
    else:
        st.title("🗺️ Step 1: Select Your Field")
        st.caption("Search by pincode, village or district, then click your exact field on the map.")

with st.expander("ℹ️ How to use the map" if lang == "en" else "ℹ️ मानचित्र का उपयोग कैसे करें", expanded=False):
    if lang == "hi":
        st.markdown("""
        1. **खोज बॉक्स** में पिनकोड, गाँव या जिला टाइप करें → **खोजें** पर क्लिक करें
        2. परिणाम चुनें — मानचित्र वहाँ जाएगा
        3. अपने खेत पर **क्लिक करें** — नारंगी मार्कर दिखेगा
        4. **"इस स्थान की पुष्टि करें"** दबाएं — राज्य, मिट्टी और जलवायु स्वतः भर जाएगी
        5. हरा ✅ दिखने पर अगले चरण पर जाएं
        """)
    else:
        st.markdown("""
        1. Type **pincode, village or district** in search → click **Search**
        2. Pick the correct result — map flies there
        3. **Click on your field** — orange marker appears
        4. Click **"Confirm this location"** — state, soil type, and climate auto-detected
        5. Once green ✅ appears, click **Next**
        """)

# ── Search box ─────────────────────────────────────────────────────────────────
st.markdown("---")
search_col, btn_col = st.columns([5, 1])
with search_col:
    search_query = st.text_input(
        "🔍 Search (pincode / village / district)" if lang == "en"
        else "🔍 खोजें (पिनकोड / गाँव / जिला)",
        placeholder="e.g. 416416, Sangli, Nashik..." if lang == "en"
                    else "जैसे: 416416, सांगली, नासिक...",
        key="search_query_input",
    )
with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    do_search = st.button("Search" if lang == "en" else "खोजें",
                          use_container_width=True)

if do_search and search_query:
    with st.spinner("Searching..." if lang == "en" else "खोजा जा रहा है..."):
        results = geocode_india(search_query)
    if results:
        st.session_state["_geocode_results"] = results
    else:
        st.session_state["_geocode_results"] = []
        st.warning(f"No results for '{search_query}'. Try a nearby town." if lang == "en"
                   else f"'{search_query}' के लिए कोई परिणाम नहीं।")

for idx, r in enumerate(st.session_state.get("_geocode_results", [])):
    short_name = r["display_name"].split(",")[0].strip()
    full_name  = ", ".join(r["display_name"].split(",")[:4])
    if st.button(f"📍 {short_name} — {full_name}", key=f"geo_{idx}", use_container_width=True):
        st.session_state["map_center"] = [r["lat"], r["lng"]]
        st.session_state["map_zoom"]   = 14
        st.session_state["_geocode_results"] = []
        st.rerun()

st.markdown("---")

# ── Map render ─────────────────────────────────────────────────────────────────
confirmed_lat = st.session_state.get("lat")
confirmed_lng = st.session_state.get("lng")
pending_lat   = st.session_state.get("pending_lat")
pending_lng   = st.session_state.get("pending_lng")
map_center    = st.session_state.get("map_center")
map_zoom      = st.session_state.get("map_zoom") or 5

if map_center is None:
    if confirmed_lat and confirmed_lng:
        map_center, map_zoom = [confirmed_lat, confirmed_lng], 15
    elif pending_lat and pending_lng:
        map_center, map_zoom = [pending_lat, pending_lng], 15

folium_map = make_selection_map(
    center=map_center, zoom=map_zoom,
    confirmed_lat=confirmed_lat, confirmed_lng=confirmed_lng,
    pending_lat=pending_lat, pending_lng=pending_lng,
)

try:
    map_result = st_folium(
        folium_map, use_container_width=True, height=540,
        returned_objects=["last_clicked", "all_drawings"],
        key=f"folium_map_{str(map_center)}_{map_zoom}",
    )
    st.session_state["map_center"] = None
    st.session_state["map_zoom"]   = None
except Exception as e:
    st.error(f"Map failed to load: {e}" if lang == "en" else f"मानचित्र लोड नहीं हुआ: {e}")
    map_result = None

# ── Capture pending click ──────────────────────────────────────────────────────
raw_lat, raw_lng = extract_lat_lng(map_result)
raw_polygon      = extract_polygon_coords(map_result)

if raw_lat is not None and raw_lng is not None:
    if validate_india_bounds(raw_lat, raw_lng):
        if (raw_lat != st.session_state.get("pending_lat") or
                raw_lng != st.session_state.get("pending_lng")):
            st.session_state["pending_lat"] = raw_lat
            st.session_state["pending_lng"] = raw_lng
            st.session_state["_pending_polygon"] = raw_polygon
    else:
        st.warning(f"⚠️ Coordinates ({raw_lat:.3f}, {raw_lng:.3f}) appear outside India."
                   if lang == "en"
                   else f"⚠️ निर्देशांक ({raw_lat:.3f}, {raw_lng:.3f}) भारत के बाहर।")

# ── Status ─────────────────────────────────────────────────────────────────────
pending_lat = st.session_state.get("pending_lat")
pending_lng = st.session_state.get("pending_lng")

if confirmed_lat and confirmed_lng:
    detected_state = st.session_state.get("detected_state", "")
    detected_soil  = st.session_state.get("detected_soil_name", "")
    detected_clim  = st.session_state.get("detected_climate", "")

    if lang == "hi":
        st.success(f"✅ **पुष्टि किया गया स्थान** — {confirmed_lat:.5f}, {confirmed_lng:.5f}")
        if detected_state:
            st.info(f"🌍 राज्य: **{detected_state}** | मिट्टी: **{detected_soil}** | जलवायु: **{detected_clim}**")
    else:
        st.success(f"✅ **Confirmed location** — Lat: {confirmed_lat:.5f}, Lng: {confirmed_lng:.5f}")
        if detected_state:
            st.info(f"🌍 State: **{detected_state}** | Soil: **{detected_soil}** | Climate: **{detected_clim}**")

if pending_lat and pending_lng and (pending_lat != confirmed_lat or pending_lng != confirmed_lng):
    if lang == "hi":
        st.info(f"📍 **नया स्थान चुना** — {pending_lat:.5f}, {pending_lng:.5f} — नीचे पुष्टि करें।")
    else:
        st.info(f"📍 **New location selected** — {pending_lat:.5f}, {pending_lng:.5f} — Confirm below.")

    confirm_cols = st.columns([3, 2, 3])
    with confirm_cols[1]:
        if st.button("✅ Confirm this location" if lang == "en" else "✅ इस स्थान की पुष्टि करें",
                     type="primary", use_container_width=True):

            # Write confirmed location
            st.session_state["lat"]     = pending_lat
            st.session_state["lng"]     = pending_lng
            st.session_state["polygon"] = st.session_state.get("_pending_polygon")

            # Auto-detect state via reverse geocode
            with st.spinner("Detecting state, soil & climate..." if lang == "en"
                            else "राज्य, मिट्टी और जलवायु पहचान रही है..."):
                detected_state = reverse_geocode_state(pending_lat, pending_lng)
                if detected_state:
                    st.session_state["detected_state"] = detected_state
                    # Resolve soil + climate from state
                    from core.soil_service import resolve_soil_climate
                    sc = resolve_soil_climate(detected_state, pending_lat, pending_lng)
                    st.session_state["detected_soil_code"] = sc.get("soil_code", "")
                    st.session_state["detected_soil_name"] = sc.get("soil_name_en", "")
                    st.session_state["detected_climate"]   = sc.get("climate_zone", "")
                    st.session_state["detected_sc_data"]   = sc  # full dict for Page 2

            st.session_state["pending_lat"] = None
            st.session_state["pending_lng"] = None
            st.session_state["map_center"]  = [pending_lat, pending_lng]
            st.session_state["map_zoom"]    = 15
            st.rerun()

elif not confirmed_lat and not pending_lat:
    st.warning("👆 Search or click the map to select your field." if lang == "en"
               else "👆 खोजें या मानचित्र पर क्लिक करें।")

if confirmed_lat:
    if st.button("🗑️ Clear & pick different location" if lang == "en"
                 else "🗑️ साफ करें और दूसरा स्थान चुनें"):
        for k in ("lat", "lng", "polygon", "pending_lat", "pending_lng",
                  "_pending_polygon", "map_center", "map_zoom",
                  "detected_state", "detected_soil_code", "detected_soil_name",
                  "detected_climate", "detected_sc_data"):
            st.session_state[k] = None
        st.rerun()

# ── 3D hook ────────────────────────────────────────────────────────────────────
confirmed_lat = st.session_state.get("lat")
confirmed_lng = st.session_state.get("lng")
with st.expander("🛰️ 3D View (Future — Skyfall-GS)" if lang == "en"
                 else "🛰️ 3D दृश्य (भविष्य — Skyfall-GS)"):
    if confirmed_lat and confirmed_lng:
        default_scene_provider.render(st, lat=confirmed_lat, lng=confirmed_lng)
    else:
        st.write("Confirm a location first." if lang == "en" else "पहले स्थान की पुष्टि करें।")

# ── Navigation ─────────────────────────────────────────────────────────────────
st.divider()
col_back, col_next = st.columns(2)
with col_back:
    if st.button("⬅️ Home" if lang == "en" else "⬅️ होम"):
        st.switch_page("app.py")
with col_next:
    has_confirmed = bool(st.session_state.get("lat") and st.session_state.get("lng"))
    if st.button("Next: Farm Details ➡️" if lang == "en" else "अगला: खेत विवरण ➡️",
                 type="primary", disabled=not has_confirmed):
        st.switch_page("pages/2_Farm_Details.py")
    if not has_confirmed:
        st.caption("Confirm a location first." if lang == "en" else "पहले स्थान की पुष्टि करें।")
