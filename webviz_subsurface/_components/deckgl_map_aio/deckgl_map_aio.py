from typing import Dict
from dash import (
    html,
    dcc,
    callback,
    Input,
    Output,
    State,
    MATCH,
    callback_context,
    no_update,
)
from dash.exceptions import PreventUpdate


from webviz_subsurface_components import DeckGLMap
from ._deckgl_map_controller import DeckGLMapController


def colormap_spec() -> Dict:
    return {
        "@@type": "ColormapLayer",
        # pylint: disable=line-too-long
        "colormap": "/colormaps/viridis_r.png",
        "bounds": "@@#resources.mapBounds",
        "colorMapRange": [0, 1],
        "image": "@@#resources.mapImage",
        "valueRange": "@@#resources.mapRange",
        "id": "colormap-layer",
        # "pickable": True,
        "valueRange": [0, 1],
    }


def hillshading_spec() -> Dict:
    return {
        "@@type": "Hillshading2DLayer",
        "id": "hillshading-layer",
        "valueRange": "@@#resources.mapRange",
        "bounds": "@@#resources.mapBounds",
        # "pickable": True,
        "image": "@@#resources.mapImage",
        # "valueRange": [0, 1],
    }


def resources() -> Dict:
    return {
        "mapImage": "/image/dummy.png",
        "mapBounds": [0, 1, 0, 1],
        "mapRange": [0, 1],
        "mapTarget": [0.5, 0.5, 0],
    }


class DeckGLMapAIO(html.Div):
    class ids:
        map = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "map",
            "aio_id": aio_id,
        }
        colormap_image = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "colormap_image",
            "aio_id": aio_id,
        }
        colormap_range = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "colormap_range",
            "aio_id": aio_id,
        }
        polylines = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "polylines",
            "aio_id": aio_id,
        }
        selected_well = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "selected_well",
            "aio_id": aio_id,
        }
        map_data = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "map_data",
            "aio_id": aio_id,
        }

    ids = ids

    def __init__(
        self,
        aio_id,
    ):
        """"""

        super().__init__(
            [
                dcc.Store(data=[], id=self.ids.colormap_image(aio_id)),
                dcc.Store(data=[], id=self.ids.colormap_range(aio_id)),
                dcc.Store(data=[], id=self.ids.polylines(aio_id)),
                dcc.Store(data=[], id=self.ids.selected_well(aio_id)),
                dcc.Store(data=[], id=self.ids.map_data(aio_id)),
                DeckGLMap(
                    id=self.ids.map(aio_id),
                    layers=[
                        colormap_spec(),
                        hillshading_spec(),
                    ],
                    resources=resources(),
                    bounds=resources()["mapBounds"],
                    editedData={
                        "selectedDrawingFeature": [],
                        "data": {"type": "FeatureCollection", "features": []},
                    },
                ),
            ]
        )

    @callback(
        Output(ids.map(MATCH), "layers"),
        Input(ids.colormap_image(MATCH), "data"),
        Input(ids.colormap_range(MATCH), "data"),
        State(ids.map(MATCH), "layers"),
    )
    def _update_spec(colormap_image, colormap_range, current_spec):
        """This should be moved to a clientside callback"""
        import json

        print(json.dumps(current_spec, indent=4))
        raise PreventUpdate
        map_controller = DeckGLMapController(current_spec)
        triggered_prop = callback_context.triggered[0]["prop_id"]
        initial_callback = True if triggered_prop == "." else False
        # if initial_callback or "colormap_image" in triggered_prop:
        #     map_controller.update_colormap(colormap_image)
        # if initial_callback or "colormap_range" in triggered_prop:
        #     map_controller.update_colormap_range(colormap_range)
        # print(map_controller._spec)
        return map_controller._spec

    @callback(
        Output(ids.map(MATCH), "resources"),
        Output(ids.map(MATCH), "bounds"),
        Input(ids.map_data(MATCH), "data"),
        State(ids.map(MATCH), "resources"),
    )
    def update_resources(map_data, current_resources):
        triggered_prop = callback_context.triggered[0]["prop_id"]
        import json

        current_resources.update(**map_data)
        print(json.dumps(current_resources, indent=4))

        return current_resources, current_resources["mapBounds"]
