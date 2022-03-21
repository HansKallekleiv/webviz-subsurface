from typing import List
import numpy as np
import xtgeo
import pyvista as pv

from ._utils import polyline_from_points, rdp_rec


def cube_to_uniform_grid(seismic: xtgeo.Cube) -> pv.StructuredGrid:
    grid = pv.UniformGrid()
    grid.dimensions = seismic.dimensions
    origin = (
        seismic.xori,
        seismic.yori,
        (seismic.zori + (seismic.dimensions[2] * +seismic.zinc)) * -1,
    )
    grid.origin = (
        seismic.xori,
        seismic.yori,
        (seismic.zori + (seismic.dimensions[2] * +seismic.zinc)) * -1,
    )
    grid.spacing = (seismic.xinc, seismic.yinc, seismic.zinc)

    grid.point_data["values"] = seismic.values.flatten(order="F")
    grid.set_active_scalars("values")
    grid = grid.flip_y(point=origin, transform_all_input_vectors=True)
    grid = grid.rotate_z(seismic.rotation, point=origin)

    # pts = grid.points
    # grid.points = np.flip(values.transpose(), axis=0)

    # origin = [seismic.xori, seismic.yori]
    # theta = np.deg2rad(seismic.rotation)

    # xarr, yarr = pts[:, 0], pts[:, 1]
    # ox, oy = origin[0], origin[1]
    # qx = ox + np.cos(theta) * (xarr - ox) - np.sin(theta) * (yarr - oy)
    # qy = oy + np.sin(theta) * (xarr - ox) + np.cos(theta) * (yarr - oy)

    # grid.points[:, 0:2] = np.vstack((qx, qy)).T

    return grid


def well_to_polydata_input(dframe) -> pv.PolyData:
    # dframe["Z_TVDSS"] = dframe["Z_TVDSS"] * -1
    dframe = dframe.fillna(0)
    coordinates = ["X_UTME", "Y_UTMN", "Z_TVDSS"]
    xyz_arr = dframe[coordinates].values
    polydata = polyline_from_points(xyz_arr)
    for log in dframe.drop(columns=coordinates):
        polydata[log] = dframe[log]

    return polydata


def well_to_polydata_fence(dframe) -> pv.PolyData:

    # dframe["Z_TVDSS"] = dframe["Z_TVDSS"] * -1
    dframe = dframe.fillna(0)
    coordinates = ["X_UTME", "Y_UTMN", "Z_TVDSS"]
    xyz_arr = dframe[coordinates].values
    xyz_arr = rdp_rec(xyz_arr, 1.0)
    polydata = polyline_from_points(xyz_arr)
    return polydata


def surface_to_structured_grid(surface: xtgeo.RegularSurface) -> pv.StructuredGrid:

    xi, yi = surface.get_xy_values(asmasked=False)
    zi = surface.values
    zif = np.ma.filled(zi, fill_value=np.nan)
    sgrid = pv.StructuredGrid(xi, yi, zif)
    # sgrid.flip_z(inplace=True)
    sgrid["Elevation"] = zif.flatten(order="F")

    return sgrid
