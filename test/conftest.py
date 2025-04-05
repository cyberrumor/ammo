#!/usr/bin/env python3
from unittest.mock import patch

import pytest

from ammo.controller.mod import ModController


@pytest.fixture
def mock_has_extra_folder():
    has_extra_folder = True
    with patch.object(
        ModController, "has_extra_folder", return_value=has_extra_folder
    ) as mock_has_extra_folder:
        yield

    mock_has_extra_folder.assert_called()
