#!/usr/bin/env python3
from pathlib import Path

import pytest

from test.mod.mod_common import (
    fomod_selections_choose_files,
)


def test_missing_data_fomod():
    """
    Check that the following elements can be absent of data and
    be self terminating:
    - <moduleName/>
    - <requiredInstallFiles/>
    - <files/>
    - <flag/>
    - <conditionFlags/>

    We require the following:
    - plugins have names: <plugin name="some text here">
    - groups have types: <group type="SelectExactlyOne">
    - file has source: <file source="my_file"/>
    - folder has source: <folder source="my_folder"/>
    """
    files = [
        # Default options: USSEP yes, both indoors and outdoors
        Path("test.esp"),
    ]

    has_extra_folder = True
    fomod_selections_choose_files(
        # option 3 is the only one that maps to a file,
        # but it still has self terminating tags.
        # Expect this to work.
        "missing_data",
        files,
        has_extra_folder,
        [
            {
                "page": 0,
                "option": 3,
            },
        ],
    )

    # other options have various self terminating tags.
    # Make sure we can make it to the end of the
    # fomod installer before finally crashing at "nothing to install".
    for option in range(0, 3):
        with pytest.raises(AssertionError) as error:
            fomod_selections_choose_files(
                "missing_data",
                [],
                [
                    {
                        "page": 0,
                        "option": option,
                    },
                ],
            )
            assert (
                error == "The selected options failed to map to installable components."
            )
