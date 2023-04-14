#!/usr/bin/env python3
import inspect
import os
import sys


class UI:
    def __init__(self, controller):
        self.controller = controller
        self.keywords = []

        # get a map of commands to functions and the amount of args they expect
        self.command = {}

        for name, func in inspect.getmembers(
            self.controller.__class__, predicate=inspect.isfunction
        ):
            # Only map "public" methods
            if name.startswith("_"):
                continue

            self.command[name] = {
                "func": func,
                "args": list(inspect.signature(func).parameters)[1:],
                "num_args": len(inspect.signature(func).parameters) - 1,
                "doc": str(func.__doc__).strip(),
                "instance": self.controller,
            }

        # Add methods of this UI class that will be available regardless of the controller.
        self.command["help"] = {
            "func": self.help,
            "args": [],
            "num_args": 0,
            "doc": str(self.help.__doc__).strip(),
        }

        self.command["exit"] = {
            "func": self.exit,
            "args": [],
            "num_args": 0,
            "doc": str(self.exit.__doc__).strip(),
        }

        self.command["configure"] = {
            "func": self.configure,
            "args": ["index"],
            "num_args": 1,
            "doc": str(self.configure.__doc__).strip(),
        }

        self.command["find"] = {
            "func": self.find,
            "args": ["keyword"],
            "num_args": -1,
            "doc": str(self.find.__doc__).strip(),
        }

    def find(self, *args):
        """
        Show only components with any keyword. `find` without args resets.
        """
        if not args:
            self.keywords = []
            return True
        self.keywords = args
        return True

    def help(self):
        """
        Show this menu.
        """
        column_cmd = []
        column_arg = []
        column_doc = []

        for k, v in sorted(self.command.items()):
            params = []
            args = v["args"]
            anno = v["func"].__annotations__
            for arg in args:
                if arg in anno:
                    params.append(
                        str(anno[arg]).lower().replace("mod.", "").replace(" | ", "|")
                    )
                else:
                    if v["num_args"] < 0:
                        params.append(f"[<{arg}> ...]")
                    else:
                        params.append(f"<{arg}>")
            # print(f"{k} {' '.join(params)} {v['doc']}")
            column_cmd.append(k)
            column_arg.append(" ".join(params))
            column_doc.append(v["doc"])

        pad_cmd = max((len(i) for i in column_cmd)) + 1
        pad_arg = max((len(i) for i in column_arg)) + 1
        # pad_doc = max([len(i) for i in column_doc]) + 1

        for cmd, arg, doc in zip(column_cmd, column_arg, column_doc):
            print(
                f"{cmd}{' ' * (pad_cmd - len(cmd))}{arg}{' ' * (pad_arg - len(arg))}{doc}"
            )

    def exit(self):
        """
        Quit. Prompts if there are changes.
        """
        if self.controller.changes:
            if input("There are unapplied changes. Quit? [y/n]: ").lower() != "y":
                return True
        sys.exit(0)

    def configure(self, index):
        """
        Configure a fomod.
        """

        # This has to run a hard refresh for now, so warn if there are uncommitted changes
        if self.controller.changes:
            print("can't configure fomod when there are unsaved changes.")
            print("Please run 'commit' and try again.")
            return False

        if not (fomod_installer_root_node := self.controller._fomod_validated(index)):
            return False

        required_files = self.controller._fomod_required_files(
            fomod_installer_root_node
        )
        module_name = fomod_installer_root_node.find("moduleName").text
        steps = self.controller._fomod_install_steps(fomod_installer_root_node)
        pages = list(steps.keys())
        page_index = 0

        command_dict = {
            "<index>": "     Choose an option.",
            "info <index>": "Show the description for the selected option.",
            "exit": "        Abandon configuration of this fomod.",
            "n": "           Next page of the installer or complete installation.",
            "b": "           Back. Return to the previous page of the installer.",
        }

        def is_match(flags, expected_flags):
            """
            Compare actual flags with the flags we expected to determine whether
            the plugin associated with expected_flags should be included.
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
                        # if dep_op is "or" (or undefined), we can try the rest of these.
                        continue
                    # A single match.
                    match = True
            return match

        while True:
            # Evaluate the flags every loop to ensure the visible pages and selected options
            # are always up to date. This will ensure the proper files are chosen later as well.
            flags = {}
            for step in steps.values():
                for plugin in step["plugins"]:
                    if plugin["selected"]:
                        if not plugin["flags"]:
                            continue
                        for flag in plugin["flags"]:
                            flags[flag] = plugin["flags"][flag]

            # Determine which steps should be visible
            visible_pages = []
            for page in pages:
                expected_flags = steps[page]["visible"]

                if not expected_flags:
                    # No requirements for this page to be shown
                    visible_pages.append(page)
                    continue

                if is_match(flags, expected_flags):
                    visible_pages.append(page)

            # Only exit loop after determining which flags are set and pages are shown.
            if page_index >= len(visible_pages):
                break

            info = False
            os.system("clear")
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
                print("Bailed from configuring fomod.")
                self.controller.__reset__()
                return False

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
                    selection = selection[-1]

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
            # toggle the 'selected' switch on appropriate plugins.
            # Whenever a plugin is unselected, re-assess all flags.
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
            # END MAIN INPUT WHILE LOOP

        # Determine which files need to be installed.
        to_install = []
        if required_files:
            for file in required_files:
                if file.tag == "files":
                    for f in file:
                        to_install.append(f)
                else:
                    to_install.append(file)

        # Normal files. If these were selected, install them unless flags disqualify.
        for step in steps:
            for plugin in steps[step]["plugins"]:
                if plugin["selected"]:
                    if plugin["conditional"]:
                        # conditional normal file
                        expected_flags = plugin["flags"]

                        if is_match(flags, expected_flags):
                            for folder in plugin["files"]:
                                to_install.append(folder)
                    else:
                        # unconditional file install
                        for folder in plugin["files"]:
                            to_install.append(folder)

        # include conditional file installs based on the user choice. These are different from
        # the normal_files with conditions because these conditions are set after all of the install
        # steps instead of inside each install step.
        patterns = []
        if conditionals := fomod_installer_root_node.find("conditionalFileInstalls"):
            patterns = conditionals.find("patterns")
        if patterns:
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
                    for folder in xml_files:
                        to_install.append(folder)

                if is_match(flags, expected_flags):
                    for folder in xml_files:
                        to_install.append(folder)

        if not to_install:
            print("The configured options failed to map to installable components!")
            return False

        # Let the controller stage the chosen files and copy them to the mod's local Data dir.
        self.controller._init_fomod_chosen_files(index, to_install)

        # If _init_fomod_chosen_files can rebuild the "files" property of the mod,
        # resetting the controller and preventing configuration when there are unsaved changes
        # will no longer be required.
        self.controller.__reset__()
        return True

    def print_status(self):
        """
        Outputs a list of all downloads, then mods, then plugins.
        """
        if len(self.controller.downloads):
            print()
            print("Downloads")
            print("---------")

            for index, download in enumerate(self.controller.downloads):
                match = True
                download_keywords = (
                    download.name.replace("_", " ").replace("-", " ").lower().split()
                )

                for keyword in self.keywords:
                    match = False
                    if any(
                        (
                            download_keyword.count(keyword.lower())
                            for download_keyword in download_keywords
                        )
                    ):
                        match = True
                        break

                if match:
                    print(f"[{index}] {download}")

            print()

        for index, components in enumerate(
            [self.controller.mods, self.controller.plugins]
        ):
            print(f" ### | Activated | {'Mod name' if index == 0 else 'Plugin name'}")
            print("-----|-----------|-----")
            for priority, component in enumerate(components):
                match = True
                component_keywords = (
                    component.name.replace("_", " ").replace("-", " ").lower().split()
                )

                for keyword in self.keywords:
                    match = False
                    if any(
                        (
                            component_keyword.count(keyword.lower())
                            for component_keyword in component_keywords
                        )
                    ):
                        match = True
                        break
                if match:
                    num = f"[{priority}]     "
                    l = len(str(priority)) + 1
                    num = num[0:-l]
                    print(f"{num} {component}")
            print()

    def repl(self):
        cmd: str = ""
        try:
            while True:
                os.system("clear")
                self.print_status()

                if not (cmd := input(f"{self.controller.name} >_: ")):
                    continue

                cmds = cmd.split()
                args = []
                func = cmds[0]

                if len(cmds) > 1:
                    args = cmds[1:]

                if not (command := self.command.get(func, None)):
                    print(f"unknown command {cmd}")
                    self.help()
                    input("[Enter]")
                    continue

                if command["num_args"] >= 0:
                    if command["num_args"] != len(args):
                        print(
                            f"{func} expected {command['num_args']} arg(s) but received {len(args)}"
                        )
                        input("[Enter]")
                        continue

                if "instance" in command:
                    args.insert(0, command["instance"])

                if not command["func"](*args):
                    # Functions that fail return False. This input() call allows the user
                    # to see the error before their screen is cleared.
                    input("[Enter]")
                    continue

        except KeyboardInterrupt:
            if self.controller.changes:
                print()
                print("There were unsaved changes! Please run 'commit' before exiting.")
                print()
            sys.exit(0)
