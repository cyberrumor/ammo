#!/usr/bin/env python3
import io
from unittest.mock import patch

import pytest

from ammo.ui import UI
from ammo.controller.bool_prompt import BoolPromptController


@pytest.mark.parametrize(
    "user_input,expected_return_value",
    (
        (
            "yes",
            True,
        ),
        (
            "no",
            False,
        ),
    ),
)
def test_bool_prompt_controller(user_input, expected_return_value):
    """
    This tests that BoolPromptController sets self.return_vaule to
    True when the user types "yes" at the prompt, and False when the
    user types "no" at the prompt.

    This also tests that UI.repl() returns controller.return_value
    when postcmd returns True (indicating to break from the repl).
    """
    with patch("sys.stdin", new_callable=io.StringIO) as mock_stdin:
        mock_stdin.write(f"{user_input}\n")
        # Reset stream back to the beginning. This is required for
        # the UI class to actually process it, for whatever reason.
        mock_stdin.seek(0)

        controller = BoolPromptController("test?")
        ui = UI(controller)

        repl_return_value = ui.repl()

        assert controller.return_value is expected_return_value
        assert repl_return_value is expected_return_value
