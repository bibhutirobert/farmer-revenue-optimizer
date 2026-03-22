"""
Page 1 — Satellite map: farmer searches and selects their field.

Flow:
  1. Farmer types a location (pincode / village / district) → geocode → map flies there
  2. Farmer clicks on their exact field → orange PENDING marker appears
  3. Farmer clicks "Confirm this location" → marker turns green, location is LOCKED
  4. Only after confirmation does the Next button become active

This two-step (click → confirm) prevents accidental clicks from polluting the workflow.
"""

import streamlit as st
from streamlit_folium import st_folium
from utils.map_utils import (
    make_selection_map,
    extract_lat_lng,
    extract_polygon_coords,
    validate_india_bounds,
    geocode_india,
)
from core.scene_provider import default_scene_provider

st.set_page_config(
    page_title="Land Selection | FRO",
    page_icon="🗺️",
    layout="wide",
)

# ── Language toggle ────────────────────────────────────────────────────────────
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

# ── Ensure pending/confirmed state keys exist ──────────────────────────────────
for key in ("lat", "lng", "polygon", "pending_lat", "pending_lng",
            "map_center", "map_zoom"):
    if key not in st.session_state:
        st.session_state[key] = None

# ── Title ──────────────────────────────────────────────────────────────────────
with col_title:
    if lang == "hi":
        st.title("🗺️ चरण 1: अपना खेत चुनें")
        st.caption("खोज बॉक्स में पिनकोड / गाँव / जिला टाइप करें, फिर मानचित्र पर अपने खेत पर क्लिक करें।")
    else:
        st.title("🗺️ Step 1: Select Your Field")
        st.caption("Search by pincode, village or district, then click your exact field on the map.")

# ── How-to instructions ────────────────────────────────────────────────────────
with st.expander(
    "ℹ️ How to use the map" if lang == "en" else "ℹ️ मानचित्र का उपयोग कैसे करें",
    expanded=False,
):
    if lang == "hi":
        st.markdown("""
        1. **खोज बॉक्स** में अपना पिनकोड, गाँव या जिला टाइप करें और **खोजें** पर क्लिक करें
        2. खोज परिणाम से अपना स्थान चुनें — मानचित्र वहाँ चला जाएगा
        3. **Satellite** दृश्य में अपने खेत के केंद्र पर **क्लिक करें** — नारंगी मार्कर दिखेगा
        4. **या** बाईं ओर के ड्रॉ टूल से खेत की सीमा बनाएं
        5. **"इस स्थान की पुष्टि करें"** बटन दबाएं → मार्कर हरा हो जाएगा
        6. हरा ✅ दिखने पर **अगले चरण** पर जाएं
        7. **Place Names** चेकबॉक्स से उपग्रह दृश्य पर गाँव/जिले के नाम देखें
        """)
    else:
        st.markdown("""
        1. Type your **pincode, village or district** in the search box and click **Search**
        2. Pick the correct result — the map will fly there automatically
        3. **Click on your field** on the satellite view — an orange marker will appear
        4. **Or** use the draw tools (left side) to outline your field boundary
        5. Click **"Confirm this location"** — the marker turns green and location is locked
        6. Once you see the green ✅, click **Next** below
        7. Toggle **Place Names** in the layer control (top-right) to see village/district labels on satellite
        """)

# ── SEARCH BOX ────────────────────────────────────────────────────────────────
st.markdown("---")
search_label = "🔍 Search location (pincode / village / district / city)" \
    if lang == "en" else "🔍 स्थान खोजें (पिनकोड / गाँव / जिला / शहर)"

search_col, btn_col = st.columns([5, 1])
with search_col:
    search_query = st.text_input(
        search_label,
        placeholder="e.g. 416416, Sangli, Nashik, Ludhiana..." if lang == "en"
                    else "जैसे: 416416, सांगली, नासिक, लुधियाना...",
        label_visibility="visible",
        key="search_query_input",
    )
with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)   # vertical align
    do_search = st.button(
        "Search" if lang == "en" else "खोजें",
        use_container_width=True,
        type="secondary",
    )

