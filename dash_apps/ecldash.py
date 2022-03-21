from enum import Enum
from pathlib import Path

import numpy as np
import xtgeo
import pyvista as pv
from ecl.grid.ecl_grid import EclGrid

import dash
import dash_vtk
from dash_vtk.utils import to_mesh_state


def pldist(point, start, end):
    """
    Calculates the distance from ``point`` to the line given
    by the points ``start`` and ``end``.
    :param point: a point
    :type point: numpy array
    :param start: a point of the line
    :type start: numpy array
    :param end: another point of the line
    :type end: numpy array
    """
    if np.all(np.equal(start, end)):
        return np.linalg.norm(point - start)

    return np.divide(
        np.abs(np.linalg.norm(np.cross(end - start, start - point))),
        np.linalg.norm(end - start),
    )


def rdp_rec(M, epsilon, dist=pldist):
    """
    Simplifies a given array of points.
    Recursive version.
    :param M: an array
    :type M: numpy array
    :param epsilon: epsilon in the rdp algorithm
    :type epsilon: float
    :param dist: distance function
    :type dist: function with signature ``f(point, start, end)`` -- see :func:`rdp.pldist`
    """
    dmax = 0.0
    index = -1

    for i in range(1, M.shape[0]):
        d = dist(M[i], M[0], M[-1])

        if d > dmax:
            index = i
            dmax = d

    if dmax > epsilon:
        r1 = rdp_rec(M[: index + 1], epsilon, dist)
        r2 = rdp_rec(M[index:], epsilon, dist)

        return np.vstack((r1[:-1], r2))
    else:
        return np.vstack((M[0], M[-1]))


def polyline_from_points(points):
    poly = pv.PolyData()
    poly.points = points
    the_cell = np.arange(0, len(points), dtype=np.int_)
    the_cell = np.insert(the_cell, 0, len(points))
    poly.lines = the_cell
    return poly


def well_to_polydata_input(well: xtgeo.Well) -> pv.PolyData:
    well.dataframe["Z_TVDSS"] = well.dataframe["Z_TVDSS"] * -1
    well.dataframe = well.dataframe.fillna(0)
    coordinates = ["X_UTME", "Y_UTMN", "Z_TVDSS"]
    xyz_arr = well.dataframe[coordinates].values
    # xyz_arr = rdp_rec(xyz_arr, 1.0)

    polydata = polyline_from_points(xyz_arr)
    for log in well.dataframe.drop(columns=coordinates):
        polydata[log] = well.dataframe[log]

    return polydata


# def ecl_to_esgrid(grid_path: Path) -> pv.ExplicitStructuredGrid:
#     eclgrid = EclGrid(grid_path)

#     class YDirection(Enum):
#         LOW = 0
#         HIGH = 2

#     class ZDirection(Enum):
#         LOW = 0
#         HIGH = 4

#     min_k = 2  # minimum value would be 0
#     max_k = 2  # maximum value would be eclgrid.nz

#     # VTK structured grid assumes certain cycle order of corner points:
#     corners = []
#     for k in range(min_k, max_k + 1):
#         for zdirection in ZDirection:
#             for j in range(eclgrid.ny):
#                 for ydirection in YDirection:
#                     for i in range(eclgrid.nx):
#                         offset = ydirection.value + zdirection.value
#                         corners += eclgrid.cell(i=i, j=j, k=k).corners[
#                             offset : offset + 2
#                         ]

#     dims = np.array([eclgrid.nx, eclgrid.ny, max_k + 1 - min_k]) + 1
#     grid = pv.ExplicitStructuredGrid(dims, corners)
#     grid = grid.compute_connectivity()
#     return grid


# esgrid = ecl_to_esgrid("./DROGON-0.EGRID")

# Convert to Unstructured grid
# ugrid = esgrid.cast_to_unstructured_grid()


ugrid = pv.read("eclipse.vtu")
# Flip z-direction for subsurface
# ugrid.flip_z(inplace=True)
grid = pv.read("eclipse.vtu")
line = np.array(
    [
        [457627.68345539965, 5935207.235094619, 0],
        [462607.1405579978, 5933140.507733894, 0],
    ]
)

well = xtgeo.well_from_file("55_33-1.rmswell")
well.dataframe = well.dataframe.loc[well.dataframe["Z_TVDSS"] > 1500]
well.dataframe["Z_TVDSS"] = well.dataframe["Z_TVDSS"] * -1

