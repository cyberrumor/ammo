#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from ammo.controller.mod import ModController

EXTRACT_CACHE = Path("/tmp/ammo_extract_cache/")


def get_cached_archive(self, index: int, download: Path) -> Path:
    """
    See if an extracted archive is cached. If it is, copy it to
    /tmp/ammo_test/MockGame/mods/. If it's not, extract it, cache it,
    then copy it to /tmp/ammo_test/MockGame/mods/.

    Return Path("/tmp/ammo_test/MockGame/mods/<extracted_archive>")
    """
    extract_to_name = "".join(
        [i for i in download.location.stem.replace(" ", "_") if i.isalnum() or i == "_"]
    ).strip()

    extract_to = self.game.ammo_mods_dir / extract_to_name
    if extract_to.exists():
        raise Warning(
            f"Extraction of {index} failed since mod '{extract_to.name}' exists."
        )

    archive_at = EXTRACT_CACHE / extract_to_name
    if not archive_at.exists():
        os.system(f"7z x '{download.location}' -o'{archive_at}'")

    os.system(f"cp -r {archive_at} {extract_to}")

    return extract_to


@pytest.fixture(scope="session", autouse=True)
def mock_extract_archive():
    try:
        EXTRACT_CACHE.mkdir(parents=True, exist_ok=True)
        with patch.object(ModController, "extract_archive", get_cached_archive):
            yield
    finally:
        shutil.rmtree(EXTRACT_CACHE, ignore_errors=True)


@pytest.fixture
def mock_has_extra_folder():
    has_extra_folder = True
    with patch.object(
        ModController, "has_extra_folder", return_value=has_extra_folder
    ) as mock_has_extra_folder:
        yield

    mock_has_extra_folder.assert_called()
