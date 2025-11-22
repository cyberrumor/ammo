#!/usr/bin/env python3
import os
import shutil
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from ammo.controller.tool import (
    ToolController,
    ComponentWrite,
)
from test.mod.mod_common import (
    AMMO_DIR,
    GAME,
)


@pytest.fixture
def mock_tool_has_extra_folder():
    has_extra_folder = True
    with patch.object(
        ToolController, "has_extra_folder", return_value=has_extra_folder
    ) as _mock_tool_has_extra_folder:
        yield

    _mock_tool_has_extra_folder.assert_called()


def extract_tool(controller, tool_name: str):
    """
    Helper function that installs a tool by name.

    Returns the index the tool inhabits.
    """
    index = [i.location.name for i in controller.downloads].index(f"{tool_name}.7z")
    controller.do_install(index)
    try:
        tool_index = [i.path.name for i in controller.tools].index(tool_name)
        return tool_index
    except ValueError:
        # tool_name was not in the list. Print the list.
        print(f"{tool_name} was not in {[i.path.name for i in controller.tools]}")


class AmmoToolController:
    """
    Context manager for ammo's ToolController class.

    Builds a ToolController instance to run against /tmp/MockGame.
    Ammo's configuration directory will be set up as AMMO_DIR,
    if it doesn't already exist.

    Removes those folders on exit or error. Raises AssertionError
    after exit logic if there were broken symlinks.
    """

    def __init__(self):
        self.game = GAME
        script_path = Path(__file__)
        self.downloads_dir = script_path.parent / "Downloads"

    def __enter__(self):
        """
        Return an instance of ammo's controller for tests to
        interact with.
        """
        return ToolController(self.downloads_dir, self.game)

    def __exit__(self, *args, **kwargs):
        """
        Remove all the files and folders associated with our mock
        ammo instance. This ensures no reliance on a state
        created by a previous test.
        """
        broken_symlinks = {}
        # remove symlinks
        for dirpath, _dirnames, filenames in os.walk(self.game.directory):
            for file in filenames:
                full_path = Path(dirpath) / file
                if full_path.is_symlink():
                    if (dest := full_path.resolve()).exists() is False:
                        broken_symlinks[str(full_path)] = str(dest)
                    full_path.unlink()

        # remove empty directories
        def remove_empty_dirs(path):
            for dirpath, dirnames, _filenames in list(os.walk(path, topdown=False)):
                for dirname in dirnames:
                    try:
                        Path(dirpath, dirname).rmdir()
                    except OSError:
                        # directory wasn't empty, ignore this
                        pass

        if self.game.directory.exists():
            remove_empty_dirs(self.game.directory)
        if self.game.directory.exists():
            shutil.rmtree(self.game.directory)
        if AMMO_DIR.exists():
            shutil.rmtree(AMMO_DIR)

        assert {} == broken_symlinks


@patch("ammo.controller.tool.ToolController.delete_tool")
def test_disambiguation_delete_tool(mock_delete, mock_tool_has_extra_folder):
    """
    Test that controller.do_delete defers to controller.delete_tool
    when it gets a tool as an arg.
    """
    with AmmoToolController() as controller:
        extract_tool(controller, "normal_mod")
        controller.do_delete(ComponentWrite.TOOL, 0)
        mock_delete.assert_called_once()


@patch("ammo.controller.tool.ToolController.delete_download")
def test_disambiguation_delete_download(mock_delete):
    """
    Test that controller.do_delete defers to controller.delete_download
    when it gets a download as an arg.
    """
    with AmmoToolController() as controller:
        controller.do_delete(ComponentWrite.DOWNLOAD, 0)
        mock_delete.assert_called_once()


def test_disambiguation_delete_garbage():
    """
    Test that controller.do_delete raises a warning when it gets
    an unexpected component.
    """
    with AmmoToolController() as controller:
        with pytest.raises(Warning):
            controller.do_delete("bogus_string", 0)


@patch("ammo.controller.tool.ToolController.rename_tool")
def test_disambiguation_rename_tool(mock_rename, mock_tool_has_extra_folder):
    """
    Test that controller.do_rename defers to controller.rename_tool
    when it gets tool as an arg.
    """
    with AmmoToolController() as controller:
        extract_tool(controller, "normal_mod")
        controller.do_rename(ComponentWrite.TOOL, 0, "new_name")
        mock_rename.assert_called_once()


@patch("ammo.controller.tool.ToolController.rename_download")
def test_disambiguation_rename_download(mock_rename):
    """
    Test that controller.do_rename defers to controller.rename_download
    when it gets download as an arg.
    """
    with AmmoToolController() as controller:
        controller.do_rename(ComponentWrite.DOWNLOAD, 0, "new_name")
        mock_rename.assert_called_with(0, "new_name")


def test_disambiguation_rename_garbage():
    """
    Test that controller.rename raises a warning when it gets
    an unexpected component.
    """
    with AmmoToolController() as controller:
        with pytest.raises(Warning):
            controller.do_rename("bogus_string", 0, "new_name")


def test_rename_tool(mock_tool_has_extra_folder):
    """
    Test that controller.rename_tool works.
    """
    with AmmoToolController() as controller:
        original_path = Path(controller.game.ammo_tools_dir) / "normal_mod"
        new_path = Path(controller.game.ammo_tools_dir) / "new_name"

        extract_tool(controller, "normal_mod")

        assert original_path.exists() is True
        assert new_path.exists() is False

        controller.rename_tool(0, "new_name")

        assert original_path.exists() is False
        assert new_path.exists() is True


def test_tool_controller_str(mock_tool_has_extra_folder):
    """
    Test that the tool controller looks the way we expect it to.
    """
    expected = textwrap.dedent(
        """
         index | Tool
        -------|----------
        [0]     edit_scripts
        [1]     normal_mod
        """
    )
    with AmmoToolController() as controller:
        # Tools get ordered alphabetically, not by install order.
        # This ensures the same order persists through different sessions.
        extract_tool(controller, "normal_mod")
        extract_tool(controller, "edit_scripts")

        assert str(controller).endswith(expected)
