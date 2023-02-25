#!/usr/bin/env python3
import inspect
import os

class UI:
    def __init__(self, controller):
        self.controller = controller

        # get a map of commands to functions and the amount of args they expect
        self.command = {}

        for name, func in inspect.getmembers(self.controller.__class__, predicate=inspect.isfunction):
            # Only map "public" methods
            if name.startswith('_'):
                continue

            self.command[name] = {
                "func": func,
                "args": list(inspect.signature(func).parameters)[1:],
                "num_args": len(inspect.signature(func).parameters) - 1,
                "doc": str(func.__doc__).strip(),
                "instance": self.controller,
            }

        # Add methods of this UI class that will be available regardless of the controller.
        self.command['help'] = {
            "func": self.help,
            "args": [],
            "num_args": 0,
            "doc": str(self.help.__doc__).strip(),
        }

        self.command['exit'] = {
            "func": self.exit,
            "args": [],
            "num_args": 0,
            "doc": str(self.exit.__doc__).strip(),
        }
    def help(self):
        """
        Show this menu.
        """
        column_cmd = []
        column_arg = []
        column_doc = []

        for k, v in sorted(self.command.items()):
            params = []
            args = v["args"]
            anno = v["func"].__annotations__
            for arg in args:
                if arg in anno:
                    params.append(str(anno[arg]).lower().replace("mod.", "").replace(" | ", "|"))
                else:
                    params.append(f"<{arg}>")
            # print(f"{k} {' '.join(params)} {v['doc']}")
            column_cmd.append(k)
            column_arg.append(' '.join(params))
            column_doc.append(v['doc'])


        pad_cmd = max([len(i) for i in column_cmd]) + 1
        pad_arg = max([len(i) for i in column_arg]) + 1
        # pad_doc = max([len(i) for i in column_doc]) + 1

        for cmd, arg, doc in zip(column_cmd, column_arg, column_doc):
            print(f"{cmd}{' ' * (pad_cmd - len(cmd))}{arg}{' ' * (pad_arg - len(arg))}{doc}")




    def exit(self):
        """
        Quit. Prompts if there are changes.
        """
        do_quit = True
        if self.controller.changes:
            do_quit = input("There are unapplied changes. Quit? [y/n]: ").lower() == 'y'
        if do_quit:
            exit()
        return True


    def print_status(self):
        """
        Outputs a list of all downloads, then mods, then plugins.
        """
        if len(self.controller.downloads):
            print()
            print("Downloads")
            print("---------")

            for index, download in enumerate(self.controller.downloads):
                print(f"[{index}] {download}")

            print()

        for index, components in enumerate([self.controller.mods, self.controller.plugins]):
            print(f" ### | Activated | {'Mod name' if index == 0 else 'Plugin name'}")
            print("-----|-----------|-----")
            for priority, component in enumerate(components):
                num = f"[{priority}]     "
                l = len(str(priority)) + 1
                num = num[0:-l]
                print(f"{num} {component}")
            print()


    def repl(self):
        cmd: str = ""
        try:
            while True:
                os.system("clear")
                self.print_status()
                cmd = input(f"{self.controller.name} >_: ")
                if not cmd:
                    continue
                cmds = cmd.split()
                args = []
                func = cmds[0]
                if len(cmds) > 1:
                    args = cmds[1:]
                command = self.command.get(func, None)
                if not command:
                    print(f"unknown command {cmd}")
                    self.help()
                    input("[Enter]")
                    continue
                if command["num_args"] != len(args):
                    print(f"{func} expected {command['num_args']} arg(s) but received {len(args)}")
                    input("[Enter]")
                    continue

                if "instance" in command:
                    args.insert(0, command["instance"])
                ret = command["func"](*args)
                if not ret:
                    input("[Enter]")
                    continue

        except KeyboardInterrupt:
            if self.controller.changes:
                print()
                print("There were unsaved changes! Please run 'commit' before exiting.")
                print()
            exit()


