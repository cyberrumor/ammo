#!/usr/bin/env python3
from pathlib import Path
from common import mod_installs_files


MOD_NAME = "duplicate_filenames"

MOD_FILES = [
    Path("Data/textures/test0/file.nif"),
    Path("Data/textures/test1/file.nif"),
    Path("Data/textures/test2/file.nif"),
]


def test_duplicate_filenames():
    """
    Test that installing a mod that contains the same filename
    several times in different folders installs all of those
    files.
    """
    mod_installs_files(MOD_NAME, MOD_FILES)
