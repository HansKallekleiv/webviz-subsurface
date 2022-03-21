from functools import wraps

import numpy as np
import xtgeo
import pyvista

from ._utils import rdp_rec


class Well(pyvista.PolyData):
    def __init__(self, well: xtgeo.Well):
        super().__init__()
        dframe = well.dataframe.fillna(0)
        coordinates = ["X_UTME", "Y_UTMN", "Z_TVDSS"]
        xyz_arr = dframe[coordinates].values

        the_cell = np.arange(0, len(xyz_arr), dtype=np.int_)
        the_cell = np.insert(the_cell, 0, len(xyz_arr))

        self.lines = the_cell
        self.points = xyz_arr

        for log in dframe.drop(columns=coordinates):
            self[log] = dframe[log]

    def intersect_grid(
        self,
        grid: pyvista.UnstructuredGrid,
        extension_x: float = 1000,
        extension_y: float = 1000,
        zmin: float = -9999,
        zmax: float = 9999,
    ) -> pyvista.PolyData:
        xyz_arr = rdp_rec(self.points, 1.0)
        xyz_arr[0][0] = xyz_arr[0][0] - extension_x
        xyz_arr[-1][0] = xyz_arr[-1][0] + extension_x
        xyz_arr[0][1] = xyz_arr[0][1] - extension_y
        xyz_arr[-1][1] = xyz_arr[-1][1] + extension_y
        xyz_arr[0][2] = zmin
        xyz_arr[-1][2] = zmax

        spline = pyvista.Spline(xyz_arr)
        clipped_grid = grid.clip_box(spline.bounds, invert=False)
        return clipped_grid.slice_along_line(spline)
