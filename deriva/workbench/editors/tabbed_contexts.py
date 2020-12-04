"""Base widget for tabbed contexts editors, intended for internal use only.
"""
import logging
from typing import Any, Callable

from PyQt5.QtWidgets import QWidget, QTabWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QLineEdit, QMessageBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal

logger = logging.getLogger(__name__)


class TabbedContextsWidget(QWidget):
    """Tabbed widget for managing annotation contexts.
    """

    createContextRequested = pyqtSignal(str)
    removeContextRequested = pyqtSignal(str)

    def __init__(self, parent: QWidget = None):
        super(TabbedContextsWidget, self).__init__(parent=parent)
        self._context_names: [str] = []

        # layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        # tabs
        self._tabs = QTabWidget(parent=self)
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self._on_tabCloseRequested)
        layout.addWidget(self._tabs)

        # initialize the 'create' context tab
        createTab = QWidget(parent=self)
        createTab.setLayout(QHBoxLayout())
        # ...label
        createTab.layout().addWidget(QLabel('Context Name:'))
        # ...line edit
        self._contextNameLineEdit = QLineEdit()
        self._contextNameLineEdit.setPlaceholderText('Enter a unique context name')
        self._contextNameLineEdit.textChanged.connect(self._on_contextName_textChanged)
        self._contextNameLineEdit.returnPressed.connect(self._on_contextName_createEvent)
        createTab.layout().addWidget(self._contextNameLineEdit)
        # ...create button
        self._createButton = QPushButton('Add')
        self._createButton.setEnabled(False)
        self._createButton.clicked.connect(self._on_contextName_createEvent)
        createTab.layout().addWidget(self._createButton)
        createTab.setAutoFillBackground(True)
        self._tabs.addTab(createTab, '<add>')

    @pyqtSlot()
    def _on_contextName_textChanged(self):
        """Handles context name text changed signals.
        """
        context = self._contextNameLineEdit.text()
        if context and context not in self._context_names:
            self._createButton.setEnabled(True)
        else:
            self._createButton.setEnabled(False)

    @pyqtSlot()
    def _on_contextName_createEvent(self):
        """Handles create button clicked signals.
        """
        self.createContextRequested.emit(
            self._contextNameLineEdit.text()
        )
        self._contextNameLineEdit.setText('')

    @pyqtSlot(int)
    def _on_tabCloseRequested(self, index: int):
        """Handles tab close requested signals.
        """
        if index == len(self._context_names):
            QMessageBox.information(
                self,
                'Message',
                'This tab cannot be removed.'
            )
            return

        ret = QMessageBox.question(
            self,
            'Confirm Context Removal',
            'Are you sure you want to remove the "%s" context from the annotations?' % self._context_names[index]
        )
        if ret == QMessageBox.Yes:
            self.removeContextRequested.emit(self._context_names[index])

    def count(self) -> int:
        """Count of contexts.
        """
        return len(self._context_names)

    def setActiveContext(self, context_name: str) -> None:
        """Sets the active context tab.
        """
        try:
            index = self._context_names.index(context_name)
            self._tabs.setCurrentIndex(index)
        except ValueError:
            logger.error('Context "%s" not found' % context_name)

    def setActiveContextByIndex(self, index: int) -> None:
        """Sets the active context tab by simple numeric index.
        """
        self._tabs.setCurrentIndex(index)

    def addContext(self, context_widget: QWidget, context_name: str) -> None:
        """Adds a context widget and label.

        :param context_widget: widget for the context
        :param context_name: text name of the context
        """
        if context_name in self._context_names:
            logger.warning('"%s" already exists in tabbed contexts' % context_name)
        self._context_names.append(context_name)
        self._tabs.insertTab(self._tabs.count()-1, context_widget, context_name)

    def removeContext(self, context: str) -> None:
        """Removes the context.
        """
        try:
            index = self._context_names.index(context)
            del self._context_names[index]
            self._tabs.removeTab(index)
        except ValueError:
            logger.error('Context "%s" not found' % context)


class EasyTabbedContextsWidget(TabbedContextsWidget):
    """Easier tabbed contexts widget.

    This widget is useful for contextualized properties of annotations. When all contexts are removed it will purge the
    property from the given annotation body.

    The 'valueChanged' signal only indicates that a context has been added or removed. It does not roll up changes made
    by the context widget which should be established in your own 'create_context_widget_fn' function.
    """

    valueChanged = pyqtSignal()

    def __init__(self,
                 key: str,
                 body: dict,
                 default_context_value: Any,
                 create_context_widget_fn: Callable,
                 parent: QWidget = None):
        """Initialize the widget.

        :param key: the key for the annotation property in the body
        :param body: the body of the annotation property
        :param default_context_value: the default value for new contexts
        :param create_context_widget_fn: function to create a new widget to manage a context
        :param parent: this widget's parent
        """
        super(EasyTabbedContextsWidget, self).__init__(parent=parent)
        self.key, self.body = key, body
        self.default_context_value = default_context_value
        self.create_context_widget_fn = create_context_widget_fn

        # connect the create/remove slots
        self.createContextRequested.connect(self._on_createContextRequested)
        self.removeContextRequested.connect(self._on_removeContextRequested)

        # create widgets for contexts
        for context in self.body.get(key, {}):
            self.addContext(
                self.create_context_widget_fn(context),
                context
            )

        # set first context active
        if self._tabs.count():
            self.setActiveContextByIndex(0)

    @pyqtSlot(str)
    def _on_createContextRequested(self, context):
        """Handles the 'createContextRequested' signal.
        """
        # create new context entry
        self.body[self.key] = self.body.get(self.key, {})
        self.body[self.key][context] = self.default_context_value

        # create and add new context editor
        self.addContext(
            self.create_context_widget_fn(context),
            context
        )
        # emit
        self.valueChanged.emit()

    @pyqtSlot(str)
    def _on_removeContextRequested(self, context):
        """Handles the 'removeContextRequested' signal.
        """
        del self.body[self.key][context]
        if not self.body[self.key]:
            del self.body[self.key]
        self.removeContext(context)
        # emit
        self.valueChanged.emit()