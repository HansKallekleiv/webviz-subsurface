import timeit
import io
import json
import base64
from PIL import Image
import numpy as np
import pandas as pd
from matplotlib import cm
import xtgeo
from webviz_config.common_cache import cache

# @cache.memoize(timeout=cache.TIMEOUT)
def array_to_png(Z, shift=True, colormap=False):
    '''The layered map dash component takes in pictures as base64 data
    (or as a link to an existing hosted image). I.e. for containers wanting
    to create pictures on-the-fly from numpy arrays, they have to be converted
    to base64. This is an example function of how that can be done.

    1) Scale the input array (Z) to the range 0-255.
    2) If shift=True and colormap=False, the 0 value in the scaled range
       is reserved for np.nan (while the actual data points utilize the
       range 1-255.

       If shift=True and colormap=True, the 0 value in the colormap range
       has alpha value equal to 0.0 (i.e. full transparency). This makes it
       possible for np.nan values in the actual map becoming transparent in
       the image.
    3) If the array is two-dimensional, the picture is stored as greyscale.
       Otherwise it is either stored as RGB or RGBA (depending on if the size
       of the third dimension is three or four, respectively).
    '''
    start = timeit.timeit()
    Z -= np.nanmin(Z)

    if shift:
        Z *= 254.0/np.nanmax(Z)
        Z += 1.0
    else:
        Z *= 255.0/np.nanmax(Z)

    Z[np.isnan(Z)] = 0

    if colormap:
        if Z.shape[0] != 1:
            raise ValueError('The first dimension of a '
                             'colormap array should be 1')
        if Z.shape[1] != 256:
            raise ValueError('The second dimension of a '
                             'colormap array should be 256')
        if Z.shape[2] not in [3, 4]:
            raise ValueError('The third dimension of a colormap '
                             'array should be either 3 or 4')
        if shift:
            if Z.shape[2] != 4:
                raise ValueError('Can not shift a colormap which '
                                 'is not utilizing alpha channel')
            else:
                Z[0][0][3] = 0.0  # Make first color channel transparent

    if Z.ndim == 2:
        image = Image.fromarray(np.uint8(Z), 'L')
    elif Z.ndim == 3:
        if Z.shape[2] == 3:
            image = Image.fromarray(np.uint8(Z), 'RGB')
        elif Z.shape[2] == 4:
            image = Image.fromarray(np.uint8(Z), 'RGBA')
        else:
            raise ValueError('Third dimension of array must '
                             'have length 3 (RGB) or 4 (RGBA)')
    else:
        raise ValueError('Incorrect number of dimensions in array')

    byte_io = io.BytesIO()
    image.save(byte_io, format='png')
    byte_io.seek(0)

    base64_data = base64.b64encode(byte_io.read()).decode('ascii')
    # print(base64_data)
    end = timeit.timeit()
    t = end - start
    print(f'Generate png {t}ms')
    return f'data:image/png;base64,{base64_data}'

# @cache.memoize(timeout=cache.TIMEOUT)
def get_colormap(colormap):
    return array_to_png(cm.get_cmap(colormap, 256)
                            ([np.linspace(0, 1, 256)]), colormap=True)


# @cache.memoize(timeout=cache.TIMEOUT)
class SurfaceLeafletLayer():

    def __init__(self, name, fn, calc=None):
        self.name = name
        self.arr = self.get_surface_array(fn, calc)
        self.colormap = self.set_colormap('viridis')

    def get_surface_array(self, fn, calc=None):
        print(fn)
        if isinstance(fn, list):
            slist = []
            for el in fn:
                s = xtgeo.surface.RegularSurface(el, fformat='irap_binary')
                slist.append(s.values)
                nparr = np.array(slist)
            if calc == 'average':
                npavg = np.average((nparr), axis=0)
                s.values = npavg
            if calc == 'diff':
                # nparr = 
                npdiff = np.subtract(np.array(slist)[1], np.array(slist)[0])
                s.values = npdiff
        else:
            s = xtgeo.surface.RegularSurface(fn, fformat='irap_binary')
        s.unrotate()
        xi, yi, zi = s.get_xyz_values()
        xi = np.flip(xi.transpose(), axis=0)
        yi = np.flip(yi.transpose(), axis=0)
        zi = np.flip(zi.transpose(), axis=0)
        return [xi, yi, zi]

    def set_colormap(self, colormap):
        return get_colormap(colormap)

    @property
    def bounds(self):
        return [[np.min(self.arr[0]), np.min(self.arr[1])],
                [np.max(self.arr[0]), np.max(self.arr[1])]]

    @property
    def center(self):
        return [np.mean(self.arr[0]), np.mean(self.arr[1])]
    
    @property
    def z_arr(self):
        return self.arr[2].filled(np.nan)

    @property
    def as_png(self):
        return array_to_png(self.z_arr)

    @property
    def leaflet_layer(self):
        return {'name': self.name,
                'checked': True,
                'base_layer': True,
                'data':[{'type': 'image',
                         'url': self.as_png,
                         'colormap': self.colormap,
                         'bounds': self.bounds,
                        }]
                }

