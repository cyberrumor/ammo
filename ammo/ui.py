#!/usr/bin/env python3
import os
import sys
import typing
from typing import (
    Callable,
    Union,
)
import inspect
import textwrap
import readline

from copy import deepcopy
from enum import (
    Enum,
    EnumMeta,
)
from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import dataclass
from itertools import product

from ammo.lib import ignored


SEPARATOR_ROW = "."
SEPARATOR_COL = ":"
TERM_WIDTH = 96


class Controller(ABC):
    """
    Command methods (which are methods prefixed with 'do_') of class
    derivatives will be exposed to the UI. A Controller must implement
    the following methods, as they are consumed by the UI.

    The UI performs validation and type casting based on type
    hinting and doc inspection, so type hints for public methods
    are required. It is required to use Union hinting instead of
    shorthand for ambiguous types.
    E.g. do Union[int, str] instead of type[int, str].

    A recoverable error from any public methods should be raised
    as a Warning(). This will cause the UI to display the warning
    text and prompt the user to [Enter] before the next frame
    is drawn.
    """

    @abstractmethod
    def prompt(self) -> str:
        """
        This returns the prompt for user input.
        """
        return ">_: "

    @abstractmethod
    def postcmd(self) -> bool:
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

    @abstractmethod
    def autocomplete(self, text: str, state: int) -> Union[str, None]:
        """
        Returns the next possible autocompletion beginning with text.
        This should only be used for arguments of existing functions.
        """
        assert readline.get_line_buffer().split()[0] in dir(self)
        return None


@dataclass(kw_only=True)
class Arg:
    name: str
    type: type
    description: str
    expressions: list[str]
    required: bool


@dataclass(kw_only=True)
class Command:
    name: str
    func: Callable[..., None]
    args: list[Arg]
    doc: str
    instance: Union[Controller, None]
    visible: bool
    examples: list[str]


