from typing import List
import numpy as np
import xtgeo
from vtk.util.numpy_support import vtk_to_numpy
import pyvista as pv

from PVGeo import points_to_poly_data
from PVGeo.filters import AddCellConnToPoints, RotatePoints


def lines_from_points(points):
    """Given an array of points, make a line set"""
    poly = pv.PolyData()
    poly.points = points
    cells = np.full((len(points) - 1, 3), 2, dtype=np.int_)
    cells[:, 1] = np.arange(0, len(points) - 1, dtype=np.int_)
    cells[:, 2] = np.arange(1, len(points), dtype=np.int_)
    poly.lines = cells
    return poly


def polyline_from_points(points):
    poly = pv.PolyData()
    poly.points = points
    the_cell = np.arange(0, len(points), dtype=np.int_)
    the_cell = np.insert(the_cell, 0, len(points))
    poly.lines = the_cell
    return poly


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


def well_to_polydata_input(well: xtgeo.Well) -> pv.PolyData:
    well.dataframe["Z_TVDSS"] = well.dataframe["Z_TVDSS"] * -1
    xyz_arr = well.dataframe[["X_UTME", "Y_UTMN", "Z_TVDSS"]].values[3:]
    line = polyline_from_points(xyz_arr)
    line["scalars"] = np.arange(line.n_points)
    tube = line.tube(radius=5)

    return tube
    # polydata = points_to_poly_data(xyz_arr)
    # polys = vtk_to_numpy(polydata.GetPolys().GetData())
    # points = polydata.points.ravel()
    # lines = AddCellConnToPoints().apply(polydata)
    # print(lines)
    # return {"points": points, "polys": polys, "lines": lines}


def surface_to_structured_grid(surface: xtgeo.RegularSurface) -> pv.StructuredGrid:

    xi, yi = surface.get_xy_values(asmasked=False)
    zi = surface.values
    zif = np.ma.filled(zi, fill_value=np.nan)
    sgrid = pv.StructuredGrid(xi, yi, zif)
    # sgrid.flip_z(inplace=True)
    sgrid["Elevation"] = zif.flatten(order="F")

    return sgrid
