#!/usr/bin/env python3
from common import mod_extracts_files, mod_installs_files

MOD = "mock_engine_fixes_part_2.7z"
FILES = [
    "d3dx9_42.dll",
    "tbb.dll",
    "tbbmalloc.dll",
]

def test_install_script_extender():
    """
    Tests that installing a script extender causes files
    to extract where we expect.
    """
    mod_extracts_files(MOD, FILES)


def test_activate_script_extender():
    """
    Tests that activating a script extender causes files
    to exist in the game dir where we expect.
    """
    mod_installs_files(MOD, FILES)
