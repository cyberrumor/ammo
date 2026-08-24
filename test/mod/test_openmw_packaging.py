#!/usr/bin/env python3
import shutil
from contextlib import contextmanager
from pathlib import Path

from ammo.component import (
    OpenMWGame,
    OpenMWMod,
)
from ammo.controller.openmw import OpenMWController

# Real Morrowind mods are usually packaged with their assets and plugins
# inside a "Data Files/" folder (Morrowind's real data directory name),
# sometimes beside a readme or screenshots, and with inconsistent
# directory casing. OpenMW's virtual file system scans ammo's merged
# data dir at its root and is case-insensitive. These tests cover
# OpenMWMod reshaping a mod into that layout (strip the wrapper,
# fold casing to Morrowind's canonical names) and OpenMWController
# auto-elevating a redundant wrapper folder at install time so neither
# needs a manual fix.

OPENMW_TEST_ROOT = Path("/tmp/ammo_openmw_packaging_test")
DATA_DIR = OPENMW_TEST_ROOT / "OpenMW" / "data"
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
def openmw_controller():
    """
    Yield an OpenMWController whose install dir is an ammo-owned OpenMW
    data dir. Cleans up the whole test root on exit.
    """
    downloads_dir = Path(__file__).parent.parent / "Downloads"
    CFG.parent.mkdir(parents=True, exist_ok=True)
    try:
        yield OpenMWController(downloads_dir, make_game())
    finally:
        shutil.rmtree(OPENMW_TEST_ROOT, ignore_errors=True)


def make_mod(controller: OpenMWController, name: str, *relpaths: str) -> None:
    """
    Create a mod folder <ammo_mods_dir>/<name> containing each relpath
    as an empty file, then refresh so the controller picks it up as
    an OpenMWMod.
    """
    mod_dir = controller.game.ammo_mods_dir / name
    for rel in relpaths:
        path = mod_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    controller.do_refresh()


def make_extract(controller: OpenMWController, *relpaths: str) -> Path:
    """
    Build a throwaway directory tree that looks like a freshly extracted
    archive and return its root, for exercising has_extra_folder
    directly. Lives outside the mods dir so it is not picked up as
    a mod.
    """
    root = controller.game.ammo_mods_dir.parent / "extract"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for rel in relpaths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    return root


def get_mod(controller: OpenMWController, name: str) -> OpenMWMod:
    return controller.mods[[m.name for m in controller.mods].index(name)]


def activate_by_name(controller: OpenMWController, name: str) -> None:
    controller.activate_mod([m.name for m in controller.mods].index(name))


def test_get_mods_returns_openmw_mod():
    """
    Test that OpenMWController builds OpenMWMod instances (not the
    generic Mod), so the Morrowind packaging heuristics apply.
    """
    with openmw_controller() as controller:
        make_mod(controller, "AnyMod", "meshes/foo.nif")
        assert type(get_mod(controller, "AnyMod")) is OpenMWMod


def test_strips_data_files_wrapper():
    """
    Test that assets and plugins inside a Data Files/ wrapper are
    elevated to the data dir root, which is what OpenMW's VFS scans.
    """
    with openmw_controller() as controller:
        make_mod(
            controller,
            "WrappedMod",
            "Data Files/meshes/foo.nif",
            "Data Files/WrappedMod.esp",
        )
        mod = get_mod(controller, "WrappedMod")
        assert set(mod.files) == {Path("Meshes/foo.nif"), Path("WrappedMod.esp")}


def test_strips_data_files_wrapper_beside_readme():
    """
    Test that a Data Files/ wrapper is stripped even when other entries
    sit beside it. This is the case has_extra_folder cannot rescue
    (it only fires when the wrapper is the single top-level entry), so
    OpenMWMod must handle it at populate time.
    """
    with openmw_controller() as controller:
        make_mod(
            controller,
            "WrappedMod",
            "Data Files/textures/foo.dds",
            "readme.txt",
            "screenshot.png",
        )
        mod = get_mod(controller, "WrappedMod")
        assert set(mod.files) == {Path("Textures/foo.dds")}


def test_loose_files_without_wrapper_stage_at_root():
    """
    Test that a mod already laid out at its root (no Data Files/
    wrapper) is staged as-is.
    """
    with openmw_controller() as controller:
        make_mod(controller, "LooseMod", "meshes/foo.nif", "LooseMod.esp")
        mod = get_mod(controller, "LooseMod")
        assert set(mod.files) == {Path("Meshes/foo.nif"), Path("LooseMod.esp")}


