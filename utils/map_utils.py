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

# Label overlay that adds place names ON TOP of the satellite layer
ESRI_LABELS_TILES = (
    "https://services.arcgisonline.com/ArcGIS/rest/services/"
    "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
)
ESRI_LABELS_ATTR = "Esri World Boundaries and Places"

INDIA_CENTER = [20.5937, 78.9629]
DEFAULT_ZOOM = 5


def geocode_india(query: str) -> List[Dict[str, Any]]:
    """
    Geocode a free-text query (pincode, district, village, city) restricted to India.
    Uses Nominatim (OpenStreetMap) — free, no API key required.

    Returns a list of up to 5 dicts:
        {"lat": float, "lng": float, "display_name": str, "type": str}
    Returns [] on failure or no results.
    """
    if not query or len(query.strip()) < 2:
        return []
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query.strip(),
                "format": "json",
                "limit": 5,
                "countrycodes": "in",
                "addressdetails": 0,
            },
            headers={"User-Agent": "FarmerRevenueOptimizer/1.0 (opensource)"},
            timeout=6,
        )
        resp.raise_for_status()
        results = resp.json()
        return [
            {
                "lat": float(r["lat"]),
                "lng": float(r["lon"]),
                "display_name": r.get("display_name", ""),
                "type": r.get("type", ""),
            }
            for r in results
        ]
    except Exception:
        return []


def make_selection_map(
    center: Optional[List[float]] = None,
    zoom: int = DEFAULT_ZOOM,
    confirmed_lat: Optional[float] = None,
    confirmed_lng: Optional[float] = None,
    pending_lat: Optional[float] = None,
    pending_lng: Optional[float] = None,
) -> folium.Map:
    """
    Build the Leaflet selection map with:
    - Esri satellite basemap (default)
    - Esri label overlay (place names visible on satellite)
    - OpenStreetMap as alternative base layer
    - Draw tools (polygon, rectangle, marker)
    - A RED pending marker if pending_lat/lng are set (not yet confirmed)
    - A GREEN confirmed marker if confirmed_lat/lng are set
    """
    center = center or INDIA_CENTER

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=None,           # We add layers manually for full control
    )

    # --- Base layers ---
    folium.TileLayer(
        tiles=ESRI_SATELLITE_TILES,
        attr=ESRI_ATTR,
        name="Satellite",
        overlay=False,
        control=True,
        show=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Street Map",
        overlay=False,
        control=True,
        show=False,
    ).add_to(m)

    # --- Label overlay: adds place/district/road names on top of satellite ---
    folium.TileLayer(
        tiles=ESRI_LABELS_TILES,
        attr=ESRI_LABELS_ATTR,
        name="Place Names (overlay)",
        overlay=True,         # overlay = sits on top of base layer
        control=True,
        show=True,            # on by default so satellite shows names
        opacity=1.0,
    ).add_to(m)

    # --- Draw tools ---
    Draw(
        export=False,
        draw_options={
            "polygon":      True,
            "marker":       True,
            "rectangle":    True,
            "circle":       False,
            "polyline":     False,
            "circlemarker": False,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    # --- Pending marker (red/orange) — user clicked but hasn't confirmed yet ---
    if pending_lat is not None and pending_lng is not None:
        folium.Marker(
            location=[pending_lat, pending_lng],
            tooltip="Click 'Confirm' below to lock this location",
            popup=folium.Popup(
                f"<b>Pending location</b><br>Lat: {pending_lat:.5f}<br>Lng: {pending_lng:.5f}"
                "<br><i>Scroll down and click Confirm</i>",
                max_width=220,
            ),
            icon=folium.Icon(color="orange", icon="map-marker", prefix="fa"),
        ).add_to(m)

    # --- Confirmed marker (green) — locked-in location ---
    if confirmed_lat is not None and confirmed_lng is not None:
        folium.Marker(
            location=[confirmed_lat, confirmed_lng],
            tooltip="Confirmed field location",
            popup=folium.Popup(
                f"<b>Confirmed location</b><br>Lat: {confirmed_lat:.5f}<br>Lng: {confirmed_lng:.5f}",
                max_width=200,
            ),
            icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def extract_lat_lng(
    st_folium_result: Optional[dict],
) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract the best available lat/lng from st_folium() result dict.
    Priority: drawn Point > Polygon centroid > last_clicked
    Returns (None, None) if no interaction yet.
    """
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
                avg_lat = sum(float(c[1]) for c in outer) / len(outer)
                avg_lng = sum(float(c[0]) for c in outer) / len(outer)
                return avg_lat, avg_lng

        if geom_type == "LineString" and coords:
            avg_lat = sum(float(c[1]) for c in coords) / len(coords)
            avg_lng = sum(float(c[0]) for c in coords) / len(coords)
            return avg_lat, avg_lng

    last_clicked = st_folium_result.get("last_clicked") or {}
    if last_clicked and "lat" in last_clicked and "lng" in last_clicked:
        return float(last_clicked["lat"]), float(last_clicked["lng"])

    return None, None


def extract_polygon_coords(
    st_folium_result: Optional[dict],
) -> Optional[List[List[float]]]:
    """Return outer-ring polygon as [[lat, lng], ...] if a polygon was drawn."""
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
    """Loose bounding box for the Indian subcontinent: Lat 6-38N, Lng 68-98E."""
    return 6.0 <= lat <= 38.0 and 68.0 <= lng <= 98.0
