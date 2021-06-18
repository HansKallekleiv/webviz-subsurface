from typing import Callable, Tuple, List, Optional
import pandas as pd
from pandas.api.types import is_numeric_dtype
import numpy as np
import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash_table.Format import Format
import dash_html_components as html
import dash_table
import plotly.express as px
import plotly.graph_objects as go
import webviz_core_components as wcc
from webviz_subsurface._components.tornado._tornado_data import TornadoData
from webviz_subsurface._components.tornado._tornado_bar_chart import TornadoBarChart
from webviz_subsurface._components.tornado._tornado_table import TornadoTable
from webviz_subsurface._models import InplaceVolumesModel
from webviz_subsurface._abbreviations.volume_terminology import (
    volume_description,
    volume_unit,
)

from ..figures import create_figure

# pylint: disable=too-many-statements, too-many-locals, too-many-branches
def distribution_controllers(
    app: dash.Dash, get_uuid: Callable, volumemodel: InplaceVolumesModel, theme
) -> None:
    @app.callback(
        Output(
            {"id": get_uuid("main-voldist"), "element": "graph", "page": ALL}, "figure"
        ),
        Output(
            {"id": get_uuid("main-voldist"), "wrapper": "table", "page": ALL},
            "children",
        ),
        Input(get_uuid("selections"), "data"),
        Input(
            {"id": get_uuid("main-voldist"), "element": "plot-table-select"}, "value"
        ),
        State(get_uuid("page-selected"), "data"),
        State({"id": get_uuid("main-voldist"), "element": "graph", "page": ALL}, "id"),
        State(
            {"id": get_uuid("main-voldist"), "wrapper": "table", "page": ALL},
            "id",
        ),
        State(
            {"id": get_uuid("main-voldist"), "element": "graph", "page": ALL}, "figure"
        ),
    )
    def _update_plots(
        selections: dict,
        plot_table_select: str,
        page_selected: str,
        figure_ids: list,
        table_wrapper_ids: list,
        figures: list,
    ) -> Tuple[list, list]:
        ctx = dash.callback_context.triggered[0]
        if page_selected not in ["1p1t", "custom"]:
            raise PreventUpdate

        selections = selections[page_selected]
        table_clicked = "plot-table-select" in ctx["prop_id"]
        page_figures = {
            id_value["page"]: figure for id_value, figure in zip(figure_ids, figures)
        }
        initial_callback = page_figures[page_selected] is None
        if not initial_callback and not table_clicked:
            if not selections["update"]:
                raise PreventUpdate
        print("running_fig")
        groups = ["REAL"]
        parameters = []
        responses = []
        for item in ["Subplots", "Color by", "X Response", "Y Response"]:
            if selections[item] is not None:
                if (
                    selections[item] in volumemodel.selectors
                    and selections[item] not in groups
                ):
                    groups.append(selections[item])
                if (
                    selections[item] in volumemodel.parameters
                    and selections[item] not in parameters
                ):
                    parameters.append(selections[item])
                if (
                    item in ["X Response", "Y Response"]
                    and selections[item] not in responses
                ):
                    responses.append(selections[item])

        df_for_figure = volumemodel.get_df(
            filters=selections["filters"], groups=groups, parameters=parameters
        )

        if not (plot_table_select == "table" and page_selected == "custom"):
            figure = create_figure(
                plot_type=selections["Plot type"],
                data_frame=df_for_figure.groupby([x for x in groups if x != "REAL"])
                .mean()
                .reset_index()
                if selections["Plot type"] == "bar" and groups != ["REAL"]
                else df_for_figure,
                x=selections["X Response"],
                y=selections["Y Response"],
                nbins=selections["hist_bins"],
                facet_col=selections["Subplots"],
                color=selections["Color by"],
                color_discrete_sequence=selections["Colorscale"],
                color_continuous_scale=selections["Colorscale"],
                barmode=selections["barmode"],
                layout=dict(
                    title=dict(
                        text=(
                            f"{volume_description(selections['X Response'])}"
                            + (
                                f" [{volume_unit(selections['X Response'])}]"
                                if selections["X Response"]
                                in volumemodel.volume_columns
                                else ""
                            )
                        ),
                        x=0.5,
                        font=dict(size=18),
                    ),
                ),
                yaxis=dict(showticklabels=True),
            ).add_annotation(fluid_annotation(selections))

            if selections["Subplots"] is not None:
                if not selections["X axis matches"]:
                    figure.update_xaxes({"matches": None})
                if not selections["Y axis matches"]:
                    figure.update_yaxes({"matches": None})
        else:
            figure = dash.no_update

        # Make tables
        if not (plot_table_select == "graph" and page_selected == "custom"):
            if not selections["sync_table"]:
                table_groups = ["ENSEMBLE", "REAL"]
                if selections["Group by"] is not None:
                    table_groups.extend(
                        [x for x in selections["Group by"] if x not in table_groups]
                    )
                df_for_table = volumemodel.get_df(
                    filters=selections["filters"],
                    groups=table_groups,
                    parameters=parameters,
                )

                responses = selections["table_responses"]
                groups = selections["Group by"]

            table_wrapper_children = make_table_wrapper_children(
                dframe=df_for_figure if selections["sync_table"] else df_for_table,
                responses=responses,
                groups=groups,
                volumemodel=volumemodel,
                page_selected=page_selected,
                selections=selections,
            )
        else:
            table_wrapper_children = dash.no_update

        figures = []
        for fig_id in figure_ids:
            if fig_id["page"] == page_selected:
                figures.append(figure)
            else:
                figures.append(dash.no_update)

        table_wrappers = []
        for wrap_id in table_wrapper_ids:
            if wrap_id["page"] == page_selected:
                table_wrappers.append(table_wrapper_children)
            else:
                table_wrappers.append(dash.no_update)

        return (figures, table_wrappers)

    @app.callback(
        Output(
            {
                "id": get_uuid("main-voldist"),
                "chart": ALL,
                "selector": ALL,
                "page": "per_zr",
            },
            "figure",
        ),
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
        State(
            {
                "id": get_uuid("main-voldist"),
                "chart": ALL,
                "selector": ALL,
                "page": "per_zr",
            },
            "id",
        ),
        State(
            {
                "id": get_uuid("main-voldist"),
                "chart": ALL,
                "selector": ALL,
                "page": "per_zr",
            },
            "figure",
        ),
    )
    def _update_plots_per_region_zone(
        selections: dict,
        page_selected: str,
        figure_ids: List[dict],
        figures: list,
    ) -> list:
        if page_selected != "per_zr":
            raise PreventUpdate

        selections = selections[page_selected]
        page_figures = {
            id_value["page"]: figure for id_value, figure in zip(figure_ids, figures)
        }
        initial_callback = page_figures[page_selected] is None
        if not initial_callback:
            if not selections["update"]:
                raise PreventUpdate

        figs = {}
        for selector in [x["selector"] for x in figure_ids]:
            dframe = volumemodel.get_df(
                filters=selections["filters"], groups=[selector]
            )
            texttemplate = (
                "%{text:.3s}"
                if selections["X Response"] in volumemodel.volume_columns
                else "%{text:.3g}"
            )
            # pylint: disable=no-member
            figs[selector] = {
                "pie": create_figure(
                    plot_type="pie",
                    data_frame=dframe,
                    values=selections["X Response"],
                    names=selector,
                    title=f"{selections['X Response']} per {selector}",
                    color_discrete_sequence=selections["Colorscale"],
                    color=selector,
                )
                .update_traces(marker_line=dict(color="#000000", width=1))
                .update_layout(margin=dict(l=10, b=10)),
                "bar": create_figure(
                    plot_type="bar",
                    data_frame=dframe,
                    x=selector,
                    y=selections["X Response"],
                    color_discrete_sequence=px.colors.diverging.BrBG_r,
                    color=selections["Color by"],
                    text=selections["X Response"],
                    xaxis=dict(
                        type="category", tickangle=45, tickfont_size=17, title=None
                    ),
                )
                .update_traces(texttemplate=texttemplate, textposition="auto")
                .add_annotation(fluid_annotation(selections)),
            }

        output_figs = []
        for fig_id in figure_ids:
            output_figs.append(figs[fig_id["selector"]][fig_id["chart"]])
        return output_figs

    @app.callback(
        Output(
            {"id": get_uuid("main-voldist"), "element": "plot", "page": "conv"},
            "figure",
        ),
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
        State(
            {"id": get_uuid("main-voldist"), "element": "plot", "page": "conv"},
            "figure",
        ),
    )
    def _update_convergence_plot(
        selections: dict, page_selected: str, figure: go.Figure
    ) -> go.Figure:
        if page_selected != "conv":
            raise PreventUpdate

        selections = selections[page_selected]

        initial_callback = figure is None
        if not initial_callback:
            if not selections["update"]:
                raise PreventUpdate

        subplots = selections["Subplots"] if selections["Subplots"] is not None else []
        groups = ["REAL"]
        if subplots and subplots not in groups:
            groups.append(subplots)

        dframe = volumemodel.get_df(filters=selections["filters"], groups=groups)
        dframe = dframe.sort_values(by=["REAL"])

        dfs = []
        df_groups = dframe.groupby(subplots) if subplots else [(None, dframe)]
        for _, df in df_groups:
            for calculation in ["mean", "p10", "p90"]:
                df_stat = df.copy()
                df_stat[selections["X Response"]] = (
                    (df_stat[selections["X Response"]].expanding().mean())
                    if calculation == "mean"
                    else df_stat[selections["X Response"]]
                    .expanding()
                    .quantile(0.1 if calculation == "p90" else 0.9)
                )
                df_stat["calculation"] = calculation
                dfs.append(df_stat)
        if dfs:
            dframe = pd.concat(dfs)

        figure = (
            create_figure(
                plot_type="line",
                data_frame=dframe,
                x="REAL",
                y=selections["X Response"],
                facet_col=selections["Subplots"],
                color="calculation",
                title=f"Convergence plot of mean/p10/p90 for {selections['X Response']} ",
                yaxis=dict(showticklabels=True),
            )
            .update_traces(line_width=3.5)
            .update_traces(line=dict(color="black"), selector={"name": "mean"})
            .update_traces(
                line=dict(color="firebrick", dash="dash"),
                selector={"name": "p10"},
            )
            .update_traces(
                line=dict(color="royalblue", dash="dash"), selector={"name": "p90"}
            )
            .add_annotation(fluid_annotation(selections))
        )

        if selections["Subplots"] is not None:
            if not selections["X axis matches"]:
                figure.update_xaxes({"matches": None})
            if not selections["Y axis matches"]:
                figure.update_yaxes(dict(matches=None))
        return figure

    @app.callback(
        Output(
            {
                "id": get_uuid("main-tornado"),
                "element": "bulktornado",
                "page": "tornado",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-tornado"),
                "element": "inplacetornado",
                "page": "tornado",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-tornado"),
                "wrapper": "table",
                "page": "tornado",
            },
            "children",
        ),
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
        State(
            {
                "id": get_uuid("main-tornado"),
                "element": "bulktornado",
                "page": "tornado",
            },
            "figure",
        ),
    )
    def _update_tornado_plots(
        selections: dict, page_selected: str, figure: go.Figure
    ) -> go.Figure:

        if page_selected != "tornado":
            raise PreventUpdate

        selections = selections[page_selected]
        initial_callback = figure is None
        if not initial_callback:
            if not selections["update"]:
                raise PreventUpdate

        filters = {key: value for key, value in selections["filters"].items()}

        figures = []
        tables = []
        for x in ["BULK", selections["Volume response"]]:

            sensfilter = (
                selections["Bulk sensitivities"]
                if x == "BULK"
                else selections["Volume sensitivities"]
            )
            if selections["Reference"] not in sensfilter:
                sensfilter.append(selections["Reference"])

            # filter on correct fluid zone depending on chosen volume response
            fluid_filter = [
                "oil" if selections["Volume response"] == "STOIIP" else "gas"
            ]
            filters.update(
                SENSNAME=sensfilter,
                FLUID_ZONE=fluid_filter,
            )

            groups = ["REAL", "ENSEMBLE", "SENSNAME", "SENSCASE", "SENSTYPE"]
            df_for_tornado = volumemodel.get_df(filters=filters, groups=groups)
            df_for_tornado.rename(columns={x: "VALUE"}, inplace=True)
            use_true = selections["Scale"] == "True"
            tornado_data = TornadoData(
                dframe=df_for_tornado,
                reference=selections["Reference"],
                scale=selections["Scale"],
                cutbyref=bool(selections["Remove no impact"]),
            )
            figure = go.Figure(
                TornadoBarChart(
                    tornado_data=tornado_data,
                    plotly_theme=theme.plotly_theme,
                    # figure_height=700,
                    label_options = selections["labeloptions"],
                    number_format="#.3g",
                    use_true_base=use_true,
                ).figure
            )

            figure.update_xaxes(
                tickfont_size=15,
                title_font_size=18,
                gridwidth=1,
                gridcolor="whitesmoke",
                showgrid=True,
                side="bottom",
            
            ).update_yaxes(
                tickfont_size=15
            ).update_layout(
                title=dict(
                    text=f"Tornadoplot for {x} "
                    + (f"({fluid_filter[0]})" if x == "BULK" else ""),
                    font=dict(size=18),
                ),
                margin={"t": 70},
            )



            figures.append(figure)
            tables.append(TornadoTable(tornado_data=tornado_data))

        return (
            figures[0],
            figures[1],
            html.Div(
                children=[
                    html.Div(
                        style={"margin-bottom": "30px"},
                        children=create_data_table(
                            volumemodel=volumemodel,
                            columns=create_table_columns(
                                columns=TornadoTable.COLUMNS,
                                format_columns=[
                                    x
                                    for x in TornadoTable.COLUMNS
                                    if x
                                    not in ["Sensitivity", "Low reals", "High reals"]
                                ],
                                use_si_format=True,
                            ),
                            data=tables[1].as_plotly_table,
                            height="22vh",
                            table_id={"table_id": f"{page_selected}-bulk"},
                        ),
                    ),
                    create_data_table(
                        volumemodel=volumemodel,
                        columns=create_table_columns(
                            columns=TornadoTable.COLUMNS,
                            format_columns=[
                                x
                                for x in TornadoTable.COLUMNS
                                if x not in ["Sensitivity", "Low reals", "High reals"]
                            ],
                            use_si_format=True,
                        ),
                        data=tables[0].as_plotly_table,
                        height="22vh",
                        table_id={"table_id": f"{page_selected}-inplace"},
                    ),
                ]
            ),
        )


