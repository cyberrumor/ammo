#!/usr/bin/env python3

import ammo
from test.common import AmmoController

with AmmoController() as controller:
    ui = ammo.ui.UI(controller)
    ui.repl()
