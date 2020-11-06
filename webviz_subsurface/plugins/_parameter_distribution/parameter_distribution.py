import pathlib
from typing import Optional

import dash_core_components as dcc
from webviz_config import WebvizPluginABC
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface
from .views import main_view
from .models import ParametersModel, SimulationTimeSeriesModel, EnsembleSetModel
from .controllers import (
    property_qc_controller,
    property_response_controller,
)
from .data_loaders import read_csv, read_parquet


class ParameterDistribution(WebvizPluginABC):
    """This plugin visualizes ensemble statistics calculated from grid properties.

---
**The main input to this plugin is property statistics extracted from grid models.
See the documentation in [fmu-tools](http://fmu-docs.equinor.com/) on how to generate this data.
Additional data includes UNSMRY data and optionally irap binary surfaces stored in standardized \
FMU format.

**Input data can be provided in two ways: Aggregated or read from ensembles stored on scratch.**

**Using aggregated data**
* **`csvfile_smry`:** Aggregated `csv` file for volumes with `REAL`, `ENSEMBLE`, `DATE` and \
    vector columns (absolute path or relative to config file).
* **`csvfile_statistics`:** Aggregated `csv` file for property statistics. See the \
    documentation in [fmu-tools](http://fmu-docs.equinor.com/) on how to generate this data.

**Using raw ensemble data stored in realization folders**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`statistic_file`:** Csv file for each realization with property statistics.
* **`column_keys`:** List of vectors to extract. If not given, all vectors \
    from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`time_index`:** Time separation between extracted values. Can be e.g. `monthly` (default) or \
    `yearly`.

---

!> For smry data it is **strongly recommended** to keep the data frequency to a regular frequency \
(like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` \
(controlled by the `sampling` key). This is because the statistics and fancharts are calculated \
per DATE over all realizations in an ensemble, and the available dates should therefore not \
differ between individual realizations of an ensemble.

**Using aggregated data**

**Using simulation time series data directly from `.UNSMRY` files**

Time series data are extracted automatically from the `UNSMRY` files in the individual
realizations, using the `fmu-ensemble` library.

?> Using the `UNSMRY` method will also extract metadata like units, and whether the vector is a \
rate, a cumulative, or historical. Units are e.g. added to the plot titles, while rates and \
cumulatives are used to decide the line shapes in the plot. Aggregated data may on the other \
speed up the build of the app, as processing of `UNSMRY` files can be slow for large models.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the \
individual realizations. You should therefore not have more than one `UNSMRY` file in this \
folder, to avoid risk of not extracting the right data.


    * **`drop_constants`:** Drop constant parameters.


"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app,
        ensembles: Optional[list] = None,
        csvfile_parameters: pathlib.Path = None,
        csvfile_smry: pathlib.Path = None,
        time_index: str = "monthly",
        column_keys: Optional[list] = None,
        drop_constants: bool = True,
    ):
        super().__init__()
        WEBVIZ_ASSETS.add(
            pathlib.Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "container.css"
        )
        self.theme = app.webviz_settings["theme"]
        self.time_index = time_index
        self.column_keys = column_keys
        self.ensembles = ensembles
        self.csvfile_parameters = csvfile_parameters
        self.csvfile_smry = csvfile_smry

        if ensembles is not None:
            self.emodel = EnsembleSetModel(
                ensemble_paths={
                    ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][
                        ens
                    ]
                    for ens in ensembles
                }
                if ensembles is not None
                else None
            )
            self.pmodel = ParametersModel(
                dataframe=self.emodel.load_parameters(),
                theme=self.theme,
                drop_constants=drop_constants,
            )
        #     self.vmodel = SimulationTimeSeriesModel(
        #         dataframe=self.emodel.load_smry(
        #             time_index=self.time_index,
        #         ),
        #         theme=self.theme,
        #     )
        else:
            self.pmodel = ParametersModel(
                dataframe=read_parquet(csvfile_parameters),
                theme=self.theme,
                drop_constants=drop_constants,
            )
            # self.vmodel = SimulationTimeSeriesModel(
            #     dataframe=read_csv(csvfile_smry), theme=self.theme.plotly_theme
            # )

        self.set_callbacks(app)

    @property
    def layout(self) -> dcc.Tabs:
        return main_view(parent=self)

    def set_callbacks(self, app) -> None:
        property_qc_controller(self, app)
        property_response_controller(self, app)

    def add_webvizstore(self):
        store = []
        if self.ensembles is not None:
            store.extend(self.emodel.webvizstore)
        else:
            store.extend(
                (
                    read_csv,
                    [
                        {"csv_file": self.csvfile_smry},
                        {"csv_file": self.csvfile_parameters},
                    ],
                )
            )
        return store
