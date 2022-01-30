import datetime
import shutil
import warnings

from dash import html
from webviz_config import WebvizPluginABC


class PersistentIds(WebvizPluginABC):
    def __init__(
        self,
    ):

        super().__init__()

    def persistent_uuid(self, str):
        return f"{__name__}-{str}"

    @property
    def layout(self) -> html.Div:
        return html.Div(
            [
                html.Label(f"Persistent plugin id: {self.persistent_uuid('label')}"),
                html.Label(f"Generated plugin id: {self.uuid('label')}"),
            ]
        )
