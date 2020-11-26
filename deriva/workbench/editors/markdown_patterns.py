"""Markdown Pattern Form Widget.
"""
from PyQt5.QtWidgets import QWidget, QFormLayout, QTextEdit
from PyQt5.QtCore import pyqtSlot
from .common import set_value_or_del_key, TemplateEngineWidget


class MarkdownPatternForm(QWidget):
    """Markdown Pattern Form Widget.
    """

    def __init__(self, field_keys: [(str, str)], body: dict, include_template_engine: bool = False, parent: QWidget = None):
        """Initialize the form.

        :param field_keys: list of (key, label) tuples where key is a key in the annotation body and label is a user friendly lable
        :param body: the body of the annotation
        :param include_template_engine: indicates whether to include the 'template_engine' handling in the form
        :param parent: parent widget
        """
        super(MarkdownPatternForm, self).__init__(parent=parent)
        self._field_keys, self._body = field_keys, body

        # form
        self.form = QFormLayout(self)
        self.setLayout(self.form)
        self.setAutoFillBackground(True)

        # add pattern fields
        self._markdown_pattern_fields = {}
        for key, label in self._field_keys:
            mdField = QTextEdit(self._body.get(key, ''), parent=self)
            mdField.setPlaceholderText('Enter markdown pattern')
            mdField.textChanged.connect(self._on_value_changed)
            self._markdown_pattern_fields[key] = mdField
            self.form.addRow(label, mdField)

        # template engine
        if include_template_engine:
            self.form.addRow('Template Engine', TemplateEngineWidget(self._body, parent=parent))

    @pyqtSlot()
    def _on_value_changed(self):
        """Handles changes to the markdown fields.
        """
        for key, _ in self._field_keys:
            text = self._markdown_pattern_fields[key].toPlainText()
            set_value_or_del_key(
                self._body,
                bool(text),
                key,
                text
            )
