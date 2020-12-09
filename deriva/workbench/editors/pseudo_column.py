"""Pseudo-Column editor widgets.
"""
import logging
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QGroupBox, QWidget, QFormLayout, QComboBox, QLineEdit, QCheckBox, QTextEdit, QVBoxLayout, \
    QListWidget, QHBoxLayout, QPushButton, QTabWidget
from deriva.core import ermrest_model as _erm, tag as _tag
from .common import SubsetSelectionWidget, source_component_to_str, constraint_name, set_value_or_del_key, SimpleTextPropertyWidget, SimpleComboBoxPropertyWidget, MultipleChoicePropertyWidget, SimpleBooleanPropertyWidget, CommentDisplayWidget, SimpleNestedPropertyManager
from .markdown_patterns import MarkdownPatternForm

logger = logging.getLogger(__name__)

# property keys
__sourcekey__ = 'sourcekey'
__source__ = 'source'
__outbound__ = 'outbound'
__inbound__ = 'inbound'


class PseudoColumnEditWidget(QTabWidget):
    """Pseudo-column edit widget.
    """

    PseudoColumn = 2**0
    SourceDefinition = 2**1

    table: _erm.Table
    entry: dict

    def __init__(self, table: _erm.Table, entry: dict, mode: int = PseudoColumn, parent: QWidget = None):
        """Initialize the pseudo-column editor widget.

        :param table: the ermrest table instance that contains this pseudo-column
        :param entry: the pseudo-column entry (can take many forms)
        :param mode: the mode flag (PseudoColumn or SourceDefinition)
        :param parent: the QWidget parent of this widget
        """
        super(PseudoColumnEditWidget, self).__init__(parent=parent)
        self.table, self.entry = table, entry

        # ...initialize entry if not starting from an existing pseudo-column
        if self.entry is None or not isinstance(self.entry, dict):
            self.entry = {
                'source': []
            }
        elif 'source' not in self.entry:
            # ...add blank source, if none found... will clean this up later, if not used
            self.entry['source'] = []

        #
        # -- Source attributes --
        #
        sourceTab = QWidget(parent=self)
        form = QFormLayout(sourceTab)
        sourceTab.setLayout(form)
        self.addTab(sourceTab, 'Source')

        # ...sourcekey
        sourcekeys = self.table.annotations.get(_tag.source_definitions, {}).get('sources', {}).keys()
        if bool(mode & PseudoColumnEditWidget.PseudoColumn):
            enable_source_entry = __sourcekey__ not in self.entry  # enable if no sourcekey property exists
            sourceKeyComboBox = SimpleComboBoxPropertyWidget(
                __sourcekey__,
                self.entry,
                sourcekeys,
                placeholder='Select a source key',
                parent=self
            )
            sourceKeyComboBox.valueChanged.connect(self.on_sourcekey_valueChanged)
            form.addRow('Source Key', sourceKeyComboBox)
        elif bool(mode & PseudoColumnEditWidget.SourceDefinition):
            enable_source_entry = True
            form.addRow('Source Key', SimpleTextPropertyWidget(
                __sourcekey__,
                self.entry,
                placeholder='Enter source key',
                parent=self
            ))
        else:
            raise ValueError('Invalid mode selected for source key control initialization')

        # ...source
        self.sourceEntry = SourceEntryWidget(self.table, self.entry, self)
        self.sourceEntry.setEnabled(enable_source_entry)
        form.addRow('Source Entry', self.sourceEntry)

        #
        # -- Options --
        #
        optionsTab = QWidget(parent=self)
        form = QFormLayout(optionsTab)
        optionsTab.setLayout(form)
        self.addTab(optionsTab, 'Options')

        # ...markdown name
        form.addRow('Markdown Name', SimpleTextPropertyWidget(
            'markdown_name',
            self.entry,
            placeholder='Enter markdown pattern',
            parent=self
        ))

        # ...comment
        form.addRow('Comment', SimpleTextPropertyWidget(
            'comment',
            self.entry,
            placeholder='Enter plain text',
            parent=self
        ))

        # ...comment_display
        form.addRow('Comment Display', CommentDisplayWidget(self.entry, parent=self))

        # ...entity
        entityWidget = MultipleChoicePropertyWidget(
            'entity',
            self.entry,
            {
                'Treat as an entity': True,
                'Treat as a scalar value': False,
                'Default behavior': None
            },
            parent=self
        )
        entityWidget.layout().setContentsMargins(0, 0, 0, 0)
        form.addRow('Entity', entityWidget)

        # ...self_link
        form.addRow('Self Link', SimpleBooleanPropertyWidget(
            'If source is key, switch display mode to self link',
            'self_link',
            self.entry,
            truth_fn=lambda x: x is not None,
            parent=self
        ))

        # ...aggregate
        form.addRow('Aggregate', SimpleComboBoxPropertyWidget(
            'aggregate',
            self.entry,
            ['min', 'max', 'cnt', 'cnt_d', 'array', 'array_d'],
            placeholder='Select aggregate function, if desired',
            parent=self
        ))

        # ...array options
        # todo

        #
        # -- Display attributes --
        #
        display = SimpleNestedPropertyManager('display', self.entry, parent=self)
        # ...markdown pattern form widget used as the base widget for this tab
        markdownPattern = MarkdownPatternForm(
            [('markdown_pattern', 'Markdown Pattern')],
            display.value,
            include_template_engine=True,
            include_wait_for=True,
            sourcekeys=sourcekeys,
            parent=self
        )
        markdownPattern.valueChanged.connect(display.onValueChanged)
        self.addTab(markdownPattern, 'Display')
        form = markdownPattern.form  # extend the markdown pattern form widget

        # ...show_foreign_key_link checkbox
        fkeyLink = MultipleChoicePropertyWidget(
            'show_foreign_key_link',
            display.value,
            {
                'Inherited behavior of outbound foreign key display': None,
                'Avoid adding extra link to the foreign key display': False
            },
            parent=self
        )
        fkeyLink.valueChanged.connect(display.onValueChanged)
        form.addRow('Show FK Link', fkeyLink)

        # ...array_ux_mode combobox
        arrayUXMode = SimpleComboBoxPropertyWidget(
            'array_ux_mode',
            display.value,
            ['olist', 'ulist', 'csv', 'raw'],
            placeholder='Select a UX mode for aggregate results',
            parent=self
        )
        form.addRow('Array UX Mode', arrayUXMode)

    @pyqtSlot()
    def on_sourcekey_valueChanged(self):
        """Handles changes to the `sourcekey` combobox.
        """
        self.sourceEntry.setEnabled(__sourcekey__ not in self.entry)


