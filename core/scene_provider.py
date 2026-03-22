from abc import ABC, abstractmethod
from typing import Optional


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


class PlaceholderSceneProvider(BaseSceneProvider):
    """
    v1 placeholder — informational upgrade-path notice.
    Replace with SkyFallSceneProvider when 3D tile API is available.
    """

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
            "**3D Terrain View** — Skyfall-GS Integration Point\n\n"
            f"Coordinates locked: **{lat:.5f}, {lng:.5f}**\n\n"
            "In a future version, a photorealistic 3D terrain view of your selected field "
            "will appear here. The interface for this module is already defined — "
            "a Skyfall-GS or Cesium-based provider can be swapped in with zero changes "
            "to the rest of the application."
        )


default_scene_provider: BaseSceneProvider = PlaceholderSceneProvider()
