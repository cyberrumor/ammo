#!/usr/bin/env python3
import argparse
import shutil
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from ammo.controller.game import (
    BethesdaGameSelection,
    GameController,
    GameSelection,
    OpenMWGameSelection,
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


def test_openmw_detected_native(ammo_dir, args, tmp_path):
    """
    Test that a native openmw.cfg under ~/.config/openmw makes ammo detect
    OpenMW as a manageable game, so users don't have to hand-write a custom
    game file for it.
    """
    home = tmp_path / "home"
    cfg = home / ".config/openmw/openmw.cfg"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('data="/games/Morrowind/Data Files"\n')

    expected = OpenMWGameSelection(
        name="OpenMW",
        directory=ammo_dir.resolve() / "OpenMW" / "data",
        cfg=cfg,
    )

    # Path.home is patched so detection is deterministic regardless of the
    # host, and manage_game is patched so a single detected game doesn't
    # launch the mod organizer.
    with (
        patch("ammo.controller.game.Path.home", return_value=home),
        patch("ammo.controller.game.GameController.manage_game", autospec=True),
    ):
        game_controller = GameController(args)

    # Verify get_openmw_games yields exactly the expected selection.
    assert list(game_controller.get_openmw_games(home)) == [expected]
    # Verify get_openmw_games was actually called during init, which caused
    # game_controller.games to be mutated.
    assert expected in game_controller.games


def test_openmw_detected_flatpak(ammo_dir, args, tmp_path):
    """
    Test that a flatpak openmw.cfg under ~/.var/app is detected too, mirroring
    how ammo already handles native vs flatpak Steam.
    """
    home = tmp_path / "home"
    cfg = home / ".var/app/org.openmw.OpenMW/config/openmw/openmw.cfg"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("")

    expected = OpenMWGameSelection(
        name="OpenMW",
        directory=ammo_dir.resolve() / "OpenMW" / "data",
        cfg=cfg,
    )

    with (
        patch("ammo.controller.game.Path.home", return_value=home),
        patch("ammo.controller.game.GameController.manage_game", autospec=True),
    ):
        game_controller = GameController(args)

    assert list(game_controller.get_openmw_games(home)) == [expected]
    assert expected in game_controller.games


def test_openmw_not_detected_without_cfg(ammo_dir, args, tmp_path):
    """
    Test that without an openmw.cfg, no OpenMW game is detected.
    """
    # A custom game so construction succeeds on a host with no other games.
    (ammo_dir / "MockGameTest.json").write_text('{"directory": "/tmp/MockGame"}')
    home = tmp_path / "home"
    home.mkdir()

    with (
        patch("ammo.controller.game.Path.home", return_value=home),
        patch("ammo.controller.game.GameController.manage_game", autospec=True),
    ):
        game_controller = GameController(args)

    assert list(game_controller.get_openmw_games(home)) == []
    assert "OpenMW" not in [i.name for i in game_controller.games]


def test_openmw_custom_json_wins_over_autodetect(ammo_dir, args, tmp_path):
    """
    Test that an explicit OpenMW.json custom game takes precedence over
    autodetection, so a user's hand-written configuration isn't duplicated
    or overridden.
    """
    (ammo_dir / "OpenMW.json").write_text('{"directory": "/tmp/custom_openmw"}')
    home = tmp_path / "home"
    cfg = home / ".config/openmw/openmw.cfg"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("")

    with (
        patch("ammo.controller.game.Path.home", return_value=home),
        patch("ammo.controller.game.GameController.manage_game", autospec=True),
    ):
        game_controller = GameController(args)

    # Exactly one OpenMW entry, and it's the custom one (a plain GameSelection
    # pointing at the JSON directory), not the autodetected OpenMWGameSelection.
    openmw_games = [i for i in game_controller.games if i.name == "OpenMW"]
    assert openmw_games == [
        GameSelection(name="OpenMW", directory=Path("/tmp/custom_openmw"))
    ]
