"""Schema editor widget that launches resource-specific editors.
"""
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget, QPlainTextEdit
from deriva.core import tag
from .editors import JSONEditor, AnnotationEditor, VisibleSourcesEditor, SourceDefinitionsEditor, CitationEditor


class SchemaEditor(QWidget):
    """Schema editor widget.

    This serves as a container for a range of resource-specific editor.
    """

    def __init__(self):
        super(SchemaEditor, self).__init__()
        self.editor = QPlainTextEdit()
        self.editor.setEnabled(False)
        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(QLabel('Schema Editor'))
        vlayout.addWidget(self.editor)
        self.setAutoFillBackground(True)
        self.setLayout(vlayout)

    @property
    def data(self):
        return self.editor.data

    @data.setter
    def data(self, value):

        if value is None:
            widget = QPlainTextEdit()
            widget.setEnabled(False)
        elif hasattr(value, 'prejson'):
            widget = JSONEditor(value.prejson())
        elif value.get('tag') == tag.visible_columns or value.get('tag') == tag.visible_foreign_keys:
            assert value and isinstance(value, dict) and 'parent' in value
            widget = VisibleSourcesEditor(value['parent'], value['tag'])
        elif value.get('tag') == tag.source_definitions:
            assert value and isinstance(value, dict) and 'parent' in value
            widget = SourceDefinitionsEditor(value['parent'])
        elif value.get('tag') == tag.citation:
            assert value and isinstance(value, dict) and 'parent' in value
            widget = CitationEditor(value['parent'])
        else:
            widget = AnnotationEditor(value)

        self.layout().replaceWidget(self.editor, widget)
        self.editor = widget
