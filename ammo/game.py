from dataclasses import dataclass
from pathlib import Path


@dataclass
class Game:
    name: str
    directory: Path
    data: Path
    ammo_conf: Path
    dlc_file: Path
    plugin_file: Path
    ammo_mods_dir: Path
