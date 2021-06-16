from typing import Tuple, Dict, List
import pandas as pd
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
import webviz_core_components as wcc
from webviz_core_components.SmartNodeSelector import SmartNodeSelector
from webviz_core_components.wrapped_components.select_with_label import SelectWithLabel
import webviz_subsurface_components as wsc
from webviz_subsurface._providers.sumo_surface_provider import SumoSurfaceProvider

from ._deckgl_surface_layer import DeckGLSurfaceLayers


class SurfaceViewerSumo(WebvizPluginABC):
    """### SurfaceViewerSumo"""

    def __init__(self, app, sumo_env="main"):

        super().__init__()
        self.shared_settings = app.webviz_settings["shared_settings"]
        self.sumo = SumoSurfaceProvider(env=sumo_env)
        self.tags = self.make_smartselector()
        print(self.tags)
        self.set_callbacks(app)

    def get_case_options(self) -> list:
        return [
            {"label": case.get("case").get("name"), "value": case.get("id")}
            for case in self.sumo.get_cases()
        ]

    @property
    def layout(self) -> wcc.FlexBox:
        return html.Div(
            children=[
                wcc.Label("Smart node selector"),
                wcc.SmartNodeSelector(
                    id=self.uuid("smartnode"),
                    data=self.tags,
                    numMetaNodes=0,
                    maxNumSelectedNodes=1,
                    numSecondsUntilSuggestionsAreShown=0,
                ),
                wcc.FlexBox(
                    style={"height": "85vh"},
                    children=[
                        wcc.FlexedColumn(
                            children=wcc.Frame(
                                style={"height": "80vh"},
                                children=[
                                    wcc.Selectors(
                                        label="Sumo surface selector",
                                        children=[
                                            wcc.Dropdown(
                                                clearable=False,
                                                id=self.uuid("case"),
                                                label="Case",
                                                options=self.get_case_options(),
                                            ),
                                            wcc.Dropdown(
                                                clearable=False,
                                                id=self.uuid("iteration"),
                                                label="Iteration",
                                            ),
                                            wcc.Dropdown(
                                                clearable=False,
                                                id=self.uuid("surface-content"),
                                                label="Surface type",
                                            ),
                                            wcc.Dropdown(
                                                clearable=False,
                                                id=self.uuid("surface-name"),
                                                label="Surface name",
                                            ),
                                            wcc.Dropdown(
                                                clearable=False,
                                                id=self.uuid("realization"),
                                                label="Realization",
                                            ),
                                        ],
                                    ),
                                    wcc.Selectors(
                                        label="Well data",
                                        children=[
                                            wcc.SelectWithLabel(
                                                id=self.uuid("wells"), label="Wells"
                                            ),
                                            wcc.Dropdown(
                                                id=self.uuid("well-log"),
                                                label="Well log",
                                            ),
                                        ],
                                    ),
                                    wcc.Selectors(
                                        label="Fault lines",
                                        children=[
                                            wcc.Checklist(
                                                id=self.uuid("fault-lines"),
                                                options=[
                                                    {
                                                        "label": "Show fault lines",
                                                        "value": "faultlines",
                                                    }
                                                ],
                                            )
                                        ],
                                    ),
                                ],
                            )
                        ),
                        wcc.FlexedColumn(
                            flex=4,
                            children=wcc.Frame(
                                style={"height": "80vh"},
                                children=[wsc.DeckGLMap(id=self.uuid("map-viz"))],
                            ),
                        ),
                        wcc.FlexedColumn(
                            flex=2,
                            children=wcc.Frame(
                                style={"height": "80vh"},
                                children=[
                                    wcc.Selectors(
                                        label="Surface information",
                                        open_details=False,
                                        children=[
                                            html.Div(
                                                style={
                                                    "overflowY": "auto",
                                                    "height": "30vh",
                                                },
                                                children=html.Pre(
                                                    id=self.uuid("sumo-description")
                                                ),
                                            )
                                        ],
                                    ),
                                    wcc.Selectors(
                                        label="Uncertainty parameters",
                                        open_details=False,
                                        children=[
                                            html.Div(
                                                style={
                                                    "overflowY": "auto",
                                                    "height": "40vh",
                                                },
                                                children=dash_table.DataTable(
                                                    style_cell={"fontSize": 10},
                                                    id=self.uuid("sumo-parameters"),
                                                    columns=[
                                                        {"name": "Name", "id": "Name"},
                                                        {
                                                            "name": "Value",
                                                            "id": "Value",
                                                        },
                                                    ],
                                                ),
                                            )
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ]
        )

    def set_callbacks(self, app) -> None:
        @app.callback(
            Output(self.uuid("iteration"), "options"),
            Output(self.uuid("iteration"), "value"),
            Input(self.uuid("case"), "value"),
            State(self.uuid("iteration"), "value"),
        )
        def _update_iterations(case, current_iteration):
            if case is None:
                raise PreventUpdate
            iterations = self.sumo.get_iterations(case)
            return get_options_and_value(iterations, current_iteration)

        @app.callback(
            Output(self.uuid("surface-content"), "options"),
            Output(self.uuid("surface-content"), "value"),
            Input(self.uuid("case"), "value"),
            Input(self.uuid("iteration"), "value"),
            State(self.uuid("surface-content"), "value"),
        )
        def _update_contents(case, iteration, current_content):
            if case is None or iteration is None:
                raise PreventUpdate
            contents = self.sumo.get_contents(case, iteration=iteration)
            return get_options_and_value(contents, current_content)

        @app.callback(
            Output(self.uuid("surface-name"), "options"),
            Output(self.uuid("surface-name"), "value"),
            Input(self.uuid("case"), "value"),
            Input(self.uuid("iteration"), "value"),
            Input(self.uuid("surface-content"), "value"),
            State(self.uuid("surface-name"), "value"),
        )
        def _update_names(case, iteration, content, current_name):
            if case is None or iteration is None or content is None:
                raise PreventUpdate
            surface_names = self.sumo.get_surfaces(
                case, iteration=iteration, content=content
            )
            return get_options_and_value(surface_names, current_name)

        @app.callback(
            Output(self.uuid("realization"), "options"),
            Output(self.uuid("realization"), "value"),
            Input(self.uuid("case"), "value"),
            Input(self.uuid("iteration"), "value"),
            Input(self.uuid("surface-content"), "value"),
            Input(self.uuid("surface-name"), "value"),
            State(self.uuid("realization"), "value"),
        )
        def _update_reals(case, iteration, content, name, current_real):
            if case is None or iteration is None or content is None or name is None:
                raise PreventUpdate
            realizations = self.sumo.get_realizations(
                case, iteration=iteration, content=content, surface=name
            )
            return get_options_and_value(realizations, current_real)

        @app.callback(
            Output(self.uuid("map-viz"), "deckglSpecPatch"),
            Output(self.uuid("sumo-parameters"), "data"),
            Output(self.uuid("sumo-description"), "children"),
            Input(self.uuid("case"), "value"),
            Input(self.uuid("iteration"), "value"),
            Input(self.uuid("surface-content"), "value"),
            Input(self.uuid("surface-name"), "value"),
            Input(self.uuid("realization"), "value"),
            # Input(self.uuid("smartnode"), "selectedTags"),
        )
        def _set_surface(case, iteration, content, name, real):
            # print("selected tag", selected_tag)
            if (
                case is None
                or iteration is None
                or content is None
                or name is None
                or real is None
            ):
                raise PreventUpdate
            surface = self.sumo.get_surface(
                case,
                iteration=iteration,
                content=content,
                surface=name,
                realization=real,
            )
            surface_obj = self.sumo.get_surface_object(
                case, iteration, content, name, real
            )
            import json

            parameters = (
                surface_obj.get("_source")
                .get("fmu")
                .get("realization")
                .get("parameters")
            )
            stuff = surface_obj.get("_source").get("data")
            surface_descr = {
                "stratigraphic": stuff.get("stratigraphic"),
                "unit": stuff.get("unit"),
                "vertical_domain": stuff.get("vertical_domain"),
                "properties": stuff.get("properties"),
                "description": stuff.get("description"),
            }

            param_df = pd.DataFrame.from_dict(
                parameters, columns=["Value"], orient="index"
            )
            param_df = param_df.reset_index()
            param_df = param_df.rename(columns={"index": "Name"})

            spec = DeckGLSurfaceLayers(surface)
            return (
                spec.patch,
                param_df.to_dict(orient="records"),
                json.dumps(surface_descr, indent=1),
            )

    def make_smartselector(self):
        tags = []
        for case_obj in [self.sumo.get_cases()[0]]:
            case = case_obj.get("id")
            tag = {}
            tag["name"] = case_obj.get("case").get("name")
            tag["id"] = case
            tag["children"] = []
            for iteration in self.sumo.get_iterations(case):
                tag_iter = {}
                tag_iter["name"] = iteration
                tag_iter["id"] = f"{case}.{iteration}"
                tag_iter["children"] = []
                for content in self.sumo.get_contents(case, iteration):
                    tag_content = {}
                    tag_content["name"] = content
                    tag_content["id"] = f"{case}.{iteration}.{content}"
                    tag_content["children"] = []
                    for name in self.sumo.get_surfaces(case, iteration, content):
                        tag_names = {}
                        tag_names["name"] = name
                        tag_names["id"] = f"{case}.{iteration}.{content}.{name}"
                        tag_names["children"] = []
                        for real in sorted(
                            self.sumo.get_realizations(case, iteration, content, name)
                        ):
                            tag_real = {}
                            tag_real["name"] = real
                            tag_real[
                                "id"
                            ] = f"{case}.{iteration}.{content}.{name}.{real}"
                            tag_names["children"].append(tag_real)
                        tag_content["children"].append(tag_names)
                    tag_iter["children"].append(tag_content)
                tag["children"].append(tag_iter)
            tags.append(tag)
        return tags


def get_options_and_value(new_values: list, current_value: str) -> Tuple[List, str]:
    if current_value and current_value in new_values:
        value = current_value
    else:
        value = new_values[0]
    return [{"label": val, "value": val} for val in new_values], value
