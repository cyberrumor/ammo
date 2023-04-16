#!/usr/bin/env python3
import pytest
from common import (
    AmmoController,
    install_everything,
    install_normal_mod_active,
    install_normal_mod_inactive,
)


def test_pending_change_restrictions():
    """
    Actions that require the persistent state and in-memory state to be the
    same should not be possible to perform when there are pending changes.

    Test that the commands configure, delete, and install are blocked.
    """
    with AmmoController() as controller:
        install_normal_mod_active(controller)
        controller.changes = True

        with pytest.raises(AssertionError):
            controller.delete("mod", 0)

        with pytest.raises(AssertionError):
            controller.install(1)


def test_pending_change_move():
    """
    Tests that a move operation creates a pending change.
    """
    with AmmoController() as controller:
        install_everything(controller)
        controller.move("mod", 0, 1)
        assert (
            controller.changes is True
        ), "move command did not create a pending change"


def test_pending_change_activate():
    """
    Tests that an activate operation creates a pending change,
    unless it's to activate a component that was already activated.
    """
    with AmmoController() as controller:
        install_normal_mod_active(controller)
        controller.activate("mod", 0)
        assert (
            controller.changes is False
        ), "activate command created a pending change when it shouldn't have."

    with AmmoController() as controller:
        install_normal_mod_inactive(controller)
        controller.activate("mod", 0)
        assert (
            controller.changes is True
        ), "activate command failed to create a pending change."


def test_pending_change_deactivate():
    """
    Tests that a deactivate command creates a pending change,
    unless it's to deactivate an inactive component.
    """
    with AmmoController() as controller:
        install_normal_mod_inactive(controller)
        controller.deactivate("mod", 0)
        assert (
            controller.changes is False
        ), "deactivate command created a pending change when it shouldn't have."

    with AmmoController() as controller:
        install_normal_mod_active(controller)
        controller.deactivate("mod", 0)
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


def test_pending_change_delete():
    """
    Tests that delete does not create a pending change.
    """
    with AmmoController() as controller:
        install_normal_mod_active(controller)
        controller.delete("mod", 0)
        assert controller.changes is False, "Delete command created a pending change."
