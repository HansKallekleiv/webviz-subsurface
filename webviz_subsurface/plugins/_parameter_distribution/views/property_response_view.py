import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
import webviz_subsurface_components as wsc

from .selector_view import (
    ensemble_selector,
)


def timeseries_view(parent) -> html.Div:
    return html.Div(
        style={"height": "38vh"},
        children=[
            html.Div(
                children=[
                    dcc.Dropdown(
                        id=parent.uuid("property-response-vector-select"),
                        options=parent.vmodel.dropdown_options,
                        clearable=False,
                        placeholder="Select a vector from the list...",
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
            wcc.Graph(
                id=parent.uuid("property-response-vector-graph"),
                config={"displayModeBar": False},
                style={"height": "35vh"},
            ),
        ],
    )


def correlation_view(parent) -> html.Div:
    return html.Div(
        style={"flex": 2, "height": "80vh"},
        className="framed",
        children=[
            wcc.Graph(
                style={"height": "78vh"},
                id=parent.uuid("property-response-correlation-graph"),
            )
        ],
    )


def filter_correlated_parameter(parent) -> html.Div:
    return html.Div(
        [
            html.H5("Filter on property"),
            html.Div(
                style={"marginBottom": "10px", "marginTop": "10px", "fontSize": "1rem"},
                children=dcc.Dropdown(
                    id=parent.uuid("property-response-correlated-filter"),
                    options=[
                        {"label": label, "value": label}
                        for label in parent.pmodel.get_labels()
                    ],
                    placeholder="Select a label to filter on...",
                    persistence=True,
                    persistence_type="session",
                ),
            ),
            dcc.RangeSlider(
                id=parent.uuid("property-response-correlated-slider"),
                disabled=True,
                persistence=True,
                persistence_type="session",
            ),
        ]
    )


def selector_view(parent) -> html.Div:
    return html.Div(
        style={"height": "80vh", "overflowY": "auto"},
        className="framed",
        children=[
            html.Div(
                children=[
                    ensemble_selector(parent=parent, tab="response"),
                ]
            ),
            html.Div(),
        ],
    )


def property_response_view(parent) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            html.Div(style={"flex": 1}, children=selector_view(parent=parent)),
            html.Div(
                style={"flex": 2, "height": "80vh"},
                className="framed",
                children=[
                    html.Div(
                        style={"height": "38vh"},
                        children=timeseries_view(parent=parent),
                    ),
                    html.Div(
                        style={"height": "39vh"},
                        children=None,
                    ),
                ],
            ),
            correlation_view(parent=parent),
        ],
    )
