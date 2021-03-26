from typing import Dict, List, Callable, Tuple, Optional, Union
import warnings

import xtgeo
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from webviz_subsurface._models import SurfaceSetModel, SurfaceLeafletModel, WellSetModel
from webviz_subsurface._datainput.well import (
    make_well_layer,
    create_leaflet_well_marker_layer,
)

# pylint: disable=too-many-statements
def update_maps(
    app: dash.Dash,
    get_uuid: Callable,
    surface_set_models: Dict[str, SurfaceSetModel],
    well_set_model: WellSetModel,
) -> None:
    @app.callback(
        Output({"id": get_uuid("map"), "element": "label"}, "children"),
        Output(get_uuid("leaflet-map"), "layers"),
        Output({"id": get_uuid("map2"), "element": "label"}, "children"),
        Output(get_uuid("leaflet-map2"), "layers"),
        Output({"id": get_uuid("map3"), "element": "label"}, "children"),
        Output(get_uuid("leaflet-map3"), "layers"),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map",
                "element": "surfaceattribute",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map2",
                "element": "surfaceattribute",
            },
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map", "element": "surfacename"},
            "value",
        ),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map2",
                "element": "surfacename",
            },
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map", "element": "ensemble"},
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map2", "element": "ensemble"},
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map", "element": "calculation"},
            "value",
        ),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map2",
                "element": "calculation",
            },
            "value",
        ),
        Input(get_uuid("leaflet-map"), "switch"),
        Input(get_uuid("leaflet-map2"), "switch"),
        Input(get_uuid("leaflet-map3"), "switch"),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map", "element": "options"},
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map2", "element": "options"},
            "value",
        ),
        Input(get_uuid("realization-store"), "data"),
        Input({"id": get_uuid("intersection_data"), "element": "well"}, "value"),
        Input({"id": get_uuid("map"), "element": "stored_polyline"}, "data"),
        State(get_uuid("leaflet-map"), "layers"),
        State(get_uuid("leaflet-map2"), "layers"),
        State(get_uuid("leaflet-map3"), "layers"),
    )
    # pylint: disable=too-many-arguments, too-many-locals, too-many-branches
    def _update_maps(
        surfattr_map: str,
        surfattr_map2: str,
        surfname_map: str,
        surfname_map2: str,
        ensemble_map: str,
        ensemble_map2: str,
        calc_map: str,
        calc_map2: str,
        shade_map: Dict[str, bool],
        shade_map2: Dict[str, bool],
        shade_map3: Dict[str, bool],
        options: List[str],
        options2: List[str],
        real_list: List[str],
        wellname: Optional[str],
        polyline: Optional[List],
        current_map: List,
        current_map2: List,
        current_map3: List,
    ) -> Tuple[str, List, str, List, str, List]:
        """Generate Leaflet layers for the three map views"""
        realizations = [int(real) for real in real_list]
        ctx = dash.callback_context.triggered[0]

        if polyline is not None:
            poly_layer = create_leaflet_polyline_layer(polyline)
            # If callback is triggered by polyline drawing, only update polyline
            if "stored_polyline" in ctx["prop_id"]:
                for map_layers in [current_map, current_map2, current_map3]:
                    map_layers = replace_or_add_map_layer(
                        map_layers, "Polyline", poly_layer
                    )
                return (
                    f"Surface A: {surfattr_map} - {surfname_map} - {ensemble_map} - {calc_map}",
                    current_map,
                    f"Surface B: {surfattr_map2} - {surfname_map2} - {ensemble_map2} - {calc_map2}",
                    current_map2,
                    "Surface A-B",
                    current_map3,
                )
        if wellname is not None:
            well = well_set_model.get_well(wellname)
            well_layer = make_well_layer(well, name=well.name)

            # If callback is triggered by well change, only update well layer
            if "well" in ctx["prop_id"]:
                for map_layers in [current_map, current_map2, current_map3]:
                    map_layers = replace_or_add_map_layer(
                        map_layers, "Well", well_layer
                    )
                return (
                    f"Surface A: {surfattr_map} - {surfname_map} - "
                    f"{ensemble_map} - {calc_map}",
                    current_map,
                    f"Surface B: {surfattr_map2} - {surfname_map2} - "
                    f"{ensemble_map2} - {calc_map2}",
                    current_map2,
                    "Surface A-B",
                    current_map3,
                )

        # Calculate maps
        if calc_map in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]:
            surface = surface_set_models[ensemble_map].calculate_statistical_surface(
                name=surfname_map,
                attribute=surfattr_map,
                calculation=calc_map,
                realizations=realizations,
            )

        else:
            surface = surface_set_models[ensemble_map].get_realization_surface(
                name=surfname_map, attribute=surfattr_map, realization=int(calc_map)
            )
        if calc_map2 in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]:
            surface2 = surface_set_models[ensemble_map2].calculate_statistical_surface(
                name=surfname_map2,
                attribute=surfattr_map2,
                calculation=calc_map2,
                realizations=realizations,
            )

        else:
            surface2 = surface_set_models[ensemble_map2].get_realization_surface(
                name=surfname_map2, attribute=surfattr_map2, realization=int(calc_map2)
            )

        # Generate Leaflet layers
        surface_layers: List[dict] = [
            SurfaceLeafletModel(
                surface,
                name="surface",
                apply_shading=shade_map.get("value", False),
            ).layer
        ]
        surface_layers2: List[dict] = [
            SurfaceLeafletModel(
                surface2,
                name="surface2",
                apply_shading=shade_map2.get("value", False),
            ).layer
        ]
        try:
            surface3 = surface.copy()
            surface3.values = surface3.values - surface2.values

            diff_layers: List[dict] = []
            diff_layers.append(
                SurfaceLeafletModel(
                    surface3,
                    name="surface3",
                    apply_shading=shade_map3.get("value", False),
                ).layer
            )
        except ValueError:
            diff_layers = []

        if wellname is not None:
            surface_layers.append(well_layer)
            surface_layers2.append(well_layer)
            diff_layers.append(well_layer)
        if polyline is not None:
            surface_layers.append(poly_layer)
            surface_layers2.append(poly_layer)
            diff_layers.append(poly_layer)

        if well_set_model is not None:
            if options is not None or options2 is not None:
                if "intersect_well" in options or "intersect_well" in options2:

                    ### This is potentially a heavy task as it loads all wells into memory
                    wells: List[xtgeo.Well] = list(well_set_model.wells.values())

                if "intersect_well" in options:
                    surface_layers.append(
                        create_leaflet_well_marker_layer(wells, surface)
                    )
                if "intersect_well" in options2:
                    surface_layers2.append(
                        create_leaflet_well_marker_layer(wells, surface2)
                    )
        return (
            f"Surface A: {surfattr_map} - {surfname_map} - {ensemble_map} - {calc_map}",
            surface_layers,
            f"Surface B: {surfattr_map2} - {surfname_map2} - {ensemble_map2} - {calc_map2}",
            surface_layers2,
            "Surface A-B",
            diff_layers,
        )

    @app.callback(
        Output({"id": get_uuid("map"), "element": "stored_polyline"}, "data"),
        Input(get_uuid("leaflet-map"), "polyline_points"),
    )
    def _store_polyline_points(
        positions_yx: List[List[float]],
    ) -> Optional[List[List[float]]]:
        """Stores drawn in polyline in a dcc.Store. Reversing elements to reflect
        normal behaviour"""
        if positions_yx is not None:
            try:
                return [[pos[1], pos[0]] for pos in positions_yx]
            except TypeError:
                warnings.warn("Polyline for map is not valid format")
                return None
        raise PreventUpdate

    @app.callback(
        Output(
            {"id": get_uuid("intersection_data"), "element": "source"},
            "value",
        ),
        Output(
            {"id": get_uuid("intersection_data"), "element": "well"},
            "value",
        ),
        Input(get_uuid("leaflet-map"), "clicked_shape"),
        Input(get_uuid("leaflet-map"), "polyline_points"),
    )
    # pylint: disable=protected-access
    def _update_from_map_click(
        clicked_shape: Optional[Dict],
        _polyline: List[List[float]],
    ) -> Tuple[str, Union[dash.dash._NoUpdate, str]]:
        """Update intersection source and optionally selected well when
        user clicks a shape in map1"""
        ctx = dash.callback_context.triggered[0]
        if "polyline_points" in ctx["prop_id"]:
            return "surface", dash.no_update
        if clicked_shape is None:
            raise PreventUpdate
        if clicked_shape.get("id") == "random_line":
            return "surface", dash.no_update
        if clicked_shape.get("id") in well_set_model.well_names:
            return "well", clicked_shape.get("id")
        raise PreventUpdate


def create_leaflet_polyline_layer(positions: List[List[float]]) -> Dict:
    return {
        "id": "Polyline",
        "name": "Polyline",
        "baseLayer": False,
        "checked": True,
        "action": "update",
        "data": [
            {
                "type": "polyline",
                "id": "random_line",
                "positions": positions,
                "color": "blue",
                "tooltip": "polyline",
            },
            {
                "type": "circle",
                "center": positions[0],
                "radius": 60,
                "color": "blue",
                "tooltip": "B",
            },
            {
                "type": "circle",
                "center": positions[-1],
                "radius": 60,
                "color": "blue",
                "tooltip": "B'",
            },
        ],
    }


def replace_or_add_map_layer(
    layers: List[Dict], uuid: str, new_layer: Dict
) -> List[Dict]:
    for idx, layer in enumerate(layers):
        if layer.get("id") == uuid:
            layers[idx] = new_layer
            return layers
    layers.append(new_layer)
    return layers
