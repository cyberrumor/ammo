#!/usr/bin/env python3
from common import mod_extracts_files, mod_installs_files

MOD = "fake_fomod.7z"
EXTRACT_FILES = [
    "fomod/no_module_conf.txt",
    "some_plugin.esp",
]
INSTALL_FILES = [
    "Data/some_plugin.esp",
]

def test_install_fake_fomod():
    """
    Tests that installing a mod that has a fomod dir but no
    ModuleConfig.txt extracts files the expected locations.
    """
    mod_extracts_files(MOD, EXTRACT_FILES)


def test_activate_fake_fomod():
    """
    Tests that activating a mod that has a fomod dir but no
    ModuleConfig.txt installs symlinks to the expected locations.

    Notably, anything inside of the fomod dir is undesired.
    """
    mod_installs_files(MOD, INSTALL_FILES)
