#!/usr/bin/env python3
from typing import Union
from unittest.mock import patch

import pytest

from ammo.controller.mod import ModController
from mod_common import (
    AmmoController,
    extract_mod,
    install_mod,
)

NUM_DOWNLOADS = 28


def ids_hook(param):
    """
    Fix up ids so it's slightly easier to tell which input buffers have bad completions.
    Note that this is still completely mangled.
    """
    return repr(param)


class TestAutocomplete:
    @pytest.fixture(scope="class", autouse=True)
    def setup_controller(self, request):
        with AmmoController() as controller:
            request.cls.controller = controller

            def complete(self, text: str, state: int) -> Union[str, None]:
                try:
                    return request.cls.controller.autocomplete(text, state)
                except Exception:
                    #  Any exception raised during the evaluation of the expression is caught,
                    # silenced and None is returned.
                    # https://docs.python.org/3/library/rlcompleter.html#rlcompleter.Completer
                    return None

            request.cls.complete = complete

            yield

    @pytest.mark.parametrize(
        "buf, text, expected",
        [
            # Note that completing the first command names is handled by readline magic,
            # so the autocomplete function in the controllers don't have to do anything
            # special for them. It also means we can't test that behavior here since our
            # autocompleters only do stuff after the command name has been passed in.
            # Install any specific download via number or "all"
            (
                "install ",
                "",
                [*(str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)), "all "],
            ),
            # "activate " with no mods instaled should still autocomplete "mod " since it's the only
            # available component type for the generic ModController.
            ("activate ", "", ["mod "]),
            # "deactivate " with no mods installed should still autocomplete "mod " since it's the only
            # available component type for the generic ModController.
            ("deactivate ", "", ["mod "]),
            # "delete " with no mods installed should autocomplete "download " since there's no mods
            # available to select.
            ("delete ", "", ["download "]),
            # "delete m" with no mods installed should autocomplete "mod ", not "download "!
            # We don't want someone to expect to have "mod" autocompleted then they accidentally
            # delete the wrong component type.
            ("delete ", "m", ["mod "]),
            # "delete mod " with no mods installed should not autocomplete anything since there's
            # no valid targets.
            ("delete mod ", "", []),
            # "delete download " should autocomplete download indices and "all ".
            (
                "delete download ",
                "",
                [*(str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)), "all "],
            ),
            # "collisions " with no mods installed should not autocomplete anything since there's no
            # valid targets.
            ("collisions ", "", []),
            # "configure " with no mods installed should not autocomplete anything since there's no
            # valid targets.
            ("configure ", "", []),
            # "move " with no mods installed should still autocomplete "mod " for consistency.
            ("move ", "", ["mod "]),
            # "rename " with no mods installed should only autcomplete "download " since there's no
            # valid mod targets.
            ("rename ", "", ["download "]),
            # "rename m" with mods installed should autocomplete the "mod " component.
            ("rename ", "m", ["mod "]),
            # "rename d" should autocomplete the "download " component.
            ("rename ", "d", ["download "]),
            # "rename download " should autocomplete download list but not "all"
            (
                "rename download ",
                "",
                [str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)],
            ),
            # "delete p" should NOT autocomplete "plugin " since it's a bogus component type for this controller.
            ("delete ", "p", []),
        ],
        ids=ids_hook,
    )
    def test_autocomplete_mods_absent(self, buf: str, text: str, expected: list[str]):
        with patch("readline.get_line_buffer", return_value=buf):
            results = []
            state = 0
            while (result := self.complete(text, state)) is not None:
                results.append(result)
                state += 1

        assert results == expected


class TestAutocompleteModSingular:
    @pytest.fixture(scope="class", autouse=True)
    def setup_controller(self, request):
        with AmmoController() as controller:
            request.cls.controller = controller
            with patch.object(
                ModController, "has_extra_folder", return_value=True
            ) as _mock_has_extra_folder:
                extract_mod(controller, "mock_relighting_skyrim")

            def complete(self, text: str, state: int) -> Union[str, None]:
                try:
                    return request.cls.controller.autocomplete(text, state)
                except Exception:
                    #  Any exception raised during the evaluation of the expression is caught,
                    # silenced and None is returned.
                    # https://docs.python.org/3/library/rlcompleter.html#rlcompleter.Completer
                    return None

            request.cls.complete = complete

            yield

    @pytest.mark.parametrize(
        "buf, text, expected",
        [
            # Note that completing the first command names is handled by readline magic,
            # so the autocomplete function in the controllers don't have to do anything
            # special for them. It also means we can't test that behavior here since our
            # autocompleters only do stuff after the command name has been passed in.
            # Install any specific download via number or "all"
            (
                "install ",
                "",
                [*(str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)), "all "],
            ),
            # "activate " with mods instaled autocomplete "mod " since it's the only available
            # component type for the generic ModController (and it's going to have a valid target).
            ("activate ", "", ["mod "]),
            ("activate mod ", "", ["0 "]),
            # "deactivate " with mods installed should autocomplete "mod " since it's the only available
            # component type for the generic ModController (and it's going to have a valid target).
            ("deactivate ", "", ["mod "]),
            ("deactivate mod ", "", ["0 "]),
            # "delete " with mods installed should autocomplete "download " and "mod " since there's
            # more than one component type with valid targets.
            ("delete ", "", ["mod ", "download "]),
            # "delete m" with mods installed should autocomplete the "mod " component name.
            ("delete ", "m", ["mod "]),
            # "delete mod " with a single mod installed should autocomplete the only available mod index, "0 ".
            ("delete mod ", "", ["0 "]),
            # "delete download " should autocomplete download indices and "all ".
            (
                "delete download ",
                "",
                [*(str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)), "all "],
            ),
            # "collisions " with a single mod installed should not autocomplete anything since there's no
            # mods with collisions.
            ("collisions ", "", []),
            # "configure " with mods installed should only autocomplete the index if the mod is a fomod.
            # In this scenario, it is.
            ("configure ", "", ["0 "]),
            # "move " with a mods installed should autocomplete the "mod " component.
            ("move ", "", ["mod "]),
            ("move mod ", "", ["0 "]),
            # "rename " with mods installed should autocomplete valid component names.
            ("rename ", "", ["mod ", "download "]),
            # "rename m" with a mod installed should autocomplete the "mod " component.
            ("rename ", "m", ["mod "]),
            ("rename mod ", "", ["0 "]),
            # "rename d" should autocomplete the "download " component.
            ("rename ", "d", ["download "]),
            # "rename download " should autocomplete download list but not "all"
            (
                "rename download ",
                "",
                [str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)],
            ),
            # "delete p" should NOT autocomplete "plugin " since it's a bogus component type for this controller.
            ("delete ", "p", []),
        ],
        ids=ids_hook,
    )
    def test_autocomplete_mods_present_singular(
        self, buf: str, text: str, expected: list[str]
    ):
        with patch("readline.get_line_buffer", return_value=buf):
            results = []
            state = 0
            while (result := self.complete(text, state)) is not None:
                results.append(result)
                state += 1

            assert results == expected