class SourceEntryWidget(QWidget):
    """Pseudo-column 'source' property editor widget.
    """

    table: _erm.Table
    entry: dict

    valueChanged = pyqtSignal()

    def __init__(self, table: _erm.Table, entry: dict, parent: QWidget = None):
        """Initializes the widget.

        :param table: the root ermrest table for the source entry
        :param entry: the visible-source pseudo-column entry dictionary; must contain an 'source' property
        :param parent: the parent widget
        """
        super(SourceEntryWidget, self).__init__(parent=parent)
        self.table = table
        self.entry = entry
        self.context = [table]

        # layout
        vlayout = QVBoxLayout(self)
        vlayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vlayout)

        # source list widget
        self.sourceList = QListWidget(parent=self)
        vlayout.addWidget(self.sourceList)

        # get source entry and enforce a canonical structure as a list of elements
        source = self.entry[__source__]
        if isinstance(source, str):
            self.entry[__source__] = source = [source]
        elif isinstance(source, list) and len(source) == 2 and all(isinstance(item, str) for item in source):
            self.entry[__source__] = source = [{__outbound__: source}]

        # populate source list widget and update context
        validated_path = []
        try:
            for item in source:
                # update the context, based on the type of source component
                if isinstance(item, str):
                    # case: column name
                    column = {col.name: col for col in self.context[-1].columns}[item]
                    self.context.append(column)
                elif __outbound__ in item:
                    # case: outbound fkey
                    fkey = self.table.schema.model.fkey(item[__outbound__])
                    self.context.append(fkey.pk_table)
                else:
                    # case: inbound fkey
                    assert __inbound__ in item
                    fkey = self.table.schema.model.fkey(item[__inbound__])
                    self.context.append(fkey.table)
                # update the source list
                self.sourceList.addItem(source_component_to_str(item))
                validated_path.append(item)
        except KeyError as e:
            logger.error("Invalid path component %s found in source entry %s" % (str(e), str(source)))
            self.entry[__source__] = validated_path  # set source to the valid partial path

        # available sources combobox
        self.availableSource = QComboBox(parent=self)
        self.availableSource.setPlaceholderText('Select next path element for the source entry')
        context = self.context[-1]
        if isinstance(context, _erm.Table):
            self._updateAvailableSourcesFromTable(context)
        vlayout.addWidget(self.availableSource)

        # source push and pop buttons
        controls = QWidget(self)
        controls.setLayout(QHBoxLayout(controls))
        controls.layout().setContentsMargins(0, 0, 0, 5)
        # ...push button
        self.pushButton = QPushButton('push')
        self.pushButton.setEnabled(len(self.availableSource) > 0)  # disable if no sources
        self.pushButton.clicked.connect(self.on_push)
        controls.layout().addWidget(self.pushButton)
        # ...pop button
        self.popButton = QPushButton('pop')
        self.popButton.clicked.connect(self.on_pop)
        controls.layout().addWidget(self.popButton)
        # ...add remaining controls to form
        vlayout.addWidget(controls)

    @property
    def value(self):
        """Returns the 'source' property value.
        """
        return self.entry[__source__]

    def _updateAvailableSourcesFromTable(self, table):
        """Updates the list of available sources based on the given table."""

        assert isinstance(table, _erm.Table)
        self.availableSource.clear()
        for column in table.columns:
            self.availableSource.addItem(
                column.name,
                userData=column
            )
        for fkey in table.foreign_keys:
            self.availableSource.addItem(
                "%s:%s (outbound)" % tuple(constraint_name(fkey)),
                userData={__outbound__: fkey}
            )
        for ref in table.referenced_by:
            self.availableSource.addItem(
                "%s:%s (inbound)" % tuple(constraint_name(ref)),
                userData={__inbound__: ref}
            )

    @pyqtSlot()
    def on_push(self):
        """Handler for pushing a path element onto the 'source' property.
        """
        data = self.availableSource.currentData()
        if not data:
            return

        # update the source list display
        self.sourceList.addItem(
            self.availableSource.currentText()
        )

        # update the available sources, source entry, and append to the context
        if isinstance(data, _erm.Column):
            context = data
            self.availableSource.clear()
            self.availableSource.setEnabled(False)
            self.pushButton.setEnabled(False)
            self.entry[__source__].append(data.name)
        elif __outbound__ in data:
            fkey = data[__outbound__]
            assert isinstance(fkey, _erm.ForeignKey)
            context = fkey.pk_table
            self._updateAvailableSourcesFromTable(context)
            self.entry[__source__].append({
                __outbound__: constraint_name(fkey)
            })
        else:
            fkey = data[__inbound__]
            assert isinstance(fkey, _erm.ForeignKey)
            context = fkey.table
            self._updateAvailableSourcesFromTable(context)
            self.entry[__source__].append({
                __inbound__: constraint_name(fkey)
            })

        # update control state
        self.context.append(context)
        self.popButton.setEnabled(True)

        # emit changes
        self.valueChanged.emit()

    @pyqtSlot()
    def on_pop(self):
        """Handler for popping the top path element of the 'source' property.
        """

        # update source list
        self.sourceList.takeItem(len(self.sourceList)-1)

        # update entry source
        if self.entry[__source__]:
            self.entry[__source__].pop()
            self.context.pop()
            self._updateAvailableSourcesFromTable(self.context[-1])

        # update control state
        self.availableSource.setEnabled(True)
        self.pushButton.setEnabled(True)
        self.popButton.setEnabled(len(self.entry[__source__]) > 0)

        # emit changes
        self.valueChanged.emit()
