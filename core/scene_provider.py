from abc import ABC, abstractmethod
from typing import Optional
import streamlit as st


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
            container: A Streamlit container (st, st.expander, st.columns()[n], etc.)
            lat: Center latitude
            lng: Center longitude
            bbox: Optional bounding box dict {"north":.., "south":.., "east":.., "west":..}
        """
        ...


class PlaceholderSceneProvider(BaseSceneProvider):
    """
    v1 placeholder — shows an informational upgrade path notice.
    Replace with SkyFallSceneProvider when 3D tile API is available.
    """

    def render(self, container, lat: float, lng: float, bbox: Optional[dict] = None) -> None:
        with container:
            st.info(
                "**3D Terrain View** — Skyfall-GS Integration Point\n\n"
                f"Coordinates: **{lat:.5f}, {lng:.5f}**\n\n"
                "In a future version, a photorealistic 3D terrain view of your selected field "
                "will appear here. The interface for this module is already defined — "
                "a Skyfall-GS or Cesium-based provider can be plugged in with zero changes "
                "to the rest of the application."
            )


default_scene_provider: BaseSceneProvider = PlaceholderSceneProvider()
