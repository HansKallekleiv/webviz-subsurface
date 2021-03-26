from typing import List, Optional, Dict, Callable
import dash_core_components as dcc
import dash_html_components as html


def intersection_source_layout(
    get_uuid: Callable,
    use_wells: bool,
    well_names: List[str],
    initial_settings: Dict,
) -> html.Div:
    """Layout for selecting intersection source"""
    return html.Div(
        id=get_uuid("intersection-source-wrapper"),
        children=[
            html.H6(
                "Intersection source",
                style={
                    "textAlign": "center",
                    "fontWeight": "bold",
                },
            ),
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
            options_layout(
                uuid=get_uuid("intersection-graph-layout-options"),
                initial_layout=initial_settings.get("intersection_layout", {}),
            ),
        ],
    )


def source_layout(uuid: str, use_wells: bool = True) -> html.Div:
    options = [
        {"label": "Intersect polyline from Surface A", "value": "surface"},
    ]
    if use_wells:
        options.append({"label": "Intersect well", "value": "well"})
    return html.Div(
        style={"display": "none"} if not use_wells else {},
        children=dcc.RadioItems(
            labelStyle={"display": "inline-block"},
            id={"id": uuid, "element": "source"},
            options=options,
            value="well" if use_wells else "surface",
            persistence=True,
            persistence_type="session",
        ),
    )


def well_layout(
    uuid: str, well_names: List[str], value: Optional[str] = None
) -> html.Div:
    return html.Div(
        style={"display": "none"} if value is None else {},
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
