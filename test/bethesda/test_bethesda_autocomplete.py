#!/usr/bin/env python3
from typing import Union
from unittest.mock import patch

import pytest

from test.bethesda.bethesda_common import (
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


class TestAutocompleteBethesda:
    """
    Test autocomplete with:
        - Downloads (plural)
        - Mods (absent)
        - Plugins (absent)
    """

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
            # "activate " with no mods instaled should still autocomplete valid component types.
            ("activate ", "", ["mod ", "plugin "]),
            ("activate ", "m", ["mod "]),
            ("activate ", "p", ["plugin "]),
            # "deactivate " with no mods installed should still autocomplete valid component types.
            ("deactivate ", "", ["mod ", "plugin "]),
            ("deactivate ", "m", ["mod "]),
            ("deactivate ", "p", ["plugin "]),
            # "delete " with no mods installed should autocomplete "download " since there's no
            # mods or plugins available to select.
            ("delete ", "", ["download "]),
            # "delete m" with no mods installed should autocomplete the only valid component.
            ("delete ", "m", ["mod "]),
            # "delete p" should autocomplete "plugin " since it's a valid component for this controller.
            ("delete ", "p", ["plugin "]),
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
            # "move " with no mods installed should still autocomplete valid component types.
            ("move ", "", ["mod ", "plugin "]),
            ("move ", "m", ["mod "]),
            ("move ", "p", ["plugin "]),
            # "rename " with no mods installed should only autcomplete "download " since there's no
            # valid mod targets.
            ("rename ", "", ["download "]),
            # "rename m" with no mods installed should autocomplete the "mod " component.
            ("rename ", "m", ["mod "]),
            # "rename d" should autocomplete the "download " component.
            ("rename ", "d", ["download "]),
            # "rename download " should autocomplete download list but not "all"
            (
                "rename download ",
                "",
                [str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)],
            ),
        ],
        ids=ids_hook,
    )
    def test_autocomplete_bethesda_mods_absent(
        self, buf: str, text: str, expected: list[str]
    ):
        with patch("readline.get_line_buffer", return_value=buf):
            results = []
            state = 0
            while (result := self.complete(text, state)) is not None:
                results.append(result)
                state += 1

            assert results == expected


class TestAutocompleteBethesdaModSingular:
    """
    Test autocomplete with:
        - Downloads (plural)
        - Mods (singular)
        - Plugins (absent)
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_controller(self, request):
        with AmmoController() as controller:
            request.cls.controller = controller
            extract_mod(controller, "normal_mod")

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
            # component type for the generic BethesdaController (and it's going to have a valid target).
            ("activate ", "", ["mod "]),
            ("activate mod ", "", ["0 "]),
            # "deactivate " with mods installed should autocomplete "mod " since it's the only available
            # component type for the generic BethesdaController (and it's going to have a valid target).
            ("deactivate ", "", ["mod "]),
            ("deactivate mod ", "", ["0 "]),
            # "delete " with mods and plugins should autocomplete components with valid targets.
            ("delete ", "", ["mod ", "plugin ", "download "]),
            # "delete m" with mods installed should autocomplete the "mod " component name.
            ("delete ", "m", ["mod "]),
            # "delete mod " with a single mod installed should autocomplete the only available mod index, "0 ".
            ("delete mod ", "", ["0 "]),
            # "delete p" should autocomplete "plugin " since it's a valid component type for this controller.
            ("delete ", "p", ["plugin "]),
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
            # In this scenario, there are no fomods.
            ("configure ", "", []),
            # "move " should autocomplete components with valid targets.
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
        ],
        ids=ids_hook,
    )
    def test_autocomplete_bethesda_mods_present_singular(
        self, buf: str, text: str, expected: list[str]
    ):
        with patch("readline.get_line_buffer", return_value=buf):
            results = []
            state = 0
            while (result := self.complete(text, state)) is not None:
                results.append(result)
                state += 1

            assert results == expected


class TestAutocompleteBethesdaModPlural:
    """
    Test autocomplete with:
        - Downloads (plural)
        - Mods (plural)
        - Plugins (plural)
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_controller(self, request):
        with AmmoController() as controller:
            request.cls.controller = controller
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
            # "activate " autocompletes components with valid targets.
            ("activate ", "", ["mod ", "plugin "]),
            ("activate ", "m", ["mod "]),
            ("activate ", "p", ["plugin "]),
            # Don't autocomplete invalid components
            ("activate ", "d", []),
            ("activate mod ", "", ["0 ", "1 ", "2 ", "all "]),
            ("activate plugin ", "", ["0 ", "1 ", "all "]),
            # "deactivate " autocompletes components with valid targets.
            ("deactivate ", "", ["mod ", "plugin "]),
            ("deactivate mod ", "", ["0 ", "1 ", "2 ", "all "]),
            ("deactivate plugin ", "", ["0 ", "1 ", "all "]),
            # "delete " autocompletes components with valid targets.
            ("delete ", "", ["mod ", "plugin ", "download "]),
            # "delete m" autocompletes "mod ".
            ("delete ", "m", ["mod "]),
            # "delete p" autocompletes "plugin ".
            ("delete ", "p", ["plugin "]),
            ("delete ", "d", ["download "]),
            # "delete mod " with multiple mods installed should autocomplete all available indices and "all ".
            ("delete mod ", "", ["0 ", "1 ", "2 ", "all "]),
            # "delete download " should autocomplete download indices and "all ".
            (
                "delete download ",
                "",
                [*(str(i) + " " for i in range(0, NUM_DOWNLOADS + 1)), "all "],
            ),
            # "delete plugin " should autocomplete plugin indices and "all ".
            ("delete plugin ", "", ["0 ", "1 ", "all "]),
            # "collisions " with mods that have conflicts should autocomplete only indices with collisions.
            # E.g., don't complete the index for "normal_mod" here. Just collision_1 and collision_2.
            ("collisions ", "", ["0 ", "1 "]),
            # "configure " with mods installed should only autocomplete the index if the mod is a fomod.
            # In this scenario, there are no fomods.
            ("configure ", "", []),
            # "move " with mods and plugins should autocomplete valid components.
            ("move ", "", ["mod ", "plugin "]),
            ("move ", "m", ["mod "]),
            ("move mod ", "", ["0 ", "1 ", "2 "]),
            ("move mod 1 ", "", ["0 ", "1 ", "2 "]),
            ("move ", "p", ["plugin "]),
            ("move plugin ", "", ["0 ", "1 "]),
            # "rename " with mods installed should autocomplete valid component names.
            # Note that renaming plugins is not allowed because it would break masters.
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
            # "rename p" should NOT autocomplete "plugin" since we can't rename plugins.
            ("rename ", "p", []),
        ],
        ids=ids_hook,
    )
    def test_autocomplete_bethesda_mods_present_plural(
        self, buf: str, text: str, expected: list[str]
    ):
        with patch("readline.get_line_buffer", return_value=buf):
            results = []
            state = 0
            while (result := self.complete(text, state)) is not None:
                results.append(result)
                state += 1

            assert results == expected
