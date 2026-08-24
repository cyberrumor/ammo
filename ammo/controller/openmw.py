#!/usr/bin/env python3
import logging

from ammo.component import OpenMWMod

from .mod import ModController

log = logging.getLogger(__name__)

# has_extra_folder can lift a mod out of a single wrapping folder. A
# folder whose name is real mod content must never be lifted. These
# are those names. "data files" is here because OpenMWMod strips that
# wrapper later, at populate time. The rest are Morrowind's asset
# folders.
OPENMW_NO_EXTRACT_DIRS = [
    "bookart",
    "data files",
    "fonts",
    "icons",
    "meshes",
    "music",
    "sound",
    "splash",
    "textures",
    "video",
]

# The file extensions OpenMW loads as plugins. A mod that is a single
# plugin file is already laid out correctly, so has_extra_folder leaves
# it alone.
OPENMW_PLUGIN_EXTENSIONS = (
    ".esp",
    ".esm",
    ".omwaddon",
    ".omwgame",
    ".omwscripts",
)


class OpenMWController(ModController):
    """
    Manage mods for OpenMW.

    Staging symlinks every mod into one ammo-owned data directory,
    the way the generic ModController does, but through OpenMWMod so
    a Morrowind Data Files/ wrapper is stripped and asset folders get
    canonical casing. On top of that, OpenMWController registers that
    directory in openmw.cfg with a single data="..." line so OpenMW's
    virtual file system scans the staged mods. Every other line in the
    file (the base game's data, plugin activation the OpenMW Launcher
    owns, fallback settings) is left untouched.
    """

    def get_mods(self):
        """
        Build an OpenMWMod for each mod folder.

        populate_mods in the parent calls this. OpenMWMod is what strips
        the Data Files/ wrapper and folds casing, so mods land at the
        root of the data dir OpenMW scans.
        """
        mods = []
        for path in self.game.ammo_mods_dir.iterdir():
            if path.is_dir():
                mods.append(
                    OpenMWMod(
                        location=path,
                        game_root=self.game.directory,
                        game_data=self.game.directory,
                        game_pak=self.game.directory,
                        game_dll=self.game.directory,
                        game_plugin_extensions=OPENMW_PLUGIN_EXTENSIONS,
                    )
                )
        return mods

    def has_extra_folder(self, path) -> bool:
        """
        Lift a mod out of a single redundant wrapper folder, no prompt.

        Mods sometimes arrive double-wrapped, like ModName/ModName/
        or ModName/SomeFolder/meshes/. do_install calls this to decide
        whether to elevate the contents to the data dir root. Only lift
        a lone top folder that is not real content: not Data Files/
        (OpenMWMod strips that later), not an asset folder, not a
        plugin. Mirrors BethesdaController.has_extra_folder.
        """
        contents = list(path.iterdir())
        if len(contents) != 1:
            return False

        folders = [i for i in contents if i.is_dir()]
        if len(folders) != 1:
            return False

        subdir_contents = list(folders[0].iterdir())

        if any(p.name == folders[0].name for p in subdir_contents):
            # Returning True here would force trying to rename
            # extract_to / my_mod_dir / my_mod_dir
            # to
            # extract_to / my_mod_dir
            # which can't be done.
            return False

        return all(
            [
                contents[0].name.lower() not in OPENMW_NO_EXTRACT_DIRS,
                contents[0].suffix.lower() not in OPENMW_PLUGIN_EXTENSIONS,
            ]
        )

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

    @staticmethod
    def archive_of(line: str) -> str | None:
        """
        Return the archive a fallback-archive= line names, or None
        if the line is not a fallback-archive entry. Used to find
        ammo's own archive lines by exact name so every other line is
        preserved.
        """
        stripped = line.strip()
        if not stripped.startswith("fallback-archive="):
            return None
        return stripped[len("fallback-archive=") :].strip()

    def staged_archives(self) -> set[str]:
        """
        Return the names of the .bsa files this commit will stage at the
        root of ammo's data dir. OpenMW ignores a BSA's contents until
        it is registered with a fallback-archive= line, so these are the
        archives ammo must have registered.
        """
        return {
            dest.name
            for dest in self.stage()
            if dest.parent == self.game.directory and dest.name.lower().endswith(".bsa")
        }

    def installed_archives(self) -> set[str]:
        """
        Return the names of the .bsa symlinks currently at the root of
        ammo's data dir. register_archives runs before the game dir is
        re-staged, so these are the archives ammo staged last commit;
        the ones no longer in staged_archives are exactly ammo's lines
        to remove when a BSA-bearing mod is disabled or deleted.
        """
        result = set()
        if self.game.directory.is_dir():
            for entry in self.game.directory.iterdir():
                if entry.is_symlink() and entry.name.lower().endswith(".bsa"):
                    result.add(entry.name)
        return result

    def register_archives(self) -> None:
        """
        Sync fallback-archive= lines with the .bsa files ammo stages.

        A mod's BSA is inert until openmw.cfg registers it; ammo adds a
        fallback-archive= line per staged .bsa and removes its own line
        once the BSA is no longer staged. ammo owns a line whose archive
        it either stages now or staged last commit (a symlink still
        in the data dir), so the base game's archives and anything the
        user wrote are never touched. New lines are appended after the
        existing archives, since OpenMW gives later fallback-archive=
        entries higher priority and mod archives should win over the
        base game's.
        """
        desired = self.staged_archives()
        owned = desired | self.installed_archives()

        lines = []
        if self.game.cfg.exists():
            with open(self.game.cfg, "r") as file:
                lines = file.readlines()

        kept = [
            line
            for line in lines
            if (name := self.archive_of(line)) is None
            or name not in owned
            or name in desired
        ]

        present = {self.archive_of(line) for line in kept}
        additions = [
            f"fallback-archive={name}\n"
            for name in sorted(desired)
            if name not in present
        ]

        if additions and kept and not kept[-1].endswith("\n"):
            kept[-1] += "\n"
        new_content = "".join(kept) + "".join(additions)

        if new_content == "".join(lines):
            return

        log.info(
            f"Syncing fallback-archive lines in {self.game.cfg}: {sorted(desired)}"
        )
        with open(self.game.cfg, "w") as file:
            file.write(new_content)

    def save_order(self) -> None:
        """
        Write ammo.conf and sync openmw.cfg with the mods ammo manages:
        the data dir registration and the fallback-archive= lines for
        staged BSAs. This runs at the start of do_commit, so committing
        keeps the cfg in sync.
        """
        super().save_order()
        self.register_data_dir()
        self.register_archives()
