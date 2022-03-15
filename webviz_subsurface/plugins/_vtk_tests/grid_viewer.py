from pathlib import Path
import json
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

from webviz_subsurface._utils.webvizstore_functions import get_path


class GridViewer(WebvizPluginABC):
    def __init__(self, vtu_file: Path):
        """
            Using dash-vtk and pyvista to visualize 3D grids.
        * **`vtu_file`:** Path to file with UnstructuredGrid VTK format
        with I,I,K field arrays
        """
        super().__init__()
        self.vtu_file = vtu_file
        self.ugrid = pv.read(get_path(vtu_file))
        self.ugrid.flip_z(inplace=True)
        indices = np.argwhere(self.ugrid["K"] == 1).ravel()
        layer = self.ugrid.extract_cells(indices)
        self.mesh = to_mesh_state(layer, field_to_keep="PERMZ")
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
                            ],
                        ),
                    ],
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
                                    id=self.uuid("grid-vtk-representation"),
                                    children=[
                                        dash_vtk.Mesh(
                                            id=self.uuid("mesh"), state=self.mesh
                                        )
                                    ],
                                    property={"show_edges": False, "opacity": 1},
                                    colorMapPreset="erdc_rainbow_bright",
                                ),
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
            prevent_initial=True,
        )
        def _update_mesh(
            grid_property: str, z_scale, grid_layer, show_full_grid, current_val
        ):
            ctx = callback_context.triggered[0]["prop_id"]
            reset_camera = time() if "z-scale" in ctx else no_update
            ugrid = self.ugrid.scale([1, 1, z_scale], inplace=False)
            if not show_full_grid:
                indices = np.argwhere(ugrid["K"] == grid_layer).ravel()
                ugrid = ugrid.extract_cells(indices)

            min = ugrid[grid_property].min()
            max = ugrid[grid_property].max()
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
            Output(self.uuid("grid-vtk-representation"), "colorDataRange"),
            Input(self.uuid("color-range"), "value"),
        )
        def _update_mesh(valrange: str):

            if not valrange or valrange == [0, 0]:
                return no_update
            return valrange

        @callback(
            Output(self.uuid("grid-vtk-representation"), "colorMapPreset"),
            Input(self.uuid("color-scale"), "value"),
        )
        def _update_mesh(scale: str):
            return scale

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
                    "grid-vtk-representation"
                ):
                    return ([json.dumps(info["worldPosition"], indent=2)],)

                return no_update
            return [""]

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [(get_path, [{"path": Path(self.vtu_file)}])]
