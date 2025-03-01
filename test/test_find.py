#!/usr/bin/env python3
from common import (
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

        for i in controller.mods + controller.downloads:
            i.visible = False

        controller.do_find()

        for i in controller.mods + controller.downloads:
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
        controller.do_activate_mod("all")

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
        controller.do_deactivate_mod("all")

        assert set([i.name for i in controller.mods if i.enabled]) == set(
            ["normal_mod"]
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
        controller.do_delete_mod("all")

        assert set([i.name for i in controller.mods]) == set(["no_data_folder_plugin"])


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
