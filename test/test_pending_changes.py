#!/usr/bin/env python3
import pytest

from ammo.component import (
    BethesdaComponentActivatable,
    BethesdaComponent,
    Component,
)
from common import (
    AmmoController,
    install_mod,
    extract_mod,
)


def test_pending_change_restrictions_delete_mod():
    """
    Actions that require the persistent state and in-memory state to be the
    same should not be possible to perform when there are pending changes.

    Test delete mod.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.changes = True

        with pytest.raises(Warning):
            controller.delete(BethesdaComponent.MOD, 0)


def test_pending_change_restrictions_delete_download():
    """
    Actions that require the persistent state and in-memory state to be the
    same should not be possible to perform when there are pending changes.

    Test delete download.
    """
    with AmmoController() as controller:
        # Create a temp download that we can manipulate,
        # just in case we're not restricted from deleting it.
        # Don't want to mess up the expected files in test/Downloads.
        temp_download = controller.downloads_dir / "temp_download.7z"
        with open(temp_download, "w") as f:
            f.write("")

        controller.refresh()
        controller.changes = True

        download_index = [i.name for i in controller.downloads].index(
            "temp_download.7z"
        )

        try:
            with pytest.raises(Warning):
                controller.delete(BethesdaComponent.DOWNLOAD, download_index)
        finally:
            temp_download.unlink(missing_ok=True)


def test_pending_change_restrictions_delete_plugin():
    """
    Actions that require the persistent state and in-memory state to be the
    same should not be possible to perform when there are pending changes.

    Test delete plugin.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.changes = True

        with pytest.raises(Warning):
            controller.delete(BethesdaComponent.PLUGIN, 0)


def test_pending_change_restrictions_install():
    """
    Actions that require the persistent state and in-memory state to be the
    same should not be possible to perform when there are pending changes.

    Test install.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.changes = True
        with pytest.raises(Warning):
            controller.install(1)


def test_pending_change_restrictions_rename_mod():
    """
    Actions that require the persistent state and in-memory state to be the
    same should not be possible to perform when there are pending changes.

    Test rename mod.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.changes = True

        with pytest.raises(Warning):
            controller.rename(Component.MOD, 0, "new_name")


def test_pending_change_restrictions_rename_download():
    """
    Actions that require the persistent state and in-memory state to be the
    same should not be possible to perform when there are pending changes.

    Test rename download.
    """
    with AmmoController() as controller:
        # Create a temp download that we can manipulate,
        # just in case we're not restricted from renaming it.
        # Don't want to mess up the expected files in test/Downloads.
        temp_download = controller.downloads_dir / "temp_download.7z"
        with open(temp_download, "w") as f:
            f.write("")

        controller.refresh()
        controller.changes = True

        download_index = [i.name for i in controller.downloads].index(
            "temp_download.7z"
        )

        try:
            with pytest.raises(Warning):
                controller.rename(
                    Component.DOWNLOAD, download_index, "new_download_name"
                )
        finally:
            temp_download.unlink(missing_ok=True)
            (controller.downloads_dir / "new_download_name.7z").unlink(missing_ok=True)


def test_pending_change_move():
    """
    Tests that a move operation creates a pending change.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "multiple_plugins")
        controller.move(BethesdaComponentActivatable.MOD, 0, 1)
        assert (
            controller.changes is True
        ), "move command did not create a pending change"


def test_pending_change_move_nowhere():
    """
    Tests that a move operation where <from> and <to>
    are the same doesn't create a pending change.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "multiple_plugins")
        controller.move(BethesdaComponentActivatable.MOD, 0, 0)
        assert (
            controller.changes is False
        ), "move command created a pending change when it shouldn't have."


