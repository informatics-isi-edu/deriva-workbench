"""Schema editor widget that launches resource-specific editors.
"""
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QGroupBox
from deriva.core import tag
from .editors import JSONEditor, AnnotationEditor, VisibleSourcesEditor, SourceDefinitionsEditor, CitationEditor, \
    TableDisplayEditor, ForeignKeyAnnotationEditor, DisplayAnnotationEditor, AssetAnnotationEditor, \
    KeyDisplayEditor, ColumnDisplayEditor


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
        elif not isinstance(value, dict):
            widget = None
        elif 'acls' in value:
            widget = JSONEditor(value.get('acls'))
        elif 'acl_bindings' in value:
            widget = JSONEditor(value.get('acl_bindings'))
        elif 'tag' in value:
            assert value and isinstance(value, dict) and 'parent' in value
            if value.get('as_source'):
                widget = AnnotationEditor(value)
            elif value.get('tag') == tag.visible_columns or value.get('tag') == tag.visible_foreign_keys:
                widget = VisibleSourcesEditor(value['parent'], value['tag'])
            elif value.get('tag') == tag.source_definitions:
                widget = SourceDefinitionsEditor(value['parent'])
            elif value.get('tag') == tag.citation:
                widget = CitationEditor(value['parent'])
            elif value.get('tag') == tag.table_display:
                widget = TableDisplayEditor(value['parent'])
            elif value.get('tag') == tag.foreign_key:
                widget = ForeignKeyAnnotationEditor(value['parent'])
            elif value.get('tag') == tag.display:
                widget = DisplayAnnotationEditor(value['parent'])
            elif value.get('tag') == tag.asset:
                widget = AssetAnnotationEditor(value['parent'])
            elif value.get('tag') == tag.key_display:
                widget = KeyDisplayEditor(value['parent'])
            elif value.get('tag') == tag.column_display:
                widget = ColumnDisplayEditor(value['parent'])
            else:
                widget = AnnotationEditor(value)
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
