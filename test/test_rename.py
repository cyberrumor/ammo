#!/usr/bin/env python3
from pathlib import Path
import pytest

from common import (
    AmmoController,
    extract_mod,
    install_mod,
    install_everything,
)
from ammo.component import (
    Mod,
    ComponentEnum,
    DeleteEnum,
)


def test_rename_mod_moves_folder():
    """
    Test that renaming a mod removes ammo_mod_dir / old_location
    and creates ammo_mod_dir / new_location.
    """
    with AmmoController() as controller:
        index = install_mod(controller, "normal_mod")
        location_original = controller.mods[index].location

        # Verify original folder exists before rename.
        assert location_original.exists()

        # Rename.
        controller.rename(DeleteEnum("mod"), index, "normal_mod_renamed")

        # Verify the original folder doesn't exist after rename.
        assert location_original.exists() is False

        # Verify that the new location exists and that the properties have
        # been updated.
        assert controller.mods[index].location.exists() is True
        assert controller.mods[index].location.stem == "normal_mod_renamed"
        assert controller.mods[index].name == "normal_mod_renamed"
        assert controller.mods[index].parent_data_dir == controller.game.data


def test_rename_mod_preserves_enabled_state():
    """
    Test that renaming an enabled mod keeps mod enabled.
    """
    with AmmoController() as controller:
        index = install_mod(controller, "normal_mod")
        assert controller.mods[index].enabled is True

        # Rename.
        controller.rename(DeleteEnum("mod"), index, "normal_mod_renamed")

        assert (
            controller.mods[index].enabled is True
        ), "An enabled mod was disabled when renamed."


def test_rename_mod_preserves_disabled_state():
    """
    Test that renaming a disabled mod  keeps mod disabled.
    """
    with AmmoController() as controller:
        index = extract_mod(controller, "normal_mod")
        assert controller.mods[index].enabled is False

        # Rename.
        controller.rename(DeleteEnum("mod"), index, "normal_mod_renamed")

        assert (
            controller.mods[index].enabled is False
        ), "A disabled mod was enabled when renamed."


def test_rename_mod_preserves_index():
    """
    Test that renaming a mod preserves that mod's position in the load order.
    """
    with AmmoController() as controller:
        install_everything(controller)
        original_index = [i.name for i in controller.mods].index("normal_mod")

        # Rename.
        controller.rename(DeleteEnum("mod"), original_index, "normal_mod_renamed")
        new_index = [i.name for i in controller.mods].index("normal_mod_renamed")

        assert new_index == original_index, "A renamed mod didn't preserve load order!"


def test_rename_mod_preserves_plugin_index():
    """
    Test that renaming a mod preserves the order of that mod's plugins.
    """
    with AmmoController() as controller:
        install_everything(controller)
        original_index = [i.name for i in controller.mods].index("normal_mod")
        original_plugin_index = [i.name for i in controller.plugins].index(
            "normal_plugin.esp"
        )

        # Rename.
        controller.rename(DeleteEnum("mod"), original_index, "normal_mod_renamed")

        new_plugin_index = [i.name for i in controller.plugins].index(
            "normal_plugin.esp"
        )
        assert (
            original_plugin_index == new_plugin_index
        ), "Renaming a mod didn't preserve plugin order!"


def test_rename_mod_name_exists():
    """
    Test that renaming a mod to the name of an existing mod
    causes a warning to be raised and no rename to take place.
    """
    with AmmoController() as controller:
        index_1 = extract_mod(controller, "conflict_1")
        index_2 = extract_mod(controller, "conflict_2")
        assert index_1 != index_2

        with pytest.raises(Warning):
            controller.rename(DeleteEnum("mod"), index_1, "conflict_2")

        assert controller.mods[index_1].location.exists()
        assert controller.mods[index_1].location.stem == "conflict_1"
        assert controller.mods[index_1].name == "conflict_1"

        assert controller.mods[index_2].location.exists()
        assert controller.mods[index_2].location.stem == "conflict_2"
        assert controller.mods[index_2].name == "conflict_2"


def test_rename_download_moves_file():
    """
    Test that renaming a download causes the file to be moved.
    """
    with AmmoController() as controller:
        temp_download = controller.downloads_dir / "rename_me.7z"
        temp_download.touch()
        renamed_download = controller.downloads_dir / "i_was_renamed.7z"

        try:
            controller.refresh()

            index = [i.name for i in controller.downloads].index("rename_me.7z")
            original_download = controller.downloads[index]

            # Rename.
            controller.rename(DeleteEnum("download"), index, "i_was_renamed")

            new_index = [i.name for i in controller.downloads].index("i_was_renamed.7z")
            new_download = controller.downloads[index]

            # Ensure the old download is gone.
            assert original_download.location.exists() is False

            # Ensure the new download is present and has the correct data.
            assert new_download.location.exists() is True
            assert new_download.name == "i_was_renamed.7z"

        finally:
            # Clean up our temporary files.
            try:
                temp_download.unlink()
            except:
                pass
            try:
                renamed_download.unlink()
            except:
                pass
