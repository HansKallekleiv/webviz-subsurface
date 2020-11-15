from typing import Union

import dash_html_components as html
import webviz_core_components as wcc


def filter_view(parent) -> html.Div:

    dropdowns = []
    for filter_name in parent.vmodel.single_filters + parent.vmodel.multi_filters:
        filter_values = list(parent.vmodel.dataframe[filter_name].unique())
        if filter_name in parent.vmodel.single_filters:
            dropdowns.append(
                filter_selector(
                    parent=parent,
                    filter_name=filter_name,
                    filter_values=filter_values,
                    filter_type="single_filter",
                    initial_value=filter_values[0],
                )
            )
        else:
            dropdowns.append(
                filter_selector(
                    parent=parent,
                    filter_name=filter_name,
                    filter_values=filter_values,
                    filter_type="multi_filter",
                    initial_value=filter_values,
                )
            )

    return html.Div(children=dropdowns)


def filter_selector(
    parent,
    filter_name: str,
    filter_type: str,
    filter_values: list,
    initial_value: Union[list, str],
) -> html.Div:
    return html.Div(
        children=[
            html.Details(
                open=True,
                children=[
                    html.Summary(filter_name.lower().capitalize()),
                    wcc.Select(
                        id={
                            "plugin": parent.uuid("plugin"),
                            "type": filter_type,
                            "name": filter_name,
                        },
                        options=[{"label": i, "value": i} for i in filter_values],
                        value=initial_value,
                        multi=True,
                        size=min(20, len(filter_values)),
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            )
        ]
    )
