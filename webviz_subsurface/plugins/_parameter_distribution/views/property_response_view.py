import dash_html_components as html
import webviz_core_components as wcc
import dash_core_components as dcc
from .selector_view import (
    ensemble_selector,
    filter_vector_selector,
    vector_selector,
    parameter_selector,
    date_selector,
    plot_options,
    html_details,
    color_selector,
)


def timeseries_view(parent) -> html.Div:
    return html.Div(
        children=[
            wcc.Graph(
                id=parent.uuid("property-response-vector-graph"),
                config={"displayModeBar": False},
                style={"height": "38vh"},
            ),
        ],
    )


def selector_view(parent) -> html.Div:

    return html.Div(
        style={
            "height": "80vh",
            "overflowY": "auto",
            "font-size": "15px",
        },
        className="framed",
        children=[
            html_details(
                summary="Selections",
                children=[
                    ensemble_selector(parent=parent, tab="response"),
                    vector_selector(parent=parent, tab="response"),
                    date_selector(parent=parent, tab="response"),
                    parameter_selector(parent=parent, tab="response"),
                ],
                open_details=True,
            ),
            html_details(
                summary="Filters",
                children=[filter_vector_selector(parent=parent, tab="response")],
                open_details=False,
            ),
            html_details(
                summary="Options",
                children=[
                    plot_options(parent=parent, tab="response"),
                    color_selector(
                        parent=parent, tab="response", colorscales=["BrBG", "RdGy"]
                    ),
                    "Opacity:",
                    dcc.Input(
                        id="input_range",
                        type="number",
                        min=0,
                        max=1,
                        step=0.1,
                        value=0.7,
                        style={"width": "10%"},
                    ),
                ],
                open_details=False,
            ),
        ],
    )


def property_response_view(parent) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            html.Div(
                style={"flex": 1, "width": "90%"},
                children=selector_view(parent=parent),
            ),
            html.Div(
                style={"flex": 2, "height": "80vh"},
                children=[
                    html.Div(
                        className="framed",
                        style={"height": "38vh"},
                        children=timeseries_view(parent=parent),
                    ),
                    html.Div(
                        className="framed",
                        style={"height": "38vh"},
                        children=[
                            wcc.Graph(
                                id=parent.uuid("property-response-vector-scatter"),
                                config={"displayModeBar": False},
                                style={"height": "38vh"},
                            )
                        ],
                    ),
                ],
            ),
            html.Div(
                style={"flex": 2, "height": "80vh"},
                children=[
                    html.Div(
                        className="framed",
                        style={"height": "38vh"},
                        children=[
                            wcc.Graph(
                                config={"displayModeBar": False},
                                style={"height": "38vh"},
                                id=parent.uuid("property-response-correlation-graph"),
                            ),
                        ],
                    ),
                    html.Div(
                        className="framed",
                        style={"height": "38vh"},
                        children=[
                            wcc.Graph(
                                config={"displayModeBar": False},
                                style={"height": "38vh"},
                                id=parent.uuid("response-parameter-correlation-graph"),
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
