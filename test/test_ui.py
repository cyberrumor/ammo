#!/usr/bin/env python3
from ammo.ui import (
    Controller,
    UI,
)

class MockController(Controller):
    def __init__(self):
        pass

    def _prompt(self) -> str:
        return super()._prompt()

    def _post_exec(self) -> bool:
        return super()._post_exec()

    def __str__(self) -> str:
        return super().__str__()


def test_cast_to_int():

    test = MockController()
    ui = UI(test)
    assert isinstance(ui.cast_to_type("10", int), int)