# Run geocoding when button pressed OR Enter key (query changed)
if do_search and search_query:
    with st.spinner("Searching..." if lang == "en" else "खोजा जा रहा है..."):
        results = geocode_india(search_query)
    if results:
        st.session_state["_geocode_results"] = results
        st.session_state["_geocode_query"]   = search_query
    else:
        st.session_state["_geocode_results"] = []
        st.warning(
            f"No results found for '{search_query}'. Try a nearby town or check the spelling."
            if lang == "en"
            else f"'{search_query}' के लिए कोई परिणाम नहीं। नजदीकी शहर या वर्तनी जाँचें।"
        )

# Show geocode results as selectable buttons
geo_results = st.session_state.get("_geocode_results", [])
if geo_results:
    st.caption(
        "Select the correct location to zoom the map there:"
        if lang == "en"
        else "मानचित्र वहाँ ले जाने के लिए सही स्थान चुनें:"
    )
    for idx, r in enumerate(geo_results):
        short_name = r["display_name"].split(",")[0].strip()
        full_name  = ", ".join(r["display_name"].split(",")[:4])
        if st.button(
            f"📍 {short_name}  —  {full_name}",
            key=f"geo_result_{idx}",
            use_container_width=True,
        ):
            st.session_state["map_center"] = [r["lat"], r["lng"]]
            st.session_state["map_zoom"]   = 14
            st.session_state["_geocode_results"] = []   # clear results after pick
            st.rerun()

st.markdown("---")

# ── Determine map centre and zoom ─────────────────────────────────────────────
confirmed_lat = st.session_state.get("lat")
confirmed_lng = st.session_state.get("lng")
pending_lat   = st.session_state.get("pending_lat")
pending_lng   = st.session_state.get("pending_lng")

# Map center: prefer geocoded target, then confirmed, then pending, then India
map_center = st.session_state.get("map_center")
map_zoom   = st.session_state.get("map_zoom") or 5

if map_center is None:
    if confirmed_lat and confirmed_lng:
        map_center = [confirmed_lat, confirmed_lng]
        map_zoom   = 15
    elif pending_lat and pending_lng:
        map_center = [pending_lat, pending_lng]
        map_zoom   = 15

# ── Build & render map ────────────────────────────────────────────────────────
folium_map = make_selection_map(
    center=map_center,
    zoom=map_zoom,
    confirmed_lat=confirmed_lat,
    confirmed_lng=confirmed_lng,
    pending_lat=pending_lat,
    pending_lng=pending_lng,
)

# Use a dynamic key: when map_center changes (geocode pick), map re-renders at new location
map_key = f"folium_map_{str(map_center)}_{map_zoom}"

try:
    map_result = st_folium(
        folium_map,
        use_container_width=True,
        height=540,
        returned_objects=["last_clicked", "all_drawings"],
        key=map_key,
    )
    # Reset map_center after render so subsequent interactions don't keep snapping
    st.session_state["map_center"] = None
    st.session_state["map_zoom"]   = None
except Exception as e:
    st.error(
        f"Map failed to load: {e}. Try refreshing the page."
        if lang == "en"
        else f"मानचित्र लोड नहीं हुआ: {e}। पृष्ठ ताज़ा करें।"
    )
    map_result = None

# ── Capture click / drawing as PENDING (not confirmed yet) ───────────────────
raw_lat, raw_lng = extract_lat_lng(map_result)
raw_polygon      = extract_polygon_coords(map_result)

if raw_lat is not None and raw_lng is not None:
    if validate_india_bounds(raw_lat, raw_lng):
        # Store as pending — do NOT overwrite confirmed lat/lng yet
        if (raw_lat != st.session_state.get("pending_lat") or
                raw_lng != st.session_state.get("pending_lng")):
            st.session_state["pending_lat"] = raw_lat
            st.session_state["pending_lng"] = raw_lng
            st.session_state["_pending_polygon"] = raw_polygon
    else:
        st.warning(
            f"⚠️ Clicked coordinates ({raw_lat:.3f}, {raw_lng:.3f}) appear outside India."
            if lang == "en"
            else f"⚠️ क्लिक किए गए निर्देशांक ({raw_lat:.3f}, {raw_lng:.3f}) भारत के बाहर हैं।"
        )

# ── Status area ────────────────────────────────────────────────────────────────
pending_lat = st.session_state.get("pending_lat")
pending_lng = st.session_state.get("pending_lng")

