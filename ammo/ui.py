#!/usr/bin/env python3
import os
import sys
import typing
import inspect
from copy import deepcopy
from enum import (
    Enum,
    EnumType,
)
from dataclasses import dataclass
from xml.etree import ElementTree


class UI:
    def __init__(self, controller):
        self.controller = controller

        # get a map of commands to functions and the amount of args they expect
        self.command = {}

        for name, func in inspect.getmembers(
            self.controller.__class__, predicate=inspect.isfunction
        ):
            if name.startswith("_"):
                continue

            signature = inspect.signature(func)
            type_hints = typing.get_type_hints(func)
            parameters = list(signature.parameters.values())[1:]
            num_args = 0

            args = []
            for param in parameters:
                required = False
                if param.default == param.empty:
                    # The argument did not have a default value set.

                    if param.kind == inspect.Parameter.VAR_POSITIONAL:
                        # *args are optional, and any
                        # number of them may be provided.
                        description = f"[<{param.name}> ... ]"

                    elif param.kind == inspect.Parameter.VAR_KEYWORD:
                        # **kwargs are optional, but there's no way to know
                        # which kwargs are accepted. Just hint at the collective.
                        description = f"[{param.name}=<value>]"

                    else:
                        description = f"<{param.name}>"
                        required = True

                if t := type_hints.get(param.name, None):
                    # If the argument is an enum, only provide the explicit values that
                    # the enum can represent. Show these as state1|state2|state3.
                    if isinstance(t, EnumType):
                        description = "|".join([e.value for e in t])

                arg = {
                    "name": param.name,
                    "type": param.annotation,
                    "description": description,
                    "required": required,
                }
                args.append(arg)

            self.command[name] = {
                "func": func,
                "args": args,
                "doc": str(func.__doc__).strip(),
                "instance": self.controller,
            }

        self.command["help"] = {
            "func": self.help,
            "args": [],
            "doc": str(self.help.__doc__).strip(),
        }

        self.command["exit"] = {
            "func": self.exit,
            "args": [],
            "doc": str(self.exit.__doc__).strip(),
        }

    def help(self):
        """
        Show this menu.
        """
        column_cmd = []
        column_arg = []
        column_doc = []

        for k, v in sorted(self.command.items()):
            column_cmd.append(k)
            column_arg.append(" ".join([arg["description"] for arg in v["args"]]))
            column_doc.append(v["doc"])

        pad_cmd = max(len(cmd) for cmd in column_cmd) + 1
        pad_arg = max(len(arg) for arg in column_arg) + 1

        for cmd, arg, doc in zip(column_cmd, column_arg, column_doc):
            print(
                f"{cmd}{' ' * (pad_cmd - len(cmd))}{arg}{' ' * (pad_arg - len(arg))}{doc}"
            )

        input("[Enter]")

    def exit(self):
        """
        Quit. Prompts if there are changes.
        """
        if self.controller.changes:
            if input("There are unapplied changes. Quit? [y/n]: ").lower() != "y":
                return True
        sys.exit(0)

    def cast_to_type(self, arg, target_type):
        if target_type is int:
            try:
                return int(arg)

            except ValueError as e:
                # If we can't parse it, let the function figure it out,
                # but only if there was a union type at play (type[int | str])
                if target_type is str:
                    return str(arg)
                raise(e)

        elif issubclass(target_type, Enum):
            return target_type(arg)

        else:
            # Probably str
            return arg

    def repl(self):
        """
        Read, execute, print loop
        """
        cmd: str = ""
        while True:
            os.system("clear")
            print(self.controller)
            if not (stdin := input(f"{self.controller._prompt()}")):
                continue
            cmds = stdin.split()
            args = [] if len(cmds) <= 1 else cmds[1:]
            func = cmds[0]

            if not (command := self.command.get(func, None)):
                print(f"unknown command {cmd}")
                self.help()
                continue

            # Validate that we received a sane number of arguments.
            num_required_args = len([arg for arg in command["args"] if arg["required"]])
            num_optional_args = len(
                [arg for arg in command["args"] if not arg["required"]]
            )
            if num_required_args > len(args) or (
                num_required_args > len(args) and len(num_optional_args) == 0
            ):
                print(
                    f"{func} expected at least {len(command['args'])} arg(s) but received {len(args)}"
                )
                input("[Enter]")
                continue

            prepared_args = []
            expected_args = deepcopy(command["args"])
            expected_arg = None if len(expected_args) == 0 else expected_args.pop(0)
            if expected_arg is None and len(args) > 0:
                print(f"{func} expected no args but received {len(args)} arg(s).")
                input("[Enter]")
                continue

            try:
                while len(args) > 0:
                    arg = args.pop(0)
                    target_type = expected_arg["type"]

                    prepared_arg = self.cast_to_type(arg, target_type)
                    prepared_args.append(prepared_arg)

                    if expected_arg["required"] and len(expected_args) > 0:
                        expected_arg = expected_args.pop(0)

            except (ValueError, KeyError) as e:
                print(e)
                input("[Enter]")
                continue

            if "instance" in command:
                # Commands that originate from the controller's methods
                # need to have "self" injected as their first argument.
                controller_instance = command["instance"]
                prepared_args.insert(0, controller_instance)

            try:
                command["func"](*prepared_args)
            except Warning as warning:
                print(warning)
                input("[Enter]")
