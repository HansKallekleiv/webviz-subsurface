import datetime
import shutil
import warnings

from dash import html
from webviz_config import WebvizPluginABC


class PersistentIds(WebvizPluginABC):
    COUNTER: int = 0

    def __init__(
        self,
    ):
        PersistentIds.COUNTER += 1

        super().__init__()

    def persistent_uuid(self, str):
        return f"{type(self).__name__}-{PersistentIds.COUNTER}-{str}"

    @property
    def layout(self) -> html.Div:
        return html.Div(
            [
                html.Label(f"Persistent plugin id: {self.persistent_uuid('label')}"),
                html.Br(),
                html.Label(f"Generated plugin id: {self.uuid('label')}"),
            ]
        )
