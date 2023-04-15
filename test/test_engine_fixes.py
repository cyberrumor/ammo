#!/usr/bin/env python3
from common import mod_extracts_files, mod_installs_files

# script extender mod
SE_MOD = "mock_engine_fixes_part_1.7z"
SE_EXTRACT_FILES = ["data/skse/plugins/mock_fixes.dll"]
SE_INSTALLED_FILES = ["Data/SKSE/Plugins/mock_fixes.dll"]
# DLL mod
DLL_MOD = "mock_engine_fixes_part_2.7z"
DLL_FILES = [
    "d3dx9_42.dll",
    "tbb.dll",
    "tbbmalloc.dll",
]


def test_install_script_extender_plugin():
    """
    Tests that installing script extender plugins causes
    files to the expected location.
    """
    mod_extracts_files(SE_MOD, SE_EXTRACT_FILES)


def test_activate_script_extender_plugin():
    """
    Tests that activating script extender plugins causes
    files to exist in the expected location.
    """
    mod_installs_files(SE_MOD, SE_INSTALLED_FILES)


def test_install_dll_mod():
    """
    Tests that custom DLLs extract to expected location.
    """
    mod_extracts_files(DLL_MOD, DLL_FILES)


def test_activate_dll_mod():
    """
    Tests that activating a custom DLL mod causes files
    to exist in the expected location.
    """
    mod_installs_files(DLL_MOD, DLL_FILES)
