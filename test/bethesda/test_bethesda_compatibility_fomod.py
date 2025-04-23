#!/usr/bin/env python3
from pathlib import Path
from bethesda_common import (
    fomod_selections_choose_files,
    mod_extracts_files,
    mod_installs_files,
)
import pytest


def test_base_object_swapper():
    """
    Test that configuring base object swapper behaves correctly.
    This ensures the conversion of the 'source' folder from the
    XML into a full path is accurate.
    """
    files = [
        Path("SKSE/Plugins/po3_BaseObjectSwapper.dll"),
        Path("SKSE/Plugins/po3_BaseObjectSwapper.pdb"),
    ]

    fomod_selections_choose_files(
        "mock_base_object_swapper",
        files,
    )


def test_no_activate_unconfigred_fomod_with_data_dir():
    """
    Test that fomods with a Data folder (like Embers XD or MCM Helper)
    aren't possible to activate before they've been configured.
    """
    files = []
    with pytest.raises(Warning):
        # "Fomods must be configured before they can be enabled."
        mod_installs_files("mock_embers_xd", files)


def test_parse_broken_moduleconfig():
    """
    Test parsing a broken ModuleConfig.xml.
    """
    files = []
    with pytest.raises(Warning):
        # xml.etree.ElementTree.ParseError: no element found
        fomod_selections_choose_files(
            "mock_embers_xd",
            files,
            selections=[
                {
                    "page": 0,
                    "option": 0,
                },
                {
                    "page": 1,
                    "option": 1,
                },
            ],
        )


def test_realistic_ragdolls():
    """
    Test advancing through the installer with default options.
    This verifies auto-selection for "selectExactlyOne"
    """
    files = [
        Path("realistic_ragdolls_Realistic.esp"),
        Path("meshes/actors/bear/character assets/skeleton.nif"),
        Path("meshes/actors/canine/character assets dog/skeleton.nif"),
        Path("meshes/actors/canine/character assets wolf/skeleton.nif"),
        Path("meshes/actors/cow/character assets/skeleton.nif"),
        Path("meshes/actors/deer/character assets/skeleton.nif"),
        Path("meshes/actors/draugr/character assets/skeleton.nif"),
        Path("meshes/actors/falmer/character assets/skeleton.nif"),
        Path("meshes/actors/frostbitespider/character assets/skeleton.nif"),
        Path("meshes/actors/giant/character assets/skeleton.nif"),
        Path("meshes/actors/goat/character assets/skeleton.nif"),
        Path("meshes/actors/hagraven/character assets/skeleton.nif"),
        Path("meshes/actors/mudcrab/character assets/skeleton.nif"),
        Path("meshes/actors/sabrecat/character assets/skeleton.nif"),
        Path("meshes/actors/troll/character assets/skeleton.nif"),
        Path("meshes/actors/werewolfbeast/character assets/skeleton.nif"),
        Path("meshes/actors/wolf/character assets/skeleton.nif"),
        Path("meshes/actors/character/character assets female/skeleton_female.nif"),
        Path(
            "meshes/actors/character/character assets female/skeletonbeast_female.nif"
        ),
        Path("meshes/actors/character/character assets/skeleton.nif"),
        Path("meshes/actors/character/character assets/skeletonbeast.nif"),
    ]

    fomod_selections_choose_files(
        "mock_realistic_ragdolls",
        files,
    )


def test_realistic_ragdolls_no_ragdolls():
    """
    This verifies that selections in "selectExactlyOne" change flags only when they are supposed to.
    """
    files = [
        Path("realistic_ragdolls_Realistic.esp"),
    ]

    fomod_selections_choose_files(
        "mock_realistic_ragdolls",
        files,
        selections=[
            {
                "page": 0,  # Force
                "option": 0,  # Realistic
            },
            {
                "page": 1,  # Ragdolls
                "option": 2,  # None (as opposed to all, or creatures only).
            },
        ],
    )


def test_extract_fake_fomod():
    """
    Tests that installing a mod that has a fomod dir but no
    ModuleConfig.txt extracts files to the expected locations.
    This behavior is needed by SkyUI.
    """
    files = [
        Path("fomod/no_module_conf.txt"),
        Path("some_plugin.esp"),
    ]
    mod_extracts_files("mock_skyui", files)


def test_activate_fake_fomod():
    """
    Tests that activating a mod that has a fomod dir but no
    ModuleConfig.txt installs symlinks to the expected locations.
    Notably, anything inside the fomod dir is undesired.
    """
    files = [
        Path("Data/some_plugin.esp"),
        Path("Data/fomod/no_module_conf.txt"),
    ]
    mod_installs_files("mock_skyui", files)


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
        Path("meshes/Relight/LightOccluder.nif"),
        # Default options: USSEP yes, both indoors and outdoors
        Path("RelightingSkyrim_SSE.esp"),
    ]

    fomod_selections_choose_files(
        "mock_relighting_skyrim",
        files,
    )


def test_fomod_relighting_skyrim_exteriors_only():
    """
    Exteriors only does not rely on the USSEP flag, it is the same plugin
    regardless of whether the user selected the USSEP option.

    Test that the correct plugin is installed regardless of whether the user
    said they had USSEP. This verifies that flags correctly map to
    conditionalFileInstalls.
    """
    files = [
        # requiredInstallFiles
        Path("meshes/Relight/LightOccluder.nif"),
        # exterior-only plugin
        Path("RelightingSkyrim_SSE_Exteriors.esp"),
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
        Path("meshes/Relight/LightOccluder.nif"),
        # conditionalFileInstalls
        Path("RelightingSkyrim_SSE_Interiors.esp"),
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

    files[-1] = Path("RelightingSkyrim_SSE_Interiors_nonUSSEP.esp")
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


def test_fomod_no_file_destination():
    """
    Immersive Armors doesn't list a destination key for files.
    It's unclear whether this is optional or not, but supporting this
    is easy so we might as well.
    """
    files = [
        Path("immersive_armors.esp"),
        Path("immersive_armors.bsa"),
    ]
    fomod_selections_choose_files(
        "mock_immersive_armors",
        files,
        selections=[
            {
                "page": 0,
                "option": 0,  # This is completely arbitrary
            }
        ],
    )
