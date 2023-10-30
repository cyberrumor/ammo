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
from abc import (
    ABC,
    abstractmethod,
)


class Controller(ABC):
    """
    Public methods of class derivatives will be exposed
    to the UI. A Controller must implement the following
    methods, as they are consumed by the UI.

    The UI performs validation and type casting based on type
    hinting and doc inspection, so type hints for public methods
    are required. It is required to use Union hinting instead of
    shorthand for ambiguous types.
    E.g. do Union[int, str] instead of type[int, str].

    Doc strings for public methods should fit on one line.

    A recoverable error from any public methods should be raised
    as a Warning(). This will cause the UI to display the warning
    text and prompt the user to [Enter] before the next frame
    is drawn.
    """

    @abstractmethod
    def _prompt(self) -> str:
        """
        This returns the prompt for user input.
        """
        return ">_: "

    @abstractmethod
    def _post_exec(self) -> bool:
        """
        This function is executed after every command.
        It returns whether the UI should break from repl.
        """
        return False

    @abstractmethod
    def __str__(self) -> str:
        """
        Between every command, the screen will be cleared, and
        controller will be printed before the user is presented
        with the prompt. This should return a 'frame' of your
        interface.
        """
        return ""


class UI:
    """
    The UI class stores a controller. On UI init, it will map all currently
    defined public methods of the controller to a dictionary of commands.

    It then presents a CLI interface, offering default commands for 'exit'
    and 'help'. The help menu is generated automatically via inspecting
    type hints of the controller's public methods, and is presented in
    a typical POSIX usage format.
    """

    def __init__(self, controller: Controller):
        self.controller = controller

        # get a map of commands to functions and the amount of args they expect
        self.command = {}

        # Default 'help', may be overridden.
        self.command["help"] = {
            "func": self.help,
            "args": [],
            "doc": str(self.help.__doc__).strip(),
        }

        # Default 'exit', may be overridden.
        self.command["exit"] = {
            "func": self.exit,
            "args": [],
            "doc": str(self.exit.__doc__).strip(),
        }

        for name, func in inspect.getmembers(
            self.controller.__class__, predicate=inspect.isfunction
        ):
            if name.startswith("_"):
                continue

            signature = inspect.signature(func)
            type_hints = typing.get_type_hints(func)
            parameters = list(signature.parameters.values())[1:]

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

    def help(self):
        """
        Show this menu.
        """
        column_cmd = []
        column_arg = []
        column_doc = []

        for name, command in sorted(self.command.items()):
            column_cmd.append(name)
            column_arg.append(" ".join([arg["description"] for arg in command["args"]]))
            column_doc.append(command["doc"])

        pad_cmd = max(len(cmd) for cmd in column_cmd) + 1
        pad_arg = max(len(arg) for arg in column_arg) + 1

        out = ""
        for cmd, arg, doc in zip(column_cmd, column_arg, column_doc):
            out += f"{cmd}{' ' * (pad_cmd - len(cmd))}{arg}{' ' * (pad_arg - len(arg))}{doc}\n"
        print(out)
        input("[Enter]")

    def exit(self):
        """
        Quit.
        """
        sys.exit(0)

    def cast_to_type(self, arg: str, target_type: typing.Type):
        """
        This method is responsible for casting user input into
        the type that the command expects.
        """
        if hasattr(target_type, '__args__'):
            # Handle unions
                for T in target_type.__args__:
                    try:
                        return T(arg)
                    except ValueError:
                        pass
                raise ValueError(f"Could not cast {arg} to any {target_type}")

        return target_type(arg)

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
            if (
                num_required_args > len(args)
                or (num_required_args > len(args) and num_optional_args == 0)
                or (len(args) > num_required_args and num_optional_args == 0)
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
                if "instance" in command:
                    controller_instance = command["instance"]
                    if controller_instance._post_exec():
                        break

            except Warning as warning:
                print(warning)
                input("[Enter]")
