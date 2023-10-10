#!/usr/bin/env python3
from pathlib import Path
from common import mod_installs_files
import pytest


@pytest.mark.parametrize("use_symlinks", [True, False])
def test_fomod_embers_xd(use_symlinks):
    """
    In the past, there were some issues with Embers XD plugin becoming visible
    upon activate, but not persisting through a refresh.

    Test that only plugins located immediately under the Data folder are
    added to self.plugins for fomods.

    mock_embers_xd is a preconfigured fomod with a Data folder, so we can
    test this by merely activating, refreshing, and checking plugins.
    """
    files = [
        Path("Data/Embers XD - Fire Magick Add-On.esp"),
    ]

    mod_installs_files("mock_embers_xd", files, use_symlinks)
