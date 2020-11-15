from typing import Tuple, Union
from itertools import chain
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash
import plotly.express as px
import plotly.graph_objects as go
from ..utils.colors import find_intermediate_color
from ..figures.correlation_figure import CorrelationFigure
from ..utils.colors import hex_to_rgb

import time


def property_response_controller(parent, app):
    @app.callback(
        Output(parent.uuid("property-response-vector-graph"), "figure"),
        Output(parent.uuid("property-response-vector-scatter"), "figure"),
        Output(parent.uuid("property-response-correlation-graph"), "figure"),
        Output(parent.uuid("response-parameter-correlation-graph"), "figure"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "response"}, "value"),
        Input(
            {"id": parent.uuid("vector-select"), "tab": "response"},
            "children",
        ),
        Input(parent.uuid("property-response-vector-graph"), "clickData"),
        Input(
            {"id": parent.uuid("parameter-select"), "tab": "response"},
            "value",
        ),
        Input(
            {"id": parent.uuid("date-selected"), "tab": "response"},
            "children",
        ),
        Input(
            {"id": parent.uuid("vector-type"), "tab": "response"},
            "value",
        ),
        State(parent.uuid("property-response-vector-graph"), "figure"),
        State(parent.uuid("response-parameter-correlation-graph"), "figure"),
        State(parent.uuid("property-response-correlation-graph"), "figure"),
    )
    # pylint: disable=too-many-locals
    def _update_graphs(
        ensemble: str,
        vector: str,
        timeseries_clickdata: Union[None, dict],
        parameter: Union[None, dict],
        date: str,
        vector_types: Union[None, list],
        timeseries_fig: dict,
        corr_p_fig: dict,
        corr_v_fig: dict,
    ) -> Tuple[dict, dict, dict, dict]:

        if (
            dash.callback_context.triggered is None
            or dash.callback_context.triggered[0]["prop_id"] == "."
            or vector is None
        ):
            raise PreventUpdate

        ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        if isinstance(ctx, dict):
            ctx = ctx["id"]

        daterange = parent.vmodel.daterange_for_plot(vector=vector)
        # Make timeseries graph
        if (
            any(
                substr in ctx
                for substr in [
                    parent.uuid("vector-select"),
                    parent.uuid("ensemble-selector"),
                ]
            )
            or timeseries_fig is None
        ):
            timeseries_fig = update_timeseries_graph(
                parent.vmodel,
                ensemble,
                vector,
                daterange,
                real_filter=None,
            )

        # Get clicked data or last available date initially
        if parent.uuid("date-selected") not in ctx:
            date = (
                timeseries_clickdata.get("points", [{}])[0].get("x", daterange[1])
                if timeseries_clickdata
                else daterange[1]
            )

        vectors_filtered = filter_vectors(parent, vector_types)
        if vector not in vectors_filtered:
            vectors_filtered.append(vector)

        # Get dataframe with vector and REAL
        vector_df = parent.vmodel.get_ensemble_vectors_for_date(
            ensemble=ensemble,
            vectors=vectors_filtered,
            date=date,
        )
        vector_df["REAL"] = vector_df["REAL"].astype(int)

        # Get dataframe with parameters
        param_df = parent.pmodel.dataframe.copy()
        param_df = param_df[param_df["ENSEMBLE"] == ensemble]
        param_df["REAL"] = param_df["REAL"].astype(int)

        # Make correlation figure for vector
        if parent.uuid("vector-type") not in ctx:
            merged_df = pd.merge(vector_df[[vector, "REAL"]], param_df, on=["REAL"])
            corr_v_fig = make_correlation_figure(merged_df, response=vector).figure

        # Get clicked parameter correlation bar or largest bar initially
        parameter = (
            parameter if parameter is not None else corr_v_fig["data"][0]["y"][-1]
        )
        corr_v_fig = color_corr_bars(corr_v_fig, parameter)

        # Make correlation figure for parameter
        if any(
            substr not in ctx
            for substr in [
                parent.uuid("parameter-select"),
                parent.uuid("vector-type"),
            ]
        ):
            merged_df = pd.merge(param_df[[parameter, "REAL"]], vector_df, on=["REAL"])
            corr_p_fig = make_correlation_figure(merged_df, response=parameter).figure
        corr_p_fig = color_corr_bars(corr_p_fig, vector)

        # Create scatter plot of vector vs parameter
        scatter_fig = update_scatter_graph(merged_df, vector, parameter)

        # Order realizations sorted on value of parameter and color traces
        real_order = parent.pmodel.get_real_order(ensemble, parameter=parameter)
        timeseries_fig = color_timeseries_graph(
            timeseries_fig, ensemble, parameter, vector, real_order
        )

        # Draw date selected as line
        timeseries_fig = add_date_line(timeseries_fig, date)

        return timeseries_fig, scatter_fig, corr_v_fig, corr_p_fig

    @app.callback(
        Output(
            {"id": parent.uuid("date-selected"), "tab": "response"},
            "children",
        ),
        Input({"id": parent.uuid("date-slider-selector"), "tab": "response"}, "value"),
    )
    def _update_date(dateidx):
        dates = sorted(parent.vmodel.dataframe["DATE"].unique())
        return dates[dateidx]

    @app.callback(
        Output(
            {"id": parent.uuid("vector-select"), "tab": "response"},
            "children",
        ),
        Input({"id": parent.uuid("vector-main-select"), "tab": "response"}, "value"),
        Input({"id": parent.uuid("vector-sub-select"), "tab": "response"}, "value"),
    )
    def _combine_substrings_to_vector(main_vector, sub_value=None):
        if sub_value is None:
            return main_vector
        return f"{main_vector}:{sub_value}"

    @app.callback(
        Output({"id": parent.uuid("vector-main-select"), "tab": "response"}, "options"),
        Output({"id": parent.uuid("vector-main-select"), "tab": "response"}, "value"),
        Output({"id": parent.uuid("vector-sub-select"), "tab": "response"}, "options"),
        Output({"id": parent.uuid("vector-sub-select"), "tab": "response"}, "value"),
        Output({"id": parent.uuid("vector-sub-select"), "tab": "response"}, "disabled"),
        Input({"id": parent.uuid("vector-type-select"), "tab": "response"}, "value"),
        Input(parent.uuid("response-parameter-correlation-graph"), "clickData"),
    )
    def _update_vectorlist(vector_type, corr_param_clickdata):
        ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        click_data = parent.uuid("response-parameter-correlation-graph") in ctx

        if click_data:
            vector_selected = corr_param_clickdata.get("points", [{}])[0].get("y")
            vector_type = find_vector_type(parent, vector_selected)
            main_vector_value = vector_selected.split(":")[0]
            sub_selection_value = (
                vector_selected.split(":")[-1]
                if "subselect" in parent.vmodel.vector_groups[vector_type]
                else None
            )
        else:
            main_vector_value = parent.vmodel.vector_groups[vector_type][
                "vectors_main"
            ][0]
            sub_selection_value = (
                parent.vmodel.vector_groups[vector_type]["subselect"][0]
                if "subselect" in parent.vmodel.vector_groups[vector_type]
                else None
            )

        main_vector_list = [
            {"label": i, "value": i}
            for i in parent.vmodel.vector_groups[vector_type]["vectors_main"]
        ]
        sub_selection_list = (
            [
                {"label": i, "value": i}
                for i in parent.vmodel.vector_groups[vector_type]["subselect"]
            ]
            if "subselect" in parent.vmodel.vector_groups[vector_type]
            else []
        )

        return (
            main_vector_list,
            main_vector_value,
            sub_selection_list,
            sub_selection_value,
            "subselect" not in parent.vmodel.vector_groups[vector_type],
        )

    @app.callback(
        Output(
            {"id": parent.uuid("parameter-select"), "tab": "response"},
            "value",
        ),
        Input(parent.uuid("property-response-correlation-graph"), "clickData"),
    )
    def _update_parameter_selected(
        corr_vector_clickdata: Union[None, dict],
    ) -> str:
        if corr_vector_clickdata is None:
            raise PreventUpdate
        return corr_vector_clickdata.get("points", [{}])[0].get("y")


