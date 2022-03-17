from pathlib import Path
import json
import logging
from time import time
from typing import List, Tuple, Callable

import numpy as np
from dash import html, Input, Output, State, callback, no_update, callback_context
import pyvista as pv
import dash_vtk
from dash_vtk.utils import presets, to_mesh_state
from webviz_config import WebvizPluginABC
from webviz_config.utils._dash_component_utils import calculate_slider_step
import webviz_core_components as wcc
import xtgeo
from webviz_subsurface._utils.webvizstore_functions import get_path

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._xtgeo_to_vtk import surface_to_structured_grid

LOGGER = logging.getLogger(__name__)


class VTKSurfaceViewer(WebvizPluginABC):
    def __init__(self, surface_file: Path):
        """ """
        super().__init__()
        self.surface_file = surface_file
        surface = xtgeo.surface_from_file(get_path(self.surface_file))
        surface.values *= -1
        self.sgrid = surface_to_structured_grid(surface)
        self.color_range = [
            self.sgrid["Elevation"].min(),
            self.sgrid["Elevation"].max(),
        ]
        self.surface_mesh = to_mesh_state(self.sgrid, field_to_keep="Elevation")
        self.set_callbacks()

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=[],
                ),
                wcc.Frame(
                    style={"flex": 5},
                    children=[
                        dash_vtk.View(
                            id=self.uuid("vtk-view"),
                            # background=[1, 1, 1],
                            pickingModes=["click"],
                            children=[
                                dash_vtk.GeometryRepresentation(
                                    id=self.uuid("surface-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(
                                            id=self.uuid("surface-mesh"),
                                            state=self.surface_mesh,
                                        )
                                    ],
                                    property={"show_edges": True, "opacity": 1},
                                    actor={"scale": [1, 1, 1]},
                                    colorMapPreset="erdc_rainbow_bright",
                                    colorDataRange=self.color_range,
                                    showCubeAxes=True,
                                ),
                                # dash_vtk.GeometryRepresentation(
                                #     id=self.uuid("contour-vtk-representation"),
                                #     children=[
                                #         dash_vtk.Mesh(
                                #             id=self.uuid("contour-mesh"),
                                #             state=self.contours,
                                #         )
                                #     ],
                                #     property={"show_edges": True, "opacity": 1},
                                #     actor={"scale": [1, 1, 1]},
                                #     colorMapPreset="erdc_rainbow_bright",
                                # ),
                            ],
                        ),
                        html.Pre(
                            id=self.uuid("tooltip"),
                            style={
                                "position": "absolute",
                                "bottom": "25px",
                                "left": "25px",
                                "zIndex": 1,
                                "color": "black",
                            },
                        ),
                    ],
                ),
            ]
        )

    def set_callbacks(self):
        @callback(
            [
                Output(self.uuid("tooltip"), "children"),
            ],
            [
                Input(self.uuid("vtk-view"), "clickInfo"),
                Input(self.uuid("vtk-view"), "hoverInfo"),
            ],
        )
        def _update_click_info(clickData, hoverData):
            info = hoverData if hoverData else clickData
            if info:
                if "representationId" in info and info["representationId"] == self.uuid(
                    "surface-vtk-representation"
                ):
                    return ([json.dumps(info["worldPosition"], indent=2)],)

                return no_update
            return [""]

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [(get_path, [{"path": Path(self.surface_file)}])]
