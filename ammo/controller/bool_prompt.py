#!/usr/bin/env python3
import readline
from typing import Union

from ammo.ui import Controller


class BoolPromptController(Controller):
    """
    Given a question that can be answered with "yes" or "no",
    return True for yes or False for no.
    """

    def __init__(self, question: str):
        self.question = question
        self.return_value = None
        self.do_exit = False

    def prompt(self) -> str:
        """
        This returns the prompt for user input.
        """
        return "[yes|no] >_: "

    def postcmd(self) -> bool:
        """
        This function is executed after every command.
        It returns whether the UI should break from repl.
        """
        if self.do_exit:
            return True

        return False

    def __str__(self) -> str:
        """
        The screen will be cleared between every command, and controller
        will be printed before the user is presented with the prompt.
        This should return a 'frame' of your interface.
        """
        return f"{self.question}"

    def autocomplete(self, text: str, state: int) -> Union[str, None]:
        """
        Returns the next possible autocompletion beginning with text.
        This should only be used for arguments of existing functions.
        """
        assert readline.get_line_buffer().split()[0] in dir(self)
        return None

    def do_yes(self) -> bool:
        """
        affirm or accept.
        """
        self.return_value = True
        self.do_exit = True

    def do_no(self) -> bool:
        """
        deny or reject.
        """
        self.return_value = False
        self.do_exit = True
