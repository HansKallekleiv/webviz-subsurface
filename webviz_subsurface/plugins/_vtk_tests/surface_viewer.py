from pathlib import Path
import json
import logging
from time import time
from typing import List, Tuple, Callable

import numpy as np
from dash import html, Input, Output, State, callback, no_update, callback_context, dcc
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
        self.contours = self.sgrid.contour(list(np.arange(0, -3000, -10)))
        self.contours_mesh = to_mesh_state(self.contours)
        self.set_callbacks()

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=[
                        html.Button(
                            style={"marginBottom": "20px", "display": "block"},
                            id=self.uuid("clear-coordinates"),
                            children="Clear coordinates",
                        ),
                        wcc.Header("Stored coordinates:"),
                        html.Pre(
                            id=self.uuid("tooltip"),
                        ),
                    ],
                ),
                wcc.Frame(
                    style={"flex": 5},
                    children=[
                        dash_vtk.View(
                            id=self.uuid("vtk-view1"),
                            # background=[1, 1, 1],
                            pickingModes=["click"],
                            # cameraParallelProjection=True,
                            children=[
                                dash_vtk.GeometryRepresentation(
                                    id=self.uuid("surface-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(
                                            id=self.uuid("surface-mesh"),
                                            state=self.surface_mesh,
                                        )
                                    ],
                                    # showScalarBar=True,
                                    property={
                                        "show_edges": True,
                                        "opacity": 1,
                                        "lighting": False,
                                    },
                                    actor={
                                        "scale": [1, 1, 5],
                                    },
                                    colorMapPreset="erdc_rainbow_bright",
                                    colorDataRange=self.color_range,
                                    # showCubeAxes=True,
                                ),
                                dash_vtk.GeometryRepresentation(
                                    id=self.uuid("contours-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(
                                            id=self.uuid("contours-mesh"),
                                            state=self.contours_mesh,
                                        )
                                    ],
                                    property={
                                        "show_edges": True,
                                        "color": "black",
                                        "width": 5,
                                        "opacity": 1,
                                    },
                                    actor={"scale": [1, 1, 5]},
                                ),
                            ],
                        ),
                    ],
                ),
                wcc.Frame(
                    style={"flex": 5},
                    children=[
                        dash_vtk.View(
                            id=self.uuid("vtk-view2"),
                            # background=[1, 1, 1],
                            pickingModes=["click"],
                            interactorSettings=[
                                {
                                    "button": 1,
                                    "action": "Pan",
                                },
                                {
                                    "button": 2,
                                    "action": "Pan",
                                },
                                {
                                    "button": 3,
                                    "action": "Zoom",
                                    "scrollEnabled": True,
                                },
                                {
                                    "button": 1,
                                    "action": "Pan",
                                    "shift": True,
                                },
                                {
                                    "button": 1,
                                    "action": "Zoom",
                                    "alt": True,
                                },
                            ],
                            # cameraParallelProjection=True,
                            children=[
                                dash_vtk.GeometryRepresentation(
                                    id=self.uuid("surface-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(
                                            id=self.uuid("surface-mesh"),
                                            state=self.surface_mesh,
                                        )
                                    ],
                                    # showScalarBar=True,
                                    property={
                                        "show_edges": True,
                                        "opacity": 1,
                                        "lighting": False,
                                    },
                                    actor={
                                        "scale": [1, 1, 1],
                                    },
                                    colorMapPreset="erdc_rainbow_bright",
                                    colorDataRange=self.color_range,
                                    showCubeAxes=True,
                                ),
                                dash_vtk.GeometryRepresentation(
                                    id=self.uuid("contours-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(
                                            id=self.uuid("contours-mesh"),
                                            state=self.contours_mesh,
                                        )
                                    ],
                                    property={
                                        "show_edges": True,
                                        "color": "black",
                                        "width": 5,
                                        "opacity": 1,
                                    },
                                    actor={"scale": [1, 1, 1]},
                                ),
                            ],
                        ),
                    ],
                ),
                dcc.Store(self.uuid("stored-coordinates"), data=[]),
            ]
        )

    def set_callbacks(self):
        @callback(
            # Output(self.uuid("tooltip"), "children"),
            Output(self.uuid("stored-coordinates"), "data"),
            Input(self.uuid("vtk-view1"), "clickInfo"),
            Input(self.uuid("clear-coordinates"), "n_clicks"),
            State(self.uuid("stored-coordinates"), "data"),
        )
        def _update_click_info(clickdata, _n_clicks, stored_cordinates):
            if "n_clicks" in callback_context.triggered[0]["prop_id"]:
                return []
            if clickdata:
                if "representationId" in clickdata and clickdata[
                    "representationId"
                ] == self.uuid("surface-vtk-representation"):
                    stored_cordinates.append(clickdata["worldPosition"])
                    return stored_cordinates
            return no_update

        @callback(
            Output(self.uuid("tooltip"), "children"),
            Input(self.uuid("stored-coordinates"), "data"),
        )
        def _show_coords(coords):
            return json.dumps(coords, indent=2)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [(get_path, [{"path": Path(self.surface_file)}])]