class WellPicksLeafletLayer():

    def __init__(self, fn, surface, color='black', radius=3):

        self.data = self.read_wellpicks(fn, surface)
        self.color = color
    def read_wellpicks(self, fn, surface):
        df = pd.read_csv(fn)
        df = df[df['HorizonName'].str.lower() == surface]
        return df[['East', 'North', 'WellName', 'TVD_MSL']].values

    @property
    def leaflet_layer(self):
        return {
                 'name': 'Well picks',
                 'base_layer': False,
                 'checked': False,
                 'data': [{
                    'type': 'circle',
                    'center': [pick[0], pick[1]], 
                    'color': self.color,
                    'fillColor': self.color,
                    'radius': 8,
                    'tooltip': f'{pick[2]}, TVD_MSL: {pick[3]:.2f}'
                   }for pick in self.data
                ]}

class FaultPolygonsLeafletLayer():
    def __init__(self,  fn, color='black'):
        self.data = self.xyz_to_layer(fn, color)
    def xyz_to_layer(self, fn, color):

        Lsub = []
        L2 = []
        with open(fn, 'r') as f:
            for line in f.readlines():
                e = line.split()
                if e[0].startswith('999'):
                    print('new')
                    L2.append({
                        'type': 'polyline', 
                        'positions': ([[e[0], e[1]] for e in Lsub]),
                        'color': color,
                        'tooltip': 'fault'})
                    Lsub = []
                else:
                    Lsub.append(e)
        return L2

    @property
    def leaflet_layer(self):
        return {
            'name': 'Fault polygons',
            'checked': False,
            'base_layer': False,
            'data': self.data
        }
# @cache.memoize(timeout=cache.TIMEOUT)
class SeismicLeafletLayer():

    def __init__(self, name, well_name, cube_name):
        self.name = name
        hmin, hmax, vmin, vmax, values = self.get_cfence(well_name, cube_name)
        self.bounds = [[-2000, 2000], [1500, 1800]]
        self.center = [0, 1650]
        self.z_arr = values
        self.colormap = self.set_colormap('RdBu')

    def get_cfence(self, well, cube_name):
        cube = xtgeo.cube.Cube(cube_name)
        return cube.get_randomline(self.get_wfence(well).values.copy())

    def get_wfence(self, well_name, nextend=200, tvdmin=0) -> pd.DataFrame:
        '''Generate 2D array along well path'''
        df = self.well_to_df(well_name)
        keep = ("X_UTME", "Y_UTMN", "Z_TVDSS")
        for col in df.columns:
            if col not in keep:
                df.drop(labels=col, axis=1, inplace=True)
        df["POLY_ID"] = 1
        df["NAME"] = well_name
        poly = xtgeo.Polygons()
        poly.dataframe = df
        poly.name = well_name

        if tvdmin is not None:
            poly.dataframe = poly.dataframe[poly.dataframe[poly.zname] >= tvdmin]
        data = poly.get_fence(nextend=nextend, asnumpy=True)
        df = pd.DataFrame(data)
        df.columns = df.columns.astype(str)
        return df

    def well_to_df(self, well_name) -> pd.DataFrame:
        return xtgeo.well.Well(well_name).dataframe

    def set_colormap(self, colormap):
        return get_colormap(colormap)

    @property
    def as_png(self):
        return array_to_png(self.z_arr)

    @property
    def leaflet_layer(self):
        return {'name': self.name,
                'checked': True,
                'base_layer': True,
                'hill_shading': False,
                'data':[{'type': 'image',
                         'url': self.as_png,
                         'colormap': self.colormap,
                         'bounds': self.bounds,
                         # 'hill_shading': hillshade
                        }]
                }

                
