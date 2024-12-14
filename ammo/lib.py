#!/usr/bin/python3
from pathlib import Path
from .component import (
    Mod,
    BethesdaMod,
)


def normalize(mod: Mod | BethesdaMod, destination: Path, dest_prefix: Path) -> Path:
    """
    Prevent folders with the same name but different case
    from being created.
    """
    # pathlib.parent is slow, get the parent with string manipulation instead.
    path, file = str(destination).rsplit("/", 1)
    prefix_lower = str(dest_prefix).lower()
    local_path = path.lower().split(prefix_lower)[-1]

    for key, value in mod.replacements.items():
        local_path = local_path.replace(key, value)

    return dest_prefix / local_path.lstrip("/") / file
