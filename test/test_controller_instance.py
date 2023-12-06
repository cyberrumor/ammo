#!/usr/bin/env python3
import os
from pathlib import Path
import shutil

import pytest

from ammo.component import (
    ComponentEnum,
)
from common import (
    AmmoController,
    install_everything,
    install_mod,
)


def test_controller_first_launch():
    """
    Sanity check the ammo_controller fixture, that it creates
    the game directory and properly removes it.
    """
    with AmmoController() as controller:
        game_dir = controller.game.directory
        assert os.path.exists(
            game_dir
        ), f"game_dir {game_dir} did not exist after the controller started."

        data_dir = controller.game.data
        assert os.path.exists(
            data_dir
        ), f"data_dir {data_dir} did not exist after the controller started."

        downloads_dir = controller.downloads_dir
        assert os.path.exists(
            downloads_dir
        ), f"downloads_dir {downloads_dir} did not exist after the controller started."

        conf_dir = os.path.split(controller.game.ammo_conf)[0]
        assert os.path.exists(
            conf_dir
        ), f"ammo_dir {conf_dir} did not exist after the controller started."

    assert not os.path.exists(
        game_dir
    ), f"game_dir {game_dir} was not removed after context manager closed"

    assert not os.path.exists(
        data_dir
    ), f"data dir {data_dir} was not removed after context manager closed"

    assert os.path.exists(
        downloads_dir
    ), f"downloads_dir {downloads_dir} was deleted after context manager closed.\
        It would be a good time to `git checkout Downloads`"

    assert not os.path.exists(
        conf_dir
    ), f"ammo_dir {conf_dir} existed after the context manager closed."


def test_controller_subsequent_launch():
    """
    Ensure ammo behaves correctly when launched against a game
    that already has mods installed, Plugins.txt populated with
    a non-default order, etc.
    """
    with AmmoController() as first_launch:
        install_everything(first_launch)

        # change some config to ensure it's not just alphabetic
        first_launch.move(ComponentEnum.PLUGIN, 0, 2)
        first_launch.move(ComponentEnum.MOD, 2, 0)
        first_launch.deactivate(ComponentEnum.MOD, 1)
        first_launch.deactivate(ComponentEnum.PLUGIN, 4)
        first_launch.commit()

        mods = [(i.name, i.location, i.enabled) for i in first_launch.mods]
        downloads = [(i.name, i.location) for i in first_launch.downloads]
        plugins = [(i.name, i.enabled) for i in first_launch.plugins]

        # Launch the second instance of ammo against this configuration.
        with AmmoController() as controller:
            # check mods are the same
            assert [
                (i.name, i.location, i.enabled) for i in controller.mods
            ] == mods, "Mods didn't load correctly on subsequent session"

            # check downloads are the same
            assert [
                (i.name, i.location) for i in controller.downloads
            ] == downloads, "Downloads didn't load correctly on subsequent session"

            # check plugins are the same
            assert [
                (i.name, i.enabled) for i in controller.plugins
            ] == plugins, "Plugins didn't load correctly on subsequent session"


def test_controller_enabled_mod_is_missing_plugin():
    """
    Test that when an enabled mod has an enabled plugin when ammo starts,
    the plugin appears as disabled if the plugin's symlink is missing.
    """
    with AmmoController() as first_launch:
        index = install_mod(first_launch, "conflict_1")

        mod = first_launch.mods[index]
        assert mod.enabled is True
        plugin = first_launch.plugins[index]
        assert plugin.enabled is True
        file = first_launch.game.directory / "Data/mock_plugin.esp"
        assert file.exists() is True
        file.unlink()

        with AmmoController() as controller:
            mod = controller.mods[index]
            assert mod.enabled is True
            plugin = controller.plugins[index]

            assert len(controller.plugins) == 1
            assert plugin.enabled is False


def test_controller_enabled_plugin_is_broken_symlink():
    """
    Test that when an enabled plugin's symlink points at a non-existing file,
    the plugin is not shown.
    """
    with AmmoController() as first_launch:
        index = install_mod(first_launch, "conflict_1")
        mod = first_launch.mods[index]
        plugin = first_launch.plugins[0]

        file = [i for i in mod.files if i.name == "mock_plugin.esp"][0]
        file.unlink()

        with AmmoController() as controller:
            mod = controller.mods[index]
            assert mod.enabled is True
            assert len(controller.plugins) == 0


def test_controller_disabled_broken_mod_enabled_plugin():
    """
    Test that a disabled mod with an enabled plugin doesn't
    automatically enable the mod if the mod was installed incorrectly.
    This can happen if a user manually edits their config and has a broken
    mod or the  mod is overwritten.
    """
    with AmmoController() as first_launch:
        install_mod(first_launch, "conflict_1")
        index = install_mod(first_launch, "conflict_2")

        with open(first_launch.game.ammo_conf, "w") as file:
            # conflict_2 is the conflict winner, but it is set disabled.
            for enabled, mod in zip(["*", ""], first_launch.mods):
                file.write(f"{enabled}{mod.name}\n")

        mod = first_launch.mods[index]
        file = first_launch.game.directory / "Data/textures/mock_texture.nif"
        file.unlink()

        with AmmoController() as controller:
            conflict_1 = controller.mods[
                [i.name for i in controller.mods].index("conflict_1")
            ]

            conflict_2 = controller.mods[
                [i.name for i in controller.mods].index("conflict_2")
            ]
            assert conflict_1.enabled is True
            assert conflict_2.enabled is False
            plugin = controller.plugins[0]
            assert plugin.enabled is True


def test_controller_missing_mod():
    """
    Test that a mod which is specified in ammo.conf but can't be
    found (because it was deleted from ammo's mod dir) isn't added
    to mods.
    """
    with AmmoController() as first_launch:
        index = install_mod(first_launch, "normal_mod")
        mod = first_launch.mods[index]
        shutil.rmtree(mod.location)

        with AmmoController() as controller:
            assert len(controller.mods) == 0


