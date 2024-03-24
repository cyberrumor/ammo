#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import readline
import textwrap
from collections.abc import Callable
from pathlib import Path
from dataclasses import (
    dataclass,
    field,
)
import typing
from typing import Union
from enum import (
    EnumMeta,
)
from .ui import (
    UI,
    Controller,
)
from .fomod_controller import FomodController
from .tool_controller import ToolController
from .component import (
    Mod,
    Download,
    Plugin,
    DeleteEnum,
    ComponentEnum,
    RenameEnum,
)
from .lib import (
    normalize,
    NO_EXTRACT_DIRS,
)


@dataclass(frozen=True)
class Game:
    ammo_conf: Path
    ammo_mods_dir: Path
    name: str
    directory: Path
    data: Path
    dlc_file: Path
    plugin_file: Path
    enabled_formula: Callable[[str], bool] = field(
        default=lambda line: line.strip().startswith("*")
    )


class ModController(Controller):
    """
    ModController is responsible for managing mods. It exposes
    methods to the UI that allow the user to easily manage mods.
    Private methods here are private simply so the UI doesn't
    display them.
    """

    def __init__(self, downloads_dir: Path, game: Game, *keywords):
        self.downloads_dir: Path = downloads_dir
        self.game: Game = game
        self.changes: bool = False
        self.downloads: list[Download] = []
        self.mods: list[Mod] = []
        self.plugins: list[Plugin] = []
        self.dlc: list[Plugin] = []
        self.keywords = [*keywords]

        # Create required directories. Harmless if exists.
        Path.mkdir(self.game.ammo_mods_dir, parents=True, exist_ok=True)
        Path.mkdir(self.game.data, parents=True, exist_ok=True)

        # Instance a Mod class for each mod folder in the mod directory.
        mods = []
        Path.mkdir(self.game.ammo_mods_dir, parents=True, exist_ok=True)
        mod_folders = [i for i in self.game.ammo_mods_dir.iterdir() if i.is_dir()]
        for path in mod_folders:
            mod = Mod(
                location=self.game.ammo_mods_dir / path.name,
                game_root=self.game.directory,
                game_data=self.game.data,
            )
            mods.append(mod)

        # Read self.game.ammo_conf. If there's mods in it, put them in order.
        if self.game.ammo_conf.exists():
            with open(self.game.ammo_conf, "r") as file:
                for line in file:
                    if not line.strip() or line.strip().startswith("#"):
                        continue
                    name = line.strip().strip("*").strip()
                    enabled = line.strip().startswith("*")

                    for mod in mods:
                        if mod.name != name:
                            continue

                        mod.enabled = enabled
                        self.mods.append(mod)
                        break

        # Put mods that aren't listed in self.game.ammo_conf file
        # at the end in an arbitrary order.
        for mod in mods:
            if mod not in self.mods:
                self.mods.append(mod)

        Path.mkdir(self.game.plugin_file.parent, parents=True, exist_ok=True)
        if not self.game.plugin_file.exists():
            with open(self.game.plugin_file, "w") as file:
                file.write("")

        # Parse DLCList.txt, take inventory of our DLC. Note that plugins from
        # mods are stored in DLCList.txt too, so you must identify DLC by finding
        # plugins from this file that didn't come from a mod.
        if self.game.dlc_file.exists():
            with open(self.game.dlc_file, "r") as file:
                for line in file:
                    if not line.strip() or line.strip().startswith("#"):
                        # Ignore empty lines and comments.
                        continue
                    name = line.strip().strip("*").strip()
                    plugin = Plugin(
                        name=name,
                        mod=None,
                        enabled=False,
                    )
                    # We must identify whether files listed here
                    # belong to a mod and assign it. If we don't,
                    # the mod's plugins appear when the mod is disabled.
                    for m in self.mods[::-1]:
                        if name in m.plugins:
                            plugin.mod = m
                            break

                    self.dlc.append(plugin)

        # Parse Plugins.txt, create plugins in order.
        with open(self.game.plugin_file, "r") as file:
            for line in file:
                if not line.strip() or line.strip().startswith("#"):
                    # Ignore empty lines and comments.
                    continue

                name = line.strip().strip("*").strip()

                # Don't add duplicate plugins
                if name.lower() in (p.name.lower() for p in self.plugins):
                    continue

                enabled = self.game.enabled_formula(line)

                # Iterate through our mods in reverse so we can assign the conflict
                # winning mod as the parent.
                mod = None
                for m in self.mods[::-1]:
                    if not m.enabled:
                        continue
                    if name in m.plugins:
                        mod = m
                        break

                if mod is None:
                    # Only add plugins without mods if the plugin file exists
                    # and isn't a symlink, because symlinks could be artifacts
                    # of disabled mods.
                    plugin_file = self.game.data / name
                    if plugin_file.exists() and not plugin_file.is_symlink():
                        self.plugins.append(
                            Plugin(
                                name=name,
                                mod=mod,
                                enabled=enabled,
                            )
                        )
                    continue

                if not mod.enabled:
                    # The parent mod either wasn't enabled or wasn't installed correctly.
                    # Don't add this plugin to the list of managed plugins. It will be
                    # added automatically when the parent mod is enabled.
                    continue

                # Disqualify plugins that aren't installed correctly
                # from starting as enabled.
                plugin_file = self.game.data / name
                if not plugin_file.exists():
                    enabled = False
                elif not plugin_file.resolve().exists():
                    enabled = False

                self.plugins.append(
                    Plugin(
                        name=name,
                        mod=mod,
                        enabled=enabled,
                    )
                )

        # Finish adding DLC from DLCList.txt that was missing from Plugins.txt.
        # These will be added as disabled. Since order is preserved in Plugins.txt and
        # these were absent from it, their true order can't be preserved.
        for plugin in self.dlc:
            if plugin.mod is None and plugin.name not in (i.name for i in self.plugins):
                self.plugins.append(plugin)

        downloads: list[Path] = []
        for file in self.downloads_dir.iterdir():
            if file.is_dir():
                continue
            if any(file.suffix.lower() == ext for ext in (".rar", ".zip", ".7z")):
                download = Download(file)
                downloads.append(download)
        self.downloads = downloads
        self.changes = False
        self.find(*self.keywords)
        self._stage()

    def __str__(self) -> str:
        """
        Output a string representing all downloads, mods and plugins.
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

        if len([i for i in self.mods if i.visible]):
            result += " index | Activated | Mod name\n"
            result += "-------|-----------|------------\n"
            for i, mod in enumerate(self.mods):
                if mod.visible:
                    priority = f"[{i}]"
                    enabled = f"[{mod.enabled}]"
                    conflict = (
                        "x"
                        if mod.enabled and mod.obsolete
                        else ("*" if mod.conflict else " ")
                    )
                    result += f"{priority:<7} {enabled:<9} {conflict:<1} {mod.name}\n"

        if len([i for i in self.plugins if i.visible]):
            result += "\n"
            result += " index | Activated | Plugin name\n"
            result += "-------|-----------|------------\n"
            for i, plugin in enumerate(self.plugins):
                if plugin.visible:
                    priority = f"[{i}]"
                    enabled = f"[{plugin.enabled}]"
                    conflict = "*" if plugin.conflict else " "
                    result += (
                        f"{priority:<7} {enabled:<9} {conflict:<1} {plugin.name}\n"
                    )

        if not result:
            result = "\n"

        return result

    def _prompt(self):
        changes = "*" if self.changes else "_"
        name = self.game.name
        return f"{name} >{changes}: "

    def _post_exec(self) -> bool:
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
                    case "mod":
                        components = self.mods
                    case "plugin":
                        components = self.plugins
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

        elif func == self.configure.__func__:
            for i in range(len(self.mods)):
                if str(i).startswith(text):
                    if self.mods[i].fomod:
                        completions.append(str(i))

        return completions[state] + " "

    def _save_order(self):
        """
        Writes ammo.conf and Plugins.txt.
        """
        with open(self.game.plugin_file, "w") as file:
            for plugin in self.plugins:
                if self.game.enabled_formula("*"):
                    file.write(f"{'*' if plugin.enabled else ''}{plugin.name}\n")
                else:
                    file.write(f"{'' if plugin.enabled else '*'}{plugin.name}\n")
        with open(self.game.ammo_conf, "w") as file:
            for mod in self.mods:
                file.write(f"{'*' if mod.enabled else ''}{mod.name}\n")

    def _get_validated_components(self, component: ComponentEnum) -> list:
        """
        Turn a ComponentEnum into either self.mods or self.plugins.
        """
        if isinstance(component, ComponentEnum):
            match component:
                case ComponentEnum.PLUGIN:
                    return self.plugins
                case ComponentEnum.MOD:
                    return self.mods
        raise TypeError(
            textwrap.dedent(
                f"""\
                Expected {[i.value for i in list(ComponentEnum)]},
                got {component} of type {type(component)}
                """
            )
        )

    def _set_component_state(self, component: ComponentEnum, index: int, state: bool):
        """
        Activate or deactivate a component.
        If a mod with plugins was deactivated, remove those plugins from self.plugins
        if they aren't also provided by another mod.
        """
        components = self._get_validated_components(component)
        subject = components[index]

        starting_state = subject.enabled
        # Handle mods
        if isinstance(subject, Mod):
            # Handle configuration of fomods
            if (
                state
                and subject.fomod
                and not (subject.location / "ammo_fomod").exists()
            ):
                raise Warning("Fomods must be configured before they can be enabled.")

            subject.enabled = state
            if subject.enabled:
                # Show plugins owned by this mod
                for name in subject.plugins:
                    if name not in [i.name for i in self.plugins]:
                        plugin = Plugin(
                            name=name,
                            mod=subject,
                            enabled=False,
                        )
                        self.plugins.append(plugin)
            else:
                # Hide plugins owned by this mod and not another mod
                for plugin in subject.plugins:
                    if plugin not in [i.name for i in self.plugins]:
                        continue
                    provided_elsewhere = False
                    for mod in self.mods:
                        if not mod.enabled:
                            continue
                        if mod == subject:
                            continue
                        if plugin in mod.plugins:
                            provided_elsewhere = True
                            break
                    if not provided_elsewhere:
                        index = [i.name for i in self.plugins].index(plugin)
                        self.plugins.pop(index)

        # Handle plugins
        elif isinstance(subject, Plugin):
            subject.enabled = state
        else:
            raise NotImplementedError

        if not self.changes:
            self.changes = starting_state != subject.enabled

    def _stage(self) -> dict:
        """
        Responsible for assigning mod.conflict for the staged configuration.
        Returns a dict containing the final symlinks that would be installed.
        """
        # { destination: (mod_name, source), ... }
        result: dict[str, tuple[str, Path]] = {}
        # Iterate through enabled mods in order.
        for mod in self.mods:
            mod.conflict = False
            mod.obsolete = True
        enabled_mods = [i for i in self.mods if i.enabled]
        for index, mod in enumerate(enabled_mods):
            # Iterate through the source files of the mod
            for src in mod.files:
                # Get the sanitized full path relative to the game.directory.
                if mod.fomod:
                    corrected_name = (
                        str(src).split(f"{mod.name}/ammo_fomod", 1)[-1].strip("/")
                    )
                else:
                    corrected_name = str(src).split(mod.name, 1)[-1].strip("/")

                dest = mod.install_dir / corrected_name

                # Add the sanitized full path to the stage, resolving
                # conflicts. Record whether a mod has conflicting files.
                dest = normalize(dest, self.game.directory)
                if dest in result:
                    conflicting_mod = [
                        i for i in enabled_mods[:index] if i.name == result[dest][0]
                    ]
                    if conflicting_mod and conflicting_mod[0].enabled:
                        mod.conflict = True
                        conflicting_mod[0].conflict = True
                result[dest] = (mod.name, src)

        # Record whether a mod is obsolete (all files are overwritten by other mods).
        for mod in enabled_mods:
            for name, src in result.values():
                if name == mod.name:
                    mod.obsolete = False
                    break

        plugin_names = []
        for mod in self.mods:
            if mod.enabled:
                plugin_names.extend(mod.plugins)
        for plugin in self.plugins:
            plugin.conflict = False
            if plugin_names.count(plugin.name.lower()) > 1:
                plugin.conflict = True

        return result

    def _remove_empty_dirs(self):
        """
        Removes empty folders.
        """
        for dirpath, dirnames, _ in list(os.walk(self.game.directory, topdown=False)):
            for dirname in dirnames:
                d = Path(dirpath) / dirname
                try:
                    d.resolve().rmdir()
                except OSError:
                    pass

    def _clean_game_dir(self):
        """
        Removes all links and deletes empty folders.
        """
        for dirpath, _, filenames in os.walk(self.game.directory):
            d = Path(dirpath)
            for file in filenames:
                full_path = d / file
                if full_path.is_symlink():
                    try:
                        full_path.unlink()
                    except FileNotFoundError:
                        pass

        self._remove_empty_dirs()

    def configure(self, index: int) -> None:
        """
        Configure a fomod
        """
        # This has to run a hard refresh for now, so warn if there are uncommitted changes
        if self.changes is True:
            raise Warning("You must `commit` changes before configuring a fomod.")

        # Since there must be a hard refresh after the fomod wizard to load the mod's new
        # files, deactivate this mod and commit changes. This prevents a scenario where
        # the user could re-configure a fomod (thereby changing mod.location/self.game.data.name),
        # and quit ammo without running 'commit', which could leave broken symlinks in their
        # game.directory.

        mod = self.mods[index]
        if not mod.fomod:
            raise Warning("Only fomods can be configured.")

        assert mod.modconf is not None

        self.deactivate(ComponentEnum.MOD, index)
        self.commit()
        self.refresh()

        # Clean up previous configuration, if it exists.
        try:
            shutil.rmtree(mod.location / "ammo_fomod" / self.game.data.name)
        except FileNotFoundError:
            pass

        # We need to instantiate a FomodController and run it against the UI.
        # This will be a new instance of the UI.
        fomod_controller = FomodController(mod)
        ui = UI(fomod_controller)
        # ui read/execute/print/loop will break from its loop when the user
        # exits or advances past the last page of the fomod config wizard.
        ui.repl()

        # If we can rebuild the "files" property of the mod, refreshing the controller
        # and preventing configuration when there are unsaved changes
        # will no longer be required.
        self.refresh()

    def activate(self, component: ComponentEnum, index: Union[int, str]) -> None:
        """
        Enabled components will be loaded by game
        """
        try:
            int(index)
        except ValueError:
            if index != "all":
                raise Warning(f"Expected int, got '{index}'")

        if index == "all":
            for i in range(len(self.__dict__[f"{component.value}s"])):
                if self.__dict__[f"{component.value}s"][i].visible:
                    self._set_component_state(component, i, True)
        else:
            try:
                self._set_component_state(component, index, True)
            except IndexError as e:
                # Demote IndexErrors
                raise Warning(e)
        self._stage()

    def deactivate(self, component: ComponentEnum, index: Union[int, str]) -> None:
        """
        Disabled components will not be loaded by game
        """
        try:
            int(index)
        except ValueError:
            if index != "all":
                raise Warning(f"Expected int, got '{index}'")

        if index == "all":
            for i in range(len(self.__dict__[f"{component.value}s"])):
                if self.__dict__[f"{component.value}s"][i].visible:
                    self._set_component_state(component, i, False)
        else:
            try:
                self._set_component_state(component, index, False)
            except IndexError as e:
                # Demote IndexErrors
                raise Warning(e)
        self._stage()

    def sort(self) -> None:
        """
        Arrange plugins by mod order
        """
        plugins = []
        for mod in self.mods[::-1]:
            if not mod.enabled:
                continue
            for plugin in self.plugins[::-1]:
                for plugin_name in mod.plugins:
                    if plugin.name == plugin_name and plugin.name not in (
                        i.name for i in plugins
                    ):
                        plugins.insert(0, plugin)
                        break
        result = []
        for plugin in list(plugins):
            if any([plugin.name.lower().endswith(i) for i in [".esl", ".esm"]]):
                result.append(plugins.pop(plugins.index(plugin)))

        result.extend(plugins)

        if self.changes is False:
            self.changes = self.plugins != result
        self.plugins = result

    def rename(self, component: RenameEnum, index: int, name: str) -> None:
        """
        Names may contain alphanumerics and underscores
        """
        if component not in list(RenameEnum):
            raise Warning(
                f"Can only rename components of types {[i.value for i in list(RenameEnum)]}, not {component}"
            )
        if self.changes is True:
            raise Warning("You must `commit` changes before renaming.")

        if name != "".join([i for i in name if i.isalnum() or i == "_"]):
            raise Warning(
                "Names can only contain alphanumeric characters or underscores"
            )

        forbidden_names = []
        for i in self.game.data.parts:
            forbidden_names.append(i.lower())
        if name.lower() in forbidden_names:
            raise Warning(
                f"Choose something else. These names are forbidden: {forbidden_names}"
            )

        match component:
            case RenameEnum.DOWNLOAD:
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
                self.refresh()

            case RenameEnum.MOD:
                try:
                    mod = self.mods[index]
                except IndexError as e:
                    raise Warning(e)

                new_location = self.game.ammo_mods_dir / name
                if new_location.exists():
                    raise Warning(f"A mod named {str(new_location)} already exists!")

                # Remove symlinks instead of breaking them.
                self._clean_game_dir()

                # Move the folder, update the mod.
                mod.location.rename(new_location)
                mod.location = new_location
                mod.name = name

                # re-assess mod files
                mod.__post_init__()

                # re-install symlinks
                self.commit()

    def delete(self, component: DeleteEnum, index: Union[int, str]) -> None:
        """
        Removes specified file from the filesystem
        """
        if not isinstance(component, DeleteEnum):
            raise TypeError(
                f"Expected DeleteEnum, got '{component}' of type '{type(component)}'"
            )
        if self.changes is True:
            raise Warning("You must `commit` changes before deleting files.")
        try:
            index = int(index)
        except ValueError:
            if index != "all":
                raise Warning(f"Expected int, got '{index}'")

        match component:
            case DeleteEnum.MOD:
                if index == "all":
                    deleted_mods = ""
                    visible_mods = [i for i in self.mods if i.visible]
                    # Don't allow deleting mods with "all" unless they're inactive.
                    for mod in visible_mods:
                        if mod.enabled:
                            raise Warning(
                                "You must deactivate all visible components of that type before deleting them with all."
                            )
                    for mod in visible_mods:
                        self.deactivate(ComponentEnum.MOD, self.mods.index(mod))
                    for mod in visible_mods:
                        self.mods.pop(self.mods.index(mod))
                        try:
                            shutil.rmtree(mod.location)
                        except FileNotFoundError:
                            pass
                        deleted_mods += f"{mod.name}\n"
                    self.commit()
                else:
                    try:
                        self.deactivate(ComponentEnum.MOD, index)

                    except IndexError as e:
                        # Demote IndexErrors
                        raise Warning(e)

                    # Remove the mod from the controller then delete it.
                    mod = self.mods.pop(index)
                    try:
                        shutil.rmtree(mod.location)
                    except FileNotFoundError:
                        pass
                    self.commit()

            case DeleteEnum.PLUGIN:

                def get_plugin_files(plugin):
                    """
                    Get plugin files from all enabled mods.
                    """
                    for mod in self.mods:
                        if not mod.enabled:
                            continue
                        if plugin.name in mod.plugins:
                            for file in mod.files:
                                if all(
                                    (
                                        file.name == plugin.name and not file.is_dir(),
                                        file.parent == mod.location
                                        or file.parent.name.lower()
                                        == self.game.data.name.lower(),
                                    )
                                ):
                                    yield file
                                    break

                if index == "all":
                    deleted_plugins = ""
                    visible_plugins = [i for i in self.plugins if i.visible]
                    for plugin in visible_plugins:
                        if plugin.enabled:
                            raise Warning(
                                "You must deactivate all visible components of that type before deleting them with all."
                            )

                    for plugin in visible_plugins:
                        if plugin.mod is None or plugin.name in (
                            p.name for p in self.dlc
                        ):
                            self.refresh()
                            self.commit()
                        self.plugins.pop(self.plugins.index(plugin))
                        for file in get_plugin_files(plugin):
                            try:
                                file.unlink()
                            except FileNotFoundError:
                                pass
                        deleted_plugins += f"{plugin.name}\n"
                    self.refresh()
                    self.commit()
                else:
                    try:
                        plugin = self.plugins.pop(index)
                        for file in get_plugin_files(plugin):
                            try:
                                file.unlink()
                            except FileNotFoundError:
                                pass
                    except IndexError as e:
                        raise Warning(e)

                    self.refresh()
                    self.commit()

            case DeleteEnum.DOWNLOAD:
                if index == "all":
                    visible_downloads = [i for i in self.downloads if i.visible]
                    for visible_download in visible_downloads:
                        download = self.downloads.pop(
                            self.downloads.index(visible_download)
                        )
                        try:
                            download.location.unlink()
                        except FileNotFoundError:
                            pass
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
        Extract and manage an archive from ~/Downloads
        """
        if self.changes is True:
            raise Warning("You must `commit` changes before installing a mod.")

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
                    files[0].name.lower() != self.game.data.name.lower(),
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
            extract_to = self.game.ammo_mods_dir / extract_to
            if extract_to.exists():
                raise Warning(
                    f"Extraction of {index} failed since mod '{extract_to.name}' exists."
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
                # This is needed for mods like skse that have a version directory
                # between the mod's base folder and the self.game.data.name folder.
                for file in next(extract_to.iterdir()).iterdir():
                    file.rename(extract_to / file.name)

            # Add the freshly install mod to self.mods so that an error doesn't prevent
            # any successfully installed mods from appearing during 'install all'.
            self.mods.append(
                Mod(
                    location=extract_to,
                    game_root=self.game.directory,
                    game_data=self.game.data,
                )
            )

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

        self.refresh()

    def move(self, component: ComponentEnum, index: int, new_index: int) -> None:
        """
        Larger numbers win file conflicts
        """
        if not isinstance(component, ComponentEnum):
            raise TypeError(
                f"Expected ComponentEnum, got '{component}' of type '{type(component)}'"
            )
        components = self._get_validated_components(component)
        # Since this operation it not atomic, validation must be performed
        # before anything is attempted to ensure nothing can become mangled.
        if index == new_index:
            return
        if new_index > len(components) - 1:
            # Auto correct astronomical <to index> to max.
            new_index = len(components) - 1
        if index > len(components) - 1:
            raise Warning("Index out of range.")
        comp = components.pop(index)
        components.insert(new_index, comp)
        self._stage()
        self.changes = True

    def commit(self) -> None:
        """
        Apply pending changes
        """
        self._save_order()
        stage = self._stage()
        self._clean_game_dir()

        count = len(stage)
        skipped_files = []
        for i, (dest, source) in enumerate(stage.items()):
            (name, src) = source
            assert dest.is_absolute()
            assert src.is_absolute()
            Path.mkdir(dest.parent, parents=True, exist_ok=True)
            try:
                dest.symlink_to(src)
            except FileExistsError:
                skipped_files.append(
                    f"{name} skipped overwriting an unmanaged file: \
                        {str(dest).split(str(self.game.directory))[-1].lstrip('/')}."
                )
            finally:
                print(f"files processed: {i+1}/{count}", end="\r", flush=True)

        warn = ""
        for skipped_file in skipped_files:
            warn += f"{skipped_file}\n"

        # Don't leave empty folders lying around
        self._remove_empty_dirs()
        self.changes = False
        if warn:
            raise Warning(warn)

    def refresh(self) -> None:
        """
        Abandon pending changes
        """
        self.__init__(self.downloads_dir, self.game, *self.keywords)

    def collisions(self, index: int) -> None:
        """
        Show file conflicts for a mod
        """
        try:
            subject = self.mods[index]
        except IndexError as e:
            # Demote index errors
            raise Warning(e)

        if not subject.conflict:
            raise Warning("No conflicts.")

        def get_relative_files(mod):
            for src in mod.files:
                # Get the sanitized full path relative to the game.directory.
                if mod.fomod:
                    corrected_name = (
                        str(src).split(f"{mod.name}/ammo_fomod", 1)[-1].strip("/")
                    )
                else:
                    corrected_name = str(src).split(mod.name, 1)[-1].strip("/")

                if mod.install_dir.name == mod.game_data.name:
                    corrected_name = mod.game_data.name + f"/{corrected_name}"
                yield corrected_name

        enabled_mods = [i for i in self.mods if i.enabled and i.conflict]
        enabled_mod_names = [i.name for i in enabled_mods]
        subject_files = list(get_relative_files(subject))
        conflicts = {}

        for mod in enabled_mods:
            if mod.name == subject.name:
                continue
            for file in get_relative_files(mod):
                if file in subject_files:
                    if conflicts.get(file, None):
                        conflicts[file].append(mod.name)
                    else:
                        conflicts[file] = [mod.name, subject.name]

        result = ""
        for file, mods in conflicts.items():
            result += f"{file}\n"
            sorted_mods = sorted(mods, key=lambda x: enabled_mod_names.index(x))
            for index, mod in enumerate(sorted_mods):
                winner = "*" if index == len(sorted_mods) - 1 else " "
                result += f"  {winner} {mod}\n"

        raise Warning(result)

    def find(self, *keyword: str) -> None:
        """
        Show only components with any keyword
        """
        self.keywords = [*keyword]

        for component in self.mods + self.plugins + self.downloads:
            component.visible = True
            name = component.name.lower()

            for kw in self.keywords:
                component.visible = False

                # Hack to filter by fomods
                if kw.lower() == "fomods" and isinstance(component, Mod):
                    if component.fomod:
                        component.visible = True

                if name.count(kw.lower()):
                    component.visible = True

                # Show plugins of visible mods.
                if isinstance(component, Plugin):
                    if component.mod is not None:
                        if component.mod.name.lower().count(kw.lower()):
                            component.visible = True

                if component.visible:
                    break

        # Show mods that contain plugins named like the visible plugins.
        # This shows all associated mods, not just conflict winners.
        for plugin in [p for p in self.plugins if p.visible]:
            # We can't simply plugin.mod.visible = True because plugin.mod
            # does not care about conflict winners. This also means we can't break.
            for mod in self.mods:
                if plugin.name in mod.plugins:
                    mod.visible = True

        if len(self.keywords) == 1:
            kw = self.keywords[0].lower()
            if kw == "downloads":
                for component in self.mods + self.plugins:
                    component.visible = False
                for component in self.downloads:
                    component.visible = True

            if kw == "mods":
                for component in self.plugins + self.downloads:
                    component.visible = False
                for component in self.mods:
                    component.visible = True

            if kw == "plugins":
                for component in self.mods + self.downloads:
                    component.visible = False
                for component in self.plugins:
                    component.visible = True

    def tools(self) -> None:
        """
        Manage tools
        """
        tool_controller = ToolController(
            self.downloads_dir,
            self.game.ammo_conf.parent / "tools",
        )
        ui = UI(tool_controller)
        ui.repl()
