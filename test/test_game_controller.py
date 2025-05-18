#!/usr/bin/env python3
import argparse
import textwrap
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from ammo.controller.game import (
    GameController,
    GameSelection,
    BethesdaGameSelection,
)


@pytest.fixture
def ammo_dir():
    ammo_dir = Path("/tmp/ammo_test/")
    ammo_dir.mkdir(parents=True, exist_ok=True)

    yield ammo_dir

    shutil.rmtree(ammo_dir)


@pytest.fixture
def args(ammo_dir):
    result = argparse.Namespace(
        conf=ammo_dir,
        downloads=Path(__file__).parent / "Downloads",
        title=None,
        mods=None,
        tools=None,
    )
    yield result


def test_custom_selection(ammo_dir, args):
    """
    Test that a file like ~/.local/share/ammo/my_game.json
    which is formatted correctly produces a valid GameSelection.
    """
    game_json_file = ammo_dir / "MockGameTest.json"

    contents = textwrap.dedent(
        """
        {
            "directory": "/tmp/MockGame"
        }
        """
    )

    expected = GameSelection(name="MockGameTest", directory=Path("/tmp/MockGame"))

    with open(game_json_file, "w") as f:
        f.write(contents)

    with patch("ammo.controller.game.GameController.manage_game", autospec=True):
        game_controller = GameController(args)
    game_selections = list(game_controller.get_custom_games(game_controller.args.conf))

    # Verify the get_custom_games did exactly what we wanted.
    assert game_selections == [expected]
    # Verify that get_custom_games was actually called during init,
    # which caused game_controller.games to be mutated.
    assert expected in game_controller.games


def test_custom_selection_bethesda(ammo_dir, args):
    """
    Test that a file like ~/.local/share/ammo/Skyrim.json
    which is formatted correctly produces a valid BethesdaGameSelection.
    """
    game_json_file = ammo_dir / "Skyrim.json"

    contents = textwrap.dedent(
        """
        {
            "directory": "/tmp/MockGame",
            "data": "/tmp/MockGame/Data",
            "dlc_file": "/tmp/MockGame/Data/DLCList.txt",
            "plugin_file": "/tmp/MockGame/Data/Plugins.txt"
        }
        """
    )

    expected = BethesdaGameSelection(
        name="Skyrim",
        directory=Path("/tmp/MockGame/"),
        data=Path("/tmp/MockGame/Data/"),
        dlc_file=Path("/tmp/MockGame/Data/DLCList.txt"),
        plugin_file=Path("/tmp/MockGame/Data/Plugins.txt"),
    )

    with open(game_json_file, "w") as f:
        f.write(contents)

    with patch("ammo.controller.game.GameController.manage_game", autospec=True):
        game_controller = GameController(args)
    game_selections = list(game_controller.get_custom_games(game_controller.args.conf))

    # Verify the get_custom_games did exactly what we wanted.
    assert game_selections == [expected]
    # Verify that get_custom_games was actually called during init,
    # which caused game_controller.games to be mutated.
    assert expected in game_controller.games


def test_custom_selection_plural(ammo_dir, args):
    """
    Test that when multiple files like ~/.local/share/ammo/game.json
    are provided, each of them manifest as a game selection.
    """
    expected = [
        GameSelection(
            name="MockGameTest",
            directory=Path("/tmp/MockGame"),
        ),
        BethesdaGameSelection(
            name="Skyrim",
            directory=Path("/tmp/MockGame/"),
            data=Path("/tmp/MockGame/Data/"),
            dlc_file=Path("/tmp/MockGame/Data/DLCList.txt"),
            plugin_file=Path("/tmp/MockGame/Data/Plugins.txt"),
        ),
    ]

    game_json_file = ammo_dir / "Skyrim.json"
    contents = textwrap.dedent(
        """
        {
            "directory": "/tmp/MockGame",
            "data": "/tmp/MockGame/Data",
            "dlc_file": "/tmp/MockGame/Data/DLCList.txt",
            "plugin_file": "/tmp/MockGame/Data/Plugins.txt"
        }
        """
    )
    with open(game_json_file, "w") as f:
        f.write(contents)

    game_json_file = ammo_dir / "MockGameTest.json"
    contents = textwrap.dedent(
        """
        {
            "directory": "/tmp/MockGame"
        }
        """
    )

    with open(game_json_file, "w") as f:
        f.write(contents)

    game_controller = GameController(args)
    game_selections = list(game_controller.get_custom_games(game_controller.args.conf))

    # Verify the get_custom_games did exactly what we wanted.
    for game_selection in expected:
        assert game_selection in game_selections
    # Verify that get_custom_games was actually called during init,
    # which caused game_controller.games to be mutated.
    for game_selection in expected:
        assert game_selection in game_controller.games
