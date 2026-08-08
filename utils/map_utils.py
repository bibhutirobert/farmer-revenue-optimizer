import folium
from folium.plugins import Draw, LocateControl
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

    # "Locate me" — the shortest path to a correct pin for a farmer standing
    # in their own field, and the single biggest friction saver on a phone.
    # Browser geolocation only; nothing is sent anywhere by this control.
    LocateControl(
        auto_start=False,
        flyTo=True,
        keepCurrentZoomLevel=False,
        showPopup=False,
        strings={"title": "Show me where I am"},
        locateOptions={"enableHighAccuracy": True, "maxZoom": 17},
    ).add_to(m)

    # Marker is intentionally omitted: tapping the map already drops the
    # pending pin, so offering a marker tool as well just doubles the ways to
    # do one thing — which reads as confusing on a small screen. Polygon and
    # rectangle stay for tracing an actual field boundary.
    Draw(export=False,
         draw_options={"polygon": True, "marker": False, "rectangle": True,
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

    # Collapsed: expanded, this covers a meaningful slice of a phone screen
    # and sits right where thumbs land when panning.
    folium.LayerControl(collapsed=True).add_to(m)
    return m


def _vertex_mean(points: List[List[float]]) -> Optional[Tuple[float, float]]:
    """Plain average of positions, as (x, y) == (lng, lat)."""
    if not points:
        return None
    return (sum(p[0] for p in points) / len(points),
            sum(p[1] for p in points) / len(points))


def ring_centroid(ring: List[List[float]]) -> Optional[Tuple[float, float]]:
    """
    True centroid of a GeoJSON linear ring, returned as (lng, lat).

    Two things this gets right that a plain average of the coordinates does not:

    1. GeoJSON rings are *closed* — RFC 7946 requires the last position to
       repeat the first — so averaging every entry counts one vertex twice and
       drags the result toward wherever the user started drawing. For a
       rectangle that is a 20% pull toward the first corner, every time.

    2. Averaging vertices is only the centroid when they are evenly spread.
       Tracing a field by hand puts more clicks along the fiddly edges, and a
       vertex average leans toward whichever side got clicked most. The
       area-weighted (shoelace) centroid does not care how the outline was
       sampled.

    Falls back to the vertex mean for degenerate rings — fewer than three
    distinct points, or collinear ones enclosing no area — where the shoelace
    formula is undefined.

    The maths is planar on raw degrees rather than geodesic. Over a field-sized
    polygon that is a sub-metre approximation, and the callers here (state
    lookup, soil, weather grid) are orders of magnitude coarser than that.
    """
    if not ring:
        return None

    try:
        points = [[float(c[0]), float(c[1])] for c in ring if c is not None and len(c) >= 2]
    except (TypeError, ValueError):
        return None
    if not points:
        return None

    # Drop the repeated closing position so no vertex is counted twice.
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    if not points:
        return None
    if len(points) < 3:
        return _vertex_mean(points)

    doubled_area = 0.0
    cx = 0.0
    cy = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        cross = (x0 * y1) - (x1 * y0)
        doubled_area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross

    area = doubled_area / 2.0
    if abs(area) < 1e-12:          # collinear / zero-area ring
        return _vertex_mean(points)

    return (cx / (6.0 * area), cy / (6.0 * area))


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
            centre = ring_centroid(outer) if outer else None
            if centre:
                lng, lat = centre
                return lat, lng
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
