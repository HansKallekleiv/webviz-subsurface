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


def xtgeo_surface_to_vtk(surface: xtgeo.RegularSurface) -> pv.StructuredGrid:
    timer = PerfTimer()
    xi, yi = surface.get_xy_values(asmasked=False)
    zi = surface.values
    zif = np.ma.filled(zi, fill_value=np.nan)
    col = np.linspace(0, 1, zif.ravel().shape[0])
    sgrid = pv.StructuredGrid(xi, yi, zif)
    sgrid.flip_z(inplace=True)
    sgrid["Elevation"] = col  # .ravel(order='F')
    print(f"Converted surface to vtk {timer.elapsed_s()}")

    return sgrid


class VTKSurfaceViewer(WebvizPluginABC):
    def __init__(self, surface_file: Path):
        """ """
        super().__init__()

        surface = xtgeo.surface_from_file(get_path(surface_file))
        timer = PerfTimer()
        self.sgrid = xtgeo_surface_to_vtk(surface)

        self.sgrid.set_active_scalars("Elevation")
        z = self.sgrid["Elevation"]
        self.color_range = [z.min(), z.max()]

        mi, ma = round(min(z), ndigits=-2), round(max(z), ndigits=-2)
        step = 10
        cntrs = np.arange(mi, ma + step, step)
        contours = self.sgrid.contour(cntrs, scalars="Elevation")
        polydata_points = self.sgrid.extract_geometry()

        self.contours = to_mesh_state(contours)
        self.surface_mesh = to_mesh_state(self.sgrid, "Elevation")
        print("preparing mesh", timer.elapsed_s())
        view = dash_vtk.View(
            id=self.uuid("vtk-view"),
            background=[1, 1, 1],
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
                    actor={"scale": [1, 1, 3]},
                    colorMapPreset="erdc_rainbow_bright",
                    colorDataRange=self.color_range,
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
        )
        print("making view", timer.elapsed_s())
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
                                dash_vtk.GeometryRepresentation(
                                    id=self.uuid("surface-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(
                                            id=self.uuid("surface-mesh"),
                                            state=self.surface_mesh,
                                        )
                                    ],
                                    property={"show_edges": True, "opacity": 1},
                                    actor={"scale": [1, 1, 3]},
                                    colorMapPreset="erdc_rainbow_bright",
                                    colorDataRange=self.color_range,
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
        return [(get_path, [{"path": Path(self.vtu_file)}])]
