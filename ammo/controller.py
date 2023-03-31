#!/usr/bin/env python3
import os
import shutil
from xml.etree import ElementTree
from mod import Mod, Download, Plugin, DLC

class Controller:
    def __init__(self, app_name, game_dir, data_dir, conf, dlc_file, plugin_file, mods_dir, downloads_dir):
        self.name = app_name
        self.game_dir = game_dir
        self.data_dir = data_dir
        self.conf = conf
        self.dlc_file = dlc_file
        self.plugin_file = plugin_file
        self.mods_dir = mods_dir
        self.downloads_dir = downloads_dir

        self.downloads = []
        self.mods = []
        self.plugins = []

        # Instance a Mod class for each mod folder in the mod directory.
        mods = []
        mod_folders = [i for i in os.listdir(self.mods_dir) if os.path.isdir(os.path.join(self.mods_dir, i))]
        for name in mod_folders:
            mod = Mod(
                name,
                location = os.path.join(self.mods_dir, name),
                parent_data_dir = self.data_dir
            )
            mods.append(mod)
        self.mods = mods

        # Read the configuration file. If there's mods in it, put them in order.
        # Put mods that aren't listed in the conf file at the end.
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

        # Read the DLCList.txt and Plugins.txt files.
        # Add Plugins from these files to the list of managed plugins,
        # with attention to the order and enabled state.
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

                    # Don't manage order of manually installed mods that were deleted.
                    if not os.path.exists(os.path.join(self.data_dir, name)):
                        continue

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


        # Populate self.downloads. Ignore downloads that have a '.part' file that
        # starts with the same name. This hides downloads that haven't completed yet.
        downloads = []
        for file in os.listdir(self.downloads_dir):
            still_downloading = False
            if any([file.endswith(ext) for ext in [".rar", ".zip", ".7z"]]):
                for other_file in [
                    i for i in os.listdir(self.downloads_dir) if i.startswith(
                        os.path.splitext(file)[0]
                    )
                ]:
                    if other_file.lower().endswith(".part"):
                        still_downloading = True
                        break
                if still_downloading:
                    continue
                download = Download(file, os.path.join(self.downloads_dir, file))
                downloads.append(download)
        self.downloads = downloads
        self.changes = False


    def __reset__(self):
        """
        Convenience function that reinitializes the controller instance.
        """
        self.__init__(
            self.name,
            self.game_dir,
            self.data_dir,
            self.conf,
            self.dlc_file,
            self.plugin_file,
            self.mods_dir,
            self.downloads_dir,
        )


    def _save_order(self):
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


    def install(self, index):
        """
        Extract and manage an archive from ~/Downloads.
        """
        if self.changes:
            print("commit changes to disk before installing a mod,")
            print("as this will force a data reload from disk.")
            return False

        if not self.downloads:
            print(f"{self.downloads_dir} has no eligible files.")
            return False

        try:
            index = int(index)
        except ValueError:
            print("expected an integer")
            return False

        if index > len(self.downloads) - 1:
            print(f"Expected int 0 through {len(self.downloads) - 1} (inclusive)")
            return False

        download = self.downloads[index]
        if not download.sane:
            # Sanitize the download name to guarantee compatibility with 7z syntax.
            fixed_name = download.name.replace(' ', '_')
            fixed_name = ''.join(
                    [i for i in fixed_name if i.isalnum() or i in ['.', '_', '-']]
            )
            parent_folder = os.path.split(download.location)[0]
            new_location = os.path.join(parent_folder, fixed_name)
            os.rename(download.location, new_location)
            download.location = new_location
            download.name = fixed_name
            download.sane = True

        # Get a decent name for the output folder.
        # This has to be done for a safe 7z call.
        output_folder = ''.join(
            [i for i in os.path.splitext(download.name)[0] if i.isalnum() or i == '_']
        ).strip('_')
        if not output_folder:
            output_folder = os.path.splitext(download.name)[0]

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

        self.__reset__()
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
        if len(components) == 0:
            print(f"Install mods to '{self.mods_dir}' to manage them with ammo.")
            print("To see plugins, the mods they belong to must be activated.")
            return False

        if index > len(components) - 1:
            print(f"Expected int 0 through {len(components) - 1} (inclusive)")
            return False

        return components


    def _fomod_validated(self, index):
        """
        Returns false if there is an issue preventing fomod configuration.
        Otherwise, returns the root node of the parsed ModuleConfig.xml.
        """
        if not (components := self._get_validated_components("mod", index)):
            print("Invalid index.")
            return False

        mod = components[int(index)]
        if not mod.fomod:
            print("'configure' was called on something other than a fomod. Aborting.")
            return False

        if not mod.modconf:
            print("Unable to find ModuleConfig.xml for this fomod.")
            print("Please configure manually in:")
            print(mod.location)
            print("Once there is a data dir inside that folder with the desired files in place,")
            print("refresh and try again.")
            return False

        # If there is already a Data dir in the mod folder,
        # warn that this is the point of no return.
        if mod.data_dir:
            print("This has been configured previously.")
            choice = input("Discard previous configuration and continue? [y/n]: ").lower() == "y"
            if not choice:
                print("No changes made.")
                return False

            # Clean up previous configuration.
            try:
                shutil.rmtree(os.path.join(mod.location, "Data"))
            except FileNotFoundError:
                pass

            # disable this mod and commit to prevent polluting the data dir
            self.deactivate("mod", index)
            self.commit()
            self.__reset__()

        # Parse the fomod installer.
        try:
            tree = ElementTree.parse(mod.modconf)
            root = tree.getroot()
        except:
            print("This mod's ModuleConfig.xml is malformed.")
            print("Please configure manually, refresh, and try again.")
            return False

        return root


    def _fomod_required_files(self, fomod_installer_root_node):
        """
        get a list of files that are always required.
        """
        return fomod_installer_root_node.find("requiredInstallFiles")


    def _fomod_install_steps(self, fomod_installer_root_node):
        """
        get a native data type (dict) representing this fomod's install stpes.
        """
        steps = {}
        # Find all the install steps
        for step in fomod_installer_root_node.find("installSteps"):
            for optional_file_groups in step:
                for group in optional_file_groups:
                    step_name = group.get("name")
                    steps[step_name] = {}
                    steps[step_name]["type"] = group.get("type")
                    steps[step_name]["plugins"] = []
                    plugins = steps[step_name]["plugins"]
                    if not (group_of_plugins := group.find("plugins")):
                        continue
                    for plugin_index, plugin in enumerate(group_of_plugins):
                        plug_dict = {}
                        plugin_name = plugin.get("name").strip()
                        plug_dict["name"] = plugin_name
                        plug_dict["description"] = plugin.find("description").text.strip()
                        plug_dict["flags"] = {}
                        # Automatically mark the first option as selected when a selection
                        # is required.
                        plug_dict["selected"] = (steps[step_name]["type"] in [
                                    "SelectExactlyOne",
                                    "SelectAtLeastOne"
                                ]) and plugin_index == 0

                        # Interpret on/off or 1/0 as true/false
                        if (conditional_flags := plugin.find("conditionFlags")):
                            for flag in conditional_flags:
                                # People use arbitrary flags here. Most commonly "On" or "1".
                                plug_dict["flags"][flag.get("name")] = flag.text in ["On", "1"]
                            plug_dict["conditional"] = True

                        else:
                            # There were no conditional flags, so this was an unconditional install.
                            plug_dict["conditional"] = False

                        plug_dict["files"] = []
                        if (plugin_files := plugin.find("files")):
                            for i in plugin_files:
                                plug_dict["files"].append(i)

                        plugins.append(plug_dict)

        return steps


    def _init_fomod_chosen_files(self, index, to_install):
        """
        Copy the chosen files 'to_install' from given mod at 'index'
        to that mod's Data folder.
        """
        mod = self.mods[int(index)]
        data = os.path.join(mod.location, "Data")

        # delete the old configuration if it exists
        try:
            shutil.rmtree(data)
        except:
            pass

        os.makedirs(data, exist_ok=True)

        stage = {}
        for node in to_install:
            for loc in node:
                # convert the 'source' folder form the xml into a full path
                s = loc.get("source")
                source = mod.location
                for i in s.split('\\'):
                    source = os.path.join(source, i)
                # get the 'destination' folder form the xml. This path is relative to Data.
                destination = ""
                d = loc.get("destination")
                for i in d.split('\\'):
                    destination = os.path.join(destination, i)

                for parent_path, folders, files in os.walk(source):
                    rel_dest_path = parent_path.split(source)[-1].lstrip('/')

                    for folder in folders:
                        rel_folder_path = os.path.join(rel_dest_path, folder)
                        full_folder_path = os.path.join(data, rel_folder_path)
                        os.makedirs(full_folder_path, exist_ok=True)

                    for file in files:
                        src = os.path.join(parent_path, file)
                        dest = os.path.join(os.path.join(data, rel_dest_path), file)
                        stage[dest] = src

        # install the new files
        for k, v in stage.items():
            shutil.copy(v, k)

        mod.data_dir = True

        return True


    def _set_component_state(self, component_type, mod_index, state):
        """
        Activate or deactivate a component.
        Returns which plugins need to be added to or removed from self.plugins.
        """
        if not (components := self._get_validated_components(component_type, mod_index)):
            print(f"There are no {component_type}s. [Enter]")
            return False
        component = components[int(mod_index)]

        starting_state = component.enabled
        # Handle mods
        if isinstance(component, Mod):

            # Handle configuration of fomods
            if hasattr(component, "fomod") and component.fomod and state and not component.data_dir:
                print("Fomods must be configured before they can be enabled.")
                print(f"Please run 'configure {mod_index}', refresh, and try again.")
                return False

            component.enabled = state
            if component.enabled:
                # Show plugins owned by this mod
                for name in component.plugins:
                    if name not in [i.name for i in self.plugins]:
                        plugin = Plugin(name, False, component)
                        self.plugins.append(plugin)
            else:
                # Hide plugins owned by this mod
                for plugin in component.associated_plugins(self.plugins):
                    plugin.enabled = False

                    if plugin in self.plugins:
                        self.plugins.remove(plugin)

        # Handle plugins
        if isinstance(component, Plugin):
            component.enabled = state

        self.changes = starting_state != component.enabled
        return True


    def activate(self, mod_or_plugin: Mod|Plugin, index):
        """
        Enabled components will be loaded by game.
        """
        return self._set_component_state(mod_or_plugin, index, True)


    def deactivate(self, mod_or_plugin: Mod|Plugin, index):
        """
        Disabled components will not be loaded by game.
        """
        return self._set_component_state(mod_or_plugin, index, False)


    def delete(self, mod_or_download: Mod|Download, index):
        """
        Removes specified file from the filesystem.
        """
        if self.changes:
            print("Changes must be committed before deleting a component, as this will")
            print("force a data reload from disk.")
            return False

        if mod_or_download not in ["download", "mod"]:
            print(f"Expected either 'download' or 'mod', got '{mod_or_download}'")
            return False

        if mod_or_download == "mod":
            if not self.deactivate("mod", index):
                # validation error
                return False

            # Remove the mod from the controller then delete it.
            mod = self.mods.pop(int(index))
            shutil.rmtree(mod.location)
            self.commit()
        else:
            try:
                index = int(index)
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


    def move(self, mod_or_plugin: Mod | Plugin, from_index, to_index):
        """
        Larger numbers win file conflicts.
        """
        components = None
        for index in [from_index, to_index]:
            components = self._get_validated_components(mod_or_plugin, index)
            if not components:
                return False

        old_ind = int(from_index)
        new_ind = int(to_index)

        component = components.pop(old_ind)
        components.insert(new_ind, component)
        self.changes = True
        return True


    def _clean_data_dir(self):
        """
        Removes all symlinks and deletes empty folders.
        """
        # remove symlinks
        for dirpath, _dirnames, filenames in os.walk(self.game_dir):
            for file in filenames:
                full_path = os.path.join(dirpath, file)
                if os.path.islink(full_path):
                    os.unlink(full_path)


        # remove empty directories
        def remove_empty_dirs(path):
            for dirpath, dirnames, _filenames in list(os.walk(path, topdown=False)):
                for dirname in dirnames:
                    try:
                        os.rmdir(os.path.realpath(os.path.join(dirpath, dirname)))
                    except OSError:
                        # directory wasn't empty, ignore this
                        pass

        remove_empty_dirs(self.game_dir)
        return True


    def vanilla(self):
        """
        Disable all managed components and clean up.
        """
        print("This will disable all mods and plugins, and remove all symlinks and \
                empty folders from the game dir.")
        print("ammo will remember th mod load order but not the plugin load order.")
        print("These changes will take place immediately.")
        if input("continue? [y/n]").lower() != "y":
            print("Not cleaned.")
            return False

        for mod in range(len(self.mods)):
            self._set_component_state("mod", mod, False)
        self._save_order()
        self._clean_data_dir()
        return True



    def _normalize(self, destination, dest_prefix):
        """
        Prevent folders with the same name but different case from being created.
        """
        path, file = os.path.split(destination)
        local_path = path.split(dest_prefix)[-1].lower()
        for i in [
                'Data',
                'DynDOLOD',
                'Plugins',
                'SKSE',
                'Edit Scripts',
                'Docs',
                'Scripts',
                'Source']:
            local_path = local_path.replace(i.lower(), i)
        new_dest = os.path.join(dest_prefix, local_path.lstrip('/'))
        result = os.path.join(new_dest, file)
        return result


    def _stage(self):
        """
        Returns a dict containing the final symlinks that will be installed.
        """
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
                    dest = self._normalize(dest, self.game_dir)
                else:
                    dest = os.path.join(
                            self.game_dir,
                            'Data' + corrected_name,
                    )
                    dest = self._normalize(dest, self.game_dir)
                # Add the sanitized full path to the stage, resolving conflicts.
                result[dest] = (mod.name, src)
        return result


    def commit(self):
        """
        Apply and save this configuration.
        """
        self._save_order()
        stage = self._stage()
        self._clean_data_dir()

        count = len(stage)
        skipped_files = []
        for index, (dest, source) in enumerate(stage.items()):
            os.makedirs(os.path.split(dest)[0], exist_ok=True)
            (name, src) = source
            try:
                os.symlink(src, dest)
            except FileExistsError:
                skipped_files.append(f"{name} skipped overwriting an unmanaged file: \
                        {dest.split(self.game_dir)[-1].lstrip('/')}.")
            finally:
                print(f"files processed: {index+1}/{count}", end='\r', flush=True)
        print()
        for skipped_file in skipped_files:
            print(skipped_file)
        self.changes = False
        # Always return False so status messages persist.
        return False


    def refresh(self):
        """
        Reload configuration and files from disk.
        """
        if self.changes:
            print("There are unsaved changes!")
            print("refreshing reloads data from disk.")
            if input("reload data from disk and lose unsaved changes? [y/n]: ").lower() == "y":
                self.__reset__()
                return True
            return False

        self.__reset__()

        return True


