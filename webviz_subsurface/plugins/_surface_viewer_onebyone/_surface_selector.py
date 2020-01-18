from datetime import datetime
from uuid import uuid4
import json
import yaml

import pandas as pd

import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc


class SurfaceSelector:
    # pylint: disable=too-many-instance-attributes,too-many-statements
    """### Surface Selector

Creates a widget to select surfaces from a yaml configuration file or dictionary, and
a dataframe of ensemble/realizations, optionally with sensitivity cases.
The current selections are stored in a dcc.Store object that can
be accessed by the storage_id property of the class instance.

* `config`: A dictionary / yaml configuration file of surfaces on the format below
* `ensembles`: A pandas dataframe with ensemble, real(index), runpath, sensname and senscase

Format of configuration:
some_property:
    names:
        - surfacename
        - surfacename
    dates:
        - somedate
        - somedate
another_property:
    names:
        - surfacename
        - surfacename
    dates:
        - somedate
        - somedate
"""

    def __init__(self, app, config, ensembles):
        self._configuration = self.read_config(config)
        self._ensembles = ensembles
        self._storage_id = f"{str(uuid4())}-surface-selector"
        self.set_ids()
        self.set_callbacks(app)

    @staticmethod
    def read_config(config):
        """Reads config file either from a yaml provided file or from a dict"""
        if isinstance(config, str):
            return yaml.safe_load(open(config, "r"))

        if isinstance(config, pd.DataFrame):
            return {
                attr: {
                    "names": list(dframe["name"].unique()),
                    "dates": list(dframe["date"].unique())
                    if "date" in dframe.columns
                    else [None],
                }
                for attr, dframe in config.groupby("attribute")
            }

        raise TypeError("Config must be a dictionary of a yaml file")

    @property
    def storage_id(self):
        """The id of the dcc.Store component that holds the selection"""
        return self._storage_id

    def set_ids(self):
        uuid = str(uuid4())
        self.attr_id = f"{uuid}-attr"
        self.attr_id_btn_prev = f"{uuid}-attr-btn-prev"
        self.attr_id_btn_next = f"{uuid}-attr-btn-next"
        self.name_id = f"{uuid}-name"
        self.name_id_btn_prev = f"{uuid}-name-btn-prev"
        self.name_id_btn_next = f"{uuid}-name-btn-next"
        self.date_id = f"{uuid}-date"
        self.date_id_btn_prev = f"{uuid}-date-btn-prev"
        self.date_id_btn_next = f"{uuid}-date-btn-next"
        self.ensemble_id = f"{uuid}-ens"
        self.ensemble_id_btn_prev = f"{uuid}-ensemble-btn-prev"
        self.ensemble_id_btn_next = f"{uuid}-ensemble-btn-next"
        self.realization_id = f"{uuid}-real"
        self.realization_id_btn_prev = f"{uuid}-realization-btn-prev"
        self.realization_id_btn_next = f"{uuid}-realization-btn-next"
        self.name_wrapper_id = f"{uuid}-name-wrapper"
        self.date_wrapper_id = f"{uuid}-date-wrapper"
        self.ens_wrapper_id = f"{uuid}-ens-wrapper"
        self.real_wrapper_id = f"{uuid}-real-wrapper"
        self.aggreal_id = f"{uuid}-aggreal"
        self.sens_name_id = f"{uuid}-sens-name-id"
        self.sens_ref_id = f"{uuid}-sens-ref-id"
        self.sens_case_id = f"{uuid}-sens-case-id"
        self.sens_name_wrapper_id = f"{uuid}-sens-name-wrapper-id"
        self.sens_ref_wrapper_id = f"{uuid}-sens-ref-wrapper-id"
        self.sens_case_wrapper_id = f"{uuid}-sens-case-wrapper-id"
        self.calculation_id = f"{uuid}-calculation-id"

    @property
    def attrs(self):
        return list(self._configuration.keys())

    def _names_in_attr(self, attr):
        return self._configuration[attr].get("names", None)

    def _dates_in_attr(self, attr):
        return self._configuration[attr].get("dates", None)

    @property
    def ensembles(self):
        return list(self._ensembles["ENSEMBLE"].unique())

    def sens_names(self, ensemble):
        sensnames = list(
            self._ensembles.loc[self._ensembles["ENSEMBLE"] == ensemble][
                "SENSNAME"
            ].unique()
        )
        if sensnames[0] is None:
            return None
        return sensnames

    def sens_cases(self, ensemble, sensname):
        senscases = list(
            self._ensembles.loc[
                (self._ensembles["ENSEMBLE"] == ensemble)
                & (self._ensembles["SENSNAME"] == sensname)
            ]["SENSCASE"].unique()
        )
        if senscases and senscases[0] is None:
            return None
        return senscases

    def realizations(self, ensemble, sensname=None, senstype=None):
        df = self._ensembles.loc[self._ensembles["ENSEMBLE"] == ensemble].copy()
        if sensname and senstype:
            df = df.loc[(df["SENSNAME"] == sensname) & (df["SENSCASE"] == senstype)]
        return list(df["REAL"])

    def get_sens_type(self, ensemble, sensname):
        df = self._ensembles.loc[self._ensembles["ENSEMBLE"] == ensemble].copy()
        sens_type = list(df.loc[(df["SENSNAME"] == sensname)]["SENSTYPE"].unique())
        if len(sens_type) == 1:
            return sens_type[0]
        else:
            return None

    @property
    def attribute_selector(self):
        return html.Div(
            style={"display": "grid"},
            children=[
                html.P("Surface property"),
                dcc.Dropdown(
                    id=self.attr_id,
                    options=[{"label": attr, "value": attr} for attr in self.attrs],
                    value=self.attrs[0],
                    clearable=False,
                ),
            ],
        )

    @property
    def name_selector(self):
        return html.Div(
            id=self.name_wrapper_id,
            style={"display": "none"},
            children=[
                html.P("Surface name"),
                dcc.Dropdown(id=self.name_id, clearable=False),
            ],
        )

    @property
    def date_selector(self):
        return html.Div(
            id=self.date_wrapper_id,
            style={"display": "none"},
            children=[html.P("Date"), dcc.Dropdown(id=self.date_id, clearable=False)],
        )

    @property
    def ensemble_selector(self):
        return html.Div(
            id=self.ens_wrapper_id,
            style={"display": "grid"},
            children=[
                html.P("Ensemble"),
                dcc.Dropdown(
                    id=self.ensemble_id,
                    options=[{"label": ens, "value": ens} for ens in self.ensembles],
                    value=self.ensembles[0],
                    clearable=False,
                ),
            ],
        )

    @property
    def sensitivity_selector(self):
        return html.Div(
            id=self.sens_name_wrapper_id,
            children=[
                html.Label("Sensitivity name"),
                dcc.Dropdown(id=self.sens_name_id, clearable=False),
            ],
        )

    @property
    def sensitivity_ref_selector(self):
        return html.Div(
            id=self.sens_ref_wrapper_id,
            children=[
                html.Label("Sensitivity reference"),
                dcc.Dropdown(id=self.sens_ref_id, clearable=False),
            ],
        )

    @property
    def calculation_mode(self):
        return html.Div(
            children=[
                html.Label("Calculation mode"),
                dcc.RadioItems(
                    id=self.calculation_id,
                    options=[
                        {"label": "P10/Mean/P90", "value": "absolute"},
                        {"label": "Relative to reference", "value": "relative"},
                    ],
                    value="absolute",
                ),
            ]
        )

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @property
    def layout(self):
        return html.Div(
            style={"fontSize": "12px", "marginLeft": "25px"},
            children=[
                html.Div(
                    style=self.set_grid_layout("1fr"),
                    children=[
                        self.attribute_selector,
                        self.name_selector,
                        self.date_selector,
                    ],
                ),
                self.ensemble_selector,
                self.sensitivity_selector,
                self.calculation_mode,
                self.sensitivity_ref_selector,
                dcc.Store(id=self.storage_id),
            ],
        )

    def set_callbacks(self, app):
        # pylint: disable=inconsistent-return-statements
        @app.callback(
            [
                Output(self.name_id, "options"),
                Output(self.name_id, "value"),
                Output(self.name_wrapper_id, "style"),
            ],
            [Input(self.attr_id, "value")],
            [State(self.name_id, "value")],
        )
        def _update_name(attr, current_value):
            names = self._names_in_attr(attr)
            if not names:
                return None, None, {"visibility": "hidden"}
            value = current_value if current_value in names else names[0]
            options = [{"label": name, "value": name} for name in names]
            return options, value, {}

        @app.callback(
            [
                Output(self.date_id, "options"),
                Output(self.date_id, "value"),
                Output(self.date_wrapper_id, "style"),
            ],
            [Input(self.attr_id, "value")],
            [State(self.date_id, "value")],
        )
        def _update_date(attr, current_value):
            dates = self._dates_in_attr(attr)
            if not dates or not dates[0]:
                return [], None, {"visibility": "hidden"}

            value = current_value if current_value in dates else dates[0]
            options = [{"label": format_date(date), "value": date} for date in dates]
            return options, value, {}

        @app.callback(
            [
                Output(self.sens_name_id, "options"),
                Output(self.sens_name_id, "value"),
                Output(self.sens_name_wrapper_id, "style"),
            ],
            [Input(self.ensemble_id, "value")],
            [State(self.sens_name_id, "value")],
        )
        def _update_sens_name(ensemble, current_value):
            sens_names = self.sens_names(ensemble)
            if not sens_names:
                return [], None, {"visibility": "hidden"}
            value = current_value if current_value in sens_names else sens_names[0]
            options = [{"value": sens, "label": sens} for sens in sens_names]
            return options, value, {}

        @app.callback(
            [
                Output(self.sens_ref_id, "options"),
                Output(self.sens_ref_id, "value"),
                Output(self.sens_ref_wrapper_id, "style"),
            ],
            [Input(self.ensemble_id, "value")],
            [State(self.sens_ref_id, "value")],
        )
        def _update_sens_ref(ensemble, current_value):
            sens_names = self.sens_names(ensemble)
            if not sens_names:
                return [], None, {"visibility": "hidden"}
            value = current_value if current_value in sens_names else sens_names[0]
            options = [{"value": sens, "label": sens} for sens in sens_names]
            return options, value, {}

        @app.callback(
            Output(self.storage_id, "children"),
            [
                Input(self.attr_id, "value"),
                Input(self.name_id, "value"),
                Input(self.date_id, "value"),
                Input(self.ensemble_id, "value"),
                Input(self.sens_name_id, "value"),
                Input(self.sens_ref_id, "value"),
                Input(self.calculation_id, "value"),
            ],
        )
        def _set_data(attr, name, date, ensemble, sens_name, sens_ref, calculation_mode):

            """
            Stores current selections to dcc.Store. The information can
            be retrieved as a json string from a dash callback Input.
            E.g. [Input(surfselector.storage_id, 'children')]
            """

            # Preventing update if selections are not valid (waiting for the other callbacks)
            if not name in self._names_in_attr(attr):
                raise PreventUpdate
            if not date in self._dates_in_attr(attr):
                raise PreventUpdate
            if not self.get_sens_type(ensemble, sens_name):
                raise PreventUpdate
            if not self.get_sens_type(ensemble, sens_ref):
                raise PreventUpdate

            ref_realizations = [
                r
                for case in self.sens_cases(ensemble, sens_ref)
                for r in self.realizations(ensemble, sens_ref, case)
            ]

            sens_cases = [
                {
                    "case": senscase,
                    "realizations": self.realizations(ensemble, sens_name, senscase),
                }
                for senscase in self.sens_cases(ensemble, sens_name)
            ]
            return json.dumps(
                {
                    "attribute": attr,
                    "name": name,
                    "date": date,
                    "ensemble": ensemble,
                    "sensname": sens_name,
                    "senstype": self.get_sens_type(ensemble, sens_name),
                    "sens_cases": sens_cases,
                    "reference": {"name": sens_ref, "realizations": ref_realizations},
                    "mode": calculation_mode
                }
            )


def format_date(date_string):
    """Reformat date string for presentation
    20010101 => Jan 2001
    20010101_20010601 => (Jan 2001) - (June 2001)
    20010101_20010106 => (01 Jan 2001) - (06 Jan 2001)"""
    if len(date_string) == 8:
        return datetime.strptime(date_string, "%Y%m%d").strftime("%b %Y")

    if len(date_string) == 17:
        [begin, end] = [
            datetime.strptime(date, "%Y%m%d") for date in date_string.split("_")
        ]
        if begin.year == end.year and begin.month == end.month:
            return f"({begin.strftime('%-d %b %Y')})-\
              ({end.strftime('%-d %b %Y')})"

        return f"({begin.strftime('%b %Y')})-({end.strftime('%b %Y')})"

    return date_string
