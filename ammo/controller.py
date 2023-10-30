#!/usr/bin/env python3
from pathlib import Path
from abc import (
    ABC,
    abstractmethod,
)


class Controller(ABC):
    """
    Public methods of this class will be exposed
    to the UI.
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def _prompt(self) -> str:
        """
        This returns the prompt for user input.
        """
        return ""

    @abstractmethod
    def _post_exec(self) -> bool:
        """
        This function is executed after every command.
        It returns whether the UI should break from repl.
        """
        return True

    @abstractmethod
    def _normalize(self, destination: Path, dest_prefix: Path) -> Path:
        """
        Prevent folders with the same name but different case
        from being created.
        """
        path = destination.parent
        file = destination.name
        local_path: str = str(path).split(str(dest_prefix))[-1].lower()
        for i in [
            "Data",
            "DynDOLOD",
            "Plugins",
            "SKSE",
            "Edit Scripts",
            "Docs",
            "Scripts",
            "Source",
        ]:
            local_path = local_path.replace(i.lower(), i)
        new_dest: Path = Path(dest_prefix / local_path.lstrip("/"))
        result = new_dest / file
        return result
