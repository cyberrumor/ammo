#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
from .ui import (
    UI,
    Controller,
)
from .fomod_controller import FomodController
from .game import Game
from .mod import (
    Mod,
    Download,
    Plugin,
    DLC,
    DeleteEnum,
    ComponentEnum,
)


class ModController(Controller):
    def __init__(self, downloads_dir: Path, game: Game, *args, **kwargs):
        self.downloads_dir: Path = downloads_dir
        self.game: Game = game
        self.changes: bool = False
        self.downloads: list[Download] = []
        self.mods: list[Mod] = []
        self.plugins: list[Plugin] = []
        self.keywords = [*args]

        # Create required directories for testing. Harmless if exists.
        Path.mkdir(self.game.ammo_mods_dir, parents=True, exist_ok=True)
        Path.mkdir(self.game.data, parents=True, exist_ok=True)

        # Instance a Mod class for each mod folder in the mod directory.
        mods = []
        Path.mkdir(self.game.ammo_mods_dir, parents=True, exist_ok=True)
        mod_folders = [i for i in self.game.ammo_mods_dir.iterdir() if i.is_dir()]
        for path in mod_folders:
            mod = Mod(
                path.name,
                location=self.game.ammo_mods_dir / path.name,
                parent_data_dir=self.game.data,
            )
            mods.append(mod)
        self.mods = mods

        # Read the game.ammo_conf file. If there's mods in it, put them in order.
        # Put mods that aren't listed in the game.ammo_conf file at the end.
        ordered_mods = []
        if self.game.ammo_conf.exists():
            with open(self.game.ammo_conf, "r") as file:
                for line in file:
                    if line.startswith("#"):
                        continue
                    name = line.strip("*").strip()
                    enabled = False
                    if line.startswith("*"):
                        enabled = True

                    if name not in [i.name for i in self.mods]:
                        continue

                    for mod in self.mods:
                        if mod.name == name:
                            mod.enabled = enabled
                            ordered_mods.append(mod)
                            break

            for mod in self.mods:
                if mod not in ordered_mods:
                    ordered_mods.append(mod)

            self.mods = ordered_mods

        # Read the DLCList.txt and Plugins.txt files.
        # Add Plugins from these files to the list of managed plugins,
        # with attention to the order and enabled state.
        # Create the plugins file if it didn't already exist.
        Path.mkdir(self.game.plugin_file.parent, parents=True, exist_ok=True)
        if not self.game.plugin_file.exists():
            with open(self.game.plugin_file, "w") as file:
                file.write("")

        # Detect whether DLCList.txt needs parsing.
        files_with_plugins: list[Path] = [self.game.plugin_file]
        if self.game.dlc_file.exists():
            files_with_plugins.append(self.game.dlc_file)

        for file_with_plugin in files_with_plugins:
            with open(file_with_plugin, "r") as file:
                for line in file:
                    # Empty lines, comments
                    if not line.strip() or line.startswith("#"):
                        continue

                    # Initially assign all plugin parents as a DLC.
                    # If the plugin has a parent mod, assign parent as that Mod.
                    # This is used to track ownership for when a mod is disabled.
                    name = line.strip("*").strip()

                    # Don't manage order of manually installed mods that were deleted.
                    if not (self.game.data / name).exists():
                        continue

                    parent_mod = DLC(name)
                    for mod in self.mods:
                        if name in mod.plugins:
                            parent_mod = mod
                            break

                    enabled = False
                    pre_existing = False
                    if line.startswith("*"):
                        enabled = True
                        # Attempt to enable the parent mod,
                        # Only do this if all that mod's files are present.
                        if parent_mod.files_in_place():
                            parent_mod.enabled = True

                        for plug in self.plugins:
                            # Enable DLC if it's already in the plugins list as enabled.
                            if plug.name == name:
                                plug.enabled = True
                                pre_existing = True
                                break

                    if pre_existing:
                        # This file was already added from DLCList.txt
                        continue

                    plugin = Plugin(name, enabled, parent_mod)
                    # Only manage plugins belonging to enabled mods.
                    if parent_mod.enabled and plugin.name not in [
                        i.name for i in self.plugins
                    ]:
                        self.plugins.append(plugin)

        # Populate self.downloads. Ignore downloads that have a '.part' file that
        # starts with the same name. This hides downloads that haven't completed yet.
        downloads: list[Path] = []
        for file in os.listdir(self.downloads_dir):
            still_downloading = False
            if any((file.endswith(ext) for ext in (".rar", ".zip", ".7z"))):
                for other_file in [
                    i
                    for i in os.listdir(self.downloads_dir)
                    if i.rsplit("-")[-1].strip(".part") in file
                ]:
                    if other_file.lower().endswith(".part"):
                        still_downloading = True
                        break
                if still_downloading:
                    continue
                download = Download(file, self.downloads_dir / file)
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
            result += "Downloads\n"
            result += "----------\n"

            for index, download in enumerate(self.downloads):
                if download.visible:
                    result += f"[{index}] {download}\n"
            result += "\n"

        for index, components in enumerate([self.mods, self.plugins]):
            result += (
                f" ### | Activated | {'Mod name' if index == 0 else 'Plugin name'}\n"
            )
            result += "-----|----------|-----\n"
            for priority, component in enumerate(components):
                if component.visible:
                    num = f"[{priority}]     "
                    length = len(str(priority)) + 1
                    num = num[0:-length]
                    result += f"{num} {component}\n"
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
        if component not in list(ComponentEnum):
            raise Warning(
                f"Can only do that with {[i.value for i in list(ComponentEnum)]}, not {component}"
            )

        components = self.plugins if component == ComponentEnum.PLUGIN else self.mods
        return components

    def _set_component_state(self, component: ComponentEnum, index: int, state: bool):
        """
        Activate or deactivate a component.
        If a mod with plugins was deactivated, remove those plugins from self.plugins
        if they aren't also provided by another mod.
        """
        if not isinstance(index, int):
            index = int(index)

        if not isinstance(component, ComponentEnum):
            raise TypeError(
                f"Expected ComponentEnum, got '{component}' of type '{type(component)}'"
            )

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
                and not subject.has_data_dir
            ):
                raise Warning("Fomods must be configured before they can be enabled.")

            subject.enabled = state
            if subject.enabled:
                # Show plugins owned by this mod
                for name in subject.plugins:
                    if name not in [i.name for i in self.plugins]:
                        plugin = Plugin(name, False, subject)
                        self.plugins.append(plugin)
            else:
                # Hide plugins owned by this mod and not another mod
                for plugin in subject.associated_plugins(self.plugins):
                    provided_elsewhere = False
                    for mod in [
                        i for i in self.mods if i.name != subject.name and i.enabled
                    ]:
                        if plugin in mod.associated_plugins(self.plugins):
                            provided_elsewhere = True
                            break
                    if not provided_elsewhere:
                        plugin.enabled = False

                        if plugin in self.plugins:
                            self.plugins.remove(plugin)

        # Handle plugins
        elif isinstance(subject, Plugin):
            subject.enabled = state
        else:
            raise NotImplementedError

        self.changes = starting_state != subject.enabled

    def _normalize(self, destination: Path, dest_prefix: Path) -> Path:
        """
        Prevent folders with the same name but different case
        from being created.
        """
        path = destination.parent
        file = destination.name
        local_path: str = str(path).split(str(dest_prefix))[-1].lower()
        for i in [
            "Data",
            "DynDOLOD",
            "Plugins",
            "SKSE",
            "Edit Scripts",
            "Docs",
            "Scripts",
            "Source",
        ]:
            local_path = local_path.replace(i.lower(), i)
        new_dest: Path = Path(dest_prefix / local_path.lstrip("/"))
        result = new_dest / file
        return result

    def _stage(self) -> dict:
        """
        Returns a dict containing the final symlinks that will be installed.
        """
        # destination: (mod_name, source)
        result = {}
        # Iterate through enabled mods in order.
        for mod in [i for i in self.mods if i.enabled]:
            # Iterate through the source files of the mod
            for src in mod.files.values():
                # Get the sanitized full path relative to the game.directory.
                corrected_name = str(src).split(mod.name, 1)[-1]

                # Don't install fomod folders.
                if corrected_name.lower() == "fomod":
                    continue

                # It is possible to make a mod install in the game.directory instead
                # of the data dir by setting mod.has_data_dir = True.
                dest = Path(
                    os.path.join(
                        self.game.directory,
                        "Data" + corrected_name,
                    )
                )
                if mod.has_data_dir:
                    dest = Path(
                        os.path.join(
                            self.game.directory,
                            corrected_name.replace("/data", "/Data").lstrip("/"),
                        )
                    )
                # Add the sanitized full path to the stage, resolving
                # conflicts.
                dest = self._normalize(dest, self.game.directory)
                result[dest] = (mod.name, src)

        return result

    def _clean_data_dir(self):
        """
        Removes all links and deletes empty folders.
        """
        # remove links
        for dirpath, _dirnames, filenames in os.walk(self.game.directory):
            d = Path(dirpath)
            for file in filenames:
                full_path = d / file
                if full_path.is_symlink():
                    full_path.unlink()
                elif os.stat(full_path).st_nlink > 1:
                    full_path.unlink()

        # remove empty directories
        def remove_empty_dirs(path: Path):
            for dirpath, dirnames, _filenames in list(os.walk(path, topdown=False)):
                for dirname in dirnames:
                    d = Path(dirname)
                    try:
                        (d / dirname).resolve().rmdir()
                    except OSError:
                        # directory wasn't empty, ignore this
                        pass

        remove_empty_dirs(self.game.directory)

    def configure(self, index: int):
        """
        Configure a fomod.
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

        self.deactivate(ComponentEnum("mod"), index)
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

    def activate(self, component: ComponentEnum, index: type[int | str]):
        """
        Enabled components will be loaded by game.
        """
        if component not in list(ComponentEnum):
            raise Warning("You can only activate mods or plugins")

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

    def deactivate(self, component: ComponentEnum, index: type[int | str]):
        """
        Disabled components will not be loaded by game.
        """
        if component not in list(ComponentEnum):
            raise Warning("You can only deactivate mods or plugins")

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

    def delete(self, component: DeleteEnum, index: type[int | str]):
        """
        Removes specified file from the filesystem.
        """
        if self.changes is True:
            raise Warning("You must `commit` changes before deleting a mod.")

        if component not in list(DeleteEnum):
            raise Warning(
                f"Can only delete components of types {[i.value for i in list(DeleteEnum)]}, not {component}"
            )

        try:
            index = int(index)
        except ValueError:
            if index != "all":
                raise Warning(f"Expected int, got '{index}'")

        if component == DeleteEnum.MOD:
            if index == "all":
                visible_mods = [i for i in self.mods if i.visible]
                for mod in visible_mods:
                    self.deactivate(ComponentEnum("mod"), self.mods.index(mod))
                for mod in visible_mods:
                    self.mods.pop(self.mods.index(mod))
                    shutil.rmtree(mod.location)
                return
            try:
                self.deactivate(ComponentEnum("mod"), index)
            except IndexError as e:
                # Demote IndexErrors
                raise Warning(e)

            # Remove the mod from the controller then delete it.
            mod = self.mods.pop(index)
            shutil.rmtree(mod.location)
            self.commit()

        elif component == DeleteEnum.DOWNLOAD:
            if index == "all":
                visible_downloads = [i for i in self.downloads if i.visible]
                for download in visible_downloads:
                    os.remove(self.downloads[self.downloads.index(download)].location)
                    self.downloads.pop(self.downloads.index(download))
                return
            index = int(index)
            try:
                download = self.downloads.pop(index)
            except IndexError as e:
                # Demote IndexErrors
                raise Warning(e)
            os.remove(download.location)
        else:
            raise Warning(f"Expected 'mod' or 'download' but got {component}")

    def install(self, index: type[int | str]):
        """
        Extract and manage an archive from ~/Downloads.
        """
        if self.changes is True:
            raise Warning("You must `commit` changes before installing a mod.")

        try:
            int(index)
        except ValueError:
            if index != "all":
                raise Warning(f"Expected int, got '{index}'")

        def install_download(download):
            if not download.sane:
                # Sanitize the download name to guarantee compatibility with 7z syntax.
                fixed_name = download.name.replace(" ", "_")
                fixed_name = "".join(
                    [i for i in fixed_name if i.isalnum() or i in [".", "_", "-"]]
                )
                parent_folder = os.path.split(download.location)[0]
                new_location = os.path.join(parent_folder, fixed_name)
                os.rename(download.location, new_location)
                download.location = new_location
                download.name = fixed_name
                download.sane = True

            # Get a decent name for the output folder.
            # This has to be done for a safe 7z call.
            output_folder = "".join(
                [
                    i
                    for i in os.path.splitext(download.name)[0]
                    if i.isalnum() or i == "_"
                ]
            ).strip("_")
            if not output_folder:
                output_folder = os.path.splitext(download.name)[0]

            extract_to = os.path.join(self.game.ammo_mods_dir, output_folder)
            if os.path.exists(extract_to):
                raise Warning(
                    "This mod appears to already be installed. Please delete it before reinstalling."
                )

            extracted_files = []
            os.system(f"7z x '{download.location}' -o'{extract_to}'")
            extracted_files = os.listdir(extract_to)

            if (
                len(extracted_files) == 1
                and extracted_files[0].lower()
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
                ]
                and os.path.splitext(extracted_files[0])[-1]
                not in [".esp", ".esl", ".esm"]
                and Path(os.path.join(extract_to, extracted_files[0])).is_dir()
            ):
                # It is reasonable to conclude an extra directory can be eliminated.
                # This is needed for mods like skse that have a version directory
                # between the mod's root folder and the Data folder.
                for file in os.listdir(os.path.join(extract_to, extracted_files[0])):
                    filename = os.path.join(extract_to, extracted_files[0], file)
                    shutil.move(filename, extract_to)

        if index == "all":
            for download in self.downloads:
                if download.visible:
                    install_download(download)
        else:
            index = int(index)
            try:
                download = self.downloads[index]
            except IndexError as e:
                # Demote IndexErrors
                raise Warning(e)

            install_download(download)

        self.refresh()

    def move(self, component: ComponentEnum, from_index: int, to_index: int):
        """
        Larger numbers win file conflicts.
        """
        components = self._get_validated_components(component)
        # Since this operation it not atomic, validation must be performed
        # before anything is attempted to ensure nothing can become mangled.
        old_ind = int(from_index)
        new_ind = int(to_index)
        if old_ind == new_ind:
            # no op
            return
        if new_ind > len(components) - 1:
            # Auto correct astronomical <to index> to max.
            new_ind = len(components) - 1
        if old_ind > len(components) - 1:
            raise Warning("Index out of range.")
        comp = components.pop(old_ind)
        components.insert(new_ind, comp)
        self.changes = True

    def commit(self):
        """
        Apply pending changes.
        """
        self._save_order()
        stage = self._stage()
        self._clean_data_dir()

        count = len(stage)
        skipped_files = []
        for index, (dest, source) in enumerate(stage.items()):
            Path.mkdir(dest.parent, parents=True, exist_ok=True)
            (name, src) = source
            try:
                dest.symlink_to(src)
            except FileExistsError:
                skipped_files.append(
                    f"{name} skipped overwriting an unmanaged file: \
                        {str(dest).split(str(self.game.directory))[-1].lstrip('/')}."
                )
            finally:
                print(f"files processed: {index+1}/{count}", end="\r", flush=True)
        print()
        for skipped_file in skipped_files:
            print(skipped_file)
        self.changes = False

    def refresh(self):
        """
        Abandon pending changes.
        """
        self.__init__(self.downloads_dir, self.game, *self.keywords)

    def find(self, *keyword: str):
        """
        Fuzzy filter. `find` without args removes filter.
        """
        self.keywords = [*keyword]

        for component in self.mods + self.plugins + self.downloads:
            component.visible = True
            name = component.name.lower()

            for kw in self.keywords:
                component.visible = False

                # Hack to filter by fomods
                if isinstance(component, Mod) and kw.lower() == "fomods":
                    if component.fomod:
                        component.visible = True

                if name.count(kw.lower()):
                    component.visible = True

                # Show plugins of visible mods.
                if isinstance(component, Plugin):
                    if component.parent_mod.name.lower().count(kw.lower()):
                        component.visible = True

                if component.visible:
                    break

        # Show mods that contain plugins named like the visible plugins.
        # This shows all associated mods, not just conflict winners.
        for plugin in [p for p in self.plugins if p.visible]:
            # We can't simply plugin.parent_mod.visible = True because parent_mod
            # does not care about conflict winners. This also means we can't break.
            for mod in self.mods:
                if plugin.name in mod.plugins:
                    mod.visible = True
