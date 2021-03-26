from typing import Dict, List, Optional, Callable, Tuple

import numpy as np
import pandas as pd
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from webviz_subsurface._models import SurfaceSetModel, WellSetModel


# pylint: disable=too-many-statements
def update_uncertainty_table(
    app: dash.Dash,
    get_uuid: Callable,
    surface_set_models: Dict[str, SurfaceSetModel],
    well_set_model: WellSetModel,
) -> None:
    @app.callback(
        Output({"id": get_uuid("uncertainty-table"), "element": "wrapper"}, "style"),
        Output(
            {"id": get_uuid("uncertainty-table"), "element": "display-button"},
            "children",
        ),
        Input(
            {"id": get_uuid("uncertainty-table"), "element": "display-button"},
            "n_clicks",
        ),
    )
    def _display_uncertainty_table(n_clicks: Optional[int]) -> Tuple[Dict, str]:
        if not n_clicks:
            raise PreventUpdate
        if n_clicks % 2 == 0:

            return {"display": "none", "flex": 3}, "Show uncertainty table"
        return {"display": "inline", "flex": 3}, "Hide uncertainty table"

    @app.callback(
        Output({"id": get_uuid("uncertainty-table"), "element": "table"}, "data"),
        Output({"id": get_uuid("uncertainty-table"), "element": "label"}, "children"),
        Input(
            {"id": get_uuid("uncertainty-table"), "element": "apply-button"}, "n_clicks"
        ),
        State({"id": get_uuid("intersection_data"), "element": "well"}, "value"),
        State(
            {"id": get_uuid("intersection_data"), "element": "surface_attribute"},
            "value",
        ),
        State(
            {"id": get_uuid("intersection_data"), "element": "surface_names"}, "value"
        ),
        State({"id": get_uuid("intersection_data"), "element": "ensembles"}, "value"),
        State(get_uuid("realization-store"), "data"),
    )
    # pylint: disable=too-many-arguments: disable=too-many-branches, too-many-locals
    def _update_uncertainty_table(
        apply_btn: Optional[int],
        wellname: str,
        surface_attribute: str,
        surface_names: List[str],
        ensembles: List[str],
        realizations: List[int],
    ) -> Tuple[List, str]:
        if apply_btn is None:
            raise PreventUpdate
        dframes = []

        well = well_set_model.get_well(wellname)
        realizations = [int(real) for real in realizations]
        for ensemble in ensembles:
            surfset = surface_set_models[ensemble]
            for surfacename in surface_names:
                for calculation in ["Mean", "Min", "Max"]:
                    surface = surfset.calculate_statistical_surface(
                        name=surfacename,
                        attribute=surface_attribute,
                        calculation=calculation,
                        realizations=realizations,
                    )

                    with np.errstate(invalid="ignore"):
                        surface_picks = well.get_surface_picks(surface)
                        if surface_picks is None:
                            dframe = pd.DataFrame([{"Z_TVDSS": 0, "MD": 0}])
                        else:
                            dframe = surface_picks.dataframe.drop(
                                columns=["X_UTME", "Y_UTMN", "DIRECTION", "WELLNAME"]
                            )
                            dframe["Z_TVDSS"] = dframe["Z_TVDSS"].apply(
                                lambda x: np.round(x, 2)
                            )
                            dframe.rename({well.mdlogname: "MD"}, axis=1, inplace=True)
                            # Do not calculate MD if Well tvd is truncated
                            dframe["MD"] = (
                                dframe["MD"].apply(lambda x: np.round(x, 2))
                                if not well_set_model.is_truncated
                                else None
                            )

                        dframe["Calculation"] = calculation
                        dframe["Pick no"] = dframe.index
                        dframe["Surface name"] = surfacename
                        dframe["Ensemble"] = ensemble
                        dframes.append(dframe)

        dframe = pd.concat(dframes).sort_values(
            by=(["Surface name", "Ensemble", "Pick no"])
        )
        return dframe.to_dict("records"), f"Statistics for well {wellname}"
