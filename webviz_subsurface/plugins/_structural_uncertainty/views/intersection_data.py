from typing import List, Callable, Dict, Optional

import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import webviz_core_components as wcc

from .modal import open_modal_layout


def intersection_data_layout(
    get_uuid: Callable,
    surface_attributes: List[str],
    surface_names: List[str],
    ensembles: List[str],
    use_wells: bool,
    well_names: List[str],
    surface_geometry: Dict,
    initial_settings: Dict,
) -> html.Div:
    """Layout for selecting intersection data"""
    return html.Div(
        id=get_uuid("intersection-data-wrapper"),
        children=[
            html.Div(
                style={
                    "padding-bottom": "10px",
                    "border-bottom-style": "solid",
                    "border-width": "thin",
                    "border-color": "grey",
                },
                id=get_uuid("intersection-source-wrapper"),
                children=[
                    html.Span("Intersection source", style={"font-weight": "bold"}),
                    source_layout(
                        uuid=get_uuid("intersection_data"),
                        use_wells=use_wells,
                    ),
                    well_layout(
                        uuid=get_uuid("intersection_data"),
                        well_names=well_names,
                        value=initial_settings.get(
                            "well",
                            well_names[0] if use_wells else None,
                        ),
                    ),
                    xline_layout(
                        uuid=get_uuid("intersection_data"),
                        surface_geometry=surface_geometry,
                    ),
                    yline_layout(
                        uuid=get_uuid("intersection_data"),
                        surface_geometry=surface_geometry,
                    ),
                ],
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
            blue_apply_button(
                uuid=get_uuid("apply-intersection-data-selections"),
                title="Update intersection",
            ),
            html.Details(
                style={
                    "marginTop": "15px",
                    "marginBottom": "10px",
                },
                open=False,
                children=[
                    html.Summary(
                        style={
                            "font-size": "20px",
                            "font-weight": "bold",
                        },
                        children="Settings",
                    ),
                    html.Div(
                        children=[
                            range_layout(
                                uuid=get_uuid("intersection_data"),
                                distance=initial_settings.get("distance", 20),
                                nextend=initial_settings.get("nextend", 200),
                            ),
                            options_layout(
                                uuid=get_uuid("intersection-graph-layout-options"),
                                initial_layout=initial_settings.get(
                                    "intersection_layout", {}
                                ),
                            ),
                            open_modal_layout(
                                modal_id="color",
                                uuid=get_uuid("modal"),
                                title="Intersection colors",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def source_layout(uuid: str, use_wells: bool = True) -> html.Div:
    options = [
        {"label": "Intersect polyline from Surface A", "value": "polyline"},
        {"label": "Intersect x-line from Surface A", "value": "xline"},
        {"label": "Intersect y-line from Surface A", "value": "yline"},
    ]
    if use_wells:
        options.append({"label": "Intersect well", "value": "well"})
    return html.Div(
        style={"display": "none"} if not use_wells else {},
        children=dcc.Dropdown(
            id={"id": uuid, "element": "source"},
            options=options,
            value="well" if use_wells else "surface",
            clearable=False,
            persistence=True,
            persistence_type="session",
        ),
    )


def well_layout(
    uuid: str, well_names: List[str], value: Optional[str] = None
) -> html.Div:
    return html.Div(
        style={
            "display": "none",
        },
        id={"id": uuid, "element": "well-wrapper"},
        children=html.Label(
            children=[
                html.Span("Well:", style={"font-weight": "bold"}),
                dcc.Dropdown(
                    id={"id": uuid, "element": "well"},
                    options=[{"label": well, "value": well} for well in well_names],
                    value=value,
                    clearable=False,
                    persistence=True,
                    persistence_type="session",
                ),
            ]
        ),
    )


def xline_layout(uuid: str, surface_geometry: Dict) -> html.Div:
    return html.Div(
        style={
            "display": "none",
        },
        id={"id": uuid, "element": "xline-wrapper"},
        children=[
            html.Label("X-Line:"),
            wcc.FlexBox(
                style={"fontSize": "0.8em"},
                children=[
                    dbc.Input(
                        id={"id": uuid, "cross-section": "xline", "element": "value"},
                        style={"flex": 3, "minWidth": "100px"},
                        type="number",
                        value=round(surface_geometry["xmin"]),
                        min=round(surface_geometry["xmin"]),
                        max=round(surface_geometry["xmax"]),
                        step=50,
                        persistence=True,
                        persistence_type="session",
                    ),
                    dbc.Label(style={"flex": 1, "minWidth": "20px"}, children="Step:"),
                    dbc.Input(
                        id={"id": uuid, "cross-section": "xline", "element": "step"},
                        style={"flex": 2, "minWidth": "20px"},
                        value=50,
                        type="number",
                        min=1,
                        max=round(surface_geometry["xmax"])
                        - round(surface_geometry["xmin"]),
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
        ],
    )


def yline_layout(uuid: str, surface_geometry: Dict) -> html.Div:
    return html.Div(
        style={
            "display": "none",
        },
        id={"id": uuid, "element": "yline-wrapper"},
        children=[
            html.Label("Y-Line:"),
            wcc.FlexBox(
                style={"fontSize": "0.8em"},
                children=[
                    dbc.Input(
                        id={"id": uuid, "cross-section": "yline", "element": "value"},
                        style={"flex": 3, "minWidth": "100px"},
                        type="number",
                        value=round(surface_geometry["ymin"]),
                        min=round(surface_geometry["ymin"]),
                        max=round(surface_geometry["ymax"]),
                        step=50,
                        persistence=True,
                        persistence_type="session",
                    ),
                    dbc.Label(style={"flex": 1, "minWidth": "20px"}, children="Step:"),
                    dbc.Input(
                        id={"id": uuid, "cross-section": "yline", "element": "step"},
                        style={"flex": 2, "minWidth": "20px"},
                        value=50,
                        type="number",
                        min=1,
                        max=round(surface_geometry["ymax"])
                        - round(surface_geometry["ymin"]),
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
        ],
    )


def options_layout(uuid: str, initial_layout: Optional[Dict] = None) -> html.Div:
    value = ["auto_yrange_polyline"]
    if initial_layout is not None:
        if initial_layout.get("uirevision"):
            value.append("uirevision")
    options = [
        {"label": "Keep zoom state", "value": "uirevision"},
        {"label": "Auto z-range (polyline)", "value": "auto_yrange_polyline"},
    ]

    return html.Div(
        style={
            "marginTop": "10px",
            "marginBottom": "10px",
        },
        children=[
            dcc.Checklist(
                id=uuid,
                options=options,
                value=value,
                persistence=True,
                persistence_type="session",
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
        style={"marginTop": "5px"},
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
        style={"marginTop": "5px"},
        children=html.Label(
            children=[
                html.Span("Ensembles", style={"font-weight": "bold"}),
                wcc.Select(
                    id={"id": uuid, "element": "ensembles"},
                    options=[{"label": ens, "value": ens} for ens in ensemble_names],
                    value=value,
                    size=2,
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
                    labelStyle={
                        "display": "inline-block",
                        "margin-right": "5px",
                    },
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


def range_layout(uuid: str, distance: float, nextend: int) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                children=[
                    html.Label(
                        "Resolution (m) ",
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
                        "Extension (m) ",
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
        ],
    )


def html_details(
    summary: str,
    children: list,
    open_details: bool = False,
) -> html.Div:
    return html.Div(
        html.Details(
            style={"margin-bottom": "25px"},
            open=open_details,
            children=[
                html.Summary(
                    children=summary,
                    style={
                        "color": "#ff1243",
                        "border-bottom-style": "solid",
                        "border-width": "thin",
                        "border-color": "#ff1243",
                        "font-weight": "bold",
                        "font-size": "20px",
                        "margin-bottom": "15px",
                    },
                )
            ]
            + children,
        )
    )
