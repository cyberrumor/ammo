#!/usr/bin/env python3
import logging

from ammo.component import (
    OpenMWMod,
    Plugin,
)

from .bethesda import BethesdaController
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

# The file extensions OpenMW loads as plugins. Unlike the classic
# Bethesda games it adds .omwaddon/.omwgame/.omwscripts and has no .esl.
# game.py copies this into OpenMWGame.plugin_extensions, the single
# source of truth the controller and OpenMWMod read from.
OPENMW_PLUGIN_EXTENSIONS = (
    ".esp",
    ".esm",
    ".omwaddon",
    ".omwgame",
    ".omwscripts",
)


class OpenMWController(BethesdaController):
    """
    Manage mods and plugins for OpenMW.

    OpenMW is a Bethesda game (Morrowind), so this reuses the
    BethesdaController plugin machinery: the same activate/deactivate/
    move/sort commands order a shared self.plugins list. Only the ends
    differ. Staging symlinks every mod into one ammo-owned data
    directory through OpenMWMod, which strips a Morrowind Data Files/
    wrapper and folds asset casing so mods land at that dir's root.
    Load order and the file registration both live in openmw.cfg
    rather than a Plugins.txt: ammo registers its data dir with a
    data= line, registers each staged .bsa with a fallback-archive=
    line, and writes the load order as content= lines. populate_plugins
    and sync_cfg override the read and write of that file; every other
    line (the base game's data and archives, comments, fallback
    settings) is preserved.
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
                        game_plugin_extensions=self.game.plugin_extensions,
                    )
                )
        return mods

    @staticmethod
    def content_of(line: str) -> str | None:
        """
        Return the plugin a content= or #content= line names, or None
        for any other line. A leading # marks a plugin ammo disabled;
        ammo still owns it, so it is parsed here, not skipped as a plain
        comment.
        """
        stripped = line.strip()
        if stripped.startswith("#"):
            stripped = stripped[1:].strip()
        if not stripped.startswith("content="):
            return None
        return stripped[len("content=") :].strip()

    def populate_plugins(self) -> None:
        """
        Build self.plugins in load order from the content= lines in
        openmw.cfg instead of a Plugins.txt.

        A content= line is an enabled plugin; a #content= line is one
        ammo disabled, kept commented so its load-order position
        survives a round trip. ammo owns every content line, including
        the base game's masters, which appear as plugins with no owning
        mod so they can be reordered (a mod plugin can be moved ahead of
        Bloodmoon.esm).
        """
        self.plugins = []

        lines = []
        if self.game.cfg.exists():
            lines = self.game.cfg.read_text().splitlines()

        for line in lines:
            name = self.content_of(line)
            if name is None:
                continue

            # Assign the conflict-winning enabled mod as the owner,
            # matching BethesdaController.populate_plugins.
            mod = None
            for m in self.mods[::-1]:
                if not m.enabled:
                    continue
                if name in (p.name for p in m.plugins):
                    mod = m
                    break

            if mod is None and (self.game.directory / name).is_symlink():
                # A staged symlink with no enabled owner is the leftover
                # of a mod disabled this session; drop its content line.
                # A base-game master is not staged here, so it survives.
                continue

            enabled = not line.strip().startswith("#")
            self.plugins.append(Plugin(name=name, mod=mod, enabled=enabled))

        # Add plugins from enabled mods the cfg does not list yet (freshly
        # installed), disabled until the user activates them.
        for mod in self.mods[::-1]:
            if not mod.enabled:
                continue
            for plugin in mod.plugins:
                if plugin.name not in (p.name for p in self.plugins):
                    self.plugins.append(
                        Plugin(name=plugin.name, mod=mod, enabled=False)
                    )

    def has_extra_folder(self, path) -> bool:
        """
        Lift a mod out of a single redundant wrapper folder, no prompt.

        Mods sometimes arrive double-wrapped, like ModName/ModName/
        or ModName/SomeFolder/meshes/. do_install calls this to decide
        whether to elevate the contents to the data dir root. Only lift
        a lone top folder that is not real content: not Data Files/
        (OpenMWMod strips that later), not an asset folder, not a
        plugin.
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
                contents[0].suffix.lower() not in self.game.plugin_extensions,
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
        ammo's data dir. sync_cfg runs before the game dir is re-staged,
        so these are the archives ammo staged last commit; the ones no
        longer in staged_archives are exactly ammo's lines to remove
        when a BSA-bearing mod is disabled or deleted.
        """
        result = set()
        if self.game.directory.is_dir():
            for entry in self.game.directory.iterdir():
                if entry.is_symlink() and entry.name.lower().endswith(".bsa"):
                    result.add(entry.name)
        return result

    def sync_cfg(self) -> None:
        """
        Rewrite the lines ammo owns in openmw.cfg in one read/edit/write
        pass: its data= dir, its fallback-archive= lines for staged
        BSAs, and the content= load order.

        Every other line (the base game's data and archives, comments,
        fallback settings, a user's extra data dirs) is kept in place.
        ammo's data= and fallback-archive= lines go last, because OpenMW
        gives later entries of those keys higher priority; the content=
        lines are written verbatim from self.plugins, so their order is
        the load order and a disabled plugin becomes a #content= line
        that holds its place.
        """
        original = ""
        lines = []
        if self.game.cfg.exists():
            original = self.game.cfg.read_text()
            lines = original.splitlines()

        # Drop every content line; ammo re-adds them from self.plugins.
        kept = [line for line in lines if self.content_of(line) is None]

        # Drop ammo's own data= line; re-added below so it lands last.
        target = str(self.game.directory)
        kept = [line for line in kept if self.data_dir_of(line) != target]

        # Drop every fallback-archive= line ammo owns (stages now or
        # staged last commit); the ones still staged are re-added below.
        # Dropping and re-appending, rather than keeping them in place,
        # keeps ammo's lines in a deterministic order across commits.
        desired = self.staged_archives()
        owned = desired | self.installed_archives()
        kept = [
            line
            for line in kept
            if (name := self.archive_of(line)) is None or name not in owned
        ]

        result = list(kept)
        result.append(f'data="{target}"')

        present = {self.archive_of(line) for line in result}
        result.extend(
            f"fallback-archive={name}"
            for name in sorted(desired)
            if name not in present
        )

        for plugin in self.plugins:
            result.append(f"{'' if plugin.enabled else '#'}content={plugin.name}")

        new_content = "".join(f"{line}\n" for line in result)
        if new_content == original:
            return

        log.info(f"Syncing ammo-owned lines in {self.game.cfg}")
        self.game.cfg.parent.mkdir(parents=True, exist_ok=True)
        self.game.cfg.write_text(new_content)

    def save_order(self) -> None:
        """
        Write ammo.conf and sync openmw.cfg with the mods and plugins
        ammo manages. do_commit calls this before it stages, so a commit
        keeps both files in sync. ModController.save_order writes only
        ammo.conf, so the Bethesda Plugins.txt write is skipped in favor
        of sync_cfg's content= lines.
        """
        ModController.save_order(self)
        self.sync_cfg()
