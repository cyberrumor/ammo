#!/usr/bin/env python3
import shutil
from contextlib import contextmanager
from pathlib import Path

from ammo.component import OpenMWGame
from ammo.controller.openmw import OpenMWController

# OpenMW aggregates every directory listed via a data="..." line in
# openmw.cfg into one virtual file system. OpenMWController owns ONE
# such directory, stages every mod into it, and registers it with a
# single data= line on commit. These tests exercise that registration:
# it must be idempotent and must not disturb any other line in the file
# (the base game data, the plugin activation the OpenMW Launcher owns,
# fallback settings, comments).

OPENMW_TEST_ROOT = Path("/tmp/ammo_openmw_cfg_test")
# The ammo-owned data directory ammo stages mods into and registers.
DATA_DIR = OPENMW_TEST_ROOT / "OpenMW" / "data"
# A throwaway openmw.cfg standing in for ~/.config/openmw/openmw.cfg.
CFG = OPENMW_TEST_ROOT / "config" / "openmw.cfg"


def make_game() -> OpenMWGame:
    return OpenMWGame(
        name="OpenMW",
        directory=DATA_DIR,
        cfg=CFG,
        ammo_conf=OPENMW_TEST_ROOT / "OpenMW" / "ammo.conf",
        ammo_log=OPENMW_TEST_ROOT / "OpenMW" / "ammo.log",
        ammo_mods_dir=OPENMW_TEST_ROOT / "OpenMW" / "mods",
        ammo_tools_dir=OPENMW_TEST_ROOT / "OpenMW" / "tools",
    )


@contextmanager
def openmw_controller(cfg_contents: str | None = None):
    """
    Yield an OpenMWController whose install dir is an ammo-owned
    OpenMW data dir and whose cfg is a throwaway openmw.cfg seeded with
    cfg_contents (or left absent when None). Cleans up the whole test
    root on exit.
    """
    downloads_dir = Path(__file__).parent.parent / "Downloads"
    CFG.parent.mkdir(parents=True, exist_ok=True)
    if cfg_contents is not None:
        CFG.write_text(cfg_contents)
    try:
        yield OpenMWController(downloads_dir, make_game())
    finally:
        shutil.rmtree(OPENMW_TEST_ROOT, ignore_errors=True)


def test_commit_registers_data_line():
    """
    Test that committing appends ammo's data= line after the
    base game's, so OpenMW gives ammo's staged mods higher
    virtual-file-system priority.
    """
    base = 'data="/games/Morrowind/Data Files"\ncontent=Morrowind.esm\n'
    with openmw_controller(base) as controller:
        controller.do_commit()
        result = CFG.read_text()

    assert result == base + f'data="{DATA_DIR}"\n'


def test_commit_data_line_idempotent():
    """
    Test that committing when ammo's data= line is already present
    neither duplicates it nor moves any other line, so repeated commits
    are stable.
    """
    base = (
        'data="/games/Morrowind/Data Files"\n'
        f'data="{DATA_DIR}"\n'
        "content=Morrowind.esm\n"
    )
    with openmw_controller(base) as controller:
        controller.do_commit()
        controller.do_commit()
        result = CFG.read_text()

    assert result == base
    assert result.count(f'data="{DATA_DIR}"') == 1


def test_commit_preserves_other_lines():
    """
    Test that registration is non-destructive: comments, blank lines,
    the base data, a user's own extra data dir, content=, and fallback
    settings all survive verbatim, and only ammo's line is appended.
    """
    base = (
        "# a user comment\n"
        "fallback-archive=Morrowind.bsa\n"
        "\n"
        'data="/games/Morrowind/Data Files"\n'
        'data="/home/me/other mods"\n'
        "content=Morrowind.esm\n"
        "fallback=Water_SurfaceFPS,12\n"
    )
    with openmw_controller(base) as controller:
        controller.do_commit()
        result = CFG.read_text()

    assert result == base + f'data="{DATA_DIR}"\n'


def test_commit_appends_newline_when_missing():
    """
    Test that a cfg whose last line has no trailing newline is not
    corrupted: ammo's line lands on its own line rather than being glued
    onto the last.
    """
    base = 'data="/games/Morrowind/Data Files"'
    with openmw_controller(base) as controller:
        controller.do_commit()
        result = CFG.read_text()

    assert result == base + "\n" + f'data="{DATA_DIR}"\n'


def test_data_dir_of_parses_lines():
    """
    Test the parser that identifies ammo's own line: quoted and unquoted
    data= values are read with surrounding whitespace and quotes
    stripped, while non-data lines and commented-out lines are ignored.
    """
    assert OpenMWController.data_dir_of('data="/a/b"') == "/a/b"
    assert OpenMWController.data_dir_of("data=/a/b") == "/a/b"
    assert OpenMWController.data_dir_of('  data="/a/b"  \n') == "/a/b"
    assert OpenMWController.data_dir_of("content=Morrowind.esm") is None
    assert OpenMWController.data_dir_of("# data=/a/b") is None
