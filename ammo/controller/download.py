#!/usr/bin/env python3
import os
import logging
import subprocess
import readline
import textwrap
from pathlib import Path
from typing import Union
from ammo.ui import Controller
from ammo.component import (
    Download,
    Game,
    BethesdaGame,
)

log = logging.getLogger(__name__)


class DownloadController(Controller):
    """
    Download controller is responsible for renaming and deleting downloads.
    """

    def __init__(self, downloads_dir: Path, game: Game | BethesdaGame):
        self.downloads_dir: Path = downloads_dir
        self.game = game
        Path.mkdir(self.downloads_dir, parents=True, exist_ok=True)
        self.populate_downloads()

    def populate_downloads(self):
        """
        Populate self.downloads.
        """
        self.downloads: list[Download] = []
        downloads: list[Path] = []
        for file in self.downloads_dir.iterdir():
            if file.is_dir():
                continue
            if any(file.suffix.lower() == ext for ext in (".rar", ".zip", ".7z")):
                download = Download(file)
                downloads.append(download)
        self.downloads = sorted(downloads, key=lambda x: x.name)

    def do_refresh(self) -> None:
        """
        Abandon pending changes.
        """
        self.__init__(self.downloads_dir, self.game)

    def __str__(self) -> str:
        """
        Output a string representing all Downloads.
        """
        result = ""
        if len([i for i in self.downloads if i.visible]):
            result += " index | Download\n"
            result += "-------|---------\n"

            for i, download in enumerate(self.downloads):
                if download.visible:
                    priority = f"[{i}]"
                    result += f"{priority:<7} {download.name}\n"
            result += "\n"

        return result

    def prompt(self):
        return ""

    def postcmd(self) -> bool:
        return False

    def autocomplete(self, text: str, state: int) -> Union[str, None]:
        buf = readline.get_line_buffer()
        name, *args = buf.split()
        name = f"do_{name}"
        completions = []

        assert name in dir(self)

        # Identify the method we're calling.
        attribute = getattr(self, name)
        if hasattr(attribute, "__func__"):
            func = attribute.__func__
        else:
            func = attribute

        if func == self.do_install.__func__:
            for i in range(len(self.downloads)):
                if str(i).startswith(text):
                    completions.append(str(i))
            if "all".startswith(text) and len(self.downloads) > 0:
                completions.append("all")

        return completions[state] + " "

    def extract_archive(self, index: int, download: Path, target_dir: Path) -> Path:
        """
        Extract an archive and return the Path of the directory
        it was extracted to.
        """
        log.info(f"Installing archive: {download.name}")
        extract_to = "".join(
            [
                i
                for i in download.location.stem.replace(" ", "_")
                if i.isalnum() or i == "_"
            ]
        ).strip()
        extract_to = target_dir / extract_to
        if extract_to.exists():
            raise Warning(
                f"Extraction of {index} failed since mod '{extract_to.name}' exists."
            )

        # 7z CLI has a bug with filenames with apostrophes. shlex.quote won't work around this.
        # Rename the archive if it has an apostrophe in it.
        if "'" in download.location.name:
            new_location = download.location.parent / download.location.name.replace(
                "'", "_"
            )
            download.location.rename(new_location)
            download.location = new_location
            download.name = new_location.name

        try:
            print("Verifying archive integrity...")
            subprocess.check_output(["7z", "t", f"{download.location}"])
        except subprocess.CalledProcessError:
            raise Warning(
                f"Extraction of {index} failed at integrity check. Incomplete download?"
            )

        os.system(f"7z x '{download.location}' -o'{extract_to}'")

        return extract_to

    def install(self, index: Union[int, str], target_dir: Path) -> None:
        """
        Common logic for do_install to rely on. This should be able to install
        tools, mods, etc.
        """
        try:
            int(index)
        except ValueError as e:
            if index != "all":
                raise Warning(e)

        packaging_error = textwrap.dedent(
            """
            This archive may have been packaged incorrectly!
            You should manually confirm that this extracted archive's directory
            structure matches your expectations:

                "{0}"

            """
        )

        try:
            if index == "all":
                errors = []
                for i, download in enumerate(self.downloads):
                    if download.visible:
                        try:
                            extract_to = self.extract_archive(i, download, target_dir)

                            if self.has_extra_folder(extract_to):
                                for file in next(extract_to.iterdir()).iterdir():
                                    file.rename(extract_to / file.name)

                            else:
                                requires_unique = next(extract_to.iterdir())
                                if requires_unique.is_dir():
                                    if any(
                                        file.name == requires_unique.name
                                        for file in requires_unique.iterdir()
                                    ):
                                        raise Warning(
                                            packaging_error.format(extract_to)
                                        )

                        except Warning as e:
                            errors.append(str(e))
                if errors:
                    raise Warning("\n".join(errors))
            else:
                index = int(index)
                try:
                    download = self.downloads[index]
                except IndexError as e:
                    raise Warning(e)

                if not download.visible:
                    raise Warning("You can only install visible downloads.")

                extract_to = self.extract_archive(index, download, target_dir)

                if self.has_extra_folder(extract_to):
                    # This is needed for mods that have a nested folder inside
                    # the extracted archive that shares a name with the mod, like
                    # my_extracted_mod/my_extracted_mod/<files>,
                    # or for mods which have a version directory under the extracted
                    # dir, like
                    # my_extracted_mod/v1.0/<files>.
                    # This code turns both of those examples into:
                    # my_extracted_mod/<files>
                    for file in next(extract_to.iterdir()).iterdir():
                        file.rename(extract_to / file.name)

                else:
                    requires_unique = next(extract_to.iterdir())
                    if requires_unique.is_dir():
                        if any(
                            file.name == requires_unique.name
                            for file in requires_unique.iterdir()
                        ):
                            raise Warning(packaging_error.format(extract_to))
        finally:
            # Add freshly installed mods to self.mods so that an error doesn't prevent
            # any successfully installed mods from appearing during 'install all'.
            # This is better than adding to self.mods during self.extract_archive because
            # subclasses of ModController might use a different class than component.Mod.
            self.do_refresh()

    def rename_download(self, index: int, name: str) -> None:
        """
        Names may contain alphanumerics, periods, or underscores.
        """
        if name != "".join([i for i in name if i.isalnum() or i in ("_", ".")]):
            raise Warning(
                "Names can only contain alphanumeric characters, periods, or underscores"
            )

        forbidden_names = []
        for i in self.game.directory.parts:
            forbidden_names.append(i.lower())
        if name.lower() in forbidden_names:
            raise Warning(
                f"Choose something else. These names are forbidden: {forbidden_names}"
            )

        try:
            download = self.downloads[index]
        except IndexError as e:
            raise Warning(e)

        if not download.visible:
            raise Warning("You can only rename visible components.")

        try:
            print("Verifying archive integrity...")
            subprocess.check_output(["7z", "t", f"{download.location}"])
        except subprocess.CalledProcessError:
            raise Warning(
                f"Rename of {index} failed at integrity check. Incomplete download?"
            )

        new_location = download.location.parent / f"{name}{download.location.suffix}"
        if new_location.exists():
            raise Warning(f"Can't rename because download {new_location} exists.")

        log.info(f"Renaming DOWNLOAD {download.location} to {new_location}")
        download.location.rename(new_location)
        self.do_refresh()

    def delete_download(self, index: Union[int, str]) -> None:
        """
        Removes specified download from the filesystem.
        """
        if index == "all":
            visible_downloads = [i for i in self.downloads if i.visible]
            for visible_download in visible_downloads:
                download = self.downloads.pop(self.downloads.index(visible_download))
                try:
                    log.info(f"Deleting DOWNLOAD: {download.location}")
                    download.location.unlink()
                except FileNotFoundError:
                    pass
        else:
            try:
                index = int(index)
                download = self.downloads[index]
            except (ValueError, IndexError) as e:
                raise Warning(e)

            if not download.visible:
                raise Warning("You can only delete visible components")

            self.downloads.remove(download)

            try:
                log.info(f"Deleting DOWNLOAD: {download.location}")
                download.location.unlink()
            except FileNotFoundError:
                pass
