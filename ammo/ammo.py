#!/usr/bin/env python3
import os
import shutil
from mod import *

IDS = {
    "Skyrim Special Edition": "489830",
    "Oblivion": "22330",
    "Fallout 4": "377160",
    "Skyrim": "72850",
}
HOME = os.environ["HOME"]
DOWNLOADS = os.path.join(HOME, "Downloads")
STEAM = os.path.join(HOME, ".local/share/Steam/steamapps")


class Ammo:
    def __init__(self, app_name, game_dir, data_dir, conf, dlc_file, plugin_file, mods_dir):
        self.name = app_name
        self.game_dir = game_dir
        self.data_dir = data_dir
        self.conf = conf
        self.dlc_file = dlc_file
        self.plugin_file = plugin_file
        self.mods_dir = mods_dir

        self.downloads = []
        self.mods = []
        self.plugins = []
        self.changes = False


    def load_mods(self):
        """
        Instance a  Mod class for each mod folder in ammo's mod directory.
        """
        mods = []
        mod_folders = [i for i in os.listdir(self.mods_dir) if os.path.isdir(os.path.join(self.mods_dir, i))]
        for mod_folder in mod_folders:
            mod = Mod(mod_folder, os.path.join(self.mods_dir, mod_folder), self.data_dir, False)
            mods.append(mod)
        self.mods = mods


    def load_mods_from_conf(self):
        """
        Read the conf file. If there's mods in it, put them in order.
        Put mods that aren't listed in the conf file at the end.
        """
        ordered_mods = []
        if not os.path.exists(self.conf):
            return

        with open(self.conf, "r") as file:
            for line in file:
                if line.startswith('#'):
                    continue
                name = line.strip('*').strip()
                enabled = False
                if line.startswith('*'):
                    enabled = True

                if name not in [i.name for i in self.mods]:
                    continue

                for mod in self.mods:
                    if mod.name == name:
                        mod.enabled = enabled
                        ordered_mods.append(mod)
                        break
        for mod in self.mods:
            if mod not in ordered_mods:
                ordered_mods.append(mod)
        self.mods = ordered_mods


    def load_plugins(self):
        """
        Read the DLCList.txt and Plugins.txt files.
        Add Plugins from these files to the list of managed plugins,
        with attention to the order and enabled state.
        """
        # Create the plugins file if it didn't already exist.
        os.makedirs(os.path.split(self.plugin_file)[0], exist_ok=True)
        if not os.path.exists(self.plugin_file):
            with open(self.plugin_file, "w") as file:
                file.write("")

        # Detect whether DLCList.txt needs parsing.
        files_with_plugins = [self.plugin_file]
        if os.path.exists(self.dlc_file):
            files_with_plugins.append(self.dlc_file)

        for file_with_plugin in files_with_plugins:
            with open(file_with_plugin, "r") as file:
                for line in file:
                    # Empty lines
                    if not line.strip():
                        continue
                    # Comments
                    if line.startswith('#'):
                        continue

                    # Initially assign all plugin parents as a DLC.
                    # If the plugin has a parent mod, assign parent as that Mod.
                    # This is used to track ownership for when a mod is disabled.
                    name = line.strip('*').strip()
                    parent_mod = DLC(name)
                    for mod in self.mods:
                        if name in mod.plugins:
                            parent_mod = mod
                            break

                    enabled = False
                    pre_existing = False
                    if line.startswith('*'):
                        enabled = True
                        # Attempt to enable the parent mod,
                        # Only do this if all that mod's files are present.
                        if parent_mod.files_in_place():
                            parent_mod.enabled = True

                        for plug in self.plugins:
                            # Enable DLC if it's already in the plugins list as enabled.
                            if plug.name == name:
                                plug.enabled = True
                                pre_existing = True
                                break

                    if pre_existing:
                        # This file was already added from DLCList.txt
                        continue

                    plugin = Plugin(name, enabled, parent_mod)
                    # Only manage plugins belonging to enabled mods.
                    if parent_mod.enabled and plugin.name not in [i.name for i in self.plugins]:
                        self.plugins.append(plugin)

        return True


    def load_downloads(self):
        """
        Populates self.downloads. Ignores downloads that have a '.part' file that
        starts with the same name. This hides downloads that haven't completed yet.
        """
        downloads = []
        for file in os.listdir(DOWNLOADS):
            still_downloading = False
            if any([file.endswith(ext) for ext in [".rar", ".zip", ".7z"]]):
                for other_file in [
                    i for i in os.listdir(DOWNLOADS) if i.startswith(
                        os.path.splitext(file)[0]
                    )
                ]:
                    if other_file.lower().endswith(".part"):
                        still_downloading = True
                        break
                if still_downloading:
                    continue
                download = Download(file, os.path.join(DOWNLOADS, file))
                downloads.append(download)
        self.downloads = downloads
        return True


    def save_order(self):
        """
        Writes ammo.conf and Plugins.txt.
        """
        with open(self.plugin_file, "w") as file:
            for plugin in self.plugins:
                file.write(f"{'*' if plugin.enabled else ''}{plugin.name}\n")
        with open(self.conf, "w") as file:
            for mod in self.mods:
                file.write(f"{'*' if mod.enabled else ''}{mod.name}\n")
        return True


    def install(self, download_index):
        """
        Extracts a Download to ammo's mod folder.
        """
        if self.changes:
            print("commit changes to disk before installing a mod,")
            print("as this will force a data reload from disk.")
            return False

        if not self.downloads:
            print(f"{DOWNLOADS} has no eligible files.")
            return False

        try:
            index = int(download_index)
        except ValueError:
            print("expected an integer")
            return False

        if index > len(self.downloads) - 1:
            print(f"Expected int 0 through {len(self.downloads) - 1} (inclusive)")
            return False

        download = self.downloads[index]
        if not download.sane:
            download.sanitize()

        # Get a decent name for the output folder.
        # This has to be done for a safe 7z call.
        output_folder = ''.join(
            [i for i in os.path.splitext(download.name)[0] if i.isalnum() or i == '_']
        ).strip('_')
        if not output_folder:
            output_folder = os.path.splittext(download.name)[0]

        extract_to = os.path.join(self.mods_dir, output_folder)
        extracted_files = []
        try:
            os.system(f"7z x '{download.location}' -o'{extract_to}'")
            extracted_files = os.listdir(extract_to)
        except FileNotFoundError:
            print("There was an issue extracting files. Is this a real archive?")
            return False

        if len(extracted_files) == 1 \
        and extracted_files[0].lower() not in [
            'data',
            'skse',
            'bashtags',
            'docs',
            'meshes',
            'textures',
            'animations',
            'interface',
            'misc',
            'shaders',
            'sounds',
            'voices',
        ] \
        and not os.path.splitext(extracted_files[0])[-1] in ['.esp', '.esl', '.esm']:
            # It is reasonable to conclude an extra directory can be eliminated.
            # This is needed for mods like skse that have a version directory
            # between the mod's root folder and the Data folder.
            for file in os.listdir(os.path.join(extract_to, extracted_files[0])):
                filename  = os.path.join(extract_to, extracted_files[0], file)
                shutil.move(filename, extract_to)

        self._hard_refresh()
        return True


    def print_status(self):
        """
        Outputs a list of all downloads, then mods, then plugins.
        """

        if len(self.downloads):
            print()
            print("Downloads")
            print("---------")

            for index, download in enumerate(self.downloads):
                print(f"[{index}] {download.name}")

            print()

        for index, components in enumerate([self.mods, self.plugins]):
            print(f" ### | Activated | {'Mod name' if index == 0 else 'Plugin name'}")
            print("-----|-----------|-----")
            for priority, component in enumerate(components):
                num = f"[{priority}]     "
                l = len(str(priority)) + 1
                num = num[0:-l]
                enabled = "[True]     " if component.enabled else "[False]    "
                print(f"{num} {enabled} {component.name}")
            print()


    def help(self):
        """
        prints help text.
        """
        print()
        print("Commands")
        print("----------------------------------------")
        for k, v in {
            'install <index>': '                         Extract and manage an archive from ~/Downloads.',
            'activate mod|plugin <index>': '             Enabled components will be loaded by game.',
            'deactivate mod|plugin <index>': '           Disabled components will not be loaded by game.',
            'delete download|mod <index>': '             Removes specified file from the filesystem.',
            'move mod|plugin <from_index> <to_index>': ' Larger numbers win file conflicts.',
            'commit': '                                  Apply and save this configuration.',
            'exit': '                                    Quit. Warns on uncommitted changes.',
            'help': '                                    Show this menu.',
            'refresh': '                                 Reload configuration and files from disk.',
            'vanilla': '                                 Disable all managed components and clean up.',
        }.items():
            print(f"{k} {v}")
        print()
        input("[Enter] to continue")
        return True


    def _get_validated_components(self, component_type, mod_index):
        index = None
        try:
            index = int(mod_index)
            if index < 0:
                raise ValueError
        except ValueError:
            print("Expected a number greater than or equal to 0")
            return False

        if component_type not in ["plugin", "mod"]:
            print(f"Expected 'plugin' or 'mod', got arg {component_type}")
            return False
        components = self.plugins if component_type == "plugin" else self.mods
        if not len(components):
            print(f"Install mods to '{self.mods_dir}' to manage them with ammo.")
            print(f"To see plugins, the mods they belong to must be activated.")
            return False

        if index > len(components) - 1:
            print(f"Expected int 0 through {len(components) - 1} (inclusive)")
            return False

        return components


    def _set_component_state(self, component_type, mod_index, state):
        """
        Activate or deactivate a component.
        Returns which plugins need to be added to or removed from self.plugins.
        """
        components = self._get_validated_components(component_type, mod_index)
        if not components:
            print(f"There are no {component_type}s. [Enter]")
            return False

        self.changes = True
        return components[int(mod_index)].set(state, self.plugins)


    def activate(self, component_type, mod_index):
        """
        Activate a component. Returns success.
        """
        return self._set_component_state(component_type, mod_index, True)


    def deactivate(self, component_type, mod_index):
        """
        Aeactivate a component. Returns success.
        """
        return self._set_component_state(component_type, mod_index, False)


    def delete(self, component_type, mod_index):
        """
        Deletes a mod from ammo's mod dir. Forces data reload from disk,
        possibly discarding unapplied changes.
        """

        if self.changes:
            print("Changes must be committed before deleting a component, as this will")
            print("force a data reload from disk.")
            return False

        if component_type not in ["download", "mod"]:
            print(f"Expected either 'download' or 'mod', got '{component_type}'")
            return False

        if component_type == "mod":
            if not self.deactivate("mod", mod_index):
                # validation error
                return False

            # Remove the mod from Ammo then delete it.
            mod = self.mods.pop(int(mod_index))
            shutil.rmtree(mod.location)
            self.commit()
        else:
            try:
                index = int(mod_index)
            except ValueError:
                print("Expected a number greater than or equal to 0")
                return False
            name = self.downloads[index].name
            try:
                os.remove(self.downloads[index].location)
                self.downloads.pop(index)
            except IsADirectoryError:
                print(f"Error deleting {name}, it is a directory not an archive!")
                return False
        return True


    def move(self, component_type, old_mod_index, new_mod_index):
        """
        Move a mod or plugin from old index to new index.
        """
        components = None
        for index in [old_mod_index, new_mod_index]:
            components = self._get_validated_components(component_type, index)
            if not components:
                return False

        old_ind = int(old_mod_index)
        new_ind = int(new_mod_index)

        component = components.pop(old_ind)
        components.insert(new_ind, component)
        self.changes = True
        return True


    def _clean_data_dir(self):
        """
        Removes all symlinks and deletes empty folders.
        """
        # remove symlinks
        for dirpath, dirnames, filenames in os.walk(self.game_dir):
            for file in filenames:
                full_path = os.path.join(dirpath, file)
                if os.path.islink(full_path):
                    os.unlink(full_path)


        # remove empty directories
        def remove_empty_dirs(path):
            for dirpath, dirnames, filenames in list(os.walk(path, topdown=False)):
                for dirname in dirnames:
                    try:
                        os.rmdir(os.path.realpath(os.path.join(dirpath, dirname)))
                    except OSError:
                        # directory wasn't empty, ignore this
                        pass

        remove_empty_dirs(self.game_dir)
        return True


    def vanilla(self):
        print("This will disable all mods and plugins, and remove all symlinks and empty folders from the game dir.")
        print("ammo will remember th mod load order but not the plugin load order.")
        print("These changes will take place immediately.")
        choice = input("continue? [y/n]: ")
        if choice.lower() != "y":
            print("Not cleaned.")
            return False

        for mod in self.mods:
            mod.set(False, self.plugins)
        self.save_order()
        self._clean_data_dir()
        return True


    def stage(self):
        """
        Returns a dict containing the final symlinks that will be installed.
        """
        def normalize(destination):
            """
            Prevent folders with the same name but different case from being created.
            """
            path, file = os.path.split(destination)
            local_path = path.split(self.game_dir)[-1].lower()
            for i in ['Data', 'DynDOLOD', 'Plugins', 'SKSE', 'Edit Scripts', 'Docs', 'Scripts', 'Source']:
                local_path = local_path.replace(i.lower(), i)
            new_dest = os.path.join(self.game_dir, local_path.lstrip('/'))
            result = os.path.join(new_dest, file)
            return result

        # destination: (mod_name, source)
        result = {}
        # Iterate through enabled mods in order.
        for mod in [i for i in self.mods if i.enabled]:
            # Iterate through the source files of the mod
            for src in mod.files.values():
                # Get the sanitized full relative to the game directory.
                corrected_name = src.split(mod.name, 1)[-1]
                # It is possible to make a mod install in the game dir instead of the data dir
                # by setting mod.data_dir = True.
                if mod.data_dir:
                    dest = os.path.join(
                            self.game_dir,
                            corrected_name.replace('/data', '/Data').lstrip('/')
                    )
                    dest = normalize(dest)
                else:
                    dest = os.path.join(
                            self.game_dir,
                            'Data' + corrected_name,
                    )
                    dest = normalize(dest)
                # Add the sanitized full path to the stage, resolving conflicts.
                result[dest] = (mod.name, src)
        return result


    def commit(self):
        """
        Makes changes persist on disk.
        """
        self.save_order()
        stage = self.stage()
        self._clean_data_dir()

        all_files_success = True
        count = len(stage)
        skipped_files = []
        for index, (dest, source) in enumerate(stage.items()):
            os.makedirs(os.path.split(dest)[0], exist_ok=True)
            (name, src) = source
            try:
                os.symlink(src, dest)
            except FileExistsError:
                skipped_files.append(f"{name} skipped overwriting an unmanaged file: {dest.split(self.game_dir)[-1].lstrip('/')}.")
            finally:
                print(f"files processed: {index+1}/{count}", end='\r', flush=True)
        print()
        for skipped_file in skipped_files:
            print(skipped_file)
        self.changes = False
        # Always return False so status messages persist.
        return False


    def _exit(self):
        if self.changes:
            print("There are unsaved changes!")
            answer = input("quit anyway? [y/n]: ").lower()
            if answer == "y":
                exit()
            return True
        exit()


    def _hard_refresh(self):
        self.downloads = []
        self.mods = []
        self.plugins = []

        self.load_mods()
        self.load_mods_from_conf()
        self.load_plugins()
        self.load_downloads()
        self.changes = False

        return True


    def refresh(self):
        if self.changes:
            print("There are unsaved changes!")
            print("refreshing reloads data from disk.")
            answer = input("reload data from disk and lose unsaved changes? [y/n]: ").lower()
            if answer == "y":
                self._hard_refresh()
                return True
            return False
        self._hard_refresh()
        return True


    def run(self):
        self._hard_refresh()

        # get a map of commands to functions and the amount of args they expect
        self.command = {
            # cmd: (method, len(args))
            "activate": {"func": self.activate, "num_args": 2},
            "vanilla": {"func": self.vanilla, "num_args": 0},
            "commit": {"func": self.commit, "num_args": 0},
            "deactivate": {"func": self.deactivate, "num_args": 2},
            "delete": {"func": self.delete, "num_args": 2},
            "disable": {"func": self.deactivate, "num_args": 2}, # alias to deactivate
            "enable": {"func": self.activate, "num_args": 2}, # alias to activate
            "exit": {"func": self._exit, "num_args": 0},
            "help": {"func": self.help, "num_args": 0},
            "install": {"func": self.install, "num_args": 1},
            "move": {"func": self.move, "num_args": 3},
            "refresh": {"func": self.refresh, "num_args": 0}, # reload data from disk
        }

        cmd = ""

        try:
            while True:
                os.system("clear")
                self.print_status()
                cmd = input(">_: ")
                if not cmd:
                    continue
                cmds = cmd.split()
                args = []
                func = cmds[0]
                if len(cmds) > 1:
                    args = cmds[1:]
                if func not in self.command:
                    self.help()
                    continue
                command = self.command[func]
                if command["num_args"] != len(args):
                    print(f"{func} expected {command['num_args']} arg(s) but received {len(args)}")
                    input("[Enter]")
                    continue
                if command["num_args"] == 0:
                    ret = command["func"]()
                elif command["num_args"] == 1:
                    ret = command["func"](args[0])
                elif command["num_args"] == 2:
                    ret = command["func"](args[0], args[1])
                else:
                    ret = command["func"](args[0], args[1], args[2])

                if not ret:
                    input("[Enter]")
                    continue

        except KeyboardInterrupt:
            if self.changes:
                print()
                print("There were unsaved changes! Please run 'commit' before exiting.")
                print()
            exit()


