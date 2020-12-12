"""Widgets for editing the 'column-display' annotation.
"""
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from deriva.core import tag, ermrest_model as _erm
from .common import raise_on_invalid, MultipleChoicePropertyWidget, SimpleNestedPropertyManager, \
    SimpleTextPropertyWidget
from .markdown_patterns import MarkdownPatternForm
from .sortkeys import SortKeysWidget
from .tabbed_contexts import EasyTabbedContextsWidget


class ColumnDisplayEditor(EasyTabbedContextsWidget):
    """Editor for the column-display contexts.
    """

    def __init__(self, column: _erm.Column, parent: QWidget = None):
        """Initialize the widget.

        :param column: an ermrest column instance
        :param parent: the parent widget
        """
        raise_on_invalid(column, _erm.Column, tag.column_display)
        super(ColumnDisplayEditor, self).__init__(
            tag.column_display,
            column.annotations,
            create_context_value=lambda context: {},
            create_context_widget_fn=lambda context, parent=None: _ColumnDisplayContextEditor(column, column.annotations[tag.column_display][context], parent=parent),
            purge_on_empty=False,
            allow_context_reference=True,
            parent=parent)


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
