"""Editor package for the citation annotation.
"""
from PyQt5.QtWidgets import QWidget
from deriva.core import tag, ermrest_model as _erm
from .markdown_patterns import MarkdownPatternForm
from .common import raise_on_invalid


class CitationEditor(MarkdownPatternForm):
    """Citation annotation editor.
    """

    def __init__(self, table: _erm.Table, parent: QWidget = None):
        """Initialize the widget.

        :param table: the ermrest table that contains the citation annotation,
        :param parent: the parent widget
        """
        raise_on_invalid(table, _erm.Table, tag.citation)
        super(CitationEditor, self).__init__(
            [
                ('journal_pattern', 'Journal'),
                ('author_pattern', 'Author'),
                ('title_pattern', 'Title'),
                ('year_pattern', 'Year'),
                ('url_pattern', 'URL'),
                ('id_pattern', 'ID')
            ],
            table.annotations[tag.citation],
            include_template_engine=True,
            include_wait_for=True,
            sourcekeys=table.annotations.get(tag.source_definitions, {}).get('sources', {}).keys(),
            parent=parent
        )
