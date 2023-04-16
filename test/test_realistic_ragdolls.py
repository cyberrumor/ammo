#!/usr/bin/env python3
from common import (
    AmmoController,
    fomod_selections_choose_files,
)


def test_fomod_realistic_ragdolls():
    """
    Test advancing through the installer with default options.
    This verifies auto-selection for "selectExactlyOne"
    """
    files = [
        "Data/realistic_ragdolls_Realistic.esp",
        "Data/meshes/actors/bear/character assets/skeleton.nif",
        "Data/meshes/actors/canine/character assets dog/skeleton.nif",
        "Data/meshes/actors/canine/character assets wolf/skeleton.nif",
        "Data/meshes/actors/cow/character assets/skeleton.nif",
        "Data/meshes/actors/deer/character assets/skeleton.nif",
        "Data/meshes/actors/draugr/character assets/skeleton.nif",
        "Data/meshes/actors/falmer/character assets/skeleton.nif",
        "Data/meshes/actors/frostbitespider/character assets/skeleton.nif",
        "Data/meshes/actors/giant/character assets/skeleton.nif",
        "Data/meshes/actors/goat/character assets/skeleton.nif",
        "Data/meshes/actors/hagraven/character assets/skeleton.nif",
        "Data/meshes/actors/mudcrab/character assets/skeleton.nif",
        "Data/meshes/actors/sabrecat/character assets/skeleton.nif",
        "Data/meshes/actors/troll/character assets/skeleton.nif",
        "Data/meshes/actors/werewolfbeast/character assets/skeleton.nif",
        "Data/meshes/actors/wolf/character assets/skeleton.nif",
        "Data/meshes/actors/character/character assets female/skeleton_female.nif",
        "Data/meshes/actors/character/character assets female/skeletonbeast_female.nif",
        "Data/meshes/actors/character/character assets/skeleton.nif",
        "Data/meshes/actors/character/character assets/skeletonbeast.nif",
    ]

    fomod_selections_choose_files(
        "mock_realistic_ragdolls",
        files,
    )


def test_fomod_realistic_ragdolls_no_ragdolls():
    """
    This verifies that selections in "selectExactlyOne" change flags only when they are supposed to.
    """
    files = [
        "Data/realistic_ragdolls_Realistic.esp",
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
