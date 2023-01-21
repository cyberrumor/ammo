#!/usr/bin/env python3
import sys
import os

class Mod:
    def __init__(self, name, location, enabled):
        self.name = name
        self.location = location
        self.files = {}
        self.author = None
        self.page = None
        self.enabled = enabled

class Esp:
    def __init__(self, name, enabled):
        self.name = name
        self.enabled = enabled
