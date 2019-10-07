import numpy as np
from xtgeo import Surfaces, RegularSurface
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def unrotate_and_transpose_surface(surface):
    s = surface.copy()
    s.unrotate()
    x, y, z = s.get_xyz_values()
    x = np.flip(x.transpose(), axis=0)
    y = np.flip(y.transpose(), axis=0)
    z = np.flip(z.transpose(), axis=0)
    return [x, y, z]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_fence(surface, fence):
    values = surface.get_randomline(fence)
    x_arr = values[:, 0]
    y_arr = values[:, 1]
    y_arr *= -1
    return [[x, y] for x, y in zip(x_arr, y_arr)]


def apply(surfaces, func, *args, **kwargs):
    template = surfaces[0].copy()
    slist = []
    for surf in surfaces:
        status = template.compare_topology(surf, strict=False)
        if not status:
            continue
        slist.append(np.ma.filled(surf.values, fill_value=np.nan))
    xlist = np.array(slist)
    template.values = func(xlist, *args, **kwargs)
    return template.copy()


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_surface(fn):
    surface = RegularSurface(fn).copy()
    values = unrotate_and_transpose_surface(surface)
    bounds = [
        [np.min(values[0]), np.min(values[1])],
        [np.max(values[0]), np.max(values[1])],
    ]
    center = [np.mean(values[0]), np.mean(values[1])]
    return values, bounds, center

@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_surface_statistics(fns):
    surfaces = Surfaces(fns).surfaces
    template = unrotate_and_transpose_surface(surfaces[0])
    bounds = [
        [np.min(template[0]), np.min(template[1])],
        [np.max(template[0]), np.max(template[1])],
    ]
    center = [np.mean(template[0]), np.mean(template[1])]
    return {
        "mean": unrotate_and_transpose_surface(apply(surfaces, np.mean, axis=0)),
        "max": unrotate_and_transpose_surface(apply(surfaces, np.max, axis=0)),
        "min": unrotate_and_transpose_surface(apply(surfaces, np.min, axis=0)),
        "stddev": unrotate_and_transpose_surface(apply(surfaces, np.std, axis=0)),
    }, bounds, center


def slice_surfaces(fns, fence):
    surfaces = Surfaces(fns).surfaces
    return {
        "mean": get_surface_fence(apply(surfaces, np.mean, axis=0), fence),
        "max": get_surface_fence(apply(surfaces, np.max, axis=0), fence),
        "min": get_surface_fence(apply(surfaces, np.min, axis=0), fence),
        # "stddev": slice_surface(apply(surfaces, np.std, axis=0), fence),
    }
def slice_surface(fn, fence):
    try:
        return get_surface_fence(RegularSurface(fn), fence)
    except IOError:
        return None