import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc


from .selector_view import ensemble_selector, delta_ensemble_selector, filter_parameter


def selector_view(parent) -> html.Div:
    return html.Div(
        className="framed",
        style={"height": "80vh", "overflowY": "auto"},
        children=[
            ensemble_selector(parent=parent, tab="qc"),
            delta_ensemble_selector(parent=parent, tab="qc"),
            filter_parameter(
                parent=parent,
                tab="qc",
                value=[parent.pmodel.parameters[0]],
                open_details=True,
            ),
        ],
    )


def property_qc_view(parent) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            html.Div(style={"flex": 1}, children=selector_view(parent=parent)),
            html.Div(
                style={"flex": 4, "height": "80vh"},
                className="framed",
                children=[
                    wcc.FlexBox(
                        children=[
                            dcc.RadioItems(
                                id=parent.uuid("property-qc-plot-type"),
                                options=[
                                    {
                                        "label": "Distribution plots",
                                        "value": "histogram",
                                    },
                                    {"label": "Statistics table", "value": "table"},
                                ],
                                value="histogram",
                                labelStyle={
                                    "display": "inline-block",
                                    "margin": "5px",
                                },
                            ),
                            dcc.RadioItems(
                                id=parent.uuid("delta-sort"),
                                options=[
                                    {"label": "Sort by Name", "value": "Name"},
                                    {
                                        "label": "Sort by Standard Deviation",
                                        "value": "Stddev",
                                    },
                                    {"label": "Sort by Average", "value": "Avg"},
                                ],
                                value="Name",
                                labelStyle={
                                    "display": "inline-block",
                                    "margin": "5px",
                                },
                                persistence=True,
                                persistence_type="session",
                            ),
                        ]
                    ),
                    html.Div(
                        style={"height": "75vh"}, id=parent.uuid("property-qc-wrapper")
                    ),
                ],
            ),
        ],
    )