def test_pending_change_activate():
    """
    Tests that an activate operation creates a pending change,
    unless it's to activate a component that was already activated.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.activate(BethesdaComponentActivatable.MOD, 0)
        assert (
            controller.changes is False
        ), "activate command created a pending change when it shouldn't have."

    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")
        controller.activate(BethesdaComponentActivatable.MOD, 0)
        assert (
            controller.changes is True
        ), "activate command failed to create a pending change."


def test_pending_change_deactivate():
    """
    Tests that a deactivate command creates a pending change,
    unless it's to deactivate an inactive component.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")
        controller.deactivate(BethesdaComponentActivatable.MOD, 0)
        assert (
            controller.changes is False
        ), "deactivate command created a pending change when it shouldn't have."

    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.deactivate(BethesdaComponentActivatable.MOD, 0)
        assert (
            controller.changes is True
        ), "deactivate command failed to create a pending change."


def test_pending_change_refresh():
    """
    Tests that the refresh command clears pending changes.
    """
    with AmmoController() as controller:
        controller.changes = True
        controller.refresh()
        assert (
            controller.changes is False
        ), "refresh command failed to clear pending changes."


def test_pending_change_commit():
    """
    Tests that the commit command clears pending changes.
    """
    with AmmoController() as controller:
        controller.changes = False
        controller.commit()
        assert (
            controller.changes is False
        ), "commit command failed to clear pending changes."


def test_pending_change_install():
    """
    Tests that install does not create a pending change.
    """
    with AmmoController() as controller:
        controller.install(0)
        assert controller.changes is False, "Install command created a pending change"


def test_pending_change_delete_mod():
    """
    Tests that delete does not create a pending change.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.delete(BethesdaComponent.MOD, 0)
        assert (
            controller.changes is False
        ), "Delete mod command created a pending change."


def test_pending_change_delete_download():
    """
    Tests that delete download does not create a pending change.
    """
    with AmmoController() as controller:
        temp_download = controller.downloads_dir / "temp_download.7z"
        with open(temp_download, "w") as f:
            f.write("")
        controller.refresh()

        download_index = [i.name for i in controller.downloads].index(
            "temp_download.7z"
        )

        try:
            controller.delete(BethesdaComponent.DOWNLOAD, download_index)
            assert (
                controller.changes is False
            ), "Delete download command created a pending change."
        finally:
            temp_download.unlink(missing_ok=True)
            (controller.downloads_dir / "new_download_name.7z").unlink(missing_ok=True)


def test_pending_change_delete_plugin():
    """
    Tests that delete plugin does not create a pending change.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.delete(BethesdaComponent.PLUGIN, 0)
        assert (
            controller.changes is False
        ), "Delete plugin command created a pending change."


def test_pending_change_rename_mod():
    """
    Tests that renaming a mod does not create a pending change.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.rename(Component.MOD, 0, "new_mod_name")
        assert (
            controller.changes is False
        ), "Rename mod command created a pending change."


def test_pending_change_rename_download():
    """
    Tests that renaming a download does not create a pending change.
    """
    # generate an expendable download file, delete
    # download in range.
    with AmmoController() as controller:
        temp_download = controller.downloads_dir / "temp_download.7z"
        with open(temp_download, "w") as f:
            f.write("")

        controller.refresh()

        download_index = [i.name for i in controller.downloads].index(
            "temp_download.7z"
        )

        try:
            controller.rename(Component.DOWNLOAD, download_index, "new_download_name")
            assert (
                controller.changes is False
            ), "Rename download command created a pending change."
        finally:
            temp_download.unlink(missing_ok=True)
            (controller.downloads_dir / "new_download_name.7z").unlink(missing_ok=True)


def test_pending_change_sort():
    """
    Tests that the 'sort' command creates a pending change.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "multiple_plugins")
        controller.move(BethesdaComponentActivatable.PLUGIN, 0, -1)
        controller.commit()
        controller.sort()
        assert (
            controller.changes is True
        ), "Sort command didn't create a pending change."


def test_pending_change_sort_no_op():
    """
    Test 'sort' doesn't create a pending change
    if it doesn't change the plugin load order.
    """
    with AmmoController() as controller:
        controller.sort()
        assert (
            controller.changes is False
        ), "Sort command created a pending change when it shouldn't have."
