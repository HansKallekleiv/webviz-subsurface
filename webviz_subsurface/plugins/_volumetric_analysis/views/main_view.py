from typing import Callable
from collections import OrderedDict

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizConfigTheme
from webviz_subsurface._models import InplaceVolumesModel
from .filter_view import filter_layout
from .distribution_main_layout import distributions_main_layout
from .selections_view import selections_layout
from .tornado_selections_view import tornado_selections_layout
from .tornado_layout import tornado_main_layout


def main_view(
    get_uuid: Callable,
    volumemodel: InplaceVolumesModel,
    theme: WebvizConfigTheme,
) -> dcc.Tabs:

    tabs = [
        make_tab(
            label="Inplace distributions",
            id_value="voldist",
            children=tab_view_layout(
                main_layout=distributions_main_layout(
                    uuid=get_uuid("main-voldist"), volumemodel=volumemodel
                ),
                selections_details=OrderedDict(
                    Selections={
                        "open": True,
                        "children": [
                            selections_layout(
                                uuid=get_uuid("selections"),
                                tab="voldist",
                                volumemodel=volumemodel,
                                theme=theme,
                            )
                        ],
                    },
                    Filters={
                        "open": True,
                        "children": [
                            filter_layout(
                                uuid=get_uuid("filters"),
                                tab="voldist",
                                volumemodel=volumemodel,
                            )
                        ],
                    },
                ),
            ),
        ),
        make_tab(
            label="Source comparison",
            id_value="src-comp",
            children=tab_view_layout(
                main_layout=[
                    html.Div(
                        "Under development - page for comparing geo/sim/eclipse "
                        "volumes and identify differences",
                        style={"margin": "50px", "font-size": "20px"},
                    )
                ],
                selections_details=OrderedDict(
                    Selections={
                        "open": True,
                        "children": [],
                    },
                    Filters={
                        "open": True,
                        "children": [
                            filter_layout(
                                uuid=get_uuid("filters"),
                                tab="src-comp",
                                volumemodel=volumemodel,
                            )
                        ],
                    },
                ),
            ),
        ),
        make_tab(
            label="Ensemble comparison",
            id_value="ens-comp",
            children=tab_view_layout(
                main_layout=[
                    html.Div(
                        "Under development - page for analyzing volume changes "
                        "and causes between ensembles (e.g between two model revision)",
                        style={"margin": "50px", "font-size": "20px"},
                    )
                ],
                selections_details=OrderedDict(
                    Selections={
                        "open": True,
                        "children": [],
                    },
                    Filters={
                        "open": True,
                        "children": [
                            filter_layout(
                                uuid=get_uuid("filters"),
                                tab="ens-comp",
                                volumemodel=volumemodel,
                            )
                        ],
                    },
                ),
            ),
        ),
    ]

    if volumemodel.sensrun:
        tabs.append(
            make_tab(
                label="Tornadoplots",
                id_value="tornado",
                children=tab_view_layout(
                    main_layout=tornado_main_layout(
                        uuid=get_uuid("main-tornado"),
                    ),
                    selections_details=OrderedDict(
                        Selections={
                            "open": True,
                            "children": [
                                tornado_selections_layout(
                                    uuid=get_uuid("selections"),
                                    tab="tornado",
                                    volumemodel=volumemodel,
                                    theme=theme,
                                )
                            ],
                        },
                        Filters={
                            "open": True,
                            "children": [
                                filter_layout(
                                    uuid=get_uuid("filters"),
                                    tab="tornado",
                                    volumemodel=volumemodel,
                                    filters=[
                                        x
                                        for x in volumemodel.selectors
                                        if x
                                        not in [
                                            "SENSCASE",
                                            "SENSNAME",
                                            "SENSTYPE",
                                            "REAL",
                                            "FLUID_ZONE",
                                        ]
                                    ],
                                )
                            ],
                        },
                    ),
                ),
            )
        )

    return dcc.Tabs(
        id=get_uuid("tabs"),
        value="voldist",
        style={"width": "100%"},
        persistence=True,
        children=tabs,
    )


def make_tab(label: str, id_value: str, children: list) -> dcc.Tab:
    tab_style = {
        "borderBottom": "1px solid #d6d6d6",
        "padding": "6px",
        "fontWeight": "bold",
    }

    tab_selected_style = {
        "borderTop": "1px solid #d6d6d6",
        "borderBottom": "1px solid #d6d6d6",
        "backgroundColor": "#007079",
        "color": "white",
        "padding": "6px",
    }
    return dcc.Tab(
        label=label,
        value=id_value,
        style=tab_style,
        selected_style=tab_selected_style,
        children=children,
    )


def tab_view_layout(main_layout: list, selections_details: OrderedDict) -> wcc.FlexBox:

    detail_sections = []
    for summary, options in selections_details.items():
        detail_sections.append(
            html.Details(
                style={"margin-bottom": "25px"},
                open=options.get("open", True),
                children=[
                    html.Summary(
                        summary,
                        className="webviz-inplace-vol-details-main",
                    ),
                ]
                + options.get("children", []),
            )
        )

    return wcc.FlexBox(
        children=[
            html.Div(
                className="framed",
                style={
                    "height": "91vh",
                    "flex": 1,
                    "fontSize": "0.8em",
                    "overflowY": "auto",
                },
                children=detail_sections,
            ),
            html.Div(
                style={"flex": 6, "height": "91vh"},
                children=main_layout,
            ),
        ]
    )
