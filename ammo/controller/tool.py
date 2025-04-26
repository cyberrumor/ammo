#!/usr/bin/env python3
import os
import shutil
import subprocess
import readline
from pathlib import Path
import typing
from typing import Union
from ammo.ui import Controller
from ammo.lib import ignored
from ammo.component import (
    Download,
    Tool,
)


class ToolController(Controller):
    """
    Tool controller is responsible for managing files that you
    don't want to have installed into your game directory.
    """

    def __init__(self, downloads_dir: Path, tools_dir: Path):
        self.downloads_dir: Path = downloads_dir
        self.tools_dir: Path = tools_dir

        self.downloads: list[Download] = []
        self.tools: list[Tool] = []

        self.do_exit: bool = False

        # Create required directories. Harmless if exists.
        Path.mkdir(self.tools_dir, parents=True, exist_ok=True)

        # Instance a Tool class for each tool folder in the tool directory.
        for path in self.tools_dir.iterdir():
            if path.is_dir():
                self.tools.append(Tool(path))

        downloads: list[Path] = []
        for file in self.downloads_dir.iterdir():
            if file.is_dir():
                continue
            if any(file.suffix.lower() == ext for ext in (".rar", ".zip", ".7z")):
                download = Download(file)
                downloads.append(download)
        self.downloads = downloads

    def __str__(self) -> str:
        """
        Output a string representing all Downloads and Tools.
        """
        result = ""
        if len([i for i in self.downloads if i.visible]):
            result += " index | Download\n"
            result += "-------|---------\n"

            for i, download in enumerate(self.downloads):
                priority = f"[{i}]"
                result += f"{priority:<7} {download.name}\n"
            result += "\n"

        result += " index | Tool\n"
        result += "-------|----------\n"
        for i, tool in enumerate(self.tools):
            priority = f"[{i}]"
            result += f"{priority:<7} {tool.path.name}\n"

        if not result:
            result = "\n"

        return result

    def prompt(self):
        return "Tools >_: "

    def postcmd(self) -> bool:
        if self.do_exit:
            return True
        self.do_refresh()
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

        type_hints = typing.get_type_hints(func)
        if buf.endswith(" "):
            target_type = list(type_hints.values())[len(args)]
        else:
            target_type = list(type_hints.values())[max(0, abs(len(args) - 1))]

        if hasattr(target_type, "__args__"):
            if func not in [self.do_install.__func__]:
                components = self.tools
                if name.endswith("download"):
                    components = self.downloads
                for i in range(len(components)):
                    if str(i).startswith(text):
                        completions.append(str(i))
                if "all".startswith(text):
                    completions.append("all")

        if func == self.do_install.__func__:
            for i in range(len(self.downloads)):
                if str(i).startswith(text):
                    completions.append(str(i))
            if "all".startswith(text) and len(self.downloads) > 0:
                completions.append("all")

        return completions[state] + " "

    def has_extra_folder(self, path) -> bool:
        # Just extract the archive, don't remove extra folders.
        return False

    def do_rename_download(self, index: int, name: str) -> None:
        """
        Names may contain alphanumerics or underscores.
        """
        if name != "".join([i for i in name if i.isalnum() or i == "_"]):
            raise Warning(
                "Names can only contain alphanumeric characters or underscores"
            )

        forbidden_names = []
        for i in self.tools_dir.parts:
            forbidden_names.append(i.lower())
        if name.lower() in forbidden_names:
            raise Warning(
                f"Choose something else. These names are forbidden: {forbidden_names}"
            )

        try:
            download = self.downloads[index]
        except IndexError as e:
            raise Warning(e)

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

        download.location.rename(new_location)

    def do_rename_tool(self, index: int, name: str) -> None:
        """
        Names may contain alphanumerics or underscores.
        """
        if name != "".join([i for i in name if i.isalnum() or i == "_"]):
            raise Warning(
                "Names can only contain alphanumeric characters or underscores"
            )

        forbidden_names = []
        for i in self.tools_dir.parts:
            forbidden_names.append(i.lower())
        if name.lower() in forbidden_names:
            raise Warning(
                f"Choose something else. These names are forbidden: {forbidden_names}"
            )

        try:
            tool = self.tools[index]
        except IndexError as e:
            raise Warning(e)

        new_location = self.tools_dir / name
        if new_location.exists():
            raise Warning(f"A tool named {str(new_location)} already exists!")

        # Move the folder, update the tool.
        tool.path.rename(new_location)
        tool.path = new_location

    def do_delete_tool(self, index: Union[int, str]) -> None:
        """
        Removes specified file from the filesystem.
        """
        try:
            index = int(index)
        except ValueError:
            if index != "all":
                raise Warning(f"Expected int, got '{index}'")

        if index == "all":
            deleted_tools = ""
            visible_tools = [i for i in self.tools if i.visible]
            for tool in visible_tools:
                self.tools.pop(self.tools.index(tool))
                with ignored(FileNotFoundError):
                    shutil.rmtree(tool.path)
                deleted_tools += f"{tool.path.name}\n"
        else:
            try:
                tool = self.tools.pop(index)

            except IndexError as e:
                # Demote IndexErrors
                raise Warning(e)

            with ignored(FileNotFoundError):
                shutil.rmtree(tool.path)

    def do_delete_download(self, index: Union[int, str]) -> None:
        """
        Removes specified file from the filesystem.
        """
        if index == "all":
            visible_downloads = [i for i in self.downloads if i.visible]
            for visible_download in visible_downloads:
                download = self.downloads.pop(self.downloads.index(visible_download))
                download.location.unlink()
        else:
            index = int(index)
            try:
                download = self.downloads.pop(index)
            except IndexError as e:
                # Demote IndexErrors
                raise Warning(e)
            with ignored(FileNotFoundError):
                download.location.unlink()

    def do_install(self, index: Union[int, str]) -> None:
        """
        Extract and manage an archive from ~/Downloads.
        """
        try:
            int(index)
        except ValueError:
            if index != "all":
                raise Warning(f"Expected int, got '{index}'")

        def install_download(index, download) -> None:
            extract_to = "".join(
                [
                    i
                    for i in download.location.stem.replace(" ", "_")
                    if i.isalnum() or i == "_"
                ]
            ).strip()
            extract_to = self.tools_dir / extract_to
            if extract_to.exists():
                raise Warning(
                    f"Extraction of {index} failed since tool '{extract_to.name}' exists."
                )

            try:
                print("Verifying archive integrity...")
                subprocess.check_output(["7z", "t", f"{download.location}"])
            except subprocess.CalledProcessError:
                raise Warning(
                    f"Extraction of {index} failed at integrity check. Incomplete download?"
                )

            os.system(f"7z x '{download.location}' -o'{extract_to}'")

            if self.has_extra_folder(extract_to):
                # It is reasonable to conclude an extra directory can be eliminated.
                # This is needed for tools like skse that have a version directory
                # between the tool's base folder and the self.tools_dir.name folder.
                for file in next(extract_to.iterdir()).iterdir():
                    file.rename(extract_to / file.name)

            # Add the freshly install tool to self.tools so that an error doesn't prevent
            # any successfully installed tools from appearing during 'install all'.
            self.tools.append(Tool(extract_to))

        if index == "all":
            errors = []
            for i, download in enumerate(self.downloads):
                if download.visible:
                    try:
                        install_download(i, download)
                    except Warning as e:
                        errors.append(str(e))
            if errors:
                raise Warning("\n".join(errors))
        else:
            index = int(index)
            try:
                download = self.downloads[index]
            except IndexError as e:
                # Demote IndexErrors
                raise Warning(e)

            install_download(index, download)

    def do_mods(self) -> None:
        """
        Return to the mod controller.
        """
        self.do_exit = True

    def do_refresh(self) -> None:
        """
        Scan for tools in the tool folder.
        """
        self.__init__(self.downloads_dir, self.tools_dir)
