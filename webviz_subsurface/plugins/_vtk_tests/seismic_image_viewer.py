from pathlib import Path
import json
import logging
from time import time
from typing import List, Tuple, Callable

import numpy as np
from dash import html, Input, Output, State, callback, no_update, callback_context
import pyvista as pv
import dash_vtk
from dash_vtk.utils import presets, to_mesh_state, to_volume_state
from webviz_config import WebvizPluginABC
from webviz_config.utils._dash_component_utils import calculate_slider_step
import webviz_core_components as wcc
import xtgeo
from webviz_subsurface._utils.webvizstore_functions import get_path

from webviz_subsurface._utils.perf_timer import PerfTimer

LOGGER = logging.getLogger(__name__)


def xtgeo_cube_to_uniform_grid(seismic: xtgeo.Cube) -> pv.UniformGrid:
    grid = pv.UniformGrid()
    grid.dimensions = list(seismic.dimensions)
    grid.origin = (seismic.xori, seismic.yori, seismic.zori)
    grid.spacing = (seismic.xinc, seismic.yinc, seismic.zinc)

    grid.point_data["values"] = seismic.values.flatten(
        order="F"
    )  # seismic.values.flatten(order="F")
    # grid.point_arrays["data"] = grid.point_arrays["values"]
    grid.set_active_scalars("values")
    return grid


class VTKSeismicImageViewer(WebvizPluginABC):
    def __init__(self, seismic_file: Path):
        """ """
        super().__init__()

        cube = xtgeo.cube_from_file(get_path(seismic_file))
        cube.values = cube.values * 1000000
        self.values = cube.values.flatten(order="F")
        self.cube = cube

        self.set_callbacks()

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=[
                        wcc.Slider(
                            id="i-slider",
                            label="I-slice",
                            min=self.cube.ilines[0],
                            max=self.cube.ilines[-1],
                            value=self.cube.ilines[0],
                            marks={
                                str(value): {"label": f"{value:.2f}"}
                                for value in [self.cube.ilines[0], self.cube.ilines[-1]]
                            },
                            step=1,
                            updatemode="drag",
                        ),
                        wcc.Slider(
                            id="j-slider",
                            label="J-slice",
                            min=self.cube.xlines[0],
                            max=self.cube.xlines[-1],
                            value=self.cube.xlines[0],
                            marks={
                                str(value): {"label": f"{value:.2f}"}
                                for value in [self.cube.xlines[0], self.cube.xlines[-1]]
                            },
                            step=1,
                            updatemode="drag",
                        ),
                        wcc.Slider(
                            id="k-slider",
                            label="K-slice",
                            min=0,
                            max=self.cube.nlay,
                            marks={
                                str(value): {"label": f"{value:.2f}"}
                                for value in [0, self.cube.nlay]
                            },
                            value=50,
                            step=1,
                            updatemode="drag",
                        ),
                    ],
                ),
                wcc.Frame(
                    style={"flex": 5},
                    children=[
                        dash_vtk.View(
                            id=self.uuid("vtk-view"),
                            background=[1, 1, 1],
                            # pickingModes=["click"],
                            children=[
                                dash_vtk.ShareDataSet(
                                    dash_vtk.ImageData(
                                        dimensions=list(self.cube.dimensions),
                                        origin=[
                                            self.cube.xori,
                                            self.cube.yori,
                                            self.cube.zori,
                                        ],
                                        spacing=[
                                            self.cube.xinc,
                                            self.cube.yinc,
                                            self.cube.zinc,
                                        ],
                                        children=[
                                            dash_vtk.PointData(
                                                [
                                                    dash_vtk.DataArray(
                                                        registration="setScalars",
                                                        values=self.values,
                                                    )
                                                ]
                                            )
                                        ],
                                    ),
                                ),
                                dash_vtk.SliceRepresentation(
                                    id="slice-repr-i",
                                    iSlice=20,
                                    property={"colorWindow": 2000, "colorLevel": 0},
                                    children=dash_vtk.ShareDataSet(),
                                ),
                                dash_vtk.SliceRepresentation(
                                    id="slice-repr-j",
                                    jSlice=20,
                                    property={"colorWindow": 2000, "colorLevel": 0},
                                    children=dash_vtk.ShareDataSet(),
                                ),
                                dash_vtk.SliceRepresentation(
                                    id="slice-repr-k",
                                    kSlice=50,
                                    property={"colorWindow": 2000, "colorLevel": 0},
                                    children=dash_vtk.ShareDataSet(),
                                ),
                            ],
                            style={"width": "100%", "height": "90vh"},
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
                    "seismic-vtk-representation"
                ):
                    return ([json.dumps(info["worldPosition"], indent=2)],)

                return no_update
            return [""]

        @callback(
            Output("slice-repr-i", "iSlice"),
            Input("i-slider", "value"),
        )
        def _update_click_info(slice_idx):
            return slice_idx

        @callback(
            Output("slice-repr-j", "jSlice"),
            Input("j-slider", "value"),
        )
        def _update_click_info(slice_idx):
            return slice_idx

        @callback(
            Output("slice-repr-k", "kSlice"),
            Input("k-slider", "value"),
        )
        def _update_click_info(slice_idx):
            return slice_idx
