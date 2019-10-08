from uuid import uuid4
from pathlib import Path
import json

import numpy as np
from matplotlib import colors

from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_colorscales

from webviz_config import WebvizContainerABC
from webviz_subsurface_components import LayeredMap
from webviz_subsurface.datainput.layeredmap._image_processing import (
    get_colormap,
    array_to_png,
)
from webviz_subsurface.datainput import get_realizations, find_surfaces
from webviz_subsurface.datainput._surface import calculate_surface_statistics
from ._surface_selector import SurfaceSelector


class SurfaceViewerOneByOne(WebvizContainerABC):
    """### SurfaceViewerOneByOne
    Visualizes statistical surfaces for one-by-one sensitivity cases
"""

    def __init__(self, app, container_settings, ensembles):

        self.ens_paths = tuple(
            (ens, container_settings["scratch_ensembles"][ens]) for ens in ensembles
        )

        # Find surfaces
        config = find_surfaces(self.ens_paths)

        # Extract realizations and sensitivity information
        ensembles = get_realizations(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )

        self._ensembles = ensembles
        self._storage_id = f"{str(uuid4())}-surface-viewer"
        self._low_map_id = f"{str(uuid4())}-low-id"
        self._base_map_id = f"{str(uuid4())}-base-id"
        self._high_map_id = f"{str(uuid4())}-high-id"
        self._low_map_label_id = f"{str(uuid4())}-low-label-id"
        self._base_map_label_id = f"{str(uuid4())}-base-label-id"
        self._high_map_label_id = f"{str(uuid4())}-high-label-id"
        self._low_map_wrapper_id = f"{str(uuid4())}-low-wrapper-id"
        self._base_map_wrapper_id = f"{str(uuid4())}-base-wrapper-id"
        self._high_map_wrapper_id = f"{str(uuid4())}-high-wrapper-id"
        self.selector = SurfaceSelector(app, config, ensembles)
        self.set_callbacks(app)

    def add_webvizstore(self):
        return [
            (
                get_realizations,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        ]

    @property
    def map_id(self):
        return self._map_id

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @staticmethod
    def layered_map_layout(wrapper_id, label_id, map_id):
        return html.Div(
            id=wrapper_id,
            style={"visibility": "hidden"},
            children=html.Div(
                style={"margin": "10px"},
                children=[
                    html.Label(style={"textAlign": "center"}, id=label_id),
                    LayeredMap(
                        id=map_id,
                        height=600,
                        layers=[],
                        map_bounds=[[0, 0], [0, 0]],
                        center=[0, 0],
                        hillShading=True,
                    ),
                ],
            ),
        )

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 2fr 2fr 2fr"),
            children=[
                html.Div(
                    style={"zIndex": 2000},
                    children=[
                        self.selector.layout,
                        dash_colorscales.DashColorscales(
                            id="colorscale-picker", nSwatches=256
                        ),
                        html.Pre(id="output"),
                    ],
                ),
                self.layered_map_layout(
                    self._low_map_wrapper_id, self._low_map_label_id, self._low_map_id
                ),
                self.layered_map_layout(
                    self._base_map_wrapper_id,
                    self._base_map_label_id,
                    self._base_map_id,
                ),
                self.layered_map_layout(
                    self._high_map_wrapper_id,
                    self._high_map_label_id,
                    self._high_map_id,
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self._low_map_id, "layers"),
                Output(self._low_map_id, "map_bounds"),
                Output(self._low_map_id, "center"),
                Output(self._low_map_label_id, "children"),
                Output(self._low_map_wrapper_id, "style"),
                Output(self._base_map_id, "layers"),
                Output(self._base_map_id, "map_bounds"),
                Output(self._base_map_id, "center"),
                Output(self._base_map_label_id, "children"),
                Output(self._base_map_wrapper_id, "style"),
                Output(self._high_map_id, "layers"),
                Output(self._high_map_id, "map_bounds"),
                Output(self._high_map_id, "center"),
                Output(self._high_map_label_id, "children"),
                Output(self._high_map_wrapper_id, "style"),
            ],
            [
                Input(self.selector.storage_id, "children"),
                Input("colorscale-picker", "colorscale"),
            ],
        )
        def _set_base_layer(surface, colorscale):

            if not surface:
                raise PreventUpdate

            surface = json.loads(surface)
            ensemble = surface["ensemble"]
            senstype = surface["senstype"]
            sensname = surface["sensname"]
            name = surface["name"]
            attribute = surface["attribute"]
            date = surface["date"]
            senscases = surface["sens_cases"]
            colormap = colors.ListedColormap(colorscale) if colorscale else "viridis"
            if senstype == "mc":
                if not len(senscases) == 1:
                    raise PreventUpdate
                fns = [
                    get_surface_path(
                        self._ensembles, ensemble, real, name, attribute, date
                    )
                    for real in senscases[0]["realizations"]
                ]

                low = set_base_layer(fns, f"{name} - min", "min", colormap)
                base = set_base_layer(fns, f"{name} - mean", "mean", colormap)
                high = set_base_layer(fns, f"{name} - max", "max", colormap)
                return (
                    *low,
                    "Min",
                    {"visibility": "visible"},
                    *base,
                    "Mean",
                    {"visibility": "visible"},
                    *high,
                    "Max",
                    {"visibility": "visible"},
                )
            elif senstype == "scalar":
                output = []
                case_count = 0
                for case in senscases:
                    fns = [
                        get_surface_path(
                            self._ensembles, ensemble, real, name, attribute, date
                        )
                        for real in case["realizations"]
                    ]
                    map_data = set_base_layer(fns, f"{name} - {case['case']}", "mean")
                    output.extend([*map_data, case["case"], {"visibility": "visible"}])
                    case_count += 1
                while case_count < 3:
                    output.extend(
                        [[], [[0, 0], [0, 0]], [0, 0], "", {"visibility": "hidden"}]
                    )
                    case_count += 1
                return output
            else:
                raise PreventUpdate


