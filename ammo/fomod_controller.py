#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
from xml.etree import ElementTree
from functools import reduce
from .ui import Controller
from .component import Mod


class FomodController(Controller):
    def __init__(self, mod: Mod):
        self.mod = mod

        # Parse the fomod installer.
        tree = ElementTree.parse(str(mod.modconf))

        # Get the root node
        self.xml_root_node = tree.getroot()

        # This is the name of the mod
        self.module_name = self.xml_root_node.find("moduleName").text

        # Get the pages
        self.steps = self._get_steps()
        self.page_index = 0
        self.flags = self._get_flags()
        self.visible_pages = self._get_pages()
        self.page = self.steps[self.visible_pages[self.page_index]]
        self.selection = self.page["type"].lower()
        self.do_exit = False

    def __str__(self) -> str:
        num_pages = len(self.visible_pages)
        result = f"{self.module_name}\n"
        result += "---------------\n"
        result += f"Page {self.page_index + 1} / {num_pages}: {self.visible_pages[self.page_index]}\n\n"
        result += " ### | Selected | Option Name\n"
        result += "-----|----------|------------\n"

        for i, p in enumerate(self.page["plugins"]):
            num = f"[{i}]    "
            num = num[0:-1]
            enabled = "[True]    " if p["selected"] else "[False]    "
            result += f"{num} {enabled} {p['name']}\n"
        result += "\n"
        return result

    def _prompt(self) -> str:
        return f"{self.selection} >_: "

    def _post_exec(self) -> bool:
        if self.do_exit:
            return True

        self.flags = self._get_flags()
        self.visible_pages = self._get_pages()
        if self.page_index >= len(self.visible_pages):
            # The user advanced to the end of the installer.
            install_nodes = self._get_nodes()
            self._install_files(install_nodes)
            return True

        self.page = self.steps[self.visible_pages[self.page_index]]
        self.selection = self.page["type"].lower()
        return False

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

    def _get_steps(self) -> dict:
        """
        Get a dictionary representing every install step for this fomod.
        """
        steps = {}
        # Find all the install steps
        for step in self.xml_root_node.find("installSteps"):
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

    def _get_flags(self) -> dict:
        """
        Expects a dictionary of fomod install steps.
        Returns a dictionary where keys are flag names
        and values are flag states.
        """
        flags = {}
        for step in self.steps.values():
            for plugin in step["plugins"]:
                if plugin["selected"]:
                    for flag in plugin.get("flags", ()):
                        flags[flag] = plugin["flags"][flag]
        return flags

    def _flags_match(self, expected_flags: dict) -> bool:
        """
        Compare actual flags with expected flags to determine whether
        the plugin associated with expected_flags should be included.

        Returns whether the plugin which owns expected_flags matches.
        """
        match = False
        for k, v in expected_flags.items():
            if k in self.flags:
                if self.flags[k] != v:
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

    def _select(self, index: int):
        """
        Toggle the 'selected' switch on appropriate plugins.
        This logic ensures any constraints on selections are obeyed.
        """
        val = not self.page["plugins"][index]["selected"]
        if "SelectExactlyOne" == self.page["type"]:
            for i in range(len(self.page["plugins"])):
                self.page["plugins"][i]["selected"] = i == index
        elif "SelectAtMostOne" == self.page["type"]:
            for i in range(len(self.page["plugins"])):
                self.page["plugins"][i]["selected"] = False
            self.page["plugins"][index]["selected"] = val
        else:
            self.page["plugins"][index]["selected"] = val

    def _get_pages(self) -> list:
        """
        Returns a list of only fomod pages that should be visible,
        determined by current flags.
        """
        return [
            page
            for page in self.steps
            # if there's no condition for visibility, just show it.
            if not self.steps[page]["visible"]
            # if there's conditions, only include if the conditions are met.
            or self._flags_match(self.steps[page]["visible"])
        ]

    def _get_nodes(self) -> list:
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
        for step in self.steps:
            for plugin in self.steps[step]["plugins"]:
                if plugin["selected"]:
                    if plugin["conditional"]:
                        # conditional normal file
                        expected_flags = plugin["flags"]
                        if self._flags_match(expected_flags):
                            selected_nodes.extend(plugin["files"])
                        continue
                    # unconditional file install
                    selected_nodes.extend(plugin["files"])

        # include conditional file installs based on the user choice. These are
        # different from the normal_files with conditions because these
        # conditions are in a different part of the xml (they're after all the
        # install steps instead of within them).
        patterns = (
            self.xml_root_node.find("conditionalFileInstalls").find("patterns")
            if self.xml_root_node.find("conditionalFileInstalls")
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

            if self._flags_match(expected_flags):
                selected_nodes.extend(xml_files)

        required_files = self.xml_root_node.find("requiredInstallFiles") or []
        for file in required_files:
            if file.tag == "files":
                selected_nodes.extend(file)
            else:
                selected_nodes.append(file)

        assert (
            len(selected_nodes) > 0
        ), "The selected options failed to map to installable components."
        return selected_nodes

    def _install_files(self, selected_nodes: list):
        """
        Copy the chosen files 'selected_nodes' from given mod at 'index'
        to that mod's Data folder.
        """
        data = self.mod.location / "Data"

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
            full_source = self.mod.location
            for i in s.split("\\"):
                folder = i
                for file in os.listdir(full_source):
                    if file.lower() == i.lower():
                        folder = file
                        break
                full_source = full_source / folder

            # get the 'destination' folder from the xml. This path is relative to Data.
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

        self.mod.has_data_dir = True

    def select(self, index: int):
        """
        Toggle state
        """
        if index < 0 or index > len(self.page["plugins"]):
            raise Warning(
                f"Expected 0 through {len(self.page['plugins']) - 1} (inclusive)"
            )

        self._select(index)

    def info(self, index: int):
        """
        Display description
        """
        if index < 0 or index > len(self.page["plugins"]):
            raise Warning(
                f"Expected 0 through {len(self.page['plugins']) - 1} (inclusive)"
            )
        raise Warning(self.page["plugins"][index]["description"])


    def b(self):
        """
        Return to the previous page
        """
        self.page_index -= 1
        if self.page_index < 0:
            self.page_index = 0
            raise Warning("Can't go back from here.")

    def n(self):
        """
        Advance to the next page
        """
        self.page_index += 1

    def exit(self):
        """
        Abandon configuration
        """
        self.do_exit = True
