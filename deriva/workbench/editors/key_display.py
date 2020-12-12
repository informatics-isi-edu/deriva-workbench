"""Widgets for editing the 'key-display' annotation.
"""
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from PyQt5.QtCore import pyqtSlot
from deriva.core import tag, ermrest_model as _erm
from .common import raise_on_invalid, MultipleChoicePropertyWidget
from .markdown_patterns import MarkdownPatternForm
from .sortkeys import SortKeysWidget
from .tabbed_contexts import TabbedContextsWidget


class KeyDisplayEditor(TabbedContextsWidget):
    """Editor for the key-display contexts.
    """

    key: _erm.Key
    body: dict

    def __init__(self, key: _erm.Key, parent: QWidget = None):
        """Initialize widget.

        :param key: an ermrest key instance
        :param parent: the parent widget
        """
        raise_on_invalid(key, _erm.Key, tag.key_display)
        super(KeyDisplayEditor, self).__init__(parent=parent)
        self.key = key
        self.body = self.key.annotations[tag.key_display]
        self.createContextRequested.connect(self._on_creatContext)
        self.removeContextRequested.connect(self._on_removeContext)

        # create tabs for each context
        for context in self.body:
            contents = self.body[context]
            tab = KeyDisplayContextEditor(self.key, contents, parent=self)
            self.addContext(tab, context)

        # set first context active
        if self.body:
            self.setActiveContext(list(self.body.keys())[0])

    @pyqtSlot(str)
    def _on_creatContext(self, context):
        """Handles the 'createContextRequested' signal.
        """
        # create new context entry
        self.body[context] = contents = {}

        # create and add new context editor
        contextEditor = KeyDisplayContextEditor(self.key, contents, parent=self)
        self.addContext(contextEditor, context)

    @pyqtSlot(str)
    def _on_removeContext(self, context):
        """Handles the 'removeContextRequested' signal.
        """
        del self.body[context]
        self.removeContext(context)


class KeyDisplayContextEditor(MarkdownPatternForm):
    """Editor for a key-display annotation (single entry).
    """

    __column_order__ = 'column_order'

    def __init__(self, key: _erm.Key, body: dict, parent: QWidget = None):
        """Initialize the widget.

        :param key: the ermrest key instance
        :param body: the annotation body for the given context
        :param parent: the parent widget
        """
        super(KeyDisplayContextEditor, self).__init__(
            [('markdown_pattern', 'Markdown Pattern')],
            body,
            include_template_engine=True,
            parent=parent
        )

        # ...column order widget
        self.form.addRow(
            'Column Order',
            MultipleChoicePropertyWidget(
                self.__column_order__,
                body,
                {
                    'Accept the default sorting behavior': None,
                    'Sorting by this key should not be offered': False
                },
                other_key='Sort by the following columns in the key',
                other_widget=SortKeysWidget(
                    self.__column_order__,
                    body,
                    [c.name for c in key.columns],
                    parent=self
                ),
                layout=QVBoxLayout(),
                parent=self
            )
        )
