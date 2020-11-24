"""Editor package for the citation annotation.
"""
import logging
from PyQt5.QtWidgets import QWidget, QFormLayout, QTextEdit
from PyQt5.QtCore import pyqtSlot
from deriva.core import tag, ermrest_model as _erm
from .common import set_value_or_del_key, SubsetSelectionWidget, TemplateEngineWidget

logger = logging.getLogger(__name__)


__markdown_pattern_field_keys__ = [
    ('journal_pattern', 'Journal'),
    ('author_pattern', 'Author'),
    ('title_pattern', 'Title'),
    ('year_pattern', 'Year'),
    ('url_pattern', 'URL'),
    ('id_pattern', 'ID')
]


class CitationEditor(QWidget):
    """Citation annotation editor.
    """

    table: _erm.Table

    def __init__(self, table: _erm.Table, parent: QWidget = None):
        super(CitationEditor, self).__init__(parent=parent)
        self.body = table.annotations[tag.citation]

        # form
        form = QFormLayout(self)
        self.setLayout(form)
        self.setAutoFillBackground(True)

        # add pattern fields
        self._markdown_pattern_fields = {}
        for key, label in __markdown_pattern_field_keys__:
            mdField = QTextEdit(self.body.get(key, ''), parent=self)
            mdField.setPlaceholderText('Enter markdown pattern')
            mdField.textChanged.connect(self._on_value_changed)
            self._markdown_pattern_fields[key] = mdField
            form.addRow(label, mdField)

        # template engine
        form.addRow('Template Engine', TemplateEngineWidget(self.body, parent=parent))

        # wait for field
        self.waitForWidget = SubsetSelectionWidget(
            self.body.get('wait_for', []),
            table.annotations.get(tag.source_definitions, {}).get('sources', {}).keys(),
            parent=self)
        self.waitForWidget.valueChanged.connect(self._on_value_changed)
        form.addRow('Wait For', self.waitForWidget)

    @pyqtSlot()
    def _on_value_changed(self):
        """Handles changes to the fields (except template engine widget).
        """
        # update markdown fields
        for key, _ in __markdown_pattern_field_keys__:
            text = self._markdown_pattern_fields[key].toPlainText()
            set_value_or_del_key(
                self.body,
                bool(text),
                key,
                text
            )

        # update wait for field
        wait_for = self.waitForWidget.selected_values
        set_value_or_del_key(
            self.body,
            bool(wait_for),
            'wait_for',
            wait_for
        )
