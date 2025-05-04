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


def normalize(mod: Mod | BethesdaMod, destination: Path, parent_path: Path) -> Path:
    """
    Prevent folders with the same name but different case
    from being created.

    destination is like Path("/tmp/MockGame/data/Textures/My_Texture.dds")
    parent_path is like Path("/tmp/MockGame")
    """
    # relative_path is like Path("data/textures/")
    relative_path = Path(str(destination.relative_to(parent_path).parent).lower())
    case_corrected_parts = tuple(
        mod.replacements.get(part, part) for part in relative_path.parts
    )
    # case_corrected_relative_path is like Path("Data/textures/")
    case_corrected_relative_path = Path(*case_corrected_parts)

    # case_corrected_absolute_path is like Path("/tmp/MockGame/Data/textures/My_Texture.dds")
    case_corrected_absolute_path = (
        parent_path / case_corrected_relative_path / destination.name
    )
    return case_corrected_absolute_path
