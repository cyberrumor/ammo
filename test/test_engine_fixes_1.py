#!/usr/bin/env python3
from common import mod_extracts_files, mod_installs_files

MOD = "mock_engine_fixes_part_1.7z"
EXTRACT_FILES = ["data/skse/plugins/mock_fixes.dll"]

INSTALLED_FILES = ["Data/SKSE/Plugins/mock_fixes.dll"]


def test_install_script_extender_plugin():
    """
    Tests that installing script extender plugins causes
    files to the expected location.
    """
    mod_extracts_files(MOD, EXTRACT_FILES)


def test_activate_script_extender_plugin():
    """
    Tests that activating script extender plugins causes
    files to exist in the expected location.
    """
    mod_installs_files(MOD, INSTALLED_FILES)
