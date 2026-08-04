#!/usr/bin/env python3
from enum import (
    Enum,
)
from unittest.mock import patch

import pytest

from ammo.ui import (
    UI,
    Controller,
)
from test.bethesda.bethesda_common import AmmoController as AmmoBethesdaController
from test.mod.mod_common import AmmoController as AmmoModController
from test.test_tool_controller import AmmoToolController


class MockEnum(str, Enum):
    A = "a"
    B = "b"


class MockController(Controller):
    def __init__(self):
        pass

    def prompt(self) -> str:
        return super().prompt()

    def postcmd(self) -> bool:
        return super().postcmd()

    def __str__(self) -> str:
        return super().__str__()

    def autocomplete(self, text: str, state: int) -> str | None:
        return super().autocomplete(text, state)


def test_cast_to_int():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("10", int) == 10


def test_cast_to_int_union():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("10", int | str) == 10
    assert ui.cast_to_type("1", int | MockEnum) == 1
    assert ui.cast_to_type("1", MockEnum | int) == 1


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
    assert ui.cast_to_type("a", int | MockEnum) == MockEnum["A"]
    assert ui.cast_to_type("a", MockEnum | int) == MockEnum["A"]


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
    assert ui.cast_to_type("True", bool | str) is True
    assert ui.cast_to_type("False", bool | str) is False
    assert ui.cast_to_type("True", bool | int) is True
    assert ui.cast_to_type("False", bool | int) is False


def test_cast_to_str():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("nan", str) == "nan"
    assert ui.cast_to_type("10", str) == "10"


def test_cast_to_str_union():
    test = MockController()
    ui = UI(test)
    assert ui.cast_to_type("nan", int | str) == "nan"
    assert ui.cast_to_type("10", str | int) == "10"
    assert ui.cast_to_type("True", str | bool) == "True"
    assert ui.cast_to_type("False", str | bool) == "False"


class TestAutocompleteModUI:
    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_ui(cls, request):
        with AmmoModController() as controller:
            request.cls.ui = UI(controller)
            request.cls.ui.populate_commands()

            def complete(self, text: str, state: int) -> str | None:
                try:
                    return request.cls.ui.autocomplete(text, state)
                except Exception:  # noqa: BLE001
                    #  Any exception raised during the evaluation of the expression is caught,
                    # silenced and None is returned.
                    # https://docs.python.org/3/library/rlcompleter.html#rlcompleter.Completer
                    return None

            request.cls.complete = complete

            yield

    @pytest.mark.parametrize(
        "buf, text, expected",
        [
            ("i", "", ["install "]),
            ("a", "", ["activate "]),
            ("m", "", ["move "]),
            ("c", "", ["collisions ", "commit ", "configure "]),
            ("col", "", ["collisions "]),
            ("com", "", ["commit "]),
            ("con", "", ["configure "]),
            ("r", "", ["refresh ", "rename "]),
            ("ref", "", ["refresh "]),
            ("ren", "", ["rename "]),
            ("f", "", ["find "]),
            ("l", "", ["log "]),
            ("d", "", ["deactivate ", "delete ", "display "]),
            ("del", "", ["delete "]),
            ("dea", "", ["deactivate "]),
            ("t", "", ["tag ", "tools "]),
            ("ta", "", ["tag "]),
            ("to", "", ["tools "]),
            ("h", "", ["help ", "h "]),
            ("he", "", ["help "]),
            ("q", "", ["q "]),
            ("e", "", ["exit "]),
        ],
    )
    def test_autocomplete_mod_ui(self, buf: str, text: str, expected: list[str]):
        with patch("readline.get_line_buffer", return_value=buf):
            results = []
            state = 0
            while (result := self.complete(text, state)) is not None:
                results.append(result)
                state += 1

            assert results == expected


class TestAutocompleteBethesdaUI:
    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_ui(cls, request):
        with AmmoBethesdaController() as controller:
            request.cls.ui = UI(controller)
            request.cls.ui.populate_commands()

            def complete(self, text: str, state: int) -> str | None:
                try:
                    return request.cls.ui.autocomplete(text, state)
                except Exception:  # noqa: BLE001
                    #  Any exception raised during the evaluation of the expression is caught,
                    # silenced and None is returned.
                    # https://docs.python.org/3/library/rlcompleter.html#rlcompleter.Completer
                    return None

            request.cls.complete = complete

            yield

    @pytest.mark.parametrize(
        "buf, text, expected",
        [
            ("i", "", ["install "]),
            ("a", "", ["activate "]),
            ("m", "", ["move "]),
            ("c", "", ["collisions ", "commit ", "configure "]),
            ("col", "", ["collisions "]),
            ("com", "", ["commit "]),
            ("con", "", ["configure "]),
            ("r", "", ["refresh ", "rename "]),
            ("ref", "", ["refresh "]),
            ("ren", "", ["rename "]),
            ("f", "", ["find "]),
            ("l", "", ["log "]),
            ("d", "", ["deactivate ", "delete ", "display "]),
            ("del", "", ["delete "]),
            ("dea", "", ["deactivate "]),
            ("t", "", ["tag ", "tools "]),
            ("ta", "", ["tag "]),
            ("to", "", ["tools "]),
            ("h", "", ["help ", "h "]),
            ("he", "", ["help "]),
            ("q", "", ["q "]),
            ("e", "", ["exit "]),
        ],
    )
    def test_autocomplete_bethesda_ui(self, buf: str, text: str, expected: list[str]):
        with patch("readline.get_line_buffer", return_value=buf):
            results = []
            state = 0
            while (result := self.complete(text, state)) is not None:
                results.append(result)
                state += 1

            assert results == expected


class TestAutocompleteToolUI:
    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_ui(cls, request):
        with AmmoToolController() as controller:
            request.cls.ui = UI(controller)
            request.cls.ui.populate_commands()

            def complete(self, text: str, state: int) -> str | None:
                try:
                    return request.cls.ui.autocomplete(text, state)
                except Exception:  # noqa: BLE001
                    #  Any exception raised during the evaluation of the expression is caught,
                    # silenced and None is returned.
                    # https://docs.python.org/3/library/rlcompleter.html#rlcompleter.Completer
                    return None

            request.cls.complete = complete

            yield

    @pytest.mark.parametrize(
        "buf, text, expected",
        [
            ("i", "", ["install "]),
            ("r", "", ["refresh ", "rename "]),
            ("ref", "", ["refresh "]),
            ("ren", "", ["rename "]),
            ("d", "", ["delete "]),
            ("m", "", ["mods "]),
            ("h", "", ["help ", "h "]),
            ("he", "", ["help "]),
            ("q", "", ["q "]),
            ("e", "", ["exit "]),
        ],
    )
    def test_autocomplete_bethesda_ui(self, buf: str, text: str, expected: list[str]):
        with patch("readline.get_line_buffer", return_value=buf):
            results = []
            state = 0
            while (result := self.complete(text, state)) is not None:
                results.append(result)
                state += 1

            assert results == expected
