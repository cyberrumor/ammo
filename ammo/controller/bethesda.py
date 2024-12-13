#!/usr/bin/env python3
import readline
import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
import typing
from typing import Union
from enum import (
    EnumMeta,
)
from dataclasses import (
    dataclass,
    field,
)
from .mod import (
    ModController,
    Game,
)
from ammo.component import (
    Mod,
    Download,
    Plugin,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class BethesdaGame(Game):
    data: Path
    dlc_file: Path
    plugin_file: Path
    enabled_formula: Callable[[str], bool] = field(
        default=lambda line: line.strip().startswith("*")
    )


class BethesdaController(ModController):
    """
    ModController is responsible for managing mods. It exposes
    methods to the UI that allow the user to easily manage mods.
    """

    def __init__(self, downloads_dir: Path, game: Game, *keywords):
        # Bethesda attributes
        self.plugins: list[Plugin] = []
        self.dlc: list[Plugin] = []

        # Generic attributes
        super().__init__(downloads_dir, game, *keywords)

        # Create required directories. Harmless if exists.
        Path.mkdir(self.game.data, parents=True, exist_ok=True)
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
                    if name in (i.name for i in m.plugins):
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
        self.do_find(*self.keywords)
        self.stage()

    def __str__(self) -> str:
        """
        Output a string representing all downloads, mods and plugins.
        """
        result = super().__str__()
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
                elif name.endswith("plugin"):
                    components = self.plugins

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

    def set_mod_state(self, index: int, desired_state: bool):
        """
        Activate or deactivate a mod.
        If a mod with plugins was deactivated, remove those plugins from self.plugins
        if they aren't also provided by another mod.
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
        if target_mod.enabled:
            # Show plugins owned by this mod
            for mod_plugin in target_mod.plugins:
                if mod_plugin.name not in (i.name for i in self.plugins):
                    plugin = Plugin(
                        name=mod_plugin.name,
                        mod=target_mod,
                        enabled=False,
                    )
                    self.plugins.append(plugin)
        else:
            # Hide plugins owned by this mod and not another mod
            for target_plugin in target_mod.plugins:
                if target_plugin.name not in (i.name for i in self.plugins):
                    continue
                provided_elsewhere = False
                for mod in self.mods:
                    if not mod.enabled:
                        continue
                    if target_mod == mod:
                        continue
                    if target_plugin.name in (i.name for i in mod.plugins):
                        provided_elsewhere = True
                        break
                if not provided_elsewhere:
                    index = [i.name for i in self.plugins].index(target_plugin.name)
                    self.plugins.pop(index)

        if not self.changes:
            self.changes = starting_state != target_mod.enabled

    def set_plugin_state(self, index: int, desired_state: bool):
        """
        Activate or deactivate a plugin.
        If a mod with plugins was deactivated, remove those plugins from self.plugins
        if they aren't also provided by another mod.
        """
        try:
            target_plugin = self.plugins[index]
        except IndexError as e:
            raise Warning(e)

        if not target_plugin.visible:
            raise Warning("You can only de/activate visible components.")

        starting_state = target_plugin.enabled
        # Handle plugins
        target_plugin.enabled = desired_state

        if not self.changes:
            self.changes = starting_state != target_plugin.enabled

    def do_activate_plugin(self, index: Union[int, str]) -> None:
        """
        Enabled plugins will be loaded by the game.
        """
        try:
            int(index)
        except ValueError as e:
            if index != "all":
                raise Warning(e)

        warnings = []

        if index == "all":
            for i in range(len(self.plugins)):
                if self.plugins[i].visible:
                    try:
                        self.set_plugin_state(i, True)
                    except Warning as e:
                        warnings.append(e)
        else:
            self.set_plugin_state(index, True)

        self.stage()
        if warnings:
            raise Warning("\n".join(set([i.args[0] for i in warnings])))

    def do_deactivate_plugin(self, index: Union[int, str]) -> None:
        """
        Disabled plugins will not be loaded by game.
        """
        try:
            int(index)
        except ValueError as e:
            if index != "all":
                raise Warning(e)

        if index == "all":
            for i in range(len(self.plugins)):
                if self.plugins[i].visible:
                    self.set_plugin_state(i, False)
        else:
            self.set_plugin_state(index, False)

        self.stage()

    def do_move_plugin(self, index: int, new_index: int) -> None:
        """
        Larger numbers win file conflicts.
        """
        # Since this operation it not atomic, validation must be performed
        # before anything is attempted to ensure nothing can become mangled.
        try:
            comp = self.plugins[index]
            new_index = int(new_index)
        except (ValueError, TypeError, IndexError) as e:
            raise Warning(e)

        if not comp.visible:
            raise Warning("You can only move visible components.")

        if index == new_index:
            return

        if new_index > len(self.plugins) - 1:
            # Auto correct astronomical <to index> to max.
            new_index = len(self.plugins) - 1

        log.info(f"moving PLUGIN {comp.name} from {index=} to {new_index=}")
        self.plugins.pop(index)
        self.plugins.insert(new_index, comp)
        self.stage()
        self.changes = True

    def do_find(self, *keyword: str) -> None:
        """
        Show only components with any keyword. Execute without args to show all.
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
                if plugin.name in (i.name for i in mod.plugins):
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

    def do_sort(self) -> None:
        """
        Arrange plugins by mod order.
        """
        plugins = []
        for mod in self.mods[::-1]:
            if not mod.enabled:
                continue
            for plugin in self.plugins[::-1]:
                for plugin_file in mod.plugins:
                    if plugin.name == plugin_file.name and plugin.name not in (
                        i.name for i in plugins
                    ):
                        plugins.insert(0, plugin)
                        break
        result = []
        for plugin in list(plugins):
            if any([plugin.name.lower().endswith(i) for i in [".esl", ".esm"]]):
                result.append(plugins.pop(plugins.index(plugin)))

        result.extend(plugins)
        for dlc in [plugin for plugin in self.plugins if plugin.mod is None][::-1]:
            result.insert(0, dlc)

        if self.changes is False:
            self.changes = self.plugins != result
        self.plugins = result

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
    def do_delete_plugin(self, index: Union[int, str]) -> None:
        """
        Removes specified plugin from the filesystem.
        """

        def get_plugin_files(plugin):
            """
            Get plugin files from all enabled mods.
            """
            for mod in self.mods:
                if not mod.enabled:
                    continue
                for file in mod.plugins:
                    if file.name == plugin.name:
                        yield file

        if index == "all":
            deleted_plugins = ""
            visible_plugins = [i for i in self.plugins if i.visible]
            for plugin in visible_plugins:
                if plugin.enabled:
                    raise Warning(
                        "You can only delete all visible components if they are all deactivated."
                    )

            for plugin in visible_plugins:
                if plugin.mod is None or plugin.name in (p.name for p in self.dlc):
                    self.do_refresh()
                    self.do_commit()
                self.plugins.remove(plugin)
                for file in get_plugin_files(plugin):
                    try:
                        log.info(f"Deleting PLUGIN: {file}")
                        file.unlink()
                    except FileNotFoundError:
                        pass
                deleted_plugins += f"{plugin.name}\n"
            self.do_refresh()
            self.do_commit()
        else:
            try:
                plugin = self.plugins[index]
            except (TypeError, IndexError) as e:
                raise Warning(e)
            if not plugin.visible:
                raise Warning("You can only delete visible components.")

            self.plugins.remove(plugin)
            for file in get_plugin_files(plugin):
                try:
                    log.info(f"Deleting PLUGIN: {file}")
                    file.unlink()
                except FileNotFoundError:
                    pass

            self.do_refresh()
            self.do_commit()
