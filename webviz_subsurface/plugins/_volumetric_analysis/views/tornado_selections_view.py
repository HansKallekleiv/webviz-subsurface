from typing import List, Optional
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizConfigTheme
from webviz_subsurface._models import InplaceVolumesModel


def tornado_selections_layout(
    uuid: str, volumemodel: InplaceVolumesModel, theme: WebvizConfigTheme, tab="none"
) -> html.Div:
    """Layout for selecting intersection data"""
    return html.Div(
        children=[
            tornado_controls_layout(uuid, tab, volumemodel),
            settings_layout(uuid, tab, theme, volumemodel),
        ]
    )


def tornado_controls_layout(
    uuid: str, tab, volumemodel: InplaceVolumesModel
) -> html.Details:

    return html.Details(
        className="webviz-inplace-vol-plotselect",
        style={"margin-top": "20px"},
        open=True,
        children=[
            html.Summary(
                style={"font-size": "15px", "font-weight": "bold"},
                children="TORNADO CONTROLS",
            ),
            html.Div(
                style={"padding": "10px"},
                children=[
                    create_dropdown(
                        selector="Volume response",
                        options=[
                            x for x in ["STOIIP", "GIIP"] if x in volumemodel.responses
                        ],
                        uuid=uuid,
                        tab=tab,
                    ),
                    create_dropdown(
                        selector="Scale",
                        options=[
                            {"label": "Delta (%)", "value": "Percentage"},
                            {"label": "Delta", "value": "Absolute"},
                            {"label": "True value", "value": "True"},
                        ],
                        uuid=uuid,
                        tab=tab,
                    ),
                    html.Div(
                        style={"margin-top": "10px"},
                        children=create_select(
                            selector="Bulk sensitivities",
                            options=volumemodel.sensitivities,
                            uuid=uuid,
                            tab=tab,
                        ),
                    ),
                    html.Div(
                        style={"margin-top": "10px"},
                        children=create_select(
                            selector="Volume sensitivities",
                            options=volumemodel.sensitivities,
                            uuid=uuid,
                            tab=tab,
                        ),
                    ),
                ],
            ),
        ],
    )


def settings_layout(
    uuid: str, tab, theme: WebvizConfigTheme, volumemodel: InplaceVolumesModel
) -> html.Details:

    theme_colors = theme.plotly_theme.get("layout", {}).get("colorway", [])
    return html.Details(
        className="webviz-inplace-vol-plotselect",
        open=False,
        children=[
            html.Summary(
                style={"font-size": "15px", "font-weight": "bold"},
                children="⚙️ SETTINGS",
            ),
            html.Div(
                style={"padding": "10px"},
                children=[
                    cut_by_ref(uuid, tab),
                    labels_display(uuid, tab),
                    create_dropdown(
                        selector="Reference",
                        options=volumemodel.sensitivities,
                        uuid=uuid,
                        tab=tab,
                    ),
                ],
            ),
        ],
    )


def create_dropdown(selector: str, options: list, uuid, tab, value=None):
    options = (
        options
        if isinstance(options[0], dict)
        else [{"label": elm, "value": elm} for elm in options]
    )
    return html.Div(
        children=[
            html.Span(selector, style={"font-weight": "bold"}),
            dcc.Dropdown(
                id={"id": uuid, "tab": tab, "selector": selector},
                options=options,
                value=value if value is not None else options[0]["value"],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
        ]
    )


def create_select(selector: str, options: list, uuid, tab, value=None):
    return html.Details(
        open=False,
        children=[
            html.Summary(
                selector,
                style={"font-weight": "bold"},
            ),
            wcc.Select(
                id={
                    "id": uuid,
                    "tab": tab,
                    "selector": selector,
                },
                options=[{"label": i, "value": i} for i in options],
                value=value if value is not None else options,
                size=min(
                    10,
                    len(options),
                ),
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def cut_by_ref(uuid: str, tab) -> dcc.Checklist:
    return dcc.Checklist(
        id={"id": uuid, "tab": tab, "selector": "Remove no impact"},
        options=[{"label": "Remove sensitivities with no impact", "value": "Remove"}],
        value=["Remove"],
    )


def labels_display(uuid: str, tab) -> html.Div:
    return html.Div(
        style={"margin-bottom": "10px"},
        children=[
            html.Span("Label options:", style={"font-weight": "bold"}),
            dcc.RadioItems(
                id={"id": uuid, "tab": tab, "selector": "labeloptions"},
                options=[
                    {"label": "detailed", "value": "detailed"},
                    {"label": "simple", "value": "simple"},
                    {"label": "hide", "value": "hide"},
                ],
                labelStyle={"display": "inline-flex", "margin-right": "5px"},
                value="detailed",
            ),
        ],
    )
