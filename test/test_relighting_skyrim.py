#!/usr/bin/env python3
from pathlib import Path
from common import fomod_selections_choose_files


def test_fomod_relighting_skyrim():
    """
    Relighting Skyrim uses the 'requiredInstallFiles' directive as well as
    conditional file installs that are matched according to flags configured
    by the users selections.

    This tests that requiredInstallFiles are included, and that conditionalFileInstalls
    are handled properly.
    """
    files = [
        # requiredInstallFiles
        Path("Data/meshes/Relight/LightOccluder.nif"),
        # Default options: USSEP yes, both indoors and outdoors
        Path("Data/RelightingSkyrim_SSE.esp"),
    ]

    fomod_selections_choose_files(
        "mock_relighting_skyrim",
        files,
    )


def test_fomod_relighting_skryim_exteriors_only():
    """
    Exteriors only does not rely on the USSEP flag, it is the same plugin
    regardless of whether the user selected the USSEP option.

    Test that the correct plugin is installed regardless of whether the user
    said they had USSEP. This verifies that flags correctly map to
    conditionalFileInstalls.
    """
    files = [
        # requiredInstallFiles
        Path("Data/meshes/Relight/LightOccluder.nif"),
        # exterior-only plugin
        Path("Data/RelightingSkyrim_SSE_Exteriors.esp"),
    ]

    # With ussep
    fomod_selections_choose_files(
        "mock_relighting_skyrim",
        files,
        selections=[
            {
                "page": 0,  # with or without ussep requirement
                "option": 0,  # with ussep
            },
            {
                "page": 1,  # choose a version to install
                "option": 1,  # exteriors only version.
            },
        ],
    )

    # Without ussep
    fomod_selections_choose_files(
        "mock_relighting_skyrim",
        files,
        selections=[
            {
                "page": 0,  # with or without ussep requirement
                "option": 1,  # without ussep
            },
            {
                "page": 1,  # choose a version to install
                "option": 1,  # exteriors only version.
            },
        ],
    )


def test_fomod_relighting_skyrim_interiors_only():
    """
    Interiors gets a different plugin depending on USSEP.

    This verifies that flags correctly map to conditionalFileInstalls.
    """
    files = [
        # requiredInstallFiles
        Path("Data/meshes/Relight/LightOccluder.nif"),
        # conditionalFileInstalls
        Path("Data/RelightingSkyrim_SSE_Interiors.esp"),
    ]

    # With ussep
    fomod_selections_choose_files(
        "mock_relighting_skyrim",
        files,
        selections=[
            {
                "page": 0,  # with/out ussep
                "option": 0,  # with
            },
            {
                "page": 1,  # version
                "option": 2,  # interiors only version
            },
        ],
    )

    files[-1] = Path("Data/RelightingSkyrim_SSE_Interiors_nonUSSEP.esp")
    # Without ussep
    fomod_selections_choose_files(
        "mock_relighting_skyrim",
        files,
        selections=[
            {
                "page": 0,  # with/out ussep
                "option": 1,  # without
            },
            {
                "page": 1,  # version
                "option": 2,  # interiors only version
            },
        ],
    )
