"""Schema editor widget that launches resource-specific editors.
"""
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QGroupBox
from deriva.core import tag
from .editors import JSONEditor, AnnotationEditor, VisibleSourcesEditor, SourceDefinitionsEditor, CitationEditor, \
    TableDisplayContextsEditor, ForeignKeyAnnotationEditor, DisplayAnnotationEditor


class SchemaEditor(QGroupBox):
    """Schema editor widget.

    This serves as a container for a range of resource-specific editor.
    """

    def __init__(self, parent: QWidget = None):
        super(SchemaEditor, self).__init__('Schema Editor', parent=parent)
        self.editor = None
        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(3, 3, 3, 3)
        self.setAutoFillBackground(True)
        self.setLayout(vlayout)

    @property
    def data(self):
        return self.editor.data

    @data.setter
    def data(self, value):
        """Sets the object to be edited.
        """

        # instantiate the appropriate editor for the type of value
        if value is None:
            widget = None
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
        elif value.get('tag') == tag.table_display:
            assert value and isinstance(value, dict) and 'parent' in value
            widget = TableDisplayContextsEditor(value['parent'])
        elif value.get('tag') == tag.foreign_key:
            assert value and isinstance(value, dict) and 'parent' in value
            widget = ForeignKeyAnnotationEditor(value['parent'])
        elif value.get('tag') == tag.display:
            assert value and isinstance(value, dict) and 'parent' in value
            widget = DisplayAnnotationEditor(value['parent'])
        else:
            widget = AnnotationEditor(value)

        # replace existing editor instance
        if self.editor:
            self.layout().replaceWidget(self.editor, widget)
            self.editor.hide()
            del self.editor
        else:
            self.layout().addWidget(widget)

        # record the editor
        self.editor = widget
