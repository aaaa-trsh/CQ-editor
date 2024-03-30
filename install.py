# install cadquery

import os
import sys
import subprocess

pkgs = [
    # "PyQt5",
    # "pyqtgraph",
    # "spyder",
    # "path",
    # "logbook",
    # "requests",
    # "qtconsole",
    # "QtAwesome"
    "pyqtdarktheme"

]

def install(pkg):
    subprocess.run([sys.executable, "-m", "pip", "install", pkg])

for pkg in pkgs:
    install(pkg)