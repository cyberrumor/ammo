#!/usr/bin/python3
from pathlib import Path


NO_EXTRACT_DIRS = [
    "skse",
    "netscriptframework",
    "bashtags",
    "docs",
    "meshes",
    "textures",
    "grass",
    "animations",
    "interface",
    "strings",
    "misc",
    "shaders",
    "sounds",
    "voices",
    "edit scripts",
    "scripts",
    "seq",
]

REPLACEMENTS = {
    # Order matters
    "data files": "Data Files",
    "data": "Data",
    # Order matters
    "edit scripts": "Edit Scripts",
    "scripts": "Scripts",
    "dyndolod": "DynDOLOD",
    "plugins": "Plugins",
    "netscriptframework": "NetScriptFramework",
    "skse": "SKSE",
    "docs": "Docs",
    "source": "Source",
}


def normalize(destination: Path, dest_prefix: Path) -> Path:
    """
    Prevent folders with the same name but different case
    from being created.
    """
    # pathlib.parent is slow, get the parent with string manipulation instead.
    path, file = str(destination).rsplit("/", 1)
    prefix_lower = str(dest_prefix).lower()
    local_path = path.lower().split(prefix_lower)[-1]
    for key, value in REPLACEMENTS.items():
        local_path = local_path.replace(key, value)
    return dest_prefix / local_path.lstrip("/") / file
