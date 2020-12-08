"""Common components for managing various forms of sort keys in annotations.
"""
from PyQt5.QtWidgets import QWidget, QHBoxLayout
from .common import SimpleComboBoxPropertyWidget, SimpleBooleanPropertyWidget
from .table import CommonTableWidget


class SortKeysWidget(CommonTableWidget):

    def __init__(self, key: str, body: dict, columns: list, parent: QWidget = None):
        """Initializes the row order widget.

        :param key: the key for the sortkeys annotation (e.g., 'row_order', 'column_order')
        :param body: an object that may contain a `sortkeys` annotation.
        :param columns: a list of column names
        :param parent: the parent widget
        """
        super(SortKeysWidget, self).__init__(
            key,
            body,
            editor_widget=_SortKeyWidget(columns),
            headers_fn=lambda sortkeys: ['Column', 'Descending'],
            row_fn=lambda sortkey: (
                sortkey if isinstance(sortkey, str) else sortkey['column'],
                sortkey.get('descending', False) if isinstance(sortkey, dict) else False
            ),
            parent=parent)


class _SortKeyWidget(QWidget):
    """Inline editor widget for sortkey properties.
    """

    def __init__(self, columns: list, parent: QWidget = None):
        """Initializes the widget.

        :param columns: list of columns that may be selected for use in a sort key
        :param parent: parent of this widget
        """
        super(_SortKeyWidget, self).__init__(parent=parent)
        self._value = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # ...column
        layout.addWidget(
            SimpleComboBoxPropertyWidget(
                'column',
                self._value,
                columns,
                placeholder='Select column name',
                parent=self
            )
        )

        # ...descending
        layout.addWidget(
            SimpleBooleanPropertyWidget(
                'descending',
                'descending',
                self._value,
                parent=self
            )
        )

    @property
    def value(self):
        return self._value
