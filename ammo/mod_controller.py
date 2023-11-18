#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Union
from .ui import (
    UI,
    Controller,
)
from .fomod_controller import FomodController
from .component import (
    Mod,
    Download,
    Plugin,
    DeleteEnum,
    ComponentEnum,
)
from .lib import normalize


@dataclass(frozen=True)
class Game:
    name: str
    directory: Path
    data: Path
    ammo_conf: Path
    dlc_file: Path
    plugin_file: Path
    ammo_mods_dir: Path


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
        ordered_mods = []
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
                        ordered_mods.append(mod)
                        break

            # Put mods that aren't listed in self.game.ammo_conf file
            # at the end in an arbitrary order.
            for mod in mods:
                if mod not in ordered_mods:
                    ordered_mods.append(mod)

        # If ordered_mods is empty, the config either didn't exist or
        # had nothing in it. In either case just load up the mods made
        # from folders earlier. Otherwise use our ordered mods.
        self.mods = ordered_mods if ordered_mods else mods

        # Read the Plugins.txt and DLCList.txt files.
        # Add Plugins from these files to the list of managed plugins,
        # with attention to the order and enabled state.
        # Create the plugins file if it didn't already exist.
        Path.mkdir(self.game.plugin_file.parent, parents=True, exist_ok=True)
        if not self.game.plugin_file.exists():
            with open(self.game.plugin_file, "w") as file:
                file.write("")

        files_with_plugins: list[Path] = [self.game.plugin_file]
        if self.game.dlc_file.exists():
            files_with_plugins.append(self.game.dlc_file)

        for file_with_plugin in files_with_plugins:
            with open(file_with_plugin, "r") as file:
                for line in file:
                    if not line.strip() or line.strip().startswith("#"):
                        # Ignore empty lines and comments.
                        continue

                    name = line.strip().strip("*").strip()
                    enabled = line.strip().startswith("*")

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
                        if (self.game.data / name).exists() and not (
                            self.game.data / name
                        ).is_symlink():
                            plugin = Plugin(
                                name=name,
                                mod=mod,
                                enabled=enabled,
                            )
                            if plugin.name not in [p.name for p in self.plugins]:
                                self.plugins.append(plugin)
                        continue

                    if not mod.enabled:
                        # The parent mod either wasn't enabled or wasn't installed correctly.
                        # Don't add this plugin to the list of managed plugins. It will be
                        # added automatically when the parent mod is enabled.
                        continue

                    plugin_location = self.game.data / name
                    if not plugin_location.exists() or (
                        plugin_location.exists()
                        and not plugin_location.resolve().exists()
                    ):
                        enabled = False
                    plugin = Plugin(
                        name=name,
                        mod=mod,
                        enabled=enabled,
                    )
                    if plugin.name not in [p.name for p in self.plugins]:
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

    def __str__(self) -> str:
        """
        Output a string representing all downloads, mods and plugins.
        """
        result = ""
        if len(self.downloads):
            result += " index | Download\n"
            result += "-------|---------\n"

            for i, download in enumerate(self.downloads):
                if download.visible:
                    index = f"[{i}]"
                    result += f"{index:<7} {download.name}\n"
            result += "\n"

        for index, components in enumerate([self.mods, self.plugins]):
            result += (
                f" index | Activated | {'Mod name' if index == 0 else 'Plugin name'}\n"
            )
            result += "-------|-----------|------------\n"
            for i, component in enumerate(components):
                if component.visible:
                    priority = f"[{i}]"
                    enabled = f"[{component.enabled}]"
                    result += f"{priority:<7} {enabled:<11} {component.name}\n"
            if index == 0:
                result += "\n"
        return result

    def _prompt(self):
        changes = "*" if self.changes else "_"
        name = self.game.name
        return f"{name} >{changes}: "

    def _post_exec(self) -> bool:
        return False

    def _save_order(self):
        """
        Writes ammo.conf and Plugins.txt.
        """
        with open(self.game.plugin_file, "w") as file:
            for plugin in self.plugins:
                file.write(f"{'*' if plugin.enabled else ''}{plugin.name}\n")
        with open(self.game.ammo_conf, "w") as file:
            for mod in self.mods:
                file.write(f"{'*' if mod.enabled else ''}{mod.name}\n")

    def _get_validated_components(self, component: ComponentEnum) -> list:
        """
        Turn a ComponentEnum into either self.mods or self.plugins.
        """
        if not isinstance(component, ComponentEnum):
            raise TypeError(
                f"Expected {[i.value for i in list(ComponentEnum)]}, got {component} of type {type(component)}"
            )

        components = self.plugins if component == ComponentEnum.PLUGIN else self.mods
        return components

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
                hasattr(subject, "fomod")
                and subject.fomod
                and state
                and subject.install_dir != self.game.directory
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
                for plugin in (i for i in self.plugins if i.name in subject.plugins):
                    provided_elsewhere = False
                    for mod in (
                        i for i in self.mods if i.enabled and i.name != subject.name
                    ):
                        if plugin in (i for i in self.plugins if i.name in mod.plugins):
                            provided_elsewhere = True
                            break
                    if not provided_elsewhere:
                        if plugin in self.plugins:
                            self.plugins.remove(plugin)

        # Handle plugins
        elif isinstance(subject, Plugin):
            subject.enabled = state
        else:
            raise NotImplementedError

        if not self.changes:
            self.changes = starting_state != subject.enabled

    def _stage(self) -> dict:
        """
        Returns a dict containing the final symlinks that will be installed.
        """
        # destination: (mod_name, source)
        result = {}
        # Iterate through enabled mods in order.
        for mod in [i for i in self.mods if i.enabled]:
            # Iterate through the source files of the mod
            for src in mod.files:
                # Get the sanitized full path relative to the game.directory.
                corrected_name = str(src).split(mod.name, 1)[-1].strip("/")

                # Don't install fomod folders.
                if corrected_name.lower() == "fomod":
                    continue

                dest = mod.install_dir / corrected_name

                # Add the sanitized full path to the stage, resolving
                # conflicts.
                dest = normalize(dest, self.game.directory)
                result[dest] = (mod.name, src)

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

    def _clean_data_dir(self):
        """
        Removes all links and deletes empty folders.
        """
        for dirpath, _, filenames in os.walk(self.game.directory):
            d = Path(dirpath)
            for file in filenames:
                full_path = d / file
                if full_path.is_symlink():
                    full_path.unlink()

        self._remove_empty_dirs()

    def configure(self, index: int):
        """
        Configure a fomod
        """
        # This has to run a hard refresh for now, so warn if there are uncommitted changes
        if self.changes is True:
            raise Warning("You must `commit` changes before configuring a fomod.")

        # Since there must be a hard refresh after the fomod wizard to load the mod's new
        # files, deactivate this mod and commit changes. This prevents a scenario where
        # the user could re-configure a fomod (thereby changing mod.location/Data),
        # and quit ammo without running 'commit', which could leave broken symlinks in their
        # game.directoryectory.

        mod = self.mods[index]
        if not mod.fomod:
            raise Warning("Only fomods can be configured.")

        assert mod.modconf is not None

        self.deactivate(ComponentEnum.MOD, index)
        self.commit()
        self.refresh()

        # Clean up previous configuration, if it exists.
        try:
            shutil.rmtree(mod.location / "Data")
        except FileNotFoundError:
            pass

        # We need to instantiate a FomodController run it against the UI.
        # This will be a new instance of the UI. The old UI will wait for
        # this 'configure' function we're in to return.
        fomod_controller = FomodController(mod)
        ui = UI(fomod_controller)
        ui.repl()

        # If we can rebuild the "files" property of the mod, refreshing the controller
        # and preventing configuration when there are unsaved changes
        # will no longer be required.
        self.refresh()

    def activate(self, component: ComponentEnum, index: Union[int, str]):
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

    def deactivate(self, component: ComponentEnum, index: Union[int, str]):
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

    def rename(self, component: DeleteEnum, index: int, name: str):
        """
        Names may contain alphanumerics and underscores
        """
        if component not in list(DeleteEnum):
            raise Warning(
                f"Can only rename components of types {[i.value for i in list(DeleteEnum)]}, not {component}"
            )
        if self.changes is True:
            raise Warning("You must `commit` changes before renaming.")

        if name != "".join([i for i in name if i.isalnum() or i == "_"]):
            raise Warning(
                "Names can only contain alphanumeric characters or underscores"
            )

        if component == DeleteEnum.DOWNLOAD:
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
                raise Warning(f"Can't rename because download {new_location} exists.")

            download.location.rename(new_location)
            self.refresh()
            return

        assert component == DeleteEnum.MOD
        try:
            mod = self.mods[index]
        except IndexError as e:
            raise Warning(e)

        new_location = self.game.ammo_mods_dir / name
        if new_location.exists():
            raise Warning(f"A mod named {str(new_location)} already exists!")

        # Remove symlinks instead of breaking them.
        self._clean_data_dir()

        # Move the folder, update the mod.
        mod.location.rename(new_location)
        mod.location = new_location
        mod.name = name

        # re-assess mod files
        mod.__post_init__()

        # re-install symlinks
        self.commit()

    def delete(self, component: DeleteEnum, index: Union[int, str]):
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

        if component == DeleteEnum.MOD:
            deleted_mods = ""
            if index == "all":
                visible_mods = [i for i in self.mods if i.visible]
                for mod in visible_mods:
                    self.deactivate(ComponentEnum.MOD, self.mods.index(mod))
                for mod in visible_mods:
                    self.mods.pop(self.mods.index(mod))
                    shutil.rmtree(mod.location)
                    deleted_mods += f"{mod.name}\n"
                self.commit()
                raise Warning(f"Deleted mods:\n{deleted_mods}")
            try:
                self.deactivate(ComponentEnum.MOD, index)
            except IndexError as e:
                # Demote IndexErrors
                raise Warning(e)

            # Remove the mod from the controller then delete it.
            mod = self.mods.pop(index)
            shutil.rmtree(mod.location)
            self.commit()
            raise Warning(f"Deleted mod: {mod.name}")

        assert component == DeleteEnum.DOWNLOAD
        if index == "all":
            visible_downloads = [i for i in self.downloads if i.visible]
            for visible_download in visible_downloads:
                download = self.downloads.pop(self.downloads.index(visible_download))
                download.location.unlink()
            return
        index = int(index)
        try:
            download = self.downloads.pop(index)
        except IndexError as e:
            # Demote IndexErrors
            raise Warning(e)
        download.location.unlink()

    def install(self, index: Union[int, str]):
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

        def has_extra_folder(path):
            files = list(path.iterdir())
            return all(
                [
                    len(files) == 1,
                    files[0].is_dir(),
                    files[0].name.lower()
                    not in [
                        "data",
                        "skse",
                        "bashtags",
                        "docs",
                        "meshes",
                        "textures",
                        "animations",
                        "interface",
                        "misc",
                        "shaders",
                        "sounds",
                        "voices",
                        "edit scripts",
                    ],
                    files[0].suffix.lower() not in [".esp", ".esl", ".esm"],
                ]
            )

        def install_download(index, download):
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
                # between the mod's base folder and the Data folder.
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
            for index, download in enumerate(self.downloads):
                if download.visible:
                    try:
                        install_download(index, download)
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

    def move(self, component: ComponentEnum, index: int, new_index: int):
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
        components[index], components[new_index] = components[new_index], components[index]
        self.changes = True

    def commit(self):
        """
        Apply pending changes
        """
        self._save_order()
        stage = self._stage()
        self._clean_data_dir()

        count = len(stage)
        skipped_files = []
        for index, (dest, source) in enumerate(stage.items()):
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
                print(f"files processed: {index+1}/{count}", end="\r", flush=True)

        warn = ""
        for skipped_file in skipped_files:
            warn += f"{skipped_file}\n"

        # Don't leave empty folders lying around
        self._remove_empty_dirs()
        self.changes = False
        if warn:
            raise Warning(warn)

    def refresh(self):
        """
        Abandon pending changes
        """
        self.__init__(self.downloads_dir, self.game, *self.keywords)

    def find(self, *keyword: str):
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
                for component in self.mods:
                    component.visible = True
