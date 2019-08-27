import os
from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import dash_daq as daq
from dash.dependencies import Input, Output
import dash_daq as daq
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from ..datainput import SurfaceLeafletLayer, FaultPolygonsLeafletLayer, WellPicksLeafletLayer, get_colormap
import webviz_subsurface_components
import timeit
import io
import tempfile
import xtgeo

class Map(WebvizContainer):
    '''### Map 

This container adds functionality for standard visualization of disk usage in
FMU projects. It adds a dashboard element where the user can choose between
showing disk usage, per user, either as a pie chart or as a bar chart.

* `scratch_dir`: Path to the directory you want to show disk usage for, e.g.
  `/scratch/fmu`.
* `title`: Optional title for the container.
'''

    def __init__(self, app):
        self.uid = uuid4()
        self.chart_id = f'chart-id-{self.uid}'
        self.surf_id = f'surf-id-{self.uid}'
        self.real_id = f'real-id-{self.uid}'
        self.chart_id2 = f'chart-id2-{self.uid}'
        self.surf_id2 = f'surf-id2-{self.uid}'
        self.surf_id3 = f'surf-id3-{self.uid}'
        self.real_id2 = f'real-id2-{self.uid}'
        self.average_id = f'average-id-{self.uid}'
        self.ensemblefolder = '/scratch/fmu/hakal/1_r001_reek/realization-'
        self.mapfolder = 'iter-0/share/results/maps'
        self.polygonsfolder = 'iter-0/share/results/polygons'
        self.tablesfolder = 'iter-0/share/results/tables'
        self.horizons = ['topupperreek', 'topmidreek', 'toplowerreek', 'baselowerreek']
        self.folder = '/scratch/fmu/hakal/1_r001_reek/realization-0/iter-0/share/results/maps/'
        self.suffix = '--ds_extracted_horizons.gri'
        self.mapsuffix = '--ds_extracted_horizons.gri'
        self.faultpolysuffix = '--dl_extracted_faultlines.pol'
        
        surface = SurfaceLeafletLayer(self.horizons[0], self.get_map_path("0", self.horizons[0]))
        self.center = surface.center
        self.colormap = get_colormap('viridis')
        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div(style={'padding-top': 20, 'display': 'grid',
                                'grid-template-columns': '1fr 1fr'},children=[
                                html.Div(style={'padding-top': 20, 'display': 'grid',
                                'grid-template-columns': '1fr 3fr'},children=[
            html.Div(children=[
                    dcc.Dropdown(id=self.surf_id,
                         options=[{'label': i, 'value': i}
                                  for i in self.horizons],
                         value=self.horizons[0],
                        multi=False,
                        clearable=False),
                    html.Label('Select realization', style={
                            'font-weight': 'bold'}),

                dcc.Dropdown(id=self.real_id,
                         options=[{'label': i, 'value': i}
                                  for i in ["0","1","2","3","4"]],
                         value="0",
                        multi=False,
                        clearable=False),
                html.Label('Calculate average', style={
                            'font-weight': 'bold'}),
                     daq.ToggleSwitch(id=self.average_id, value=False),
                ]),
                


            webviz_subsurface_components.LayeredMap(
                id=self.chart_id,
                map_bounds=[[]],
                center=self.center,
                layers=[]
            )

        ]),
        html.Div(style={'padding-top': 20, 'display': 'grid',
                                'grid-template-columns': '1fr 3fr'},children=[
            html.Div(children=[
                    html.Label('Calculate difference surface', style={
                            'font-weight': 'bold'}),
                    html.Label('Select top surface', style={
                            'font-weight': 'bold'}),
                    dcc.Dropdown(id=self.surf_id2,
                         options=[{'label': i, 'value': i}
                                  for i in self.horizons],
                         value=self.horizons[0],
                        multi=False,
                        clearable=False),
                        html.Label('Select base surface', style={
                            'font-weight': 'bold'}),
                          dcc.Dropdown(id=self.surf_id3,
                         options=[{'label': i, 'value': i}
                                  for i in self.horizons],
                         value=self.horizons[1],
                        multi=False,
                        clearable=False),
                          html.Label('Select realization', style={
                            'font-weight': 'bold'}),
                dcc.Dropdown(id=self.real_id2,
                         options=[{'label': i, 'value': i}
                                  for i in ["0","1","2","3","4"]],
                         value="0",
                        multi=False,
                        clearable=False)
                ]),
                


            webviz_subsurface_components.LayeredMap(
                id=self.chart_id2,
                map_bounds=[[]],
                center=self.center,
                layers=[]
            )

        ])])


    def get_map_path(self, real, mapname):
        return os.path.join(self.ensemblefolder+str(real), self.mapfolder, mapname + self.mapsuffix)

    def get_polygons_path(self, real, mapname):
        return os.path.join(self.ensemblefolder+str(real), self.polygonsfolder, mapname + self.faultpolysuffix)

    def get_table_path(self, real, tablename):
        return os.path.join(self.ensemblefolder+str(real), self.tablesfolder, tablename)

    def set_callbacks(self, app):
        @app.callback(Output(self.chart_id, 'layers'), 
            [Input(self.surf_id, 'value'), Input(self.real_id, 'value'), Input(self.average_id, 'value')])
        def change_map(mapname, real, average):
            layers = []
            if average:
                s = [self.get_map_path(real, mapname) for real in ["0", "1", "2"]]
                surface = SurfaceLeafletLayer(mapname, s, calc="average")
            else:
                surface = SurfaceLeafletLayer(mapname, self.get_map_path(real, mapname))

            layer = surface.leaflet_layer
            layers.append(layer)
            faultpolygons = FaultPolygonsLeafletLayer(self.get_polygons_path(real, mapname))
            w = WellPicksLeafletLayer(self.get_table_path(0, 'wellpicks.csv'), mapname)
            layers.append(faultpolygons.leaflet_layer)
            layers.append(w.leaflet_layer)
            return layers

        @app.callback(Output(self.chart_id2, 'layers'), 
            [Input(self.surf_id2, 'value'), Input(self.surf_id3, 'value'), Input(self.real_id2, 'value')])
        def change_map2(mapname, mapname2, real):
            layers = []
            s = [self.get_map_path(real, mapname), self.get_map_path(real, mapname2)]
            surface = SurfaceLeafletLayer(f'{mapname2}-{mapname}', s, calc="diff")
            layer = surface.leaflet_layer
            layers.append(layer)
            faultpolygons = FaultPolygonsLeafletLayer(self.get_polygons_path(real, mapname))
            w = WellPicksLeafletLayer(self.get_table_path("0", 'wellpicks.csv'), mapname)
            layers.append(faultpolygons.leaflet_layer)
            layers.append(w.leaflet_layer)
            return layers

            