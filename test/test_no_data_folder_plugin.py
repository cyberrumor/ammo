#!/usr/bin/env python3
from common import mod_extracts_files, mod_installs_files

MOD = "no_data_folder_plugin.7z"
EXTRACT_FILES = [
    "no_data_folder_plugin.esp",
]
INSTALL_FILES = [
    "Data/no_data_folder_plugin.esp",
]

def test_install_no_data_folder_plugin():
    """
    Tests that installing a script extender causes files
    to extract where we expect.
    """
    mod_extracts_files(MOD, EXTRACT_FILES)


def test_activate_no_data_folder_plugin():
    """
    Tests that activating a script extender causes files
    to exist in the game dir where we expect.
    """
    mod_installs_files(MOD, INSTALL_FILES)
