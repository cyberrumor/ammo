#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import textwrap

import pytest

from bethesda_common import (
    AmmoController,
    extract_mod,
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
        assert os.path.exists(game_dir), (
            f"game_dir {game_dir} did not exist after the controller started."
        )

        data_dir = controller.game.data
        assert os.path.exists(data_dir), (
            f"data_dir {data_dir} did not exist after the controller started."
        )

        downloads_dir = controller.downloads_dir
        assert os.path.exists(downloads_dir), (
            f"downloads_dir {downloads_dir} did not exist after the controller started."
        )

        conf_dir = os.path.split(controller.game.ammo_conf)[0]
        assert os.path.exists(conf_dir), (
            f"ammo_dir {conf_dir} did not exist after the controller started."
        )

    assert not os.path.exists(game_dir), (
        f"game_dir {game_dir} was not removed after context manager closed"
    )

    assert not os.path.exists(data_dir), (
        f"data dir {data_dir} was not removed after context manager closed"
    )

    assert os.path.exists(downloads_dir), (
        f"downloads_dir {downloads_dir} was deleted after context manager closed.\
        It would be a good time to `git checkout Downloads`"
    )

    assert not os.path.exists(conf_dir), (
        f"ammo_dir {conf_dir} existed after the context manager closed."
    )


def test_controller_subsequent_launch():
    """
    Ensure ammo behaves correctly when launched against a game
    that already has mods installed, Plugins.txt populated with
    a non-default order, etc.
    """
    with AmmoController() as first_launch:
        install_everything(first_launch)

        # change some config to ensure it's not just alphabetic
        first_launch.move_plugin(0, 2)
        first_launch.move_mod(2, 0)
        first_launch.deactivate_mod(1)
        first_launch.deactivate_plugin(4)
        first_launch.do_commit()

        mods = [(i.name, i.location, i.enabled) for i in first_launch.mods]
        downloads = [(i.name, i.location) for i in first_launch.downloads]
        plugins = [(i.name, i.enabled) for i in first_launch.plugins]

        # Launch the second instance of ammo against this configuration.
        with AmmoController() as controller:
            # check mods are the same
            assert [(i.name, i.location, i.enabled) for i in controller.mods] == mods, (
                "Mods didn't load correctly on subsequent session"
            )

            # check downloads are the same
            assert [(i.name, i.location) for i in controller.downloads] == downloads, (
                "Downloads didn't load correctly on subsequent session"
            )

            # check plugins are the same
            assert [(i.name, i.enabled) for i in controller.plugins] == plugins, (
                "Plugins didn't load correctly on subsequent session"
            )


def test_controller_plugin_not_referenced():
    """
    Test that when a plugin is absent from plugins.txt and dlclist.txt
    but present in a mod directory, it's still added to self.plugins.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        assert len(controller.plugins) == 1
        assert controller.plugins[0].name == "normal_plugin.esp"

        new_plugin = (
            controller.game.ammo_mods_dir / "normal_mod" / "Data" / "new_plugin.esp"
        )
        new_plugin.touch()

        controller.do_refresh()
        assert len(controller.plugins) == 2
        assert controller.plugins[1].name == "new_plugin.esp"


def test_controller_move():
    """
    Test that moving a mod or plugin to a new position causes the
    components between the old location and the new location to collapse
    (take out at old location, insert at new location), rather than
    causing the old location and new location components to merely swap.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "mock_conflict_1")
        install_mod(controller, "mock_conflict_2")
        install_mod(controller, "multiple_plugins")

        assert controller.mods[0].name == "normal_mod"
        assert controller.mods[1].name == "mock_conflict_1"
        assert controller.mods[2].name == "mock_conflict_2"
        assert controller.mods[3].name == "multiple_plugins"

        controller.move_mod(1, 3)
        assert controller.mods[0].name == "normal_mod"
        assert controller.mods[1].name == "mock_conflict_2"
        assert controller.mods[2].name == "multiple_plugins"
        assert controller.mods[3].name == "mock_conflict_1"


