"""Pseudo-Column editor widgets.
"""
import logging
import sys
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QWidget, QFormLayout, QComboBox, QVBoxLayout, QListWidget, QHBoxLayout, QPushButton, \
    QTabWidget, QFrame, QLabel
from deriva.core import ermrest_model as _erm, tag as _tag
from .common import source_component_to_str, constraint_name, SimpleTextPropertyWidget, SimpleComboBoxPropertyWidget, \
    MultipleChoicePropertyWidget, SimpleBooleanPropertyWidget, CommentDisplayWidget, SimpleNestedPropertyManager
from .markdown_patterns import MarkdownPatternForm
from .sortkeys import SortKeysWidget
from .table import CommonTableWidget

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
        self.sourceEntry = _SourceEntryWidget(self.table, self.entry, self)
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

        # array_options
        array_options = SimpleNestedPropertyManager('array_options', self.entry, parent=self)
        arrayOptions = QFrame(parent=self)
        arrayOptions.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        form.addRow('Array Options', arrayOptions)
        form = QFormLayout(arrayOptions)  # replace tab form with frame's internal form layout
        arrayOptions.setLayout(form)

        # ...array_options.order
        arrOrder = SortKeysWidget(
            'order',
            array_options.value,
            [c.name for c in table.columns],
            parent=arrayOptions
        )
        arrOrder.valueChanged.connect(array_options.onValueChanged)
        form.addRow('Order', arrOrder)

        # ...array_options.max_length
        arrMaxLen = SimpleTextPropertyWidget(
            'max_length',
            array_options.value,
            placeholder='Maximum number of elements that should be displayed',
            validator=QIntValidator(1, 2**sys.int_info.bits_per_digit),
            parent=self
        )
        arrMaxLen.valueChanged.connect(array_options.onValueChanged)
        form.addRow('Max Length', arrMaxLen)

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

        #
        # -- Facet --
        #
        facetTab = QWidget(parent=self)
        form = QFormLayout(facetTab)
        facetTab.setLayout(form)
        self.addTab(facetTab, 'Facet')

        # ...instructive note
        form.addWidget(QLabel("The options on this form apply only when the pseudo-column is used as a facet.", parent=facetTab))

        # ...open
        form.addRow("Open", MultipleChoicePropertyWidget(
            'open',
            self.entry,
            {
                "Open the facet by default": True,
                "Close the facet by default": False,
                "Default behavior": None
            },
            parent=facetTab
        ))

        # ...ux_mode
        form.addRow('UX Mode', SimpleComboBoxPropertyWidget(
            'ux_mode',
            self.entry,
            choices=['choices', 'ranges', 'check_presence'],
            placeholder='Select the default UX mode for multi-modal facets',
            parent=facetTab
        ))

        # ...constraints
        constraintsTab = QTabWidget(parent=self)
        form.addRow('Constraints', constraintsTab)

        # ...choices
        constraintsTab.addTab(
            CommonTableWidget(
                'choices',
                self.entry,
                editor_widget=SimpleTextPropertyWidget(
                    '_',  # this is just a bogus property name
                    {'_': ''},  # bogus property, widget will still produce valid `.value`
                    placeholder='Enter a choice',
                    truth_fn=lambda x: x is not None,
                    parent=facetTab
                ),
                parent=constraintsTab
            ),
            'Choices'
        )

        # ...ranges
        constraintsTab.addTab(
            CommonTableWidget(
                'ranges',
                self.entry,
                editor_widget=_RangeWidget(facetTab),
                headers_fn=lambda ranges: ['Min', 'Min Exclusive', 'Max', 'Max Exclusive'],
                row_fn=lambda range: (
                    range.get('min'), range.get('min_exclusive'), range.get('max'), range.get('max_exclusive')
                ),
                parent=constraintsTab
            ),
            'Ranges'
        )

        # ...not_null
        constraintsTab.addTab(
            SimpleBooleanPropertyWidget(
                'Match any record that has a value other than NULL',
                'not_null',
                self.entry,
                parent=constraintsTab
            ),
            'Not NULL'
        )

        # ...bar_plot
        form.addRow(
            'Bar Plot',
            MultipleChoicePropertyWidget(
                'bar_plot',
                self.entry,
                {
                    'Default behavior': None,
                    'Show': True,
                    'Hide': False
                },
                other_key='Show w/ # Bins',
                other_widget=_NBinsWidget(self.entry, parent=self),
                parent=self
            )
        )

        # ...hide_null_choice
        form.addRow(
            'Hide NULL',
            SimpleBooleanPropertyWidget(
                'Hide the NULL option in the choice picker',
                'hide_null_choice',
                self.entry,
                parent=self
            )
        )

        # ...hide_not_null_choice
        form.addRow(
            'Hide NOT NULL',
            SimpleBooleanPropertyWidget(
                'Hide the NOT NULL option in the choice picker',
                'hide_not_null_choice',
                self.entry,
                parent=self
            )
        )

    @pyqtSlot()
    def on_sourcekey_valueChanged(self):
        """Handles changes to the `sourcekey` combobox.
        """
        self.sourceEntry.setEnabled(__sourcekey__ not in self.entry)


