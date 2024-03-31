import sys
import argparse
import os

os.environ["QT_ENABLE_HIGHDPI_SCALING"]   = "0"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR"]             = "1"

from PyQt5.QtWidgets import QApplication

NAME = 'CQ-editor'

app = QApplication(sys.argv, applicationName=NAME)

import qdarktheme
qdarktheme.setup_theme()

from .main_window import MainWindow

def main():

    parser = argparse.ArgumentParser(description=NAME)
    parser.add_argument('filename',nargs='?',default=None)

    args = parser.parse_args(app.arguments()[1:])

    win = MainWindow(filename=args.filename if args.filename else None)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":

    main()
