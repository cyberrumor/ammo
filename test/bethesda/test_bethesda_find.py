#!/usr/bin/env python3
from pathlib import Path

import pytest

from bethesda_common import (
    AmmoController,
    install_mod,
    extract_mod,
    install_everything,
)


def test_find_no_args_shows_all():
    """
    Test that using the find command without arguments
    will cause all components to become visible.
    """
    with AmmoController() as controller:
        install_everything(controller)

        for i in controller.mods + controller.downloads + controller.plugins:
            i.visible = False

        controller.do_find()

        for i in controller.mods + controller.downloads + controller.plugins:
            assert i.visible is True


def test_find_install_all():
    """
    Test that narrowing visible downloads with the 'find'
    command then opting to install 'all' only installs
    visible components.
    """
    with AmmoController() as controller:
        controller.do_find("conflict")
        controller.do_install("all")
        assert set([i.name for i in controller.mods]) == set(
            ["mock_conflict_2", "mock_conflict_1"]
        )


def test_find_activate_all_mods():
    """
    Test that narrowing visible mods with the 'find'
    command then opting to activate 'all' only activates
    visible mods.
    """
    with AmmoController() as controller:
        extract_mod(controller, "mock_conflict_1")
        extract_mod(controller, "mock_conflict_2")
        extract_mod(controller, "normal_mod")

        controller.do_find("conflict")
        controller.activate_mod("all")

        assert set([i.name for i in controller.mods if i.enabled]) == set(
            [
                "mock_conflict_2",
                "mock_conflict_1",
            ]
        )


def test_find_deactivate_all_mods():
    """
    Test that narrowing visible mods with the 'find'
    command then opting to deactivate 'all' only deactivates
    visible mods.
    """
    with AmmoController() as controller:
        install_mod(controller, "mock_conflict_1")
        install_mod(controller, "mock_conflict_2")
        install_mod(controller, "normal_mod")

        controller.do_find("conflict")
        controller.deactivate_mod("all")

        assert set([i.name for i in controller.mods if i.enabled]) == set(
            ["normal_mod"]
        )


def test_find_activate_all_plugins():
    """
    Test that narrowing visible plugins with the 'find'
    command then activating 'all' only activates visible
    plugins.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")
        extract_mod(controller, "mock_conflict_1")
        extract_mod(controller, "no_data_folder_plugin")
        controller.activate_mod("all")

        controller.do_find("normal", "mock")
        controller.activate_plugin("all")

        assert set([i.name for i in controller.plugins if i.enabled]) == set(
            [
                "mock_plugin.esp",
                "normal_plugin.esp",
            ]
        )


def test_find_deactivate_all_plugins():
    """
    Test that narrowing visible plugins with the 'find'
    command then deactivating 'all' only deactivates
    visible plugins.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "mock_conflict_1")
        install_mod(controller, "no_data_folder_plugin")

        controller.do_find("normal", "mock")
        controller.deactivate_plugin("all")

        assert set([i.name for i in controller.plugins if i.enabled]) == set(
            ["no_data_folder_plugin.esp"]
        )


def test_find_delete_all_mods():
    """
    Test that narrowing visible mods with 'find'
    then deleting all will only delete visible mods.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")
        extract_mod(controller, "mock_conflict_1")
        extract_mod(controller, "no_data_folder_plugin")

        controller.do_find("normal", "conflict")
        controller.delete_mod("all")

        assert set([i.name for i in controller.mods]) == set(["no_data_folder_plugin"])


def test_find_plugin_by_mod_name():
    """
    Test that finding a mod will show the plugins associated
    with it, even if the plugin names don't have anything
    to do with the mod's name.
    """
    with AmmoController() as controller:
        install_mod(controller, "mock_conflict_1")

        controller.do_find("conflict")

        assert set([i.name for i in controller.plugins if i.visible]) == set(
            ["mock_plugin.esp"]
        )


def test_find_mod_by_plugin_name():
    """
    Test that finding a plugin will show the mods it belongs to,
    even if the mod names don't have anything to do with the
    plugin's name.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "mock_conflict_1")
        install_mod(controller, "mock_conflict_2")
        controller.do_find("mock_plugin.esp")

        assert set([i.name for i in controller.mods if i.visible]) == set(
            ["mock_conflict_1", "mock_conflict_2"]
        )


def test_find_filter_persists_after_refresh():
    """
    Test that installing a mod doesn't remove the filter.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.do_find("conflict")
        controller.do_install("all")

        assert set([m.name for m in controller.mods if m.visible]) == set(
            ["mock_conflict_1", "mock_conflict_2"]
        )


def test_find_fomods():
    """
    Test that "find fomod" or "find fomods" will match all fomods.
    """
    with AmmoController() as controller:
        install_everything(controller)

        controller.do_find("fomods")

        for i in controller.mods:
            if i.fomod:
                assert i.visible
                continue
            assert i.visible is False


def test_find_dlc_no_crash():
    """
    The find command references DLC, which is an instance of Plugin with
    self.mod == None. The find command references self.mod.name for plugins.
    This tests that we aren't calling '.name' on a NoneType.
    """
    plugin = None
    dlc_file = None
    plugin_file = None
    with AmmoController() as controller:
        plugin = controller.game.data / "normal_plugin.esp"
        dlc_file = controller.game.dlc_file
        plugin_file = controller.game.plugin_file

    # Add the plugin to DLCList.txt.
    Path.mkdir(dlc_file.parent, parents=True, exist_ok=True)
    with open(dlc_file, "w") as dlc_txt:
        dlc_txt.write("normal_plugin.esp")

    with open(plugin_file, "w") as plugin_txt:
        plugin_txt.write("*normal_plugin.esp")

    try:
        # Create a fake normal_plugin.esp file.
        Path.mkdir(plugin.parent, parents=True, exist_ok=True)
        with open(plugin, "w") as normal_plugin:
            normal_plugin.write("")

        # Test that the find command works.
        with AmmoController() as controller:
            controller.do_find("normal_plugin.esp")
            # No mod to check here since DLC doesn't have an
            # associated mod. Check that our plugin is visible.
            assert controller.plugins[0].visible is True
    finally:
        try:
            plugin.unlink()
        except FileNotFoundError:
            pass


def test_find_activate_hidden_component():
    """
    Test that the activate commands raise a warning
    when used against hidden components.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.do_find("no_match")

        with pytest.raises(Warning):
            controller.activate_mod(0)

        with pytest.raises(Warning):
            controller.activate_plugin(0)


def test_find_deactivate_hidden_component():
    """
    Test that the deactivate commands raise a warning
    when used against hidden components.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.do_find("no_match")

        with pytest.raises(Warning):
            controller.deactivate_plugin(0)

        with pytest.raises(Warning):
            controller.deactivate_mod(0)


def test_find_delete_hidden_component():
    """
    Test that the delete commands raise a warning
    when used against hidden components.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.do_find("no_match")

        with pytest.raises(Warning):
            controller.delete_download(0)

        with pytest.raises(Warning):
            controller.delete_mod(0)

        with pytest.raises(Warning):
            controller.delete_plugin(0)
