#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
from functools import reduce
from xml.etree import ElementTree
from .game import Game
from .mod import (
    Mod,
    Download,
    Plugin,
    DLC,
)


class Controller:
    def __init__(self, downloads_dir: Path, game: Game):
        self.downloads_dir: Path = downloads_dir
        self.game: Game = game
        self.changes: bool = False
        self.downloads: list[Download] = []
        self.mods: list[Mod] = []
        self.plugins: list[Plugin] = []

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

    def _save_order(self) -> bool:
        """
        Writes ammo.conf and Plugins.txt.
        """
        with open(self.game.plugin_file, "w") as file:
            for plugin in self.plugins:
                file.write(f"{'*' if plugin.enabled else ''}{plugin.name}\n")
        with open(self.game.ammo_conf, "w") as file:
            for mod in self.mods:
                file.write(f"{'*' if mod.enabled else ''}{mod.name}\n")
        return True

    def _get_validated_components(self, component_type: str) -> list:
        """
        Expects either the string "plugin" or the string "mod",
        and an index. If the index is within the valid range
        for that type of component, return that entire component list.
        Otherwise, return False.
        """
        if component_type not in ["plugin", "mod"]:
            raise TypeError

        components = self.plugins if component_type == "plugin" else self.mods
        return components

    def _set_component_state(
        self, component_type: str, mod_index: int, state: bool
    ) -> bool:
        """
        Activate or deactivate a component.
        If a mod with plugins was deactivated, remove those plugins from self.plugins
        if they aren't also provided by another mod.
        """
        components = self._get_validated_components(component_type)
        component = components[int(mod_index)]

        starting_state = component.enabled
        # Handle mods
        if isinstance(component, Mod):
            # Handle configuration of fomods
            if (
                hasattr(component, "fomod")
                and component.fomod
                and state
                and not component.has_data_dir
            ):
                print("Fomods must be configured before they can be enabled.")
                print(f"Please run 'configure {mod_index}', refresh, and try again.")
                return False

            component.enabled = state
            if component.enabled:
                # Show plugins owned by this mod
                for name in component.plugins:
                    if name not in [i.name for i in self.plugins]:
                        plugin = Plugin(name, False, component)
                        self.plugins.append(plugin)
            else:
                # Hide plugins owned by this mod and not another mod
                for plugin in component.associated_plugins(self.plugins):
                    provided_elsewhere = False
                    for mod in [i for i in self.mods if i.name != component.name]:
                        if plugin in mod.associated_plugins(self.plugins):
                            provided_elsewhere = True
                            break
                    if not provided_elsewhere:
                        plugin.enabled = False

                        if plugin in self.plugins:
                            self.plugins.remove(plugin)

        # Handle plugins
        if isinstance(component, Plugin):
            component.enabled = state

        self.changes = starting_state != component.enabled
        return True

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
                if "fomod" in corrected_name.lower():
                    continue

                # It is possible to make a mod install in the game.directory instead
                # of the data dir by setting mod.has_data_dir = True.
                if mod.has_data_dir:
                    dest = Path(
                        os.path.join(
                            self.game.directory,
                            corrected_name.replace("/data", "/Data").lstrip("/"),
                        )
                    )
                else:
                    dest = Path(
                        os.path.join(
                            self.game.directory,
                            "Data" + corrected_name,
                        )
                    )
                # Add the sanitized full path to the stage, resolving
                # conflicts.
                dest = self._normalize(dest, self.game.directory)
                result[dest] = (mod.name, src)

        return result

    def _clean_data_dir(self) -> bool:
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
        return True

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

            # convert the 'source' folder form the xml into a full path
            s = node.get("source")
            """
            full_source = reduce(
                lambda path, name: path / name.lower() if name.lower() in path.iterdir() else path / name,
                s.split("\\"),
                mod.location,
            )
            """
            full_source = mod.location
            for i in s.split("\\"):
                # i requires case-sensitivity correction because mod authors
                # might have said a resource was at "00 Core/Meshes" in
                # ModuleConfig.xml when the actual file itself might be
                # "00 Core/meshes".
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

            for dest, src in pre_stage.items():
                if dest.is_dir():
                    # Handle directories
                    for parent_dir, _folders, files in os.walk(dest):
                        for file in files:
                            source = Path(parent_dir) / str(file)
                            local_parent_dir = parent_dir.split(str(dest))[-1].strip(
                                "/"
                            )
                            destination = src / local_parent_dir / str(file)
                            stage[destination] = source
                else:
                    # Handle files
                    stage[src] = dest

        # install the new files
        for k, v in stage.items():
            Path.mkdir(k.parent, parents=True, exist_ok=True)
            assert (
                v.exists()
            ), f"expected {v} but it did not exist.\nWe were going to copy to {k}\n\nIssue with fomod configurator."
            shutil.copy(v, k)

        mod.has_data_dir = True

    def configure(self, index) -> bool:
        """
        Configure a fomod.
        """
        # This has to run a hard refresh for now, so warn if there are uncommitted changes
        assert self.changes is False

        # Since there must be a hard refresh after the fomod wizard to load the mod's new
        # files, deactivate this mod and commit changes. This prevents a scenario where
        # the user could re-configure a fomod (thereby changing mod.location/Data),
        # and quit ammo without running 'commit', which could leave broken symlinks in their
        # game.directoryectory.
        self.deactivate("mod", index)
        self.commit()
        self.refresh()

        mod = self.mods[int(index)]
        if not mod.fomod:
            raise TypeError

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
                return True

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

        if not (install_nodes := self._fomod_get_nodes(xml_root_node, steps, flags)):
            print("The configured options failed to map to installable components!")
            return False

        # Let the controller stage the chosen files and copy them to the mod's local Data dir.
        self._fomod_install_files(index, install_nodes)

        # If _fomod_install_files can rebuild the "files" property of the mod,
        # resetting the controller and preventing configuration when there are unsaved changes
        # will no longer be required.
        self.refresh()
        return True

    def activate(self, mod_or_plugin: Mod | Plugin, index) -> bool:
        """
        Enabled components will be loaded by game.
        """
        return self._set_component_state(mod_or_plugin, index, True)

    def deactivate(self, mod_or_plugin: Mod | Plugin, index) -> bool:
        """
        Disabled components will not be loaded by game.
        """
        return self._set_component_state(mod_or_plugin, index, False)

    def delete(self, mod_or_download: Mod | Download, index) -> bool:
        """
        Removes specified file from the filesystem.
        """
        assert self.changes is False

        if mod_or_download not in ["download", "mod"]:
            raise TypeError

        if mod_or_download == "mod":
            if not self.deactivate("mod", index):
                # validation error
                return False

            # Remove the mod from the controller then delete it.
            mod = self.mods.pop(int(index))
            shutil.rmtree(mod.location)
            self.commit()
        else:
            index = int(index)
            os.remove(self.downloads[index].location)
            self.downloads.pop(index)
        return True

    def install(self, index) -> bool:
        """
        Extract and manage an archive from ~/Downloads.
        """
        assert self.changes is False

        index = int(index)
        download = self.downloads[index]

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
            [i for i in os.path.splitext(download.name)[0] if i.isalnum() or i == "_"]
        ).strip("_")
        if not output_folder:
            output_folder = os.path.splitext(download.name)[0]

        extract_to = os.path.join(self.game.ammo_mods_dir, output_folder)
        if os.path.exists(extract_to):
            raise FileExistsError

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
            and os.path.splitext(extracted_files[0])[-1] not in [".esp", ".esl", ".esm"]
            and Path(os.path.join(extract_to, extracted_files[0])).is_dir()
        ):
            # It is reasonable to conclude an extra directory can be eliminated.
            # This is needed for mods like skse that have a version directory
            # between the mod's root folder and the Data folder.
            for file in os.listdir(os.path.join(extract_to, extracted_files[0])):
                filename = os.path.join(extract_to, extracted_files[0], file)
                shutil.move(filename, extract_to)

        self.refresh()
        return True

    def move(self, mod_or_plugin: Mod | Plugin, from_index, to_index) -> bool:
        """
        Larger numbers win file conflicts.
        """
        components = self._get_validated_components(mod_or_plugin)
        # Since this operation it not atomic, validation must be performed
        # before anything is attempted to ensure nothing can become mangled.
        old_ind = int(from_index)
        new_ind = int(to_index)
        if old_ind == new_ind:
            return True
        if new_ind > len(components) - 1:
            raise IndexError
        if old_ind > len(components) - 1:
            raise IndexError
        component = components.pop(old_ind)
        components.insert(new_ind, component)
        self.changes = True
        return True

    def vanilla(self) -> bool:
        """
        Disable all managed components and clean up.
        """
        print(
            "This will disable all mods and plugins, and remove all symlinks, \
                hardlinks, and empty folders from the game.directory."
        )
        print("ammo will remember th mod load order but not the plugin load order.")
        print("These changes will take place immediately.")
        if input("continue? [y/n]").lower() != "y":
            print("Not cleaned.")
            return False

        for mod in range(len(self.mods)):
            self._set_component_state("mod", mod, False)
        self._save_order()
        self._clean_data_dir()
        return True

    def commit(self) -> bool:
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
                # dest.hardlink_to(src)
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
        # Always return False so status messages persist.
        return False

    def refresh(self) -> bool:
        """
        Abandon pending changes.
        """
        self.__init__(self.downloads_dir, self.game)
        return True
