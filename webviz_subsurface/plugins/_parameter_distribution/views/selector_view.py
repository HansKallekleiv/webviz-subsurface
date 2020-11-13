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


def vector_selector(parent, tab: str) -> html.Div:
    return html.Div(
        style={"width": "90%", "font-size": "15px"},
        children=[
            html.H5("Vector"),
            html.Span("Vector type:", style={"font-weight": "bold"}),
            dcc.RadioItems(
                id={"id": parent.uuid("vector-type-select"), "tab": tab},
                options=[
                    {"label": i, "value": i} for i in parent.vmodel.vector_types.keys()
                ],
                value="Field",
                style={"background-color": "white"},
                labelStyle={"display": "inline-block", "margin-right": "10px"},
            ),
            html.Div(
                style={"width": "70%", "margin-top": "5px"},
                children=[
                    html.Span("Vector:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id={"id": parent.uuid("vector-main-select"), "tab": tab},
                        options=[
                            {"label": i, "value": i}
                            for i in parent.vmodel.vector_groups["Field"][
                                "vectors_main"
                            ]
                        ],
                        value=parent.vmodel.vector_groups["Field"]["vectors_main"][0],
                        placeholder="Select a vector...",
                        clearable=False,
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
            html.Div(
                style={"width": "70%"},
                children=[
                    dcc.Dropdown(
                        id={"id": parent.uuid("vector-sub-select"), "tab": tab},
                        disabled=True,
                        placeholder="Subselection...",
                        clearable=False,
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
            html.Div(
                id={"id": parent.uuid("vector-select"), "tab": tab},
                style={"display": "none"},
            ),
        ],
    )


def parameter_selector(parent, tab: str) -> html.Div:
    return html.Div(
        style={"width": "90%", "font-size": "15px"},
        children=[
            html.H5("Parameter"),
            dcc.Dropdown(
                id={"id": parent.uuid("parameter-select"), "tab": tab},
                options=[{"label": i, "value": i} for i in parent.pmodel.parameters],
                placeholder="Select a parameter...",
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
) -> html.Div:
    return html.Div(
        style={"margin-top": "25px"},
        children=[
            html.H5("Parameters"),
            html.Div(
                style={"font-size": "15px"},
                children=[
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
                        size=min(25, len(parent.pmodel.parameters)),
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
        ],
    )


def make_filter(
    parent,
    tab: str,
    df_column: str,
    column_values: list,
    multi: bool = True,
    value: Union[str, float] = None,
    open_details: bool = False,
) -> html.Div:
    return html.Div(
        children=html.Details(
            open=open_details,
            style={"margin-top": "10px"},
            children=[
                html.Summary(df_column.lower().capitalize()),
                wcc.Select(
                    id={
                        "id": parent.uuid("filter_vector_selector"),
                        "tab": tab,
                        "selector": df_column,
                    },
                    options=[{"label": i, "value": i} for i in column_values],
                    value=[value] if value is not None else column_values,
                    multi=multi,
                    size=min(15, len(column_values)),
                    persistence=True,
                    persistence_type="session",
                ),
            ],
        ),
    )


def filter_vector_selector(
    parent,
    tab: str,
    multi: bool = True,
    value: Union[str, float] = None,
    open_details: bool = False,
) -> html.Div:
    return html.Div(
        style={"width": "90%", "margin-top": "25px"},
        children=[
            html.H5("Filters"),
            html.Div(
                children=[
                    html.Span("Vector type:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id={
                            "id": parent.uuid("vector-type"),
                            "tab": tab,
                        },
                        options=[
                            {"label": i, "value": i}
                            for i in parent.vmodel.vector_types.keys()
                        ],
                        value=[
                            x
                            for x in ["Field", "Well"]
                            if x in parent.vmodel.vector_types
                        ],
                        clearable=False,
                        style={"background-color": "white"},
                        multi=True,
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
            html.Div(
                children=[
                    make_filter(
                        parent=parent,
                        tab=tab,
                        df_column=vtype,
                        column_values=vlist,
                        multi=multi,
                        value=value,
                        open_details=open_details,
                    )
                    for vtype, vlist in parent.vmodel.vector_selectors.items()
                ]
            ),
        ],
    )
