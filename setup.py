from setuptools import setup

setup(
    name="ammo",
    version="0.1",
    description="A simple terminal based mod organizer for Linux.",
    author="cyberrumor",
    url="https://github.com/cyberrumor/ammo",
    packages=["ammo", "ammo/controller"],
    scripts=["ammo/bin/ammo"],
)
