#!/usr/bin/env python3
import shutil
from contextlib import contextmanager
from pathlib import Path

from ammo.component import OpenMWGame
from ammo.controller.openmw import (
    OPENMW_PLUGIN_EXTENSIONS,
    OpenMWController,
)

# OpenMW aggregates every directory listed via a data="..." line in
# openmw.cfg into one virtual file system. OpenMWController owns ONE
# such directory, stages every mod into it, and registers it with a
# single data= line on commit. It also owns every content= line (the
# load order) and the fallback-archive= lines for staged BSAs. These
# tests exercise that sync: it must be idempotent and must not disturb
# any other line in the file (the base game data, fallback settings,
# comments, a user's extra data dirs).

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
        data=DATA_DIR,
        dlc_file=CFG,
        plugin_file=CFG,
        plugin_extensions=OPENMW_PLUGIN_EXTENSIONS,
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
    virtual-file-system priority. The base master moves into ammo's
    content block, which follows the data lines.
    """
    base = 'data="/games/Morrowind/Data Files"\ncontent=Morrowind.esm\n'
    with openmw_controller(base) as controller:
        controller.do_commit()
        result = CFG.read_text()

    assert result == (
        'data="/games/Morrowind/Data Files"\n'
        + f'data="{DATA_DIR}"\n'
        + "content=Morrowind.esm\n"
    )


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
    the base data, a user's own extra data dir, and fallback settings
    all survive verbatim. content= is the exception ammo now manages: it
    is relocated into ammo's content block at the end (order preserved).
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
    # The same file with the content= line lifted out; ammo keeps these
    # lines in place and appends its own after them.
    preserved = (
        "# a user comment\n"
        "fallback-archive=Morrowind.bsa\n"
        "\n"
        'data="/games/Morrowind/Data Files"\n'
        'data="/home/me/other mods"\n'
        "fallback=Water_SurfaceFPS,12\n"
    )
    with openmw_controller(base) as controller:
        controller.do_commit()
        result = CFG.read_text()

    assert result == preserved + f'data="{DATA_DIR}"\n' + "content=Morrowind.esm\n"


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


# The launcher-written content= line for the base master. ammo owns
# every content line, so on commit it moves this into ammo's content
# block at the end of the file (base masters become mod=None plugins so
# they can be reordered).
BASE_MASTER = "content=Morrowind.esm\n"
# The base game's lines ammo keeps in place: its archives and its data
# dir. ammo appends its own data=, fallback-archive=, and content= lines
# after these.
BASE_CFG_NO_CONTENT = (
    "fallback-archive=Morrowind.bsa\n"
    "fallback-archive=Tribunal.bsa\n"
    'data="/games/Morrowind/Data Files"\n'
)
# A cfg matching what a real openmw.cfg looks like, used to prove ammo's
# sync never disturbs the base archives.
BASE_CFG = BASE_CFG_NO_CONTENT + BASE_MASTER
# ammo's own data= line, which sync_cfg appends after the base game's
# lines. Every fallback-archive= test cfg grows by this line too, since a
# commit registers the data dir alongside the archives.
DATA_LINE = f'data="{DATA_DIR}"\n'


def make_mod(controller: OpenMWController, name: str, *relpaths: str) -> None:
    """
    Create a mod folder <ammo_mods_dir>/<name> containing each relpath
    as an empty file, then refresh so the controller picks it up.
    Mirrors what an extracted OpenMW mod looks like: assets and archives
    at the mod root.
    """
    mod_dir = controller.game.ammo_mods_dir / name
    for rel in relpaths:
        path = mod_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    controller.do_refresh()


def activate_by_name(controller: OpenMWController, name: str) -> None:
    controller.activate_mod([m.name for m in controller.mods].index(name))


def deactivate_by_name(controller: OpenMWController, name: str) -> None:
    controller.deactivate_mod([m.name for m in controller.mods].index(name))


def test_commit_registers_fallback_archive():
    """
    Test that staging a mod with a .bsa adds a fallback-archive=
    line after the base game's archives, so OpenMW actually loads the
    archive's contents and the mod's archive wins conflicts against the
    base game.
    """
    with openmw_controller(BASE_CFG) as controller:
        make_mod(controller, "BsaMod", "Foo.bsa")
        activate_by_name(controller, "BsaMod")
        controller.do_commit()
        result = CFG.read_text()

    assert result == (
        BASE_CFG_NO_CONTENT + DATA_LINE + "fallback-archive=Foo.bsa\n" + BASE_MASTER
    )


def test_commit_fallback_archive_removed_on_disable():
    """
    Test that disabling a BSA-bearing mod removes ammo's
    fallback-archive= line for it, without touching the base game's
    archives, so a disabled mod's archive stops loading.
    """
    with openmw_controller(BASE_CFG) as controller:
        make_mod(controller, "BsaMod", "Foo.bsa")
        activate_by_name(controller, "BsaMod")
        controller.do_commit()

        deactivate_by_name(controller, "BsaMod")
        controller.do_commit()
        result = CFG.read_text()

    assert result == BASE_CFG_NO_CONTENT + DATA_LINE + BASE_MASTER
    assert "Foo.bsa" not in result


def test_commit_fallback_archive_idempotent():
    """
    Test that re-committing an unchanged BSA-bearing mod neither
    duplicates its fallback-archive= line nor moves any other line.
    """
    with openmw_controller(BASE_CFG) as controller:
        make_mod(controller, "BsaMod", "Foo.bsa")
        activate_by_name(controller, "BsaMod")
        controller.do_commit()
        controller.do_commit()
        result = CFG.read_text()

    assert result == (
        BASE_CFG_NO_CONTENT + DATA_LINE + "fallback-archive=Foo.bsa\n" + BASE_MASTER
    )
    assert result.count("fallback-archive=Foo.bsa") == 1


def test_commit_no_archive_line_without_bsa():
    """
    Test that a mod with no .bsa adds no fallback-archive= line, so ammo only
    registers archives that actually exist.
    """
    with openmw_controller(BASE_CFG) as controller:
        make_mod(controller, "PluginMod", "plugin.esp")
        activate_by_name(controller, "PluginMod")
        controller.do_commit()
        result = CFG.read_text()

    # Only the data dir was registered; the base archives are untouched and
    # no archive line was invented for the loose plugin. Activating the mod
    # stages its plugin but leaves it disabled, so it is a #content= line.
    assert result == (
        BASE_CFG_NO_CONTENT + DATA_LINE + BASE_MASTER + "#content=plugin.esp\n"
    )


def test_commit_registers_multiple_archives_sorted():
    """
    Test that a mod shipping several .bsa files registers each one, in a
    deterministic (sorted) order so repeated commits are stable.
    """
    with openmw_controller(BASE_CFG) as controller:
        make_mod(controller, "MultiBsa", "BBB.bsa", "AAA.bsa")
        activate_by_name(controller, "MultiBsa")
        controller.do_commit()
        result = CFG.read_text()

    assert result == (
        BASE_CFG_NO_CONTENT
        + DATA_LINE
        + "fallback-archive=AAA.bsa\n"
        + "fallback-archive=BBB.bsa\n"
        + BASE_MASTER
    )


def test_archive_of_parses_lines():
    """
    Test the parser that identifies ammo's own archive lines: fallback-archive
    values are read with surrounding whitespace stripped, while other lines
    and commented-out lines are ignored.
    """
    assert OpenMWController.archive_of("fallback-archive=Foo.bsa") == "Foo.bsa"
    assert OpenMWController.archive_of("  fallback-archive=Foo.bsa \n") == "Foo.bsa"
    assert OpenMWController.archive_of("content=Morrowind.esm") is None
    assert OpenMWController.archive_of("# fallback-archive=Foo.bsa") is None


def test_content_of_parses_lines():
    """
    Test the parser that identifies content lines: an enabled content=
    line and a disabled #content= line both yield the plugin name, while
    other keys and plain comments yield None.
    """
    assert OpenMWController.content_of("content=Morrowind.esm") == "Morrowind.esm"
    assert OpenMWController.content_of("#content=Foo.esp") == "Foo.esp"
    assert OpenMWController.content_of("# content=Foo.esp") == "Foo.esp"
    assert OpenMWController.content_of("  content=Foo.esp \n") == "Foo.esp"
    assert OpenMWController.content_of('data="/a/b"') is None
    assert OpenMWController.content_of("# a user comment") is None


# A cfg holding just the base masters, in load order, as the OpenMW
# Launcher would write them. ammo takes these over as mod=None plugins.
BASE_MASTERS_CFG = (
    'data="/games/Morrowind/Data Files"\n'
    "content=Morrowind.esm\n"
    "content=Tribunal.esm\n"
    "content=Bloodmoon.esm\n"
)


def content_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if OpenMWController.content_of(line)]


def plugin_index(controller: OpenMWController, name: str) -> int:
    return [p.name for p in controller.plugins].index(name)


def test_activating_plugin_writes_content_line():
    """
    Test that a mod plugin the user activates is written as an enabled
    content= line, after the base masters ammo already tracks.
    """
    with openmw_controller(BASE_MASTERS_CFG) as controller:
        make_mod(controller, "CoolMod", "CoolMod.esp")
        activate_by_name(controller, "CoolMod")
        controller.activate_plugin(plugin_index(controller, "CoolMod.esp"))
        controller.do_commit()
        result = CFG.read_text()

    assert content_lines(result) == [
        "content=Morrowind.esm",
        "content=Tribunal.esm",
        "content=Bloodmoon.esm",
        "content=CoolMod.esp",
    ]


def test_disabled_plugin_written_as_comment():
    """
    Test that a plugin left disabled becomes a #content= line, so OpenMW
    does not load it but its position is remembered.
    """
    with openmw_controller(BASE_MASTERS_CFG) as controller:
        make_mod(controller, "CoolMod", "CoolMod.esp")
        activate_by_name(controller, "CoolMod")
        controller.do_commit()
        result = CFG.read_text()

    assert "#content=CoolMod.esp\n" in result
    assert "\ncontent=CoolMod.esp\n" not in result


def test_plugin_orders_before_base_master():
    """
    Test the Distant Seafloor case (Nexus Morrowind #50796): a mod plugin
    can be ordered ahead of a base master, here before Bloodmoon.esm.
    ammo owns every content line, so arbitrary insertion is possible,
    not only appending after the masters.
    """
    with openmw_controller(BASE_MASTERS_CFG) as controller:
        make_mod(controller, "DistantSeafloor", "DistantSeafloor.esp")
        activate_by_name(controller, "DistantSeafloor")
        controller.activate_plugin(plugin_index(controller, "DistantSeafloor.esp"))
        controller.move_plugin(
            plugin_index(controller, "DistantSeafloor.esp"),
            plugin_index(controller, "Bloodmoon.esm"),
        )
        controller.do_commit()
        result = CFG.read_text()

    assert content_lines(result) == [
        "content=Morrowind.esm",
        "content=Tribunal.esm",
        "content=DistantSeafloor.esp",
        "content=Bloodmoon.esm",
    ]


def test_content_order_survives_round_trip():
    """
    Test that committing then refreshing rebuilds the same plugin list,
    order and enabled state, from the content= / #content= lines. This is
    what makes the disabled-plugin comment worth keeping.
    """
    with openmw_controller(BASE_MASTERS_CFG) as controller:
        make_mod(controller, "CoolMod", "CoolMod.esp")
        activate_by_name(controller, "CoolMod")
        controller.do_commit()

        controller.do_refresh()
        assert [p.name for p in controller.plugins] == [
            "Morrowind.esm",
            "Tribunal.esm",
            "Bloodmoon.esm",
            "CoolMod.esp",
        ]
        assert [p.enabled for p in controller.plugins] == [True, True, True, False]


def test_content_commit_idempotent():
    """
    Test that re-committing an unchanged load order rewrites the cfg
    identically, so commits are stable.
    """
    with openmw_controller(BASE_MASTERS_CFG) as controller:
        make_mod(controller, "CoolMod", "CoolMod.esp")
        activate_by_name(controller, "CoolMod")
        controller.activate_plugin(plugin_index(controller, "CoolMod.esp"))
        controller.do_commit()
        first = CFG.read_text()
        controller.do_commit()
        second = CFG.read_text()

    assert first == second
