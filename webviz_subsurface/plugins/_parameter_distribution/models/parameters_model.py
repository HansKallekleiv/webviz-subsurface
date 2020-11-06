from typing import List, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import plotly.graph_objects as go
import plotly.express as px
from dash_table.Format import Format

import time


# pylint: disable=too-many-public-methods
class ParametersModel:
    """Class to process and visualize ensemble property statistics data"""

    REQUIRED_COLUMNS = [
        "ENSEMBLE",
        "REAL",
    ]

    def __init__(
        self, dataframe: pd.DataFrame, theme: dict, drop_constants: bool = True
    ) -> None:
        self._dataframe = dataframe
        self.theme = theme
        self.colorway = self.theme.plotly_theme.get("layout", {}).get("colorway", None)
        self._parameters = []
        self._prepare_data(drop_constants)
        self._statframe = self._aggregate_ensemble_data(self._dataframe)
        self._statframe_normalized = self._normalize_and_aggregate()

    def _prepare_data(self, drop_constants):

        if drop_constants:
            constant_params = [
                param
                for param in [
                    x for x in self._dataframe.columns if x not in self.REQUIRED_COLUMNS
                ]
                if len(self._dataframe[param].unique()) == 1
            ]
            self._dataframe = self._dataframe.drop(columns=constant_params)

        # Keep only LOG parameters
        log_params = [
            param.replace("LOG10_", "")
            for param in [
                x for x in self._dataframe.columns if x not in self.REQUIRED_COLUMNS
            ]
            if param.startswith("LOG10_")
        ]
        self._dataframe = self._dataframe.drop(columns=log_params)
        self._dataframe = self._dataframe.rename(
            columns={
                col: f"{col} (log)"
                for col in self._dataframe.columns
                if col.startswith("LOG10_")
            }
        )
        self._dataframe = self._dataframe.rename(
            columns={
                col: (col.split(":", 1)[1])
                for col in self._dataframe.columns
                if (":" in col and col not in self.REQUIRED_COLUMNS)
            }
        )
        self._parameters = [
            x for x in self._dataframe.columns if x not in self.REQUIRED_COLUMNS
        ]

    @property
    def dataframe_melted(self) -> pd.DataFrame:
        return self.dataframe.melt(
            id_vars=["ENSEMBLE", "REAL"], var_name="PARAMETER", value_name="VALUE"
        )

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @property
    def statframe(self) -> pd.DataFrame:
        return self._statframe

    @property
    def parameters(self) -> pd.DataFrame:
        return self._parameters

    @parameters.setter
    def parameters(self, sortorder):
        self._parameters = sortorder

    @property
    def ensembles(self) -> List[str]:
        return list(self.dataframe["ENSEMBLE"].unique())

    def _aggregate_ensemble_data(self, dframe) -> pd.DataFrame:
        return (
            dframe.drop(columns=["REAL"])
            .groupby(["ENSEMBLE"])
            .agg(
                [
                    ("Avg", np.mean),
                    ("Stddev", np.std),
                    ("P10", lambda x: np.percentile(x, 10)),
                    ("P90", lambda x: np.percentile(x, 90)),
                    ("Min", np.min),
                    ("Max", np.max),
                ]
            )
            .stack(0)
            .rename_axis(["ENSEMBLE", "PARAMETER"])
            .reset_index()
        )

    def _normalize_and_aggregate(self):
        df = self._dataframe.copy()

        df_norm = pd.DataFrame(
            MinMaxScaler().fit_transform(df[self.parameters]),
            columns=[x for x in df.columns if x in self.parameters],
        )
        extra_cols = [x for x in df.columns if x not in self.parameters]
        df_norm[extra_cols] = df[extra_cols]
        return self._aggregate_ensemble_data(df_norm)

    def sort_parameters(
        self,
        ensemble: str,
        delta_ensemble: str,
        sortby: str,
    ):
        start = time.time()
        print("sort")
        df = self._delta_statistics(ensemble, delta_ensemble)
        df = df.sort_values(
            by="PARAMETER" if sortby == "Name" else [(sortby, "diff")],
            ascending=(sortby == "Name"),
        )
        end = time.time()
        print(end - start)
        self._parameters = list(df["PARAMETER"])
        return list(df["PARAMETER"])

    def _delta_statistics(
        self,
        ensemble: str,
        delta_ensemble: str,
    ) -> pd.DataFrame:

        df = self._statframe_normalized.copy()
        df = df.pivot_table(columns=["ENSEMBLE"], index="PARAMETER").reset_index()

        df["Avg", "diff"] = abs(df["Avg"][ensemble] - df["Avg"][delta_ensemble])
        df["Stddev", "diff"] = df["Stddev"][ensemble] - df["Stddev"][delta_ensemble]

        return df

    @staticmethod
    def make_table(df: pd.DataFrame) -> Tuple[List[Any], List[Any]]:
        df.columns = df.columns.map(" | ".join).str.strip(" | ")
        columns = [
            {"id": col, "name": col, "type": "numeric", "format": Format(precision=3)}
            for col in df.columns
        ]
        return columns, df.to_dict("records")

    def make_statistics_table(
        self,
        ensembles: list,
        parameters: List[Any],
    ) -> Tuple[List[Any], List[Any]]:
        df = self.statframe.copy()
        df = df[df["ENSEMBLE"].isin(ensembles)]
        df = df[df["PARAMETER"].isin(parameters)]
        df = df.pivot_table(columns=["ENSEMBLE"], index="PARAMETER").reset_index()
        return self.make_table(df)

    def make_grouped_plot(
        self,
        ensembles: list,
        parameters: List[Any],
        plot_type: str = "histogram",
    ) -> go.Figure:

        df = self.dataframe_melted.copy()
        df = df[df["ENSEMBLE"].isin(ensembles)]
        df = df[df["PARAMETER"].isin(parameters)]
        sortorder = [x for x in self._parameters if x in parameters]
        df = df.set_index("PARAMETER").loc[sortorder].reset_index()

        if len(parameters) > 72:
            facet_col_wrap = 12
        elif 42 < len(parameters) <= 72:
            facet_col_wrap = 9
        elif 18 < len(parameters) <= 42:
            facet_col_wrap = 6
        else:
            facet_col_wrap = 3

        if plot_type == "histogram":
            fig = (
                px.violin(
                    df,
                    x="VALUE",
                    facet_col="PARAMETER",
                    facet_col_wrap=facet_col_wrap,
                    color="ENSEMBLE",
                    color_discrete_sequence=self.colorway,
                )
                .update_xaxes(
                    matches=None, fixedrange=True, title=None, showticklabels=True
                )
                .update_yaxes(matches=None, fixedrange=True)
                .for_each_trace(
                    lambda t: t.update(
                        meanline_visible=True,
                        orientation="h",
                        side="positive",
                        width=3,
                    )
                )
                .for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
                # .add_vline(
                #    x=0,
                #    row="all",
                #    col="all",
                #    line_width=3,
                #    line_dash="dash",
                #    line_color="green",
                # )
                # .for_each_shape(
                #    lambda a: a.update(yref=a.yref.replace(" domain", ""), y1=1.5)
                # )
            )
        fig = fig.to_dict()
        fig["layout"] = self.theme.create_themed_layout(fig["layout"])
        return fig
