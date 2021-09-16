from typing import Callable

from dash import html, dcc
import webviz_core_components as wcc
from webviz_config import WebvizConfigTheme
from .selections_view import table_selections_layout


def main_view(
    get_uuid: Callable, theme: WebvizConfigTheme, responses, filters, dframe
) -> dcc.Tabs:

    tabs = [
        wcc.Tab(
            label="Plots",
            value="plots",
            children=tab_view_layout(
                main_layout=html.Div(id=get_uuid("main-plots")),
                sidebar_layout=[html.Div(id=get_uuid("selections-plots"))],
            ),
        ),
        wcc.Tab(
            label="Tables",
            value="tables",
            children=tab_view_layout(
                main_layout=html.Div(id=get_uuid("main-table")),
                sidebar_layout=[
                    table_selections_layout(
                        uuid=get_uuid("selections-table"),
                        responses=responses,
                        filters=filters,
                        dframe=dframe,
                    )
                ],
            ),
        ),
    ]

    return wcc.Tabs(
        id=get_uuid("tabs"),
        value="tables",
        style={"width": "100%"},
        persistence=True,
        children=tabs,
    )


def tab_view_layout(main_layout: list, sidebar_layout: list) -> wcc.FlexBox:
    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style={"flex": 1, "height": "91vh"},
                children=sidebar_layout,
            ),
            html.Div(
                style={"flex": 6, "height": "91vh"},
                children=main_layout,
            ),
        ]
    )
