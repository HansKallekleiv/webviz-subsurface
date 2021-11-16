from typing import Dict

import numpy as np


class DeckGLMapLayersModel:
    """Handles updates to the DeckGLMap layers prop"""

    def __init__(self, layers: Dict) -> None:
        self._layers = layers

    def set_surface_grid(self, values: np.ndarray, rotation: float = 0.0):
        ...

    def set_surface_range(self):
        ...

    def set_colormap(self):
        ...

    def set_colormap_range(self):
        ...
