"""Editor for the `display` annotation.
"""
import logging
from PyQt5.QtWidgets import QWidget, QFormLayout
from deriva.core import tag, ermrest_model as _erm
from .common import SimpleTextPropertyWidget, SimpleBooleanPropertyWidget

logger = logging.getLogger(__name__)


class DisplayAnnotationEditor(QWidget):
    """Display annotation editor widget.
    """

    __comment_display_choices__ = [
        'inline',
        'tooltip'
    ]

    def __init__(self,
                 model_obj: _erm.Schema or _erm.Table or _erm.Column or _erm.Key or _erm.ForeignKey,
                 parent: QWidget = None):
        """ Initialize the widget.

        :param model_obj: a schema, table, column, key, or foreign key object that contains annotations
        :param parent: the parent widget of this widget
        """
        super(DisplayAnnotationEditor, self).__init__(parent=parent)
        self.body = model_obj.annotations[tag.display]

        layout = QFormLayout(self)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        # ...name
        layout.addRow('Name', SimpleTextPropertyWidget('name', self.body, 'Enter a display name'))
        layout.addRow('Markdown Name', SimpleTextPropertyWidget('markdown_name', self.body, 'Enter a display name using markdown'))

        # ...comment, only if it is a simple string form
        if isinstance(self.body.get('comment', ''), str):
            layout.addRow('Comment', SimpleTextPropertyWidget('comment', self.body, 'Enter comment text'))
        else:
            logger.warning('Contextualized "comment" is not yet supported in "%s" annotations' % tag.display)

        # name style
        name_style = self.body['name_style'] = self.body.get('name_style', {})
        # ...underline space
        layout.addRow('Underline Space', SimpleBooleanPropertyWidget(
            'Convert underline "_" characters into spaces in model names for display',
            'underline_space',
            name_style,
            parent=self
        ))
        # ...title case
        layout.addRow('Title Case', SimpleBooleanPropertyWidget(
            'Convert model names into title case',
            'title_case',
            name_style,
            parent=self
        ))
        # ...markdown
        layout.addRow('Markdown', SimpleBooleanPropertyWidget(
            'Interpret the model name as a markdown pattern',
            'markdown',
            name_style,
            parent=self
        ))
