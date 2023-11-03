#!/usr/bin/env python3
from pathlib import Path
from common import mod_extracts_files, mod_installs_files

PLUGIN_MOD_NAME = "no_data_folder_plugin"
PLUGIN_EXTRACT_FILES = [
    Path("no_data_folder_plugin.esp"),
]
PLUGIN_INSTALL_FILES = [
    Path("Data/no_data_folder_plugin.esp"),
]


DLL_MOD_NAME = "no_data_folder_dll"
DLL_EXTRACT_FILES = [
    Path("no_data_folder.dll"),
]
DLL_INSTALL_FILES = [
    Path("no_data_folder.dll"),
]

EDIT_SCRIPTS_MOD_NAME = "edit_scripts"
EDIT_SCRIPTS_EXTRACT_FILES = [Path("Edit Scripts/script.pas")]
EDIT_SCRIPTS_INSTALL_FILES = [Path("Edit Scripts/script.pas")]


def test_install_no_data_folder_plugin():
    """
    Tests that installing a mod with no data folder
    causes files to extract to expected locations.
    """
    mod_extracts_files(PLUGIN_MOD_NAME, PLUGIN_EXTRACT_FILES)


def test_activate_no_data_folder_plugin():
    """
    Tests that activating a mod that has a plugin but no
    data folder causes files to install to expected location.
    """
    mod_installs_files(PLUGIN_MOD_NAME, PLUGIN_INSTALL_FILES)


def test_install_no_data_folder_dll():
    """
    Tests that installing a mod that contains only a dll
    with no data folder causes files to extract to the
    expected location.
    """
    mod_extracts_files(DLL_MOD_NAME, DLL_EXTRACT_FILES)


def test_activate_no_data_folder_dll():
    """
    Tests that activating a mod that has a dll on the surface
    level, where that dll is the only file, causes that file
    to install to the expected location.
    """
    mod_extracts_files(DLL_MOD_NAME, DLL_INSTALL_FILES)


def test_install_edit_scripts():
    """
    Test that installing a mod which only contains edit scripts
    extracts correctly.
    """
    mod_extracts_files(EDIT_SCRIPTS_MOD_NAME, EDIT_SCRIPTS_EXTRACT_FILES)


def test_activate_edit_scripts():
    """
    Test that activating a mod which only contains edit scripts
    installs files to the correct location.
    """
    mod_installs_files(EDIT_SCRIPTS_MOD_NAME, EDIT_SCRIPTS_INSTALL_FILES)
