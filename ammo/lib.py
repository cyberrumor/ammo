#!/usr/bin/python3
from pathlib import Path
from contextlib import contextmanager


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass


def casefold_path(
    replacements: dict[str, str], parent_path: Path, relative_path: Path
) -> Path:
    """
    Prevent folders with the same name but different case
    from being created.

    parent_path is like Path("/tmp/MockGame")
    relative_path is like Path("data/Textures/My_Texture.dds")
    """
    assert relative_path.is_absolute() is False

    # relative_path is like Path("data/textures/")
    case_corrected_parts = tuple(
        replacements.get(p := part.lower(), p) for part in relative_path.parent.parts
    )

    # case_corrected_relative_path is like Path("Data/textures/")
    case_corrected_relative_path = Path(*case_corrected_parts)

    # case_corrected_absolute_path is like Path("/tmp/MockGame/Data/textures/My_Texture.dds")
    case_corrected_absolute_path = (
        parent_path / case_corrected_relative_path / relative_path.name
    )

    return case_corrected_absolute_path
