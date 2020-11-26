"""Editor package for the citation annotation.
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSlot
from deriva.core import tag, ermrest_model as _erm
from .common import set_value_or_del_key, SubsetSelectionWidget, TemplateEngineWidget
from .markdown_patterns import MarkdownPatternForm


__markdown_pattern_field_keys__ = [
    ('journal_pattern', 'Journal'),
    ('author_pattern', 'Author'),
    ('title_pattern', 'Title'),
    ('year_pattern', 'Year'),
    ('url_pattern', 'URL'),
    ('id_pattern', 'ID')
]


class CitationEditor(MarkdownPatternForm):
    """Citation annotation editor.
    """

    table: _erm.Table

    def __init__(self, table: _erm.Table, parent: QWidget = None):
        self.body = table.annotations[tag.citation]
        super(CitationEditor, self).__init__(
            __markdown_pattern_field_keys__,
            self.body,
            include_template_engine=True,
            parent=parent
        )

        # wait for field
        self.waitForWidget = SubsetSelectionWidget(
            self.body.get('wait_for', []),
            table.annotations.get(tag.source_definitions, {}).get('sources', {}).keys(),
            parent=self)
        self.waitForWidget.valueChanged.connect(self._on_wait_for_changed)
        self.form.addRow('Wait For', self.waitForWidget)

    @pyqtSlot()
    def _on_wait_for_changed(self):
        """Handles changes to the wait_for field.
        """
        wait_for = self.waitForWidget.selected_values
        set_value_or_del_key(
            self.body,
            bool(wait_for),
            'wait_for',
            wait_for
        )
