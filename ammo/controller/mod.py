#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import readline
import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from dataclasses import dataclass
import typing
from typing import Union
from enum import (
    EnumMeta,
)
from ammo.ui import (
    UI,
    Controller,
)
from ammo.component import (
    Mod,
    Download,
)
from ammo.lib import (
    normalize,
)
from .tool import ToolController
from .fomod import FomodController

log = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class Game:
    ammo_conf: Path
    ammo_log: Path
    ammo_mods_dir: Path
    name: str
    directory: Path


class ModController(Controller):
    """
    ModController is responsible for managing mods. It exposes
    methods to the UI that allow the user to easily manage mods.
    """

    def __init__(self, downloads_dir: Path, game: Game, *keywords):
        self.downloads_dir: Path = downloads_dir
        self.game: Game = game
        self.keywords = [*keywords]
        self.changes: bool = False
        self.downloads: list[Download] = []
        self.mods: list[Mod] = []

        # Create required directories. Harmless if exists.
        Path.mkdir(self.game.ammo_mods_dir, parents=True, exist_ok=True)
        Path.mkdir(self.game.ammo_log.parent, parents=True, exist_ok=True)

        logging.basicConfig(filename=self.game.ammo_log, level=logging.INFO)
        log.info("initializing")

        mods = self.get_mods()
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

        downloads: list[Path] = []
        for file in self.downloads_dir.iterdir():
            if file.is_dir():
                continue
            if any(file.suffix.lower() == ext for ext in (".rar", ".zip", ".7z")):
                download = Download(file)
                downloads.append(download)
        self.downloads = downloads
        self.changes = False
        self.do_find(*self.keywords)
        self.stage()

    def get_mods(self):
        # Instance a Mod class for each mod folder in the mod directory.
        mods = []
        mod_folders = [i for i in self.game.ammo_mods_dir.iterdir() if i.is_dir()]
        for path in mod_folders:
            mod = Mod(
                location=self.game.ammo_mods_dir / path.name,
                game_root=self.game.directory,
            )
            mods.append(mod)
        return mods

    def __str__(self) -> str:
        """
        Output a string representing all downloads, mods.
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

        if not result:
            result = "\n"

        return result

    def prompt(self):
        changes = "*" if self.changes else "_"
        name = self.game.name
        return f"{name} >{changes}: "

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

        type_hints = typing.get_type_hints(func)
        if buf.endswith(" "):
            target_type = list(type_hints.values())[len(args)]
        else:
            target_type = list(type_hints.values())[max(0, abs(len(args) - 1))]

        if hasattr(target_type, "__args__"):
            if func not in [
                self.do_install.__func__,
                self.do_configure.__func__,
                self.do_collisions.__func__,
            ]:
                components = self.mods
                if name.endswith("download"):
                    components = self.downloads

                for i in range(len(components)):
                    if str(i).startswith(text):
                        completions.append(str(i))
                if "all".startswith(text):
                    completions.append("all")

        elif isinstance(target_type, EnumMeta):
            for i in list(target_type):
                if i.value.startswith(text):
                    completions.append(i.value)

        if func == self.do_install.__func__:
            for i in range(len(self.downloads)):
                if str(i).startswith(text):
                    completions.append(str(i))
            if "all".startswith(text) and len(self.downloads) > 0:
                completions.append("all")

        elif func == self.do_configure.__func__:
            for i in range(len(self.mods)):
                if str(i).startswith(text):
                    if self.mods[i].fomod:
                        completions.append(str(i))

        elif func == self.do_collisions.__func__:
            for i in range(len(self.mods)):
                if str(i).startswith(text):
                    if self.mods[i].conflict:
                        completions.append(str(i))

        return completions[state] + " "

    def save_order(self):
        """
        Writes ammo.conf.
        """
        with open(self.game.ammo_conf, "w") as file:
            for mod in self.mods:
                file.write(f"{'*' if mod.enabled else ''}{mod.name}\n")

    def set_mod_state(self, index: int, desired_state: bool):
        """
        Activate or deactivate a mod.
        """
        try:
            target_mod = self.mods[index]
        except IndexError as e:
            raise Warning(e)

        if not target_mod.visible:
            raise Warning("You can only de/activate visible components.")

        starting_state = target_mod.enabled
        # Handle configuration of fomods
        if (
            desired_state
            and target_mod.fomod
            and not (target_mod.location / "ammo_fomod").exists()
        ):
            raise Warning("Fomods must be configured before they can be enabled.")

        target_mod.enabled = desired_state
        if not self.changes:
            self.changes = starting_state != target_mod.enabled

    def stage(self) -> dict:
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

        return result

    def remove_empty_dirs(self):
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

    def clean_game_dir(self):
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

        self.remove_empty_dirs()

    def has_extra_folder(self, path) -> bool:
        files = list(path.iterdir())
        return all(
            [
                len(files) == 1,
                files[0].is_dir(),
            ]
        )

    def do_activate_mod(self, index: Union[int, str]) -> None:
        """
        Enabled mods will be loaded by game.
        """
        try:
            int(index)
        except ValueError as e:
            if index != "all":
                raise Warning(e)

        warnings = []

        if index == "all":
            for i in range(len(self.mods)):
                if self.mods[i].visible:
                    try:
                        self.set_mod_state(i, True)
                    except Warning as e:
                        warnings.append(e)
        else:
            self.set_mod_state(index, True)

        self.stage()
        if warnings:
            raise Warning("\n".join(set([i.args[0] for i in warnings])))

    def do_deactivate_mod(self, index: Union[int, str]) -> None:
        """
        Diabled mods will not be loaded by game.
        """
        try:
            int(index)
        except ValueError as e:
            if index != "all":
                raise Warning(e)

        if index == "all":
            for i in range(len(self.mods)):
                if self.mods[i].visible:
                    self.set_mod_state(i, False)
        else:
            self.set_mod_state(index, False)

        self.stage()

    def do_move_mod(self, index: int, new_index: int) -> None:
        """
        Larger numbers win file conflicts.
        """
        # Since this operation it not atomic, validation must be performed
        # before anything is attempted to ensure nothing can become mangled.
        try:
            comp = self.mods[index]
            new_index = int(new_index)
        except (ValueError, TypeError, IndexError) as e:
            raise Warning(e)

        if not comp.visible:
            raise Warning("You can only move visible components.")

        if index == new_index:
            return

        if new_index > len(self.mods) - 1:
            # Auto correct astronomical <to index> to max.
            new_index = len(self.mods) - 1

        log.info(f"moving MOD {comp.name} from {index=} to {new_index=}")
        self.mods.pop(index)
        self.mods.insert(new_index, comp)
        self.stage()
        self.changes = True

    def do_commit(self) -> None:
        """
        Apply pending changes.
        """
        log.info("Committing pending changes to storage")
        self.save_order()
        stage = self.stage()
        self.clean_game_dir()

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
        self.remove_empty_dirs()
        self.changes = False
        if warn:
            raise Warning(warn)

    def do_refresh(self) -> None:
        """
        Abandon pending changes.
        """
        self.__init__(self.downloads_dir, self.game, *self.keywords)

    def do_collisions(self, index: int) -> None:
        """
        Show file conflicts for a mod. Mods prefixed with asterisks
        have file conflicts. Mods prefixed with x install no files.
        """
        try:
            target_mod = self.mods[index]
        except (TypeError, IndexError) as e:
            raise Warning(e)

        if not target_mod.conflict:
            raise Warning("No conflicts.")

        def get_relative_files(mod: Mod):
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
                dest = normalize(dest, self.game.directory)
                dest = str(dest).split(str(self.game.directory), 1)[-1].strip("/")

                yield dest

        enabled_mods = [i for i in self.mods if i.enabled and i.conflict]
        enabled_mod_names = [i.name for i in enabled_mods]
        target_mod_files = list(get_relative_files(target_mod))
        conflicts = {}

        for mod in enabled_mods:
            if mod.name == target_mod.name:
                continue
            for file in get_relative_files(mod):
                if file in target_mod_files:
                    if conflicts.get(file, None):
                        conflicts[file].append(mod.name)
                    else:
                        conflicts[file] = [mod.name, target_mod.name]

        result = ""
        for file, mods in conflicts.items():
            result += f"{file}\n"
            sorted_mods = sorted(mods, key=lambda x: enabled_mod_names.index(x))
            for index, mod in enumerate(sorted_mods):
                winner = "*" if index == len(sorted_mods) - 1 else " "
                result += f"  {winner} {mod}\n"

        raise Warning(result)

    def do_find(self, *keyword: str) -> None:
        """
        Show only components with any keyword. Execute without args to show all.
        """
        self.keywords = [*keyword]

        for component in self.mods + self.downloads:
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

                if component.visible:
                    break

        if len(self.keywords) == 1:
            kw = self.keywords[0].lower()
            if kw == "downloads":
                for component in self.mods:
                    component.visible = False
                for component in self.downloads:
                    component.visible = True

            if kw == "mods":
                for component in self.downloads:
                    component.visible = False
                for component in self.mods:
                    component.visible = True

    def do_log(self) -> None:
        """
        Show debug log history.
        """
        _log = ""
        if self.game.ammo_log.exists():
            with open(self.game.ammo_log, "r") as f:
                _log = f.read()

        raise Warning(_log)

    def requires_sync(func: Callable) -> Callable:
        """
        Decorator which prevents decorated function from executing
        if self.changes is True.
        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.changes:
                raise Warning(
                    "Not executed. You must refresh or commit before doing that."
                )
            return func(self, *args, **kwargs)

        return wrapper

    @requires_sync
    def do_configure(self, index: int) -> None:
        """
        Configure a fomod.
        """
        # Since there must be a hard refresh after the fomod wizard to load the mod's new
        # files, deactivate this mod and commit changes. This prevents a scenario where
        # the user could re-configure a fomod (thereby changing mod.location/ammo_conf),
        # and quit ammo without running 'commit', which could leave broken symlinks in their
        # game.directory.

        try:
            mod = self.mods[index]
        except (TypeError, IndexError) as e:
            raise Warning(e)

        if not mod.visible:
            raise Warning("You can only configure visible mods.")
        if not mod.fomod:
            raise Warning("Only fomods can be configured.")

        assert mod.modconf is not None

        self.do_deactivate_mod(index)
        self.do_commit()
        self.do_refresh()

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
        self.do_refresh()

    @requires_sync
    def do_rename_download(self, index: int, name: str) -> None:
        """
        Names may contain alphanumerics and underscores.
        """
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

        try:
            download = self.downloads[index]
        except IndexError as e:
            raise Warning(e)

        if not download.visible:
            raise Warning("You can only rename visible components.")

        if "pytest" not in sys.modules:
            # Don't run this during tests because it's slow.
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

    @requires_sync
    def do_rename_mod(self, index: int, name: str) -> None:
        """
        Names may contain alphanumerics and underscores.
        """
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
        try:
            mod = self.mods[index]
        except IndexError as e:
            raise Warning(e)

        if not mod.visible:
            raise Warning("You can only rename visible components.")

        new_location = self.game.ammo_mods_dir / name
        if new_location.exists():
            raise Warning(f"A mod named {str(new_location)} already exists!")

        if mod.enabled:
            # Remove symlinks instead of breaking them in case something goes
            # wrong with the rename and ammo exits before it can commit.
            self.clean_game_dir()

        # Move the folder, update the mod.
        log.info(f"Renaming MOD {mod.location} to {new_location}")
        mod.location.rename(new_location)
        mod.location = new_location
        mod.name = name

        # re-assess mod files
        mod.__post_init__()

        # re-install symlinks
        self.do_commit()

    @requires_sync
    def do_delete_mod(self, index: Union[int, str]) -> None:
        """
        Removes specified mod from the filesystem.
        """
        try:
            index = int(index)
        except ValueError as e:
            if index != "all":
                raise Warning(e)

        if index == "all":
            deleted_mods = ""
            visible_mods = [i for i in self.mods if i.visible]
            # Don't allow deleting mods with "all" unless they're inactive.
            for mod in visible_mods:
                if mod.enabled:
                    raise Warning(
                        "You can only delete all visible components if they are all deactivated."
                    )
            for target_mod in visible_mods:
                # Deactivate the mod here in case set_mod_state is overridden and
                # provides any cleanup to the child (like removing plugins).
                # Then we don't have to override this in children which use plugins.
                self.set_mod_state(self.mods.index(target_mod), False)
                self.mods.remove(target_mod)
                try:
                    log.info(f"Deleting MOD: {target_mod.location}")
                    shutil.rmtree(target_mod.location)
                except FileNotFoundError:
                    pass
                deleted_mods += f"{target_mod.name}\n"
            self.do_commit()
        else:
            try:
                target_mod = self.mods[index]

            except IndexError as e:
                raise Warning(e)

            if not target_mod.visible:
                raise Warning("You can only delete visible components.")

            originally_active = target_mod.enabled

            # Remove the mod from the controller then delete it.
            self.set_mod_state(self.mods.index(target_mod), False)
            self.mods.pop(index)
            try:
                log.info(f"Deleting MOD: {target_mod.location}")
                shutil.rmtree(target_mod.location)
            except FileNotFoundError:
                pass

            if originally_active:
                self.do_commit()

    @requires_sync
    def do_delete_download(self, index: Union[int, str]) -> None:
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

    @requires_sync
    def do_install(self, index: Union[int, str]) -> None:
        """
        Extract and manage an archive from ~/Downloads.
        """
        try:
            int(index)
        except ValueError as e:
            if index != "all":
                raise Warning(e)

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

            # 7z CLI has a bug with filenames with apostrophes. shlex.quote won't work around this.
            # Rename the archive if it has an apostrophe in it.
            if "'" in download.location.name:
                new_location = (
                    download.location.parent / download.location.name.replace("'", "_")
                )
                download.location.rename(new_location)
                download.location = new_location
                download.name = new_location.name

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

            if self.has_extra_folder(extract_to):
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
                raise Warning(e)

            if not download.visible:
                raise Warning("You can only install visible downloads.")

            install_download(index, download)

        self.do_refresh()

    @requires_sync
    def do_tools(self) -> None:
        """
        Manage tools.
        """
        tool_controller = ToolController(
            self.downloads_dir,
            self.game.ammo_conf.parent / "tools",
        )
        ui = UI(tool_controller)
        ui.repl()
        self.do_refresh()