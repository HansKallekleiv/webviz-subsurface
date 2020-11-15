import dash_html_components as html

import webviz_core_components as wcc
from .filter_view import filter_view
from .plot_view import plot_view


def main_view(parent) -> wcc.FlexBox:
    return wcc.FlexBox(
        children=[
            html.H1(style={"width": "100%"}, children="New volumetrics plugin"),
            html.Div(style={"flex": 1}, children=filter_view(parent=parent)),
            html.Div(style={"flex": 4}, children=plot_view(parent=parent)),
        ]
    )
