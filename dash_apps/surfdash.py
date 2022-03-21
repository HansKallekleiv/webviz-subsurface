from enum import Enum
from pathlib import Path
import glob

import numpy as np
import xtgeo
import pyvista as pv
from ecl.grid.ecl_grid import EclGrid

import dash
import dash_vtk
from dash_vtk.utils import to_mesh_state


def surface_to_structured_grid(surface: xtgeo.RegularSurface) -> pv.StructuredGrid:

    xi, yi = surface.get_xy_values(asmasked=False)
    zi = surface.values
    zif = np.ma.filled(zi, fill_value=np.nan)

    sgrid = pv.StructuredGrid(xi, yi, zif)
    # sgrid.flip_z(inplace=True)
    sgrid["Elevation"] = zif.flatten(order="F")

    return sgrid


path = glob.glob(
    "../map/webviz-subsurface-testdata/01_drogon_ahm/realization-*/iter-0/share/results/maps/topvolantis--ds_extract_postprocess.gri"
)

surfaces = xtgeo.Surfaces()
surfs = []
for sp in path:
    s = xtgeo.surface_from_file(sp, fformat="irap_binary")
    s.values *= -1
    surfs.append(s)
surfaces.surfaces = surfs
mb = pv.MultiBlock()

# for surface in surfaces:

#     mb.append(surface_to_structured_grid(surface))
min_surf: xtgeo.RegularSurface = surfaces.apply(np.min, axis=0)
max_surf = surfaces.apply(np.max, axis=0)
mean_surf = surfaces.apply(np.mean, axis=0)
stddev_surf = surfaces.apply(np.std, axis=0)

stddevvals = [
    stddev_surf.values,
    stddev_surf.values,
]
# sgrid["Elevation"] = zif.flatten(order="F")
# min_surf.load_values()
# mean_surf.load_values()
# max_surf.load_values()
min_mesh = surface_to_structured_grid(min_surf)
mean_mesh = surface_to_structured_grid(mean_surf)
max_mesh = surface_to_structured_grid(max_surf)
min_mesh.scale([1, 1, 5], inplace=True)
mean_mesh.scale([1, 1, 5], inplace=True)
max_mesh.scale([1, 1, 5], inplace=True)
xiv = []
yiv = []
ziv = []

for surface in [min_surf, max_surf]:
    xi, yi = min_surf.get_xy_values(asmasked=False)
    zi = surface.values
    zif = np.ma.filled(zi, fill_value=np.nan)
    xiv.append(xi)
    yiv.append(yi)
    ziv.append(zif)

vol = pv.StructuredGrid(np.array(xiv), np.array(yiv), np.array(ziv))
vol["Elevation"] = np.array(stddevvals).flatten(order="F")
vol.scale([1, 1, 5], inplace=True)
print(min_mesh.dimensions)
print(vol)
xrng = np.arange(-10, 10, 2, dtype=np.float32)
yrng = np.arange(-10, 10, 2, dtype=np.float32)
zrng = np.arange(-10, 10, 2, dtype=np.float32)
x, y, z = np.meshgrid(xrng, yrng, zrng)
grid = pv.StructuredGrid(x, y, z)
print(grid)
# geom = mb.extract_geometry()

min_range = [min_surf.values.min(), min_surf.values.max()]
mean_range = [mean_surf.values.min(), mean_surf.values.max()]
max_range = [max_surf.values.min(), max_surf.values.max()]


app = dash.Dash()

app.layout = dash_vtk.View(
    style={"height": "90vh"},
    children=[
        # dash_vtk.GeometryRepresentation(
        #     colorDataRange=min_range,
        #     # id={"id": self.uuid("well-rep"), "name": well_name},
        #     children=[
        #         dash_vtk.Mesh(
        #             # id={"id": self.uuid("well-mesh"), "name": well_name},
        #             state=to_mesh_state(min_mesh, field_to_keep="Elevation"),
        #         ),
        #     ],
        # ),
        dash_vtk.GeometryRepresentation(
            colorDataRange=mean_range,
            # id={"id": self.uuid("well-rep"), "name": well_name},
            children=[
                dash_vtk.Mesh(
                    # id={"id": self.uuid("well-mesh"), "name": well_name},
                    state=to_mesh_state(mean_mesh, field_to_keep="Elevation"),
                ),
            ],
        ),
        # dash_vtk.GeometryRepresentation(
        #     colorDataRange=max_range,
        #     # id={"id": self.uuid("well-rep"), "name": well_name},
        #     children=[
        #         dash_vtk.Mesh(
        #             # id={"id": self.uuid("well-mesh"), "name": well_name},
        #             state=to_mesh_state(max_mesh, field_to_keep="Elevation"),
        #         ),
        #     ],
        # ),
        dash_vtk.GeometryRepresentation(
            # colorDataRange=[vol["Elevation"].min(), vol["Elevation"].max()],
            # id={"id": self.uuid("well-rep"), "name": well_name},
            children=[
                dash_vtk.Mesh(
                    # id={"id": self.uuid("well-mesh"), "name": well_name},
                    state=to_mesh_state(vol)  # , field_to_keep="Elevation"),
                ),
            ],
            property={"opacity": 0.3},
        ),
    ],
)

app.run_server(debug=True)
