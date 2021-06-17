from typing import List, Optional

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface._models import InplaceVolumesModel


def filter_layout(
    uuid: str,
    volumemodel: InplaceVolumesModel,
    filters: Optional[list] = None,
    tab="None",
) -> html.Div:
    """Layout for selecting intersection data"""
    return html.Div(
        children=[
            filter_dropdowns(
                uuid=uuid, tab=tab, volumemodel=volumemodel, filters=filters
            ),
            realization_filters(uuid=uuid, tab=tab, volumemodel=volumemodel),
        ]
    )


def filter_dropdowns(
    uuid: str, volumemodel: InplaceVolumesModel, tab, filters: Optional[list] = None
) -> html.Div:
    """Makes dropdowns for each selector"""
    dropdowns: List[html.Div] = []
    filters = filters if filters is not None else volumemodel.selectors
    if "REAL" in filters:
        filters.remove("REAL")
    for selector in filters:
        elements = list(volumemodel.dataframe[selector].unique())

        dropdowns.append(
            html.Div(
                style={"display": "inline" if len(elements) > 1 else "none"},
                children=html.Details(
                    open=True,
                    children=[
                        html.Summary(
                            selector.lower().capitalize(), style={"font-weight": "bold"}
                        ),
                        wcc.Select(
                            id={"id": uuid, "tab": tab, "selector": selector},
                            options=[{"label": i, "value": i} for i in elements],
                            value=elements,
                            multi=True,
                            size=min(15, len(elements)),
                            persistence=True,
                            persistence_type="session",
                        ),
                    ],
                ),
            )
        )
    return html.Div(dropdowns)


def realization_filters(uuid: str, tab, volumemodel) -> html.Div:
    reals = volumemodel.realizations
    return html.Div(
        style={"margin-top": "15px"},
        children=[
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    html.Span(
                        "Realizations: ",
                        style={"font-weight": "bold"},
                    ),
                    html.Span(
                        id={"id": uuid, "tab": tab, "element": "real_text"},
                        style={"margin-left": "10px"},
                        children=f"{min(reals)}-{max(reals)}",
                    ),
                ],
            ),
            html.Div(
                children=dcc.RadioItems(
                    id={"id": uuid, "tab": tab, "element": "real-selector-option"},
                    options=[
                        {"label": "Range", "value": "range"},
                        {"label": "Select", "value": "select"},
                    ],
                    value="range",
                    labelStyle={
                        "display": "inline-block",
                        "margin": "5px",
                    },
                ),
            ),
            html.Div(
                id={"id": uuid, "tab": tab, "element": "real-slider-wrapper"},
                children=dcc.RangeSlider(
                    id={
                        "id": uuid,
                        "tab": tab,
                        "component_type": "range",
                    },
                    value=[min(reals), max(reals)],
                    min=min(reals),
                    max=max(reals),
                    marks={str(i): {"label": str(i)} for i in [min(reals), max(reals)]},
                ),
            ),
            html.Div(
                style={"display": "none"},
                children=wcc.Select(
                    id={"id": uuid, "tab": tab, "selector": "REAL"},
                    options=[{"label": i, "value": i} for i in reals],
                    value=reals,
                ),
            ),
        ],
    )
