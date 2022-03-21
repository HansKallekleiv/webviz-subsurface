import glob
import pyvista as pv

mb = pv.MultiBlock()
for fn in glob.glob("vtk/horizons/*.vtk"):
    surf = pv.read(fn)
    surf = surf.scale([1, 1, -3])
    surf = surf.decimate(0.5)
    surf = surf.elevation()
    mb.append(surf)
    print(surf)
    break
    # a = mb.extract_geometry()
    # a.plot()
for fn in glob.glob("vtk/faults/*.vtk"):
    surf = pv.read(fn)
    surf = surf.scale([1, 1, -3])
    # surf = surf.elevation()
    mb.append(surf)
mb.plot()