def test_controller_enabled_mod_is_missing_plugin():
    """
    Test that when an enabled mod has an enabled plugin when ammo starts,
    the plugin appears as disabled if the plugin's symlink is missing.
    """
    with AmmoController() as first_launch:
        index = install_mod(first_launch, "mock_conflict_1")

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
    with pytest.raises(AssertionError):
        with AmmoController() as first_launch:
            index = install_mod(first_launch, "mock_conflict_1")
            mod = first_launch.mods[index]
            plugin = first_launch.plugins[0]

            file = [src for dest, src in mod.files.items() if src.name == plugin.name][
                0
            ]
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
        install_mod(first_launch, "mock_conflict_1")
        index = install_mod(first_launch, "mock_conflict_2")

        with open(first_launch.game.ammo_conf, "w") as file:
            # mock_conflict_2 is the conflict winner, but it is set disabled.
            for enabled, mod in zip(["*", ""], first_launch.mods):
                file.write(f"{enabled}{mod.name}\n")

        mod = first_launch.mods[index]
        file = first_launch.game.directory / "Data/textures/mock_texture.nif"
        file.unlink()

        with AmmoController() as controller:
            mock_conflict_1 = controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_1")
            ]

            mock_conflict_2 = controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_2")
            ]
            assert mock_conflict_1.enabled is True
            assert mock_conflict_2.enabled is False
            plugin = controller.plugins[0]
            assert plugin.enabled is True


def test_controller_missing_mod():
    """
    Test that a mod which is specified in ammo.conf but can't be
    found (because it was deleted from ammo's mod dir) isn't added
    to mods.
    """
    with pytest.raises(AssertionError):
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
    plugin_file = None
    with AmmoController() as controller:
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
            controller.do_commit()
            controller.do_refresh()
            assert controller.plugins[0].enabled is False
    finally:
        try:
            plugin.unlink()
        except FileNotFoundError:
            pass


def test_controller_deactivate_mod_with_multiple_plugins():
    """
    Test that disabling a mod that contains multiple plugins actually
    causes all of that mod's plugins to disappear.
    """
    with AmmoController() as controller:
        install_mod(controller, "multiple_plugins")
        # Make sure all plugins are there.
        assert len(controller.plugins) == 3

        # Deactivate the mod
        controller.deactivate_mod(0)

        # Ensure all plugins are absent.
        assert len(controller.plugins) == 0


def test_controller_delete_plugin():
    """
    Test that deleting a plugin removes the plugin from
    the parent mod's files somewhere under ~/.local/share/ammo
    and doesn't leave a broken symlink in the game dir.

    Tests that it doesn't delete files if they weren't loaded as plugins
    (like .esp files that weren't under Data).
    """
    with AmmoController() as controller:
        # Install a mod with a plugin, ensure the plugin is there.
        install_mod(controller, "mult_plugins_same_name")
        assert len(controller.plugins) == 1

        # Delete the plugin, make sure it's gone.
        controller.delete_plugin(0)
        assert len(controller.plugins) == 0

        # reinitialize the mod to force a rescan of its files.
        controller.deactivate_mod(0)
        controller.activate_mod(0)
        # Ensure the plugin hasn't returned.
        assert len(controller.plugins) == 0

        # Ensure we didn't delete .esp files that weren't under Data
        assert (
            controller.game.ammo_mods_dir
            / "mult_plugins_same_name/Data/test/plugin.esp"
        ).exists()
        assert (controller.game.data / "test/plugin.esp").exists()


def test_controller_plugin_wrong_spot():
    """
    Test that a plugin which isn't under Data or the root
    directory of a mod doesn't appear in mod.plugins.
    """
    with AmmoController() as controller:
        extract_mod(controller, "plugin_wrong_spot")
        assert controller.mods[0].plugins == []
        controller.activate_mod(0)
        assert controller.mods[0].plugins == []
        controller.deactivate_mod(0)
        assert controller.mods[0].plugins == []
        controller.do_commit()
        assert controller.mods[0].plugins == []
        controller.rename_mod(0, "new_name")
        assert controller.mods[0].plugins == []


def test_no_delete_all_if_mod_active():
    """
    It's not the first time I've done this on accident, but
    it will be the last. Test that deleting all mods fails if
    any visible mod is still enabled. In other words, deleting
    all mods is only allowed if all visible mods are inactive.
    """
    with AmmoController() as controller:
        install_mod(controller, "mock_conflict_1")
        extract_mod(controller, "mock_conflict_2")

        expected = "You must deactivate all visible components of that type before deleting them with all."

        with pytest.raises(Warning) as warning:
            controller.delete_mod("all")
            assert warning.value.args == (expected,)


