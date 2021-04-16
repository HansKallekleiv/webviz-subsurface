import dash_html_components as html
import dash_table
import webviz_core_components as wcc


def uncertainty_table_layout(
    uuid: str,
) -> html.Div:
    """Layout for the uncertainty table modal"""
    return html.Div(
        className="webviz-structunc-uncertainty-table-wrapper",
        children=[
            wcc.FlexBox(
                children=[
                    html.Label(
                        className="webviz-structunc-uncertainty-table-label",
                        children="Statistics for well: ",
                        id={"id": uuid, "element": "label"},
                    ),
                    html.Button(
                        "Recalculate",
                        className="webviz-structunc-uncertainty-table-apply-btn",
                        id={"id": uuid, "element": "apply-button"},
                    ),
                ]
            ),
            dash_table.DataTable(
                id={"id": uuid, "element": "table"},
                columns=[
                    {"id": "Surface name", "name": "Surface name", "selectable": False},
                    {"id": "Ensemble", "name": "Ensemble", "selectable": False},
                    {"id": "Pick no", "name": "Pick no", "selectable": False},
                    {"id": "Calculation", "name": "Calculation", "selectable": False},
                    {
                        "id": "Z_TVDSS",
                        "name": "Z_TVDSS",
                        "selectable": False,
                    },
                    {
                        "id": "MD",
                        "name": "MD",
                        "selectable": False,
                    },
                ],
                style_data_conditional=[
                    {
                        "if": {"filter_query": '{Calculation} = "Mean"'},
                        "backgroundColor": "#0074D9",
                        "color": "white",
                    }
                ],
                sort_action="native",
                filter_action="native",
            ),
        ],
    )


def uncertainty_table_btn(uuid: str, disabled: bool = False) -> html.Button:
    return html.Div(
        children=html.Button(
            "Show uncertainty table",
            className="webviz-structunc-open-modal-btn",
            id={"id": uuid, "element": "display-button"},
            disabled=disabled,
        ),
    )
