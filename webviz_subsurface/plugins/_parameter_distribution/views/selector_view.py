from typing import Union

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc


def ensemble_selector(
    parent, tab: str, multi: bool = False, value: str = None
) -> html.Div:
    return html.Div(
        style={"width": "75%"},
        children=[
            html.H5("Ensemble"),
            dcc.Dropdown(
                id={"id": parent.uuid("ensemble-selector"), "tab": tab},
                options=[
                    {"label": ens, "value": ens} for ens in parent.pmodel.ensembles
                ],
                multi=multi,
                value=value if value is not None else parent.pmodel.ensembles[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def delta_ensemble_selector(parent, tab: str, multi: bool = False) -> html.Div:
    return html.Div(
        style={"width": "75%"},
        children=[
            html.H5("Delta Ensemble"),
            dcc.Dropdown(
                id={"id": parent.uuid("delta-ensemble-selector"), "tab": tab},
                options=[
                    {"label": ens, "value": ens} for ens in parent.pmodel.ensembles
                ],
                multi=multi,
                value=parent.pmodel.ensembles[-1],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def filter_parameter(
    parent,
    tab: str,
    multi: bool = True,
    value: Union[str, float] = None,
    open_details: bool = False,
) -> html.Div:
    return html.Div(
        children=[
            html.H5("PARAMETERS"),
            html.Details(
                open=open_details,
                children=[
                    html.Summary("PARAMETERS"),
                    wcc.Select(
                        id={
                            "id": parent.uuid("filter-parameter"),
                            "tab": tab,
                        },
                        options=[
                            {"label": i, "value": i} for i in parent.pmodel.parameters
                        ],
                        value=value,
                        multi=multi,
                        size=min(30, len(parent.pmodel.parameters)),
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
        ]
    )
