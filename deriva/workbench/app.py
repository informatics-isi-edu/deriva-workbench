"""Workbench app window launcher.
"""
import os
import sys
import traceback

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyleFactory, QMessageBox

from deriva.core import format_exception, BaseCLI
from .window import WorkbenchWindow
from . import resources, __version__


class WorkbenchApp(BaseCLI):

    def __init__(self, description, epilog, cookie_persistence=True):
        super().__init__(description, epilog, __version__)
        self.cookie_persistence = cookie_persistence

    @staticmethod
    def excepthook(etype, value, tb):
        traceback.print_tb(tb)
        print(format_exception(value), file=sys.stderr)
        msg = QMessageBox()
        msg.setText(str(value))
        msg.setStandardButtons(QMessageBox.Close)
        msg.setWindowTitle("Unhandled Exception: %s" % etype.__name__)
        msg.setIcon(QMessageBox.Critical)
        msg.setDetailedText('\n'.join(traceback.format_exception(etype, value, tb)))
        msg.exec_()

    def main(self):
        sys.excepthook = WorkbenchApp.excepthook
        self.parser.add_argument("--no-persistence", action="store_true", help="Disable cookie and local storage persistence for QtWebEngine.")
        self.parser.add_argument("--catalog", type=str, help="Catalog identifier")
        args = self.parse_cli()
        config_file = args.config_file or os.path.expanduser('~') + '/.deriva/workbench.json'

        QApplication.setDesktopSettingsAware(False)
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(":/icons/workbench.png"))
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)

        window = WorkbenchWindow(args.host,
                                 args.catalog,
                                 config_file,
                                 credential_file=args.credential_file,
                                 cookie_persistence=not args.no_persistence)
        window.show()
        ret = app.exec_()
        window.destroy()
        return ret
