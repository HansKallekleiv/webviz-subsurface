from pathlib import Path
import json
import logging
from time import time
from typing import List, Tuple, Callable

import numpy as np
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


class VTKCombinedViewer(WebvizPluginABC):
    def __init__(self, seismic_file: Path, well_files: List[Path], surface_file: Path):
        """ """
        super().__init__()
        self.seismic_file = seismic_file
        self.well_files = well_files
        self.surface_file = surface_file
        cube = xtgeo.cube_from_file(get_path(self.seismic_file))
        surface = xtgeo.surface_from_file(get_path(self.surface_file))
        surface.values = surface.values * -5
        # cube.values = cube.values * -5
        self.wells = {}
        for well_file in self.well_files:
            well = xtgeo.well_from_file(get_path(well_file))
            well.dataframe["Z_TVDSS"] = well.dataframe["Z_TVDSS"] * 5
            well.downsample(20)
            dataframe = well.dataframe.copy()
            dataframe["Z_TVDSS"] = dataframe["Z_TVDSS"] * -1
            self.wells[well.name] = well_to_polydata_input(dataframe)
        self.sgrid = surface_to_structured_grid(surface)
        self.color_range = [
            self.sgrid["Elevation"].min(),
            self.sgrid["Elevation"].max(),
        ]
        self.surface_mesh = to_mesh_state(self.sgrid, field_to_keep="Elevation")
        self.ugrid = cube_to_uniform_grid(cube)
        self.values = cube.values.flatten(order="F")

        self.cube = cube
        self.imin = self.cube.ilines[0]
        self.imax = self.cube.ilines[-1]
        self.jmin = self.cube.xlines[0]
        self.jmax = self.cube.xlines[-1]
        self.kmin = 0
        self.kmax = self.cube.nlay - 1
        # self.ugrid = self.ugrid.rotate_z(angle=self.cube.rotation)
        self.ugrid = self.ugrid.flip_z()
        ugrid = self.ugrid.extract_subset(
            [self.imin, self.imax, self.jmin, self.jmax, 50, 50]
        )

        self.seismic_mesh = to_mesh_state(ugrid, field_to_keep="values")
        self.crange = [self.values.min(), self.values.max()]
        self.histo = self.make_value_distribution_plot()
        self.set_callbacks()

    def make_value_distribution_plot(self):
        counts, bins = np.histogram(self.values, bins=500)

        bins = 0.5 * (bins[:-1] + bins[1:])
        histo = px.bar(
            x=bins,
            y=counts,
            color_discrete_sequence=["indianred"],
            title="Seismic color range - Zoom to adjust",
        )
        histo.update_traces(hoverinfo="skip")
        histo["layout"].update(
            dict(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title=""),
                yaxis=dict(visible=False, fixedrange=True),
                margin=dict(b=0),
            )
        )

        return histo

    @property
    def well_representations(self):
        return [
            dash_vtk.GeometryRepresentation(
                id="well",
                property={
                    "show_edges": False,
                    "opacity": 1,
                    "color": (0, 0, 0),
                    "lineWidth": 10,
                    "pointSize": 10,
                },
                children=[
                    dash_vtk.Mesh(
                        state=to_mesh_state(
                            well.tube(radius=20, scalars="PHIT"), field_to_keep="PHIT"
                        )
                    ),
                ],
            )
            for well in self.wells.values()
        ]

    @property
    def seismic_slice_representations(self):
        return [
            dash_vtk.GeometryRepresentation(
                id={
                    "id": self.uuid("slice-rep"),
                    "indices": indice,
                },
                children=[
                    dash_vtk.Mesh(
                        id={
                            "id": self.uuid("slice-mesh"),
                            "indices": indice,
                        },
                        state=self.seismic_mesh,
                    )
                ],
                colorMapPreset="BuRd",
                colorDataRange=self.crange,
            )
            for indice in ["i", "j", "k"]
        ]

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=[
                        wcc.Slider(
                            id={"id": self.uuid("slice-slider"), "indices": "i"},
                            label="I-slice",
                            min=self.cube.ilines[0],
                            max=self.cube.ilines[-1],
                            value=self.cube.ilines[20],
                            marks={
                                str(value): {"label": f"{value:.2f}"}
                                for value in [self.cube.ilines[0], self.cube.ilines[-1]]
                            },
                            step=1,
                            updatemode="drag",
                        ),
                        wcc.Slider(
                            id={"id": self.uuid("slice-slider"), "indices": "j"},
                            label="J-slice",
                            min=self.cube.xlines[0],
                            max=self.cube.xlines[-1],
                            value=self.cube.xlines[20],
                            marks={
                                str(value): {"label": f"{value:.2f}"}
                                for value in [self.cube.xlines[0], self.cube.xlines[-1]]
                            },
                            step=1,
                            updatemode="drag",
                        ),
                        wcc.Slider(
                            id={"id": self.uuid("slice-slider"), "indices": "k"},
                            label="K-slice",
                            min=0,
                            max=self.cube.nlay - 1,
                            marks={
                                str(value): {"label": f"{value:.2f}"}
                                for value in [0, self.cube.nlay]
                            },
                            value=50,
                            step=1,
                            updatemode="drag",
                        ),
                        wcc.Slider(
                            label="Z-scale",
                            id=self.uuid("z-scale"),
                            min=1,
                            max=10,
                            value=5,
                            step=1,
                            # updatemode="drag",
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
                            children=[
                                dash_vtk.GeometryRepresentation(
                                    id=self.uuid("surface-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(
                                            id=self.uuid("surface-mesh"),
                                            state=self.surface_mesh,
                                        )
                                    ],
                                    showCubeAxes=True,
                                    property={"show_edges": True, "opacity": 1},
                                    actor={"scale": [1, 1, 1]},
                                    colorMapPreset="erdc_rainbow_bright",
                                    colorDataRange=self.color_range,
                                )
                            ]
                            + self.well_representations
                            + self.seismic_slice_representations,
                        ),
                        wcc.Graph(
                            style={"height": "20vh"},
                            id=self.uuid("histogram"),
                            figure=self.histo,
                        ),
                    ],
                ),
            ]
        )

    def set_callbacks(self):
        @callback(
            Output({"id": self.uuid("slice-mesh"), "indices": MATCH}, "state"),
            Input({"id": self.uuid("slice-slider"), "indices": MATCH}, "value"),
            Input(self.uuid("z-scale"), "value"),
        )
        def _update_click_info(slice_idx, z_scale):

            indice = callback_context.inputs_list[0]["id"]["indices"]
            if indice == "i":
                ugrid = self.ugrid.extract_subset(
                    [slice_idx, slice_idx, self.jmin, self.jmax, 0, self.cube.nlay - 1]
                )
            elif indice == "j":
                ugrid = self.ugrid.extract_subset(
                    [self.imin, self.imax, slice_idx, slice_idx, 0, self.cube.nlay - 1]
                )
            else:
                ugrid = self.ugrid.extract_subset(
                    [self.imin, self.imax, self.jmin, self.jmax, slice_idx, slice_idx]
                )
            print("zscale", z_scale)
            ugrid = ugrid.scale([1, 1, z_scale], inplace=False)
            return to_mesh_state(ugrid, field_to_keep="values")

        @callback(
            Output({"id": self.uuid("slice-rep"), "indices": ALL}, "colorDataRange"),
            Input(self.uuid("histogram"), "relayoutData"),
        )
        def _update_color_range(data):
            if data is not None:
                if data.get("xaxis.range[0]") and data.get("xaxis.range[1]"):
                    return [[data["xaxis.range[0]"], data["xaxis.range[1]"]]] * 3
                if data.get("xaxis.autorange") is True:
                    return [self.crange] * 3
            return no_update, no_update, no_update

        @callback(
            Output(self.uuid("vtk-view"), "triggerResetCamera"),
            Input(self.uuid("reset-camera"), "n_clicks"),
        )
        def _reset_camera(n_clicks):
            if not n_clicks:
                return no_update
            return time()

        # @callback(
        #     Output(self.uuid("tooltip"), "children"),
        #     [
        #         Input(self.uuid("vtk-view"), "clickInfo"),
        #         Input(self.uuid("vtk-view"), "hoverInfo"),
        #     ],
        # )
        # def _update_click_info(clickData, hoverData):
        #     info = hoverData if hoverData else clickData
        #     print(info)
        #     return info
        #     if info:
        #         if "representationId" in info and info["representationId"] == self.uuid(
        #             "grid-vtk-representation"
        #         ):
        #             return ([json.dumps(info["worldPosition"], indent=2)],)

        #         return no_update
        #     return [""]

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        files = self.well_files + [self.surface_file, self.seismic_file]
        return [(get_path, [{"path": Path(wellfile)} for wellfile in files])]