if confirmed_lat and confirmed_lng:
    if lang == "hi":
        st.success(
            f"✅ **पुष्टि किया गया स्थान** — अक्षांश: {confirmed_lat:.5f}, "
            f"देशांतर: {confirmed_lng:.5f}  |  मानचित्र पर क्लिक करके बदलें।"
        )
    else:
        st.success(
            f"✅ **Confirmed location** — Lat: {confirmed_lat:.5f}, "
            f"Lng: {confirmed_lng:.5f}  |  Click the map to pick a different spot."
        )

if pending_lat and pending_lng and (pending_lat != confirmed_lat or pending_lng != confirmed_lng):
    if lang == "hi":
        st.info(
            f"📍 **नया स्थान चुना गया** — अक्षांश: {pending_lat:.5f}, "
            f"देशांतर: {pending_lng:.5f}\n\n"
            "नीचे **'इस स्थान की पुष्टि करें'** बटन दबाएं।"
        )
    else:
        st.info(
            f"📍 **New location selected** — Lat: {pending_lat:.5f}, "
            f"Lng: {pending_lng:.5f}\n\n"
            "Click **'Confirm this location'** below to lock it in."
        )

    # ── CONFIRM BUTTON ─────────────────────────────────────────────────────────
    confirm_cols = st.columns([3, 2, 3])
    with confirm_cols[1]:
        if st.button(
            "✅ Confirm this location" if lang == "en" else "✅ इस स्थान की पुष्टि करें",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["lat"]     = pending_lat
            st.session_state["lng"]     = pending_lng
            st.session_state["polygon"] = st.session_state.get("_pending_polygon")
            st.session_state["pending_lat"] = None
            st.session_state["pending_lng"] = None
            # Zoom to confirmed location so green marker is visible
            st.session_state["map_center"] = [pending_lat, pending_lng]
            st.session_state["map_zoom"]   = 15
            st.rerun()

elif not confirmed_lat and not pending_lat:
    st.warning(
        "👆 Search for your location above or click directly on the satellite map."
        if lang == "en"
        else "👆 ऊपर अपना स्थान खोजें या सीधे उपग्रह मानचित्र पर क्लिक करें।"
    )

# ── Clear location button (shown only when something is confirmed) ────────────
if confirmed_lat:
    if st.button(
        "🗑️ Clear & pick a different location" if lang == "en"
        else "🗑️ साफ करें और दूसरा स्थान चुनें",
        type="secondary",
    ):
        for k in ("lat", "lng", "polygon", "pending_lat", "pending_lng",
                  "_pending_polygon", "map_center", "map_zoom"):
            st.session_state[k] = None
        st.rerun()

# ── 3D scene hook (Skyfall-GS placeholder) ───────────────────────────────────
confirmed_lat = st.session_state.get("lat")
confirmed_lng = st.session_state.get("lng")

with st.expander(
    "🛰️ 3D View (Future Feature — Skyfall-GS)" if lang == "en"
    else "🛰️ 3D दृश्य (भविष्य की सुविधा — Skyfall-GS)"
):
    if confirmed_lat and confirmed_lng:
        # Direct call — never `with container:` on the st module (causes TypeError)
        default_scene_provider.render(
            st,
            lat=confirmed_lat,
            lng=confirmed_lng,
        )
    else:
        st.write(
            "Confirm a location first to preview the 3D integration point."
            if lang == "en"
            else "3D पूर्वावलोकन के लिए पहले स्थान की पुष्टि करें।"
        )

# ── Navigation ────────────────────────────────────────────────────────────────
st.divider()
col_back, col_next = st.columns(2)
with col_back:
    if st.button("⬅️ Home" if lang == "en" else "⬅️ होम"):
        st.switch_page("app.py")

with col_next:
    has_confirmed = bool(st.session_state.get("lat") and st.session_state.get("lng"))
    next_label = (
        "Next: Enter Farm Details ➡️" if lang == "en"
        else "अगला: खेत विवरण दर्ज करें ➡️"
    )
    if st.button(next_label, type="primary", disabled=not has_confirmed):
        st.switch_page("pages/2_Farm_Details.py")
    if not has_confirmed:
        st.caption(
            "Confirm a location on the map first."
            if lang == "en"
            else "पहले मानचित्र पर स्थान की पुष्टि करें।"
        )
