from typing import List, Optional, Dict, Any, Union, Tuple
from uuid import uuid4
import json

import pandas as pd
import dash
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_table
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizSettings

from ._tornado_data import TornadoData
from ._tornado_bar_chart import TornadoBarChart
from ._tornado_table import TornadoTable


class TornadoWidget:
    """### TornadoWidget

    This component visualizes a Tornado plot.
    It is meant to be used as a component in other plugin, and is initialized
     with a dataframe of realizations with corresponding sensitivities,
    but without the response values that are to be plotted.
    Instead we registers a dcc.Store which will contain the response values.

    To use:
    1. Initialize an instance of this class in a plugin.
    2. Add tornadoplot.layout to the plugin layout
    3. Register a callback that writes a json dump to tornadoplot.storage_id
    The format of the json dump must be ('ENSEMBLE' and 'data' are mandatory, the others optional):
    {'ENSEMBLE': name of ensemble,
     'data': 2d array of realizations / response values
     'number_format' (str): Format of the numeric part based on the Python Format Specification
      Mini-Language e.g. '#.3g' for 3 significant digits, '.2f' for two decimals, or '.0f' for no
      decimals.
     'unit' (str): String to append at the end as a unit.
     'spaced' (bool): Include a space between last numerical digit and SI-prefix.
     'locked_si_prefix' (str or int): Lock the SI prefix to either a string (e.g. 'm' (milli) or 'M'
      (mega)), or an integer which is the base 10 exponent (e.g. 3 for kilo, -3 for milli).
    }

    Mouse events:
    The current case at mouse cursor can be retrieved by registering a callback
    that reads from  `tornadoplot.click_id` if `allow_click` has been specified at initialization.


    * `realizations`: Dataframe of realizations with corresponding sensitivity cases
    * `reference`: Which sensitivity to use as reference.
    * `allow_click`: Registers a callback to store current data on mouse click
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        realizations: pd.DataFrame,
        reference: str = "rms_seed",
        height: str = "90vh",
        allow_click: bool = False,
    ):
        self.realizations = realizations
        self.height = height
        self.sensnames = list(self.realizations["SENSNAME"].unique())
        if self.sensnames == [None]:
            raise KeyError(
                "No sensitivity information found in ensemble. "
                "Containers utilizing tornadoplot can only be used for ensembles with "
                "one by one design matrix setup "
                "(SENSNAME and SENSCASE must be present in parameter file)."
            )
        self.initial_reference = (
            reference if reference in self.sensnames else self.sensnames[0]
        )
        self.allow_click = allow_click
        self.uid = uuid4()
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.set_callbacks(app)

    def ids(self, element: str) -> str:
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": self.ids("tornado-graph"),
                "content": ("Shows tornado plot."),
            },
            {
                "id": self.ids("reference"),
                "content": (
                    "Set reference sensitivity for which to calculate tornado plot"
                ),
            },
            {
                "id": self.ids("scale"),
                "content": (
                    "Set tornadoplot scale to either percentage or absolute values"
                ),
            },
            {
                "id": self.ids("cut-by-ref"),
                "content": (
                    "Remove sensitivities smaller than the reference from the plot"
                ),
            },
            {
                "id": self.ids("reset"),
                "content": "Clears the currently selected sensitivity",
            },
        ]

    @property
    def storage_id(self) -> str:
        """The id of the dcc.Store component that holds the tornado data"""
        return self.ids("storage")

    @property
    def click_id(self) -> str:
        """The id of the dcc.Store component that holds click data"""
        return self.ids("click-store")

    @property
    def high_low_storage_id(self) -> str:
        """The id of the dcc.Store component that holds click data"""
        return self.ids("high-low-storage")

    @staticmethod
    def set_grid_layout(columns: Union[str, List[str]]) -> Dict[str, str]:
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @property
    def layout(self) -> html.Div:
        return html.Div(
            style={"marginLeft": "10px", "height": "90vh"},
            children=[
                html.Div(
                    children=[
                        html.Label(
                            "Tornado Plot",
                            style={
                                "textAlign": "center",
                                "font-weight": "bold",
                            },
                        ),
                        dcc.RadioItems(
                            id=self.ids("plot-or-table"),
                            options=[
                                {"label": "Show bars", "value": "bars"},
                                {
                                    "label": "Show table",
                                    "value": "table",
                                },
                            ],
                            value="bars",
                        ),
                        html.Details(
                            open=False,
                            children=[
                                html.Summary("Settings"),
                                html.Div(
                                    style={"maxWidth": "600px"},
                                    children=[
                                        wcc.FlexBox(
                                            # style=self.set_grid_layout("1fr 1fr"),
                                            children=[
                                                html.Div(
                                                    style={
                                                        "minWidth": "100px",
                                                        "flex": 1,
                                                    },
                                                    children=html.Label("Reference:"),
                                                ),
                                                html.Div(
                                                    style={
                                                        "minWidth": "100px",
                                                        "flex": 1,
                                                    },
                                                    children=html.Label("Scale:"),
                                                ),
                                                html.Div(
                                                    style={
                                                        "minWidth": "100px",
                                                        "flex": 1,
                                                    },
                                                    children=html.Label(
                                                        "Filter sensitivities:"
                                                    ),
                                                ),
                                            ],
                                        ),
                                        wcc.FlexBox(
                                            children=[
                                                html.Div(
                                                    style={
                                                        "minWidth": "100px",
                                                        "flex": 1,
                                                    },
                                                    children=dcc.Dropdown(
                                                        id=self.ids("reference"),
                                                        options=[
                                                            {
                                                                "label": r,
                                                                "value": r,
                                                            }
                                                            for r in self.sensnames
                                                        ],
                                                        value=self.initial_reference,
                                                        clearable=False,
                                                        persistence=True,
                                                        persistence_type="session",
                                                    ),
                                                ),
                                                html.Div(
                                                    style={
                                                        "minWidth": "100px",
                                                        "flex": 1,
                                                    },
                                                    children=dcc.Dropdown(
                                                        id=self.ids("scale"),
                                                        options=[
                                                            {
                                                                "label": r,
                                                                "value": r,
                                                            }
                                                            for r in [
                                                                "Percentage",
                                                                "Absolute",
                                                            ]
                                                        ],
                                                        value="Percentage",
                                                        clearable=False,
                                                        persistence=True,
                                                        persistence_type="session",
                                                    ),
                                                ),
                                                html.Div(
                                                    style={
                                                        "minWidth": "100px",
                                                        "flex": 1,
                                                    },
                                                    children=html.Details(
                                                        open=False,
                                                        children=[
                                                            html.Summary("Filter"),
                                                            wcc.Select(
                                                                id=self.ids(
                                                                    "sens_filter"
                                                                ),
                                                                options=[
                                                                    {
                                                                        "label": i,
                                                                        "value": i,
                                                                    }
                                                                    for i in self.sensnames
                                                                ],
                                                                value=self.sensnames,
                                                                multi=True,
                                                                size=min(
                                                                    10,
                                                                    len(self.sensnames),
                                                                ),
                                                                persistence=True,
                                                                persistence_type="session",
                                                            ),
                                                        ],
                                                    ),
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                dcc.Checklist(
                                    id=self.ids("cut-by-ref"),
                                    options=[
                                        {
                                            "label": "Cut by reference",
                                            "value": "Cut by reference",
                                        },
                                    ],
                                    value=[],
                                    persistence=True,
                                    persistence_type="session",
                                ),
                                html.Button(
                                    style={
                                        "position": "relative",
                                        "top": "-50%",
                                        "fontSize": "10px",
                                    },
                                    id=self.ids("reset"),
                                    children="Clear selected",
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id=self.ids("graph-wrapper"),
                    children=wcc.Graph(
                        id=self.ids("tornado-graph"),
                        style={"height": "70vh"},
                        config={"displayModeBar": False},
                    ),
                ),
                html.Div(
                    id=self.ids("table-wrapper"),
                    style={"display": "none"},
                    children=dash_table.DataTable(
                        id=self.ids("tornado-table"),
                        columns=[
                            {
                                "name": col,
                                "id": col,
                                "type": "numeric",
                                "format": {
                                    "locale": {"symbol": ["", ""]},
                                    "specifier": "$.4s",
                                },
                            }
                            for col in TornadoTable.COLUMNS
                        ],
                        data=[],
                    ),
                ),
                dcc.Store(id=self.ids("storage"), storage_type="session"),
                dcc.Store(id=self.ids("click-store"), storage_type="session"),
                dcc.Store(id=self.ids("high-low-storage"), storage_type="session"),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        @app.callback(
            Output(self.ids("graph-wrapper"), "style"),
            Output(self.ids("table-wrapper"), "style"),
            Input(self.ids("plot-or-table"), "value"),
        )
        def _set_visualization(viz_type: str) -> Tuple[Dict[str, str], Dict[str, str]]:
            if viz_type == "bars":
                return {"display": "inline"}, {"display": "none"}
            if viz_type == "table":
                return {"display": "none"}, {"display": "inline"}
            raise PreventUpdate

        @app.callback(
            [
                Output(self.ids("tornado-graph"), "figure"),
                Output(self.ids("tornado-table"), "data"),
                Output(self.ids("high-low-storage"), "data"),
            ],
            [
                Input(self.ids("reference"), "value"),
                Input(self.ids("scale"), "value"),
                Input(self.ids("cut-by-ref"), "value"),
                Input(self.ids("storage"), "data"),
                Input(self.ids("sens_filter"), "value"),
            ],
        )
        def _calc_tornado(
            reference: str,
            scale: str,
            cutbyref: str,
            data: Union[str, bytes, bytearray],
            sens_filter: List[str],
        ) -> Tuple[dict, dict]:
            if not data:
                raise PreventUpdate
            data = json.loads(data)
            if not isinstance(data, dict):
                raise PreventUpdate
            values = pd.DataFrame(data["data"], columns=["REAL", "VALUE"])
            realizations = self.realizations.loc[
                self.realizations["ENSEMBLE"] == data["ENSEMBLE"]
            ]
            design_and_responses = pd.merge(values, realizations, on="REAL")
            if sens_filter is not None:
                if reference not in sens_filter:
                    sens_filter.append(reference)
                design_and_responses = design_and_responses.loc[
                    design_and_responses["SENSNAME"].isin(sens_filter)
                ]

            tornado_data = TornadoData(
                dframe=design_and_responses,
                reference=reference,
                scale=scale,
                cutbyref="Cut by reference" in cutbyref,
            )
            tornado_figure = TornadoBarChart(
                tornado_data=tornado_data,
                plotly_theme=self.plotly_theme,
                number_format=data.get("number_format", ""),
                unit=data.get("unit", ""),
                spaced=data.get("spaced", True),
                locked_si_prefix=data.get("locked_si_prefix", None),
            )
            tornado_table = TornadoTable(tornado_data=tornado_data)
            return (
                tornado_figure.figure,
                tornado_table.as_plotly_table,
                tornado_data.low_high_realizations_list,
            )

        if self.allow_click:

            @app.callback(
                Output(self.ids("click-store"), "data"),
                [
                    Input(self.ids("tornado-graph"), "clickData"),
                    Input(self.ids("reset"), "n_clicks"),
                ],
            )
            def _save_click_data(data: dict, nclicks: Optional[int]) -> str:
                if dash.callback_context.triggered is None:
                    raise PreventUpdate

                ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

                if ctx == self.ids("reset") and nclicks:

                    return json.dumps(
                        {
                            "real_low": [],
                            "real_high": [],
                            "sens_name": None,
                        }
                    )
                try:
                    real_low = data["points"][0]["customdata"]
                    real_high = data["points"][1]["customdata"]
                    sens_name = data["points"][0]["y"]
                    return json.dumps(
                        {
                            "real_low": real_low,
                            "real_high": real_high,
                            "sens_name": sens_name,
                        }
                    )
                except TypeError as exc:
                    raise PreventUpdate from exc
