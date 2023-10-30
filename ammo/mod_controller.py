#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
from functools import reduce
from xml.etree import ElementTree
from .controller import Controller
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
            raise TypeError(f"Expected ComponentEnum, got '{component}' of type '{type(component)}'")

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
        Prevent folders with the same name but different case from being
        created.
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

    def _fomod_get_flags(self, steps) -> dict:
        """
        Expects a dictionary of fomod install steps.
        Returns a dictionary where keys are flag names and values
        are flag states.
        """
        flags = {}
        for step in steps.values():
            for plugin in step["plugins"]:
                if plugin["selected"]:
                    if not plugin["flags"]:
                        continue
                    for flag in plugin["flags"]:
                        flags[flag] = plugin["flags"][flag]
        return flags

    def _fomod_get_pages(self, steps: dict, flags: dict) -> list:
        """
        Returns a list of only fomod pages that should be visible,
        determined by the current flags.
        """
        # Determine which steps should be visible
        return [
            page
            for page in list(steps.keys())
            # if there's no condition for visibility, just show it.
            if not steps[page]["visible"]
            # if there's conditions, only include if the conditions are met.
            or self._fomod_flags_match(flags, steps[page]["visible"])
        ]

    def _fomod_get_steps(self, xml_root_node) -> dict:
        """
        Get a dictionary representing every install step for this fomod.
        """
        steps = {}
        # Find all the install steps
        for step in xml_root_node.find("installSteps"):
            for optional_file_groups in step:
                for group in optional_file_groups:
                    if not (group_of_plugins := group.find("plugins")):
                        # This step has no configurable plugins.
                        # Skip the false positive.
                        continue

                    step_name = group.get("name")
                    steps[step_name] = {}

                    this_step = steps[step_name]
                    this_step["type"] = group.get("type")
                    this_step["plugins"] = []
                    this_step["visible"] = {}

                    # Collect this step's visibility conditions. Associate it
                    # with the group instead of the step. This is inefficient
                    # but fits into the "each step is a page" paradigm better.
                    if visible := step.find("visible"):
                        if dependencies := visible.find("dependencies"):
                            dep_op = dependencies.get("operator")
                            if dep_op:
                                dep_op = dep_op.lower()
                            this_step["visible"]["operator"] = dep_op
                            for xml_flag in dependencies:
                                this_step["visible"][
                                    xml_flag.get("flag")
                                ] = xml_flag.get("value") in ["On", "1"]

                    plugins = this_step["plugins"]
                    for plugin_index, plugin in enumerate(group_of_plugins):
                        plug_dict = {}
                        plugin_name = plugin.get("name").strip()
                        plug_dict["name"] = plugin_name
                        if (description := plugin.find("description")) and description:
                            plug_dict["description"] = description.text.strip()
                        else:
                            plug_dict[
                                "description"
                            ] = "No description for this plugin was provided"
                        plug_dict["flags"] = {}
                        # Automatically mark the first option as selected when
                        # a selection is required.
                        plug_dict["selected"] = (
                            this_step["type"]
                            in ["SelectExactlyOne", "SelectAtLeastOne"]
                        ) and plugin_index == 0

                        # Interpret on/off or 1/0 as true/false
                        if conditional_flags := plugin.find("conditionFlags"):
                            for flag in conditional_flags:
                                # People use arbitrary flags here.
                                # Most commonly "On" or "1".
                                plug_dict["flags"][flag.get("name")] = flag.text in [
                                    "On",
                                    "1",
                                ]
                            plug_dict["conditional"] = True

                        else:
                            # There were no conditional flags, so this was an
                            # unconditional install.
                            plug_dict["conditional"] = False

                        plug_dict["files"] = []
                        if plugin_files := plugin.find("files"):
                            plug_dict["files"].extend(plugin_files)

                        plugins.append(plug_dict)

        return steps

    def _fomod_get_nodes(self, xml_root_node, steps: dict, flags: dict) -> list:
        """
        Expects xml root node for the fomod, a dictionary representing
        all install steps, and a dictionary representing configured flags.

        Returns a list of xml nodes for each folder that matched the
        configured flags.
        """
        # Determine which files need to be installed.
        selected_nodes = []

        # Normal files. If these were selected, install them unless flags
        # disqualify.
        for step in steps:
            for plugin in steps[step]["plugins"]:
                if plugin["selected"]:
                    if plugin["conditional"]:
                        # conditional normal file
                        expected_flags = plugin["flags"]
                        if self._fomod_flags_match(flags, expected_flags):
                            selected_nodes.extend(plugin["files"])
                        continue
                    # unconditional file install
                    selected_nodes.extend(plugin["files"])

        # include conditional file installs based on the user choice. These are
        # different from the normal_files with conditions because these
        # conditions are in a different part of the xml (they're after all the
        # install steps instead of within them).
        patterns = (
            xml_root_node.find("conditionalFileInstalls").find("patterns")
            if xml_root_node.find("conditionalFileInstalls")
            else []
        )
        for pattern in patterns:
            dependencies = pattern.find("dependencies")
            dep_op = dependencies.get("operator")
            if dep_op:
                dep_op = dep_op.lower()
            expected_flags = {"operator": dep_op}
            for xml_flag in dependencies:
                expected_flags[xml_flag.get("flag")] = xml_flag.get("value") in [
                    "On",
                    "1",
                ]

            # xml_files is a list of folders. The folder objects contain the paths.
            xml_files = pattern.find("files")
            if not xml_files:
                # can't find files for this, no point in checking whether to include.
                continue

            if not expected_flags:
                # No requirements for these files to be used.
                selected_nodes.extend(xml_files)

            if self._fomod_flags_match(flags, expected_flags):
                selected_nodes.extend(xml_files)

        required_files = xml_root_node.find("requiredInstallFiles") or []
        for file in required_files:
            if file.tag == "files":
                selected_nodes.extend(file)
            else:
                selected_nodes.append(file)

        assert (
            len(selected_nodes) > 0
        ), "The selected options failed to map to installable components."
        return selected_nodes

    def _fomod_flags_match(self, flags: dict, expected_flags: dict) -> bool:
        """
        Compare actual flags with expected flags to determine whether
        the plugin associated with expected_flags should be included.

        Returns whether the plugin which owns expected_flags matches.
        """
        match = False
        for k, v in expected_flags.items():
            if k in flags:
                if flags[k] != v:
                    if (
                        "operator" in expected_flags
                        and expected_flags["operator"] == "and"
                    ):
                        # Mismatched flag. Skip this plugin.
                        return False
                    # if dep_op is "or" (or undefined), try the rest of these.
                    continue
                # A single match.
                match = True
        return match

    def _fomod_select(self, page: dict, selection: str):
        """
        Toggle the 'selected' switch on appropriate plugins.
        This logic ensures any constraints on selections are obeyed.
        """
        val = not page["plugins"][selection]["selected"]
        if "SelectExactlyOne" == page["type"]:
            for i in range(len(page["plugins"])):
                page["plugins"][i]["selected"] = i == selection
        elif "SelectAtMostOne" == page["type"]:
            for i in range(len(page["plugins"])):
                page["plugins"][i]["selected"] = False
            page["plugins"][selection]["selected"] = val
        else:
            page["plugins"][selection]["selected"] = val

    def _fomod_install_files(self, index, selected_nodes: list):
        """
        Copy the chosen files 'selected_nodes' from given mod at 'index'
        to that mod's Data folder.
        """
        mod = self.mods[int(index)]
        data = mod.location / "Data"

        # delete the old configuration if it exists
        shutil.rmtree(data, ignore_errors=True)
        Path.mkdir(data, parents=True, exist_ok=True)

        stage = {}
        for node in selected_nodes:
            pre_stage = {}

            # convert the 'source' folder from the xml into a full path.
            # Use case sensitivity correction because mod authors
            # might have said a resource was at "00 Core/Meshes" in
            # ModuleConfig.xml when the actual file itself might be
            # "00 Core/meshes".
            s = node.get("source")
            """
            full_source = reduce(
                lambda path, name: path / name
                if any(map(lambda p: p.name == name, path.iterdir()))
                else path / name.lower(),
                s.split("\\"),
                mod.location,
            )
            """
            full_source = mod.location
            for i in s.split("\\"):
                folder = i
                for file in os.listdir(full_source):
                    if file.lower() == i.lower():
                        folder = file
                        break
                full_source = full_source / folder

            # get the 'destination' folder form the xml. This path is relative to Data.
            full_destination = reduce(
                lambda path, name: path / name,
                node.get("destination").split("\\"),
                data,
            )
            # TODO: this is broken :)
            # Normalize the capitalization of folder names

            full_destination = self._normalize(full_destination, data.parent)

            # Handle the mod's file conflicts that are caused by itself.
            # There's technically a priority clause in the fomod spec that
            # isn't implemented here yet.
            pre_stage[full_source] = full_destination

            for src, dest in pre_stage.items():
                if src.is_file():
                    stage[dest] = src
                    continue

                # Subsurface files require path localization.
                for parent_dir, _, files in os.walk(src):
                    for file in files:
                        # Determine the local directory structure
                        local_parent_dir = parent_dir.split(str(src))[-1].strip("/")

                        # Build the destination and source paths
                        destination = dest / local_parent_dir / file
                        source = Path(parent_dir) / file
                        stage[destination] = source

        # install the new files
        for k, v in stage.items():
            Path.mkdir(k.parent, parents=True, exist_ok=True)
            assert (
                v.exists()
            ), f"expected {v} but it did not exist.\nWe were going to copy to {k}\n\nIssue with fomod configurator."
            shutil.copy(v, k)

        mod.has_data_dir = True

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

        # Parse the fomod installer.
        tree = ElementTree.parse(str(mod.modconf))
        xml_root_node = tree.getroot()

        module_name = xml_root_node.find("moduleName").text
        steps = self._fomod_get_steps(xml_root_node)
        page_index = 0

        command_dict = {
            "<index>": "     Choose an option.",
            "info <index>": "Show the description for the selected option.",
            "exit": "        Abandon configuration of this fomod.",
            "n": "           Next page of the installer or complete installation.",
            "b": "           Back. Return to the previous page of the installer.",
        }

        while True:
            os.system("clear")
            # Evaluate the flags every loop to ensure the visible pages and selected options
            # are always up to date. This will ensure the proper files are chosen later as well.
            flags = self._fomod_get_flags(steps)

            visible_pages = self._fomod_get_pages(steps, flags)

            # Only exit loop after determining which flags are set and pages are shown.
            if page_index >= len(visible_pages):
                break

            info = False
            page = steps[visible_pages[page_index]]

            print(module_name)
            print("-----------------")
            print(
                f"Page {page_index + 1} / {len(visible_pages)}: {visible_pages[page_index]}"
            )
            print()

            print(" ### | Selected | Option Name")
            print("-----|----------|------------")
            for i, p in enumerate(page["plugins"]):
                num = f"[{i}]     "
                num = num[0:-1]
                enabled = "[True]     " if p["selected"] else "[False]    "
                print(f"{num} {enabled} {p['name']}")
            print()
            selection = input(f"{page['type']} >_: ").lower()

            if (not selection) or (
                selection not in command_dict and selection.isalpha()
            ):
                print()
                for k, v in command_dict.items():
                    print(f"{k} {v}")
                print()
                input("[Enter]")
                continue

            # Set a flag for 'info' command. This is so the index validation can be recycled.
            if selection.split() and "info" == selection.split()[0]:
                info = True

            if "exit" == selection:
                self.refresh()
                return

            if "n" == selection:
                page_index += 1
                continue

            if "b" == selection:
                page_index -= 1
                if page_index < 0:
                    page_index = 0
                    print("Can't go back from here.")
                    input("[Enter]")
                continue

            # Convert selection to int and validate.
            try:
                if selection.split():
                    selection = selection.split()[-1]

                selection = int(selection)
                if selection not in range(len(page["plugins"])):
                    print(f"Expected 0 through {len(page['plugins']) - 1} (inclusive)")
                    input("[Enter]")
                    continue

            except ValueError:
                print(f"Expected 0 through {len(page['plugins']) - 1} (inclusive)")
                input("[Enter]")
                continue

            if info:
                # Selection was valid argument for 'info' command.
                print()
                print(page["plugins"][selection]["description"])
                print()
                input("[Enter]")
                continue

            # Selection was a valid index command.
            # Whenever a plugin is unselected, re-assess all flags.
            self._fomod_select(page, selection)

        install_nodes = self._fomod_get_nodes(xml_root_node, steps, flags)

        # Let the controller stage the chosen files and copy them to the mod's local Data dir.
        self._fomod_install_files(index, install_nodes)

        # If _fomod_install_files can rebuild the "files" property of the mod,
        # resetting the controller and preventing configuration when there are unsaved changes
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