def find_vector_type(parent, vector):
    for vgroup, values in parent.vmodel.vector_groups.items():
        if vector in values["vectors"]:
            return vgroup
    return None


def filter_vectors(parent, vector_types=None):
    return list(
        chain.from_iterable(
            [parent.vmodel.vector_groups[v]["vectors"] for v in vector_types]
        )
    )


def update_timeseries_graph(
    timeseries_model, ensemble, vector, daterange, real_filter=None
):
    return {
        "data": timeseries_model.add_realization_traces(
            ensemble=ensemble, vector=vector, real_filter=real_filter
        ),
        "layout": dict(
            margin={"r": 50, "l": 20, "t": 60, "b": 20},
            yaxis={"automargin": True},
            xaxis={"range": daterange},
            hovermode="closest",
            paper_bgcolor="white",
            plot_bgcolor="white",
            showlegend=False,
        ),
    }


def add_date_line(figure, selected_date):
    # Draw clicked date as a black line and add annotation
    ymin = min([min(trace["y"]) for trace in figure["data"]])
    ymax = max([max(trace["y"]) for trace in figure["data"]])

    if any([trace["name"] == "Dateline" for trace in figure["data"]]):
        for trace in figure["data"]:
            if trace["name"] == "Dateline":
                trace.update(x=[selected_date, selected_date])
    else:
        figure["data"].append(
            go.Scatter(
                x=[selected_date, selected_date],
                y=[ymin, ymax],
                cliponaxis=False,
                mode="lines+text",
                line={"dash": "dot", "width": 4, "color": "#243746"},
                name="Dateline",
                text=["", selected_date],
                textposition="top center",
            )
        )
    return figure


