import dash_html_components as html
import dash_core_components as dcc
import dash_table
import webviz_core_components as wcc
import webviz_subsurface_components as wsc

from .selector_view import ensemble_selector, delta_ensemble_selector, filter_parameter


def selector_view(parent) -> html.Div:
    return html.Div(
        style={"height": "80vh", "overflowY": "auto"},
        className="framed",
        children=[
            html.Div(
                children=[
                    ensemble_selector(parent=parent, tab="delta"),
                    delta_ensemble_selector(parent=parent, tab="delta"),
                    filter_parameter(
                        parent=parent,
                        tab="delta",
                        value=[parent.pmodel.parameters[0]],
                        open_details=True,
                    ),
                ]
            ),
        ],
    )


def delta_avg_view() -> html.Div:
    return html.Div(
        style={"flex": 1},
        children=[],
    )


def property_delta_view(parent) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            html.Div(style={"flex": 1}, children=selector_view(parent=parent)),
            html.Div(
                style={"flex": 4, "height": "80vh"},
                className="framed",
                children=[
                    wcc.Graph(
                        id=parent.uuid("delta-bar-graph"),
                        config={"displayModeBar": False},
                        style={"height": "75vh"},
                    ),
                ],
            ),
            html.Div(
                style={"flex": 4, "height": "80vh"},
                className="framed",
                children=[
                    html.Div(id=parent.uuid("delta-table-wrapper")),
                ],
            ),
        ],
    )


def table_view(data, columns) -> html.Div:
    return html.Div(
        style={"fontSize": "1rem"},
        children=dash_table.DataTable(
            sort_action="native",
            page_action="native",
            filter_action="native",
            style_table={
                "height": "74vh",
                "overflow": "auto",
            },
            data=data,
            columns=columns,
        ),
    )
