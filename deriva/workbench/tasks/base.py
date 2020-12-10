"""Base class for workbench tasks.
"""
from PyQt5.QtCore import QObject, pyqtSignal
from deriva.qt import async_execute


class WorkbenchTask(QObject):
    """Base class for workbench tasks, based on similar class from the `deriva.qt` package.
    """

    status_update_signal = pyqtSignal(bool, str, str, object)
    progress_update_signal = pyqtSignal(int, int)

    def __init__(self, connection, parent=None):
        super(WorkbenchTask, self).__init__(parent)
        assert (connection is not None and isinstance(connection, dict))
        self.connection = connection
        self.task = None

    def start(self):
        async_execute(self.task)

    def cancel(self):
        self.task.cancel()

    def set_status(self, success, status, detail, result):
        self.status_update_signal.emit(success, status, detail, result)

    def progress_callback(self, current, maximum):
        if self.task.canceled:
            return False

        self.progress_update_signal.emit(current, maximum)
        return True