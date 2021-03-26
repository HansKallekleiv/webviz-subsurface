from typing import List

import dash_core_components as dcc
import dash_html_components as html
import webviz_core_components as wcc


def map_data_layout(
    uuid: str,
    surface_attributes: List[str],
    surface_names: List[str],
    ensembles: List[str],
    realizations: List[int],
    use_wells: bool,
) -> wcc.FlexBox:
    """Layout for the map data modal"""
    return wcc.FlexBox(
        style={"fontSize": "0.8em"},
        children=[
            html.Div(
                style={"minWidth": "200px", "flex": 1},
                children=[
                    html.Label(
                        "Surface A", style={"fontWeight": "bold", "textAlign": "center"}
                    ),
                    make_map_selectors(
                        uuid=uuid,
                        surface_attributes=surface_attributes,
                        surface_names=surface_names,
                        ensembles=ensembles,
                        realizations=realizations,
                        use_wells=use_wells,
                        map_id="map",
                    ),
                ],
            ),
            html.Div(
                style={"minWidth": "200px", "flex": 1},
                children=[
                    html.Label(
                        "Surface B", style={"fontWeight": "bold", "textAlign": "center"}
                    ),
                    make_map_selectors(
                        uuid=uuid,
                        surface_attributes=surface_attributes,
                        surface_names=surface_names,
                        ensembles=ensembles,
                        realizations=realizations,
                        use_wells=use_wells,
                        map_id="map2",
                    ),
                ],
            ),
        ],
    )


def make_map_selectors(
    uuid: str,
    map_id: str,
    surface_attributes: List[str],
    surface_names: List[str],
    ensembles: List[str],
    realizations: List[int],
    use_wells: bool,
) -> html.Div:
    return html.Div(
        children=[
            html.Label(
                "Surface attribute", style={"fontSize": "0.8em", "fontWeight": "bold"}
            ),
            dcc.Dropdown(
                style={
                    "padding": "5px",
                },
                id={"id": uuid, "map_id": map_id, "element": "surfaceattribute"},
                options=[{"label": val, "value": val} for val in surface_attributes],
                value=surface_attributes[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
            html.Label(
                "Surface name", style={"fontSize": "0.8em", "fontWeight": "bold"}
            ),
            dcc.Dropdown(
                style={
                    "padding": "5px",
                },
                id={"id": uuid, "map_id": map_id, "element": "surfacename"},
                options=[{"label": val, "value": val} for val in surface_names],
                value=surface_names[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
            html.Label("Ensemble", style={"fontSize": "0.8em", "fontWeight": "bold"}),
            dcc.Dropdown(
                style={
                    "padding": "5px",
                },
                id={"id": uuid, "map_id": map_id, "element": "ensemble"},
                options=[{"label": val, "value": val} for val in ensembles],
                value=ensembles[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
            html.Label(
                "Calculation/Realization",
                style={"fontSize": "0.8em", "fontWeight": "bold"},
            ),
            dcc.Dropdown(
                style={
                    "padding": "5px",
                },
                id={"id": uuid, "map_id": map_id, "element": "calculation"},
                options=[
                    {"label": val, "value": val}
                    for val in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]
                    + [str(real) for real in realizations]
                ],
                value=realizations[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
            dcc.Checklist(
                style={"marginTop": "10px"},
                id={"id": uuid, "map_id": map_id, "element": "options"},
                options=[
                    {"label": "Calculate well intersections", "value": "intersect_well"}
                ]
                if use_wells
                else [],
                value=[],
                persistence=True,
                persistence_type="session",
            ),
        ]
    )
