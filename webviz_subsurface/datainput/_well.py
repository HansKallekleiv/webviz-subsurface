from xtgeo import Well



def get_well_fence(fn):
    return Well(fn).get_fence_polyline(nextend=0, sampling=5, tvdmin= 1500, asnumpy=False).get_fence()