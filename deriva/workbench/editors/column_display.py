"""Widgets for editing the 'column-display' annotation.
"""
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QGroupBox
from PyQt5.QtCore import pyqtSlot
from deriva.core import tag, ermrest_model as _erm
from .common import raise_on_invalid, MultipleChoicePropertyWidget, SimpleNestedPropertyManager, \
    SimpleTextPropertyWidget
from .markdown_patterns import MarkdownPatternForm
from .sortkeys import SortKeysWidget
from .tabbed_contexts import TabbedContextsWidget


class ColumnDisplayEditor(TabbedContextsWidget):
    """Editor for the column-display contexts.
    """

    column: _erm.Column
    body: dict

    def __init__(self, column: _erm.Column, parent: QWidget = None):
        """Initialize the widget.

        :param column: an ermrest column instance
        :param parent: the parent widget
        """
        raise_on_invalid(column, _erm.Column, tag.column_display)
        super(ColumnDisplayEditor, self).__init__(parent=parent)
        self.column = column
        self.body = self.column.annotations[tag.column_display]
        self.createContextRequested.connect(self._on_creatContext)
        self.removeContextRequested.connect(self._on_removeContext)

        # create tabs for each context
        for context in self.body:
            contents = self.body[context]
            tab = _ColumnDisplayContextEditor(self.column, contents, parent=self)
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
        contextEditor = _ColumnDisplayContextEditor(self.column, contents, parent=self)
        self.addContext(contextEditor, context)

    @pyqtSlot(str)
    def _on_removeContext(self, context):
        """Handles the 'removeContextRequested' signal.
        """
        del self.body[context]
        self.removeContext(context)


class _ColumnDisplayContextEditor(MarkdownPatternForm):
    """Editor for a column-display annotation (single entry).
    """

    __column_order__ = 'column_order'

    def __init__(self, column: _erm.Column, body: dict, parent: QWidget = None):
        """Initialize the widget.

        :param column: the ermrest column instance
        :param body: the annotation body for the given context
        :param parent: the parent widget
        """
        super(_ColumnDisplayContextEditor, self).__init__(
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
                    'Sorting by this column should not be offered': False
                },
                other_key='Sort by the following columns',
                other_widget=SortKeysWidget(
                    self.__column_order__,
                    body,
                    [c.name for c in column.table.columns],
                    parent=self
                ),
                layout=QVBoxLayout(),
                parent=self
            )
        )

        # pre_format
        pre_format = SimpleNestedPropertyManager('pre_format', body, parent=self)

        # ...format
        format = SimpleTextPropertyWidget(
            'format',
            pre_format.value,
            'Enter a POSIX standard format string',
            parent=self
        )
        format.valueChanged.connect(pre_format.onValueChanged)
        self.form.addRow('Format', format)

        # ...bool_true_value
        bool_true_value = SimpleTextPropertyWidget(
            'bool_true_value',
            pre_format.value,
            'Alternate display text for "true" value',
            parent=self
        )
        bool_true_value.valueChanged.connect(pre_format.onValueChanged)
        self.form.addRow('Alt. True', bool_true_value)

        # ...bool_false_value
        bool_false_value = SimpleTextPropertyWidget(
            'bool_false_value',
            pre_format.value,
            'Alternate display text for "false" value',
            parent=self
        )
        bool_false_value.valueChanged.connect(pre_format.onValueChanged)
        self.form.addRow('Alt. False', bool_false_value)
