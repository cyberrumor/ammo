#!/usr/bin/python3
from pathlib import Path


def normalize(destination: Path, dest_prefix: Path) -> Path:
    """
    Prevent folders with the same name but different case
    from being created.
    """
    path = destination.parent
    file = destination.name
    local_path = str(path).split(str(dest_prefix))[-1].lower()
    for i in [
        "NetScriptFramework",
        "Data Files",
        "Data",
        "DynDOLOD",
        "Plugins",
        "SKSE",
        "Edit Scripts",
        "Docs",
        "Scripts",
        "Source",
    ]:
        local_path = local_path.replace(i.lower(), i)

    new_dest: Path = Path(dest_prefix / local_path.lstrip("/"))
    result = new_dest / file
    return result
