from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd
from dash.exceptions import PreventUpdate
from dash_table import DataTable
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, ALL
import webviz_core_components as wcc
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore
from webviz_config import WebvizPluginABC

from webviz_subsurface._datainput.inplace_volumes import extract_volumes

from webviz_subsurface._abbreviations.number_formatting import table_statistics_base
from .models.inplace_volumes_model import InplaceVolumesModel
from webviz_subsurface._models.ensemble_set_model import EnsembleSetModel
from .tour import tour
from .views.main_view import main_view
from .controllers import vol_controller


class InplaceVolumes(WebvizPluginABC):
    """Visualizes inplace volumetric results from
FMU ensembles.

Input can be given either as aggregated `csv` files or as ensemble name(s)
defined in `shared_settings` (with volumetric `csv` files stored per realization).

---

**Using aggregated data**
* **`csvfile`:** Aggregated csvfile with `REAL`, `ENSEMBLE` and `SOURCE` columns \
(absolute path or relative to config file).

**Using data stored per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`volfiles`:**  Key/value pair of csv files E.g. `{geogrid: geogrid--oil.csv}`.
Only relevant if `ensembles` is defined. The key (e.g. `geogrid`) will be used as `SOURCE`.
* **`volfolder`:** Local folder for the `volfiles`.

**Common settings for both input options**
* **`response`:** Optional volume response to visualize initially.

---

?> The input files must follow FMU standards.

* [Example of an aggregated file for `csvfiles`](https://github.com/equinor/\
webviz-subsurface-testdata/blob/master/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/\
realization-0/iter-0/share/results/volumes/geogrid--oil.csv).

**The following columns will be used as available filters, if present:**

* `ZONE`
* `REGION`
* `FACIES`
* `LICENSE`
* `SOURCE` (relevant if calculations are done for multiple grids)


**Remaining columns are seen as volumetric responses.**

All names are allowed (except those mentioned above, in addition to `REAL` and `ENSEMBLE`), \
but the following responses are given more descriptive names automatically:

* `BULK_OIL`: Bulk Volume (Oil)
* `NET_OIL`: Net Volume (Oil)
* `PORE_OIL`: Pore Volume (Oil)
* `HCPV_OIL`: Hydro Carbon Pore Volume (Oil)
* `STOIIP_OIL`: Stock Tank Oil Initially In Place
* `BULK_GAS`: Bulk Volume (Gas)
* `NET_GAS`: Net Volume (Gas)
* `PORV_GAS`: Pore Volume (Gas)
* `HCPV_GAS`: Hydro Carbon Pore Volume (Gas)
* `GIIP_GAS`: Gas Initially In Place
* `RECOVERABLE_OIL`: Recoverable Volume (Oil)
* `RECOVERABLE_GAS`: Recoverable Volume (Gas)

"""

    TABLE_STATISTICS = [("Group", {})] + table_statistics_base()

    def __init__(
        self,
        app,
        csvfile: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        response: str = "STOIIP_OIL",
    ):

        super().__init__()

        self.csvfile = csvfile if csvfile else None
        self.ensembles = ensembles
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        if csvfile and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )
        if csvfile:
            dataframe = read_csv(csvfile)

        elif ensembles and volfiles:
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
            dataframe = self.emodel.extract_volumes(
                volfolder=volfolder, volfiles=volfiles
            )

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )
        self.vmodel = InplaceVolumesModel(
            dataframe=dataframe, initial_response=response
        )
        self.set_callbacks(app)

    @property
    def tour_steps(self):
        return tour(parent=self)

    def add_webvizstore(self):
        if self.ensembles is not None:
            return self.emodel.webvizstore
        return [
            (
                read_csv,
                [
                    {"csv_file": self.csvfile},
                ],
            )
        ]

    @property
    def layout(self):
        """Main layout"""
        return main_view(parent=self)

    def set_callbacks(self, app):
        vol_controller(parent=self, app=app)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=None)