class TestAutocompleteModPlural:
    @pytest.fixture(scope="class", autouse=True)
    def setup_controller(self, request):
        with AmmoController() as controller:
            request.cls.controller = controller
            with patch.object(
                ModController, "has_extra_folder", return_value=True
            ) as _mock_has_extra_folder:
                install_mod(controller, "mock_conflict_1")
                install_mod(controller, "mock_conflict_2")
                install_mod(controller, "normal_mod")

            def complete(self, text: str, state: int) -> Union[str, None]:
                try:
                    return request.cls.controller.autocomplete(text, state)
                except Exception:
                    #  Any exception raised during the evaluation of the expression is caught,
                    # silenced and None is returned.
                    # https://docs.python.org/3/library/rlcompleter.html#rlcompleter.Completer
                    return None

            request.cls.complete = complete

            yield

    @pytest.mark.parametrize(
        "buf, text, expected",
        [
            # Note that completing the first command names is handled by readline magic,
            # so the autocomplete function in the controllers don't have to do anything
            # special for them. It also means we can't test that behavior here since our
            # autocompleters only do stuff after the command name has been passed in.
            # Install any specific download via number or "all"
            (
                "install ",
                "",
                [*(str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)), "all "],
            ),
            # "activate " with mods instaled autocomplete "mod " since it's the only available
            # component type for the generic ModController (and it's going to have a valid target).
            ("activate ", "", ["mod "]),
            ("activate mod ", "", ["0 ", "1 ", "2 ", "all "]),
            # "deactivate " with mods installed should autocomplete "mod " since it's the only available
            # component type for the generic ModController (and it's going to have a valid target).
            ("deactivate ", "", ["mod "]),
            ("deactivate mod ", "", ["0 ", "1 ", "2 ", "all "]),
            # "delete " with mods installed should autocomplete "download " and "mod " since there's
            # more than one component type with valid targets.
            ("delete ", "", ["mod ", "download "]),
            # "delete m" with mods installed should autocomplete the "mod " component name.
            ("delete ", "m", ["mod "]),
            # "delete mod " with multiple mods installed should autocomplete all available indices and "all ".
            ("delete mod ", "", ["0 ", "1 ", "2 ", "all "]),
            # "delete download " should autocomplete download indices and "all ".
            (
                "delete download ",
                "",
                [*(str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)), "all "],
            ),
            # "collisions " with mods that have conflicts should autocomplete only indices with collisions.
            # E.g., don't complete the index for "normal_mod" here. Just collision_1 and collision_2.
            ("collisions ", "", ["0 ", "1 "]),
            # "configure " with mods installed should only autocomplete the index if the mod is a fomod.
            # In this scenario, there are no fomods.
            ("configure ", "", []),
            # "move " with mods installed should autocomplete the "mod " component.
            ("move ", "", ["mod "]),
            ("move mod ", "", ["0 ", "1 ", "2 "]),
            ("move mod 1 ", "", ["0 ", "1 ", "2 "]),
            # "rename " with mods installed should autocomplete valid component names.
            ("rename ", "", ["mod ", "download "]),
            # "rename m" with mods installed should autocomplete the "mod " component.
            ("rename ", "m", ["mod "]),
            ("rename mod ", "", ["0 ", "1 ", "2 "]),
            # "rename d" should autocomplete the "download " component.
            ("rename ", "d", ["download "]),
            # "rename download " should autocomplete download list but not "all"
            (
                "rename download ",
                "",
                [str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)],
            ),
            # "delete p" should NOT autocomplete "plugin " since it's a bogus component type for this controller.
            ("delete ", "p", []),
        ],
        ids=ids_hook,
    )
    def test_autocomplete_mods_present_plural(
        self, buf: str, text: str, expected: list[str]
    ):
        with patch("readline.get_line_buffer", return_value=buf):
            results = []
            state = 0
            while (result := self.complete(text, state)) is not None:
                results.append(result)
                state += 1

            assert results == expected
