#!/usr/bin/env python3
import textwrap
import pytest

from mod_common import (
    AmmoController,
    install_mod,
    extract_mod,
    install_everything,
)


def test_find_no_args_shows_all(mock_has_extra_folder):
    """
    Test that using the find command without arguments
    will cause all components to become visible.
    """
    with AmmoController() as controller:
        install_everything(controller)

        for i in controller.mods + controller.downloads:
            i.visible = False

        controller.do_find()

        for i in controller.mods + controller.downloads:
            assert i.visible is True


def test_find_install_all(mock_has_extra_folder):
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


def test_find_activate_all_mods(mock_has_extra_folder):
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


def test_find_deactivate_all_mods(mock_has_extra_folder):
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


def test_find_delete_all_mods(mock_has_extra_folder):
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


def test_find_filter_persists_after_refresh(mock_has_extra_folder):
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


def test_find_fomods(mock_has_extra_folder):
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


def test_find_activate_hidden_component(mock_has_extra_folder):
    """
    Test that the activate command raises a warning
    when used against hidden components.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.do_find("no_match")

        with pytest.raises(Warning):
            controller.activate_mod(0)


def test_find_deactivate_hidden_component(mock_has_extra_folder):
    """
    Test that the deactivate command raises a warning
    when used against hidden components.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.do_find("no_match")

        with pytest.raises(Warning):
            controller.deactivate_mod(0)


def test_find_delete_hidden_component(mock_has_extra_folder):
    """
    Test that the delete command raises a warning
    when used against hidden components.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        controller.do_find("no_match")

        with pytest.raises(Warning):
            controller.delete_mod(0)

        with pytest.raises(Warning):
            controller.delete_download(0)


def test_find_message():
    """
    Test that when a filter is applied with the find command,
    there's a message indicating components are hidden.
    """
    expected = textwrap.dedent(
        """\
        A filter is applied with `find` which may hide components.
        Running commands against `all` components will only affect
        the ones you can see.
        Execute `find` without arguments to remove the filter.
        """
    )
    with AmmoController() as controller:
        # We start with no message or filter by default.
        assert str(controller).startswith(expected) is False

        # Upon applying a filter, we should see the message.
        controller.do_find("anything")
        assert str(controller).startswith(expected) is True

        # Removing the filter should remove the message.
        controller.do_find()
        assert str(controller).startswith(expected) is False


def test_find_downloads(mock_has_extra_folder):
    """
    Test that `find downloads` shows downloads but nothing else.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")

        controller.do_find("downloads")

        # Confirm all downloads are visible
        for download in controller.downloads:
            assert download.visible is True

        # Confirm all mods are hidden
        for mod in controller.mods:
            assert mod.visible is False
