"""Pseudo-Column editor widgets.
"""
import logging
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QGroupBox, QWidget, QFormLayout, QComboBox, QLineEdit, QCheckBox, QTextEdit, QVBoxLayout, \
    QListWidget, QHBoxLayout, QPushButton
from deriva.core import ermrest_model as _erm, tag as _tag
from .common import SubsetSelectionWidget, source_component_to_str, constraint_name

logger = logging.getLogger(__name__)


class PseudoColumnEditWidget(QGroupBox):
    """Pseudo-column edit widget.
    """

    PseudoColumn = 2**0
    SourceDefinition = 2**1

    table: _erm.Table
    entry: dict

    def __init__(self, table: _erm.Table, entry: dict, mode: int = PseudoColumn, parent: QWidget = None):
        """Initialize the pseudo-column editor widget.

        :param table: the ermrest_model.Table instance that contains this pseudo-column
        :param entry: the pseudo-column entry (can take many forms)
        :param mode: the mode flag (PseudoColumn or SourceDefinition)
        :param parent: the QWidget parent of this widget
        """
        super(PseudoColumnEditWidget, self).__init__(parent=parent)
        self.table, self.entry = table, entry
        display = self.entry.get('display', {}) if isinstance(self.entry, dict) else {}

        # ...initialize entry if not starting from an existing pseudo-column
        if self.entry is None or not isinstance(self.entry, dict):
            self.entry = {
                'source': []
            }
        elif 'source' not in self.entry:
            # ...add blank source, if none found... will clean this up later, if not used
            self.entry['source'] = []

        # Form layout
        form = QFormLayout()
        self.setLayout(form)

        # -- Source attributes --

        # ...sourcekey
        sourcekeys = self.table.annotations.get(_tag.source_definitions, {}).get('sources', {}).keys()
        if bool(mode & PseudoColumnEditWidget.PseudoColumn):
            self.sourceKeyComboBox = QComboBox(parent=self)
            self.sourceKeyComboBox.addItem('')
            self.sourceKeyComboBox.addItems(sourcekeys)
            self.sourceKeyComboBox.setPlaceholderText('Select a source key')
            self.sourceKeyComboBox.setCurrentIndex(
                self.sourceKeyComboBox.findText(self.entry.get('sourcekey', '')) or -1
            )
            self.sourceKeyComboBox.currentIndexChanged.connect(self.on_sourcekey_indexchanged)
            enable_source_entry = bool(self.sourceKeyComboBox.currentIndex() == -1)  # enable if no sourcekey selected
            form.addRow('Source Key', self.sourceKeyComboBox)
        elif bool(mode & PseudoColumnEditWidget.SourceDefinition):
            self.sourceKeyEdit = QLineEdit(parent=self)
            self.sourceKeyEdit.setText(self.entry.get('sourcekey'))
            self.sourceKeyEdit.setPlaceholderText('Enter source key')
            self.sourceKeyEdit.textChanged.connect(self.on_sourcekey_textchanged)
            enable_source_entry = True
            form.addRow('Source Key', self.sourceKeyEdit)
        else:
            raise ValueError('Invalid mode selected for source key control initialization')

        # source entry widget
        self.sourceEntry = SourceEntryWidget(self.table, self.entry, self)
        self.sourceEntry.setEnabled(enable_source_entry)
        form.addRow('Source Entry', self.sourceEntry)

        # ...entity checkbox
        self.disableEntityModeCheckbox = QCheckBox('Treat the source as an entity rather than scalar value', parent=self)
        self.disableEntityModeCheckbox.setChecked(not self.entry.get('entity', True))
        self.disableEntityModeCheckbox.clicked.connect(self.on_entity_clicked)
        form.addRow('Entity', self.disableEntityModeCheckbox)

        # ...self_link checkbox
        self.selfLinkCheckbox = QCheckBox('If source is key, switch display mode to self link', parent=self)
        self.selfLinkCheckbox.setChecked(self.entry.get('self_link', False))
        self.selfLinkCheckbox.clicked.connect(self.on_self_link_clicked)
        form.addRow('Self Link', self.selfLinkCheckbox)

        # ...aggregate combobox
        self.aggregateComboBox = QComboBox(parent=self)
        self.aggregateComboBox.setPlaceholderText('Select aggregate function, if desired')
        self.aggregateComboBox.insertItems(0, ['', 'min', 'max', 'cnt', 'cnt_d', 'array', 'array_d'])
        self.aggregateComboBox.setCurrentIndex(
            self.aggregateComboBox.findText(self.entry.get('aggregate', '')) or -1
        )
        self.aggregateComboBox.currentIndexChanged.connect(self.on_aggregate_change)
        form.addRow('Aggregate', self.aggregateComboBox)

        # -- Other attributes --

        # ...markdown name line edit
        self.markdownNameLineEdit = QLineEdit(self.entry.get('markdown_name', ''), parent=self)
        self.markdownNameLineEdit.setPlaceholderText('Enter markdown pattern')
        self.markdownNameLineEdit.textChanged.connect(self.on_markdown_name_change)
        form.addRow('Markdown Name', self.markdownNameLineEdit)

        # ...comment line edit
        self.commentLineEdit = QLineEdit(self.entry.get('comment', ''), parent=self)
        self.commentLineEdit.setPlaceholderText('Enter plain text')
        self.commentLineEdit.textChanged.connect(self.on_comment_change)
        form.addRow('Comment', self.commentLineEdit)

        # ...comment_display combobox
        self.commentDisplayComboBox = QComboBox(parent=self)
        self.commentDisplayComboBox.setPlaceholderText('Select comment display mode')
        self.commentDisplayComboBox.insertItems(0, ['', 'inline', 'tooltip'])
        self.commentDisplayComboBox.setCurrentIndex(
            self.commentDisplayComboBox.findText(self.entry.get('comment_display', '')) or -1
        )
        self.commentDisplayComboBox.currentIndexChanged.connect(self.on_comment_display_change)
        form.addRow('Comment Display', self.commentDisplayComboBox)

        # -- Display attributes --

        # ...markdown display line edit
        self.markdownPatternLineEdit = QTextEdit(display.get('markdown_display', ''), parent=self)
        self.markdownPatternLineEdit.textChanged.connect(self.on_markdown_pattern_change)
        self.markdownPatternLineEdit.setPlaceholderText('Enter markdown pattern')
        self.markdownPatternLineEdit.setText(display.get('markdown_pattern', ''))
        form.addRow('Markdown Display', self.markdownPatternLineEdit)

        # ...template engine
        self.templateEngineComboBox = QComboBox(parent=self)
        self.templateEngineComboBox.addItems(['', 'handlebars', 'mustache'])
        self.templateEngineComboBox.setPlaceholderText('Select a template engine')
        self.templateEngineComboBox.setCurrentIndex(
            self.templateEngineComboBox.findText(display.get('template_engine', '')) or -1
        )
        self.templateEngineComboBox.currentIndexChanged.connect(self.on_template_engine_changed)
        form.addRow('Template Engine', self.templateEngineComboBox)

        # ...wait for widget
        self.waitForWidget = SubsetSelectionWidget(display.get('wait_for', []), sourcekeys, parent=self)
        self.waitForWidget.valueChanged.connect(self.on_wait_for_changed)
        form.addRow('Wait For', self.waitForWidget)

        # ...show_foreign_key_link checkbox
        self.disableForeignKeyLinkCheckBox = QCheckBox('Disable outbound foreign key link', parent=self)
        self.disableForeignKeyLinkCheckBox.setChecked(not display.get('show_foreign_key_link', True))
        self.disableForeignKeyLinkCheckBox.clicked.connect(self.on_show_foreign_key_link_clicked)
        form.addRow('FK Link', self.disableForeignKeyLinkCheckBox)

        # ...array_ux_mode combobox
        self.arrayUXModeComboBox = QComboBox(parent=self)
        self.arrayUXModeComboBox.addItems(['', 'olist', 'ulist', 'csv', 'raw'])
        self.arrayUXModeComboBox.setPlaceholderText('Select a UX mode for aggregate results')
        self.arrayUXModeComboBox.setCurrentIndex(
            self.arrayUXModeComboBox.findText(display.get('array_ux_mode', '')) or -1
        )
        self.arrayUXModeComboBox.currentIndexChanged.connect(self.on_array_ux_mode_changed)
        form.addRow('Array UX Mode', self.arrayUXModeComboBox)

    @pyqtSlot()
    def on_sourcekey_indexchanged(self):
        """Handles changes to the `sourcekey` combobox.
        """
        sourcekey = self.sourceKeyComboBox.currentText()
        if sourcekey:
            self.entry['sourcekey'] = sourcekey
            self.sourceEntry.setEnabled(False)
        else:
            self.sourceEntry.setEnabled(True)
            if 'sourcekey' in self.entry:
                del self.entry['sourcekey']

    @pyqtSlot()
    def on_sourcekey_textchanged(self):
        """Handles changes to the `sourcekey` line edit.
        """
        sourcekey = self.sourceKeyEdit.text()
        if sourcekey:
            self.entry['sourcekey'] = sourcekey
        elif 'sourcekey' in self.entry:
            del self.entry['sourcekey']

    @pyqtSlot()
    def on_entity_clicked(self):
        """Handler for the `entity` checkbox field.
        """
        if self.disableEntityModeCheckbox.isChecked():
            self.entry['entity'] = False
        elif 'entity' in self.entry:
            del self.entry['entity']

    @pyqtSlot()
    def on_self_link_clicked(self):
        """Handles the `self_link` checkbox state.
        """
        if self.selfLinkCheckbox.isChecked():
            self.entry['self_link'] = True
        elif 'self_link' in self.entry:
            del self.entry['self_link']

    @pyqtSlot()
    def on_aggregate_change(self):
        """Handles `aggregates` combobox changes.
        """
        aggregate = self.aggregateComboBox.currentText()
        if aggregate:
            self.entry['aggregate'] = aggregate
        elif 'aggregate' in self.entry:
            del self.entry['aggregate']

    @pyqtSlot()
    def on_markdown_name_change(self):
        """Handles changes to the `markdown_name` field."""

        markdown_name = self.markdownNameLineEdit.text()
        if markdown_name:
            self.entry['markdown_name'] = markdown_name
        elif 'markdown_name' in self.entry:
            del self.entry['markdown_name']

    @pyqtSlot()
    def on_comment_change(self):
        """Handles changes to the `comment` field."""

        comment = self.commentLineEdit.text()
        if comment:
            self.entry['comment'] = comment
        elif 'comment' in self.entry:
            del self.entry['comment']

    @pyqtSlot()
    def on_comment_display_change(self):
        """Handles changes to the `comment_display` combobox.
        """
        comment_display = self.commentDisplayComboBox.currentText()
        if comment_display:
            self.entry['comment_display'] = comment_display
        elif 'comment_display' in self.entry:
            del self.entry['comment_display']

    def _set_display_value(self, cond: bool, key: str, value):
        """Conditionally, set the value of the display property or erase it from pseudo-column entry.

        :param cond: indicates if the key should be set to the value or dropped from the display dictionary
        :param key: display dictionary key (i.e., 'wait_for')
        :param value: valid value for the key
        """
        display = self.entry.get('display', {})

        # set or delete value
        if cond:
            display[key] = value
        elif key in display:
            del display[key]

        # update or delete display
        if display:
            self.entry['display'] = display
        elif 'display' in self.entry:
            del self.entry['display']

    @pyqtSlot()
    def on_markdown_pattern_change(self):
        """Handles changes to the `markdown_pattern` text field.
        """
        markdown_pattern = self.markdownPatternLineEdit.toPlainText()
        self._set_display_value(
            bool(markdown_pattern),
            'markdown_pattern',
            markdown_pattern
        )

    @pyqtSlot()
    def on_template_engine_changed(self):
        """Handles changes to the `template_engine` combobox.
        """
        template_engine = self.templateEngineComboBox.currentText()
        self._set_display_value(
            template_engine in ['handlebars', 'mustache'],
            'template_engine',
            template_engine
        )

    @pyqtSlot()
    def on_wait_for_changed(self):
        """Handles changes to the `wait_for` widget.
        """
        wait_for = self.waitForWidget.selected_values
        self._set_display_value(
            bool(wait_for),
            'wait_for',
            wait_for
        )

    @pyqtSlot()
    def on_show_foreign_key_link_clicked(self):
        """Handles `show_foreign_key_link` changes.
        """
        show_foreign_key_link = not self.disableForeignKeyLinkCheckBox.isChecked()
        self._set_display_value(
            not show_foreign_key_link,
            'show_foreign_key_link',
            show_foreign_key_link
        )

    @pyqtSlot()
    def on_array_ux_mode_changed(self):
        """Handles changes to the `array_ux_mode`.
        """
        array_ux_mode = self.arrayUXModeComboBox.currentText()
        self._set_display_value(
            array_ux_mode != '',
            'array_ux_mode',
            array_ux_mode
        )


