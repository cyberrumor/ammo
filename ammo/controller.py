#!/usr/bin/env python3
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
        return ""
