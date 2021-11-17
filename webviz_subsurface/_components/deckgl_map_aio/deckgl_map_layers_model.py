from typing import Dict, List, Optional
from enum import Enum

import numpy as np


class LayerTypes(str, Enum):
    HILLSHADING = "Hillshading2DLayer"
    COLORMAP = "ColormapLayer"
    WELL = "WellsLayer"


class DeckGLMapLayersModel:
    """Handles updates to the DeckGLMap layers prop"""

    def __init__(self, layers: List[Dict]) -> None:
        self._layers = layers

    def _update_layer_by_type(self, layer_type: Enum, layer_data: Dict):
        layers = list(filter(lambda x: x["@@type"] == layer_type, self._layers))
        if not layers:
            raise KeyError(f"No {layer_type} found in layer specification!")
        if len(layers) > 1:
            raise KeyError(
                f"Multiple layers of type {layer_type} found in layer specification!"
            )
        layer_idx = self._layers.index(layers[0])
        self._layers[layer_idx].update(layer_data)

    def set_property_map(self, layer_id: Optional[str] = None):
        self._update_layer_by_type(layer_type=LayerTypes.HILLSHADING, layer_data={})

    def set_surface_range(self):
        ...

    def set_colormap(self):
        ...

    def set_colormap_range(self):
        ...
