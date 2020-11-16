from typing import Tuple, Union
from itertools import chain
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash
import plotly.express as px
import plotly.graph_objects as go
from ..utils.colors import find_intermediate_color
from ..figures.correlation_figure import CorrelationFigure
from ..utils.colors import hex_to_rgb


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
        Input(
            {
                "id": parent.uuid("filter-vector-selector"),
                "tab": "response",
                "selector": ALL,
            },
            "value",
        ),
        Input({"id": parent.uuid("show-dateline"), "tab": "response"}, "value"),
        State(parent.uuid("property-response-vector-graph"), "figure"),
        State(parent.uuid("response-parameter-correlation-graph"), "figure"),
        State(parent.uuid("property-response-correlation-graph"), "figure"),
        State(parent.uuid("property-response-vector-scatter"), "figure"),
    )
    # pylint: disable=too-many-locals
    def _update_graphs(
        ensemble: str,
        vector: str,
        parameter: Union[None, dict],
        date: str,
        vector_type_filter: list,
        vector_item_filters: list,
        show_dateline: str,
        timeseries_fig: dict,
        corr_p_fig: dict,
        corr_v_fig: dict,
        scatter_fig: dict,
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

        if parent.uuid("show-dateline") not in ctx:
            daterange = parent.vmodel.daterange_for_plot(vector=vector)
            # Make timeseries graph
            if (
                uuids_impact(parent, ctx, plot="timeseries_fig")
                or timeseries_fig is None
            ):
                timeseries_fig = update_timeseries_graph(
                    parent.vmodel,
                    ensemble,
                    vector,
                    daterange,
                    real_filter=None,
                )

            vectors_filtered = filter_vectors(
                parent, vector_type_filter, vector_item_filters
            )
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
            if (
                uuids_impact(parent, ctx, plot="vector_correlation")
                or corr_v_fig is None
            ):
                merged_df = pd.merge(vector_df[[vector, "REAL"]], param_df, on=["REAL"])
                corr_v_fig = make_correlation_figure(merged_df, response=vector).figure

            # Get clicked parameter correlation bar or largest bar initially
            parameter = (
                parameter if parameter is not None else corr_v_fig["data"][0]["y"][-1]
            )
            corr_v_fig = color_corr_bars(corr_v_fig, parameter)

            # Make correlation figure for parameter
            if (
                uuids_impact(parent, ctx, plot="parameter_correlation")
                or corr_p_fig is None
            ):
                merged_df = pd.merge(
                    param_df[[parameter, "REAL"]], vector_df, on=["REAL"]
                )
                corr_p_fig = make_correlation_figure(
                    merged_df, response=parameter
                ).figure

            corr_p_fig = color_corr_bars(corr_p_fig, vector)

            # Create scatter plot of vector vs parameter
            if uuids_impact(parent, ctx, plot="scatter") or scatter_fig is None:
                scatter_fig = update_scatter_graph(merged_df, vector, parameter)

            # Order realizations sorted on value of parameter and color traces
            real_order = parent.pmodel.get_real_order(ensemble, parameter=parameter)
            timeseries_fig = color_timeseries_graph(
                timeseries_fig, ensemble, parameter, vector, real_order
            )

        # Draw date selected as line
        timeseries_fig = add_date_line(timeseries_fig, date, show_dateline)

        return timeseries_fig, scatter_fig, corr_v_fig, corr_p_fig

    @app.callback(
        Output({"id": parent.uuid("date-slider-selector"), "tab": "response"}, "value"),
        Input(parent.uuid("property-response-vector-graph"), "clickData"),
    )
    def _update_date_from_clickdata(timeseries_clickdata):
        dates = parent.vmodel.dates
        return (
            dates.index(timeseries_clickdata.get("points", [{}])[0]["x"])
            if timeseries_clickdata is not None
            else len(dates) - 1
        )

    @app.callback(
        Output(
            {"id": parent.uuid("date-selected"), "tab": "response"},
            "children",
        ),
        Input({"id": parent.uuid("date-slider-selector"), "tab": "response"}, "value"),
    )
    def _update_date(dateidx):
        return parent.vmodel.dates[dateidx]

    @app.callback(
        Output(
            {"id": parent.uuid("vector-select"), "tab": "response"},
            "children",
        ),
        Input(
            {"id": parent.uuid("vector-shortname-select"), "tab": "response"}, "value"
        ),
        Input({"id": parent.uuid("vector-item-select"), "tab": "response"}, "value"),
    )
    def _combine_substrings_to_vector(vector_shortname, item=None):
        if item is None:
            return vector_shortname
        return f"{vector_shortname}:{item}"

    @app.callback(
        Output(
            {"id": parent.uuid("vector-shortname-select"), "tab": "response"}, "options"
        ),
        Output(
            {"id": parent.uuid("vector-shortname-select"), "tab": "response"}, "value"
        ),
        Output({"id": parent.uuid("vector-item-select"), "tab": "response"}, "options"),
        Output({"id": parent.uuid("vector-item-select"), "tab": "response"}, "value"),
        Output(
            {"id": parent.uuid("vector-item-select"), "tab": "response"}, "disabled"
        ),
        Input({"id": parent.uuid("vector-type-select"), "tab": "response"}, "value"),
        Input(parent.uuid("response-parameter-correlation-graph"), "clickData"),
    )
    def _update_vectorlist(vector_type, corr_param_clickdata):
        ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        click_data = parent.uuid("response-parameter-correlation-graph") in ctx

        if click_data:
            vector_selected = corr_param_clickdata.get("points", [{}])[0].get("y")
            vector_type = find_vector_type(parent, vector_selected)
            shortname = vector_selected.split(":")[0]
            item = (
                vector_selected.split(":")[1]
                if "items" in parent.vmodel.vector_groups[vector_type]
                else None
            )
        else:
            shortname = parent.vmodel.vector_groups[vector_type]["shortnames"][0]
            item = (
                parent.vmodel.vector_groups[vector_type]["items"][0]
                if "items" in parent.vmodel.vector_groups[vector_type]
                else None
            )

        shortnames = [
            {"label": i, "value": i}
            for i in parent.vmodel.vector_groups[vector_type]["shortnames"]
        ]
        items = (
            [
                {"label": i, "value": i}
                for i in parent.vmodel.vector_groups[vector_type]["items"]
            ]
            if "items" in parent.vmodel.vector_groups[vector_type]
            else []
        )

        return (
            shortnames,
            shortname,
            items,
            item,
            "items" not in parent.vmodel.vector_groups[vector_type],
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


def uuids_impact(parent, ctx, plot):

    vector = parent.uuid("vector-select") in ctx
    date = parent.uuid("date-selected") in ctx
    parameter = parent.uuid("parameter-select") in ctx
    ensemble = parent.uuid("ensemble-selector") in ctx
    filtered_vectors = (
        parent.uuid("filter-vector-selector") in ctx
        or parent.uuid("vector-type") in ctx
    )

    if plot == "timeseries_fig":
        return any([vector, ensemble])

    if plot == "scatter":
        return any([vector, date, parameter, ensemble])

    if plot == "parameter_correlation":
        return any([filtered_vectors, date, parameter, ensemble])

    if plot == "vector_correlation":
        return any([vector, date, ensemble])


def find_vector_type(parent, vector):
    for vgroup, values in parent.vmodel.vector_groups.items():
        if vector in values["vectors"]:
            return vgroup
    return None


def filter_vectors(parent, vector_types: list = None, vector_items: list = None):
    vectors = list(
        chain.from_iterable(
            [parent.vmodel.vector_groups[vtype]["vectors"] for vtype in vector_types]
        )
    )
    items = list(chain.from_iterable(vector_items))
    filtered_vectors_with_items = [
        v for v in vectors if any(v.split(":")[1] == x for x in items if ":" in v)
    ]
    return [v for v in vectors if v in filtered_vectors_with_items or ":" not in v]


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


def add_date_line(figure, selected_date, show_dateline):
    dateline_idx = [
        idx for idx, trace in enumerate(figure["data"]) if trace["name"] == "Dateline"
    ]
    if dateline_idx:
        if show_dateline:
            figure["data"][dateline_idx[0]].update(
                x=[selected_date, selected_date], text=["", selected_date]
            )
        else:
            figure["data"].pop(int(dateline_idx[0]))

    else:
        if show_dateline:
            ymin = min([min(trace["y"]) for trace in figure["data"]])
            ymax = max([max(trace["y"]) for trace in figure["data"]])
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
        figure["layout"]["shapes"] = max_avg_min_colorbar(
            colors=[
                "rgba(255,18,67, 0.8)",
                "rgba(220,220,220, 0.4)",
                "rgba(62,208,62, 0.8)",
            ],
            pxsize=15,
            yanchor=0.8,
            xanchor=1.03,
            yshift=0.08,
        )

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


def max_avg_min_colorbar(
    colors=None, pxsize=15, yanchor=0.8, xanchor=1.03, yshift=0.08
):
    shapes = []
    for idx, color in enumerate(colors):
        yanchor = yanchor if idx == 0 else yanchor - yshift
        shapes.append(
            dict(
                type="circle",
                xref="paper",
                yref="paper",
                x0=0,
                y0=0,
                x1=pxsize,
                y1=pxsize,
                line=dict(color=color),
                fillcolor=color,
                xsizemode="pixel",
                ysizemode="pixel",
                xanchor=str(xanchor),
                yanchor=str(yanchor),
            )
        )
    return shapes


def update_scatter_graph(df, vector, selected_param):
    colors = [
        "#FF1243",
        "#243746",
        "#007079",
    ]
    return (
        px.scatter(
            df[[vector, selected_param]],
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