class _SourceEntryWidget(QWidget):
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
        super(_SourceEntryWidget, self).__init__(parent=parent)
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


class _RangeWidget(QWidget):
    """Inline editor widget for pseudu-column 'range' property values.
    """

    def __init__(self, parent: QWidget = None):
        """Initializes the widget.

        :param parent: parent of this widget
        """
        super(_RangeWidget, self).__init__(parent=parent)
        self._value = {}

        # layout
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        self.setLayout(form)

        # add min and max widgets
        for label, key, exclusive in [
            ('Min', 'min', 'min_exclusive'),
            ('Max', 'max', 'max_exclusive')
        ]:
            # row layout
            widget = QWidget(self)
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)
            form.addRow(label, widget)

            # key (numeric)
            layout.addWidget(
                SimpleTextPropertyWidget(
                    key,
                    self._value,
                    placeholder='Enter a number',
                    validator=QIntValidator(),
                    truth_fn=lambda x: x is not None,
                    parent=widget
                )
            )

            # exclusive (boolean)
            layout.addWidget(
                SimpleBooleanPropertyWidget(
                    'exclusive',
                    exclusive,
                    self._value,
                    parent=widget
                )
            )

    @property
    def value(self):
        return self._value


class _NBinsWidget(QWidget):
    """Special purpose n_bins widget.
    """

    valueChanged = pyqtSignal()

    __n_bins__ = 'n_bins'

    def __init__(self, body: dict, parent: QWidget = None):
        """Initialize the widget.

        :param body: annotation property for 'bar_plot'
        :param parent: the parent widget
        """
        super(_NBinsWidget, self).__init__(parent=parent)
        self.value = body.get('bar_plot')
        if not isinstance(self.value, dict) or self.__n_bins__ not in self.value:
            self.value = {self.__n_bins__: 0}

        # layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # setup the simple text widget
        self._textWidget = SimpleTextPropertyWidget(
            self.__n_bins__,
            {self.__n_bins__: str(self.value[self.__n_bins__])},  # pass value as string
            placeholder='Enter number of bins',
            validator=QIntValidator(),
            truth_fn=lambda x: x is not None,
            parent=self
        )
        self._textWidget.valueChanged.connect(self._on_text_valueChanged)
        layout.addWidget(self._textWidget)

    @pyqtSlot()
    def _on_text_valueChanged(self):
        """Handle text widget value changes.
        """
        try:
            # convert to int
            n_bins = int(self._textWidget.value)
            self.value = {self.__n_bins__: n_bins}
            self.valueChanged.emit()
        except ValueError:
            pass
