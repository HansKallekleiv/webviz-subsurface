import os
from pathlib import Path

import xtgeo
from flask import send_file
from dash import Dash
import webviz_subsurface
import webviz_subsurface_components as wsc


def set_routes(app: Dash, surface_ensemble_set_model) -> None:
    def _send_surface_as_png(ensemble, surface_id):
        surface_id = surface_id.split(".png")[0]

        if not os.path.isfile(f"/tmp/{surface_id}.png"):
            surface_path = surface_ensemble_set_model[ensemble]._get_path_from_id(
                surface_id
            )
            surface = xtgeo.surface_from_file(surface_path)

            surface_data = wsc.XtgeoSurfaceArray(surface.copy())
            url = surface_data.map_image

            url.save(f"/tmp/{surface_id}.png", format="png")
        return send_file(f"/tmp/{surface_id}.png", mimetype="image/png")

    def _send_dummy():
        surface = xtgeo.RegularSurface(ncol=1, nrow=1, xinc=1, yinc=1)
        surface_data = wsc.XtgeoSurfaceArray(surface)
        url = surface_data.map_image

        url.save(f"/tmp/test.png", mimetype="image/png")
        return send_file("/tmp/test.png", mimetype="image/png")

    def _send_colormap(colormap="seismic"):
        return send_file(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "colormaps"
            / f"{colormap}.png",
            mimetype="image/png",
        )

    app.server.view_functions["_send_surface_as_png"] = _send_surface_as_png
    app.server.view_functions["_send_dummy"] = _send_dummy
    app.server.view_functions["_send_colormap"] = _send_colormap

    app.server.add_url_rule(
        "/surface/<ensemble>/<surface_id>",
        "_send_surface_as_png",
    )
    app.server.add_url_rule(
        "/image/dummy.png",
        "_send_dummy",
    )
    app.server.add_url_rule(
        "/colormaps/<colormap>.png",
        "_send_colormap",
    )