class SourceEntryWidget(QWidget):
    """Source entry widget.
    """

    table: _erm.Table
    entry: dict

    def __init__(self, table: _erm.Table, entry: dict, parent: QWidget = None):
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
        source = self.entry['source']
        if isinstance(source, str):
            self.entry['source'] = source = [source]
        elif isinstance(source, list) and len(source) == 2 and all(isinstance(item, str) for item in source):
            self.entry['source'] = source = [{'outbound': source}]

        # populate source list widget and update context
        validated_path = []
        try:
            for item in source:
                # update the context, based on the type of source component
                if isinstance(item, str):
                    # case: column name
                    column = {col.name: col for col in self.context[-1].columns}[item]
                    self.context.append(column)
                elif 'outbound' in item:
                    # case: outbound fkey
                    fkey = self.table.schema.model.fkey(item['outbound'])
                    self.context.append(fkey.pk_table)
                else:
                    # case: inbound fkey
                    assert 'inbound' in item
                    fkey = self.table.schema.model.fkey(item['inbound'])
                    self.context.append(fkey.table)
                # update the source list
                self.sourceList.addItem(source_component_to_str(item))
                validated_path.append(item)
        except KeyError as e:
            logger.error("Invalid path component %s found in source entry %s" % (str(e), str(source)))
            self.entry['source'] = validated_path  # set source to the valid partial path

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
                userData={'outbound': fkey}
            )
        for ref in table.referenced_by:
            self.availableSource.addItem(
                "%s:%s (inbound)" % tuple(constraint_name(ref)),
                userData={'inbound': ref}
            )

    @pyqtSlot()
    def on_push(self):
        """Handler for pushing a path element onto the source entry."""
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
            self.entry['source'].append(data.name)
        elif 'outbound' in data:
            fkey = data['outbound']
            assert isinstance(fkey, _erm.ForeignKey)
            context = fkey.pk_table
            self._updateAvailableSourcesFromTable(context)
            self.entry['source'].append({
                'outbound': constraint_name(fkey)
            })
        else:
            fkey = data['inbound']
            assert isinstance(fkey, _erm.ForeignKey)
            context = fkey.table
            self._updateAvailableSourcesFromTable(context)
            self.entry['source'].append({
                'inbound': constraint_name(fkey)
            })

        # update control state
        self.context.append(context)
        self.popButton.setEnabled(True)

    @pyqtSlot()
    def on_pop(self):
        """Handler for popping the top path element of a source entry."""

        # update source list
        self.sourceList.takeItem(len(self.sourceList)-1)

        # update entry source
        if self.entry['source']:
            self.entry['source'].pop()
            self.context.pop()
            self._updateAvailableSourcesFromTable(self.context[-1])

        # update control state
        self.availableSource.setEnabled(True)
        self.pushButton.setEnabled(True)
        self.popButton.setEnabled(len(self.entry['source']) > 0)