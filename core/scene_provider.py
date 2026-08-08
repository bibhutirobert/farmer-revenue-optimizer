"""
Scene Provider — pluggable 3D / satellite view for a confirmed field.
=====================================================================

`BaseSceneProvider` is the stable seam. Anything that can draw a scene for a
lat/lng can be dropped in without touching the pages.

Two concrete providers ship today:

  TerrainSceneProvider   Real, tilted 3D terrain. Elevation from AWS Terrain
                         Tiles (Terrarium), textured with the same Esri World
                         Imagery the 2D map already uses. No API key, no GPU,
                         no paid tier — it renders in the browser via deck.gl.

  PlaceholderSceneProvider
                         The original informational notice. Kept as the
                         automatic fallback when pydeck is unavailable.

On Skyfall-GS: it is a research codebase (Gaussian splatting from satellite
imagery), not a hosted tile API — there is no key to buy and per-scene
optimisation needs a CUDA GPU, so it cannot run on Streamlit Cloud's CPU tier.
If that ever ships as a service, it becomes a third class here and the rest of
the app still does not change. That is the point of this seam.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from utils.map_utils import ESRI_SATELLITE_TILES

# AWS Terrain Tiles — public, free, no key, no rate limit worth worrying about.
# https://registry.opendata.aws/terrain-tiles/
TERRARIUM_TILES = (
    "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
)

# Terrarium encodes height as (R * 256 + G + B / 256) - 32768 metres.
TERRARIUM_DECODER = {
    "rScaler": 256,
    "gScaler": 1,
    "bScaler": 1 / 256,
    "offset": -32768,
}

DEFAULT_PITCH = 55
DEFAULT_ZOOM = 15


class BaseSceneProvider(ABC):
    @abstractmethod
    def render(
        self,
        container,
        lat: float,
        lng: float,
        bbox: Optional[dict] = None,
    ) -> None:
        """
        Render a 3D or satellite scene into a Streamlit container.

        Args:
            container : Streamlit module or container object (st, st.sidebar, column, etc.)
                        IMPORTANT: Do NOT use `with container:` — st module is not a context
                        manager. Always call container.info() / container.markdown() directly.
            lat       : Centre latitude
            lng       : Centre longitude
            bbox      : Optional {"north":.., "south":.., "east":.., "west":..}
        """
        ...


def bbox_from_polygon(polygon: Optional[List[List[float]]]) -> Optional[dict]:
    """
    [[lat, lng], ...] -> {"north","south","east","west"}.

    Matches the ordering produced by map_utils.extract_polygon_coords.
    Returns None for empty/malformed input so callers can pass it straight
    through to render() without guarding.
    """
    if not polygon:
        return None
    try:
        lats = [float(p[0]) for p in polygon]
        lngs = [float(p[1]) for p in polygon]
    except (TypeError, ValueError, IndexError):
        return None
    if not lats or not lngs:
        return None
    return {
        "north": max(lats),
        "south": min(lats),
        "east": max(lngs),
        "west": min(lngs),
    }


def _bbox_ring(bbox: dict) -> List[List[float]]:
    """Closed [lng, lat] ring for the field outline (deck.gl wants lng first)."""
    n, s = bbox["north"], bbox["south"]
    e, w = bbox["east"], bbox["west"]
    return [[w, n], [e, n], [e, s], [w, s], [w, n]]


def build_scene_spec(
    lat: float,
    lng: float,
    bbox: Optional[dict] = None,
    pitch: int = DEFAULT_PITCH,
    zoom: int = DEFAULT_ZOOM,
) -> Dict[str, Any]:
    """
    Pure description of the scene — plain dicts, no pydeck import.

    Keeping this separate means the camera and layer geometry are unit-testable
    without a rendering stack, and the pydeck call below stays a thin adapter.
    """
    view_state = {
        "latitude": float(lat),
        "longitude": float(lng),
        "zoom": zoom,
        "pitch": pitch,
        "bearing": 0,
    }

    layers: List[Dict[str, Any]] = [
        {
            "type": "TerrainLayer",
            "elevation_data": TERRARIUM_TILES,
            "texture": ESRI_SATELLITE_TILES,
            "elevation_decoder": TERRARIUM_DECODER,
            "max_zoom": 15,
        }
    ]

    if bbox:
        layers.append(
            {
                "type": "PathLayer",
                "data": [{"path": _bbox_ring(bbox)}],
                "get_path": "path",
                "get_color": [255, 214, 10],
                "get_width": 4,
                "width_min_pixels": 2,
            }
        )

    layers.append(
        {
            "type": "ScatterplotLayer",
            "data": [{"position": [float(lng), float(lat)]}],
            "get_position": "position",
            "get_fill_color": [255, 59, 48],
            "get_radius": 12,
            "radius_min_pixels": 4,
        }
    )

    return {"initial_view_state": view_state, "layers": layers}


class PlaceholderSceneProvider(BaseSceneProvider):
    """Informational notice — the fallback when pydeck is not importable."""

    def render(
        self,
        container,
        lat: float,
        lng: float,
        bbox: Optional[dict] = None,
    ) -> None:
        # Call container.info() DIRECTLY — never `with container:`
        # `st` (the module itself) is not a context manager and raises TypeError.
        container.info(
            "**3D Terrain View**\n\n"
            f"Coordinates locked: **{lat:.5f}, {lng:.5f}**\n\n"
            "The 3D renderer needs the `pydeck` package, which is not installed "
            "in this environment. Add `pydeck` to requirements.txt to enable it — "
            "no API key or configuration is required."
        )


class TerrainSceneProvider(BaseSceneProvider):
    """
    Real 3D terrain, rendered client-side by deck.gl.

    Elevation tiles and imagery tiles are both public CDNs, so this works on a
    free Streamlit Cloud deployment with nothing configured. If pydeck is
    missing we degrade to the placeholder rather than breaking the page.
    """

    def __init__(self, pitch: int = DEFAULT_PITCH, zoom: int = DEFAULT_ZOOM):
        self.pitch = pitch
        self.zoom = zoom
        self._fallback = PlaceholderSceneProvider()

    def render(
        self,
        container,
        lat: float,
        lng: float,
        bbox: Optional[dict] = None,
    ) -> None:
        try:
            import pydeck as pdk
        except ImportError:
            self._fallback.render(container, lat, lng, bbox)
            return

        spec = build_scene_spec(
            lat, lng, bbox, pitch=self.pitch, zoom=self.zoom
        )

        layers = []
        for layer in spec["layers"]:
            kwargs = {k: v for k, v in layer.items() if k != "type"}
            layers.append(pdk.Layer(layer["type"], **kwargs))

        deck = pdk.Deck(
            layers=layers,
            initial_view_state=pdk.ViewState(**spec["initial_view_state"]),
            # None keeps this off Mapbox entirely — no token needed.
            map_style=None,
        )

        # pydeck_chart, like info(), is called directly on the container.
        container.pydeck_chart(deck)
        container.caption(
            "Drag to rotate · scroll to zoom · elevation from AWS Terrain Tiles, "
            "imagery from Esri World Imagery. Vertical detail is limited at very "
            "close zoom — terrain tiles are ~30 m resolution."
        )


default_scene_provider: BaseSceneProvider = TerrainSceneProvider()
