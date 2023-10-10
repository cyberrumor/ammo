#!/usr/bin/env python3
from pathlib import Path
from common import mod_extracts_files, mod_installs_files
import pytest

MOD = "mock_script_extender"
FILES = [
    Path("Data/Scripts/Source/Game.psc"),
    Path("Data/Scripts/game.pex"),
    Path("se64.dll"),
    Path("se64_loader.exe"),
    Path("se64_readme.txt"),
    Path("se64_whatsnew.txt"),
]


def test_install_script_extender():
    """
    Tests that installing a script extender causes files
    to extract to expected locations.
    """
    mod_extracts_files(MOD, FILES)


@pytest.mark.parametrize("use_symlinks", [True, False])
def test_activate_script_extender(use_symlinks):
    """
    Tests that activating a script extender causes files
    to exist in expected locations.
    """
    mod_installs_files(MOD, FILES, use_symlinks)
