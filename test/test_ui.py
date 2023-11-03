#!/usr/bin/env python3
from typing import Union
from enum import (
    Enum,
)

import pytest

from ammo.ui import (
    Controller,
    UI,
)


class MockEnum(str, Enum):
    A = "a"
    B = "b"


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
    assert ui.cast_to_type("10", int) == 10


def test_cast_to_int_union():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("10", Union[int, str]) == 10
    assert ui.cast_to_type("1", Union[int, MockEnum]) == 1
    assert ui.cast_to_type("1", Union[MockEnum, int]) == 1


def test_cast_to_enum():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("A", MockEnum) == MockEnum["A"]
    assert ui.cast_to_type("a", MockEnum) == MockEnum["A"]
    assert ui.cast_to_type("B", MockEnum) == MockEnum["B"]
    with pytest.raises(KeyError):
        ui.cast_to_type("This should error", MockEnum)


def test_cast_to_enum_union():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("a", Union[int, MockEnum]) == MockEnum["A"]
    assert ui.cast_to_type("a", Union[MockEnum, int]) == MockEnum["A"]


def test_cast_to_bool():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("True", bool) is True
    assert ui.cast_to_type("False", bool) is False
    assert ui.cast_to_type("TRUE", bool) is True
    assert ui.cast_to_type("FALSE", bool) is False
    assert ui.cast_to_type("true", bool) is True
    assert ui.cast_to_type("false", bool) is False
    with pytest.raises(ValueError):
        ui.cast_to_type("This should error", bool)


def test_cast_to_bool_union():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("True", Union[bool, str]) is True
    assert ui.cast_to_type("False", Union[bool, str]) is False
    assert ui.cast_to_type("True", Union[bool, int]) is True
    assert ui.cast_to_type("False", Union[bool, int]) is False


def test_cast_to_str():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("nan", str) == "nan"
    assert ui.cast_to_type("10", str) == "10"


def test_cast_to_str_union():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("nan", Union[int, str]) == "nan"
    assert ui.cast_to_type("10", Union[str, int]) == "10"
    assert ui.cast_to_type("True", Union[str, bool]) == "True"
    assert ui.cast_to_type("False", Union[str, bool]) == "False"
