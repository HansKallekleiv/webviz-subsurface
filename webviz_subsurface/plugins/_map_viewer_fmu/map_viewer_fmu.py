import io
import json
from pathlib import Path
from typing import Callable, List, Tuple, Union

from flask import send_file
import pandas as pd
import webviz_core_components as wcc
from webviz_core_components.wrapped_components.flexbox import FlexBox
import xtgeo
from dash import (
    Dash,
    Input,
    Output,
    State,
    callback_context,
    dcc,
    html,
    callback,
    no_update,
)
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils._dash_component_utils import calculate_slider_step
from webviz_config.webviz_store import webvizstore
from webviz_subsurface_components import LeafletMap

from webviz_subsurface._datainput.fmu_input import find_surfaces, get_realizations
from webviz_subsurface._datainput.well import make_well_layers
from webviz_subsurface._models import SurfaceLeafletModel, SurfaceSetModel
from webviz_subsurface._private_plugins.surface_selector import SurfaceSelector


from ._deckgl_map_aio import DeckGLMapAIO
from ._flask_routes import set_routes
from .xtgeo_utils import XtgeoSurfaceArray


class MapViewerFMU(WebvizPluginABC):
    """"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        attributes: list = None,
        attribute_settings: dict = None,
        wellfolder: Path = None,
        wellsuffix: str = ".w",
        map_height: int = 600,
    ):

        super().__init__()
        self._app = app
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

        # Find surfaces
        self._surface_table = find_surfaces(self.ens_paths)

        # Extract realizations and sensitivity information
        self.ens_df = get_realizations(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )

        # Drop any ensembles that does not have surfaces
        self.ens_df = self.ens_df.loc[
            self.ens_df["ENSEMBLE"].isin(self._surface_table["ENSEMBLE"].unique())
        ]

        if attributes is not None:
            self._surface_table = self._surface_table[
                self._surface_table["attribute"].isin(attributes)
            ]
            if self._surface_table.empty:
                raise ValueError("No surfaces found with the given attributes")
        self._surface_ensemble_set_model = {
            ens: SurfaceSetModel(surf_ens_df)
            for ens, surf_ens_df in self._surface_table.groupby("ENSEMBLE")
        }
        self.attribute_settings: dict = attribute_settings if attribute_settings else {}
        self.map_height = map_height
        self.surfaceconfig = surfacedf_to_dict(self._surface_table)
        self.wellfolder = wellfolder
        self.wellsuffix = wellsuffix
        self.wellfiles: Union[List[str], None] = (
            json.load(find_files(wellfolder, wellsuffix))
            if wellfolder is not None
            else None
        )
        self.well_layer = (
            make_well_layers([get_path(wellfile) for wellfile in self.wellfiles])
            if self.wellfiles
            else None
        )

        self.selector = SurfaceSelector(app, self.surfaceconfig, ensembles)

        self.set_callbacks(app)
        set_routes(app, self._surface_ensemble_set_model)

    @property
    def ensembles(self) -> List[str]:
        return list(self.ens_df["ENSEMBLE"].unique())

    def realizations(
        self, ensemble: str, sensname: str = None, senstype: str = None
    ) -> List[str]:
        df = self.ens_df.loc[self.ens_df["ENSEMBLE"] == ensemble].copy()
        if sensname and senstype:
            df = df.loc[(df["SENSNAME"] == sensname) & (df["SENSCASE"] == senstype)]
        return list(df["REAL"]) + ["Mean", "StdDev", "Min", "Max"]

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard to compare surfaces from a FMU ensemble. "
                    "The two left views can be set independently, while the right "
                    "view shows a calculated surface."
                ),
            },
            {
                "id": self.uuid("settings-view1"),
                "content": ("Settings for the first map view"),
            },
        ]

    def ensemble_layout(
        self,
        ensemble_id: str,
        ens_prev_id: str,
        ens_next_id: str,
        real_id: str,
        real_prev_id: str,
        real_next_id: str,
    ) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    [
                        html.Label("Ensemble"),
                        html.Div(
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "12fr 1fr 1fr",
                            },
                            children=[
                                dcc.Dropdown(
                                    style={"flex": 5},
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in self.ensembles
                                    ],
                                    value=self.ensembles[0],
                                    id=ensemble_id,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="session",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                        "flex": 1,
                                    },
                                    id=ens_prev_id,
                                    children="⬅",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                        "flex": 1,
                                    },
                                    id=ens_next_id,
                                    children="➡",
                                ),
                            ],
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Label("Realization / Statistic"),
                        html.Div(
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "6fr 1fr 1fr",
                            },
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": real, "value": real}
                                        for real in self.realizations(self.ensembles[0])
                                    ],
                                    value=self.realizations(self.ensembles[0])[0],
                                    id=real_id,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="session",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=real_prev_id,
                                    children="⬅",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=real_next_id,
                                    children="➡",
                                ),
                            ],
                        ),
                    ]
                ),
            ]
        )

    @property
    def layout(self) -> html.Div:
        return html.Div(
            id=self.uuid("layout"),
            children=[
                wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            style={"flex": 1, "height": "90vh"},
                            id=self.uuid("settings-view1"),
                            children=[
                                wcc.Selectors(
                                    label="Surface data",
                                    children=[
                                        self.selector.layout,
                                        self.ensemble_layout(
                                            ensemble_id=self.uuid("ensemble"),
                                            ens_prev_id=self.uuid("ensemble-prev"),
                                            ens_next_id=self.uuid("ensemble-next"),
                                            real_id=self.uuid("realization"),
                                            real_prev_id=self.uuid("realization-prev"),
                                            real_next_id=self.uuid("realization-next"),
                                        ),
                                    ],
                                ),
                                wcc.Selectors(
                                    label="Surface coloring",
                                    children=[
                                        wcc.Dropdown(
                                            label="Colormap",
                                            id=self.uuid("colormap-select"),
                                            options=[
                                                {"label": name, "value": name}
                                                for name in ["viridis_r", "seismic"]
                                            ],
                                            value="viridis_r",
                                            clearable=False,
                                        ),
                                        wcc.RangeSlider(
                                            label="Value range",
                                            id=self.uuid("colormap-range"),
                                            updatemode="drag",
                                            tooltip={
                                                "always_visible": True,
                                                "placement": "bottomLeft",
                                            },
                                        ),
                                        wcc.Checklist(
                                            id=self.uuid("colormap-range-keep"),
                                            options=[
                                                {
                                                    "label": "Keep range",
                                                    "value": "keep",
                                                }
                                            ],
                                        ),
                                        html.Button(
                                            "Reset range",
                                            style={"marginTop": "5px"},
                                            id=self.uuid("colormap-range-reset"),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        wcc.Frame(
                            style={
                                "flex": 5,
                            },
                            children=[
                                DeckGLMapAIO(
                                    app=self._app, aio_id=self.uuid("mapview")
                                ),
                            ],
                        ),
                        dcc.Store(
                            id=self.uuid("attribute-settings"),
                            data=json.dumps(self.attribute_settings),
                            storage_type="session",
                        ),
                        dcc.Store(
                            id=self.uuid("surface-geometry"),
                            data={
                                "mapImage": f"/surface/undef.png",
                                "mapBounds": [0, 1, 0, 1],
                                "mapRange": [0, 1],
                                "mapTarget": [0.5, 0.5, 0],
                            },
                        ),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        @callback(
            Output(self.uuid("surface-geometry"), "data"),
            Input(self.selector.storage_id, "data"),
            Input(self.uuid("ensemble"), "value"),
            Input(self.uuid("realization"), "value"),
            Input(self.uuid("attribute-settings"), "data"),
        )
        def _set_stored_surface_geometry(
            stored_selector_data: str,
            ensemble: str,
            real: str,
            stored_attribute_settings: str,
        ):
            ctx = callback_context.triggered

            if not ctx or not stored_selector_data:
                raise PreventUpdate

            data: dict = json.loads(stored_selector_data)
            if not isinstance(data, dict):
                raise TypeError("Selector data payload must be of type dict")
            attribute_settings: dict = json.loads(stored_attribute_settings)
            if not isinstance(attribute_settings, dict):
                raise TypeError("Expected stored attribute_settings to be of type dict")

                # if real in ["Mean", "StdDev", "Min", "Max"]:
                #     surface = self._surface_ensemble_set_model[
                #         ensemble
                #     ].calculate_statistical_surface(**data, calculation=real)

                # else:
            surface_id = self._surface_ensemble_set_model[
                ensemble
            ].get_id_from_selections(**data, realization=int(real))
            surface = self._surface_ensemble_set_model[
                ensemble
            ].get_realization_surface(**data, realization=int(real))
            surface_data = XtgeoSurfaceArray(surface.copy())
            return {
                "mapImage": f"/surface/{ensemble}/{surface_id}.png",
                "mapBounds": surface_data.map_bounds,
                "mapRange": [surface_data.min_val, surface_data.max_val],
                "mapTarget": surface_data.view_target,
            }

        @callback(
            Output(DeckGLMapAIO.ids.map(self.uuid("mapview")), "resources"),
            Input(self.uuid("surface-geometry"), "data"),
            State(DeckGLMapAIO.ids.map(self.uuid("mapview")), "resources"),
        )
        def _update_deckgl_resources(
            surface_geometry,
            current_resources,
        ):
            current_resources.update(**surface_geometry)
            return current_resources

        @callback(
            Output(DeckGLMapAIO.ids.colormap_image(self.uuid("mapview")), "data"),
            Input(self.uuid("colormap-select"), "value"),
        )
        def _update_color_map_image(colormap):
            return colormap

        @callback(
            Output(DeckGLMapAIO.ids.colormap_range(self.uuid("mapview")), "data"),
            Input(self.uuid("colormap-range"), "value"),
        )
        def _update_color_map_range(colormap_range):
            return colormap_range

        @callback(
            Output(self.uuid("colormap-range"), "min"),
            Output(self.uuid("colormap-range"), "max"),
            Output(self.uuid("colormap-range"), "step"),
            Output(self.uuid("colormap-range"), "value"),
            Output(self.uuid("colormap-range"), "marks"),
            Input(self.uuid("surface-geometry"), "data"),
            Input(self.uuid("colormap-range-keep"), "value"),
            Input(self.uuid("colormap-range-reset"), "n_clicks"),
            State(self.uuid("colormap-range"), "value"),
        )
        def _update_colormap_range(surface_geometry, keep, reset, current_val):
            ctx = callback_context.triggered[0]["prop_id"]

            min_val = surface_geometry["mapRange"][0]
            max_val = surface_geometry["mapRange"][1]
            if ctx == ".":
                value = no_update
            if "colormap-range-reset" in ctx or not keep or current_val is None:
                value = [min_val, max_val]
            else:
                value = current_val

            return (
                min_val,
                max_val,
                calculate_slider_step(min_value=min_val, max_value=max_val, steps=100),
                value,
                {
                    str(min_val): {"label": f"{min_val:.2f}"},
                    str(max_val): {"label": f"{max_val:.2f}"},
                },
            )

        def _update_from_btn(
            _n_prev: int, _n_next: int, current_value: str, options: List[dict]
        ) -> str:
            """Updates dropdown value if previous/next btn is clicked"""
            option_values: List[str] = [opt["value"] for opt in options]
            ctx = callback_context.triggered
            if not ctx or current_value is None:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if "-prev" in callback:
                return prev_value(current_value, option_values)
            if "-next" in callback:
                return next_value(current_value, option_values)
            return current_value

        for btn_name in ["ensemble", "realization", "ensemble2", "realization2"]:
            callback(
                Output(self.uuid(f"{btn_name}"), "value"),
                [
                    Input(self.uuid(f"{btn_name}-prev"), "n_clicks"),
                    Input(self.uuid(f"{btn_name}-next"), "n_clicks"),
                ],
                [
                    State(self.uuid(f"{btn_name}"), "value"),
                    State(self.uuid(f"{btn_name}"), "options"),
                ],
            )(_update_from_btn)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        store_functions: List[Tuple[Callable, list]] = [
            (
                find_surfaces,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "suffix": "*.gri",
                        "delimiter": "--",
                    }
                ],
            )
        ]
        for ens in list(self.ens_df["ENSEMBLE"].unique()):
            for calculation in ["Mean", "StdDev", "Min", "Max"]:
                store_functions.append(
                    self._surface_ensemble_set_model[
                        ens
                    ].webviz_store_statistical_calculation(calculation=calculation)
                )
            store_functions.append(
                self._surface_ensemble_set_model[
                    ens
                ].webviz_store_realization_surfaces()
            )

        if self.wellfolder is not None:
            store_functions.append(
                (find_files, [{"folder": self.wellfolder, "suffix": self.wellsuffix}])
            )
        if self.wellfiles is not None:
            store_functions.extend(
                [(get_path, [{"path": fn}]) for fn in self.wellfiles]
            )
        store_functions.append(
            (
                get_realizations,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        )
        return store_functions


@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)


def prev_value(current_value: str, options: List[str]) -> str:
    try:
        index = options.index(current_value)
        return options[max(0, index - 1)]
    except ValueError:
        return current_value


def next_value(current_value: str, options: List[str]) -> str:
    try:
        index = options.index(current_value)
        return options[min(len(options) - 1, index + 1)]

    except ValueError:
        return current_value


def surfacedf_to_dict(df: pd.DataFrame) -> dict:
    return {
        attr: {
            "names": list(dframe["name"].unique()),
            "dates": list(dframe["date"].unique())
            if "date" in dframe.columns
            else None,
        }
        for attr, dframe in df.groupby("attribute")
    }


@webvizstore
def find_files(folder: Path, suffix: str) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in folder.glob(f"*{suffix}")])
        ).encode()
    )


def calculate_surface_difference(
    surface: xtgeo.RegularSurface,
    surface2: xtgeo.RegularSurface,
    calculation: str = "Difference",
) -> xtgeo.RegularSurface:
    if calculation == "Difference":
        calculated_surface = surface - surface2
    elif calculation == "Sum":
        calculated_surface = surface + surface2
    elif calculation == "Product":
        calculated_surface = surface * surface2
    elif calculation == "Quotient":
        calculated_surface = surface / surface2
    return calculated_surface
