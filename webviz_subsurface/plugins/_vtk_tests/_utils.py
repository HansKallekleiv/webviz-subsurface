import numpy as np
import pandas as pd
import pyvista as pv

# Functions copied  from https://github.com/OpenGeoVis/PVGeo
def points_to_poly_data(points, copy_z=False):
    """
    Create ``vtkPolyData`` from a numpy array of XYZ points. If the points
    have more than 3 dimensions, then all dimensions after the third will be
    added as attributes. Assume the first three dimensions are the XYZ
    coordinates.
    Args:
        points (np.ndarray or pandas.DataFrame): The points and pointdata
        copy_z (bool): A flag on whether to append the z values as a PointData
            array
    Return:
        vtkPolyData : points with point-vertex cells
    """
    # This prevents an error that occurs when only one point is passed
    if points.ndim < 2:
        points = points.reshape((1, -1))
    keys = ["Field %d" % i for i in range(points.shape[1] - 3)]
    # Check if input is anything other than a NumPy array and cast it
    # e.g. you could send a Pandas dataframe
    if not isinstance(points, np.ndarray):
        if isinstance(points, pd.DataFrame):
            # If a pandas data frame, lets grab the keys
            keys = points.keys()[3::]
        points = np.array(points)
    # If points are not 3D
    if points.shape[1] < 2:
        raise RuntimeError("Points must be 3D. Try adding a third dimension of zeros.")

    atts = points[:, 3::]
    points = points[:, 0:3].astype(float)

    # Create polydata
    pdata = pv.PolyData(points)

    # Add attributes if given
    scalSet = False
    for i, key in enumerate(keys):
        data = convert_array(atts[:, i], name=key)
        pdata.GetPointData().AddArray(data)
        if not scalSet:
            pdata.GetPointData().SetActiveScalars(key)
            scalSet = True
    if copy_z:
        z = convert_array(points[:, 2], name="Elevation")
        pdata.GetPointData().AddArray(z)
    return pv.wrap(pdata)


def convert_array(arr, name="Data", deep=0, array_type=None, pdf=False):
    """A helper to convert a NumPy array to a vtkDataArray or vice versa
    Args:
        arr (ndarray or vtkDataArry) : A numpy array or vtkDataArry to convert
        name (str): the name of the data array for VTK
        deep (bool, int): if input is numpy array then deep copy values
        pdf (bool): if input is vtkDataArry, make a pandas DataFrame of the array
    Return:
        vtkDataArray, ndarray, or DataFrame:
            the converted array (if input is a NumPy ndaray then returns
            ``vtkDataArray`` or is input is ``vtkDataArray`` then returns NumPy
            ``ndarray``). If pdf==True and the input is ``vtkDataArry``,
            return a pandas DataFrame.
    """
    num_data = pv.convert_array(arr, name=name, deep=deep, array_type=array_type)
    if not isinstance(num_data, np.ndarray):
        return num_data
    if not pdf:
        return num_data
    return pd.DataFrame(data=num_data, columns=[arr.GetName()])