def test_controller_plugin_without_mod():
    """
    Test that a plugin in Plugins.txt that doesn't have an associated
    mod is added if Data/<plugin_name> exists and isn't a symlink.
    """
    # Get a plugin install location and plugin conf file location
    plugin = None
    plugin_file = None
    with AmmoController() as controller:
        plugin = controller.game.data / "normal_plugin.esp"
        plugin_file = controller.game.plugin_file

    try:
        # Create a plugin that's not associated with a mod and isn't a symlink.
        Path.mkdir(plugin.parent, parents=True, exist_ok=True)
        with open(plugin, "w") as esp:
            esp.write("")

        # Add the plugin to Plugins.txt as enabled.
        Path.mkdir(plugin_file.parent, parents=True, exist_ok=True)
        with open(plugin_file, "w") as plugin_txt:
            plugin_txt.write("* normal_plugin.esp")

        # Test that the plugin is added.
        with AmmoController() as controller:
            assert len(controller.plugins) == 1

    finally:
        try:
            plugin.unlink()
        except FileNotFoundError:
            pass


def test_controller_plugin_without_mod_is_link():
    """
    Test that a plugin in Plugins.txt that doesn't have an associated
    mod isn't added if Data/<plugin_name> exists and is a symlink.
    """
    # Get a plugin install location and plugin conf file location
    plugin = None
    plugin_file = None
    with AmmoController() as controller:
        plugin = controller.game.data / "normal_plugin.esp"
        plugin_file = controller.game.plugin_file

    try:
        # Create a plugin that's not associated with a mod and is a symlink.
        # Point the symlink at /dev/null.
        Path.mkdir(plugin.parent, parents=True, exist_ok=True)
        dev_null = Path("/dev/null")
        assert dev_null.exists()

        plugin.symlink_to(dev_null)
        assert plugin.exists()

        # Add the plugin to Plugins.txt as enabled.
        Path.mkdir(plugin_file.parent, parents=True, exist_ok=True)
        with open(plugin_file, "w") as plugin_txt:
            plugin_txt.write("* normal_plugin.esp")

        # Test that the plugin is not added.
        with AmmoController() as controller:
            assert len(controller.plugins) == 0

    finally:
        try:
            plugin.unlink()
        except FileNotFoundError:
            pass


def test_controller_plugin_without_mod_or_file():
    """
    Test that a plugin in Plugins.txt that doesn't have an associated
    mod isn't added if Data/<plugin_name> doesn't exist.
    """
    # Get a plugin install location and plugin conf file location
    plugin = None
    plugin_file = None
    with AmmoController() as controller:
        plugin = controller.game.data / "normal_plugin.esp"
        plugin_file = controller.game.plugin_file

    # Add the plugin to Plugins.txt as enabled.
    Path.mkdir(plugin_file.parent, parents=True, exist_ok=True)
    with open(plugin_file, "w") as plugin_txt:
        plugin_txt.write("* normal_plugin.esp")

    # Test that the plugin is not added.
    with AmmoController() as controller:
        assert len(controller.plugins) == 0


def test_controller_dlc_deactivated():
    """
    Test that a plugin in dlcList.txt is not considered activated
    when it is not present in Plugins.txt.
    """
    plugin = None
    dlc_file = None
    with AmmoController() as controller:
        plugin = controller.game.data / "normal_plugin.esp"
        dlc_file = controller.game.dlc_file

    # Add the plugin to DLCList.txt.
    Path.mkdir(dlc_file.parent, parents=True, exist_ok=True)
    with open(dlc_file, "w") as dlc_txt:
        dlc_txt.write("normal_plugin.esp")

    try:
        # Create a fake normal_plugin.esp file.
        Path.mkdir(plugin.parent, parents=True, exist_ok=True)
        with open(plugin, "w") as normal_plugin:
            normal_plugin.write("")

        # Test that the plugin loads as disabled
        with AmmoController() as controller:
            assert controller.plugins[0].name == "normal_plugin.esp"
            assert controller.plugins[0].enabled is False
    finally:
        try:
            plugin.unlink()
        except FileNotFoundError:
            pass


def test_controller_dlc_activated():
    """
    Test that a plugin in dlcList.txt is considered activated when
    it is also present in Plugins.txt. Ammo conditionally expects
    the plugin to start with an asterisk. Some titles require this,
    others require the plain filename of the plugin without prefix.
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

        # Test that the plugin loads as disabled
        with AmmoController() as controller:
            assert controller.plugins[0].name == "normal_plugin.esp"
            assert controller.plugins[0].enabled is True
    finally:
        try:
            plugin.unlink()
        except FileNotFoundError:
            pass


def test_controller_save_dlc():
    """
    Test that saving DLC doesn't swap the enabled state.
    This is needed because DLC plugins in Plugins.txt are either absent or begin with an asterisk
    in Plugins.txt if they're deactivated, and have no prefix and are present if they're activated.
    This is the opposite of how normal mods work.
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
        plugin_txt.write("normal_plugin.esp")

    try:
        # Create a fake normal_plugin.esp file.
        Path.mkdir(plugin.parent, parents=True, exist_ok=True)
        with open(plugin, "w") as normal_plugin:
            normal_plugin.write("")

        # Test that the plugin loads as disabled
        with AmmoController() as controller:
            assert controller.plugins[0].name == "normal_plugin.esp"
            assert controller.plugins[0].enabled is False
            controller.commit()
            controller.refresh()
            assert controller.plugins[0].enabled is False
    finally:
        try:
            plugin.unlink()
        except FileNotFoundError:
            pass
