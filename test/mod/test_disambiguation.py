#!/usr/bin/env python3
from unittest.mock import patch

import pytest

from ammo.controller.mod import (
    ComponentMove,
    ComponentWrite,
)
from mod_common import (
    AmmoController,
    extract_mod,
)


@patch("ammo.controller.mod.ModController.activate_mod")
def test_disambiguation_activate_mod(mock_activate, mock_has_extra_folder):
    """
    Test that the controller.do_activate command defers to
    controller.activate_mod when it gets a mod as an argument,
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")
        controller.do_activate(ComponentMove.MOD, 0)
        mock_activate.assert_called_once()


def test_disambiguation_activate_garbage():
    """
    Test that the controller.do_activate command raises
    a warning if it doesn't get an expected component type.
    """
    with AmmoController() as controller:
        with pytest.raises(Warning):
            controller.do_activate("bogus_string", 0)


@patch("ammo.controller.mod.ModController.deactivate_mod")
def test_disambiguation_deactivate_mod(mock_deactivate, mock_has_extra_folder):
    """
    Test that the controller.do_deactivate command defers to
    controller.deactivate_mod when it gets a mod as an argument,
    and raises a warning for any other argument.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")
        controller.do_deactivate(ComponentMove.MOD, 0)
        mock_deactivate.assert_called_once()


def test_disambiguation_deactivate_garbage():
    with AmmoController() as controller:
        with pytest.raises(Warning):
            controller.do_deactivate("bogus_string", 0)


@patch("ammo.controller.mod.ModController.delete_mod")
def test_disambiguation_delete_mod(mock_delete, mock_has_extra_folder):
    """
    Test that the controller.do_delete command defers to
    controller.delete_mod when it gets a mod as an argument.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")
        controller.do_delete(ComponentWrite.MOD, 0)

        mock_delete.assert_called_once()


@patch("ammo.controller.mod.ModController.delete_download")
def test_disambiguation_delete_download(mock_delete):
    """
    Test that the controller.do_delete command defers to
    controller.delete_downlaod when it gets a download as an arg.
    """
    with AmmoController() as controller:
        controller.do_delete(ComponentWrite.DOWNLOAD, 0)
        mock_delete.assert_called_once()


def test_disambiguation_delete_garbage():
    """
    Test that the controller.do_delete command raises a warning
    when it doesn't get an expected component type.
    """
    with AmmoController() as controller:
        with pytest.raises(Warning):
            controller.do_delete("bogus_string", 0)


@patch("ammo.controller.mod.ModController.move_mod")
def test_disambiguation_move_mod(mock_move, mock_has_extra_folder):
    """
    Test that the controller.do_move command defers to
    controller.move_mod when it gets a mod as an arg.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")
        controller.do_move(ComponentMove.MOD, 0, 1)
        mock_move.assert_called_once()


def test_disambiguation_move_garbage():
    """
    Test that the controller.do_move command raises
    a warning when it gets an unexpected component type.
    """
    with AmmoController() as controller:
        with pytest.raises(Warning):
            controller.do_move("bogus_string", 0, 1)


@patch("ammo.controller.mod.ModController.rename_download")
def test_disambiguation_rename_download(mock_rename):
    """
    Test that the controller.do_rename command defers to
    controller.rename_download when ti gets a download as an arg.
    """
    with AmmoController() as controller:
        controller.do_rename(ComponentWrite.DOWNLOAD, 0, "new_name")
        mock_rename.assert_called_once()


@patch("ammo.controller.mod.ModController.rename_mod")
def test_disambiguation_rename_mod(mock_rename):
    """
    Test that the controller.do_rename command defers to
    controller.rename_download when it gets a download as an arg.
    """
    with AmmoController() as controller:
        controller.do_rename(ComponentWrite.MOD, 0, "new_name")
        mock_rename.assert_called_once()


def test_disambiguation_rename_garbage():
    """
    Test that the controller.do_rename command raises a warning
    when it gets an unexpected component.
    """
    with AmmoController() as controller:
        with pytest.raises(Warning):
            controller.do_rename("bogus_string", 0, "new_name")
