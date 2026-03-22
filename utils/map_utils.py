import folium
from folium.plugins import Draw
from typing import Optional, Tuple, List

ESRI_SATELLITE_TILES = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
ESRI_ATTR = (
    "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, "
    "GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
)

INDIA_CENTER = [20.5937, 78.9629]
DEFAULT_ZOOM = 5


def make_selection_map(
    center: Optional[List[float]] = None,
    zoom: int = DEFAULT_ZOOM,
) -> folium.Map:
    center = center or INDIA_CENTER

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=None,
    )

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

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def extract_lat_lng(
    st_folium_result: Optional[dict],
) -> Tuple[Optional[float], Optional[float]]:
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
