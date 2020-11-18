from typing import List, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import plotly.graph_objects as go
import plotly.express as px
from dash_table.Format import Format

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

    def _prepare_data(self, drop_constants):

        self._dataframe = self._dataframe.reset_index(drop=True)
        print(self._dataframe[["RMSGLOBPARAMS:FWL", "FWL"]])

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
        self._dataframe = self._dataframe.loc[:, ~self._dataframe.columns.duplicated()]
        self._parameters = [
            x for x in self._dataframe.columns if x not in self.REQUIRED_COLUMNS
        ]

    def _aggregate_ensemble_data(self, dframe) -> pd.DataFrame:
        print(dframe.columns)
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
        df_norm[self.REQUIRED_COLUMNS] = df[self.REQUIRED_COLUMNS]
        df = self._aggregate_ensemble_data(df_norm)
        return df.pivot_table(columns=["ENSEMBLE"], index="PARAMETER").reset_index()

    def sort_parameters(
        self,
        ensemble: str,
        delta_ensemble: str,
        sortby: str,
    ):
        # compute diff between ensembles
        df = self._statframe_normalized.copy()
        df["Avg", "diff"] = abs(df["Avg"][ensemble] - df["Avg"][delta_ensemble])
        df["Stddev", "diff"] = df["Stddev"][ensemble] - df["Stddev"][delta_ensemble]

        # set parameter column and update parameter list
        df = df.sort_values(
            by="PARAMETER" if sortby == "Name" else [(sortby, "diff")],
            ascending=(sortby == "Name"),
        )
        self._parameters = list(df["PARAMETER"])
        return list(df["PARAMETER"])

    @staticmethod
    def make_table(df: pd.DataFrame) -> Tuple[List[Any], List[Any]]:
        df.columns = df.columns.map(" | ".join).str.strip(" | ")
        columns = [
            {"id": col, "name": col, "type": "numeric", "format": Format(precision=3)}
            for col in df.columns
        ]
        return columns, df.to_dict("records")

    def _sort_parameters_col(self, df, parameters):
        sortorder = [x for x in self._parameters if x in parameters]
        return df.set_index("PARAMETER").loc[sortorder].reset_index()

    def make_statistics_table(
        self,
        ensembles: list,
        parameters: List[Any],
    ) -> Tuple[List[Any], List[Any]]:
        df = self.statframe.copy()
        df = df[df["ENSEMBLE"].isin(ensembles)]
        df = df[df["PARAMETER"].isin(parameters)]
        df = df.pivot_table(columns=["ENSEMBLE"], index="PARAMETER").reset_index()
        df = self._sort_parameters_col(df, parameters)
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
        df = self._sort_parameters_col(df, parameters)

        if plot_type == "histogram":
            fig = (
                px.violin(
                    df,
                    x="VALUE",
                    facet_col="PARAMETER",
                    facet_col_wrap=min(
                        min(
                            [x for x in range(100) if (x * (x + 1)) >= len(parameters)]
                        ),
                        20,
                    ),
                    color="ENSEMBLE",
                    color_discrete_sequence=self.colorway,
                )
                .update_xaxes(
                    matches=None,
                    fixedrange=True,
                    title=None,
                    showticklabels=(len(parameters) < 20),
                )
                .for_each_trace(
                    lambda t: t.update(
                        hoveron="violins",
                        hoverinfo="name",
                        meanline_visible=True,
                        #    meanline={"color": "black"},
                        orientation="h",
                        side="positive",
                        width=3,
                        points=False,
                    )
                )
                .for_each_annotation(
                    lambda a: a.update(
                        hovertext=a.text.split("=")[-1],
                        text=(a.text.split("=")[-1]) if len(parameters) < 40 else "",
                    )
                )
            )

        fig = fig.to_dict()
        fig["layout"] = self.theme.create_themed_layout(fig["layout"])

        return fig

    def get_real_order(self, ensemble: str, parameter: str) -> pd.DataFrame:
        df = self.dataframe_melted.copy()
        df = df[["VALUE", "REAL"]].loc[
            (df["ENSEMBLE"] == ensemble) & (df["PARAMETER"] == parameter)
        ]
        return df.sort_values(by="VALUE")
