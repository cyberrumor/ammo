#!/usr/bin/env python3
from pathlib import Path
from common import mod_extracts_files, mod_installs_files
import pytest

MOD = "mock_skyui"
EXTRACT_FILES = [
    Path("fomod/no_module_conf.txt"),
    Path("some_plugin.esp"),
]
INSTALL_FILES = [
    Path("Data/some_plugin.esp"),
]


def test_install_fake_fomod():
    """
    Tests that installing a mod that has a fomod dir but no
    ModuleConfig.txt extracts files the expected locations.
    """
    mod_extracts_files(MOD, EXTRACT_FILES)


@pytest.mark.parametrize("use_symlinks", [True, False])
def test_activate_fake_fomod(use_symlinks):
    """
    Tests that activating a mod that has a fomod dir but no
    ModuleConfig.txt installs symlinks to the expected locations.

    Notably, anything inside of the fomod dir is undesired.
    """
    mod_installs_files(MOD, INSTALL_FILES, use_symlinks)
