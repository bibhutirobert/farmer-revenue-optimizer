import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.scene_provider import (
    TERRARIUM_DECODER,
    PlaceholderSceneProvider,
    TerrainSceneProvider,
    bbox_from_polygon,
    build_scene_spec,
)


class FakeContainer:
    """Records what a provider would have drawn, without Streamlit."""

    def __init__(self):
        self.infos = []
        self.decks = []
        self.captions = []

    def info(self, text):
        self.infos.append(text)

    def pydeck_chart(self, deck):
        self.decks.append(deck)

    def caption(self, text):
        self.captions.append(text)


# ── bbox_from_polygon ──────────────────────────────────────────────────────────

def test_bbox_from_polygon_matches_extents():
    # [lat, lng] ordering, as produced by map_utils.extract_polygon_coords
    polygon = [[19.0, 72.8], [19.2, 72.8], [19.2, 73.1], [19.0, 73.1]]
    assert bbox_from_polygon(polygon) == {
        "north": 19.2, "south": 19.0, "east": 73.1, "west": 72.8,
    }


def test_bbox_from_polygon_handles_missing_and_malformed():
    assert bbox_from_polygon(None) is None
    assert bbox_from_polygon([]) is None
    assert bbox_from_polygon([["not", "numeric"]]) is None
    assert bbox_from_polygon([[19.0]]) is None


# ── build_scene_spec ───────────────────────────────────────────────────────────

def test_spec_centres_camera_on_field_and_tilts():
    spec = build_scene_spec(19.07, 72.87)
    view = spec["initial_view_state"]
    assert view["latitude"] == 19.07
    assert view["longitude"] == 72.87
    # A pitch of zero would be a flat map, not a 3D view.
    assert view["pitch"] > 0


def test_spec_always_includes_terrain_and_marker():
    types = [layer["type"] for layer in build_scene_spec(19.07, 72.87)["layers"]]
    assert "TerrainLayer" in types
    assert "ScatterplotLayer" in types


def test_terrain_layer_uses_keyless_public_tiles():
    terrain = build_scene_spec(19.07, 72.87)["layers"][0]
    # Both CDNs must stay key-free — a token here would break free deployments.
    assert "elevation-tiles-prod" in terrain["elevation_data"]
    assert "arcgisonline" in terrain["texture"]
    assert "key=" not in terrain["texture"].lower()
    assert "token" not in terrain["texture"].lower()


def test_terrarium_decoder_recovers_known_elevation():
    # Terrarium: (R * 256 + G + B / 256) - 32768 metres.
    # R=128, G=10, B=0 -> 32768 + 10 - 32768 = 10 m
    d = TERRARIUM_DECODER
    height = 128 * d["rScaler"] + 10 * d["gScaler"] + 0 * d["bScaler"] + d["offset"]
    assert height == 10


def test_field_outline_only_drawn_when_bbox_given():
    without = [l["type"] for l in build_scene_spec(19.07, 72.87)["layers"]]
    assert "PathLayer" not in without

    bbox = {"north": 19.2, "south": 19.0, "east": 73.1, "west": 72.8}
    with_bbox = build_scene_spec(19.07, 72.87, bbox=bbox)["layers"]
    paths = [l for l in with_bbox if l["type"] == "PathLayer"]
    assert len(paths) == 1

    ring = paths[0]["data"][0]["path"]
    # Closed ring, and deck.gl expects [lng, lat] — the reverse of our input.
    assert ring[0] == ring[-1]
    assert ring[0] == [72.8, 19.2]


# ── providers ──────────────────────────────────────────────────────────────────

def test_terrain_provider_falls_back_when_pydeck_missing(monkeypatch):
    """A missing optional dependency must degrade, never crash the page."""
    import builtins

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "pydeck":
            raise ImportError("simulated missing pydeck")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)

    container = FakeContainer()
    TerrainSceneProvider().render(container, lat=19.07, lng=72.87)

    assert container.decks == []
    assert len(container.infos) == 1


def test_placeholder_provider_reports_coordinates():
    container = FakeContainer()
    PlaceholderSceneProvider().render(container, lat=19.07, lng=72.87)
    assert "19.07" in container.infos[0]
