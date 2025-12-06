#!/usr/bin/env python3
import readline
import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
import typing
from typing import Union
from enum import (
    auto,
    EnumMeta,
    StrEnum,
)
from ammo.component import (
    BethesdaMod,
    Plugin,
)
from ammo.lib import ignored
from ammo.component import BethesdaGame
from .mod import (
    ModController,
    ComponentWrite,
    InterfaceMode,
)

log = logging.getLogger(__name__)

NO_EXTRACT_DIRS = [
    "animations",
    "bashtags",
    "docs",
    "edit scripts",
    "grass",
    "interface",
    "lightplacer",
    "meshes",
    "misc",
    "netscriptframework",
    "oblivionremastered",
    "scripts",
    "seq",
    "shaders",
    "skse",
    "sounds",
    "strings",
    "textures",
    "voices",
]


SE_IGNORELIST = [
    "Dawnguard.esm",
    "Dragonborn.esm",
    "HearthFires.esm",
    "_ResourcePack.esl",
    "ccBGSSSE001-Fish.esm",
    "ccBGSSSE025-AdvDSGS.esm",
    "ccBGSSSE037-Curios.esl",
    "ccQDRSSE001-SurvivalMode.esl",
    "ccVSVSSE003-NecroArts.esl",
    "ccafdsse001-dwesanctuary.esm",
    "ccasvsse001-almsivi.esm",
    "ccbgssse002-exoticarrows.esl",
    "ccbgssse003-zombies.esl",
    "ccbgssse004-ruinsedge.esl",
    "ccbgssse005-goldbrand.esl",
    "ccbgssse006-stendarshammer.esl",
    "ccbgssse007-chrysamere.esl",
    "ccbgssse008-wraithguard.esl",
    "ccbgssse010-petdwarvenarmoredmudcrab.esl",
    "ccbgssse011-hrsarmrelvn.esl",
    "ccbgssse012-hrsarmrstl.esl",
    "ccbgssse013-dawnfang.esl",
    "ccbgssse014-spellpack01.esl",
    "ccbgssse016-umbra.esm",
    "ccbgssse018-shadowrend.esl",
    "ccbgssse019-staffofsheogorath.esl",
    "ccbgssse020-graycowl.esl",
    "ccbgssse021-lordsmail.esl",
    "ccbgssse025-advdsgs.esm",
    "ccbgssse031-advcyrus.esm",
    "ccbgssse034-mntuni.esl",
    "ccbgssse035-petnhound.esl",
    "ccbgssse036-petbwolf.esl",
    "ccbgssse037-curios.esl",
    "ccbgssse038-bowofshadows.esl",
    "ccbgssse040-advobgobs.esl",
    "ccbgssse041-netchleather.esl",
    "ccbgssse043-crosselv.esl",
    "ccbgssse045-hasedoki.esl",
    "ccbgssse050-ba_daedric.esl",
    "ccbgssse051-ba_daedricmail.esl",
    "ccbgssse052-ba_iron.esl",
    "ccbgssse053-ba_leather.esl",
    "ccbgssse054-ba_orcish.esl",
    "ccbgssse055-ba_orcishscaled.esl",
    "ccbgssse056-ba_silver.esl",
    "ccbgssse057-ba_stalhrim.esl",
    "ccbgssse058-ba_steel.esl",
    "ccbgssse059-ba_dragonplate.esl",
    "ccbgssse060-ba_dragonscale.esl",
    "ccbgssse061-ba_dwarven.esl",
    "ccbgssse062-ba_dwarvenmail.esl",
    "ccbgssse063-ba_ebony.esl",
    "ccbgssse064-ba_elven.esl",
    "ccbgssse066-staves.esl",
    "ccbgssse067-daedinv.esm",
    "ccbgssse068-bloodfall.esl",
    "ccbgssse069-contest.esl",
    "cccbhsse001-gaunt.esl",
    "ccedhsse001-norjewel.esl",
    "ccedhsse002-splkntset.esl",
    "ccedhsse003-redguard.esl",
    "cceejsse001-hstead.esm",
    "cceejsse002-tower.esl",
    "cceejsse003-hollow.esl",
    "cceejsse004-hall.esl",
    "cceejsse005-cave.esm",
    "ccffbsse001-imperialdragon.esl",
    "ccffbsse002-crossbowpack.esl",
    "ccfsvsse001-backpacks.esl",
    "cckrtsse001_altar.esl",
    "ccmtysse001-knightsofthenine.esl",
    "ccmtysse002-ve.esl",
    "ccpewsse002-armsofchaos.esl",
    "ccqdrsse002-firewood.esl",
    "ccrmssse001-necrohouse.esl",
    "cctwbsse001-puzzledungeon.esm",
    "ccvsvsse001-winter.esl",
    "ccvsvsse002-pets.esl",
    "ccvsvsse004-beafarmer.esl",
]


