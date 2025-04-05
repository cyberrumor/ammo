#!/usr/bin/env python3
import pytest

from bethesda_common import (
    AmmoController,
    extract_mod,
    install_mod,
    install_everything,
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
        controller.do_rename_mod(index, "normal_mod_renamed")

        # Verify the original folder doesn't exist after rename.
        assert location_original.exists() is False

        # Verify that the new location exists and that the properties have
        # been updated.
        assert controller.mods[index].location.exists() is True
        assert controller.mods[index].location.stem == "normal_mod_renamed"
        assert controller.mods[index].name == "normal_mod_renamed"


def test_rename_mod_fomod():
    """
    Test that renaming a fomod also moves fomod specific data
    like where the ModuleConfig.txt is located.
    """
    with AmmoController() as controller:
        original_index = extract_mod(controller, "mock_base_object_swapper")
        # Verify original ModuleConfig.xml exists
        original_mod = controller.mods[original_index]
        original_modconf = original_mod.modconf
        assert original_modconf.exists() is True

        # Rename.
        controller.do_rename_mod(original_index, "bos")

        # Verify the original modconf doesn't exist
        assert original_modconf.exists() is False

        # Verify that the new modconf isn't the old modconf
        new_index = [i.name for i in controller.mods].index("bos")
        new_mod = controller.mods[new_index]
        new_modconf = new_mod.modconf
        assert original_modconf != new_modconf

        # Verify new modconf exists
        assert new_modconf.exists() is True


def test_rename_mod_preserves_enabled_state():
    """
    Test that renaming an enabled mod keeps mod enabled.
    """
    with AmmoController() as controller:
        index = install_mod(controller, "normal_mod")
        assert controller.mods[index].enabled is True

        # Rename.
        controller.do_rename_mod(index, "normal_mod_renamed")

        assert controller.mods[index].enabled is True, (
            "An enabled mod was disabled when renamed."
        )


def test_rename_mod_preserves_disabled_state():
    """
    Test that renaming a disabled mod  keeps mod disabled.
    """
    with AmmoController() as controller:
        index = extract_mod(controller, "normal_mod")
        assert controller.mods[index].enabled is False

        # Rename.
        controller.do_rename_mod(index, "normal_mod_renamed")

        assert controller.mods[index].enabled is False, (
            "A disabled mod was enabled when renamed."
        )


def test_rename_mod_preserves_index():
    """
    Test that renaming a mod preserves that mod's position in the load order.
    """
    with AmmoController() as controller:
        install_everything(controller)
        original_index = [i.name for i in controller.mods].index("normal_mod")

        # Rename.
        controller.do_rename_mod(original_index, "normal_mod_renamed")
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
        controller.do_rename_mod(original_index, "normal_mod_renamed")

        new_plugin_index = [i.name for i in controller.plugins].index(
            "normal_plugin.esp"
        )
        assert original_plugin_index == new_plugin_index, (
            "Renaming a mod didn't preserve plugin order!"
        )


def test_rename_mod_name_exists():
    """
    Test that renaming a mod to the name of an existing mod
    causes a warning to be raised and no rename to take place.
    """
    with AmmoController() as controller:
        extract_mod(controller, "mock_conflict_1")
        extract_mod(controller, "mock_conflict_2")
        index_1 = [i.name for i in controller.mods].index("mock_conflict_1")
        index_2 = [i.name for i in controller.mods].index("mock_conflict_2")

        with pytest.raises(Warning):
            controller.do_rename_mod(index_1, "mock_conflict_2")

        assert controller.mods[index_1].location.exists()
        assert controller.mods[index_1].location.stem == "mock_conflict_1"
        assert controller.mods[index_1].name == "mock_conflict_1"

        assert controller.mods[index_2].location.exists()
        assert controller.mods[index_2].location.stem == "mock_conflict_2"
        assert controller.mods[index_2].name == "mock_conflict_2"


def test_rename_download_moves_file():
    """
    Test that renaming a download causes the file to be moved.
    """
    with AmmoController() as controller:
        temp_download = controller.downloads_dir / "rename_me.7z"
        temp_download.touch()
        renamed_download = controller.downloads_dir / "i_was_renamed.7z"

        try:
            controller.do_refresh()

            index = [i.name for i in controller.downloads].index("rename_me.7z")
            original_download = controller.downloads[index]

            # Rename.
            controller.do_rename_download(index, "i_was_renamed")

            new_index = [i.name for i in controller.downloads].index("i_was_renamed.7z")
            new_download = controller.downloads[new_index]

            # Ensure the old download is gone.
            assert original_download.location.exists() is False

            # Ensure the new download is present and has the correct data.
            assert new_download.location.exists() is True
            assert new_download.name == "i_was_renamed.7z"

        finally:
            # Clean up our temporary files.
            try:
                temp_download.unlink()
            except FileNotFoundError:
                pass
            try:
                renamed_download.unlink()
            except FileNotFoundError:
                pass
