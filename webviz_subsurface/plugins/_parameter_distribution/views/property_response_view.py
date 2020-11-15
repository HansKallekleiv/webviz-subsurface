import dash_html_components as html
import webviz_core_components as wcc

from .selector_view import (
    ensemble_selector,
    filter_vector_selector,
    vector_selector,
    parameter_selector,
    date_selector,
)


def timeseries_view(parent) -> html.Div:
    return html.Div(
        style={"height": "38vh"},
        children=[
            html.Div(
                children=[
                    wcc.Graph(
                        id=parent.uuid("property-response-vector-graph"),
                        config={"displayModeBar": False},
                        style={"height": "38vh"},
                    ),
                ]
            ),
        ],
    )


def correlation_view(parent) -> html.Div:
    return html.Div(
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
    )


def selector_view(parent) -> html.Div:
    return html.Div(
        style={"height": "80vh", "overflowY": "auto", "font-size": "15px"},
        className="framed",
        children=[
            html.Div(
                children=[
                    html.H5("Selections"),
                    ensemble_selector(parent=parent, tab="response"),
                    vector_selector(parent=parent, tab="response"),
                    date_selector(parent=parent, tab="response"),
                    parameter_selector(parent=parent, tab="response"),
                    filter_vector_selector(parent=parent, tab="response"),
                ],
            )
        ],
    )


def property_response_view(parent) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            html.Div(
                style={
                    "flex": 1,
                },
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
            correlation_view(parent=parent),
        ],
    )
