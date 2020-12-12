"""Widgets for editing the 'table-display' annotation.
"""
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QGroupBox, QLabel
from PyQt5.QtGui import QIntValidator
from deriva.core import tag, ermrest_model as _erm
from .common import SimpleTextPropertyWidget, SimpleBooleanPropertyWidget, raise_on_invalid
from .markdown_patterns import MarkdownPatternForm
from .sortkeys import SortKeysWidget
from .tabbed_contexts import EasyTabbedContextsWidget


class TableDisplayEditor(EasyTabbedContextsWidget):
    """Editor for the table-display contexts.
    """

    def __init__(self, table: _erm.Table, parent: QWidget = None):
        """Initialize widget.

        :param table: an ermrest table instance
        :param parent: the parent widget
        """
        raise_on_invalid(table, _erm.Table, tag.table_display)
        super(TableDisplayEditor, self).__init__(
            tag.table_display,
            table.annotations,
            create_context_value=lambda context: {},
            create_context_widget_fn=lambda context, parent = None: _TableDisplayContextEditor(table, context, table.annotations[tag.table_display][context], parent=parent),
            purge_on_empty=False,
            allow_context_reference=True,
            parent=parent
        )


__markdown_pattern_field_keys__ = [
    ('page_markdown_pattern', 'Page'),
    ('row_markdown_pattern', 'Row'),
    ('separator_pattern', 'Separator'),
    ('prefix_pattern', 'Prefix'),
    ('suffix_pattern', 'Suffix')
]


class _TableDisplayContextEditor(QWidget):
    """Editor for a table-display annotation (single entry).
    """

    table: _erm.Table
    context_name: str
    body: dict

    def __init__(self, table: _erm.Table, context_name: str, body: dict, parent: QWidget = None):
        super(_TableDisplayContextEditor, self).__init__(parent=parent)
        self.table, self.context_name, self.body = table, context_name, body

        # layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        # sortkeys
        rowOrderGroup = QGroupBox('Row Order', parent=self)
        rowOrderGroup.setLayout(QVBoxLayout(rowOrderGroup))
        rowOrderGroup.layout().setContentsMargins(0, 0, 0, 0)
        rowOrderGroup.layout().addWidget(
            SortKeysWidget('row_order', self.body, [c.name for c in self.table.columns], parent=rowOrderGroup))
        layout.addWidget(rowOrderGroup)

        # markdown patterns
        mdGroup = QGroupBox('Markdown Patterns', parent=self)
        mdGroup.setLayout(QVBoxLayout(mdGroup))
        mdGroup.layout().setContentsMargins(0, 0, 0, 0)
        mdGroup.layout().addWidget(MarkdownPatternForm(__markdown_pattern_field_keys__,
                                                       self.body,
                                                       include_template_engine=True,
                                                       parent=mdGroup))
        layout.addWidget(mdGroup)

        # additional options
        optGroup = QGroupBox('Additional Options', parent=self)
        optGroup.setLayout(QHBoxLayout(optGroup))
        layout.addWidget(optGroup)
        # ...page size
        optGroup.layout().addWidget(QLabel('Page Size:'))
        optGroup.layout().addWidget(SimpleTextPropertyWidget(
            'page_size', self.body, placeholder='Enter integer', validator=QIntValidator(), parent=optGroup
        ))
        # ...collapse toc
        optGroup.layout().addWidget(SimpleBooleanPropertyWidget(
            'Collapse TOC Panel', 'collapse_toc_panel', self.body, parent=optGroup
        ))
        # ...hide column headers
        optGroup.layout().addWidget(SimpleBooleanPropertyWidget(
            'Hide Column Headers', 'hide_column_headers', self.body, parent=optGroup
        ))