def test_canonical_casing_applied():
    """
    Test that case-variant asset directories fold to Morrowind's
    canonical casing, keeping the staging dir recognizable when
    browsing. Filenames keep their original case.
    """
    with openmw_controller() as controller:
        make_mod(controller, "ShoutyMod", "TEXTURES/Foo.dds", "MeShEs/bar.nif")
        mod = get_mod(controller, "ShoutyMod")
        assert set(mod.files) == {Path("Textures/Foo.dds"), Path("Meshes/bar.nif")}


def test_case_variant_dirs_conflict():
    """
    Test that two mods whose asset dirs differ only in case stage into
    the same directory, so ammo detects the file collision OpenMW's
    case-insensitive VFS would also see.
    """
    with openmw_controller() as controller:
        make_mod(controller, "ModA", "Textures/shared.dds")
        make_mod(controller, "ModB", "textures/shared.dds")
        activate_by_name(controller, "ModA")
        activate_by_name(controller, "ModB")
        assert get_mod(controller, "ModA").conflict
        assert get_mod(controller, "ModB").conflict


def test_has_extra_folder_elevates_redundant_wrapper():
    """
    Test that a single non-content wrapper folder (e.g.
    ModName/SomeFolder/) is elevated so its contents land at the data
    dir root.
    """
    with openmw_controller() as controller:
        root = make_extract(controller, "ModWrapper/meshes/foo.nif")
        assert controller.has_extra_folder(root) is True


def test_has_extra_folder_keeps_data_files_wrapper():
    """
    Test that a single Data Files/ folder is not elevated here:
    OpenMWMod strips it at populate time, so elevating it at install
    would be redundant restructuring of the stored mod.
    """
    with openmw_controller() as controller:
        root = make_extract(controller, "Data Files/meshes/foo.nif")
        assert controller.has_extra_folder(root) is False


def test_has_extra_folder_keeps_asset_dir():
    """
    Test that a mod whose single top-level folder is a real asset directory
    (e.g. meshes/) is left alone.
    """
    with openmw_controller() as controller:
        root = make_extract(controller, "meshes/foo.nif")
        assert controller.has_extra_folder(root) is False


def test_has_extra_folder_keeps_single_plugin():
    """
    Test that a mod that is a single loose plugin is not elevated (there
    is no wrapper to strip).
    """
    with openmw_controller() as controller:
        root = make_extract(controller, "SoloPlugin.esp")
        assert controller.has_extra_folder(root) is False


def test_has_extra_folder_keeps_multiple_top_level_entries():
    """
    Test that a mod with more than one top-level entry is left alone:
    there is no single wrapper to unambiguously elevate.
    """
    with openmw_controller() as controller:
        root = make_extract(controller, "ModWrapper/meshes/foo.nif", "readme.txt")
        assert controller.has_extra_folder(root) is False


def test_discovers_root_level_plugins():
    """
    Test that OpenMWMod exposes its root-level plugins, including the
    OpenMW-only .omwaddon and .omwscripts types, so the controller can
    order them. Assets and .bsa archives are not plugins.
    """
    with openmw_controller() as controller:
        make_mod(
            controller,
            "PluginMod",
            "Data Files/PluginMod.esp",
            "Data Files/PluginMod.esm",
            "Data Files/PluginMod.omwaddon",
            "Data Files/PluginMod.omwscripts",
            "Data Files/PluginMod.bsa",
            "Data Files/meshes/foo.nif",
        )
        mod = get_mod(controller, "PluginMod")
        assert {p.name for p in mod.plugins} == {
            "PluginMod.esp",
            "PluginMod.esm",
            "PluginMod.omwaddon",
            "PluginMod.omwscripts",
        }


def test_esl_not_treated_as_plugin():
    """
    Test that .esl is not a plugin for OpenMW. Morrowind has no light
    plugins; .esl is a Skyrim SE / Fallout 4 type, so OpenMW's extension
    set excludes it.
    """
    with openmw_controller() as controller:
        make_mod(controller, "EslMod", "Data Files/EslMod.esl")
        assert get_mod(controller, "EslMod").plugins == []


def test_install_elevates_redundant_wrapper():
    """
    Test end-to-end that do_install auto-elevates a mod wrapped in a
    single redundant folder without prompting, landing its plugin at the
    data dir root OpenMW scans.
    """
    with openmw_controller() as controller:
        index = [d.name for d in controller.downloads].index("no_data_folder_plugin.7z")
        controller.do_install(index)

        mod = get_mod(controller, "no_data_folder_plugin")
        assert set(mod.files) == {Path("no_data_folder_plugin.esp")}

        activate_by_name(controller, "no_data_folder_plugin")
        controller.do_commit()
        assert (DATA_DIR / "no_data_folder_plugin.esp").is_symlink()
