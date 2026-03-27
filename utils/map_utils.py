import folium
from folium.plugins import Draw
from typing import Optional, Tuple, List, Dict, Any
import requests

ESRI_SATELLITE_TILES = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
ESRI_ATTR = (
    "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, "
    "GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
)
ESRI_LABELS_TILES = (
    "https://services.arcgisonline.com/ArcGIS/rest/services/"
    "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
)
ESRI_LABELS_ATTR = "Esri World Boundaries and Places"

INDIA_CENTER = [20.5937, 78.9629]
DEFAULT_ZOOM = 5


def geocode_india(query: str) -> List[Dict[str, Any]]:
    if not query or len(query.strip()) < 2:
        return []
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query.strip(), "format": "json", "limit": 5,
                    "countrycodes": "in", "addressdetails": 0},
            headers={"User-Agent": "FarmerRevenueOptimizer/1.0 (opensource)"},
            timeout=6,
        )
        resp.raise_for_status()
        return [{"lat": float(r["lat"]), "lng": float(r["lon"]),
                 "display_name": r.get("display_name", ""),
                 "type": r.get("type", "")} for r in resp.json()]
    except Exception:
        return []


def reverse_geocode_state(lat: float, lng: float) -> Optional[str]:
    """
    Returns the Indian state name for given coordinates.
    Used on location confirm to auto-fill state in farm details form.
    Returns None on failure.
    """
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "zoom": 5},
            headers={"User-Agent": "FarmerRevenueOptimizer/1.0 (opensource)"},
            timeout=6,
        )
        resp.raise_for_status()
        data = resp.json()
        address = data.get("address", {})
        # Nominatim returns state in "state" field
        state = address.get("state", None)
        if state:
            # Normalize common name variations
            state = _normalize_state_name(state)
        return state
    except Exception:
        return None


# Known name variations from Nominatim
_STATE_NAME_MAP = {
    "Uttar Pradesh":          "Uttar Pradesh",
    "UP":                     "Uttar Pradesh",
    "Madhya Pradesh":         "Madhya Pradesh",
    "MP":                     "Madhya Pradesh",
    "Andhra Pradesh":         "Andhra Pradesh",
    "AP":                     "Andhra Pradesh",
    "Himachal Pradesh":       "Himachal Pradesh",
    "HP":                     "Himachal Pradesh",
    "Arunachal Pradesh":      "Arunachal Pradesh",
    "Jammu and Kashmir":      "Jammu and Kashmir",
    "Jammu & Kashmir":        "Jammu and Kashmir",
    "Odisha":                 "Odisha",
    "Orissa":                 "Odisha",
    "Uttarakhand":            "Uttarakhand",
    "Uttaranchal":            "Uttarakhand",
    "Telangana":              "Telangana",
    "Chhattisgarh":           "Chhattisgarh",
    "Chattisgarh":            "Chhattisgarh",
    "Jharkhand":              "Jharkhand",
}

VALID_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]


def _normalize_state_name(name: str) -> Optional[str]:
    if name in VALID_STATES:
        return name
    mapped = _STATE_NAME_MAP.get(name)
    if mapped:
        return mapped
    # Fuzzy match
    name_lower = name.lower()
    for valid in VALID_STATES:
        if valid.lower() in name_lower or name_lower in valid.lower():
            return valid
    return name  # Return as-is if no match


def make_selection_map(
    center: Optional[List[float]] = None,
    zoom: int = DEFAULT_ZOOM,
    confirmed_lat: Optional[float] = None,
    confirmed_lng: Optional[float] = None,
    pending_lat: Optional[float] = None,
    pending_lng: Optional[float] = None,
) -> folium.Map:
    center = center or INDIA_CENTER
    m = folium.Map(location=center, zoom_start=zoom, tiles=None)

    folium.TileLayer(tiles=ESRI_SATELLITE_TILES, attr=ESRI_ATTR,
                     name="Satellite", overlay=False, control=True, show=True).add_to(m)
    folium.TileLayer(tiles="OpenStreetMap", name="Street Map",
                     overlay=False, control=True, show=False).add_to(m)
    folium.TileLayer(tiles=ESRI_LABELS_TILES, attr=ESRI_LABELS_ATTR,
                     name="Place Names (overlay)", overlay=True, control=True,
                     show=True, opacity=1.0).add_to(m)

    Draw(export=False,
         draw_options={"polygon": True, "marker": True, "rectangle": True,
                       "circle": False, "polyline": False, "circlemarker": False},
         edit_options={"edit": True, "remove": True}).add_to(m)

    if pending_lat is not None and pending_lng is not None:
        folium.Marker(
            location=[pending_lat, pending_lng],
            tooltip="Click 'Confirm' below to lock this location",
            popup=folium.Popup(
                f"<b>Pending location</b><br>Lat: {pending_lat:.5f}<br>Lng: {pending_lng:.5f}"
                "<br><i>Scroll down and click Confirm</i>", max_width=220),
            icon=folium.Icon(color="orange", icon="map-marker", prefix="fa"),
        ).add_to(m)

    if confirmed_lat is not None and confirmed_lng is not None:
        folium.Marker(
            location=[confirmed_lat, confirmed_lng],
            tooltip="Confirmed field location",
            popup=folium.Popup(
                f"<b>Confirmed location</b><br>Lat: {confirmed_lat:.5f}<br>Lng: {confirmed_lng:.5f}",
                max_width=200),
            icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def extract_lat_lng(st_folium_result: Optional[dict]) -> Tuple[Optional[float], Optional[float]]:
    if not st_folium_result:
        return None, None
    drawings = st_folium_result.get("all_drawings") or []
    for feature in drawings:
        geom = feature.get("geometry") or {}
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates") or []
        if geom_type == "Point" and len(coords) >= 2:
            return float(coords[1]), float(coords[0])
        if geom_type in ("Polygon", "MultiPolygon") and coords:
            outer = coords[0] if geom_type == "Polygon" else coords[0][0]
            if outer:
                return (sum(float(c[1]) for c in outer) / len(outer),
                        sum(float(c[0]) for c in outer) / len(outer))
        if geom_type == "LineString" and coords:
            return (sum(float(c[1]) for c in coords) / len(coords),
                    sum(float(c[0]) for c in coords) / len(coords))
    last_clicked = st_folium_result.get("last_clicked") or {}
    if last_clicked and "lat" in last_clicked and "lng" in last_clicked:
        return float(last_clicked["lat"]), float(last_clicked["lng"])
    return None, None


def extract_polygon_coords(st_folium_result: Optional[dict]) -> Optional[List[List[float]]]:
    if not st_folium_result:
        return None
    drawings = st_folium_result.get("all_drawings") or []
    for feature in drawings:
        geom = feature.get("geometry") or {}
        if geom.get("type") == "Polygon":
            outer = (geom.get("coordinates") or [[]])[0]
            return [[float(c[1]), float(c[0])] for c in outer]
    return None


def validate_india_bounds(lat: float, lng: float) -> bool:
    return 6.0 <= lat <= 38.0 and 68.0 <= lng <= 98.0
