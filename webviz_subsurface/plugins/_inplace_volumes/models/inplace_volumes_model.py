import pandas as pd
from webviz_subsurface._abbreviations.volume_terminology import (
    volume_description,
    volume_unit,
)


class InplaceVolumesModel:
    """Class to process and visualize ensemble inplace volumetrics"""

    SINGLE_FILTERS = [
        "ENSEMBLE",
        "SOURCE",
    ]
    MULTI_FILTERS = [
        "ZONE",
        "REGION",
        "FACIES",
        "LICENSE",
        "FIPNUM",
    ]

    def __init__(
        self,
        dataframe: pd.DataFrame,
        initial_response: str = None,
        single_filters: list = None,
        multi_filters: list = None,
        theme: dict = None,
    ) -> None:
        self._dataframe = dataframe
        self._single_filters = single_filters if single_filters is not None else []
        self._multi_filters = multi_filters if multi_filters is not None else []
        self._initial_response = (
            initial_response
            if initial_response is not None and initial_response in self.responses
            else self.responses[0]
        )

    @property
    def initial_response(self):
        return self._initial_response

    @property
    def dataframe(self):
        return self._dataframe

    @property
    def single_filters(self):
        return [
            x
            for x in self.SINGLE_FILTERS + self._single_filters
            if x in self.dataframe.columns
        ]

    @property
    def multi_filters(self):
        return [
            x
            for x in self.MULTI_FILTERS + self._multi_filters
            if x in self.dataframe.columns
        ]

    @property
    def responses(self):
        """List of available volume responses in dframe"""
        return [
            x
            for x in self.dataframe.columns
            if x not in self.single_filters + self.multi_filters + ["REAL"]
        ]

    @staticmethod
    def response_description(response):
        return volume_description(response)

    @staticmethod
    def response_unit(response):
        return volume_unit(response)

    @staticmethod
    def filter_dataframe(dataframe, columns, column_values):
        dframe = dataframe.copy()
        if not isinstance(columns, list):
            columns = [columns]
        for filt, col in zip(column_values, columns):
            if isinstance(filt, list):
                dframe = dframe.loc[dframe[col].isin(filt)]
            else:
                dframe = dframe.loc[dframe[col] == filt]
        return dframe

    # def plot_table(response, name):
    #     values = dframe[response]
    #     try:
    #         output = {
    #             "Group": str(name),
    #             "Minimum": values.min(),
    #             "Maximum": values.max(),
    #             "Mean": values.mean(),
    #             "Stddev": values.std(),
    #             "P10": np.percentile(values, 90),
    #             "P90": np.percentile(values, 10),
    #         }
    #     except KeyError:
    #         output = None

    #     return output