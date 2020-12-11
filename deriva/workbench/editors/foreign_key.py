"""Editor for the foreign-key annotation.
"""
import logging
from PyQt5.QtWidgets import QWidget, QFormLayout, QVBoxLayout, QGroupBox, QHBoxLayout, QFrame
from deriva.core import tag, ermrest_model as _erm
from .common import SimpleTextPropertyWidget, MultipleChoicePropertyWidget, SimpleNestedPropertyManager, \
    CommentDisplayWidget, raise_on_invalid
from .sortkeys import SortKeysWidget
from .tabbed_contexts import EasyTabbedContextsWidget

logger = logging.getLogger(__name__)


class ForeignKeyAnnotationEditor(QWidget):
    """Foreign Key annotation editor widget.
    """

    __display__ = 'display'
    __column_order__ = 'column_order'
    __show_foreign_key_link__ = 'show_foreign_key_link'

    def __init__(self, fkey: _erm.ForeignKey, parent: QWidget = None):
        """Initialize the widget.

        :param fkey: a foreign key resource
        :param parent: the parent widget
        """
        raise_on_invalid(fkey, _erm.ForeignKey, tag.foreign_key)
        super(ForeignKeyAnnotationEditor, self).__init__(parent=parent)
        self.body = fkey.annotations[tag.foreign_key]

        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        # to-from container, for side-by-side display of to and from group boxes
        to_from_ = QWidget(self)
        to_from_.setLayout(QHBoxLayout(to_from_))
        to_from_.layout().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(to_from_)

        # to
        to_ = QGroupBox("To Direction", parent=self)
        to_.setLayout(QFormLayout(to_))
        to_.layout().addRow('Name', SimpleTextPropertyWidget('to_name', self.body, 'Enter a display name'))
        to_.layout().addRow('Comment', SimpleTextPropertyWidget('to_comment', self.body, 'Enter comment text'))
        to_.layout().addRow('Comment Display', CommentDisplayWidget(
            self.body,
            key='to_comment_display',
            parent=to_
        ))
        to_from_.layout().addWidget(to_)

        # from
        from_ = QGroupBox("From Direction", parent=self)
        from_.setLayout(QFormLayout(from_))
        from_.layout().addRow('Name', SimpleTextPropertyWidget('from_name', self.body, 'Enter a display name'))
        from_.layout().addRow('Comment', SimpleTextPropertyWidget('from_comment', self.body, 'Enter comment text'))
        from_.layout().addRow('Comment Display', CommentDisplayWidget(
            self.body,
            key='from_comment_display',
            parent=from_
        ))
        to_from_.layout().addWidget(from_)

        #
        # Domain Filter
        #
        __domain_filter_pattern__ = 'domain_filter_pattern'
        __domain_filter__ = 'domain_filter'
        __ermrest_path_pattern__ = 'ermrest_path_pattern'

        # ...convert deprecated value to current format
        if __domain_filter_pattern__ in self.body:
            base_message = 'Deprecated "%s" property found in "%s" annotation.' % (__domain_filter_pattern__, tag.foreign_key)
            if __domain_filter__ not in self.body:
                logger.warning(base_message + ' Annotation will be converted into "%s.%s" property.' % (
                    __domain_filter__, __ermrest_path_pattern__
                ))
                self.body[__domain_filter__] = {
                    __ermrest_path_pattern__: self.body[__domain_filter_pattern__]
                }
                del self.body[__domain_filter_pattern__]
            else:
                logger.warning(base_message + ' It will be ignored in favor of existing "%s" property.' % __domain_filter__)

        # ...domain filter widgets
        domainFilter = QGroupBox("Domain Filter")
        domainFilter.setLayout(QFormLayout(domainFilter))
        domain_filter_manager = SimpleNestedPropertyManager('domain_filter', self.body, parent=domainFilter)

        for row_label, nested_key, placeholder in [
            ('ERMrest Path', __ermrest_path_pattern__, 'Enter an ERMrest path pattern'),
            ('Display Markdown', 'display_markdown_pattern', 'Enter a markdown pattern')
        ]:
            nestedWidget = SimpleTextPropertyWidget(nested_key,
                                                    domain_filter_manager.value,
                                                    placeholder=placeholder,
                                                    parent=domainFilter)
            nestedWidget.valueChanged.connect(domain_filter_manager.onValueChanged)
            domainFilter.layout().addRow(row_label, nestedWidget)

        layout.addWidget(domainFilter)

        #
        # display
        #
        display = QGroupBox("Display", parent=self)
        display.setLayout(QVBoxLayout(display))

        # ...function to create editor widget
        def create_display_editor_widget(context: str, parent: QWidget = self) -> QWidget:
            """Returns a new display editor widget for the given context.
            """
            container = QWidget(parent)
            container.setLayout(QVBoxLayout(container))

            # ...column order widget
            columnOrder = MultipleChoicePropertyWidget(
                self.__column_order__,
                self.body[self.__display__][context],
                {
                    'Accept the default sorting behavior': None,
                    'Sorting by this foreign key should not be offered': False
                },
                other_key='Sort by the following columns in the referenced table',
                other_widget=SortKeysWidget(self.__column_order__,
                                            self.body[self.__display__][context],
                                            [c.name for c in fkey.pk_table.columns],
                                            parent=container),
                layout=QVBoxLayout(),
                parent=container
            )
            container.layout().addWidget(columnOrder)

            # ...separator
            hline = QFrame(parent=container)
            hline.setFrameStyle(QFrame.HLine | QFrame.Sunken)
            container.layout().addWidget(hline)

            # ...show fk link widget
            fkLink = MultipleChoicePropertyWidget(
                self.__show_foreign_key_link__,
                self.body[self.__display__][context],
                {
                    'Accept the default behavior of foreign key display': None,
                    'Override the inherited behavior of foreign key display and add a link to the referred row': True,
                    'Override the inherited behavior of foreign key display by not adding any the extra': False
                },
                layout=QVBoxLayout(),
                parent=container
            )
            container.layout().addWidget(fkLink)

            return container

        # ...add the tabbed context widget
        displayContexts = EasyTabbedContextsWidget(self.__display__,
                                                   self.body,
                                                   lambda context: {self.__column_order__: []},
                                                   create_display_editor_widget,
                                                   parent=self)
        display.layout().addWidget(displayContexts)
        layout.addWidget(display)

