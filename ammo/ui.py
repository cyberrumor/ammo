#!/usr/bin/env python3
import inspect
import os
import sys
from xml.etree import ElementTree


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
        """
        Read, execute, print loop
        """
        cmd: str = ""
        try:
            while True:
                os.system("clear")
                self.print_status()

                if not (cmd := input(f"{self.controller.game.name} >_: ")):
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

                try:
                    ret = command["func"](*args)
                    if not ret:
                        input("[Enter]")

                except IndexError:
                    print("Index out of range.")
                    input("[Enter]")

                except ValueError:
                    print("Expected a number and got a string.")
                    input("[Enter]")

                except FileExistsError:
                    print("Resource exists. Try removing it first.")
                    input("[Enter]")

                except FileNotFoundError:
                    print("Failed to extract. Is this a real archive?")
                    input("[Enter]")

                except IsADirectoryError:
                    print("Failed to delete directory disguised as archive.")
                    input("[Enter]")

                except AssertionError:
                    print("Changes must be committed first.")
                    input("[Enter]")

                except TypeError:
                    print("invalid component for that command")
                    input("[Enter]")

                except ElementTree.ParseError:
                    print("This mod's ModuleConfig.xml is malformed.")
                    input("[Enter]")

        except KeyboardInterrupt:
            if self.controller.changes:
                print()
                print("There were unsaved changes! Please run 'commit' before exiting.")
                print()
            sys.exit(0)
