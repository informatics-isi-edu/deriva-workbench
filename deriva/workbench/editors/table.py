"""Components for shared table widgets.
"""
from collections.abc import Callable
from copy import deepcopy
import logging
from PyQt5.QtWidgets import QVBoxLayout, QFrame, QWidget, QTableView, QPushButton, QHBoxLayout, QDialog, QHeaderView
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, pyqtSlot, pyqtSignal
from .common import set_value_or_del_key

logger = logging.getLogger(__name__)


class CommonTableWidget(QWidget):
    """A reusable table widget that supports a common set of operations on list-valued annotation properties.
    """

    value: list
    valueChanged = pyqtSignal()

    class _InternalTableModel(QAbstractTableModel):
        """Internal table model.
        """

        def __init__(self, data: list, headers_fn: Callable = None, row_fn: Callable = None):
            """Initializes the internal data model.

            This is a subclass of the abstract table model for a table view.

            :param data: a list of data to be managed by the component
            :param headers_fn: a function to return the headers of the table
            :param row_fn: a function to return one row tuple for a single given element of the data
            """
            super(CommonTableWidget._InternalTableModel, self).__init__()

            # header
            if headers_fn:
                self.headers = headers_fn(data)
            elif data and isinstance(data[0], dict):
                self.headers = list(data[0].keys())
            else:
                self.headers = ['Value']

            # row values
            if row_fn:
                self.rows = [row_fn(entry) for entry in data]
            elif data and isinstance(data[0], dict):
                self.rows = [tuple(entry.values()) for entry in data]
            else:
                self.rows = [(str(entry),) for entry in data]

        def rowCount(self, parent):
            return len(self.rows)

        def columnCount(self, parent):
            return len(self.headers)

        def data(self, index, role):
            if role != Qt.DisplayRole:
                return QVariant()
            return self.rows[index.row()][index.column()]

        def headerData(self, section, orientation, role):
            if role != Qt.DisplayRole or orientation != Qt.Horizontal:
                return QVariant()
            return self.headers[section]

    def __init__(
            self,
            key: str,
            body: dict,
            editor_widget: QWidget = None,
            editor_dialog_exec_fn: Callable = None,
            headers_fn: Callable = None,
            row_fn: Callable = None,
            resize_mode: QHeaderView.ResizeMode = QHeaderView.Stretch,
            allow_copy: bool = False,
            truth_fn: Callable = bool,
            parent: QWidget = None
    ):
        """Initialize the widget.

        This widget displays a table view for managing list properties of annotations.

        The `editor_widget` must be a widget for entering a new value into the table. It must have a `value` attribute
        or getter that returns a properly structured data element to enter into the managed list of values. This
        param is optional.

        The `editor_dialog_exec_fn` must be a function that accepts a `value` and optional `parent`. The `value` will
        either be an element from the list or `None`. The `parent` will be an instance of QWidget or `None`. The
        function should show a dialog, accept user input, destroy the dialog, and return a `(code, value)` pair where
        `code` should be `QDialog.Accepted` if the dialog was accept or any other value if rejected, and `value` must be
        a properly structured value to be entered into the list. This param is optional.

        An `editor_widget` or `editor_dialog_exec_fn` is required.

        :param key: annotation key
        :param body: annotation body where `body[key]` must be a list of values to be managed by the widget
        :param editor_widget: the widget to be used for entering new values into the list
        :param editor_dialog_exec_fn: a function to return a dialog for adding to or editing values of the list
        :param headers_fn: a function that takes the property as input and returns a list of text for the table header
        :param row_fn: a function that takes an item from the property and returns a flattened tuple for the row value
        :param resize_mode: the resize mode applied to the table view
        :param allow_copy: allow copying (duplication) of table items
        :param truth_fn: function applied to value to determine whether it should be set or dropped from body
        :param parent: parent widget
        """
        assert editor_widget or editor_dialog_exec_fn, "Missing required editor widget or dialog function"
        super(CommonTableWidget, self).__init__(parent=parent)
        self.key, self.body = key, body
        self.headers_fn, self.row_fn = headers_fn, row_fn
        self.resize_mode = resize_mode
        self.editor_widget, self.editor_dialog_exec_fn = editor_widget, editor_dialog_exec_fn
        self._truth_fn = truth_fn
        # ...defensively, get property value
        self.value = body.get(key)
        if not isinstance(self.value, list):
            self.value = []

        # table view
        self.tableView = QTableView(parent=self)
        self.tableView.setModel(self._InternalTableModel(self.value, headers_fn=self.headers_fn, row_fn=self.row_fn))

        # ...table view styling
        self.tableView.setWordWrap(True)
        self.tableView.setAlternatingRowColors(True)
        self.tableView.horizontalHeader().setSectionResizeMode(self.resize_mode)

        # ...table row selection
        self.tableView.doubleClicked.connect(self.on_doubleclick)

        # controls frame
        controls = QFrame()
        hlayout = QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        # ...add column button
        addElement = QPushButton('+', parent=controls)
        addElement.clicked.connect(self.on_add_click)
        hlayout.addWidget(addElement)
        # ...remove column button
        removeElement = QPushButton('-', parent=controls)
        removeElement.clicked.connect(self.on_remove_click)
        hlayout.addWidget(removeElement)
        # ...duplicate column button
        if allow_copy:
            copyElement = QPushButton('copy', parent=controls)
            copyElement.clicked.connect(self.on_duplicate_click)
            hlayout.addWidget(copyElement)
        # ...move up button
        moveUp = QPushButton('up', parent=controls)
        moveUp.clicked.connect(self.on_move_up_click)
        hlayout.addWidget(moveUp)
        # ...move down button
        moveDown = QPushButton('down', parent=controls)
        moveDown.clicked.connect(self.on_move_down_click)
        hlayout.addWidget(moveDown)
        controls.setLayout(hlayout)

        # tab layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tableView)
        if self.editor_widget:
            layout.addWidget(self.editor_widget)
        layout.addWidget(controls)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

    def _refreshTableModel(self):
        """Refreshes the table view model.
        """
        self.tableView.setModel(
            self._InternalTableModel(self.value, headers_fn=self.headers_fn, row_fn=self.row_fn)
        )

    @pyqtSlot()
    def on_add_click(self):
        """Handler for adding an element.
        """
        if self.editor_widget:
            # ...if editor_widget, then take value
            value = deepcopy(self.editor_widget.value)
        else:
            # ...else display dialog and take value if accepted
            code, value = self.editor_dialog_exec_fn(None, parent=self)
            if code != QDialog.Accepted:
                return

        # add value and set
        self.value.append(value)
        set_value_or_del_key(
            self.body,
            self._truth_fn(self.value),
            self.key,
            self.value
        )

        # refresh view model and emit state change
        self._refreshTableModel()
        self.valueChanged.emit()

    @pyqtSlot()
    def on_duplicate_click(self):
        """Handler for duplicating an element.
        """
        index = self.tableView.currentIndex().row()
        if index >= 0:
            duplicate = deepcopy(self.value[index])
            self.value.append(duplicate)
            set_value_or_del_key(
                self.body,
                self._truth_fn(self.value),
                self.key,
                self.value
            )

            # refresh view model and emit state change
            self._refreshTableModel()
            self.valueChanged.emit()

    @pyqtSlot()
    def on_remove_click(self):
        """Handler for removing an element of the list property.
        """
        index = self.tableView.currentIndex().row()
        if index >= 0:
            del self.value[index]
            set_value_or_del_key(
                self.body,
                self._truth_fn(self.value),
                self.key,
                self.value
            )

            # refresh view model and emit state change
            self._refreshTableModel()
            self.valueChanged.emit()

            # update current index
            index = index if index < len(self.value) else index - 1
            self.tableView.selectRow(index)

    @pyqtSlot()
    def on_move_up_click(self):
        """Handler for reordering (up) an element of the list property.
        """
        index = self.tableView.currentIndex().row()
        if index > 0:
            temp = self.value[index]
            del self.value[index]
            self.value.insert(index-1, temp)
            set_value_or_del_key(
                self.body,
                self._truth_fn(self.value),
                self.key,
                self.value
            )

            # refresh view model and emit state change
            self._refreshTableModel()
            self.valueChanged.emit()

            # update current index
            self.tableView.selectRow(index - 1)

    @pyqtSlot()
    def on_move_down_click(self):
        """Handler for reordering (down) an element of the list property.
        """
        index = self.tableView.currentIndex().row()
        if -1 < index < len(self.value)-1:
            temp = self.value[index]
            del self.value[index]
            self.value.insert(index+1, temp)
            set_value_or_del_key(
                self.body,
                self._truth_fn(self.value),
                self.key,
                self.value
            )

            # refresh view model and emit state change
            self._refreshTableModel()
            self.valueChanged.emit()

            # update current index
            self.tableView.selectRow(index + 1)

    @pyqtSlot()
    def on_doubleclick(self):
        """Handler for double-click event which opens the editor dialog.
        """
        # if dialog, show but if not accepted, return without adding value
        if self.editor_dialog_exec_fn:
            index = self.tableView.currentIndex().row()
            code, value = self.editor_dialog_exec_fn(self.value[index], parent=self)
            if code == QDialog.Accepted:
                # ...replace value and set
                self.value[index] = value
                set_value_or_del_key(
                    self.body,
                    self._truth_fn(self.value),
                    self.key,
                    self.value
                )
                # ...refresh view model and emit state change
                self._refreshTableModel()
                self.valueChanged.emit()
