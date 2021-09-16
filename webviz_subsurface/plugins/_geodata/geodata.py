from typing import List, Tuple, Callable, Optional
from pathlib import Path

import pandas as pd
import numpy as np
from pandas.api.types import is_numeric_dtype
from dash import html, Dash, Input, Output, State, ALL, dash_table
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from .main_view import main_view
from .varviz_callback import varviz_callback

class GeoData(WebvizPluginABC):
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        csvfile_channel: Path = None,
        csvfile_variogram: Path = None,
    ):

        super().__init__()

        self.csvfile_channel = read_csv(csvfile_channel) if csvfile_channel else None
        self.csvfile_variogram = (
            read_csv(csvfile_variogram) if csvfile_variogram else None
        )

        print(csvfile_channel)

        self.theme = webviz_settings.theme

        self.filters = ["Delft3D model", "Formation", "Attribute"]
        self.variogram_filters = [
            "Delft3D model",
            "Attribute",
            "Identifier",
            "Indicator",
        ]
        self.variogram_responses = [
            col for col in self.csvfile_variogram if col not in self.variogram_filters
        ]
        print(self.variogram_responses)
        self.responses = [
            col for col in self.csvfile_channel if col not in self.filters
        ]
        print(self.csvfile_variogram)
        self.set_callbacks(app)

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                main_view(
                    get_uuid=self.uuid,
                    theme=self.theme,
                    responses=self.responses,
                    filters=self.filters,
                    channel_dframe=self.csvfile_channel,
                    variogram_dframe=self.csvfile_variogram,
                    variogram_filters=self.variogram_filters,
                    variogram_responses=self.variogram_responses,
                ),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.uuid("main-table"), "children"),
            Input({"id": self.uuid("selections-table"), "selector": ALL}, "value"),
            Input({"id": self.uuid("selections-table"), "filter": ALL}, "value"),
            State({"id": self.uuid("selections-table"), "selector": ALL}, "id"),
            State({"id": self.uuid("selections-table"), "filter": ALL}, "id"),
        )
        def update_table(
            table_selections: list, table_filters: list, selector_ids, filter_ids
        ) -> list:

            selection = {
                id_value["selector"]: value
                for id_value, value in zip(selector_ids, table_selections)
            }
            filters = {
                id_value["filter"]: value
                for id_value, value in zip(filter_ids, table_filters)
            }

            dframe = self.csvfile_channel
            for filt, values in filters.items():
                dframe = dframe.loc[dframe[filt].isin(values)]

            return make_table(
                dframe,
                selection["table_responses"],
                table_type=selection["Table type"],
                groups=selection["Group by"],
            )

        varviz_callback(app=app, get_uuid=self.uuid,dframe= self.csvfile_variogram)

def make_table(
    dframe: pd.DataFrame,
    responses: list,
    table_type: str,
    groups: Optional[list] = None,
) -> html.Div:

    groups = groups if groups is not None else []

    if table_type == "Statistics table":
        statcols = ["Mean", "Stddev", "P90", "P10", "Minimum", "Maximum"]
        df_groups = dframe.groupby(groups) if groups else [(None, dframe)]

        data_list = []
        for response in responses:
            if not is_numeric_dtype(dframe[response]):
                continue
            for name, df in df_groups:
                values = df[response]
                data = {
                    "Response": response,
                    "Mean": values.mean(),
                    "Stddev": values.std(),
                    "P10": np.nanpercentile(values, 90),
                    "P90": np.nanpercentile(values, 10),
                    "Minimum": values.min(),
                    "Maximum": values.max(),
                }

                for idx, group in enumerate(groups):
                    data[group] = (
                        name if not isinstance(name, tuple) else list(name)[idx]
                    )
                data_list.append(data)

        return html.Div(
            style={"margin-top": "20px"},
            children=[
                dash_table.DataTable(
                    columns=[
                        {
                            "id": col,
                            "name": col,
                            "type": "numeric",
                            "format": {"specifier": ".1f"},
                        }
                        for col in ["Response"] + groups + statcols
                    ],
                    data=data_list,
                    style_table={
                        "height": "80vh",
                        "overflowY": "auto",
                    },
                )
            ],
        )

    # if table type Mean table
    dframe = (
        dframe.groupby(groups).mean().reset_index()
        if groups
        else dframe[responses].mean().to_frame().T
    )

    return html.Div(
        style={"margin-top": "20px"},
        children=[
            dash_table.DataTable(
                columns=[
                    {
                        "id": col,
                        "name": col,
                        "type": "numeric",
                        "format": {"specifier": ".1f"},
                    }
                    for col in dframe
                ],
                data=dframe.iloc[::-1].to_dict("records"),
                style_table={
                    "height": "80vh",
                    "overflowY": "auto",
                },
            )
        ],
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file)