class UI:
    """
    Expose public methods of whatever class (derived from Controller)
    you provide as an argument as commands in an interactive CLI.
    """

    def __init__(self, controller: Controller):
        """
        On UI init, map all presently defined public methods of the controller
        into a dictionary of commands.
        """
        self.controller = controller
        self.command = {}

        readline.parse_and_bind("tab: complete")
        readline.set_completer(self.autocomplete)

    def autocomplete(self, text: str, state: int) -> Union[str, None]:
        """
        Autocomplete function desired by the readline interface.
        If we can complete a command, do it. Otherwise, attempt to
        return results from self.controller.autocomplete.
        """
        buf = readline.get_line_buffer()
        if len(buf.split()) <= 1 and not buf.endswith(" "):
            # If there's only one word in the buffer, we want to try
            # to complete commands.
            completions = []
            for cmd in self.command:
                if cmd.startswith(buf):
                    completions.append(cmd)

            # If state is greater than the number of completions,
            # return None to signal that we've provided all completions.
            if state > len(completions):
                return None

            # Auto insert a space after the command.
            return completions[state] + " "

        # There was more than one word.
        return self.controller.autocomplete(text, state)

    def populate_commands(self):
        """
        Populate self.command with Command objects that represent
        public methods of self.controller.
        """
        self.command = {}

        # Default 'help', may be overridden.
        self.command["help"] = Command(
            name="help",
            func=self.help,
            args=[],
            doc=str(self.help.__doc__).strip(),
            examples=[],
            instance=None,
            visible=True,
        )

        # Make 'help' available from 'h' too.
        self.command["h"] = Command(
            name="h",
            func=self.help,
            args=[],
            doc=str(self.help.__doc__).strip(),
            examples=[],
            instance=None,
            visible=False,
        )

        # Default 'exit', may be overridden.
        self.command["exit"] = Command(
            name="exit",
            func=self.exit,
            args=[],
            doc=str(self.exit.__doc__).strip(),
            examples=[],
            instance=None,
            visible=True,
        )

        # Make 'exit' available from 'q' too.
        self.command["q"] = Command(
            name="q",
            func=self.exit,
            args=[],
            doc=str(self.exit.__doc__).strip(),
            examples=[],
            instance=None,
            visible=False,
        )

        for name in dir(self.controller):
            # Collect command methods
            if not name.startswith("do_"):
                continue

            attribute = getattr(self.controller, name)
            if not callable(attribute):
                continue

            if hasattr(attribute, "__func__"):
                # attribute is a bound method (which is transient).
                # Get the actual function associated with it instead
                # of a descriptor.
                func = attribute.__func__
            else:
                # lambdas
                func = attribute

            signature = inspect.signature(func)
            type_hints = typing.get_type_hints(func)
            parameters = list(signature.parameters.values())[1:]

            args = []
            for index, param in enumerate(parameters):
                # enumerate so we can get a unique int for each int arg
                # in the help text.
                expressions = []
                required = False
                description = ""
                if param.default == param.empty:
                    # The argument did not have a default value set.

                    if param.kind == inspect.Parameter.VAR_POSITIONAL:
                        # *args are optional, and any
                        # number of them may be provided.
                        description = f"[<{param.name}> ... ]"
                        expressions.append("")
                        expressions.append(f"{param.name}1")
                        expressions.append(f"{param.name}1 {param.name}2")

                    elif param.kind == inspect.Parameter.VAR_KEYWORD:
                        # **kwargs are optional, but there's no way to know
                        # which kwargs are accepted. Just hint at the collective.
                        description = f"[{param.name}=<value>]"
                        expressions.append("")
                        expressions.append("undocumented_arg1=some_value")
                        expressions.append(
                            "undocumented_arg1=some_value undocumented_arg2=some_value"
                        )

                    elif (t := type_hints.get(param.name, None)) and not isinstance(
                        t, EnumMeta
                    ):
                        description = f"<{param.name}>"
                        required = True
                        t = type_hints.get(param.name, None)
                        if t is Union[int, str]:
                            expressions.append(f"{index}")
                            # guh, business logic in the UI class :c
                            expressions.append("all")
                        elif t is int:
                            # TODO: Make this say 3 if it's not the first int
                            expressions.append(f"{index}")
                        elif t is str:
                            expressions.append("some_text")
                        else:
                            expressions.append(param.name)

                if t := type_hints.get(param.name, None):
                    # If the argument is an enum, only provide the explicit values that
                    # the enum can represent. Show these as (state1|state2|state3).
                    if isinstance(t, EnumMeta):
                        required = True
                        description = "(" + "|".join([e.value for e in t]) + ")"
                        for e in t:
                            expressions.append(e.value)

                args.append(
                    Arg(
                        name=param.name,
                        type=param.annotation,
                        description=description,
                        expressions=expressions,
                        required=required,
                    )
                )

            examples = set()
            expressions_lists = [arg.expressions for arg in args]
            product_combinations = product(*expressions_lists)
            for combination in product_combinations:
                examples.add(
                    f"{name.replace('do_', '')} {' '.join(combination)}".strip()
                )
            examples = sorted(list(examples))

            # Get rid of examples that are just the command name alone.
            if len(examples) == 1 and examples[0] == name.replace("do_", ""):
                examples = []

            self.command[name.replace("do_", "")] = Command(
                name=name,
                func=func,
                args=args,
                doc=str(func.__doc__).strip(),
                instance=self.controller,
                visible=True,
                examples=examples,
            )

    def help(self):
        """
        Show this menu.
        """
        column_cmd = []
        column_arg = []
        column_doc = []
        example_doc = []

        for name, command in sorted(self.command.items()):
            if not command.visible:
                continue
            column_cmd.append(name)
            column_arg.append(" ".join([arg.description for arg in command.args]))
            column_doc.append(command.doc)
            example_doc.append(command.examples)

        pad_cmd = max(len(cmd) for cmd in column_cmd) + 1
        pad_arg = max(len(arg) for arg in column_arg) + 1

        row_divider = SEPARATOR_ROW * TERM_WIDTH

        out = f"\n{row_divider}\n"
        for cmd, arg, doc, examples in zip(
            column_cmd, column_arg, column_doc, example_doc
        ):
            line = f"{cmd}{' ' * (pad_cmd - len(cmd))}{SEPARATOR_COL} {arg}{' ' * (pad_arg - len(arg))}{SEPARATOR_COL} "
            # Treat linebreaks, tabs and multiple spaces as a single space.
            docstring = " ".join(doc.split())
            # Wrap the document so it stays in the description column.
            out += (
                textwrap.fill(
                    line + docstring,
                    subsequent_indent=(" " * pad_cmd)
                    + SEPARATOR_COL
                    + (" " * pad_arg)
                    + f" {SEPARATOR_COL} ",
                    width=TERM_WIDTH,
                )
                + "\n"
            )
            for example in examples:
                out += (
                    textwrap.fill(
                        f"- `{example}`",
                        initial_indent=(" " * pad_cmd)
                        + SEPARATOR_COL
                        + (" " * pad_arg)
                        + f" {SEPARATOR_COL} ",
                        subsequent_indent=(" " * pad_cmd)
                        + SEPARATOR_COL
                        + (" " * pad_arg)
                        + f" {SEPARATOR_COL} ",
                        width=TERM_WIDTH,
                    )
                    + "\n"
                )
            out += f"{row_divider}\n"

        print(out)
        try:
            input("[Enter] ")
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)

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

        def _cast(argument: str, T: typing.Type):
            # Attention to bools
            if T is bool:
                if argument.lower() in ("true", "false"):
                    return argument.lower() == "true"
                else:
                    # Users must explicitly type "true" or "false",
                    # don't just return whether truthy. Error instead.
                    raise ValueError(f"Could not convert {argument} to bool")

            # Attention to enums.
            if issubclass(T, Enum):
                return T[argument.upper()]

            # Anything else is a primitive type.
            return T(argument)

        # If we have a union type, return first successful cast.
        if hasattr(target_type, "__args__"):
            for t in target_type.__args__:
                with ignored(KeyError, ValueError):
                    return _cast(arg, t)
            raise ValueError(f"Could not cast {arg} to any {target_type}")

        # Not a union, cast directly.
        return _cast(arg, target_type)

    def repl(self, clear=True):
        """
        Read, execute, print loop
        """
        cmd: str = ""
        while True:
            # Repopulate commands on every iteration so controllers
            # that dynamically change available methods work.
            self.populate_commands()
            # Set the completer here to fix returning from nested UIs.
            readline.set_completer(self.autocomplete)

            if clear:
                os.system("clear")
            print(self.controller)

            try:
                if not (stdin := input(f"{self.controller.prompt()}")):
                    continue
            except (KeyboardInterrupt, EOFError):
                print()
                sys.exit(0)

            cmds = stdin.split()
            args = [] if len(cmds) <= 1 else cmds[1:]
            func = cmds[0]

            if not (command := self.command.get(func, None)):
                print(f"unknown command {cmd}")
                self.help()
                continue

            # Validate that we received a sane number of arguments.
            num_required_args = len([arg for arg in command.args if arg.required])
            num_optional_args = len([arg for arg in command.args if not arg.required])

            if (
                num_required_args > len(args)
                or (num_required_args > len(args) and num_optional_args == 0)
                or (len(args) > num_required_args and num_optional_args == 0)
            ):
                print(
                    f"{func} expected at least {len(command.args)} arg(s) but received {len(args)}"
                )
                input("[Enter] ")
                continue

            prepared_args = []
            expected_args = deepcopy(command.args)
            expected_arg = None if len(expected_args) == 0 else expected_args.pop(0)
            if expected_arg is None and len(args) > 0:
                print(f"{func} expected no args but received {len(args)} arg(s).")
                input("[Enter] ")
                continue

            try:
                while len(args) > 0:
                    arg = args.pop(0)
                    target_type = expected_arg.type
                    prepared_arg = self.cast_to_type(arg, target_type)
                    prepared_args.append(prepared_arg)

                    if expected_arg.required and len(expected_args) > 0:
                        expected_arg = expected_args.pop(0)

            except (ValueError, KeyError) as e:
                print(f"arg '{e}' was unexpected type: {type(e)}")
                input("[Enter] ")
                continue

            if command.instance is not None:
                # Commands that originate from the controller's methods
                # need to have "self" injected as their first argument.
                controller_instance = command.instance
                prepared_args.insert(0, controller_instance)

            try:
                command.func(*prepared_args)
                if command.instance is not None:
                    controller_instance = command.instance
                    if controller_instance.postcmd():
                        if hasattr(self.controller, "return_value"):
                            return self.controller.return_value

                        break

            except Warning as warning:
                print(f"\n{warning}")
                input("[Enter] ")

            except Exception as e:
                print(e)
                print(f"{prepared_args=}")
                raise
