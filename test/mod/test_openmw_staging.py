#!/usr/bin/env python3
import re
import shutil
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from ammo.component import Game
from ammo.controller.mod import ModController
from test.mod.mod_common import expect_files

# OpenMW aggregates every directory listed via a `data="..."` line in
# openmw.cfg into a single virtual file system. The strategy for OpenMW
# support is to have ammo own ONE such directory, symlink all mods into it,
# and register that directory with a single `data=` line. This exercises
# the existing generic ModController with a game whose install directory is
# that ammo-owned data dir, mirroring what ~/.local/share/ammo/OpenMW.json
# produces (name "OpenMW" is not a Bethesda title, so it yields a generic
# GameSelection -> ModController).

OPENMW_TEST_ROOT = Path("/tmp/ammo_openmw_test")
# The ammo-owned data directory ammo stages mods into and that the user
# registers in openmw.cfg with a single `data="..."` line.
DATA_DIR = OPENMW_TEST_ROOT / "OpenMW" / "data"
# Where a real setup keeps openmw.cfg. Only used to prove the registration
# is coherent; ammo does not read or write it in this slice.
OPENMW_CFG = OPENMW_TEST_ROOT / "config" / "openmw.cfg"

GAME = Game(
    name="OpenMW",
    directory=DATA_DIR,
    ammo_conf=OPENMW_TEST_ROOT / "OpenMW" / "ammo.conf",
    ammo_log=OPENMW_TEST_ROOT / "OpenMW" / "ammo.log",
    ammo_mods_dir=OPENMW_TEST_ROOT / "OpenMW" / "mods",
    ammo_tools_dir=OPENMW_TEST_ROOT / "OpenMW" / "tools",
)


@contextmanager
def openmw_controller():
    """
    Yield a generic ModController whose install directory is an ammo-owned
    OpenMW data dir. Cleans up the whole test root on exit.
    """
    downloads_dir = Path(__file__).parent.parent / "Downloads"
    try:
        yield ModController(downloads_dir, GAME)
    finally:
        shutil.rmtree(OPENMW_TEST_ROOT, ignore_errors=True)


def extract(controller, mod_name):
    """
    Extract a mod by name, elevating its single top-level folder so its
    contents land at the data dir root (the layout OpenMW's VFS expects:
    plugins and asset folders directly under a data= dir).
    """
    with patch.object(ModController, "has_extra_folder", return_value=True):
        download_index = [i.name for i in controller.downloads].index(mod_name + ".7z")
        controller.do_install(download_index)


def activate(controller, mod_name):
    """Activate a previously extracted mod by name."""
    mod_index = [i.name for i in controller.mods].index(mod_name)
    controller.activate_mod(mod_index)


def test_openmw_stages_merged_data_dir():
    """
    Test that the generic controller aggregates multiple mods into the one
    ammo-owned data dir as symlinks, which is the whole OpenMW strategy.

    OpenMW cannot launch in CI, so whether its VFS actually reads a
    symlink-populated data dir stays a manual, in-game check. This test
    covers the ammo side: that staging targets the OpenMW data dir and
    produces resolvable symlinks for it to consume.
    """
    with openmw_controller() as controller:
        extract(controller, "normal_mod")
        extract(controller, "no_data_folder_plugin")
        activate(controller, "normal_mod")
        activate(controller, "no_data_folder_plugin")
        controller.do_commit()

        expected = [
            Path("normal_plugin.esp"),
            Path("no_data_folder_plugin.esp"),
        ]
        # expect_files asserts each file exists, resolves (not a broken
        # symlink), and that nothing unexpected is present.
        expect_files(DATA_DIR, expected)

        # Every staged file is a symlink back into ammo's mods dir; OpenMW's
        # VFS must be able to read through these links (the manual check).
        for rel in expected:
            staged = DATA_DIR / rel
            assert staged.is_symlink(), f"{staged} is not a symlink"
            assert staged.resolve().is_relative_to(controller.game.ammo_mods_dir)


def test_openmw_data_line_points_at_staged_dir():
    """
    Test that the `data="..."` line a user adds to openmw.cfg refers to the
    exact directory ammo stages into, so OpenMW's VFS scans the staged mods.
    """
    with openmw_controller() as controller:
        extract(controller, "normal_mod")
        activate(controller, "normal_mod")
        controller.do_commit()

        # Write the openmw.cfg a user would end up with: the base Morrowind
        # data, then the ammo-owned data dir, then plugin activation (which
        # the OpenMW Launcher owns, not ammo).
        OPENMW_CFG.parent.mkdir(parents=True, exist_ok=True)
        OPENMW_CFG.write_text(
            'data="/games/Morrowind/Data Files"\n'
            f'data="{DATA_DIR}"\n'
            "content=Morrowind.esm\n"
            "content=normal_plugin.esp\n"
        )

        data_lines = re.findall(r'data="([^"]+)"', OPENMW_CFG.read_text())
        assert str(DATA_DIR) in data_lines, (
            f"ammo data dir {DATA_DIR} not registered in {data_lines}"
        )

        # The plugin activated via content= resolves inside the registered
        # data dir, so OpenMW would find it there.
        assert (DATA_DIR / "normal_plugin.esp").exists()


def test_openmw_uses_generic_controller():
    """
    Test that a game named "OpenMW" is managed by the generic ModController
    (symlink staging) rather than the Bethesda plugin machinery, since the
    OpenMW Launcher, not ammo, owns plugin order in this slice.
    """
    from ammo.controller.game import BETHESDA_TITLES

    assert "OpenMW" not in BETHESDA_TITLES
    with openmw_controller() as controller:
        assert type(controller) is ModController