def test_no_delete_all_if_plugin_active():
    """
    Test that all target plugins are deactivated before
    deleting them with all. If there's an active one,
    prompt the user to deactivate it before allowing this operation.
    """
    with AmmoController() as controller:
        install_mod(controller, "mock_conflict_1")
        install_mod(controller, "normal_mod")
        controller.activate_plugin(1)

        expected = "You must deactivate all visible components of that type before deleting them with all."

        with pytest.raises(Warning) as warning:
            controller.delete_plugin("all")
            assert warning.value.args == (expected,)


def test_sort_esm_esl():
    """
    Test that .esl and .esm plugins are auto-sorted to
    before .esp plugins from the 'sort' command.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "esm")
        install_mod(controller, "esl")
        install_mod(controller, "mock_conflict_1")

        assert controller.plugins[0].name == "normal_plugin.esp"
        assert controller.plugins[1].name == "plugin.esm"
        assert controller.plugins[2].name == "plugin.esl"
        assert controller.plugins[3].name == "mock_plugin.esp"

        controller.do_sort()

        assert controller.plugins[0].name == "plugin.esm"
        assert controller.plugins[1].name == "plugin.esl"
        assert controller.plugins[2].name == "normal_plugin.esp"
        assert controller.plugins[3].name == "mock_plugin.esp"


def test_sort_dlc():
    """
    Test that DLC (plugins where plugin.mod is None) gets sorted
    above other plugins.
    """
    with AmmoController() as controller:
        install_mod(controller, "esm")
        install_mod(controller, "esl")

        # Create a file which will behave as a DLC plugin
        with open(controller.game.data / "dlc.esm", "w") as f:
            f.write("")

        # Create a DLCPlugins.txt file so it will get loaded by
        # a refresh. Another way to get a file to be considered
        # DLC for the purposes of 'sort' is to set plugin.mod to
        # None, but we don't have enough .esm mods available to
        # test with via that method.
        with open(controller.game.dlc_file, "w") as f:
            f.write("*dlc.esm")

        controller.do_refresh()
        assert controller.plugins[0].name == "plugin.esm"
        assert controller.plugins[1].name == "plugin.esl"
        # DLC which wasn't in plugins.txt goes to the bottom as disabled.
        assert controller.plugins[2].name == "dlc.esm"

        controller.do_sort()

        assert controller.plugins[0].name == "dlc.esm"
        assert controller.plugins[1].name == "plugin.esm"
        assert controller.plugins[2].name == "plugin.esl"


def test_dlc_order():
    """
    Test that DLC gets loaded at the bottom of controller.plugins
    as disabled if it wasn't listed in plugins.txt.

    If it's listed in plugins.txt, it should get loaded in that order
    as enabled/disabled according to plugins.txt enabled state.
    """

    with AmmoController() as controller:
        install_mod(controller, "esm")
        install_mod(controller, "esl")

        # Create a file which will behave as a DLC plugin
        with open(controller.game.data / "dlc.esm", "w") as f:
            f.write("")

        # Create a DLCPlugins.txt file so it will get loaded by
        # a refresh. Another way to get a file to be considered
        # DLC for the purposes of 'sort' is to set plugin.mod to
        # None, but we don't have enough .esm mods available to
        # test with via that method.
        with open(controller.game.dlc_file, "w") as f:
            f.write("*dlc.esm")

        controller.do_refresh()
        assert controller.plugins[0].name == "plugin.esm"
        assert controller.plugins[1].name == "plugin.esl"
        # DLC which wasn't in plugins.txt goes to the bottom as disabled.
        assert controller.plugins[2].name == "dlc.esm"

        # Enable and move the DLC
        controller.activate_plugin(2)
        controller.move_plugin(2, 1)
        controller.do_commit()

        controller.do_refresh()

        assert controller.plugins[1].name == "dlc.esm"


def test_bethesda_controller_str():
    """
    Test that the BethesdaController looks the way we expect.
    """
    expected = textwrap.dedent(
        """\
         index | Active | Mod name
        -------|--------|------------
        [0]     [True]    normal_mod
        [1]     [True]    no_data_folder_plugin
        [2]     [False]   mock_conflict_1

         index | Active | Plugin name
        -------|--------|------------
        [0]     [True]    normal_plugin.esp
        [1]     [False]   no_data_folder_plugin.esp
        """
    )

    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "no_data_folder_plugin")
        extract_mod(controller, "mock_conflict_1")
        controller.deactivate_plugin(-1)

        assert str(controller).endswith(expected)
