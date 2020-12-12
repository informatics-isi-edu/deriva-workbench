"""Widgets for editing the 'key-display' annotation.
"""
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from deriva.core import tag, ermrest_model as _erm
from .common import raise_on_invalid, MultipleChoicePropertyWidget
from .markdown_patterns import MarkdownPatternForm
from .sortkeys import SortKeysWidget
from .tabbed_contexts import EasyTabbedContextsWidget


class KeyDisplayEditor(EasyTabbedContextsWidget):
    """Editor for the key-display contexts.
    """

    def __init__(self, key: _erm.Key, parent: QWidget = None):
        """Initialize widget.

        :param key: an ermrest key instance
        :param parent: the parent widget
        """
        raise_on_invalid(key, _erm.Key, tag.key_display)
        super(KeyDisplayEditor, self).__init__(
            tag.key_display,
            key.annotations,
            create_context_value=lambda context: {},
            create_context_widget_fn=lambda context, parent=None: _KeyDisplayContextEditor(key, key.annotations[tag.key_display][context], parent=parent),
            purge_on_empty=False,
            allow_context_reference=True,
            parent=parent)


class _KeyDisplayContextEditor(MarkdownPatternForm):
    """Editor for a key-display annotation (single entry).
    """

    __column_order__ = 'column_order'

    def __init__(self, key: _erm.Key, body: dict, parent: QWidget = None):
        """Initialize the widget.

        :param key: the ermrest key instance
        :param body: the annotation body for the given context
        :param parent: the parent widget
        """
        super(_KeyDisplayContextEditor, self).__init__(
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
