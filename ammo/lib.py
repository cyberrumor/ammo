#!/usr/bin/python3
from pathlib import Path
from contextlib import contextmanager
from .component import (
    Mod,
    BethesdaMod,
)


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass


def normalize(mod: Mod | BethesdaMod, destination: Path, dest_prefix: Path) -> Path:
    """
    Prevent folders with the same name but different case
    from being created.

    destination is like Path("/tmp/MockGame/data/Textures/My_Texture.dds")
    dest_prefix is like Path("/tmp/MockGame")
    """
    # local_path is like Path("data/textures/")
    local_path = Path(str(destination.relative_to(dest_prefix).parent).lower())
    case_corrected_parts = tuple(
        mod.replacements.get(part, part) for part in local_path.parts
    )
    case_corrected_local_path = Path(*case_corrected_parts)
    # local_path is now like Path("Data/textures/")

    # result is like Path("/tmp/MockGame/Data/textures/My_Texture.dds")
    result = dest_prefix / case_corrected_local_path / destination.name
    return result
