from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
import base64
from pathlib import Path
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
import glob
from plotly.subplots import make_subplots
import plotly.graph_objects as go

def make_figure():
    # Create figure
    fig = make_subplots(vertical_spacing=0, rows=2, cols=1)
    # Constants
    img_width = 1600
    img_height = 900
    scale_factor = 0.5
    fig.add_trace(
        go.Scatter(
            x=[0, img_width * scale_factor],
            y=[0, img_height * scale_factor],
            mode="markers",
            marker_opacity=0,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[0, img_width * scale_factor],
            y=[0, img_height * scale_factor],
            mode="markers",
            marker_opacity=0,
        ),
        row=2,
        col=1,
    )





    # Configure axes
    fig.update_xaxes(visible=False, range=[0, img_width * scale_factor])

    fig.update_yaxes(
        visible=False,
        range=[0, img_height * scale_factor],
        # the scaleanchor attribute ensures that the aspect ratio stays constant
        scaleanchor="x",
    )
    fig["layout"]["yaxis"]["matches"] = "y2"
    fig["layout"]["yaxis2"]["matches"] = "y"
    fig["layout"]["xaxis"]["matches"] = "x2"
    fig["layout"]["xaxis2"]["matches"] = "x"
    # fig["layout"]["yaxis2"]["scaleanchor"] = "x2"

    print(fig)
    # Configure other layout
    fig.update_layout(
        width=img_width * scale_factor,
        height=img_height*2 * scale_factor,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
    )
    # Disable the autosize on double click because it adds unwanted margins around the image
    # More detail: https://plotly.com/python/configuration-options/
    # fig.show(config={'doubleClick': 'reset'})
    return fig
# pylint: disable=too-many-instance-attributes
class ImageCrossSection(WebvizPluginABC):
    """### ImageCrossSection
Well cross-section displaying statistical surfaces fro
"""

    def __init__(
        self, app, folder: Path = "/scratch/val_kvb/tnatt/plots/surf_ds_final_gf"
    ):

        super().__init__()
        self.folder = folder
        self.files = Path(folder).glob("*.png")
        # print([str(f) for f in self.files])
        self.set_callbacks(app)

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
                html.Div(
                    style={"flex": 1},
                    children=[
                        wcc.Select(
                            id=self.uuid("well"),
                            # value=self.files[0],
                            multi=False,
                            size=30,
                            persistence=True,
                            options=[
                                {"label": f.stem, "value": f.stem} for f in sorted(self.files)
                            ],
                        )
                    ],
                ),
                html.Div(
                    style={"flex": 3},
                    children=[
                        wcc.Graph(id=self.uuid("fig"), figure=make_figure()),
                    ],
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("fig"), "figure"),
            [Input(self.uuid("well"), "value")],
            [State(self.uuid("fig"), "figure")],
        )
        def update_img(img, figure):
            # print(img)
            # print(figure)
            img = img[0]
            image = image_to_base64(
                "/scratch/val_kvb/tnatt/plots/surf_ds_final_gf/" + img + ".png"
            )
            image2 = image_to_base64(
                "/scratch/val_kvb/tnatt/plots/surf_from_grid/" + img + ".png"
            )
            iimg = [
                {
                    "layer": "below",
                    "opacity": 1.0,
                    "sizex": 800.0,
                    "sizey": 450.0,
                    "sizing": "stretch",
                    "source": image,
                    "x": 0,
                    "xref": "x",
                    "y": 450.0,
                    "yref": "y",
                    "row":1, "col":1
                },
                {
                    "layer": "below",
                    "opacity": 1.0,
                    "sizex": 800.0,
                    "sizey": 450.0,
                    "sizing": "stretch",
                    "source": image2,
                    "x": 0,
                    "xref": "x",
                    "y": 450.0,
                    "yref": "y2",
                    "row":2, "col":1
                }
            ]
            figure["layout"]["images"] = iimg

            return figure


def image_to_base64(fn):
    print(fn)
    with open(fn, "rb") as img_file:
        return f"data:image/png;base64, {base64.b64encode(img_file.read()).decode('ascii')}"
