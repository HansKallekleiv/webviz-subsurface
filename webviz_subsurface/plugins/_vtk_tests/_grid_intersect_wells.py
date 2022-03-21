from pathlib import Path
import json
import logging
from time import time
from typing import List, Tuple, Callable

import numpy as np
from pandas.api.types import is_numeric_dtype
import plotly.express as px
from dash import (
    html,
    Input,
    Output,
    State,
    callback,
    no_update,
    callback_context,
    MATCH,
    ALL,
)
import pyvista as pv
import dash_vtk
from dash_vtk.utils import presets, to_mesh_state, to_volume_state
from webviz_config import WebvizPluginABC
from webviz_config.utils._dash_component_utils import calculate_slider_step
import webviz_core_components as wcc
import xtgeo
from webviz_subsurface._utils.webvizstore_functions import get_path

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._xtgeo_to_vtk import well_to_polydata_input, well_to_polydata_fence

from ._geometries import Well

LOGGER = logging.getLogger(__name__)


class VTKGridIntersectWells(WebvizPluginABC):
    def __init__(self, well_files: List[Path], grid_file: Path):
        """ """
        super().__init__()

        self.well_files = well_files
        wells = [xtgeo.well_from_file(get_path(well)) for well in self.well_files]
        self.wells = {well.name: well for well in wells}
        self.grid_file = grid_file
        self.ugrid = pv.read(get_path(self.grid_file))
        # self.ugrid = self.ugrid.scale([1, 1, -1])
        self.ugrid["PHIT"] = np.random.uniform(-100, 100, self.ugrid.points.shape)

        last_layer_indices = np.argwhere(
            self.ugrid["BLOCK_K"] == self.ugrid["BLOCK_K"].min()
        ).ravel()
        last_layer_grid = self.ugrid.extract_cells(last_layer_indices)
        self.last_layer_mesh = to_mesh_state(
            last_layer_grid.scale([1, 1, 5]), field_to_keep="PHIT"
        )
        self.well_tubes = {}
        self.well_fences = {}
        self.log_names = []
        self.log_color_ranges = {}

        for well_file in self.well_files:

            well = xtgeo.well_from_file(get_path(well_file))
            # Coarsen a bit
            # well.downsample(10)
            # Reverse z
            well.dataframe = well.dataframe.loc[well.dataframe["Z_TVDSS"] > 1500]
            dataframe = well.dataframe.copy()
            # dataframe["Z_TVDSS"] = dataframe["Z_TVDSS"] * -1

            # Add log names
            log_names = list(
                well.dataframe.drop(columns=["X_UTME", "Y_UTMN", "Z_TVDSS"]).columns
            )
            self.log_names = (
                log_names
                if not self.log_names
                else list(set(self.log_names).intersection(log_names))
            )

            # Add min/max of log to color
            for log_name in log_names:
                values = well.dataframe[log_name]
                if is_numeric_dtype(values):
                    minmax = [values.min(), values.max()]
                    if log_name in self.log_color_ranges:
                        self.log_color_ranges[log_name].extend(minmax)
                    else:
                        self.log_color_ranges[log_name] = minmax

            # Generate tube geometries
            self.well_tubes[well.name] = well_to_polydata_input(dataframe)

        # Calculate min max for logs across all wells
        for logname, log_vals in self.log_color_ranges.items():
            self.log_color_ranges[logname] = [min(log_vals), max(log_vals)]
        self.log_names = list(self.log_names)
        self.set_callbacks()

    @property
    def grid_layer_representation(self):
        return dash_vtk.GeometryRepresentation(
            id=self.uuid("grid-layer-representation"),
            children=[
                dash_vtk.Mesh(
                    id=self.uuid("grid-layer-mesh"),
                    state=self.last_layer_mesh,
                )
            ],
            property={"edgeVisibility ": True, "opacity": 1},
            colorMapPreset="erdc_rainbow_bright",
            showCubeAxes=True,
        )

    def intersect_view(self, well_name):

        pll = pv.Plotter()
        # pl.enable_parallel_projection()
        grid_mesh = self.well_fences[well_name]
        tube = self.well_tubes[well_name].tube(radius=5)
        # grid = grid.flip_z()

        # grid = grid.scale([1, 1, 10])
        # tube = tube.scale([1, 1, 10])
        # grid_mesh = to_mesh_state(grid, field_to_keep="PHIT")
        tube_mesh = to_mesh_state(tube, field_to_keep="PHIT")

        # pll.add_mesh(grid)
        pll.add_mesh(tube)
        return

    @property
    def well_tube_representations(self):
        return [
            dash_vtk.GeometryRepresentation(
                id={"id": self.uuid("well-rep"), "name": well_name},
                property={
                    "show_edges": False,
                    "opacity": 1,
                    "color": (0, 0, 0),
                    "lineWidth": 10,
                    "pointSize": 10,
                },
                colorDataRange=self.log_color_ranges.get("PHIT", [0, 10]),
                children=[
                    dash_vtk.Mesh(
                        id={"id": self.uuid("well-mesh"), "name": well_name},
                        state=to_mesh_state(
                            well_polydata.tube(radius=5, scalars="PHIT").scale(
                                [1, 1, 5]
                            ),
                            field_to_keep="PHIT",
                        ),
                    ),
                ],
            )
            for well_name, well_polydata in self.well_tubes.items()
        ]

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=[
                        wcc.SelectWithLabel(
                            id=self.uuid("well-select"),
                            label="Well",
                            options=[
                                {"label": well, "value": well}
                                for well in list(self.well_tubes.keys())
                            ],
                            value=list(self.well_tubes.keys())[0],
                            size=20,
                            multi=False,
                        ),
                        html.Button(
                            id=self.uuid("reset-camera"), children="Reset Camera"
                        ),
                    ],
                ),
                html.Div(
                    style={
                        "flex": 5,
                    },
                    children=[
                        wcc.Frame(
                            children=dash_vtk.View(
                                id=self.uuid("vtk-view"),
                                style={"width": "100%", "height": "40vh"},
                                # background=[1, 1, 1],
                                pickingModes=["click"],
                                children=self.well_tube_representations
                                + [
                                    self.grid_layer_representation,
                                    dash_vtk.GeometryRepresentation(
                                        id=self.uuid("well-plane-representation"),
                                        children=[
                                            dash_vtk.Mesh(
                                                id=self.uuid("well-plane-mesh"),
                                                state={},
                                            )
                                        ],
                                        property={
                                            "edgeVisibility ": True,
                                            "opacity": 1,
                                            "lighting": False,
                                        },
                                        colorMapPreset="erdc_rainbow_bright",
                                    ),
                                ],
                            )
                        ),
                        wcc.Frame(
                            style={"height": "40vh"},
                            children=[
                                dash_vtk.View(
                                    id=self.uuid("vtk-view-intersect"),
                                    style={"width": "100%", "height": "40vh"},
                                    # background=[1, 1, 1],
                                    pickingModes=["click"],
                                    cameraViewUp=(0, 0, -1),
                                    cameraParallelProjection=True,
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
                                    children=[
                                        dash_vtk.GeometryRepresentation(
                                            id=self.uuid(
                                                "well-intersect-representation"
                                            ),
                                            children=[
                                                dash_vtk.Mesh(
                                                    id=self.uuid("well-intersect-mesh"),
                                                    state={},
                                                )
                                            ],
                                            property={
                                                "show_edges": False,
                                                "opacity": 1,
                                            },
                                            colorMapPreset="erdc_rainbow_bright",
                                        ),
                                        dash_vtk.GeometryRepresentation(
                                            id=self.uuid(
                                                "grid-intersect-representation"
                                            ),
                                            children=[
                                                dash_vtk.Mesh(
                                                    id=self.uuid("grid-intersect-mesh"),
                                                    state={},
                                                )
                                            ],
                                            property={
                                                "lighting": False,
                                                "edgeVisibility ": True,
                                                "opacity": 1,
                                            },
                                            colorMapPreset="erdc_rainbow_bright",
                                        ),
                                    ],
                                )
                            ],
                        ),
                    ],
                ),
                # wcc.Frame(
                #     style={"flex": 5, "height": "90vh", "overflowY": "scroll"},
                #     children=[
                #     ],
                # ),
            ]
        )

    def set_callbacks(self):
        @callback(
            Output(self.uuid("grid-intersect-mesh"), "state"),
            Output(self.uuid("well-intersect-mesh"), "state"),
            Output(self.uuid("well-plane-mesh"), "state"),
            Output(self.uuid("vtk-view-intersect"), "cameraPosition"),
            Input(self.uuid("well-select"), "value"),
        )
        def _update_intersection(well_name):
            well_name = well_name[0] if isinstance(well_name, list) else well_name
            well = self.wells[well_name].copy()

            well.dataframe = well.dataframe.loc[well.dataframe["Z_TVDSS"] > 1500]
            well.dataframe = well.dataframe.loc[well.dataframe["Z_TVDSS"] < 1700]
            well.downsample(10)
            well_line = Well(well)
            tube = well_line.tube(radius=2)
            tube.scale([1, 1, 5], inplace=True)

            intersect = well_line.intersect_grid(self.ugrid)
            intersect_scaled = intersect.scale([1, 1, 5], inplace=False)
            pll = pv.Plotter()
            pll.add_mesh(intersect_scaled)
            pll.add_mesh(tube)
            mesh = to_mesh_state(intersect.scale([1, 1, 5]), field_to_keep="PHIT")
            mesh_scaled = to_mesh_state(intersect_scaled, field_to_keep="PHIT")
            tube_mesh = to_mesh_state(tube, field_to_keep="PHIT")

            return (
                mesh_scaled,
                tube_mesh,
                mesh,
                pll.camera.position,  # , pll.camera.focal_point, (0, 0, -1)],
            )

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        files = self.well_files + [self.grid_file]
        return [(get_path, [{"path": Path(wellfile)} for wellfile in files])]