# well.downsample(1000)
# well.downsample(2000)
well_line = well_to_polydata_input(well)
tube = well_line.tube(radius=10)
tube.scale([1, 1, 5], inplace=True)

spline = pv.Spline(line)


# try:
#     intersect = ugrid.slice_along_line(well_line)
# except TypeError:

extend_minus_x = [well_line.points[0][0] - 1000, well_line.points[0][1] - 1000, 0]
extend_plus_x = [well_line.points[0][0] + 1000, well_line.points[0][1] + 1000, 4000]
points = np.array(
    [extend_minus_x, well_line.points[0], well_line.points[1], extend_plus_x]
)
# print(points[:, 1])
xmin = points[:, 0].min()
xmax = points[:, 0].max()
ymin = points[:, 1].min()
ymax = points[:, 1].max()
bounds = [xmin, xmax, ymin, ymax, 0, 4000]
extended_line = pv.Spline(points, n_points=100)
print("spline", extended_line)
print(bounds)
ugrid.clear_data()
# ug = ugrid.select_enclosed_points(extended_line)
intersect = ugrid.clip_box(bounds, invert=False)
print("clipped box", intersect)
print(intersect.array_names)
intersect = intersect.slice_along_line(extended_line)
print("Intersection", intersect)
# print(extended_line)
# intersect = intersect.select_enclosed_points(extended_line)
# print(ug["SelectedPoints"].max())
# intersect2 = intersect.clip_box(bounds, invert=False)
# print(intersect2)

# print("inverted", intersect3)
# print(intersect.extract_subset(bounds))
intersect.scale([1, 1, 5], inplace=True)
pll = pv.Plotter()
# pl.enable_parallel_projection()
pll.add_mesh(intersect)
pll.add_mesh(tube)

pll.camera.position = (474560.9094285129, 5946790.293485353, 30526.59055966513)
# Extract mesh without any property
# mesh = to_mesh_state(ugrid)

# Alternatively have some property:
intersect["poro"] = np.random.rand(*intersect.points.shape)
mesh = to_mesh_state(intersect, field_to_keep="poro")

app = dash.Dash()

app.layout = dash_vtk.View(
    style={"height": "90vh"},
    cameraViewUp=(0, 0, -1),
    cameraParallelProjection=True,
    cameraPosition=pll.camera.position,
    interactorSettings=[
        {
            "button": 1,
            "action": "Pan",
        },
        {
            "button": 2,
            "action": "Pan",
        },
        {
            "button": 3,
            "action": "Zoom",
            "scrollEnabled": True,
        },
        {
            "button": 1,
            "action": "Pan",
            "shift": True,
        },
        {
            "button": 1,
            "action": "Zoom",
            "alt": True,
        },
    ],
    children=[
        dash_vtk.GeometryRepresentation(
            # id={"id": self.uuid("well-rep"), "name": well_name},
            property={
                "show_edges": False,
                "opacity": 1,
                "color": (0, 0, 0),
                "lineWidth": 10,
                "pointSize": 10,
            },
            # colorDataRange=[well.dataframe["PHIT"].min(), well.dataframe["PHIT"].max()],
            children=[
                dash_vtk.Mesh(
                    # id={"id": self.uuid("well-mesh"), "name": well_name},
                    state=to_mesh_state(
                        extended_line,
                        # field_to_keep="PHIT",
                    ),
                ),
            ],
        ),
        dash_vtk.GeometryRepresentation(
            # id={"id": self.uuid("well-rep"), "name": well_name},
            property={
                "show_edges": False,
                "opacity": 0.2,
                "color": (0, 0, 0),
                "lineWidth": 10,
                "pointSize": 10,
            },
            colorDataRange=[well.dataframe["PHIT"].min(), well.dataframe["PHIT"].max()],
            children=[
                dash_vtk.Mesh(
                    # id={"id": self.uuid("well-mesh"), "name": well_name},
                    state=to_mesh_state(
                        tube,
                        field_to_keep="PHIT",
                    ),
                ),
            ],
        ),
        dash_vtk.GeometryRepresentation(
            children=[dash_vtk.Mesh(state=mesh)],
            colorMapPreset="erdc_rainbow_bright",
            # showCubeAxes=True,
            property={
                "lighting": False,
                "opacity": 0.5,
            },
        ),
    ],
)

app.run_server(debug=True)
