#!/usr/bin/env python3
import logging

from .mod import ModController

log = logging.getLogger(__name__)


class OpenMWController(ModController):
    """
    Manage mods for OpenMW.

    Staging is identical to the generic ModController: every mod is
    symlinked into one ammo-owned data directory. On top of that,
    OpenMWController registers that directory in openmw.cfg with a
    single data="..." line so OpenMW's virtual file system scans the
    staged mods. Every other line in the file (the base game's data,
    plugin activation the OpenMW Launcher owns, fallback settings) is
    left untouched.
    """

    @staticmethod
    def data_dir_of(line: str) -> str | None:
        """
        Return the directory a data= line points at, with surrounding
        quotes removed, or None if the line is not a data= entry. Used
        to find ammo's own line by exact path so every other line is
        preserved.
        """
        stripped = line.strip()
        if not stripped.startswith("data="):
            return None
        value = stripped[len("data=") :].strip()
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        return value

    def register_data_dir(self) -> None:
        """
        Ensure openmw.cfg contains exactly one data= line pointing at
        ammo's merged data directory.

        OpenMW gives later data= entries higher priority in its virtual
        file system, so ammo's line must come after the base game's;
        it is appended at the end of the file. ammo owns the line whose
        path equals game.directory and finds it by exact match, so
        the base game's data= line and anything the user or the OpenMW
        Launcher wrote are preserved. Doing nothing when the line is
        already present keeps commit idempotent.
        """
        target = str(self.game.directory)

        lines = []
        if self.game.cfg.exists():
            with open(self.game.cfg, "r") as file:
                lines = file.readlines()

        if any(self.data_dir_of(line) == target for line in lines):
            return

        log.info(f"Registering data dir in {self.game.cfg}: {target}")
        with open(self.game.cfg, "a") as file:
            if lines and not lines[-1].endswith("\n"):
                file.write("\n")
            file.write(f'data="{target}"\n')

    def save_order(self) -> None:
        """
        Write ammo.conf and register ammo's data dir in openmw.cfg. This
        runs at the start of do_commit, so committing keeps the cfg in
        sync with the mods ammo manages.
        """
        super().save_order()
        self.register_data_dir()
