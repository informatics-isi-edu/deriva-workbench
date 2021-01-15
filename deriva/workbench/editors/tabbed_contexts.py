"""Base widget for tabbed contexts editors, intended for internal use only.
"""
import logging
from typing import Callable
from PyQt5.QtWidgets import QWidget, QTabWidget, QFormLayout, QLabel, QComboBox, QPushButton, QVBoxLayout, QLineEdit, \
    QMessageBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal

logger = logging.getLogger(__name__)

__compact__ = "compact"
__compact_brief__ = "compact/brief"
__compact_brief_inline__ = "compact/brief/inline"
__compact_select__ = "compact/select"
__detailed__ = "detailed"
__entry__ = "entry"
__entry_create__ = "entry/create"
__entry_edit__ = "entry/edit"
__export__ = "export"
__filter__ = "filter"
__row_name__ = "row_name"
__row_name_compact__ = "row_name/compact"
__row_name_detailed__ = "row_name/detailed"
__star__ = "*"

all_contexts = frozenset([
    __compact__,
    __compact_brief__,
    __compact_brief_inline__,
    __compact_select__,
    __detailed__,
    __entry__,
    __entry_create__,
    __entry_edit__,
    __export__,
    __filter__,
    __row_name__,
    __row_name_compact__,
    __row_name_detailed__,
    __star__
])


class TabbedContextsWidget(QWidget):
    """Tabbed widget for managing annotation contexts.
    """

    createContextRequested = pyqtSignal(str, str)
    removeContextRequested = pyqtSignal(str)

    def __init__(self, allow_context_reference: bool = False, available_contexts: iter = all_contexts, parent: QWidget = None):
        """Initialize the widget.

        :param allow_context_reference: when adding a new context, allow context references
        :param available_contexts: known context names that may be used
        :param parent: the parent widget
        """
        super(TabbedContextsWidget, self).__init__(parent=parent)
        self._context_names: [str] = []
        self._available_contexts: {str} = set(available_contexts)

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

        # ...context name
        self._contextNameComboBox = QComboBox()
        self._contextNameComboBox.setPlaceholderText(self.tr('Enter an unused context name'))
        self._contextNameComboBox.setEditable(True)
        self._contextNameComboBox.currentIndexChanged.connect(self._on_contextName_textChanged)
        self._contextNameComboBox.editTextChanged.connect(self._on_contextName_textChanged)
        form.addRow(self.tr('Context Name'), self._contextNameComboBox)

        # ...reference existing
        self._referenceExistingComboBox = QComboBox()
        self._referenceExistingComboBox.setPlaceholderText(self.tr('Select to reference existing context (optional)'))
        if allow_context_reference:
            form.addRow(self.tr('Reference Existing'), self._referenceExistingComboBox)

        self._resetComboBoxes()

        # ...create button
        self._createButton = QPushButton('Add')
        self._createButton.setEnabled(False)
        self._createButton.clicked.connect(self._on_contextName_createEvent)
        form.addWidget(self._createButton)
        addContextTab.setAutoFillBackground(True)
        self._tabs.addTab(addContextTab, '<add>')

    @pyqtSlot()
    def _on_contextName_textChanged(self):
        """Handles index changes to contextName combo box.
        """
        if self._contextNameComboBox.currentText():
            self._createButton.setEnabled(True)
        else:
            self._createButton.setEnabled(False)

    @pyqtSlot()
    def _on_contextName_createEvent(self):
        """Handles create button clicked signals.
        """
        self.createContextRequested.emit(
            self._contextNameComboBox.currentText(),
            self._referenceExistingComboBox.currentText()
        )

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
        self._available_contexts -= {context_name}
        self._resetComboBoxes()
        self._tabs.insertTab(self._tabs.count()-1, context_widget, context_name)

    def removeContext(self, context_name: str) -> None:
        """Removes the context.
        """
        assert context_name in self._context_names, 'Unexpected context_name'
        try:
            index = self._context_names.index(context_name)
            del self._context_names[index]
            self._available_contexts |= {context_name}
            self._resetComboBoxes()
            self._tabs.removeTab(index)
        except ValueError:
            logger.error('Context "%s" not found' % context_name)

    def _resetComboBoxes(self):
        """Resets the state of the ComboBoxes.
        """
        self._contextNameComboBox.clear()
        self._contextNameComboBox.addItems(self._available_contexts)
        self._contextNameComboBox.model().sort(0)
        self._referenceExistingComboBox.clear()
        self._referenceExistingComboBox.addItems(self._context_names)
        self._referenceExistingComboBox.model().sort(0)


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