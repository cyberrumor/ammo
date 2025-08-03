#!/usr/bin/env python3
import os
import shutil
import readline
import logging
import textwrap
from collections.abc import Callable
from functools import wraps
from pathlib import Path
import typing
from typing import Union
from enum import (
    EnumMeta,
    StrEnum,
    auto,
)
from ammo.ui import UI
from ammo.component import (
    Game,
    Mod,
)
from ammo.lib import ignored
from .download import DownloadController
from .tool import ToolController
from .fomod import FomodController
from .bool_prompt import BoolPromptController

log = logging.getLogger(__name__)

# Filenames which won't contribute to collision detection.
IGNORE_COLLISIONS = {
    ".git",
    "LICENSE",
    "README.md",
    "fomod",
}


class ComponentWrite(StrEnum):
    MOD = auto()
    DOWNLOAD = auto()


class ComponentMove(StrEnum):
    MOD = auto()


class ModController(DownloadController):
    """
    ModController is responsible for managing mods. It exposes
    methods to the UI that allow the user to easily manage mods.
    """

    def __init__(self, downloads_dir: Path, game: Game, *keywords):
        super().__init__(downloads_dir, game)
        self.game: Game = game
        self.keywords = [*keywords]
        self.changes: bool = False
        self.mods: list[Mod] = []

        # Create required directories. Harmless if exists.
        Path.mkdir(self.game.ammo_mods_dir, parents=True, exist_ok=True)
        Path.mkdir(self.game.ammo_log.parent, parents=True, exist_ok=True)
        Path.mkdir(self.game.directory, parents=True, exist_ok=True)

        logging.basicConfig(filename=self.game.ammo_log, level=logging.INFO)
        log.info("initializing")

        self.populate_mods()
        self.populate_downloads()
        self.changes = False
        self.do_find(*self.keywords)
        self.stage()

    def get_mods(self):
        # Instance a Mod class for each mod folder in the mod directory.
        mods = []
        for path in self.game.ammo_mods_dir.iterdir():
            if path.is_dir():
                mod = Mod(
                    location=self.game.ammo_mods_dir / path.name,
                    game_root=self.game.directory,
                )
                mods.append(mod)
        return mods

    def populate_mods(self):
        """
        Populate self.mods in the correct order.
        """
        self.mods: list[Mod] = []
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

    def __str__(self) -> str:
        """
        Output a string representing all downloads, mods.
        """
        result = ""

        if self.keywords:
            result += "A filter is applied with `find` which may hide components.\n"
            result += "Running commands against `all` components will only affect\n"
            result += "the ones you can see.\n"
            result += "Execute `find` without arguments to remove the filter.\n\n"

        result += super().__str__()

        if len([i for i in self.mods if i.visible]):
            result += " index | Active | Mod name\n"
            result += "-------|--------|------------\n"
            for i, mod in enumerate(self.mods):
                if mod.visible:
                    priority = f"[{i}]"
                    enabled = f"[{mod.enabled}]"
                    conflict = (
                        "x"
                        if mod.enabled and mod.obsolete
                        else ("*" if mod.conflict else " ")
                    )
                    result += f"{priority:<7} {enabled:<7} {conflict:<1} {mod.name}\n"

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

        match func:
            case self.do_install.__func__:
                for i in range(len(self.downloads)):
                    if str(i).startswith(text):
                        completions.append(str(i))
                if "all".startswith(text) and len(self.downloads) > 1:
                    completions.append("all")

            case self.do_configure.__func__:
                for i in range(len(self.mods)):
                    if str(i).startswith(text):
                        if self.mods[i].fomod:
                            completions.append(str(i))

            case self.do_collisions.__func__:
                for i in range(len(self.mods)):
                    if str(i).startswith(text):
                        if self.mods[i].conflict:
                            completions.append(str(i))
        if completions:
            return completions[state] + " "

        type_hints = typing.get_type_hints(func)
        if buf.endswith(" "):
            target_type = list(type_hints.values())[len(args)]
        else:
            target_type = list(type_hints.values())[max(0, abs(len(args) - 1))]

        if hasattr(target_type, "__args__"):
            target_type = target_type.__args__

        if target_type == (int, str):
            # handle completing int or 'all' for functions that accept either.
            components = []
            if args[0] == "mod":
                components = self.mods
            elif args[0] == "download":
                components = self.downloads

            for i in range(len(components)):
                if str(i).startswith(text):
                    completions.append(str(i))
            if "all".startswith(text) and len(components) > 1:
                completions.append("all")

        if target_type is int:
            # Find valid ints for the rename and move commands.
            components = []
            if args[0] == "mod":
                components = self.mods
            elif args[0] == "download":
                components = self.downloads

            for i in range(len(components)):
                if str(i).startswith(text):
                    completions.append(str(i))

        if isinstance(target_type, EnumMeta):
            if target_type == ComponentWrite:
                # If we're renaming or deleting something,
                # and there's only one type of component available,
                # only autocomplete that component. Take care not
                # to switch a component a user has already typed though!
                if not len(args):
                    if (
                        self.mods
                        and not self.downloads
                        and ComponentWrite.MOD.value.startswith(text)
                    ):
                        completions.append(ComponentWrite.MOD.value)
                    if (
                        self.downloads
                        and not self.mods
                        and ComponentWrite.DOWNLOAD.value.startswith(text)
                    ):
                        completions.append(ComponentWrite.DOWNLOAD.value)

            if not completions:
                for i in list(target_type):
                    if i.value.startswith(text):
                        completions.append(i.value)

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
            for src, relative_dest in mod.files:
                if relative_dest.name in IGNORE_COLLISIONS:
                    continue
                if set(relative_dest.parts).intersection(IGNORE_COLLISIONS):
                    continue

                case_corrected_absolute_path = mod.install_dir / relative_dest
                if case_corrected_absolute_path in result:
                    conflicting_mod = [
                        i
                        for i in enabled_mods[:index]
                        if i.name == result[case_corrected_absolute_path][0]
                    ]
                    if conflicting_mod and conflicting_mod[0].enabled:
                        mod.conflict = True
                        conflicting_mod[0].conflict = True
                result[case_corrected_absolute_path] = (mod.name, src)

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
        for parent_dir, folders, _ in list(os.walk(self.game.directory, topdown=False)):
            parent_path = Path(parent_dir)
            for folder in folders:
                with ignored(OSError):
                    (parent_path / folder).resolve().rmdir()

    def clean_game_dir(self):
        """
        Removes all links and deletes empty folders.
        """
        for parent_dir, _, files in os.walk(self.game.directory):
            parent_path = Path(parent_dir)
            for file in files:
                full_path = parent_path / file
                if full_path.is_symlink():
                    with ignored(FileNotFoundError):
                        full_path.unlink()

        self.remove_empty_dirs()

    def has_extra_folder(self, path: Path) -> bool:
        """
        The only assumption that the generic mod.controller can reasonable make
        about whether extracted mods have an extra folder between the extraction
        dir and the actual contents that should be installed into the game dir
        is that there's no extra dir if the extraction dir contains a different
        number of directories than 1.

        Every other scenario needs to prompt the user.

        Game-specific subclasses may wish to override this in order to
        automatically correct common packaging mistakes, skipping the prompt.
        """
        contents = list(path.iterdir())
        if len(contents) != 1:
            # If there's more than one folder, we can't tell which folder we
            # should elevate files out of. If there's no folders, there's no
            # depth to elevate files out of.
            return False

        folders = [i for i in contents if i.is_dir()]
        if len(folders) != 1:
            return False

        subdir_contents = list(folders[0].iterdir())

        if any(p.name == folders[0].name for p in subdir_contents):
            # Returning True here would force trying to rename
            # extract_to / my_mod_dir / my_mod_dir
            # to
            # extract_to / my_mod_dir
            # which can't be done.
            return False

        display_subdir_contents = subdir_contents[0 : min(3, len(subdir_contents))]
        question = textwrap.dedent(
            f"""
            This mod contains a single directory.

            Mod files will be installed into the game directory like this:

            {self.game.directory}/
            └──{folders[0].name}/
                └──{"\n                └──".join(i.name for i in display_subdir_contents)}

            If files are elevated above '{folders[0].name}/',
            they will be installed into the game directory like this instead:

            {self.game.directory}/
            └──{"\n            └──".join(i.name for i in display_subdir_contents)}

            Elevate files above '{folders[0].name}/'?
            """
        )
        prompt_controller = BoolPromptController(question)
        ui = UI(prompt_controller)
        return ui.repl()

    def activate_mod(self, index: Union[int, str]) -> None:
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
                        # Activate the mod, unless it's an unconfigured fomod.
                        self.set_mod_state(i, True)
                    except Warning as e:
                        warnings.append(e)
        else:
            self.set_mod_state(index, True)

        self.stage()
        if warnings:
            raise Warning("\n".join(set([i.args[0] for i in warnings])))

    def do_activate(self, component: ComponentMove, index: Union[int, str]) -> None:
        """
        Enabled mods will be loaded by the game.
        """
        match component:
            case ComponentMove.MOD:
                return self.activate_mod(index)
            case _:
                raise Warning(
                    f"Expected one of {list(ComponentMove)} but got '{component}'"
                )

    def deactivate_mod(self, index: Union[int, str]) -> None:
        """
        Diabled mods will not be loaded by the game.
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

    def do_deactivate(self, component: ComponentMove, index: Union[int, str]) -> None:
        """
        Disabled mods will not be loaded by the game.
        """
        match component:
            case ComponentMove.MOD:
                return self.deactivate_mod(index)
            case _:
                raise Warning(
                    f"Expected one of {list(ComponentMove)} but got '{component}'"
                )

    def move_mod(self, index: int, new_index: int) -> None:
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

    def do_move(self, component: ComponentMove, index: int, new_index: int) -> None:
        """
        Larger numbers win file conflicts.
        """
        match component:
            case ComponentMove.MOD:
                return self.move_mod(index, new_index)
            case _:
                raise Warning(
                    f"Expected one of {list(ComponentMove)}, got '{component}'"
                )

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
                        {dest.relative_to(self.game.directory)}."
                )
            finally:
                print(f"files processed: {i + 1}/{count}", end="\r", flush=True)

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

        enabled_mods = [i for i in self.mods if i.enabled and i.conflict]
        enabled_mod_names = [i.name for i in enabled_mods]
        target_mod_files = [i[1] for i in target_mod.files]

        conflicts = {}

        for mod in enabled_mods:
            if mod.name == target_mod.name:
                continue
            for src, dest in mod.files:
                if dest in target_mod_files:
                    if dest in conflicts:
                        conflicts[dest].append(mod.name)
                    else:
                        conflicts[dest] = [mod.name, target_mod.name]

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
        n = 30
        if self.game.ammo_log.exists():
            with open(self.game.ammo_log, "r") as f:
                lines = f.readlines()
                _log = "".join(lines[-min(len(lines), n) :])

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

        self.deactivate_mod(index)
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
    def rename_download(self, index: int, name: str) -> None:
        """
        Names may contain alphanumerics, periods, and underscores.
        """
        # This function basically only exists so we can put the
        # requires_sync decorator on it.
        return super().rename_download(index, name)

    @requires_sync
    def rename_mod(self, index: int, name: str) -> None:
        """
        Names may contain alphanumerics, periods, and underscores.
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
        log.info(f"Renaming MOD {mod.name} to {name}")

        mod.location.rename(new_location)
        mod.location = new_location
        mod.name = name

        # re-assess mod files
        mod.__post_init__()

        # re-install symlinks
        self.do_commit()

    @requires_sync
    def do_rename(self, component: ComponentWrite, index: int, name: str) -> None:
        """
        Names may contain alphanumerics, periods, and underscores.
        """
        match component:
            case ComponentWrite.MOD:
                self.rename_mod(index, name)
            case ComponentWrite.DOWNLOAD:
                self.rename_download(index, name)
            case _:
                raise Warning(
                    f"Expected one of {list(ComponentWrite)}, got '{component}'"
                )

    @requires_sync
    def delete_mod(self, index: Union[int, str]) -> None:
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
                with ignored(FileNotFoundError):
                    log.info(f"Deleting MOD: {target_mod.name}")
                    shutil.rmtree(target_mod.location)
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
            with ignored(FileNotFoundError):
                log.info(f"Deleting MOD: {target_mod.name}")
                shutil.rmtree(target_mod.location)

            if originally_active:
                self.do_commit()

    @requires_sync
    def delete_download(self, index: Union[int, str]) -> None:
        """
        Removes specified download from the filesystem.
        """
        # This function basically only exists so we can put the
        # requires_sync decorator on it.
        return super().delete_download(index)

    @requires_sync
    def do_delete(self, component: ComponentWrite, index: Union[int, str]):
        """
        Removes specified component from the filesystem.
        """
        match component:
            case ComponentWrite.DOWNLOAD:
                self.delete_download(index)
            case ComponentWrite.MOD:
                self.delete_mod(index)
            case _:
                raise Warning(
                    f"Expected one of {list(ComponentWrite)}, got '{component}'"
                )

    @requires_sync
    def do_install(self, index: Union[int, str]) -> None:
        """
        Extract and manage an archive from ~/Downloads.
        """
        return super().install(index, self.game.ammo_mods_dir)

    @requires_sync
    def do_tools(self) -> None:
        """
        Manage tools.
        """
        tool_controller = ToolController(
            self.downloads_dir,
            self.game,
        )
        ui = UI(tool_controller)
        ui.repl()
        self.do_refresh()
