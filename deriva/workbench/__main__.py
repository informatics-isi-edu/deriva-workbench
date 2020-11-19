"""Workbench main routine.
"""
import sys
from deriva.workbench.app import WorkbenchApp

DESC = "DERIVA Schema Workbench"
INFO = "For more information see: https://github.com/informatics-isi-edu/deriva-workbench"


def main():
    app = WorkbenchApp(DESC, INFO)
    return app.main()


if __name__ == '__main__':
    sys.exit(main())
