from typing import Callable
import pandas as pd
import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash_core_components as dcc


def export_data_controllers(app: dash.Dash, get_uuid: Callable) -> None:
    @app.callback(
        Output(get_uuid("download-dataframe"), "data"),
        Input({"request": "table_data", "table_id": ALL}, "data_requested"),
        State({"table_id": ALL}, "data"),
        State({"request": "table_data", "table_id": ALL}, "id"),
        State({"table_id": ALL}, "id"),
        prevent_initial_call=True,
    )
    def _export_table_data(
        _data_requested: list,
        table_data: list,
        button_ids: list,
        table_ids: list,
    ) -> Callable:

        ctx = dash.callback_context.triggered[0]
        export_clicks = {
            id_value["table_id"]: n_clicks
            for id_value, n_clicks in zip(button_ids, _data_requested)
        }
        table_to_extract = next(x for x in export_clicks.keys() if x in ctx["prop_id"])
        if export_clicks[table_to_extract] is None:
            raise PreventUpdate

        index = [x["table_id"] for x in table_ids].index(table_to_extract)
        table_data = table_data[index]

        return dcc.send_data_frame(
            pd.DataFrame(table_data).to_excel, "VolumetricAnalysis.xlsx", index=False
        )
