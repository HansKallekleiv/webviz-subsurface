from typing import List, Callable, Dict

import dash_core_components as dcc
import dash_html_components as html
import webviz_core_components as wcc

from .modal import open_modal_layout


def intersection_data_layout(
    get_uuid: Callable,
    surface_attributes: List[str],
    surface_names: List[str],
    ensembles: List[str],
    initial_settings: Dict,
) -> html.Div:
    """Layout for selecting intersection data"""
    return html.Div(
        id=get_uuid("intersection-data-wrapper"),
        children=[
            html.H6(
                "Intersection data",
                style={
                    "textAlign": "center",
                    "fontWeight": "bold",
                },
            ),
            surface_attribute_layout(
                uuid=get_uuid("intersection_data"),
                surface_attributes=surface_attributes,
                value=initial_settings.get(
                    "surface_attribute",
                    surface_attributes[0],
                ),
            ),
            surface_names_layout(
                uuid=get_uuid("intersection_data"),
                surface_names=surface_names,
                value=initial_settings.get("surface_names", [surface_names[0]]),
            ),
            ensemble_layout(
                uuid=get_uuid("intersection_data"),
                ensemble_names=ensembles,
                value=initial_settings.get("ensembles", [ensembles[0]]),
            ),
            statistical_layout(
                uuid=get_uuid("intersection_data"),
                value=initial_settings.get("calculation", ["Mean", "Min", "Max"]),
            ),
            html.Div(
                style={"marginBottom": "10px"},
                children=[
                    range_layout(
                        uuid=get_uuid("intersection_data"),
                        distance=initial_settings.get("distance", 20),
                        atleast=initial_settings.get("atleast", 5),
                        nextend=initial_settings.get("nextend", 2),
                    ),
                ],
            ),
            open_modal_layout(
                modal_id="color",
                uuid=get_uuid("modal"),
                title="Intersection colors",
            ),
            blue_apply_button(
                uuid=get_uuid("apply-intersection-data-selections"),
                title="Update intersection",
            ),
        ],
    )


def surface_attribute_layout(
    uuid: str, surface_attributes: List[str], value: str
) -> html.Div:
    return html.Div(
        style={"marginTop": "10px"},
        children=html.Label(
            children=[
                html.Span("Surface attribute", style={"font-weight": "bold"}),
                dcc.Dropdown(
                    id={"id": uuid, "element": "surface_attribute"},
                    options=[
                        {"label": attribute, "value": attribute}
                        for attribute in surface_attributes
                    ],
                    value=value,
                    clearable=False,
                    multi=False,
                    persistence=True,
                    persistence_type="session",
                ),
            ]
        ),
    )


def surface_names_layout(
    uuid: str, surface_names: List[str], value: List[str]
) -> html.Div:
    return html.Div(
        style={"marginTop": "10px"},
        children=html.Label(
            children=[
                html.Span("Surfacenames", style={"font-weight": "bold"}),
                wcc.Select(
                    id={"id": uuid, "element": "surface_names"},
                    options=[
                        {"label": attribute, "value": attribute}
                        for attribute in surface_names
                    ],
                    value=value,
                    multi=True,
                    size=5,
                    persistence=True,
                    persistence_type="session",
                ),
            ]
        ),
    )


def ensemble_layout(uuid: str, ensemble_names: List[str], value: List[str]) -> html.Div:
    return html.Div(
        style={"marginTop": "10px"},
        children=html.Label(
            children=[
                html.Span("Ensembles", style={"font-weight": "bold"}),
                wcc.Select(
                    id={"id": uuid, "element": "ensembles"},
                    options=[{"label": ens, "value": ens} for ens in ensemble_names],
                    value=value,
                    size=4,
                    persistence=True,
                    persistence_type="session",
                ),
            ]
        ),
    )


def statistical_layout(uuid: str, value: List[str]) -> html.Div:
    return html.Div(
        style={"marginTop": "10px"},
        children=html.Label(
            children=[
                html.Span("Show surfaces:", style={"font-weight": "bold"}),
                dcc.Checklist(
                    id={"id": uuid, "element": "calculation"},
                    options=[
                        {"label": "Mean", "value": "Mean"},
                        {"label": "Min", "value": "Min"},
                        {"label": "Max", "value": "Max"},
                        {"label": "Realizations", "value": "Realizations"},
                        {
                            "label": "Uncertainty envelope (slow)",
                            "value": "Uncertainty envelope",
                        },
                    ],
                    value=value,
                    persistence=True,
                    persistence_type="session",
                ),
            ]
        ),
    )


def blue_apply_button(uuid: str, title: str) -> html.Div:
    return html.Button(
        title,
        className="webviz-structunc-blue-apply-btn",
        id=uuid,
    )


def range_layout(uuid: str, distance: float, atleast: int, nextend: int) -> html.Div:
    return html.Div(
        children=[
            html.Label(
                style={"font-weight": "bold"}, children="Intersection settings:"
            ),
            html.Div(
                children=[
                    html.Label(
                        "Horizontal distance between points",
                        className="webviz-structunc-range-label",
                    ),
                    dcc.Input(
                        className="webviz-structunc-range-input",
                        id={"id": uuid, "element": "distance"},
                        debounce=True,
                        type="number",
                        required=True,
                        value=distance,
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
            html.Div(
                children=[
                    html.Label(
                        "Minimum number of points",
                        className="webviz-structunc-range-label",
                    ),
                    dcc.Input(
                        className="webviz-structunc-range-input",
                        id={"id": uuid, "element": "atleast"},
                        debounce=True,
                        type="number",
                        required=True,
                        value=atleast,
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
            html.Div(
                children=[
                    html.Label(
                        "Extension (distance * nextend)",
                        className="webviz-structunc-range-label",
                    ),
                    dcc.Input(
                        className="webviz-structunc-range-input",
                        id={"id": uuid, "element": "nextend"},
                        debounce=True,
                        type="number",
                        required=True,
                        value=nextend,
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
        ]
    )
