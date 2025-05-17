#!/usr/bin/env python3
from pathlib import Path
from common import (
    mod_extracts_files,
    mod_installs_files,
)


def test_duplicate_filenames():
    """
    Test that installing a mod that contains the same filename
    several times in different folders installs all of those files.
    """
    files = [
        Path("data/textures/test0/file.nif"),
        Path("data/textures/test1/file.nif"),
        Path("data/textures/test2/file.nif"),
    ]

    mod_installs_files("duplicate_filenames", files)


def test_extract_script_extender():
    """
    Tests that installing a script extender causes files
    to extract to expected locations.
    """
    has_extra_folder = True
    files = [
        Path("Data/Scripts/Source/Game.psc"),
        Path("Data/Scripts/game.pex"),
        Path("se64.dll"),
        Path("se64_loader.exe"),
        Path("se64_readme.txt"),
        Path("se64_whatsnew.txt"),
    ]
    mod_extracts_files("mock_script_extender", files, has_extra_folder)


def test_activate_script_extender():
    """
    Tests that activating a script extender causes links to
    be created accurately.
    """
    has_extra_folder = True
    files = [
        Path("data/scripts/source/Game.psc"),
        Path("data/scripts/game.pex"),
        Path("se64.dll"),
        Path("se64_loader.exe"),
        Path("se64_readme.txt"),
        Path("se64_whatsnew.txt"),
    ]
    mod_installs_files("mock_script_extender", files, has_extra_folder)


def test_extract_script_extender_plugin():
    """
    Tests that installing script extender plugins cause files
    to be extracted to the correct location.
    """
    has_extra_folder = True
    files = [Path("data/skse/plugins/mock_fixes.dll")]
    mod_extracts_files("mock_engine_fixes_part_1", files, has_extra_folder)


def test_activate_script_extender_plugin():
    """
    Tests that activating script extender plugins causes
    files to exist in the expected location.
    """
    has_extra_folder = True
    files = [Path("data/skse/plugins/mock_fixes.dll")]
    mod_installs_files("mock_engine_fixes_part_1", files, has_extra_folder)


def test_extract_dll_mod():
    """
    Tests that custom DLLs extract to expected location.
    """
    has_extra_folder = True
    files = [
        Path("d3dx9_42.dll"),
        Path("tbb.dll"),
        Path("tbbmalloc.dll"),
    ]
    mod_extracts_files("mock_engine_fixes_part_2", files, has_extra_folder)


def test_activate_dll_mod():
    """
    Tests that activating a custom DLL mod causes links to be
    created in the expected location.
    """
    has_extra_folder = True
    files = [
        Path("d3dx9_42.dll"),
        Path("tbb.dll"),
        Path("tbbmalloc.dll"),
    ]
    mod_installs_files("mock_engine_fixes_part_2", files, has_extra_folder)


def test_extract_extra_folder_mod():
    """
    Tests that installing a mod with no data folder
    causes files to extract to expected locations.
    """
    has_extra_folder = True
    files = [
        Path("data/DVLaSS Skyrim Underside.esp"),
        Path("data/Meshes/Terrain/Tamriel_Underside.nif"),
        Path("data/Scripts/DVLaSS_ObjectEnabler.pex"),
        Path("data/Scripts/Source/DVLaSS_ObjectEnabler.psc"),
    ]
    mod_extracts_files("mock_evlas_underside", files, has_extra_folder)


def test_activate_extra_folder_mod():
    """
    Tests that activating a mod that has a plugin but no
    data folder causes files to install to expected location.
    """
    has_extra_folder = True
    files = [
        Path("data/DVLaSS Skyrim Underside.esp"),
        Path("data/meshes/terrain/Tamriel_Underside.nif"),
        Path("data/scripts/DVLaSS_ObjectEnabler.pex"),
        Path("data/scripts/source/DVLaSS_ObjectEnabler.psc"),
    ]
    mod_installs_files("mock_evlas_underside", files, has_extra_folder)


def test_extract_no_data_folder_plugin():
    """
    Tests that installing a mod with no data folder
    causes files to extract to expected locations.
    """
    has_extra_folder = True
    files = [Path("no_data_folder_plugin.esp")]
    mod_extracts_files("no_data_folder_plugin", files, has_extra_folder)


def test_activate_no_data_folder_plugin():
    """
    Tests that activating a mod with no data folder causes
    accurate links to be created.
    """
    has_extra_folder = True
    files = [Path("no_data_folder_plugin.esp")]
    mod_installs_files("no_data_folder_plugin", files, has_extra_folder)


def test_extract_no_data_folder_dll():
    """
    Tests that installing a mod that contains only a dll
    with no data folder causes files to extract to the
    expected location.
    """
    has_extra_folder = True
    files = [Path("no_data_folder.dll")]
    mod_extracts_files("no_data_folder_dll", files, has_extra_folder)


def test_activate_no_data_folder_dll():
    """
    Tests that activating a mod that has a dll on the surface
    level, where that dll is the only file, causes an accurate
    link for that file.
    """
    has_extra_folder = True
    files = [Path("no_data_folder.dll")]
    mod_installs_files("no_data_folder_dll", files, has_extra_folder)


def test_extract_edit_scripts():
    """
    Test that installing a mod which only contains edit scripts
    extracts correctly.
    """
    files = [Path("Edit Scripts/script.pas")]
    mod_extracts_files("edit_scripts", files)


def test_install_edit_scripts():
    """
    Test that activating a mod which only contains edit scripts
    installs files to the correct location.
    """
    files = [Path("edit scripts/script.pas")]
    mod_installs_files("edit_scripts", files)
