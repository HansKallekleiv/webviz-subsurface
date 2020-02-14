import functools

import xtgeo

# pylint: disable=no-member
@functools.lru_cache()
def load_grid(gridpath):
    return xtgeo.grid_from_file(gridpath)


# pylint: disable=no-member
@functools.lru_cache()
def load_grid_parameter(grid, gridparameterpath):
    return xtgeo.gridproperty_from_file(gridparameterpath, grid=grid)
