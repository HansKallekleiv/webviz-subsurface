from dash.dependencies import Input, Output, ALL
from dash.exceptions import PreventUpdate
import plotly.express as px

import webviz_core_components as wcc


def vol_controller(parent, app):
    @app.callback(
        Output(parent.uuid("plot"), "figure"),
        Input(
            {"plugin": parent.uuid("plugin"), "type": "single_filter", "name": ALL},
            "value",
        ),
        Input(
            {"plugin": parent.uuid("plugin"), "type": "multi_filter", "name": ALL},
            "value",
        ),
    )
    def _update_plot(single_filters, multi_filters):
        all_filter_values = single_filters + multi_filters
        all_filter_names = parent.vmodel.single_filters + parent.vmodel.multi_filters
        dframe = parent.vmodel.filter_dataframe(
            parent.vmodel.dataframe, all_filter_names, all_filter_values
        )
        print(dframe)
        return px.violin(
            data_frame=dframe,
            y="STOIIP_OIL",
            violinmode="overlay",
            color="ENSEMBLE",
            facet_col="ZONE",
        )

        raise PreventUpdate