def color_timeseries_graph(figure, ensemble, selected_param, vector, real_order=None):
    """Color timeseries lines by parameter value"""
    if real_order is not None:
        mean = real_order["VALUE"].mean()
        min_val = real_order["VALUE"].min()
        max_val = real_order["VALUE"].max()
        low_reals = real_order[real_order["VALUE"] <= mean]["REAL"].astype(str).values
        high_reals = real_order[real_order["VALUE"] > mean]["REAL"].astype(str).values
        for trace_no, trace in enumerate(figure.get("data", [])):
            if trace["name"] == ensemble:
                figure["data"][trace_no]["marker"]["color"] = set_real_color(
                    str(trace["customdata"]), low_reals, high_reals
                )
        figure["layout"]["title"] = {
            "text": f"{vector} colored by {selected_param}",
        }

        figure["layout"]["shapes"] = [
            dict(
                type="circle",
                xref="paper",
                yref="paper",
                x0=0,
                y0=0,
                x1=15,
                y1=15,
                line=dict(color="rgba(255,18,67, 1)"),
                fillcolor="rgba(255,18,67, 0.8)",
                xsizemode="pixel",
                ysizemode="pixel",
                xanchor="1.03",
                yanchor="0.8",
            ),
            dict(
                type="circle",
                xref="paper",
                yref="paper",
                x0=0,
                y0=0,
                x1=15,
                y1=15,
                line=dict(color="rgba(220,220,220, 1)"),
                fillcolor="rgba(220,220,220, 0.4)",
                xsizemode="pixel",
                ysizemode="pixel",
                xanchor="1.03",
                yanchor="0.72",
            ),
            dict(
                type="circle",
                xref="paper",
                yref="paper",
                x0=0,
                y0=0,
                x1=15,
                y1=15,
                line=dict(color="rgba(62,208,62, 1)"),
                fillcolor="rgba(62,208,62, 0.8)",
                xsizemode="pixel",
                ysizemode="pixel",
                xanchor="1.03",
                yanchor="0.64",
            ),
        ]

    return figure


def set_real_color(real_no: str, low_reals: list, high_reals: list):
    red = "rgba(255,18,67, 1)"
    green = "rgba(62,208,62, 1)"

    if real_no in low_reals:
        index = int(list(low_reals).index(real_no))
        intermed = index / len(low_reals)
        return find_intermediate_color(
            red,
            "rgba(220,220,220, 0.1)",
            intermed,
            colortype="rgba",
        )
    if real_no in high_reals:
        index = int(list(high_reals).index(real_no))
        intermed = index / len(high_reals)
        return find_intermediate_color(
            "rgba(220,220,220, 0.1)", green, intermed, colortype="rgba"
        )

    return "rgba(220,220,220, 0.2)"


def update_scatter_graph(df, vector, selected_param):
    colors = [
        "#FF1243",
        "#243746",
        "#007079",
    ]
    df = df[[vector, selected_param]]
    return (
        px.scatter(
            df,
            x=selected_param,
            y=vector,
            trendline="ols",
            trendline_color_override="#243746",
        )
        .update_layout(
            margin={
                "r": 20,
                "l": 20,
                "t": 60,
                "b": 20,
            },
            paper_bgcolor="white",
            plot_bgcolor="white",
            title={"text": f"{vector} vs {selected_param}", "x": 0.5},
        )
        .update_traces(
            marker={
                "size": 15,
                "color": hex_to_rgb(colors[2], 0.7),
            }
        )
        .update_xaxes(title=None)
        .update_yaxes(title=None)
    )


def make_correlation_figure(df, response):
    # Correlate properties against vector
    corrseries = correlate(df, response=response)
    # Make correlation figure
    return CorrelationFigure(
        corrseries, n_rows=15, title=f"Correlations with {response}"
    )


def correlate(df, response):
    """Returns the correlation matrix for a dataframe"""
    df = df[df.columns[df.nunique() > 1]].copy()
    if response not in df.columns:
        df[response] = np.nan
    series = df[response]
    df = df.drop(columns=[response, "REAL"])
    corrdf = df.corrwith(series)
    return corrdf.reindex(corrdf.abs().sort_values().index)


def color_corr_bars(figure, selected_bar):
    colors = [
        "#FF1243",
        "#243746",
        "#007079",
    ]

    figure["data"][0]["marker"] = {
        "color": [
            hex_to_rgb(colors[2], 0.4)
            if _bar != selected_bar
            else hex_to_rgb(colors[0], 0.8)
            for _bar in figure["data"][0]["y"]
        ],
        "line": {
            "color": [
                colors[2] if _bar != selected_bar else colors[0]
                for _bar in figure["data"][0]["y"]
            ],
            "width": 1.2,
        },
    }
    return figure
