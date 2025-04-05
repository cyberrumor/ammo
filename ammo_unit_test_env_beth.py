#!/usr/bin/env python3

import ammo
from test.common import AmmoController

with AmmoController() as controller:
    ui = ammo.ui.UI(controller, clear_screen=False)
    ui.repl()
