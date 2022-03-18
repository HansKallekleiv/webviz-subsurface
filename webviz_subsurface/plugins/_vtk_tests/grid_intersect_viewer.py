from pathlib import Path
import json
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

from webviz_subsurface._utils.webvizstore_functions import get_path


class VTKGridIntersectViewer(WebvizPluginABC):
    def __init__(self, vtu_file: Path):
        """
            Using dash-vtk and pyvista to visualize 3D grids.
        * **`vtu_file`:** Path to file with UnstructuredGrid VTK format
        with I,I,K field arrays
        """
        super().__init__()
        self.vtu_file = vtu_file
        points = np.array(
            [
                [1368.747674583733, 8736.023727834163, 1827.4556186053305],
                [8197.706796255321, 6298.683476134713, 1932.6929383187016],
            ]
        )
        line = pv.Spline(points, 100)

        self.ugrid = pv.read(get_path(vtu_file))
        self.ugrid.flip_z(inplace=True)
        # indices = np.argwhere(self.ugrid["K"] == 1).ravel()
        # layer = self.ugrid.extract_cells(indices)
        # self.mesh = to_mesh_state(layer, field_to_keep="PERMZ")
        self.set_callbacks()

    @property
    def grid_properties(self):
        return self.ugrid.array_names

    @property
    def layers(self):
        return list(set(self.ugrid["K"]))

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=[
                        wcc.Dropdown(
                            label="Grid property",
                            id=self.uuid("grid-property"),
                            options=[
                                {"value": prop, "label": prop}
                                for prop in self.grid_properties
                            ],
                            value="PERMZ",
                            clearable=False,
                        ),
                        wcc.Slider(
                            label="Z-scale",
                            id=self.uuid("z-scale"),
                            min=1,
                            max=10,
                            value=1,
                            step=1,
                            # updatemode="drag",
                        ),
                        wcc.Dropdown(
                            label="Color scale",
                            id=self.uuid("color-scale"),
                            options=[
                                {"value": prop, "label": prop} for prop in presets
                            ],
                            value="erdc_rainbow_bright",
                            clearable=False,
                        ),
                        wcc.RangeSlider(
                            label="Color Range",
                            id=self.uuid("color-range"),
                            min=self.ugrid["PERMZ"].min(),
                            max=self.ugrid["PERMZ"].max(),
                            step=10,
                            value=[
                                self.ugrid["PERMZ"].min(),
                                self.ugrid["PERMZ"].max(),
                            ],
                            # marks=None,
                            tooltip={
                                "placement": "bottom",
                                "always_visible": True,
                            },
                            updatemode="drag",
                        ),
                        wcc.Selectors(
                            label="Grid filter",
                            children=[
                                wcc.Checklist(
                                    id=self.uuid("full-grid"),
                                    options=[
                                        {
                                            "label": "Show full grid",
                                            "value": "full_grid",
                                        }
                                    ],
                                ),
                                wcc.Slider(
                                    label="Grid layer",
                                    id=self.uuid("grid-layer"),
                                    min=min(self.layers),
                                    max=max(self.layers),
                                    value=self.layers[1],
                                    step=1,
                                    updatemode="drag",
                                    marks=None,
                                    tooltip={
                                        "placement": "bottom",
                                        "always_visible": True,
                                    },
                                ),
                                html.Button(
                                    style={"marginBottom": "20px", "display": "block"},
                                    id=self.uuid("clear-coordinates"),
                                    children="Clear coordinates",
                                ),
                                html.Button(
                                    style={"marginBottom": "20px", "display": "block"},
                                    id=self.uuid("apply-coordinates"),
                                    children="Create intersection",
                                ),
                                wcc.Header("Stored coordinates:"),
                                html.Pre(
                                    style={"height": "40vh", "overflowY": "auto"},
                                    id=self.uuid("tooltip"),
                                ),
                            ],
                        ),
                    ],
                ),
                wcc.Frame(
                    style={"flex": 5},
                    children=[
                        dash_vtk.View(
                            id=self.uuid("vtk-view"),
                            # background=[0, 0, 0],
                            pickingModes=["click"],
                            children=[
                                dash_vtk.GeometryRepresentation(
                                    id=self.uuid("grid-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(id=self.uuid("mesh"), state={})
                                    ],
                                    property={"show_edges": False, "opacity": 1},
                                    colorMapPreset="erdc_rainbow_bright",
                                    # showCubeAxes=True,
                                    # cubeAxesStyle={
                                    # "gridColor": "black",
                                    # "backgroundColor": "black",
                                    # "color": "black",
                                    # "borderColor": "black",
                                    # "axisTextStyle": {
                                    #     "fontColor": "black",
                                    #     "color": "black",
                                    #     "borderColor": "black",
                                    #     "fontStyle": "normal",
                                    #     "fontSize": 18,
                                    #     "fontFamily": "serif",
                                    #     "storeColor": "black",
                                    #     "fillStyle": "black",
                                    # },
                                    # "tickLabelPixelOffset": 12.0,
                                    # "tickTextStyle": {
                                    #     "fontColor": "black",
                                    #     "borderColor": "black",
                                    #     "color": "black",
                                    #     "fontStyle": "normal",
                                    #     "fontSize": 14,
                                    #     "fontFamily": "serif",
                                    # },
                                    # },
                                ),
                                dash_vtk.GeometryRepresentation(
                                    id=self.uuid("slice-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(
                                            id=self.uuid("slice-mesh"),
                                            state={},
                                        )
                                    ],
                                    property={"show_edges": True, "opacity": 1},
                                    colorMapPreset="erdc_rainbow_bright",
                                ),
                            ],
                        ),
                    ],
                ),
                dcc.Store(id=self.uuid("stored-coordinates"), data=[]),
            ]
        )

    def set_callbacks(self):
        @callback(
            Output(self.uuid("mesh"), "state"),
            Output(self.uuid("color-range"), "min"),
            Output(self.uuid("color-range"), "max"),
            Output(self.uuid("color-range"), "step"),
            Output(self.uuid("color-range"), "value"),
            Output(self.uuid("color-range"), "marks"),
            Output(self.uuid("vtk-view"), "triggerResetCamera"),
            Input(self.uuid("grid-property"), "value"),
            Input(self.uuid("z-scale"), "value"),
            Input(self.uuid("grid-layer"), "value"),
            Input(self.uuid("full-grid"), "value"),
            State(self.uuid("color-range"), "value"),
        )
        def _update_mesh(
            grid_property: str, z_scale, grid_layer, show_full_grid, current_val
        ):
            ctx = callback_context.triggered[0]["prop_id"]
            print("hello")
            reset_camera = time() if "z-scale" in ctx or ctx == "." else no_update
            ugrid = self.ugrid.scale([1, 1, z_scale], inplace=False)
            if not show_full_grid:
                indices = np.argwhere(ugrid["K"] == grid_layer).ravel()
                ugrid = ugrid.extract_cells(indices)

            min = self.ugrid[grid_property].min()
            max = self.ugrid[grid_property].max()
            current_val = [min, max]
            return (
                to_mesh_state(ugrid, field_to_keep=grid_property),
                min,
                max,
                calculate_slider_step(
                    min_value=min,
                    max_value=max,
                    steps=100,
                ),
                current_val,
                {str(value): {"label": f"{value:.2f}"} for value in [min, max]},
                reset_camera,
            )

        @callback(
            Output(self.uuid("slice-mesh"), "state"),
            Output(self.uuid("vtk-view"), "triggerRender"),
            Input(self.uuid("grid-property"), "value"),
            Input(self.uuid("z-scale"), "value"),
            Input(self.uuid("apply-coordinates"), "n_clicks"),
            Input(self.uuid("stored-coordinates"), "data"),
            prevent_initial=True,
        )
        def _update_mesh(
            grid_property: str, z_scale: int, apply, stored_coordinates: list
        ):

            ctx = callback_context.triggered[0]["prop_id"]
            if not stored_coordinates or len(stored_coordinates) < 2:
                return {}, time()
            line = pv.Spline(np.array(stored_coordinates))
            slice = self.ugrid.slice_along_line(line)
            slice = slice.scale([1, 1, z_scale])

            return to_mesh_state(slice, field_to_keep=grid_property), no_update

        @callback(
            Output(self.uuid("grid-vtk-representation"), "colorDataRange"),
            Output(self.uuid("slice-vtk-representation"), "colorDataRange"),
            Input(self.uuid("color-range"), "value"),
        )
        def _update_mesh(valrange: str):

            if not valrange or valrange == [0, 0]:
                return no_update, no_update
            return valrange, valrange

        @callback(
            Output(self.uuid("grid-vtk-representation"), "colorMapPreset"),
            Output(self.uuid("slice-vtk-representation"), "colorMapPreset"),
            Input(self.uuid("color-scale"), "value"),
        )
        def _update_mesh(scale: str):
            return scale, scale

        @callback(
            # Output(self.uuid("tooltip"), "children"),
            Output(self.uuid("stored-coordinates"), "data"),
            Input(self.uuid("vtk-view"), "clickInfo"),
            Input(self.uuid("clear-coordinates"), "n_clicks"),
            State(self.uuid("stored-coordinates"), "data"),
        )
        def _update_click_info(clickdata, _n_clicks, stored_cordinates):
            if "n_clicks" in callback_context.triggered[0]["prop_id"]:
                return []
            if clickdata:
                if "representationId" in clickdata and clickdata[
                    "representationId"
                ] == self.uuid("grid-vtk-representation"):
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
        return [(get_path, [{"path": Path(self.vtu_file)}])]
