#!/usr/bin/env python3
from pathlib import Path

import pytest

from bethesda_common import (
    mod_extracts_files,
    mod_installs_files,
)


def test_extract_pak_root():
    """
    Test that installing a pak mod which contains all the directories
    up to and including ~mods is extracted without modification.
    """
    files = [
        Path("OblivionRemastered/Content/Paks/~mods/test.pak"),
        Path("OblivionRemastered/Content/Paks/~mods/test.ucas"),
        Path("OblivionRemastered/Content/Paks/~mods/test.utoc"),
    ]
    mod_extracts_files("pak_root", files)


def test_activate_pak_root():
    """
    Test that activating a pak mod which contains all the directories
    up to and including ~mods causes files to be installed in the
    correct location under the game directory.
    """
    files = [
        Path("OblivionRemastered/Content/Paks/~mods/test.pak"),
        Path("OblivionRemastered/Content/Paks/~mods/test.ucas"),
        Path("OblivionRemastered/Content/Paks/~mods/test.utoc"),
    ]
    mod_installs_files("pak_root", files)
