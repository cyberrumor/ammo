#!/usr/bin/env python3
from common import mod_extracts_files, mod_installs_files

MOD = "no_data_folder_plugin"
EXTRACT_FILES = [
    "no_data_folder_plugin.esp",
]
INSTALL_FILES = [
    "Data/no_data_folder_plugin.esp",
]


def test_install_no_data_folder_plugin():
    """
    Tests that installing a mod with no data folder
    causes files to extract to expected locations.
    """
    mod_extracts_files(MOD, EXTRACT_FILES)


def test_activate_no_data_folder_plugin():
    """
    Tests that activating a mod that has a plugin but no
    data folder causes files to install to expected location.
    """
    mod_installs_files(MOD, INSTALL_FILES)