if __name__ == "__main__":
    # game selection
    games = os.listdir(os.path.join(STEAM, "common"))
    games = [game for game in games if game in IDS]
    if len(games) == 1:
        choice = 0
    elif len(games) > 1:
        while True:
            choice = None
            print("Index   |   Game")
            print("----------------")
            for index, game in enumerate(games):
                print(f"[{index}]         {game}")
            choice = input("Index of game to manage: ")
            try:
                choice = int(choice)
                assert choice in range(len(games))
            except ValueError:
                print(f"Expected integer 0 through {len(games) - 1} (inclusive)")
                continue
            except AssertionError:
                print(f"Expected integer 0 through {len(games) - 1} (inclusive)")
                continue
            break
    else:
        print("Install a game through steam!")
        print("ammo supports Skyrim, Skyrim SE, Fallout 4, and Oblivion.")
        print(f"ammo looks for games in {os.path.join(STEAM, 'common')}")
        print("ammo stores mods in ~/.local/share/ammo")
        print("ammo looks for mods to install in ~/Downloads")
        exit()

    # create the paths
    app_name = games[choice]
    app_id = IDS[app_name]
    pfx = os.path.join(STEAM, f"compatdata/{app_id}/pfx")
    game_dir = os.path.join(STEAM, f"common/{app_name}")
    app_data = os.path.join(STEAM, f"{pfx}/drive_c/users/steamuser/AppData/Local")
    plugins = os.path.join(app_data, f"{app_name.replace('t 4', 't4')}/Plugins.txt")
    dlc = os.path.join(app_data, f"{app_name.replace('t 4', 't4')}/DLCList.txt")

    data = os.path.join(game_dir, "Data")
    mods_dir = os.path.join(HOME, f".local/share/ammo/{app_name}/mods")
    conf_dir = os.path.join(HOME, f".local/share/ammo/{app_name}")
    conf = os.path.join(conf_dir, "ammo.conf")

    # Create expected directories if they don't alrady exist.
    expected_dirs = [mods_dir, conf_dir]
    for directory in expected_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # Create an instance of Ammo and run it.
    ammo = Ammo(app_name, game_dir, data, conf, dlc, plugins, mods_dir)
    exit(ammo.run())