class ComponentDelete(StrEnum):
    MOD = auto()
    PLUGIN = auto()
    DOWNLOAD = auto()


class ComponentMove(StrEnum):
    MOD = auto()
    PLUGIN = auto()


class BethesdaController(ModController):
    """
    ModController is responsible for managing mods. It exposes
    methods to the UI that allow the user to easily manage mods.
    """

    def __init__(
        self,
        downloads_dir: Path,
        game: BethesdaGame,
        *keywords,
        interface_mode=InterfaceMode.LIST,
        reset_log=False,
    ):
        # Bethesda attributes
        self.plugins: list[Plugin] = []
        self.dlc: list[Plugin] = []

        # Generic attributes
        super().__init__(
            downloads_dir,
            game,
            *keywords,
            interface_mode=interface_mode,
            reset_log=reset_log,
        )

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

        # Finish adding DLC plugins from DLCList.txt that were missing from Plugins.txt.
        # These will be added as disabled and in an arbitrary order since they weren't
        # in Plugins.txt.
        for plugin in self.dlc:
            if plugin.mod is None and plugin.name not in (i.name for i in self.plugins):
                self.plugins.append(plugin)

        # Add plugins that were in mod folders but weren't listed in plugins.txt
        # or DLCList.txt.
        for mod in self.mods[::-1]:
            if not mod.enabled:
                continue
            for plugin in mod.plugins:
                if plugin.name not in (p.name for p in self.plugins):
                    self.plugins.append(
                        Plugin(
                            name=plugin.name,
                            mod=mod,
                            enabled=False,
                        )
                    )

        # Add any remaining orphaned plugins.
        for file in self.game.data.iterdir():
            if file.is_symlink():
                continue
            if file.is_dir():
                continue
            if file.suffix.lower() not in (".esp", ".esm", ".esl"):
                continue
            if file.name in (plugin.name for plugin in self.plugins):
                continue

            # Neither Skyrim SE nor Skyrim LE supports having Skyrim.esm
            # or Update.esm in Plugins.txt.
            if file.name in (
                "Skyrim.esm",
                "Update.esm",
            ):
                continue

            if self.game.name.endswith("Special Edition"):
                # Skyrim SE / Enderal SE don't support disabling or reordering
                # DLC. The games just overwrite their plugins.txt file without
                # these files every time it launches, which would cause ammo to
                # append them as disabled to self.plugins.
                if file.name in SE_IGNORELIST:
                    continue

            self.plugins.append(
                Plugin(
                    name=file.name,
                    mod=None,
                    enabled=False,
                )
            )

        self.populate_downloads()
        self.changes = False
        self.do_find(*self.keywords)
        self.stage()

    def get_mods(self):
        """
        Instance a Mod class for each mod folder in the mod directory.

        This method is called by self.populate_mods which is defined in
        the parent class ModController.
        """
        mods = []
        for path in self.game.ammo_mods_dir.iterdir():
            if path.is_dir():
                mod = BethesdaMod(
                    location=path,
                    game_root=self.game.directory,
                    game_data=self.game.data,
                    game_pak=self.game.pak,
                    game_dll=self.game.dll
                    if self.game.name == "Oblivion Remastered"
                    else self.game.directory,
                )
                mods.append(mod)
        return mods

    def __str__(self) -> str:
        """
        Output a string representing all downloads, mods and plugins.
        """
        result = super().__str__()
        if len([i for i in self.plugins if i.visible]):
            result += "\n"
            result += " index | Active | Plugin name\n"
            result += "-------|--------|------------\n"
            for i, plugin in enumerate(self.plugins):
                if plugin.visible:
                    priority = f"[{i}]"
                    enabled = f"[{plugin.enabled}]"
                    conflict = "*" if plugin.conflict else " "
                    result += (
                        f"{priority:<7} {enabled:<7} {conflict:<1} {plugin.name}\n"
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
            elif args[0] == "plugin":
                components = self.plugins

            for i in range(len(components)):
                if str(i).startswith(text):
                    completions.append(str(i))
            if "all".startswith(text) and len(components) > 1:
                completions.append("all")

        if target_type is int:
            # handle rename and move
            components = []
            if args[0] == "download":
                components = self.downloads
            elif args[0] == "mod":
                components = self.mods
            elif args[0] == "plugin" and name != "rename":
                components = self.plugins

            for i in range(len(components)):
                if str(i).startswith(text):
                    completions.append(str(i))

        if isinstance(target_type, EnumMeta):
            if target_type == ComponentMove:
                # If we're activating, deactivating, or moving something,
                # and there's only one type of component, only autocomplete
                # that component. Take care not to switch a component a
                # user has already typed though!
                if not len(args):
                    if (
                        self.mods
                        and not self.plugins
                        and ComponentMove.MOD.value.startswith(text)
                    ):
                        completions.append(ComponentMove.MOD.value)
                    if (
                        self.plugins
                        and not self.mods
                        and ComponentMove.PLUGIN.value.startswith(text)
                    ):
                        completions.append(ComponentMove.PLUGIN.value)

            if target_type == ComponentDelete:
                # If we're deleting something and there's only one type of component
                # available, only autocomplete that component. Take care not to
                # switch a component a user has already typed though!
                if not len(args):
                    if (
                        self.mods
                        and not self.downloads
                        and not self.plugins
                        and ComponentDelete.MOD.value.startswith(text)
                    ):
                        completions.append(ComponentDelete.MOD.value)
                    if (
                        self.plugins
                        and not self.mods
                        and not self.downloads
                        and ComponentDelete.PLUGIN.value.startswith(text)
                    ):
                        completions.append(ComponentDelete.PLUGIN.value)
                    if (
                        self.downloads
                        and not self.mods
                        and not self.plugins
                        and ComponentDelete.DOWNLOAD.value.startswith(text)
                    ):
                        completions.append(ComponentDelete.DOWNLOAD.value)

            if target_type == ComponentWrite:
                # If we're renaming something and there's only one type fo component
                # available, only autocomplete that component. Take care not to
                # switch a component a user has already typed though!
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
                file.write(
                    f"{'*' if mod.enabled else ''}{mod.name}{' ' if mod.tags else ''}{' '.join(mod.tags)}\n"
                )

    def has_extra_folder(self, path) -> bool:
        """
        This method is called by self.do_install which is defined in
        the parent class ModController.
        """
        contents = list(path.iterdir())
        if len(contents) != 1:
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

        return all(
            [
                contents[0].name.lower() != self.game.data.name.lower(),
                contents[0].name.lower() not in NO_EXTRACT_DIRS,
                contents[0].suffix.lower() not in [".esp", ".esl", ".esm"],
            ]
        )

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

    def activate_plugin_all(self) -> None:
        for i, plugin in enumerate(self.plugins):
            if plugin.visible:
                self.set_plugin_state(i, True)
        self.stage()

    def activate_plugin(self, index: Union[int, str]) -> None:
        """
        Enabled plugins will be loaded by the game.
        """
        if index == "all":
            return self.activate_plugin_all()

        try:
            self.set_plugin_state(int(index), True)
            self.stage()
        except ValueError as e:
            raise Warning(e)

    def do_activate(self, component: ComponentMove, index: Union[int, str]) -> None:
        """
        Enabled components will be loaded by the game.
        """
        match component:
            case ComponentMove.PLUGIN:
                return self.activate_plugin(index)
            case ComponentMove.MOD:
                return self.activate_mod(index)
            case _:
                raise Warning(
                    f"Expected one of {list(ComponentMove)} but got '{component}'"
                )

    def deactivate_plugin_all(self) -> None:
        for i, plugin in enumerate(self.plugins):
            if plugin.visible:
                self.set_plugin_state(i, False)
        self.stage()

    def deactivate_plugin(self, index: Union[int, str]) -> None:
        """
        Disabled plugins will not be loaded by the game.
        """
        if index == "all":
            return self.deactivate_plugin_all()

        try:
            self.set_plugin_state(int(index), False)
            self.stage()
        except ValueError as e:
            raise Warning(e)

    def do_deactivate(self, component: ComponentMove, index: Union[int, str]) -> None:
        """
        Disabled components will not be loaded by the game.
        """
        match component:
            case ComponentMove.PLUGIN:
                return self.deactivate_plugin(index)
            case ComponentMove.MOD:
                return self.deactivate_mod(index)
            case _:
                raise Warning(
                    f"Expected one of {list(ComponentMove)} but got '{component}'"
                )

    def move_plugin(self, index: int, new_index: int) -> None:
        """
        Larger numbers win record conflicts.
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

    def do_move(self, component: ComponentMove, index: int, new_index: int) -> None:
        """
        Larger numbers win conflicts.
        """
        match component:
            case ComponentMove.PLUGIN:
                return self.move_plugin(index, new_index)
            case ComponentMove.MOD:
                return self.move_mod(index, new_index)
            case _:
                raise Warning(
                    f"Expected one of {list(ComponentMove)}, got '{component}'"
                )

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

                if hasattr(component, "tags"):
                    if kw in component.tags:
                        component.visible = True

                # Hack to filter by fomods
                if kw.lower() == "fomods" and isinstance(component, BethesdaMod):
                    if component.fomod:
                        component.visible = True

                if name.count(kw.lower()):
                    component.visible = True

                # Show plugins of visible mods.
                if isinstance(component, Plugin):
                    if component.mod is not None:
                        if component.mod.visible:
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
        Arrange plugins by mod-order.
        """
        # Get mod-owned plugins in mod-order.
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

        # Put DLC and orphaned plugins before mod-owned plugins. Ideally DLC would be
        # sorted to the front and orphaned plugins would go wherever the user put them,
        # but that would require distinguishing between DLC and orphaned plugins, which
        # is not possible for every game.
        for orphan in [plugin for plugin in self.plugins if plugin.mod is None][::-1]:
            if orphan.name not in (plugin.name for plugin in plugins):
                plugins.insert(0, orphan)

        # Get a new list with .esm plugins at the front, pulling .esm plugins
        # out of mod-added plugins list.
        result = []
        for plugin in list(plugins):
            if plugin.name.lower().endswith(".esm"):
                result.append(plugins.pop(plugins.index(plugin)))

        # Put .esl plugins next, pulling them out of mod-added plugins list.
        for plugin in list(plugins):
            if plugin.name.lower().endswith(".esl"):
                result.append(plugins.pop(plugins.index(plugin)))

        # Now the mod-added plugins list only contains .esp plugins.
        # Combine DLC/orphans with mod-added plugins.
        result.extend(plugins)

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
    def delete_plugin(self, index: Union[int, str]) -> None:
        """
        Removes specified plugin from the filesystem.
        """

        def get_plugin_file(plugin) -> Path:
            """
            Get the plugin file from the winning mod.
            """
            for mod in self.mods[::-1]:
                if not mod.enabled:
                    continue
                for file in mod.plugins:
                    if file.name == plugin.name:
                        return file

            # If we get this far, the plugin is DLC or an orphan.
            # Just generate the filename from game.data in this case.
            file = self.game.data / plugin.name
            return file

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
                if (file := get_plugin_file(plugin)) is not None:
                    with ignored(FileNotFoundError):
                        log.info(f"Deleting PLUGIN: {file}")
                        file.unlink()
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
            if (file := get_plugin_file(plugin)) is not None:
                with ignored(FileNotFoundError):
                    log.info(f"Deleting PLUGIN: {file}")
                    file.unlink()

            self.do_refresh()
            self.do_commit()

    def do_delete(self, component: ComponentDelete, index: Union[int, str]) -> None:
        """
        Removes the specified file from the filesystem.
        """
        match component:
            case ComponentDelete.MOD:
                return self.delete_mod(index)
            case ComponentDelete.PLUGIN:
                return self.delete_plugin(index)
            case ComponentDelete.DOWNLOAD:
                return self.delete_download(index)
            case _:
                raise Warning(
                    f"Expected one of {list(ComponentDelete)}, got '{component}'"
                )
