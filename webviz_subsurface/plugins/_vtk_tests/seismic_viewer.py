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

LOGGER = logging.getLogger(__name__)


def xtgeo_seismic_to_vtk(seismic: xtgeo.Cube) -> pv.StructuredGrid:
    timer = PerfTimer()
    xi, yi = seismic.get_xy_values(asmasked=False)
    zi = seismic.values
    zif = np.ma.filled(zi, fill_value=np.nan)
    col = np.linspace(0, 1, zif.ravel().shape[0])
    sgrid = pv.StructuredGrid(xi, yi, zif)
    sgrid.flip_z(inplace=True)
    sgrid["Elevation"] = col  # .ravel(order='F')
    print(f"Converted seismic to vtk {timer.elapsed_s()}")

    return sgrid


class VTKSeismicViewer(WebvizPluginABC):
    def __init__(self, seismic_file: Path):
        """ """
        super().__init__()

        cube = xtgeo.cube_from_file(get_path(seismic_file))
        dimensions = list(cube.dimensions)
        self.cube = cube
        self.values = cube.values.flatten(order="C")
        print(cube.values.shape)
        print(cube.dimensions)
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
                            background=[1, 1, 1],
                            pickingModes=["click"],
                            children=[
                                dash_vtk.VolumeRepresentation(
                                    [
                                        dash_vtk.VolumeController(size=[400, 150]),
                                        dash_vtk.ImageData(
                                            dimensions=list(self.cube.dimensions),
                                            origin=[-2, -2, -2],
                                            spacing=[250, 250, 250],
                                            children=[
                                                dash_vtk.PointData(
                                                    [
                                                        dash_vtk.DataArray(
                                                            registration="setScalars",
                                                            values=self.values * 10000,
                                                            name="Temperature",
                                                        )
                                                    ]
                                                )
                                            ],
                                        ),
                                    ],
                                    colorDataRange=[
                                        self.values.min(),
                                        self.values.max(),
                                    ],
                                    colorMapPreset="BuRd",
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
                    "surface-vtk-representation"
                ):
                    return ([json.dumps(info["worldPosition"], indent=2)],)

                return no_update
            return [""]

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [(get_path, [{"path": Path(self.vtu_file)}])]
