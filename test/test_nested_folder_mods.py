#!/usr/bin/env python3
from pathlib import Path
from common import mod_extracts_files, mod_installs_files

EXTRA_FOLDER_MOD_NAME = "mock_evlas_underside"
PLUGIN_EXTRACT_FILES = [
    Path("data/DVLaSS Skyrim Underside.esp"),
    Path("data/Meshes/Terrain/Tamriel_Underside.nif"),
    Path("data/Scripts/DVLaSS_ObjectEnabler.pex"),
    Path("data/Scripts/Source/DVLaSS_ObjectEnabler.psc"),
]
MOD_INSTALL_FILES = [
    Path("Data/DVLaSS Skyrim Underside.esp"),
    Path("Data/meshes/terrain/Tamriel_Underside.nif"),
    Path("Data/Scripts/DVLaSS_ObjectEnabler.pex"),
    Path("Data/Scripts/Source/DVLaSS_ObjectEnabler.psc"),
]


def test_extract_extra_folder_mod():
    """
    Tests that installing a mod with no data folder
    causes files to extract to expected locations.
    """
    mod_extracts_files(EXTRA_FOLDER_MOD_NAME, PLUGIN_EXTRACT_FILES)


def test_activate_extra_folder_mod():
    """
    Tests that activating a mod that has a plugin but no
    data folder causes files to install to expected location.
    """
    mod_installs_files(EXTRA_FOLDER_MOD_NAME, MOD_INSTALL_FILES)
