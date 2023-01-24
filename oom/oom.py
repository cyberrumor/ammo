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


class Oom:
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
        Instance a  Mod class for each mod folder in oom's mod directory.
        """
        mods = []
        mod_folders = [i for i in os.listdir(self.mods_dir) if os.path.isdir(os.path.join(self.mods_dir, i))]
        for mod_folder in mod_folders:
            mod = Mod(mod_folder, os.path.join(self.mods_dir, mod_folder), self.data_dir, False)
            mods.append(mod)
        self.mods = mods


    def load_mods_from_conf(self):
        """
        Read our conf file. If there's mods in it, put them in order.
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
                    print(f"we found a mod '{name}' that isn't in {self.conf}. Ignoring.")
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
        # make sure we actually have a plugins file to read, if it
        # didn't already exist. This can happen if the game hasn't been
        # launched before.
        os.makedirs(os.path.split(self.plugin_file)[0], exist_ok=True)
        if not os.path.exists(self.plugin_file):
            with open(self.plugin_file, "w") as file:
                file.write("")
        files_with_plugins = [self.plugin_file]
        if os.path.exists(self.dlc_file):
            files_with_plugins.append(self.dlc_file)

        for file_with_plugin in files_with_plugins:
            with open(file_with_plugin, "r") as file:
                for line in file:
                    if not line.strip():
                        continue
                    if line.startswith('#'):
                        continue

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
                        # attempt to enable the parent mod,
                        # only do this if all that mod's files are present.
                        if parent_mod.files_in_place():
                            parent_mod.enabled = True

                        for plug in self.plugins:
                            # enable DLC if it's already in our plugins list.
                            # plugins.txt as enabled.
                            if plug.name == name:
                                plug.enabled = True
                                pre_existing = True
                                break

                    if pre_existing:
                        # we've already added this file from DLCList.txt
                        continue

                    plugin = Plugin(name, enabled, parent_mod)
                    # only manage plugins belonging to enabled mods.
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
        Writes oom.conf and Plugins.txt.
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
        extracts a Download to oom's mod folder.
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

        # get a decent name for our output folder.
        output_folder = ''.join(
            [i for i in os.path.splitext(download.name)[0] if i.isalnum() or i == '_']
        ).strip('_')
        if not output_folder:
            output_folder = os.path.splittext(download.name)[0]

        extract_to = os.path.join(self.mods_dir, output_folder)
        os.system(f"7z x '{download.location}' -o'{extract_to}'")
        extracted_files = os.listdir(extract_to)
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
                    # we are reasonably sure we can eliminate a redundant directory.
                    # This is needed for mods like skse that have a version directory
                    # between our install location and the mod's data folder.
                    for file in os.listdir(os.path.join(extract_to, extracted_files[0])):
                        filename  = os.path.join(extract_to, extracted_files[0], file)
                        shutil.move(filename, extract_to)
        self._hard_refresh()
        # return false even if successful to show 7z output
        return False

    def print_status(self):
        """
        outputs a list of all downloads, then mods, then plugins.
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


    def help(self, *args):
        """
        prints help text.
        """
        print()
        print("Command    | Syntax")
        print("-------------------")
        for k, v in sorted({
            'activate': '  activate mod|plugin <index>               add a mod or plugin to the stage.',
            'commit': '    commit                                    make this configuration persistent.',
            'deactivate': 'deactivate mod|plugin <index>             remove a mod or plugin from the stage.',
            'delete': '    delete download|mod <index>               delete a file from the filesystem.',
            'disable': '   disable mod|plugin <index>                alias for deactivate.',
            'enable': '    enable mod|plugin <index>                 alias for activate.',
            'exit': '      exit                                      quit without saving changes.',
            'help': '      help                                      show this menu.',
            'install': '   install <index>                           extract a mod from downloads,',
            'move': '      move mod|plugin <from_index> <to_index>   rearrange the load order.',
            'refresh': '   refresh                                   reload all mods/plugins/downloads from disk.',
            'vanilla': '   vanilla                                   disable all components and clean up.',
        }.items()):
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
            print(f"expected 'plugin' or 'mod', got arg {component_type}")
            return False
        components = self.plugins if component_type == "plugin" else self.mods
        if not len(components):
            print(f"Install mods to '{self.mods_dir}' to manage them with oom.")
            print(f"To see your plugins, you must activate the mods they belong ot.")
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
            input(f"There are no {component_type}s. [Enter]")
            return False

        return components[int(mod_index)].set(state, self.plugins)


    def activate(self, component_type, mod_index):
        """
        activate a component. Returns success.
        """
        if not self._set_component_state(component_type, mod_index, True):
            return False
        self.changes = True
        return True


    def deactivate(self, component_type, mod_index):
        """
        deactivate a component. Returns success.
        """
        self._set_component_state(component_type, mod_index, False)
        self.changes = True
        return True


    def delete(self, component_type, mod_index):
        """
        deletes a mod from oom's mod dir. Forces data reload from disk,
        possibly discarding unapplied changes.
        """

        if self.changes:
            print("You must commit changes before deleting a mod, as this will")
            print("force a data reload from disk.")
            return False


        if component_type not in ["download", "mod"]:
            print(f"expected either 'download' or 'mod', got '{component_type}'")
            return False

        if component_type == "mod":
            if not self.deactivate("mod", mod_index):
                # validation error
                return False

            # get the mod out of oom's non-persistent mem.
            mod = self.mods.pop(int(mod_index))
            # delete the mod from oom's mod folder.
            shutil.rmtree(mod.location)
            self.commit()
        else:
            try:
                index = int(mod_index)
            except ValueError:
                print("Expected a number greater than or equal to 0")
                return False
            download = self.downloads.pop(index)
            os.remove(download.location)
        return True


    def move(self, component_type, old_mod_index, new_mod_index):
        """
        move a mod or plugin from old index to new index.
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
        print("This will disable all mods and plugins, and remove all symlinks and empty folders from your game dir.")
        print("oom will remember your mod load order but not your plugin load order.")
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

        # destination: source
        result = {}
        for mod in [i for i in self.mods if i.enabled]:
            for src in mod.files.values():
                corrected_name = src.split(mod.name, 1)[-1]
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
                result[dest] = src
        return result


    def commit(self):
        """
        Makes changes persist on disk.
        """
        self.save_order()
        stage = self.stage()
        self._clean_data_dir()

        for dest, src in stage.items():
            os.makedirs(os.path.split(dest)[0], exist_ok=True)
            os.symlink(src, dest)

        self.changes = False
        return True


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
        print("Install some games to manage through steam!")
        print(f"oom looks for games in {os.path.join(STEAM, 'common')}")
        print("If you were previously managing mods with oom but uninstalled the game,")
        print("you can find your mod files intact in ~/.local/share/oom")
        exit()

    # create out paths
    app_name = games[choice]
    app_id = IDS[app_name]
    pfx = os.path.join(STEAM, f"compatdata/{app_id}/pfx")
    game_dir = os.path.join(STEAM, f"common/{app_name}")
    app_data = os.path.join(STEAM, f"{pfx}/drive_c/users/steamuser/AppData/Local")
    plugins = os.path.join(app_data, f"{app_name.replace(' ', '')}/Plugins.txt")
    dlc = os.path.join(app_data, f"{app_name.replace(' ', '')}/DLCList.txt")

    data = os.path.join(game_dir, "Data")
    mods_dir = os.path.join(HOME, f".local/share/oom/{app_name}/mods")
    conf_dir = os.path.join(HOME, f".local/share/oom/{app_name}")
    conf = os.path.join(conf_dir, "oom.conf")

    # Create expected directories if they don't alrady exist.
    expected_dirs = [mods_dir, conf_dir]
    for directory in expected_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # Create an instance of Oom and run it.
    oom = Oom(app_name, game_dir, data, conf, dlc, plugins, mods_dir)
    exit(oom.run())

