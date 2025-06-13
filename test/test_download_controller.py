#!/usr/bin/env python3
import os
import shutil
import textwrap
from pathlib import Path

from ammo.controller.download import DownloadController
from mod.mod_common import (
    AMMO_DIR,
    GAME,
)


class AmmoDownloadController:
    """
    Context manager for ammo's DownloadController class.

    Builds a DownloadController instance to run against /tmp/MockGame.
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
        return DownloadController(self.downloads_dir, self.game)

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


def test_download_controller_str():
    """
    Test that the download controller looks the way we expect it to.
    """
    expected = textwrap.dedent(
        """\
         index | Download
        -------|---------
        [0]     aaa.7z
        [1]     duplicate_filenames.7z
        [2]     edit_scripts.7z
        [3]     esl.7z
        [4]     esm.7z
        [5]     missing_data.7z
        [6]     mock_base_object_swapper.7z
        [7]     mock_conflict_1.7z
        [8]     mock_conflict_2.7z
        [9]     mock_embers_xd.7z
        [10]    mock_engine_fixes_part_1.7z
        [11]    mock_engine_fixes_part_2.7z
        [12]    mock_evlas_underside.7z
        [13]    mock_immersive_armors.7z
        [14]    mock_placed_light.7z
        [15]    mock_realistic_ragdolls.7z
        [16]    mock_relighting_skyrim.7z
        [17]    mock_script_extender.7z
        [18]    mock_skyui.7z
        [19]    mult_plugins_same_name.7z
        [20]    multiple_plugins.7z
        [21]    no_data_folder_dll.7z
        [22]    no_data_folder_plugin.7z
        [23]    normal_mod.7z
        [24]    pak_mods.7z
        [25]    pak_no_dir.7z
        [26]    pak_root.7z
        [27]    plugin_wrong_spot.7z
        [28]    zzz.7z

        """
    )
    with AmmoDownloadController() as controller:
        # Downloads get ordered alphabetically, not by install order.
        # This ensures the same order persists through different sessions.
        assert str(controller).endswith(expected)


def test_rename_download_moves_file():
    """
    Test that renaming a download causes the file to be moved.
    """
    with AmmoDownloadController() as controller:
        temp_download = controller.downloads_dir / "temp_download.7z"
        shutil.copy(controller.downloads_dir / "normal_mod.7z", temp_download)
        renamed_download = controller.downloads_dir / "i_was_renamed.7z"

        try:
            controller.do_refresh()
            index = [i.name for i in controller.downloads].index("temp_download.7z")
            original_download = controller.downloads[index]

            # Rename.
            controller.rename_download(index, "i_was_renamed")

            new_index = [i.name for i in controller.downloads].index("i_was_renamed.7z")
            new_download = controller.downloads[new_index]

            # Ensure the old download is gone.
            assert original_download.location.exists() is False

            # Ensure the new download is present and has the correct data.
            assert new_download.location.exists() is True
            assert new_download.name == "i_was_renamed.7z"

        finally:
            # Clean up our temporary files.
            try:
                temp_download.unlink()
            except FileNotFoundError:
                pass
            try:
                renamed_download.unlink()
            except FileNotFoundError:
                pass
