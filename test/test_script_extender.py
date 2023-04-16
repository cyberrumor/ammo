#!/usr/bin/env python3
from common import mod_extracts_files, mod_installs_files

MOD = "mock_script_extender"
FILES = [
    "Data/Scripts/Source/Game.psc",
    "Data/Scripts/game.pex",
    "se64.dll",
    "se64_loader.exe",
    "se64_readme.txt",
    "se64_whatsnew.txt",
]


def test_install_script_extender():
    """
    Tests that installing a script extender causes files
    to extract to expected locations.
    """
    mod_extracts_files(MOD, FILES)


def test_activate_script_extender():
    """
    Tests that activating a script extender causes files
    to exist in expected locations.
    """
    mod_installs_files(MOD, FILES)
