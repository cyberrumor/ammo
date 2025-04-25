#!/usr/bin/env python3
from pathlib import Path

from bethesda_common import (
    mod_extracts_files,
    mod_installs_files,
)


def test_extract_pak_root():
    """
    Test that installing a pak mod which contains all the directories
    up to and including ~mods is extracted without modification.
    .
    ├── pak_root.7z
    │   └── OblivionRemastered
    │       └── Content
    │           └── Paks
    │               └── ~mods
    │                   ├── test.pak
    │                   ├── test.ucas
    │                   └── test.utoc
    """
    files = [
        Path("OblivionRemastered/Content/Paks/~mods/test.pak"),
        Path("OblivionRemastered/Content/Paks/~mods/test.ucas"),
        Path("OblivionRemastered/Content/Paks/~mods/test.utoc"),
    ]
    mod_extracts_files("pak_root", files)


def test_activate_pak_root():
    """
    Test that activating a pak mod which contains all the directories
    up to and including ~mods causes files to be installed in the
    correct location under the game directory.
    .
    ├── pak_root.7z
    │   └── OblivionRemastered
    │       └── Content
    │           └── Paks
    │               └── ~mods
    │                   ├── test.pak
    │                   ├── test.ucas
    │                   └── test.utoc
    """
    files = [
        Path("OblivionRemastered/Content/Paks/~mods/test.pak"),
        Path("OblivionRemastered/Content/Paks/~mods/test.ucas"),
        Path("OblivionRemastered/Content/Paks/~mods/test.utoc"),
    ]
    mod_installs_files("pak_root", files)


def test_extract_pak_mods():
    """
    Test that installing a pak mod which only includes the ~mods
    directory is extracted without modification.
    .
    ├── pak_mods.7z
    │   └── ~mods
    │       ├── test.pak
    │       ├── test.ucas
    │       └── test.utoc
    """
    files = [
        Path("~mods/test.pak"),
        Path("~mods/test.ucas"),
        Path("~mods/test.utoc"),
    ]
    mod_extracts_files("pak_mods", files)


def test_activate_pak_mods():
    """
    Test that activating a pak mod which only includes the ~mods
    directory has files installed to the correct location under
    the game directory.

    Since these mods aren't packaged from the game root, we have to
    guess what the directory name between the game root and "Content"
    will be. Until more games besides Oblivion Remastered are added,
    we can't detect a pattern in naming convention. Thus, we just use
    game.name.replace(" ", "") for now. This means we will get MockGame
    instead of OblivionRemastered in the paths here.
    .
    ├── pak_mods.7z
    │   └── ~mods
    │       ├── test.pak  -> MockGame/Content/Paks/~mods/test.pak
    │       ├── test.ucas -> MockGame/Content/Paks/~mods/test.ucas
    │       └── test.utoc -> MockGame/Content/Paks/~mods/test.utoc
    """
    files = [
        Path("MockGame/Content/Paks/~mods/test.pak"),
        Path("MockGame/Content/Paks/~mods/test.ucas"),
        Path("MockGame/Content/Paks/~mods/test.utoc"),
    ]
    mod_installs_files("pak_mods", files)


def test_extract_pak_no_dir():
    """
    Test that installing a pak mod which contains only loose files
    without any sort of directory structure is extracted without
    modification.
    ├── pak_no_dir.7z
    │   ├── test.pak
    │   ├── test.ucas
    │   └── test.utoc
    """
    files = [
        Path("test.pak"),
        Path("test.ucas"),
        Path("test.utoc"),
    ]
    mod_extracts_files("pak_no_dir", files)
