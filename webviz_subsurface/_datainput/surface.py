import numpy as np
from xtgeo import RegularSurface, Surfaces
from webviz_config.common_cache import CACHE

from .image_processing import array_to_png, get_colormap


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_surface(surface_path):
    return RegularSurface(surface_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_arr(surface, unrotate=True, flip=True):
    if unrotate:
        surface.unrotate()
    x, y, z = surface.get_xyz_values()
    if flip:
        x = np.flip(x.transpose(), axis=0)
        y = np.flip(y.transpose(), axis=0)
        z = np.flip(z.transpose(), axis=0)
    return [x, y, z]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_fence(fence, surface):
    return surface.get_fence(fence)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_surface_layer(
    surface,
    name="surface",
    min_val=None,
    max_val=None,
    color="viridis",
    hillshading=False,
    unit="",
):
    """Make LayeredMap surface image base layer"""
    arr = get_surface_arr(surface)
    bounds = [[np.min(arr[0]), np.min(arr[1])], [np.max(arr[0]), np.max(arr[1])]]
    min_val = min_val if min_val else np.min(arr[2])
    max_val = max_val if max_val else np.max(arr[2])
    return {
        "name": name,
        "checked": True,
        "base_layer": True,
        "data": [
            {
                "type": "image",
                "url": array_to_png(arr[2].copy()),
                "colormap": get_colormap(color),
                "bounds": bounds,
                "allowHillshading": hillshading,
                "minvalue": f"{min_val:.2f}" if min_val else None,
                "maxvalue": f"{max_val:.2f}" if max_val else None,
                "unit": unit,
            }
        ],
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def unrotate_and_transpose_surface(surface, fns):
    surface.unrotate()
    x, y, z = surface.get_xyz_values()
    x = np.flip(x.transpose(), axis=0)
    y = np.flip(y.transpose(), axis=0)
    z = np.flip(z.transpose(), axis=0)
    return [x, y, z]

def _zvalue_from_index(arr, ind):
    """private helper function to work around the limitation of np.choose() by employing np.take()
    arr has to be a 3D array
    ind has to be a 2D array containing values for z-indicies to take from arr
    See: http://stackoverflow.com/a/32091712/4169585
    This is faster and more memory efficient than using the ogrid based solution with fancy indexing.
    """
    # get number of columns and rows
    _,nC,nR = arr.shape

    # get linear indices and extract elements with np.take()
    idx = nC*nR*ind + np.arange(nC*nR).reshape((nC,nR))
    return np.take(arr, idx)

def nan_percentile(arr, q):
    # valid (non NaN) observations along the first axis
    valid_obs = np.sum(np.isfinite(arr), axis=0)
    # replace NaN with maximum
    # max_val = np.nanmin(arr)
    # arr[np.isnan(arr)] = max_val
    # sort - former NaNs will move to the end
    arr = np.sort(arr, axis=0)

    # loop over requested quantiles
    if type(q) is list:
        qs = []
        qs.extend(q)
    else:
        qs = [q]
    if len(qs) < 2:
        quant_arr = np.zeros(shape=(arr.shape[1], arr.shape[2]))
    else:
        quant_arr = np.zeros(shape=(len(qs), arr.shape[1], arr.shape[2]))

    result = []
    for i in range(len(qs)):
        quant = qs[i]
        # desired position as well as floor and ceiling of it
        k_arr = (valid_obs - 1) * (quant / 100.0)
        f_arr = np.floor(k_arr).astype(np.int32)
        c_arr = np.ceil(k_arr).astype(np.int32)
        fc_equal_k_mask = f_arr == c_arr

        # linear interpolation (like numpy percentile) takes the fractional part of desired position
        floor_val = _zvalue_from_index(arr=arr, ind=f_arr) * (c_arr - k_arr)
        ceil_val = _zvalue_from_index(arr=arr, ind=c_arr) * (k_arr - f_arr)

        quant_arr = floor_val + ceil_val
        quant_arr[fc_equal_k_mask] = _zvalue_from_index(arr=arr, ind=k_arr.astype(np.int32))[fc_equal_k_mask]  # if floor == ceiling take floor value

        result.append(quant_arr)

    return result

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
def calculate_surface_statistics(fns):
    surfaces = Surfaces(fns).surfaces
    return {
        "template": unrotate_and_transpose_surface(surfaces[0], fns),
        "mean": unrotate_and_transpose_surface(apply(surfaces, np.mean, axis=0), fns),
        "max": unrotate_and_transpose_surface(apply(surfaces, np.max, axis=0), fns),
        "min": unrotate_and_transpose_surface(apply(surfaces, np.min, axis=0), fns),
        "stddev": unrotate_and_transpose_surface(apply(surfaces, np.std, axis=0), fns),
        "p10": unrotate_and_transpose_surface(apply(surfaces, nan_percentile, 10), fns),
        "p90": unrotate_and_transpose_surface(apply(surfaces, nan_percentile, 90), fns),
    }
