from dataclasses import dataclass


@dataclass
class Game:
    name: str
    directory: str
    data: str
    ammo_conf: str
    dlc_file: str
    plugin_file: str
    ammo_mods_dir: str
