import dash_html_components as html
import webviz_core_components as wcc


def plot_view(parent) -> html.Div:
    return html.Div(children=wcc.Graph(id=parent.uuid("plot")))
