"""Common components for managing various forms of sort keys in annotations.
"""
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant, pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView, QHBoxLayout, QComboBox, QCheckBox, \
    QPushButton


class SortKeysWidget(QWidget):
    """Sort keys editor widget.
    """

    class _TableModel(QAbstractTableModel):
        """Internal table model for a context.
        """

        def __init__(self, data):
            super(SortKeysWidget._TableModel, self).__init__()
            self.headers = ['Column', 'Descending']
            self.rows = data

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

    def __init__(self, key: str, annotations: dict, columns: list, parent: QWidget = None):
        """Initializes the row order widget.

        :param key: the key for the sortkeys annotation (e.g., 'row_order', 'column_order')
        :param annotations: an object that may contain a `sortkeys` annotation.
        :param columns: a list of columns names
        :param parent: the parent widget
        """
        super(SortKeysWidget, self).__init__(parent=parent)
        self.key = key
        self.annotations = annotations
        self.sortkeys = self.annotations.get(self.key, [])

        # layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        # table view
        self._tableView = QTableView(parent=parent)
        self._tableView.setWordWrap(True)
        self._tableView.setAlternatingRowColors(True)
        self._tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self._tableView)

        # refresh table model
        self._refresh()

        # sortkey
        sortkey = QWidget(parent=self)
        sortkey.setLayout(QHBoxLayout(sortkey))
        sortkey.layout().setContentsMargins(2, 0 , 2, 0)
        layout.addWidget(sortkey)

        # ...sortkey column
        self._sortkeyColumn = QComboBox(parent=self)
        self._sortkeyColumn.addItems(columns)
        sortkey.layout().addWidget(self._sortkeyColumn)

        # ...sortkey descending
        self._sortkeyDescending = QCheckBox('descending', parent=self)
        sortkey.layout().addWidget(self._sortkeyDescending)

        # controls
        controls = QWidget(parent=self)
        controls.setLayout(QHBoxLayout(controls))
        controls.layout().setContentsMargins(2, 0, 2, 0)
        layout.addWidget(controls)

        # ...push
        self._pushButton = QPushButton('push', parent=self)
        self._pushButton.clicked.connect(self._on_pushButton_clicked)
        controls.layout().addWidget(self._pushButton)
        # ...pop
        self._popButton = QPushButton('pop', parent=self)
        self._popButton.clicked.connect(self._on_popButton_clicked)
        controls.layout().addWidget(self._popButton)

    def _refresh(self):
        """Refreshes the UI.
        """
        self._tableView.setModel(SortKeysWidget._TableModel([
            (
                sortkey if isinstance(sortkey, str) else sortkey['column'],
                bool(sortkey.get('descending', False)) if isinstance(sortkey, dict) else False
            )
            for sortkey in self.sortkeys
        ]))

    @pyqtSlot()
    def _on_pushButton_clicked(self):
        """Handle push event.
        """
        sortkey = {
            'column': self._sortkeyColumn.currentText(),
        }
        if self._sortkeyDescending.isChecked():
            sortkey['descending'] = True

        # update annotation
        self.sortkeys.append(sortkey)
        if self.key not in self.annotations:
            self.annotations[self.key] = self.sortkeys

        # refresh ui
        self._refresh()

    @pyqtSlot()
    def _on_popButton_clicked(self):
        """Handles pop event.
        """
        if not self.sortkeys:
            return

        # update annotation
        del self.sortkeys[-1]
        if not self.sortkeys and self.key in self.annotations:
            del self.annotations[self.key]

        # refresh ui
        self._refresh()