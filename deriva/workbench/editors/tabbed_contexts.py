"""Base widget for tabbed contexts editors, intended for internal use only.
"""
import logging
from typing import Callable
from PyQt5.QtWidgets import QWidget, QTabWidget, QFormLayout, QLabel, QComboBox, QPushButton, QVBoxLayout, QLineEdit, \
    QMessageBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal

logger = logging.getLogger(__name__)


class TabbedContextsWidget(QWidget):
    """Tabbed widget for managing annotation contexts.
    """

    createContextRequested = pyqtSignal(str, str)
    removeContextRequested = pyqtSignal(str)

    def __init__(self, allow_context_reference: bool = False, parent: QWidget = None):
        """Initialize the widget.

        :param allow_context_reference: when adding a new context, allow context references
        :param parent: the parent widget
        """
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

        # initialize the 'add' context tab
        addContextTab = QWidget(parent=self)
        form = QFormLayout(addContextTab)
        addContextTab.setLayout(form)

        # ...line edit
        self._contextNameLineEdit = QLineEdit(parent=addContextTab)
        self._contextNameLineEdit.setPlaceholderText('Enter a unique context name')
        self._contextNameLineEdit.textChanged.connect(self._on_contextName_textChanged)
        self._contextNameLineEdit.returnPressed.connect(self._on_contextName_createEvent)
        form.addRow(self.tr('Context Name'), self._contextNameLineEdit)

        # ...reference existing
        self._referenceExistingComboBox = QComboBox()
        self._referenceExistingComboBox.setPlaceholderText(self.tr('Select an existing context (optional)'))
        self._referenceExistingComboBox.addItems(self._context_names)
        if allow_context_reference:
            form.addRow(self.tr('Reference Existing'), self._referenceExistingComboBox)

        # ...create button
        self._createButton = QPushButton('Add')
        self._createButton.setEnabled(False)
        self._createButton.clicked.connect(self._on_contextName_createEvent)
        addContextTab.layout().addWidget(self._createButton)
        addContextTab.setAutoFillBackground(True)
        self._tabs.addTab(addContextTab, '<add>')

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
            self._contextNameLineEdit.text(),
            self._referenceExistingComboBox.currentText()
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
        self._referenceExistingComboBox.clear()
        self._referenceExistingComboBox.addItems(self._context_names)
        self._tabs.insertTab(self._tabs.count()-1, context_widget, context_name)

    def removeContext(self, context: str) -> None:
        """Removes the context.
        """
        try:
            index = self._context_names.index(context)
            del self._context_names[index]
            self._referenceExistingComboBox.clear()
            self._referenceExistingComboBox.addItems(self._context_names)
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
                 create_context_value: Callable,
                 create_context_widget_fn: Callable,
                 purge_on_empty: bool = True,
                 allow_context_reference: bool = False,
                 parent: QWidget = None):
        """Initialize the widget.

        :param key: the key for the annotation property in the body
        :param body: the body of the annotation property
        :param create_context_value: function to create an initial value for new contexts; it must accept a context
                name string, and it may return Any type of value.
        :param create_context_widget_fn: function to create an editor widget to manage a context; it must accept a
                context name string and an optional parent object, and it may return an instance of QWidget.
        :param purge_on_empty: if all contexts are removed, purge the 'key' from the 'body'
        :param allow_context_reference: when adding a new context, allow context references
        :param parent: this widget's parent
        """
        super(EasyTabbedContextsWidget, self).__init__(allow_context_reference=allow_context_reference, parent=parent)
        self.key, self.body = key, body
        self.create_context_value = create_context_value
        self.create_context_widget_fn = create_context_widget_fn
        self.purge_on_empty = purge_on_empty

        # connect the create/remove slots
        self.createContextRequested.connect(self._on_createContextRequested)
        self.removeContextRequested.connect(self._on_removeContextRequested)

        # create widgets for contexts
        for context, value in self.body.get(key, {}).items():
            self.addContext(
                self._referenceWidget(value) if allow_context_reference and isinstance(value, str) else self.create_context_widget_fn(context, parent=self),
                context
            )

        # set first context active
        if self._tabs.count():
            self.setActiveContextByIndex(0)

    def _referenceWidget(self, context_name):
        """Returns the widget to represent a context that references another context.
        """
        widget = QWidget(parent=self)
        widget.setLayout(QFormLayout(widget))
        widget.layout().addWidget(QLabel(self.tr('This context references: ') + context_name, parent=self))
        return widget

    @pyqtSlot(str, str)
    def _on_createContextRequested(self, context, reference):
        """Handles the 'createContextRequested' signal.
        """
        self.body[self.key] = self.body.get(self.key, {})
        self.body[self.key][context] = reference if reference else self.create_context_value(context)
        self.addContext(
            self._referenceWidget(reference) if reference else self.create_context_widget_fn(context, parent=self),
            context
        )
        self.valueChanged.emit()

    @pyqtSlot(str)
    def _on_removeContextRequested(self, context):
        """Handles the 'removeContextRequested' signal.
        """
        del self.body[self.key][context]
        if self.purge_on_empty and not self.body[self.key]:
            del self.body[self.key]
        self.removeContext(context)
        self.valueChanged.emit()