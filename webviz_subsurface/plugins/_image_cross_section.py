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
                            id="wells",
                            # value=self.files[0],
                            multi=False,
                            size=50,
                            options=[
                                {"label": f.stem, "value": f.stem} for f in self.files
                            ],
                        )
                    ],
                ),
                html.Div(
                    style={"flex": 3},
                    children=[html.Img(style={"maxWidth":"100%"}, id="image")],
                ),
                html.Div(
                    style={"flex": 3},
                    children=[html.Img(style={"maxWidth":"100%"}, id="image2")],
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            [Output("image", "src"), Output("image2", "src")], [Input("wells", "value")]
        )
        def update_img(img):
            print(img)
            img = img[0]
            return [
                image_to_base64(
                    "/scratch/val_kvb/tnatt/plots/surf_ds_final_gf/" + img + ".png"
                ),
                image_to_base64(
                    "/scratch/val_kvb/tnatt/plots/surf_from_grid/" + img + ".png"
                ),
            ]


def image_to_base64(fn):
    print(fn)
    with open(fn, "rb") as img_file:
        return f"data:image/png;base64, {base64.b64encode(img_file.read()).decode('ascii')}"
