#!/usr/bin/env python3
import logging
import subprocess
import readline
from pathlib import Path
from typing import Union
from ammo.ui import Controller
from ammo.component import Download

log = logging.getLogger(__name__)


class DownloadController(Controller):
    """
    Download controller is responsible for renaming and deleting downloads.
    """

    def __init__(self, downloads_dir: Path):
        self.downloads_dir: Path = downloads_dir
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

    def __str__(self) -> str:
        """
        Output a string representing all Downloads.
        """
        result = ""
        if len([i for i in self.downloads if i.visible]):
            result += " index | Download\n"
            result += "-------|---------\n"

            for i, download in enumerate(self.downloads):
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
