#!/usr/bin/env python3
from common import mod_extracts_files, mod_installs_files

MOD = "mock_engine_fixes_part_2.7z"
FILES = [
    "d3dx9_42.dll",
    "tbb.dll",
    "tbbmalloc.dll",
]

def test_install_dll_mod():
    """
    Tests that custom DLLs extract to expected location.
    """
    mod_extracts_files(MOD, FILES)


def test_activate_dll_mod():
    """
    Tests that activating a custom DLL mod causes files
    to exist in the expected location.
    """
    mod_installs_files(MOD, FILES)
