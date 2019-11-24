from uuid import uuid4
from pathlib import Path
import json
import yaml
import time
import datetime
import itertools
import random

import pandas as pd
from plotly.subplots import make_subplots
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizContainerABC
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE

from ..datainput import load_smry


class FasterTimeSeries(WebvizContainerABC):
    """### FasterTimeSeries

Visualizes reservoir simulation time series for FMU ensembles.
Input can be given either as aggregated csv file or an ensemble defined
in container settings.

* `csvfile`: Aggregated csvfile for unsmry with 'REAL', 'ENSEMBLE', 'DATE' and vector columns
* `ensembles`: Which ensembles in `container_settings` to visualize.
* `column_keys`: List of vectors to extract. If not given, all vectors
                 from the simulations will be extracted. Wild card asterisk *
                 can be used.
* `sampling`: Time separation between extracted values. Can be e.g. `monthly`
              or `yearly`.
* `options`: Options to initialize plots with. See below

Plot options:
    * `vector1` : First vector to display
    * `vector2` : Second vector to display
    * `vector3` : Third vector to display
    * `visualization` : 'realizations', 'statistics' or 'statistics_hist',
    * `date` : Date to show in histograms
"""

    ENSEMBLE_COLUMNS = [
        "REAL",
        "ENSEMBLE",
        "DATE",
    ]
    # pylint:disable=too-many-arguments
    def __init__(
        self,
        app,
        container_settings,
        csvfile: Path = None,
        ensembles: list = None,
        obsfile: Path = None,
        column_keys=None,
        sampling: str = "monthly",
        options: dict = None,
    ):
        self.csvfile = csvfile if csvfile else None
        self.obsfile = obsfile if obsfile else None
        self.time_index = sampling
        self.column_keys = tuple(column_keys) if column_keys else None
        if csvfile and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles"'
            )
        self.observations = {}
        if obsfile:
            with open(get_path(self.obsfile), "r") as stream:
                self.observations = format_observations(
                    yaml.safe_load(stream).get("smry", [dict()])
                )
        if csvfile:
            self.smry = read_csv(csvfile)
        elif ensembles:
            self.ens_paths = tuple(
                (ensemble, container_settings["scratch_ensembles"][ensemble])
                for ensemble in ensembles
            )
            self.smry = load_smry(
                ensemble_paths=self.ens_paths,
                ensemble_set_name="EnsembleSet",
                time_index=self.time_index,
                column_keys=self.column_keys,
            )
        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles"'
            )

        self.smry_cols = [
            c
            for c in [*self.smry.columns]
            if c not in FasterTimeSeries.ENSEMBLE_COLUMNS
            if not c.endswith("H")
        ]
        self.ensembles = list(self.smry["ENSEMBLE"].unique())
        self.plotly_layout = app.webviz_settings["plotly_layout"]
        self.plot_options = options if options else {}
        self.plot_options["date"] = (
            str(self.plot_options.get("date"))
            if self.plot_options.get("date")
            else None
        )

        colors = self.plotly_layout.get(
            "colors",
            [
                "#243746",
                "#eb0036",
                "#919ba2",
                "#7d0023",
                "#66737d",
                "#4c9ba1",
                "#a44c65",
                "#80b7bc",
                "#ff1243",
                "#919ba2",
                "#be8091",
                "#b2d4d7",
                "#ff597b",
                "#bdc3c7",
                "#d8b2bd",
                "#ffe7d6",
                "#d5eaf4",
                "#ff88a1",
            ],
        )
        self.ens_colors = {
            ens: colors[self.ensembles.index(ens)] for ens in self.ensembles
        }

        self.allow_delta = len(self.ensembles) > 1
        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }


    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 4fr"),
            children=[
                html.Div(
                    children=[
                        html.Div(
                            style={"padding": "10px"},
                            children=[
                                dcc.Slider(
                                    id=self.ids("ens-slider"),
                                    min=0,
                                    updatemode="drag",
                                    max=len(self.ensembles) - 1,
                                    step=(len(self.ensembles) - 1) / 10,
                                    marks={
                                        i: {
                                            "label": ens,
                                           
                                        } for i, ens in enumerate(self.ensembles)
                                    },
                                    value=0
                                ),
                                
                                html.Label(
                                    style={"marginTop": "25px"}, children="Time Series"
                                ),
                                dcc.Dropdown(
                                    style={"marginTop": "5px", "marginBottom": "5px"},
                                    id=self.ids("vectors"),
                                    clearable=False,
                                    multi=False,
                                    options=[
                                        {"label": i, "value": i} for i in self.smry_cols
                                    ],
                                    value=self.plot_options.get(
                                        "vector1", self.smry_cols[0]
                                    ),
                                ),
                                html.Label(id=self.ids("datapoints")),
                            ],
                        ),
                    ]
                ),
                html.Div(
                    [
                        # wcc.Graph(id=self.ids("graph")),
                        html.Div(id=self.ids("uPlot")),
                    ]
                ),
            ],
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.ids("uPlot"), "children"),
                # Output(self.ids("uPlot"), "series"),
                # Output(self.ids("uPlot"), "legend"),
                Output(self.ids("datapoints"), "children"),
            ],
            [
                Input(self.ids("vectors"), "value"),
                Input(self.ids("ens-slider"), "value"),
            ],
        )
        # pylint: disable=too-many-instance-attributes, too-many-arguments, too-many-locals, too-many-branches
        def _update_graph(vectors, slider):
            """Callback to update all graphs based on selections"""
            print(slider)
            if slider is None:
                print("ok", slider)
                raise PreventUpdate
            slider = str(slider).split(".")
            if len(slider) == 2:
                if slider[0] < self.ensembles[-1]:
                    ensembles = [
                        self.ensembles[int(slider[0])],
                        self.ensembles[int(slider[0]) + 1],
                    ]
                    opacity = [1 - float(slider[1]) / 10, float(slider[1]) / 10]
            if len(slider) == 1:
                ensembles = [self.ensembles[int(slider[0])]]
                opacity = [1]
            print(ensembles)
            # Combine selected vectors
            vectors = vectors if isinstance(vectors, list) else [vectors]
            if not ensembles:
                print("bah")
                raise PreventUpdate
            print("bah2")
            # Ensure selected ensembles is a list
            # ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
            df = filter_df(self.smry, ensembles, vectors)
            data = []
            data.append(
                [
                    time.mktime(datetime.datetime.strptime(d, "%Y-%m-%d").timetuple())
                    for d in list(df["DATE"].unique())
                ]
            )

            # for ens, ensdf in self.smry.groupby('ENSEMBLE'):
            #     realdfs = []
            #     for real, realdf in ensdf.groupby('REAL'):
            #         for i in range(1,25):
            #             df2 = realdf.copy()
            #             df2['REAL'] = df2['REAL']*i
            #             for j in self.smry_cols:
            #                 df2[j] = df2[j] * random.uniform(0.9, 1.1)
            #             realdfs.append(df2)
            #     df3 = pd.concat(realdfs)
            # dfs = []
            # for i in range(0,4):
            #     df4 = df3.copy()
            #     df4['ENSEMBLE'] = f"iter-{i}"
            #     for j in self.smry_cols:
            #         df4[j] = df4[j] * random.uniform(1-i*0.1, 1)
            #     dfs.append(df4)

            # pd.concat(dfs).to_csv('/tmp/smry.csv', index=False)
            series = []
            print(data)
            for ens_no, (ens, ensdf) in enumerate(df.groupby("ENSEMBLE")):
                color = hex_to_rgb(self.ens_colors[ens], opacity[ens_no])
                for real, realdf in ensdf.groupby("REAL"):
                    for vector in vectors:
                        data.append(list(realdf[vector]))
                        series.append({"label": vector, "width": 1, "color": color})
            points = len(data) * len(data[1])
            # print(data)
            return (
                wcc.UPlot(
                    id="ok",
                    width=1200,
                    data=data,
                    series=series,
                    legend={"show": False},
                ),
                f"Plotting {points} datapoints",
            )
            # return data, series, {"show": False},

    def add_webvizstore(self):
        functions = []
        if self.csvfile:
            functions.append((read_csv, [{"csv_file": self.csvfile}]))
        else:
            functions.append(
                (
                    load_smry,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "ensemble_set_name": "EnsembleSet",
                            "time_index": self.time_index,
                            "column_keys": self.column_keys,
                        }
                    ],
                )
            )
        if self.obsfile:
            functions.append((get_path, [{"path": self.obsfile}]))
        return functions


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_df(df, ensembles, vectors):
    """Filter dataframe for current vector. Include history
    vector if present"""
    columns = ["REAL", "ENSEMBLE", *vectors, "DATE"]
    return df.loc[df["ENSEMBLE"].isin(ensembles)][columns]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_delta(df, base_ens, delta_ens):
    """Calculate delta between two ensembles"""
    base_df = (
        df.loc[df["ENSEMBLE"] == base_ens]
        .set_index(["DATE", "REAL"])
        .drop("ENSEMBLE", axis=1)
    )
    delta_df = (
        df.loc[df["ENSEMBLE"] == delta_ens]
        .set_index(["DATE", "REAL"])
        .drop("ENSEMBLE", axis=1)
    )
    dframe = base_df.sub(delta_df).reset_index()
    dframe["ENSEMBLE"] = f"{base_ens}-{delta_ens}"
    return dframe.fillna(0)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)


@webvizstore
def get_path(path) -> Path:
    return Path(path)


def hex_to_rgb(hex_string, opacity=1):
    """Converts a hex color to rgb"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    rgb.append(opacity)
    return f"rgba{tuple(rgb)}"
