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

from ._xtgeo_to_vtk import (
    cube_to_uniform_grid,
    well_to_polydata_input,
    surface_to_structured_grid,
)

LOGGER = logging.getLogger(__name__)


class VTKWellViewer(WebvizPluginABC):
    def __init__(self, well_files: List[Path]):
        """ """
        super().__init__()

        self.well_files = well_files
        self.wells = {}
        self.log_names = []
        self.log_color_ranges = {}
        wells = []
        for well_file in self.well_files:

            well = xtgeo.well_from_file(get_path(well_file))
            # Reverse z
            well.dataframe["Z_TVDSS"] = well.dataframe["Z_TVDSS"] * 5
            # Coarsen a bit
            well.downsample(10)

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

            self.wells[well.name] = well_to_polydata_input(well)

        for logname, log_vals in self.log_color_ranges.items():
            self.log_color_ranges[logname] = [min(log_vals), max(log_vals)]

        self.log_names = list(self.log_names)
        self.set_callbacks()

    @property
    def well_representations(self):
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
                            well_polydata.tube(radius=20, scalars="PHIT"),
                            field_to_keep="PHIT",
                        ),
                    ),
                ],
            )
            for well_name, well_polydata in self.wells.items()
        ]

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=[
                        wcc.SelectWithLabel(
                            id=self.uuid("well-log"),
                            label="Well log",
                            options=[
                                {"label": log, "value": log} for log in self.log_names
                            ],
                            value=self.log_names[0],
                            size=20,
                        ),
                        html.Button(
                            id=self.uuid("reset-camera"), children="Reset Camera"
                        ),
                    ],
                ),
                wcc.Frame(
                    style={
                        "flex": 5,
                    },
                    children=[
                        dash_vtk.View(
                            id=self.uuid("vtk-view"),
                            style={"width": "100%", "height": "70vh"},
                            # background=[1, 1, 1],
                            pickingModes=["click"],
                            children=self.well_representations,
                        ),
                    ],
                ),
            ]
        )

    def set_callbacks(self):
        @callback(
            Output(self.uuid("vtk-view"), "triggerResetCamera"),
            Input(self.uuid("reset-camera"), "n_clicks"),
        )
        def _reset_camera(n_clicks):
            if not n_clicks:
                return no_update
            return time()

        @callback(
            Output({"id": self.uuid("well-mesh"), "name": ALL}, "state"),
            Output({"id": self.uuid("well-rep"), "name": ALL}, "colorDataRange"),
            Input(self.uuid("well-log"), "value"),
        )
        def _set_well_log(log_name):
            log_name = log_name[0] if isinstance(log_name, list) else log_name
            well_mesh_and_range = []

            meshes = [
                to_mesh_state(
                    well_polydata.tube(radius=20, scalars=log_name),
                    field_to_keep=log_name,
                )
                for well_name, well_polydata in self.wells.items()
            ]
            log_range = [self.log_color_ranges.get(log_name, [0, 10])]
            if log_range == [0, 0]:
                log_range = [0, 1]
            return meshes, log_range * len(list(self.wells.keys()))

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        files = self.well_files
        return [(get_path, [{"path": Path(wellfile)} for wellfile in files])]
