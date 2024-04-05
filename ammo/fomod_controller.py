#!/usr/bin/env python3
import os
import shutil
import textwrap
from typing import Union
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from xml.etree import ElementTree
from functools import reduce
from .ui import Controller
from .component import Mod
from .lib import normalize


@dataclass
class Dependency:
    """
    Stores fomod flags and the dependency operator,
    both of which are used for determining whether the
    selections on a page should map to any particular file.
    """

    operator: str = field(init=False, default_factory=str)
    flags: dict = field(init=False, default_factory=dict)


@dataclass(kw_only=True)
class Selection:
    """
    A wizard-configurable option local to a Page.
    """

    name: str
    description: str
    flags: dict
    selected: bool
    conditional: bool
    files: list[ElementTree.Element]


@dataclass(kw_only=True)
class Page:
    """
    A group of related configurable options.
    """

    name: str
    step_name: str
    archtype: str
    selections: list[Selection]
    dependency: Dependency


class FomodController(Controller):
    def __init__(self, mod: Mod):
        self.mod: Mod = mod

        # Parse the fomod installer.
        try:
            tree: ElementTree = ElementTree.parse(str(mod.modconf))
        except ElementTree.ParseError:
            raise Warning(
                "This fomod's ModuleConfig.xml is malformed and can not be parsed."
            )

        # Get the root node
        self.xml_root_node: ElementTree.Element = tree.getroot()

        # This is the name of the mod
        self.module_name: str = self.xml_root_node.find("moduleName").text

        # Get the pages
        self.steps: list[Page] = self._get_pages()
        self.page_index: int = 0
        self.flags = self._get_flags()
        self.visible_pages: list[Page] = self._get_visible_pages()
        self.page: Page = self.steps[
            self.steps.index(self.visible_pages[self.page_index])
        ]
        self.selection_type: str = self.page.archtype.lower()
        self.do_exit: bool = False
        self._populate_index_commands()

    def __str__(self) -> str:
        num_pages = len(self.visible_pages)
        result = f"{self.module_name} {self.page.step_name}\n"
        result += "--------------------------------\n"
        result += f"Page {self.page_index + 1} / {num_pages}: {self.visible_pages[self.page_index].name}\n"
        result += "--------------------------------\n\n"
        for selection in self.page.selections:
            if selection.selected and selection.description:
                result += f"{selection.name}\n"
                result += "--------------------------------\n"
                for line in textwrap.wrap(f"{selection.description}\n\n"):
                    result += f"{line}\n"
                result += "\n"

        result += " index | Activated | Option Name\n"
        result += "-------|-----------|------------\n"

        for i, selection in enumerate(self.page.selections):
            index = f"[{i}]"
            enabled = f"[{selection.selected}]"
            result += f"{index:<7} {enabled:<11} {selection.name}\n"
        result += "\n"
        return result

    def _prompt(self) -> str:
        return f"{self.selection_type} >_: "

    def _post_exec(self) -> bool:
        if self.do_exit:
            return True

        self.flags = self._get_flags()
        self.visible_pages: list[Page] = self._get_visible_pages()
        if self.page_index >= len(self.visible_pages):
            # The user advanced to the end of the installer.
            install_nodes: list[ElementTree.Element] = self._get_nodes()
            self._install_files(install_nodes)
            return True

        self.page: Page = self.steps[
            self.steps.index(self.visible_pages[self.page_index])
        ]
        self.selection_type: str = self.page.archtype.lower()
        self._populate_index_commands()
        return False

    def _autocomplete(self, text: str, state: int) -> Union[str, None]:
        return super()._autocomplete(text, state)

    def _populate_index_commands(self) -> None:
        """
        Hack to get dynamically allocated methods which are
        named after numbers, one for each selectable option.
        """
        # Remove all attributes that are numbers
        for i in list(self.__dict__.keys()):
            try:
                int(i)
                del self.__dict__[i]
            except ValueError:
                pass
        for i in range(len(self.page.selections)):
            setattr(self, str(i), lambda self, i=i: self._select(i))
            self.__dict__[str(i)].__doc__ = f"Toggle {self.page.selections[i].name}"

    def _get_pages(self) -> list[Page]:
        """
        Get a representation of every install step for this fomod.
        """
        steps = []
        # Find all the install steps
        for step in self.xml_root_node.find("installSteps"):
            install_step_name = step.get("name", "")
            if install_step_name:
                install_step_name = f"- {install_step_name}"
            for optional_file_groups in step:
                for group in optional_file_groups:
                    if not (group_of_plugins := group.find("plugins")):
                        # This step has no configurable plugins.
                        # Skip the false positive.
                        continue

                    dependency = Dependency()

                    # Collect this step's visibility conditions. Associate it
                    # with the group instead of the step. This is inefficient
                    # but fits into the "each step is a page" paradigm better.
                    if visible := step.find("visible"):
                        if dependencies := visible.find("dependencies"):
                            dep_op = dependencies.get("operator", "").lower()
                            dependency.operator = dep_op
                            for xml_flag in dependencies:
                                if flag := xml_flag.get("flag"):
                                    dependency.flags[flag] = xml_flag.get(
                                        "value", ""
                                    ).lower() in ["on", "1", "active"]

                    page = Page(
                        name=group.get("name"),
                        step_name=install_step_name,
                        archtype=group.get("type"),
                        selections=[],
                        dependency=dependency,
                    )

                    for i, plugin in enumerate(group_of_plugins):
                        name = plugin.get("name").strip()
                        description = plugin.findtext("description", default="").strip()
                        flags = {}
                        # Automatically mark the first option as selected when
                        # a selection is required.
                        selected = (
                            page.archtype in ["SelectExactlyOne", "SelectAtLeastOne"]
                        ) and i == 0

                        # Interpret on/off or 1/0 as true/false
                        if conditional_flags := plugin.find("conditionFlags"):
                            for flag in conditional_flags:
                                # People use arbitrary flags here.
                                # Most commonly "On", "1" or "active".
                                flags[flag.get("name")] = (flag.text or "").lower() in [
                                    "on",
                                    "1",
                                    "active",
                                ]
                            conditional = True

                        else:
                            # There were no conditional flags, so this was an
                            # unconditional install.
                            conditional = False

                        files = plugin.find("files") or []

                        page.selections.append(
                            Selection(
                                name=name,
                                description=description,
                                flags=flags,
                                selected=selected,
                                conditional=conditional,
                                files=files,
                            )
                        )
                    steps.append(page)
        return steps

    def _get_flags(self) -> dict:
        """
        Expects a dictionary of fomod install steps.
        Returns a dictionary where keys are flag names
        and values are flag states.
        """
        flags = {}
        for step in self.steps:
            for selection in step.selections:
                if selection.selected:
                    for k, v in selection.flags.items():
                        flags[k] = v
        return flags

    def _flags_match(self, flags: dict, operator=None) -> bool:
        """
        Compare actual flags with dependency flags to determine whether
        the plugin associated with dependency should be included.

        Returns whether the plugin which owns dependency matches.
        """
        match = False
        for k, v in flags.items():
            if k in self.flags:
                if self.flags[k] != v:
                    if operator == "and":
                        # Mismatched flag. Skip this plugin.
                        return False
                    # if dep_op is "or" (or undefined), try the rest of these.
                    continue
                # A single match.
                match = True
            elif operator == "and":
                # Missing flags counts as failure for 'and'.
                return False
        return match

    def _select(self, index: int) -> None:
        """
        Toggle the 'selected' switch on appropriate plugins.
        This logic ensures any constraints on selections are obeyed.
        """
        val = not self.page.selections[index].selected
        if "SelectExactlyOne" == self.page.archtype:
            for i in range(len(self.page.selections)):
                self.page.selections[i].selected = i == index
        elif "SelectAtMostOne" == self.page.archtype:
            for i in range(len(self.page.selections)):
                self.page.selections[i].selected = False
            self.page.selections[index].selected = val
        else:
            self.page.selections[index].selected = val

    def _get_visible_pages(self) -> list[Page]:
        """
        Returns a list of only fomod pages that should be visible,
        determined by current flags.
        """
        return [
            page
            for page in self.steps
            # if there's no condition for visibility, just show it.
            if not page.dependency.flags
            # if there's conditions, only include if the conditions are met.
            or self._flags_match(page.dependency.flags, page.dependency.operator)
        ]

    def _get_nodes(self) -> list[ElementTree.Element]:
        """
        Returns a flat list of xml folder nodes that matched configured flags.
        """
        # Determine which files need to be installed.
        selected_nodes = []

        # Normal files. If these were selected, install them unless flags
        # disqualify.
        for step in self.steps:
            for plugin in step.selections:
                if plugin.selected:
                    if plugin.conditional:
                        # conditional normal file
                        if self._flags_match(plugin.flags):
                            selected_nodes.extend(plugin.files)
                        continue
                    # unconditional file install
                    selected_nodes.extend(plugin.files)

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
            xml_dependencies = pattern.find("dependencies")
            dependency = Dependency()
            dependency.operator = xml_dependencies.get("operator", "").lower()
            for xml_flag in xml_dependencies:
                if flag := xml_flag.get("flag"):
                    dependency.flags[flag] = xml_flag.get("value", "").lower() in [
                        "on",
                        "1",
                        "active",
                    ]

            # xml_files is a list of folders. The folder objects contain the paths.
            xml_files = pattern.find("files")
            if not xml_files:
                # can't find files for this, no point in checking whether to include.
                continue

            if not dependency.flags:
                # No requirements for these files to be used.
                selected_nodes.extend(xml_files)
            elif self._flags_match(dependency.flags, dependency.operator):
                selected_nodes.extend(xml_files)

        xml_required_files = self.xml_root_node.find("requiredInstallFiles") or []
        for xml_file in xml_required_files:
            if xml_file.tag == "files":
                selected_nodes.extend(xml_file)
            else:
                selected_nodes.append(xml_file)

        assert (
            len(selected_nodes) > 0
        ), "The selected options failed to map to installable components."
        return selected_nodes

    def _install_files(self, selected_nodes: list) -> None:
        """
        Copy the chosen files 'selected_nodes' from given mod at 'index'
        to that mod's game files folder.
        """
        data = self.mod.location / "ammo_fomod" / self.mod.game_data.name

        # delete the old configuration if it exists.
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
            full_source = self.mod.location
            for i in s.split("\\"):
                folder = i
                for file in os.listdir(full_source):
                    if file.lower() == i.lower():
                        folder = file
                        break
                full_source = full_source / folder

            # get the 'destination' folder from the xml. This path is relative to
            # the mod's game files folder.
            full_destination = reduce(
                lambda path, name: path / name,
                node.get("destination").split("\\"),
                data,
            )

            # TODO: this is broken :)
            # Normalize the capitalization of folder names

            full_destination = normalize(full_destination, data.parent)

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

        self.mod.install_dir = self.mod.game_root

    def b(self) -> None:
        """
        Return to the previous page
        """
        self.page_index -= 1
        if self.page_index < 0:
            self.page_index = 0
            raise Warning("Can't go back from here.")

    def n(self) -> None:
        """
        Advance to the next page
        """
        self.page_index += 1

    def exit(self) -> None:
        """
        Abandon configuration
        """
        self.do_exit = True
