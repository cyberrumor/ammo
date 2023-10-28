#!/usr/bin/env python3
from pathlib import Path
from common import (
    AmmoController,
    fomod_selections_choose_files,
)


def test_fomod_base_object_swapper():
    """
    Test that configuring Base Object Swapper behaves correctly.
    This ensures the conversion of the 'source' folder from the XML
    into a full path is accurate.
    """
    files = [
        Path("Data/SKSE/Plugins/po3_BaseObjectSwapper.dll"),
        Path("Data/SKSE/Plugins/po3_BaseObjectSwapper.pdb"),
    ]

    fomod_selections_choose_files(
        "mock_base_object_swapper",
        files,
    )