def get_runpath(ensembles, ensemble, realization):
    """Returns the local runpath for a given ensemble and realization"""
    return Path(
        ensembles.loc[
            (ensembles["ENSEMBLE"] == ensemble) & (ensembles["REAL"] == realization)
        ]["RUNPATH"].item()
    )


def get_surface_stem(name, attribute, date=None):
    """Returns the name of a surface as stored on disk (FMU standard)"""
    return f"{name}--{attribute}--{date}.gri" if date else f"{name}--{attribute}.gri"


def get_surface_path(ensembles, ensemble, realization, name, attribute, date=None):
    """Returns the full path to a surface as stored on disk (FMU standard"""
    return str(
        get_runpath(ensembles, ensemble, realization)
        / "share"
        / "results"
        / "maps"
        / get_surface_stem(name, attribute, date)
    )


def set_base_layer(
    fns, name, aggregation="mean", colormap="viridis", min_value=None, max_value=None
):
    """Given a list of file paths to irap bin surfaces, returns statistical surfaces"""

    # Calculate surface arrays
    surface_stat = calculate_surface_statistics(fns)

    first_real = surface_stat["template"]

    bounds = [
        [np.min(first_real[0]), np.min(first_real[1])],
        [np.max(first_real[0]), np.max(first_real[1])],
    ]

    center = [np.mean(first_real[0]), np.mean(first_real[1])]

    z_arr = surface_stat[aggregation]
    layer = {
        "name": name,
        "checked": True,
        "base_layer": True,
        "data": [
            {
                "allowHillshading": True,
                "type": "image",
                "url": array_to_png(z_arr[2].copy()),
                "colormap": get_colormap(colormap),
                "bounds": bounds,
                "minvalue": min_value if min_value else f"{z_arr[2].min():.2f}",
                "maxvalue": max_value if max_value else f"{z_arr[2].max():.2f}",
            }
        ],
    }
    return [layer], bounds, center
