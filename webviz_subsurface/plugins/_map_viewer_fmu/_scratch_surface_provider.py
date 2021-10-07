import hashlib

import pandas as pd


class ScratchSurfaceProvider:
    def __init__(self, surfacetable: pd.DataFrame) -> None:
        self._surfacetable = surfacetable
        self._surfacetable["id"] = self._surfacetable["path"].apply(_make_hash_string)


def _make_hash_string(string_to_hash: str) -> str:
    # There is no security risk here and chances of collision should be very slim
    return hashlib.md5(string_to_hash.encode()).hexdigest()  # nosec