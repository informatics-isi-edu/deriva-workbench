"""Widgets for editing the 'table-display' annotation.
"""
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QGroupBox, QLabel
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QIntValidator
from deriva.core import tag, ermrest_model as _erm
from .common import SimpleTextPropertyWidget, SimpleBooleanPropertyWidget
from .markdown_patterns import MarkdownPatternForm
from .sortkeys import SortKeysWidget
from .tabbed_contexts import TabbedContextsWidget


class TableDisplayContextsEditor(TabbedContextsWidget):
    """Editor for the table-display contexts.
    """

    table: _erm.Table
    body: dict

    def __init__(self, table: _erm.Table, parent: QWidget = None):
        """Initialize widget.
        """
        super(TableDisplayContextsEditor, self).__init__(parent=parent)
        assert isinstance(table, _erm.Table)
        self.table = table
        self.body = self.table.annotations[tag.table_display]
        self.createContextRequested.connect(self._on_creatContext)
        self.removeContextRequested.connect(self._on_removeContext)

        # create tabs for each context
        for context in self.body:
            contents = self.body[context]
            tab = TableDisplayEditor(self.table, context, contents, parent=self)
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
        contextEditor = TableDisplayEditor(self.table, context, contents, parent=self)
        self.addContext(contextEditor, context)

    @pyqtSlot(str)
    def _on_removeContext(self, context):
        """Handles the 'removeContextRequested' signal.
        """
        del self.body[context]
        self.removeContext(context)


__markdown_pattern_field_keys__ = [
    ('page_markdown_pattern', 'Page'),
    ('row_markdown_pattern', 'Row'),
    ('separator_pattern', 'Separator'),
    ('prefix_pattern', 'Prefix'),
    ('suffix_pattern', 'Suffix')
]


class TableDisplayEditor(QWidget):
    """Editor for a table-display annotation (single entry).
    """

    table: _erm.Table
    context_name: str
    body: dict

    def __init__(self, table: _erm.Table, context_name: str, body: dict, parent: QWidget = None):
        super(TableDisplayEditor, self).__init__(parent=parent)
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
