from uuid import uuid4
from pathlib import Path
import json
import io

import numpy as np
import xtgeo
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap

from webviz_subsurface._datainput.fmu_input import get_realizations, find_surfaces
from webviz_subsurface._datainput.surface import make_surface_layer, load_surface
from webviz_subsurface._datainput.well import make_well_layers
from webviz_subsurface._private_plugins.surface_selector import SurfaceSelector


class SurfaceViewerFMU(WebvizPluginABC):
    """### SurfaceViewerFMU

A plugin to covisualize surfaces from an ensemble.
There are 3 separate map views. 2 views can be set independently, while
the 3rd view displays the resulting map by combining the other maps e.g.
by taking the difference or summing the values.

There is flexibility in which combinations of surfaces that are displayed
and calculated, such that surfaces can e.g. be compared across ensembles.

The available maps are gathered from the `share/results/maps/` folder
for each realization. Statistical calculations across the ensemble(s) are
done on the fly. If the ensemble or surfaces have a large size it is recommended
to run webviz in `portable` mode so that the statistical surfaces are pre-calculated
and available for instant viewing.

* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `attributes`: List of surface attributes to include, if not given
                all surface attributes will be included.
* `attribute_settings`: Dictionary with setting for each attribute.
                Available settings are 'min' and 'max' to truncate colorscale,
                as well as 'color' to set the colormap (default is viridis).
* `wellfolder`: Folder with RMS wells
* `wellsuffix`: File suffix for wells in well folder.
"""

    def __init__(
        self,
        app,
        ensembles,
        attributes: list = None,
        attribute_settings: dict = None,
        wellfolder: Path = None,
        wellsuffix: str = ".w",
    ):

        super().__init__()
        self.ens_paths = {
            ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
            for ens in ensembles
        }

        # Find surfaces
        self.surfacedf = find_surfaces(self.ens_paths)
        if attributes is not None:
            self.surfacedf = self.surfacedf[
                self.surfacedf["attribute"].isin(attributes)
            ]
            if self.surfacedf.empty:
                raise ValueError("No surfaces found with the given attributes")
        self.attribute_settings = attribute_settings if attribute_settings else {}
        self.surfaceconfig = surfacedf_to_dict(self.surfacedf)
        self.wellfolder = wellfolder
        self.wellsuffix = wellsuffix
        self.wellfiles = (
            json.load(find_files(wellfolder, wellsuffix))
            if wellfolder is not None
            else None
        )
        self.well_layer = make_well_layers(self.wellfiles) if self.wellfiles else None
        # Extract realizations and sensitivity information
        self.ens_df = get_realizations(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )
        self._storage_id = f"{str(uuid4())}-surface-viewer"
        self._map_id = f"{str(uuid4())}-map-id"
        self.selector = SurfaceSelector(app, self.surfaceconfig, ensembles)
        self.selector2 = SurfaceSelector(app, self.surfaceconfig, ensembles)

        self.set_callbacks(app)

    @property
    def ensembles(self):
        return list(self.ens_df["ENSEMBLE"].unique())

    def realizations(self, ensemble, sensname=None, senstype=None):
        df = self.ens_df.loc[self.ens_df["ENSEMBLE"] == ensemble].copy()
        if sensname and senstype:
            df = df.loc[(df["SENSNAME"] == sensname) & (df["SENSCASE"] == senstype)]
        reals = list(df["REAL"])
        reals.extend(["Mean", "StdDev", "Min", "Max"])
        return reals

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

    def ensemble_layout(
        self, ensemble_id, ens_prev_id, ens_next_id, real_id, real_prev_id, real_next_id
    ):
        return wcc.FlexBox(
            children=[
                html.Div(
                    [
                        html.Label("Ensemble"),
                        html.Div(
                            style=self.set_grid_layout("12fr 1fr 1fr"),
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in self.ensembles
                                    ],
                                    value=self.ensembles[0],
                                    id=ensemble_id,
                                    clearable=False,
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "1rem",
                                        "padding": "10px",
                                        "textTransform": "none",
                                    },
                                    id=ens_prev_id,
                                    children="Prev",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "1rem",
                                        "padding": "10px",
                                        "textTransform": "none",
                                    },
                                    id=ens_next_id,
                                    children="Next",
                                ),
                            ],
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Label("Realization / Statistic"),
                        html.Div(
                            style=self.set_grid_layout("12fr 1fr 1fr"),
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": real, "value": real}
                                        for real in self.realizations(self.ensembles[0])
                                    ],
                                    value=self.realizations(self.ensembles[0])[0],
                                    id=real_id,
                                    clearable=False,
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "1rem",
                                        "padding": "10px",
                                        "textTransform": "none",
                                    },
                                    id=real_prev_id,
                                    children="Prev",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "1rem",
                                        "padding": "10px",
                                        "textTransform": "none",
                                    },
                                    id=real_next_id,
                                    children="Next",
                                ),
                            ],
                        ),
                    ]
                ),
            ]
        )

    @property
    def layout(self):
        return html.Div(
            [
                wcc.FlexBox(
                    style={"fontSize": "1rem"},
                    children=[
                        html.Div(
                            style={"margin": "10px", "flex": 4},
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
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                self.selector2.layout,
                                self.ensemble_layout(
                                    ensemble_id=self.uuid("ensemble2"),
                                    ens_prev_id=self.uuid("ensemble2-prev"),
                                    ens_next_id=self.uuid("ensemble2-next"),
                                    real_id=self.uuid("realization2"),
                                    real_prev_id=self.uuid("realization2-prev"),
                                    real_next_id=self.uuid("realization2-next"),
                                ),
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                html.Label("Calculation"),
                                html.Div(
                                    dcc.Dropdown(
                                        id=self.uuid("calculation"),
                                        value="Difference",
                                        clearable=False,
                                        options=[
                                            {"label": i, "value": i}
                                            for i in [
                                                "Difference",
                                                "Sum",
                                                "Product",
                                                "Quotient",
                                            ]
                                        ],
                                    )
                                ),
                                html.Label("Truncate Min / Max"),
                                wcc.FlexBox(
                                    children=[
                                        dcc.Input(
                                            debounce=True,
                                            type="number",
                                            id=self.uuid("truncate-diff-min"),
                                            style={"maxWidth": "20%"},
                                        ),
                                        dcc.Input(
                                            debounce=True,
                                            type="number",
                                            id=self.uuid("truncate-diff-max"),
                                            style={"maxWidth": "20%"},
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
                wcc.FlexBox(
                    style={"fontSize": "1rem"},
                    children=[
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                LayeredMap(
                                    sync_ids=[self.uuid("map2"), self.uuid("map3")],
                                    id=self.uuid("map"),
                                    height=600,
                                    layers=[],
                                    hillShading=True,
                                )
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                LayeredMap(
                                    sync_ids=[self.uuid("map"), self.uuid("map3")],
                                    id=self.uuid("map2"),
                                    height=600,
                                    layers=[],
                                    hillShading=True,
                                )
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                LayeredMap(
                                    sync_ids=[self.uuid("map"), self.uuid("map2")],
                                    id=self.uuid("map3"),
                                    height=600,
                                    layers=[],
                                    hillShading=True,
                                )
                            ],
                        ),
                        dcc.Store(
                            id=self.uuid("attribute-settings"),
                            data=json.dumps(self.attribute_settings),
                        ),
                    ],
                ),
            ]
        )

    def get_runpath(self, data, ensemble, real):
        data = make_fmu_filename(data)
        runpath = Path(
            self.ens_df.loc[
                (self.ens_df["ENSEMBLE"] == ensemble) & (self.ens_df["REAL"] == real)
            ]["RUNPATH"].unique()[0]
        )

        return str(
            get_path(str(runpath / "share" / "results" / "maps" / f"{data}.gri"))
        )

    def get_ens_runpath(self, data, ensemble):
        data = make_fmu_filename(data)
        runpaths = self.ens_df.loc[(self.ens_df["ENSEMBLE"] == ensemble)][
            "RUNPATH"
        ].unique()
        return [
            str((Path(runpath) / "share" / "results" / "maps" / f"{data}.gri"))
            for runpath in runpaths
        ]

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.uuid("map"), "layers"),
                Output(self.uuid("map2"), "layers"),
                Output(self.uuid("map3"), "layers"),
            ],
            [
                Input(self.selector.storage_id, "children"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("realization"), "value"),
                Input(self.selector2.storage_id, "children"),
                Input(self.uuid("ensemble2"), "value"),
                Input(self.uuid("realization2"), "value"),
                Input(self.uuid("calculation"), "value"),
                Input(self.uuid("attribute-settings"), "data"),
                Input(self.uuid("truncate-diff-min"), "value"),
                Input(self.uuid("truncate-diff-max"), "value"),
            ],
        )
        # pylint: disable=too-many-arguments, too-many-locals
        def _set_base_layer(
            data,
            ensemble,
            real,
            data2,
            ensemble2,
            real2,
            calculation,
            attribute_settings,
            diff_min,
            diff_max,
        ):
            if not data or not data2:
                raise PreventUpdate
            data = json.loads(data)
            data2 = json.loads(data2)
            attribute_settings = json.loads(attribute_settings)

            if real in ["Mean", "StdDev", "Min", "Max"]:
                surface = calculate_surface(self.get_ens_runpath(data, ensemble), real)

            else:
                surface = load_surface(self.get_runpath(data, ensemble, real))
            if real2 in ["Mean", "StdDev", "Min", "Max"]:
                surface2 = calculate_surface(
                    self.get_ens_runpath(data2, ensemble2), real2
                )

            else:
                surface2 = load_surface(self.get_runpath(data2, ensemble2, real2))

            surface_layer = make_surface_layer(
                surface,
                name="surface",
                color=attribute_settings.get(data["attr"], {}).get("color", "viridis"),
                min_val=attribute_settings.get(data["attr"], {}).get("min", None),
                max_val=attribute_settings.get(data["attr"], {}).get("max", None),
                hillshading=True,
            )
            surface_layer2 = make_surface_layer(
                surface2,
                name="surface",
                color=attribute_settings.get(data2["attr"], {}).get("color", "viridis"),
                min_val=attribute_settings.get(data2["attr"], {}).get("min", None),
                max_val=attribute_settings.get(data2["attr"], {}).get("max", None),
                hillshading=True,
            )

            surface3 = surface.copy()
            try:
                values = surface3.values.copy()
                if calculation == "Difference":
                    values = values - surface2.values
                if calculation == "Sum":
                    values = values + surface2.values
                if calculation == "Product":
                    values = values * surface2.values
                if calculation == "Quotient":
                    values = values / surface2.values
                if diff_min is not None:
                    values[values <= diff_min] = diff_min
                if diff_max is not None:
                    values[values >= diff_max] = diff_max
                surface3.values = values.copy()
                diff_layers = [
                    make_surface_layer(
                        surface3,
                        name="surface",
                        color=attribute_settings.get(data["attr"], {}).get(
                            "color", "viridis"
                        ),
                        hillshading=True,
                    ),
                    self.well_layer,
                ]

            except ValueError:
                diff_layers = [self.well_layer]
            return (
                [surface_layer, self.well_layer],
                [surface_layer2, self.well_layer],
                diff_layers,
            )

        def _update_from_btn(_n_prev, _n_next, current_value, options):
            """Updates dropdown value if previous/next btn is clicked"""
            options = [opt["value"] for opt in options]
            ctx = dash.callback_context.triggered
            if not ctx or current_value is None:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if "-prev" in callback:
                return prev_value(current_value, options)
            if "-next" in callback:
                return next_value(current_value, options)
            return current_value

        for btn_name in ["ensemble", "realization", "ensemble2", "realization2"]:
            app.callback(
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

    def add_webvizstore(self):
        store_functions = [
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

        filenames = []
        # Generate all file names
        for attr, values in self.surfaceconfig.items():
            for name in values["names"]:
                for date in values["dates"]:
                    filename = f"{name}--{attr}"
                    if date is not None:
                        filename += f"--{date}"
                    filename += f".gri"
                    filenames.append(filename)

        # Copy all realization files
        for runpath in self.ens_df["RUNPATH"].unique():
            for filename in filenames:
                path = Path(runpath) / "share" / "results" / "maps" / filename
                if path.exists():
                    store_functions.append((get_path, [{"path": str(path)}]))

        # Calculate and store statistics
        for _, ens_df in self.ens_df.groupby("ENSEMBLE"):
            runpaths = list(ens_df["RUNPATH"].unique())
            for filename in filenames:
                paths = [
                    str(Path(runpath) / "share" / "results" / "maps" / filename)
                    for runpath in runpaths
                ]
                for statistic in ["Mean", "StdDev", "Min", "Max"]:
                    store_functions.append(
                        (save_surface, [{"fns": paths, "statistic": statistic}])
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


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_surface(fns, statistic):
    return surface_from_json(json.load(save_surface(fns, statistic)))


@webvizstore
def save_surface(fns, statistic) -> io.BytesIO:
    surfaces = xtgeo.Surfaces(fns)
    if len(surfaces.surfaces) == 0:
        surface = xtgeo.RegularSurface()
    if statistic == "Mean":
        surface = surfaces.apply(np.nanmean, axis=0)
    if statistic == "StdDev":
        surface = surfaces.apply(np.nanstd, axis=0)
    if statistic == "Min":
        surface = surfaces.apply(np.nanmin, axis=0)
    if statistic == "Max":
        surface = surfaces.apply(np.nanmax, axis=0)
    if statistic == "P10":
        surface = surfaces.apply(np.nanpercentile, 10, axis=0)
    if statistic == "P90":
        surface = surfaces.apply(np.nanpercentile, 90, axis=0)

    return io.BytesIO(surface_to_json(surface).encode())


def surface_to_json(surface):
    return json.dumps(
        {
            "ncol": surface.ncol,
            "nrow": surface.nrow,
            "xori": surface.xori,
            "yori": surface.yori,
            "rotation": surface.rotation,
            "xinc": surface.xinc,
            "yinc": surface.yinc,
            "values": surface.values.copy().filled(np.nan).tolist(),
        }
    )


def surface_from_json(surfaceobj):
    return xtgeo.RegularSurface(**surfaceobj)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surfaces(fns):
    return xtgeo.surface.surfaces.Surfaces(fns)


@webvizstore
def get_path(path) -> Path:

    return Path(path)


def prev_value(current_value, options):
    try:
        index = options.index(current_value)
        return options[max(0, index - 1)]
    except ValueError:
        return current_value


def next_value(current_value, options):
    try:
        index = options.index(current_value)
        return options[min(len(options) - 1, index + 1)]

    except ValueError:
        return current_value


def surfacedf_to_dict(df):
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
def find_files(folder, suffix) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in folder.glob(f"*{suffix}")])
        ).encode()
    )


def make_fmu_filename(data):
    if data["date"] is None:
        return f"{data['name']}--{data['attr']}"
    return f"{data['name']}--{data['attr']}--{data['date']}"
