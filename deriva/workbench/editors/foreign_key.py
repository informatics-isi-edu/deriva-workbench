"""Editor for the foreign-key annotation.
"""
from PyQt5.QtWidgets import QWidget, QFormLayout
from deriva.core import tag, ermrest_model as _erm
from .common import SimpleTextPropertyWidget, SimpleComboBoxPropertyWidget


class ForeignKeyAnnotationEditor(QWidget):
    """Foreign Key annotation editor widget.
    """

    __comment_display_choices__ = [
        'inline',
        'tooltip'
    ]

    def __init__(self, fkey: _erm.ForeignKey, parent: QWidget = None):
        super(ForeignKeyAnnotationEditor, self).__init__(parent=parent)
        self.body = fkey.annotations[tag.foreign_key]

        layout = QFormLayout(self)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        layout.addRow('To Name', SimpleTextPropertyWidget('to_name', self.body, 'Enter a display name'))
        layout.addRow('To Comment', SimpleTextPropertyWidget('to_comment', self.body, 'Enter comment text'))
        layout.addRow('To Comment Display', SimpleComboBoxPropertyWidget(
            'to_comment_display',
            self.body,
            self.__comment_display_choices__,
            placeholder='Select a comment display mode'
        ))
        layout.addRow('From Name', SimpleTextPropertyWidget('from_name', self.body, 'Enter a display name'))
        layout.addRow('From Comment', SimpleTextPropertyWidget('from_comment', self.body, 'Enter comment text'))
        layout.addRow('From Comment Display', SimpleComboBoxPropertyWidget(
            'from_comment_display',
            self.body,
            self.__comment_display_choices__,
            placeholder='Select a comment display mode'
        ))
        layout.addRow('Domain Filter Pattern (deprecated)', SimpleTextPropertyWidget('domain_filter_pattern', self.body, 'Enter a pattern'))
