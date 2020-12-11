"""Editor for the `display` annotation.
"""
import logging
from typing import Union
from PyQt5.QtWidgets import QWidget, QFormLayout, QVBoxLayout
from deriva.core import tag, ermrest_model as _erm
from .common import SimpleTextPropertyWidget, SimpleBooleanPropertyWidget, MultipleChoicePropertyWidget, \
    SimpleComboBoxPropertyWidget, raise_on_invalid
from .tabbed_contexts import EasyTabbedContextsWidget

logger = logging.getLogger(__name__)


class DisplayAnnotationEditor(QWidget):
    """Display annotation editor widget.
    """

    __comment__ = 'comment'
    __show_null__ = 'show_null'
    __comment_display__ = 'comment_display'
    __comment_display_choices__ = [
        'inline',
        'tooltip'
    ]
    __show_foreign_key_link__ = 'show_foreign_key_link'

    def __init__(self,
                 model_obj: Union[_erm.Model, _erm.Schema, _erm.Table, _erm.Column, _erm.Key],
                 parent: QWidget = None):
        """ Initialize the widget.

        :param model_obj: a schema, table, column, key, or foreign key object that contains annotations
        :param parent: the parent widget of this widget
        """
        raise_on_invalid(model_obj, [_erm.Model, _erm.Schema, _erm.Table, _erm.Column, _erm.Key], tag.display)
        super(DisplayAnnotationEditor, self).__init__(parent=parent)
        self.body = model_obj.annotations[tag.display]

        # layout
        layout = QFormLayout(self)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        # ...name
        layout.addRow('Name', SimpleTextPropertyWidget('name', self.body, 'Enter a display name'))
        layout.addRow('Markdown Name', SimpleTextPropertyWidget('markdown_name', self.body, 'Enter a display name using markdown'))

        # name style
        name_style = self.body['name_style'] = self.body.get('name_style', {})
        # ...underline space
        layout.addRow('Underline Space', SimpleBooleanPropertyWidget(
            'Convert underline characters (_) into space characters in model element names',
            'underline_space',
            name_style,
            parent=self
        ))
        # ...title case
        layout.addRow('Title Case', SimpleBooleanPropertyWidget(
            'Convert element names to "title case" meaning the first character of each word is capitalized',
            'title_case',
            name_style,
            parent=self
        ))
        # ...markdown
        layout.addRow('Markdown', SimpleBooleanPropertyWidget(
            "Interpret the model element’s actual name as a Markdown string",
            'markdown',
            name_style,
            parent=self
        ))

        #
        # comment
        #

        # ...convert deprecated values
        if isinstance(self.body.get(self.__comment__), str):
            logger.warning('Deprecated "%s" value in "%s" annotation. Converting to contextualized format with '
                           'current value in "*" context.' % (self.__comment__, tag.display))
            self.body[self.__comment__] = {"*": self.body[self.__comment__]}

        # ...function to create editor widget
        def create_comment_editor_widget(context: str, parent: QWidget = self) -> QWidget:
            """Returns a new comment editor widget for the given context.
            """
            return MultipleChoicePropertyWidget(
                context,
                self.body[self.__comment__],
                {
                    'Do not show comments for this context': False
                },
                other_key='Comment',
                other_widget=SimpleTextPropertyWidget(context, self.body[self.__comment__],
                                                      placeholder='Enter comment text',
                                                      parent=parent),
                layout=QVBoxLayout(),
                parent=self
            )

        # ...add the tabbed context widget
        comment = EasyTabbedContextsWidget(self.__comment__,
                                           self.body,
                                           lambda context: False,
                                           create_comment_editor_widget,
                                           parent=self)
        layout.addRow("Comment", comment)

        #
        # comment_display
        #
        table_comment_display = 'table_comment_display'
        column_comment_display = 'column_comment_display'

        # ...function to create editor widget
        def create_comment_display_widget(context: str, parent: QWidget = self) -> QWidget:
            """Returns a new comment_display editor.
            """
            widget = QWidget(parent=parent)
            form = QFormLayout(widget)
            widget.setLayout(form)

            form.addRow("Table Comment Display",
                        SimpleComboBoxPropertyWidget(table_comment_display,
                                                     self.body[self.__comment_display__][context],
                                                     self.__comment_display_choices__,
                                                     placeholder='Select the mode for comment display',
                                                     parent=widget)
                        )

            form.addRow("Column Comment Display",
                        SimpleComboBoxPropertyWidget(column_comment_display,
                                                     self.body[self.__comment_display__][context],
                                                     self.__comment_display_choices__,
                                                     placeholder='Select the mode for comment display',
                                                     parent=widget)
                        )

            return widget

        # ...add the tabbed context widget
        commentDisplay = EasyTabbedContextsWidget(self.__comment_display__,
                                                  self.body,
                                                  lambda context: {},
                                                  create_comment_display_widget,
                                                  parent=self)
        layout.addRow("Comment Display", commentDisplay)

        #
        # show_null
        #

        # ...function to create editor widget
        def create_shownull_editor_widget(context: str, parent: QWidget = self) -> QWidget:
            """Returns a new show_null editor widget for the given context.
            """
            return MultipleChoicePropertyWidget(
                context,
                self.body[self.__show_null__],
                {
                    'Show': True,
                    'Hide': False
                },
                other_key='Use other indicator for NULLs',
                other_widget=SimpleTextPropertyWidget(context, self.body[self.__show_null__],
                                                      placeholder='Enter text to use as indicator of NULL value',
                                                      parent=parent),
                parent=parent
            )

        # ...add the tabbed context widget
        showNull = EasyTabbedContextsWidget(self.__show_null__,
                                            self.body,
                                            lambda context: True,
                                            create_shownull_editor_widget,
                                            parent=self)
        layout.addRow("Show Nulls", showNull)

        #
        # show_foreign_key_link
        #

        # ...function to create editor widget
        def create_show_foreign_key_link_widget(context: str, parent: QWidget = self) -> QWidget:
            """Returns a new show_foreign_key_link editor.
            """
            return MultipleChoicePropertyWidget(
                context,
                self.body[self.__show_foreign_key_link__],
                {
                    'Present the foreign key values with a link to the referred row': True,
                    'Present the foreign key values without adding extra links': False
                },
                layout=QVBoxLayout(),
                parent=parent
            )

        # ...add the tabbed context widget
        fkLink = EasyTabbedContextsWidget(self.__show_foreign_key_link__,
                                          self.body,
                                          lambda context: True,
                                          create_show_foreign_key_link_widget,
                                          parent=self)
        layout.addRow("Show FK Link", fkLink)
