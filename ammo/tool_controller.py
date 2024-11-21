#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import readline
from pathlib import Path
import typing
from typing import Union
from enum import (
    EnumMeta,
)
from .ui import Controller
from .component import (
    Download,
    ToolEnum,
    BethesdaComponentNoDownload,
)
from .lib import NO_EXTRACT_DIRS


class ToolController(Controller):
    """
    Tool controller is responsible for managing files that you
    don't want to have installed into your game directory.
    """

    def __init__(self, downloads_dir: Path, tools_dir: Path):
        self.downloads_dir: Path = downloads_dir
        self.tools_dir: Path = tools_dir

        self.downloads: list[Download] = []
        self.tools: list[Path] = []

        self.do_exit: bool = False

        # Create required directories. Harmless if exists.
        Path.mkdir(self.tools_dir, parents=True, exist_ok=True)

        # Instance a Tool class for each tool folder in the tool directory.
        for path in self.tools_dir.iterdir():
            if path.is_dir():
                self.tools.append(path)

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
            result += f"{priority:<7} {tool.name}\n"

        if not result:
            result = "\n"

        return result

    def _prompt(self):
        return "Tools >_: "

    def _post_exec(self) -> bool:
        if self.do_exit:
            return True
        self.refresh()
        return False

    def _autocomplete(self, text: str, state: int) -> Union[str, None]:
        buf = readline.get_line_buffer()
        name, *args = buf.split()
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
            if int in target_type.__args__ and len(args) > 0:
                match args[0]:
                    case "download":
                        components = self.downloads
                    case "tool":
                        components = self.tools
                    case _:
                        components = []
            if func not in [self.install.__func__, self.configure.__func__]:
                for i in range(len(components)):
                    if str(i).startswith(text):
                        completions.append(str(i))
                if "all".startswith(text):
                    completions.append("all")

        elif isinstance(target_type, EnumMeta):
            for i in list(target_type):
                if i.value.startswith(text):
                    completions.append(i.value)

        if func == self.install.__func__:
            for i in range(len(self.downloads)):
                if str(i).startswith(text):
                    completions.append(str(i))
            if "all".startswith(text) and len(self.downloads) > 0:
                completions.append("all")

        return completions[state] + " "

    def rename(self, component: ToolEnum, index: int, name: str) -> None:
        """
        Names may contain alphanumerics or underscores.
        """
        if component not in list(ToolEnum):
            raise Warning(
                f"Can only rename components of types {[i.value for i in list(ToolEnum)]}, not {component}"
            )

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

        match component:
            case ToolEnum.DOWNLOAD:
                try:
                    download = self.downloads[index]
                except IndexError as e:
                    raise Warning(e)

                if "pytest" not in sys.modules:
                    # Don't run this during tests because it's slow.
                    try:
                        print("Verifying archive integrity...")
                        subprocess.check_output(["7z", "t", f"{download.location}"])
                    except subprocess.CalledProcessError:
                        raise Warning(
                            f"Rename of {index} failed at integrity check. Incomplete download?"
                        )

                new_location = (
                    download.location.parent / f"{name}{download.location.suffix}"
                )
                if new_location.exists():
                    raise Warning(
                        f"Can't rename because download {new_location} exists."
                    )

                download.location.rename(new_location)

            case ToolEnum.TOOL:
                try:
                    tool = self.tools[index]
                except IndexError as e:
                    raise Warning(e)

                new_location = self.tools_dir / name
                if new_location.exists():
                    raise Warning(f"A tool named {str(new_location)} already exists!")

                # Move the folder, update the tool.
                tool.rename(new_location)
                tool = new_location

    def delete(self, component: ToolEnum, index: Union[int, str]) -> None:
        """
        Removes specified file from the filesystem.
        """
        if not isinstance(component, ToolEnum):
            raise TypeError(
                f"Expected ToolEnum, got '{component}' of type '{type(component)}'"
            )
        try:
            index = int(index)
        except ValueError:
            if index != "all":
                raise Warning(f"Expected int, got '{index}'")

        match component:
            case ToolEnum.TOOL:
                if index == "all":
                    deleted_tools = ""
                    visible_tools = [i for i in self.tools if i.visible]
                    for tool in visible_tools:
                        self.deactivate(
                            BethesdaComponentNoDownload.TOOL, self.tools.index(tool)
                        )
                    for tool in visible_tools:
                        self.tools.pop(self.tools.index(tool))
                        try:
                            shutil.rmtree(tool)
                        except FileNotFoundError:
                            pass
                        deleted_tools += f"{tool.name}\n"
                    self.commit()
                else:
                    try:
                        tool = self.tools.pop(index)

                    except IndexError as e:
                        # Demote IndexErrors
                        raise Warning(e)

                    try:
                        shutil.rmtree(tool)
                    except FileNotFoundError:
                        pass

            case ToolEnum.DOWNLOAD:
                if index == "all":
                    visible_downloads = [i for i in self.downloads if i.visible]
                    for visible_download in visible_downloads:
                        download = self.downloads.pop(
                            self.downloads.index(visible_download)
                        )
                        download.location.unlink()
                else:
                    index = int(index)
                    try:
                        download = self.downloads.pop(index)
                    except IndexError as e:
                        # Demote IndexErrors
                        raise Warning(e)
                    try:
                        download.location.unlink()
                    except FileNotFoundError:
                        pass

    def install(self, index: Union[int, str]) -> None:
        """
        Extract and manage an archive from ~/Downloads.
        """
        try:
            int(index)
        except ValueError:
            if index != "all":
                raise Warning(f"Expected int, got '{index}'")

        def has_extra_folder(path) -> bool:
            files = list(path.iterdir())
            return all(
                [
                    len(files) == 1,
                    files[0].is_dir(),
                    files[0].name.lower() != self.tools_dir.name.lower(),
                    files[0].name.lower() not in NO_EXTRACT_DIRS,
                    files[0].suffix.lower() not in [".esp", ".esl", ".esm"],
                ]
            )

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

            if "pytest" not in sys.modules:
                # Don't run this during tests because it's slow.
                try:
                    print("Verifying archive integrity...")
                    subprocess.check_output(["7z", "t", f"{download.location}"])
                except subprocess.CalledProcessError:
                    raise Warning(
                        f"Extraction of {index} failed at integrity check. Incomplete download?"
                    )

            os.system(f"7z x '{download.location}' -o'{extract_to}'")

            if has_extra_folder(extract_to):
                # It is reasonable to conclude an extra directory can be eliminated.
                # This is needed for tools like skse that have a version directory
                # between the tool's base folder and the self.tools_dir.name folder.
                for file in next(extract_to.iterdir()).iterdir():
                    file.rename(extract_to / file.name)

            # Add the freshly install tool to self.tools so that an error doesn't prevent
            # any successfully installed tools from appearing during 'install all'.
            self.tools.append(extract_to)

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

    def mods(self) -> None:
        """
        Return to the mod controller.
        """
        self.do_exit = True

    def refresh(self) -> None:
        """
        Scan for tools in the tool folder.
        """
        self.__init__(self.downloads_dir, self.tools_dir)
