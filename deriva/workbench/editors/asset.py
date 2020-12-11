"""Editor for the `asset` annotation.
"""
from PyQt5.QtWidgets import QWidget, QFormLayout, QVBoxLayout
from deriva.core import tag, ermrest_model as _erm
from .common import SimpleTextPropertyWidget, SimpleComboBoxPropertyWidget, MultipleChoicePropertyWidget, \
    raise_on_invalid
from .table import CommonTableWidget

__system_cnames__ = {'RID', 'RCB', 'RCT', 'RMB', 'RMT'}


class AssetAnnotationEditor(QWidget):
    """Asset annotation editor widget.
    """

    def __init__(self, column: _erm.Column, parent: QWidget = None):
        super(AssetAnnotationEditor, self).__init__(parent=parent)
        raise_on_invalid(column, _erm.Column, tag.asset)
        self.column = column
        self.body = column.annotations[tag.asset]
        column_names = [c.name for c in self.column.table.columns if c.name not in __system_cnames__]

        # layout
        form = QFormLayout(self)
        self.setLayout(form)

        # url_pattern
        form.addRow(
            'URL Pattern',
            SimpleTextPropertyWidget(
                'url_pattern',
                self.body,
                placeholder='Enter an URL upload pattern',
                parent=self
            )
        )

        # browser_upload
        form.addRow(
            'Browser Upload',
            MultipleChoicePropertyWidget(
                'browser_upload',
                self.body,
                {
                    'Allow browser upload when given valid URL Pattern': None,
                    'Disable browser upload': False
                },
                layout=QVBoxLayout(),
                parent=self
            )
        )

        # filename_column
        form.addRow(
            'Filename',
            SimpleComboBoxPropertyWidget(
                'filename_column',
                self.body,
                column_names,
                placeholder='Select a text column to store the filename',
                parent=self
            )
        )

        # byte_count_column
        form.addRow(
            'Byte Count',
            SimpleComboBoxPropertyWidget(
                'byte_count_column',
                self.body,
                column_names,
                placeholder='Select an int column to store the byte count'
            )
        )

        # md5 (sha256 is not yet supported)
        for alg in ['md5']:
            form.addRow(
                alg.upper(),
                MultipleChoicePropertyWidget(
                    alg,
                    self.body,
                    {
                        'Do not store checksum': None,
                        'Store checksum in asset storage service': True
                    },
                    other_key='Store checksum in selected column',
                    other_widget=SimpleComboBoxPropertyWidget(
                        alg,
                        self.body,
                        column_names,
                        placeholder='Select a text column to store the checksum',
                        parent=self
                    ),
                    layout=QVBoxLayout(),
                    parent=self
                )
            )

        # filename_ext_filter
        form.addRow(
            'File Extensions',
            CommonTableWidget(
                'filename_ext_filter',
                self.body,
                editor_widget=SimpleTextPropertyWidget(
                    '_',        # this is just a bogus property name
                    {'_': ''},  # bogus property, widget will still produce valid `.value`
                    placeholder='Enter extension (e.g., ".jpg", ".pdf", etc.)',
                    truth_fn=lambda x: x is not None,
                    parent=self
                ),
                parent=self
            )
        )