# pylint: disable=too-many-locals
def make_table_wrapper_children(
    dframe: pd.DataFrame,
    responses: list,
    volumemodel: InplaceVolumesModel,
    selections: dict,
    page_selected: str,
    groups: Optional[list] = None,
) -> Tuple[list, list]:

    groups = groups if groups is not None else []
    groupby_real = (
        selections["Group by"] is not None and "REAL" in selections["Group by"]
    )
    groups = (
        groups
        if groupby_real and selections["Table type"] != "Statistics table"
        else [x for x in groups if x != "REAL"]
    )
    vol_responses = [x for x in responses if x in volumemodel.volume_columns]

    if selections["Table type"] == "Statistics table":
        statcols = ["Mean", "Stddev", "P90", "P10", "Minimum", "Maximum"]

        df_groups = dframe.groupby(groups) if groups else [(None, dframe)]

        data_properties = []
        data_volcols = []
        for response in responses:
            if not is_numeric_dtype(dframe[response]):
                continue
            for name, df in df_groups:
                values = df[response]
                data = {
                    "Response" if response in vol_responses else "Property": response,
                    "Mean": values.mean(),
                    "Stddev": values.std(),
                    "P10": np.nanpercentile(values, 90),
                    "P90": np.nanpercentile(values, 10),
                    "Minimum": values.min(),
                    "Maximum": values.max(),
                }
                if "FLUID_ZONE" not in groups:
                    data.update(
                        FLUID_ZONE=(" + ").join(selections["filters"]["FLUID_ZONE"])
                    )

                for idx, group in enumerate(groups):
                    data[group] = (
                        name if isinstance(name, str) == 1 else list(name)[idx]
                    )
                if response in volumemodel.volume_columns:
                    data_volcols.append(data)
                else:
                    data_properties.append(data)

        if page_selected == "custom":
            height = "43vh" if all([data_volcols, data_properties]) else "88vh"
        else:
            height = "22vh" if all([data_volcols, data_properties]) else "44vh"

        return html.Div(
            children=[
                html.Div(
                    style={"margin-bottom": "30px"}
                    if all([data_volcols, data_properties])
                    else None,
                    children=create_data_table(
                        volumemodel=volumemodel,
                        columns=create_table_columns(
                            columns=["Response"]
                            + [x for x in groups if x != "FLUID_ZONE"]
                            + statcols
                            + ["FLUID_ZONE"],
                            format_columns=statcols,
                            volumemodel=volumemodel,
                            use_si_format=True,
                        ),
                        data=data_volcols,
                        height=height,
                        table_id={"table_id": f"{page_selected}-responses"},
                    ),
                ),
                create_data_table(
                    volumemodel=volumemodel,
                    columns=create_table_columns(
                        columns=["Property"]
                        + [x for x in groups if x != "FLUID_ZONE"]
                        + statcols
                        + ["FLUID_ZONE"],
                        format_columns=statcols,
                        volumemodel=volumemodel,
                        use_si_format=False,
                    ),
                    data=data_properties,
                    height=height,
                    table_id={"table_id": f"{page_selected}-properties"},
                ),
            ]
        )

    # if table type Mean table
    columns = responses + [x for x in groups if x not in responses]
    dframe = (
        dframe[columns].groupby(groups).mean().reset_index()
        if groups
        else dframe[responses].mean().to_frame().T
    )

    if "FLUID_ZONE" not in dframe:
        dframe["FLUID_ZONE"] = (" + ").join(selections["filters"]["FLUID_ZONE"])

    dframe = dframe[[x for x in dframe.columns if x != "FLUID_ZONE"] + ["FLUID_ZONE"]]
    return html.Div(
        children=[
            create_data_table(
                volumemodel=volumemodel,
                columns=create_table_columns(
                    columns=dframe.columns,
                    format_columns=dframe.columns,
                    volumemodel=volumemodel,
                ),
                data=dframe.iloc[::-1].to_dict("records"),
                height="88vh" if page_selected == "custom" else "44vh",
                table_id={"table_id": f"{page_selected}-meantable"},
            )
        ]
    )


