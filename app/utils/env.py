import os
from typing import Any

default_alias = Any | None


def get(
    key: str, default: default_alias = None, strict: bool = False
) -> str | default_alias:
    result = os.environ.get(key)
    if not result:
        if strict:
            raise KeyError(f"{key} not found in env")
        result = default
    return result
