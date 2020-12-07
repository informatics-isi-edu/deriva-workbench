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
        """Internal table model."""

        def __init__(self, data: list, headers_fn: Callable = None, row_fn: Callable = None):
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
                self.rows = [str(entry) for entry in data]

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
            headers_fn: Callable = None,
            row_fn: Callable = None,
            resize_mode: QHeaderView.ResizeMode = QHeaderView.Stretch,
            truth_fn: Callable = lambda v: v is not None,
            parent: QWidget = None
    ):
        """Initialize the widget.

        If the `editor_widget` is a subclass of QDialog the dialog will be shown on add or edit events. If it is not a
        QDialog, the widget will be displayed inline and only used for add events, while edit events will not be
        supported. The editor should have a `value` property getter and also a setter, the latter only if it is a
        QDialog subclass.

        :param key: annotation key
        :param body: annotation body (container)
        :param editor_widget: the widget to be used for creating or editing elements of the list property
        :param headers_fn: a function that takes the property as input and returns a list of text for the table header
        :param row_fn: a function that takes an item from the property and returns a flattened tuple for the row value
        :param resize_mode: the resize mode applied to the table view
        :param truth_fn: function applied to value to determine whether it should be set or dropped from body
        :param parent: parent widget
        """
        super(CommonTableWidget, self).__init__(parent=parent)
        self.key, self.body = key, body
        self.headers_fn, self.row_fn = headers_fn, row_fn
        self.resize_mode = resize_mode
        self.editor_widget = editor_widget
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
        addSource = QPushButton('+', parent=controls)
        addSource.clicked.connect(self.on_add_click)
        hlayout.addWidget(addSource)
        # ...remove column button
        removeSource = QPushButton('-', parent=controls)
        removeSource.clicked.connect(self.on_remove_click)
        hlayout.addWidget(removeSource)
        # ...duplicate column button
        duplicateSource = QPushButton('copy', parent=controls)
        duplicateSource.clicked.connect(self.on_duplicate_click)
        hlayout.addWidget(duplicateSource)
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
        if isinstance(self.editor_widget, QWidget) and not isinstance(self.editor_widget, QDialog):
            layout.addWidget(self.editor_widget)
        layout.addWidget(controls)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

    @pyqtSlot()
    def on_add_click(self):
        """Handler for adding an element.
        """
        # if dialog, show but if not accepted, return without adding value
        if isinstance(self.editor_widget, QDialog):
            self.editor_widget.value = None
            code = self.editor_widget.exec_()
            if code != QDialog.Accepted:
                return

        # add value and set
        self.value.append(deepcopy(self.editor_widget.value))
        set_value_or_del_key(
            self.body,
            self._truth_fn(self.value),
            self.key,
            self.value
        )

        # update view model
        self.tableView.setModel(
            self._InternalTableModel(self.value, headers_fn=self.headers_fn, row_fn=self.row_fn)
        )
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

            # update view model
            self.tableView.setModel(
                self._InternalTableModel(self.value, headers_fn=self.headers_fn, row_fn=self.row_fn)
            )
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

            # update view model
            self.tableView.setModel(
                self._InternalTableModel(self.value, headers_fn=self.headers_fn, row_fn=self.row_fn)
            )
            index = index if index < len(self.value) else index - 1
            self.tableView.selectRow(index)
            self.valueChanged.emit()

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

            # update view model
            self.tableView.setModel(
                self._InternalTableModel(self.value, headers_fn=self.headers_fn, row_fn=self.row_fn)
            )
            self.tableView.selectRow(index - 1)
            self.valueChanged.emit()

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

            # update view model
            self.tableView.setModel(
                CommonTableWidget._InternalTableModel(self.value)
            )
            self.tableView.selectRow(index + 1)
            self.valueChanged.emit()

    @pyqtSlot()
    def on_doubleclick(self):
        """Handler for double-click event on a visible-source which opens the editor dialog.
        """
        # if dialog, show but if not accepted, return without adding value
        if isinstance(self.editor_widget, QDialog):
            index = self.tableView.currentIndex().row()
            # ...update editor property value
            self.editor_widget.value = deepcopy(self.value[index])
            code = self.editor_widget.exec_()
            if code == QDialog.Accepted:
                # ...replace value and set
                self.value[index] = self.editor_widget.value
                set_value_or_del_key(
                    self.body,
                    self._truth_fn(self.value),
                    self.key,
                    self.value
                )
                # ...update view model
                self.tableView.setModel(
                    self._InternalTableModel(self.value, headers_fn=self.headers_fn, row_fn=self.row_fn)
                )
                self.valueChanged.emit()
