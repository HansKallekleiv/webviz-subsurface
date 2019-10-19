from uuid import uuid4
from pathlib import Path
import json

import numpy as np
from matplotlib.colors import ListedColormap

import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
import dash_colorscales

from webviz_config import WebvizContainerABC
from webviz_config.webviz_store import webvizstore
from webviz_subsurface_components import LayeredMap
from webviz_subsurface.datainput.layeredmap._image_processing import (
    get_colormap,
    array_to_png,
)

from webviz_config.common_cache import CACHE
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
        self.config = find_surfaces(
            ensemble_paths=self.ens_paths, suffix="*.gri", delimiter="--"
        )

        # Extract realizations and sensitivity information
        self._ensembles = get_realizations(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )

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
        self._color_scale_id = f"{str(uuid4())}-color-scale-id"
        self._min_color_id = f"{str(uuid4())}-min-color-id"
        self._max_color_id = f"{str(uuid4())}-max-color-id"
        self.selector = SurfaceSelector(app, self.config, self._ensembles)
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
            ),
            (
                find_surfaces,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "suffix": "*.gri",
                        "delimiter": "--",
                    }
                ],
            ),
            (
                get_path,
                [
                    {"path": Path(path)}
                    for path in list(self.config["runpath"].unique())
                ],
            ),
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

    def layered_map_layout(self, wrapper_id, label_id, map_id):
        return html.Div(
            id=wrapper_id,
            style={"visibility": "hidden"},
            children=html.Div(
                style={"margin": "10px"},
                children=[
                    html.Label(style={"textAlign": "center"}, id=label_id),
                    LayeredMap(
                        id=map_id,
                        sync_ids=[
                            self._low_map_id,
                            self._base_map_id,
                            self._high_map_id,
                        ],
                        height=600,
                        layers=[],
                        hillShading=True,
                    ),
                ],
            ),
        )

    @property
    def color_control(self):
        return html.Div(
            style={"fontSize": "12px", "marginLeft": "25px"},
            children=[
                html.Label("Color settings"),
                html.Div(
                    style={"zIndex": 2000},
                    children=[
                        dash_colorscales.DashColorscales(
                            id=self._color_scale_id, nSwatches=256
                        )
                    ],
                ),
                html.Div(
                    style=self.set_grid_layout("1fr 1fr"),
                    children=[
                        html.Label("Min"),
                        html.Label("Max"),
                        dcc.Input(
                            id=self._min_color_id,
                            debounce=True,
                            placeholder="Using surface min",
                        ),
                        dcc.Input(
                            id=self._max_color_id,
                            debounce=True,
                            placeholder="Using surface max",
                        ),
                    ],
                ),
            ],
        )

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 2fr 2fr 2fr"),
            children=[
                html.Div(children=[self.selector.layout, self.color_control]),
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
                Output(self._low_map_label_id, "children"),
                Output(self._low_map_wrapper_id, "style"),
                Output(self._base_map_id, "layers"),
                Output(self._base_map_label_id, "children"),
                Output(self._base_map_wrapper_id, "style"),
                Output(self._high_map_id, "layers"),
                Output(self._high_map_label_id, "children"),
                Output(self._high_map_wrapper_id, "style"),
            ],
            [
                Input(self.selector.storage_id, "children"),
                Input(self._color_scale_id, "colorscale"),
                Input(self._min_color_id, "value"),
                Input(self._max_color_id, "value"),
            ],
        )
        def _set_base_layer(selection, colorscale, min_color, max_color):
            if not selection:
                raise PreventUpdate
            print(min_color)
            selection = json.loads(selection)
            ensemble = selection["ensemble"]
            senstype = selection["senstype"]
            sensname = selection["sensname"]
            name = selection["name"]
            attribute = selection["attribute"]
            date = selection["date"]
            senscases = selection["sens_cases"]
            reference = selection["reference"]
            mode = selection["mode"]

            colormap = ListedColormap(colorscale) if colorscale else "viridis"

            if senstype == "mc":
                if not len(senscases) == 1:
                    raise PreventUpdate
                surfaces = calculate_surface_statistics(
                    [
                        get_surface_path(
                            self._ensembles, ensemble, real, name, attribute, date
                        )
                        for real in senscases[0]["realizations"]
                    ]
                )
                if mode == "relative":
                    ref_mean = calculate_surface_statistics(
                        [
                            get_surface_path(
                                self._ensembles, ensemble, real, name, attribute, date
                            )
                            for real in reference["realizations"]
                        ]
                    )["mean"]
                    low = surfaces["min"]
                    low[2] = low[2].copy() - ref_mean[2].copy()
                    base = ref_mean
                    high = surfaces["max"]
                    high[2] = high[2].copy() - ref_mean[2].copy()

                    low = set_base_layer(
                        low,
                        f"{name} - min",
                        colormap=colormap,
                        min_color=min_color,
                        max_color=max_color,
                    )
                    base = set_base_layer(
                        base,
                        f"{name} - mean",
                        colormap=colormap,
                        min_color=min_color,
                        max_color=max_color,
                    )
                    high = set_base_layer(
                        high,
                        f"{name} - max",
                        colormap=colormap,
                        min_color=min_color,
                        max_color=max_color,
                    )
                    return (
                        low,
                        "Low - reference mean",
                        {"visibility": "visible"},
                        base,
                        "Reference mean",
                        {"visibility": "visible"},
                        high,
                        "High - Reference mean",
                        {"visibility": "visible"},
                    )
                else:
                    low = surfaces["min"]
                    base = surfaces["mean"]
                    high = surfaces["max"]

                    low = set_base_layer(
                        low,
                        f"{name} - min",
                        colormap=colormap,
                        min_color=min_color,
                        max_color=max_color,
                    )
                    base = set_base_layer(
                        base,
                        f"{name} - mean",
                        colormap=colormap,
                        min_color=min_color,
                        max_color=max_color,
                    )
                    high = set_base_layer(
                        high,
                        f"{name} - max",
                        colormap=colormap,
                        min_color=min_color,
                        max_color=max_color,
                    )
                    return (
                        low,
                        "Low",
                        {"visibility": "visible"},
                        base,
                        "Mean",
                        {"visibility": "visible"},
                        high,
                        "High",
                        {"visibility": "visible"},
                    )
            elif senstype == "scalar":
                if len(senscases) == 2:

                    case1_mean = calculate_surface_statistics(
                        [
                            get_surface_path(
                                self._ensembles, ensemble, real, name, attribute, date
                            )
                            for real in senscases[0]["realizations"]
                        ]
                    )["mean"]
                    case2_mean = calculate_surface_statistics(
                        [
                            get_surface_path(
                                self._ensembles, ensemble, real, name, attribute, date
                            )
                            for real in senscases[1]["realizations"]
                        ]
                    )["mean"]

                    if mode == "relative":
                        ref_mean = calculate_surface_statistics(
                            [
                                get_surface_path(
                                    self._ensembles,
                                    ensemble,
                                    real,
                                    name,
                                    attribute,
                                    date,
                                )
                                for real in reference["realizations"]
                            ]
                        )["mean"]
                        case1_mean[2] = case1_mean[2].copy() - ref_mean[2].copy()
                        case2_mean[2] = case2_mean[2].copy() - ref_mean[2].copy()
                        low = set_base_layer(
                            case1_mean,
                            f"{name} - min",
                            colormap=colormap,
                            min_color=min_color,
                            max_color=max_color,
                        )
                        base = set_base_layer(
                            ref_mean,
                            f"{name} - mean",
                            colormap=colormap,
                            min_color=min_color,
                            max_color=max_color,
                        )
                        high = set_base_layer(
                            case2_mean,
                            f"{name} - max",
                            colormap=colormap,
                            min_color=min_color,
                            max_color=max_color,
                        )
                        return (
                            low,
                            f"{senscases[0]['case']} - reference mean",
                            {"visibility": "visible"},
                            base,
                            "Reference mean",
                            {"visibility": "visible"},
                            high,
                            f"{senscases[1]['case']} - reference mean",
                            {"visibility": "visible"},
                        )
                    else:
                        low = set_base_layer(
                            case1_mean,
                            f"{name} - min",
                            colormap=colormap,
                            min_color=min_color,
                            max_color=max_color,
                        )
                        high = set_base_layer(
                            case2_mean,
                            f"{name} - max",
                            colormap=colormap,
                            min_color=min_color,
                            max_color=max_color,
                        )
                        return (
                            low,
                            f"{senscases[0]['case']}",
                            {"visibility": "visible"},
                            high,
                            f"{senscases[1]['case']}",
                            {"visibility": "visible"},
                            [],
                            "",
                            {"visibility": "hidden"},
                        )
                if len(senscases) == 1:
                    case1_mean = calculate_surface_statistics(
                        [
                            get_surface_path(
                                self._ensembles, ensemble, real, name, attribute, date
                            )
                            for real in senscases[0]["realizations"]
                        ]
                    )["mean"]
                    if mode == "relative":
                        ref_mean = calculate_surface_statistics(
                            [
                                get_surface_path(
                                    self._ensembles,
                                    ensemble,
                                    real,
                                    name,
                                    attribute,
                                    date,
                                )
                                for real in reference["realizations"]
                            ]
                        )["mean"]
                        case1_mean[2] = case1_mean[2].copy() - ref_mean[2].copy()
                        low = set_base_layer(
                            case1_mean,
                            f"{name} - min",
                            colormap=colormap,
                            min_color=min_color,
                            max_color=max_color,
                        )
                        base = set_base_layer(
                            ref_mean,
                            f"{name} - mean",
                            colormap=colormap,
                            min_color=min_color,
                            max_color=max_color,
                        )
                        return (
                            low,
                            f"{senscases[0]['case']} - reference mean",
                            {"visibility": "visible"},
                            base,
                            "Reference mean",
                            {"visibility": "visible"},
                            [],
                            "",
                            {"visibility": "hidden"},
                        )
                    else:
                        low = set_base_layer(
                            case1_mean,
                            f"{name} - min",
                            colormap=colormap,
                            min_color=min_color,
                            max_color=max_color,
                        )

                        return (
                            low,
                            f"{senscases[0]['case']}",
                            {"visibility": "visible"},
                            [],
                            "",
                            {"visibility": "hidden"},
                            [],
                            "",
                            {"visibility": "hidden"},
                        )
                else:
                    raise PreventUpdate
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
        get_path(
            Path(
                get_runpath(ensembles, ensemble, realization)
                / "share"
                / "results"
                / "maps"
                / get_surface_stem(name, attribute, date)
            )
        )
    )


@webvizstore
def get_path(path) -> Path:
    return path


def set_base_layer(surface, name, colormap="viridis", min_color=None, max_color=None):
    """Given a list of file paths to irap bin surfaces, returns statistical surfaces"""

    # Calculate surface arrays

    bounds = [
        [np.min(surface[0]), np.min(surface[1])],
        [np.max(surface[0]), np.max(surface[1])],
    ]

    center = [np.mean(surface[0]), np.mean(surface[1])]
    layer = {
        "name": name,
        "checked": True,
        "base_layer": True,
        "data": [
            {
                "allowHillshading": True,
                "type": "image",
                "url": array_to_png(surface[2].copy()),
                "colormap": get_colormap(colormap),
                "bounds": bounds,
                "minvalue": min_color if min_color else f"{surface[2].min():.2f}",
                "maxvalue": max_color if max_color else f"{surface[2].max():.2f}",
            }
        ],
    }
    return [layer]