def create_table_columns(
    columns: list,
    volumemodel: Optional[InplaceVolumesModel] = None,
    format_columns: Optional[list] = None,
    use_si_format: Optional[bool] = None,
) -> List[dict]:

    format_columns = format_columns if format_columns is not None else []

    table_columns = []
    for col in columns:
        data = {"id": col, "name": col}
        if col in format_columns:
            data.update(
                {
                    "type": "numeric",
                    "format": {"locale": {"symbol": ["", ""]}, "specifier": "$.4s"}
                    if use_si_format
                    or volumemodel is not None
                    and col in volumemodel.volume_columns
                    else Format(precision=3),
                }
            )
        table_columns.append(data)
    return table_columns


# pylint: disable=inconsistent-return-statements
def create_data_table(
    volumemodel: InplaceVolumesModel,
    columns: list,
    height: str,
    data: Optional[list],
    table_id,
) -> dash_table.DataTable:

    if not data:
        return []

    style_cell_conditional = [
        {"if": {"column_id": c}, "textAlign": "left"}
        for c in [x for x in volumemodel.selectors if x != "FLUID_ZONE"]
        + ["Response", "Property", "Sensitivity"]
    ]
    style_cell_conditional.extend(
        [
            {"if": {"column_id": c}, "width": "10%"}
            for c in volumemodel.selectors + ["Response", "Property", "Sensitivity"]
        ]
    )
    style_data_conditional = [
        {
            "if": {
                "filter_query": "{FLUID_ZONE} = " + f"'{fluid}'",
                "column_id": "FLUID_ZONE",
            },
            "backgroundColor": color,
        }
        for fluid, color in fluid_colors().items()
    ] + [
        {
            "if": {
                "filter_query": "{FLUID_ZONE} contains '+'",
                "column_id": "FLUID_ZONE",
            },
            "backgroundColor": "#E8E8E8",
        }
    ]

    return wcc.WebvizPluginPlaceholder(
        id={"request": "table_data", "table_id": table_id["table_id"]},
        buttons=["expand", "download"],
        children=dash_table.DataTable(
            id=table_id,
            sort_action="native",
            sort_mode="multi",
            filter_action="native",
            columns=columns,
            data=data,
            style_cell_conditional=style_cell_conditional,
            style_data_conditional=style_data_conditional,
            style_table={
                "height": height,
                "overflowY": "auto",
            },
        ),
    )


def fluid_colors() -> dict:
    return {
        "oil": "#c6ebd9",
        "gas": "#ffcccc",
        "water": "#ADD8E6",
    }


def fluid_annotation(selections: dict) -> dict:
    fluid_text = (" + ").join(selections["filters"]["FLUID_ZONE"])
    return dict(
        visible=bool(selections["Fluid annotation"])
        and selections["Subplots"] != "FLUID_ZONE",
        x=1,
        y=1,
        xref="paper",
        yref="paper",
        showarrow=False,
        text="Fluid zone<br>" + fluid_text,
        font=dict(size=15, color="black"),
        bgcolor=fluid_colors().get(fluid_text, "#E8E8E8"),
    )
