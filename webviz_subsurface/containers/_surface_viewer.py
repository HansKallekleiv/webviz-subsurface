import os
import numpy as np
import json
from uuid import uuid4
import dash
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output, State
from webviz_config.containers import WebvizContainer
from webviz_subsurface.datainput.layeredmap import LayeredSurface
from webviz_subsurface_components import LayeredMap
from webviz_subsurface.private_containers._surface_selector import SurfaceSelector
from webviz_subsurface.datainput import get_realizations
from xtgeo import RegularSurface, Surfaces



class SurfaceViewer(WebvizContainer):
    """### SurfaceViewer


* `ensembles`: Which ensembles in `container_settings` to visualize.
* `stratigraphic_context`: A YAML file with stratigraphic context of surfaces stored on disk
"""

    def __init__(self, app, container_settings, ensembles, stratigraphic_context=None):

        self.ensemble_names = tuple(
            (ens, container_settings["scratch_ensembles"][ens]) for ens in ensembles
        )
        self.ensembles = get_realizations(
            ensemble_paths=self.ensemble_names, ensemble_set_name="EnsembleSet"
        )
        self.strat_context = stratigraphic_context
        self.ensembles.to_csv("/tmp/webviz.tmp.csv", index=False)
        self.uid = f"{uuid4()}"

        self.surface_selector = SurfaceSelector(
            app, self.strat_context, self.ensembles
        )
        self.set_callbacks(app)

    @property
    def styles(self):
        return {"pre": {"border": "thin lightgrey solid", "overflowX": "scroll"}}

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
            style=self.set_grid_layout("2fr 3fr"),
            children=[
                html.Div(children=[self.surface_selector.layout, wcc.Graph("hist-id")]),
                LayeredMap(
                    id="my-map",
                    draw_toolbar_marker=True,
                    layers=[],
                    map_bounds=[[0, 0], [0, 0]],
                    center=[0, 0],
                ),
                html.Pre(id="test", style=self.styles["pre"]),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output("test", "children"),
            [Input(self.surface_selector.storage_id, "children")],
        )
        def _set_data(data):

            return json.dumps(json.loads(data), indent=4)

        @app.callback(
            [
                Output("my-map", "layers"),
                Output("my-map", "map_bounds"),
                Output("my-map", "center"),
                Output("hist-id", "figure"),
            ],
            [
                Input(self.surface_selector.storage_id, "children"),
                Input("my-map", "marker_point"),
            ],
        )
        def test_selector(data, coords):
            # Assume FMU scratch storage
            data = json.loads(data)
            fig = {"layout": {"title": "Add a marker on the plot to see distribution"}}
            if not data["aggregation"]:
                path = get_path(
                    self.ensembles,
                    data["ensemble"],
                    data["realization"],
                    data["name"],
                    data["attribute"],
                    data["date"],
                )
                s = RegularSurface(path)

                ls = LayeredSurface("Top res", s)
                return ls.layers, ls.bounds, ls.center, fig
            else:
                calc = data["aggregation"]
                paths = [
                    get_path(
                        self.ensembles,
                        data["ensemble"],
                        real,
                        data["name"],
                        data["attribute"],
                        data["date"],
                    )
                    for real in data["realization"]
                ]
                slist = Surfaces(paths)
                if calc == "mean":
                    s = slist.apply(np.mean, axis=0)

                if calc == "stddev":
                    s = slist.apply(np.std, axis=0)

                if calc == "min":
                    s = slist.apply(np.min, axis=0)

                if calc == "max":
                    s = slist.apply(np.max, axis=0)

                if calc == "p10":
                    s = slist.apply(np.nanpercentile, 10, axis=0)

                if calc == "p90":
                    s = slist.apply(np.nanpercentile, 90, axis=0)

                ls = LayeredSurface("Top res", s)
                if coords:
                    # x, y = y, x - Should look at this in the Leaflet component
                    xy = (coords[1], coords[0])

                    # Get z-value of all surfaces at given coordinates
                    points = [surf.get_value_from_xy(xy) for surf in slist.surfaces]

                    fig = {
                        "data": [
                            {"x": points, "type": "histogram"}
                        ],
                        "layout": {
                            "title": "Distribution at marker",
                            "xaxis": {"title": "Realization"},
                            "yaxis": {"title": data["name"]},
                        },
                    }
                return ls.layers, ls.bounds, ls.center, fig

    def add_webvizstore(self):
        return [
            (
                get_realizations,
                [
                    {
                        "ensemble_paths": self.ensemble_names,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        ]


def get_path(
    df,
    ensemble,
    realization,
    name,
    attribute=None,
    date=None,
    suffix=".gri",
    sep="--",
    folder="share/results/maps",
):
    runpath = df.loc[
        (df["ENSEMBLE"] == ensemble) & (df["REAL"] == realization), "RUNPATH"
    ]
    runpath = list(runpath)[0]
    fn = fn = f"{name}{sep}{attribute}"
    if date:
        fn = f"{fn}{sep}{date}"
    fn = f"{fn}{suffix}"
    return os.path.join(runpath, folder, fn)
