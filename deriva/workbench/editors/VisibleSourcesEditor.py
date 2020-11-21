"""Visible-Columns annotation editor."""
from copy import deepcopy
import logging

from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFrame, QWidget, QTableView, QComboBox, QFormLayout, \
    QPushButton, QGroupBox, QHBoxLayout, QTabWidget, QLineEdit, QDialog, QButtonGroup, QRadioButton, \
    QCheckBox, QListWidget, QHeaderView, QDialogButtonBox, QListWidgetItem, QTextEdit
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, pyqtSlot, pyqtSignal

from deriva.core import tag as _tag, ermrest_model as _erm


logger = logging.getLogger(__name__)


def _constraint_name(constraint):
    """Returns the annotation-friendly form of the constraint name.
    """
    return [constraint.constraint_schema.name if constraint.constraint_schema else '', constraint.constraint_name]


def _source_component_to_str(component):
    """Readable string representation of a `source` path component.
    """
    return (
        component if isinstance(component, str) else
        '%s:%s (inbound)' % tuple(component['inbound']) if 'inbound' in component else
        '%s:%s (outbound)' % tuple(component['outbound']) if 'outbound' in component else
        '%s <<unexpected structure>>' % component
    )

def _source_path_to_str(source):
    """Readable string representation of a `source` path.
    """
    if isinstance(source, str):
        return source
    elif isinstance(source, list) and all(isinstance(elem, str) for elem in source):
        return source[1]
    else:
        return ' > '.join(_source_component_to_str(component) for component in source)


class VisibleSourcesEditor(QWidget):
    """Visible sources (column or foreign key) annotation editor.
    """

    table: _erm.Table
    tag: str

    def __init__(self, table, tag):
        """Initialize visible sources editor.
        """
        super(VisibleSourcesEditor, self).__init__()
        assert isinstance(table, _erm.Table)
        self.table, self.tag = table, tag
        self.body = self.table.annotations[tag]

        # create tabs for each context
        self.tabs = QTabWidget()
        for context in self.body:
            if context == 'filter':
                contents = self.body[context].get('and', [])
            else:
                contents = self.body[context]
            tab = VisibleSourcesContextEditor(self.table, self.tag, context, contents, self.on_remove_context)
            self.tabs.addTab(tab, context)

        # tab for creating a new context
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel('New Context Name:'))
        # ...context line editor
        self.line = QLineEdit()
        self.line.textChanged.connect(self.on_context_line_edit_change)
        layout.addWidget(self.line)
        # ...add context button
        self.addContext = QPushButton('Add')
        self.addContext.setEnabled(False)
        self.addContext.clicked.connect(self.on_add_context)
        layout.addWidget(self.addContext)
        tab = QWidget()
        tab.setLayout(layout)
        tab.setAutoFillBackground(True)
        self.tabs.addTab(tab, "+")

        # add tabs to layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

    @pyqtSlot()
    def on_remove_context(self):
        index = self.tabs.currentIndex()
        context = self.tabs.currentWidget().context
        self.tabs.removeTab(index)
        del self.body[context]

    @pyqtSlot()
    def on_context_line_edit_change(self):
        context = self.line.text()
        if context not in self.body:
            self.addContext.setEnabled(True)
        else:
            self.addContext.setEnabled(False)

    @pyqtSlot()
    def on_add_context(self):
        context = self.line.text()
        self.line.clear()
        self.addContext.setEnabled(False)
        if context == 'filter':
            self.body[context] = {'and': []}
            contents = self.body[context]['and']
        else:
            self.body[context] = []
            contents = self.body[context]
        tab = VisibleSourcesContextEditor(self.table, self.tag, context, contents, self.on_remove_context)
        self.tabs.insertTab(len(self.tabs)-1, tab, context)


class VisibleSourcesContextEditor(QWidget):
    """Editor for the visible sources context.
    """

    @staticmethod
    def _entry2row(entry):
        """Converts a visible sources entry into a tuple for use in the table model."""

        if isinstance(entry, str):
            return (
                'Column',
                entry
            )
        elif isinstance(entry, list):
            assert len(entry) == 2
            return (
                'Constraint',
                entry[1]
            )
        else:
            assert isinstance(entry, dict)
            return (
                'Pseudo',
                _source_path_to_str(entry.get('source', entry.get('sourcekey', 'virtual')))
            )

    class TableModel(QAbstractTableModel):
        """Internal table model for a context."""

        def __init__(self, body):
            super(VisibleSourcesContextEditor.TableModel, self).__init__()
            self.headers = ["Type", "Source"]
            self.rows = [
                VisibleSourcesContextEditor._entry2row(entry) for entry in body
            ]

        def rowCount(self, parent):
            return len(self.rows)

        def columnCount(self, parent):
            return len(self.headers)

        def data(self, index, role):
            if role != Qt.DisplayRole:
                return QVariant()
            return self.rows[index.row()][index.column()]

        def headerData(self, section, orientation, role):
            if role != Qt.DisplayRole or orientation != Qt.Horizontal:
                return QVariant()
            return self.headers[section]

    table: _erm.Table
    context: str
    body: dict

    def __init__(self, table, tag, context, body, on_remove_context):
        """Initialize the VisibleSourcesContextEditor.
        """
        super(VisibleSourcesContextEditor, self).__init__()
        self.table, self.context, self.body, self.on_remove_context = table, context, body, on_remove_context

        # add/edit mode
        if tag == _tag.visible_columns:
            self.mode = VisibleSourceDialog.VisibleColumns
            if self.context == 'entry':
                self.mode &= ~VisibleSourceDialog.AllowPseudoColumn
        else:
            self.mode = VisibleSourceDialog.VisibleForeignKeys

        # table view
        self.model = model = VisibleSourcesContextEditor.TableModel(body)
        self.tableView = QTableView(parent=self)
        self.tableView.setModel(model)

        # ...table selection change
        self.tableView.clicked.connect(self.on_click)
        self.tableView.doubleClicked.connect(self.on_doubleclick)

        # ...table view styling
        self.tableView.setWordWrap(True)
        self.tableView.setAlternatingRowColors(True)
        self.tableView.horizontalHeader().setStretchLastSection(True)

        # controls frame
        controls = QFrame()
        hlayout = QHBoxLayout()
        # ...add column button
        addSource = QPushButton('+', parent=controls)
        addSource.clicked.connect(self.on_add_click)
        hlayout.addWidget(addSource)
        # ...remove column button
        self.removeSource = QPushButton('-', parent=controls)
        self.removeSource.clicked.connect(self.on_remove_click)
        hlayout.addWidget(self.removeSource)
        # ...duplicate column button
        self.duplicateSource = QPushButton('dup', parent=controls)
        self.duplicateSource.clicked.connect(self.on_duplicate_click)
        hlayout.addWidget(self.duplicateSource)
        # ...move up button
        self.moveUp = QPushButton('up', parent=controls)
        self.moveUp.clicked.connect(self.on_move_up_click)
        hlayout.addWidget(self.moveUp)
        # ...move down button
        self.moveDown = QPushButton('down', parent=controls)
        self.moveDown.clicked.connect(self.on_move_down_click)
        hlayout.addWidget(self.moveDown)
        # ...remove context button
        removeContext = QPushButton('- context', parent=controls)
        removeContext.clicked.connect(self.on_remove_context)
        hlayout.addWidget(removeContext)
        controls.setLayout(hlayout)

        # tab layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.tableView)
        layout.addWidget(controls)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

    @pyqtSlot()
    def on_add_click(self):
        """Handler for adding visible source."""

        dialog = VisibleSourceDialog(self.table, mode=self.mode)
        code = dialog.exec_()
        if code == QDialog.Accepted:
            assert isinstance(self.body, list)
            self.body.append(dialog.entry)
            self.tableView.setModel(
                VisibleSourcesContextEditor.TableModel(self.body)
            )

    @pyqtSlot()
    def on_duplicate_click(self):
        """Handler for duplicating visible source."""

        assert isinstance(self.body, list)
        index = self.tableView.currentIndex().row()
        if index >= 0:
            duplicate = deepcopy(self.body[index])
            self.body.append(duplicate)
            self.tableView.setModel(
                VisibleSourcesContextEditor.TableModel(self.body)
            )

    @pyqtSlot()
    def on_remove_click(self):
        """Handler for removing a visible source."""

        assert isinstance(self.body, list)
        index = self.tableView.currentIndex().row()
        if index >= 0:
            del self.body[index]
            self.tableView.setModel(
                VisibleSourcesContextEditor.TableModel(self.body)
            )
            index = index if index < len(self.body) else index - 1
            self.tableView.selectRow(index)

    @pyqtSlot()
    def on_move_up_click(self):
        """Handler for reordering (up) a visible source."""

        assert isinstance(self.body, list)
        i = self.tableView.currentIndex().row()
        if i > 0:
            temp = self.body[i]
            del self.body[i]
            self.body.insert(i-1, temp)
            self.tableView.setModel(
                VisibleSourcesContextEditor.TableModel(self.body)
            )
            self.tableView.selectRow(i - 1)

    @pyqtSlot()
    def on_move_down_click(self):
        """Handler for reordering (down) a visible source."""

        assert isinstance(self.body, list)
        i = self.tableView.currentIndex().row()
        if -1 < i < len(self.body)-1:
            temp = self.body[i]
            del self.body[i]
            self.body.insert(i+1, temp)
            self.tableView.setModel(
                VisibleSourcesContextEditor.TableModel(self.body)
            )
            self.tableView.selectRow(i + 1)

    @pyqtSlot()
    def on_doubleclick(self):
        """Handler for double-click event on a visible-source which opens the editor dialog."""

        assert isinstance(self.body, list)
        i = self.tableView.currentIndex().row()
        dialog = VisibleSourceDialog(self.table, entry=deepcopy(self.body[i]), mode=self.mode)
        code = dialog.exec_()
        if code == QDialog.Accepted:
            self.body[i] = dialog.entry
            self.tableView.setModel(
                VisibleSourcesContextEditor.TableModel(self.body)
            )

    @pyqtSlot()
    def on_click(self):
        """Handler for click event on a visible-source which records its index for use in combination with other commands."""

        idx = self.tableView.currentIndex()
        # todo: enable/disable the up/down/- buttons


class VisibleSourceDialog(QDialog):
    """Dialog for editing or defining a visible source entry."""

    COLUMN, CONSTRAINT, PSEUDO = 'Column', 'Constraint', 'Pseudo-Column'

    AllowColumn, AllowPrimaryKey, AllowInboundForeignKey, AllowOutboundForeignKey, AllowPseudoColumn = 1, 2, 4, 8, 16
    AllowAll = AllowColumn | AllowPrimaryKey | AllowOutboundForeignKey | AllowInboundForeignKey | AllowPseudoColumn
    VisibleColumns = AllowColumn | AllowPrimaryKey | AllowOutboundForeignKey | AllowPseudoColumn
    VisibleForeignKeys = AllowInboundForeignKey | AllowPseudoColumn

    def __init__(self, table, entry=None, mode=AllowAll):
        """Init the dialog.

        :param table: the ERMrest table model object that contains the entry
        :param entry: a visible source entry
        """
        super(VisibleSourceDialog, self).__init__()
        assert isinstance(table, _erm.Table)
        self.table = table
        self.entry = entry
        self.mode = mode

        self.setWindowTitle(("Edit" if entry else "Add") + " Visible Source Entry")
        self.setMinimumWidth(640)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the type of visible source and complete its details."))

        # ...setup button group for radio buttons
        self.buttonGroup = buttonGroup = QButtonGroup(self)
        buttonGroup.buttonClicked.connect(self.on_buttonGroup_clicked)

        # ...collection of all control groups
        self.controlGroups = []

        # ...column
        if bool(mode & VisibleSourceDialog.AllowColumn):
            enabled = isinstance(entry, str)
            radioColumn = QRadioButton(self.COLUMN)
            radioColumn.setChecked(enabled)
            buttonGroup.addButton(radioColumn)
            layout.addWidget(radioColumn)

            # ...column group controls
            self.columnGroup = group = QFrame(parent=self)
            group.setLayout(QVBoxLayout(group))
            layout.addWidget(group)
            match = -1  # keep track of index and update currIndex if match found
            index = 0
            self.columnCombo = combo = QComboBox(group)
            for column in self.table.columns:
                if self.entry == column.name:
                    match = index
                combo.addItem(
                    column.name,
                    column
                )
                index += 1
            # ...set curr index if match
            if match > -1:
                self.columnCombo.setCurrentIndex(match)
            group.layout().addWidget(combo)
            group.setEnabled(enabled)
            self.controlGroups.append(group)

        # ...constraint
        if bool(mode & (
                VisibleSourceDialog.AllowPrimaryKey |
                VisibleSourceDialog.AllowInboundForeignKey |
                VisibleSourceDialog.AllowOutboundForeignKey)):

            enabled = isinstance(entry, list)
            radioConstraint = QRadioButton(self.CONSTRAINT)
            radioConstraint.setChecked(enabled)
            buttonGroup.addButton(radioConstraint)
            layout.addWidget(radioConstraint)

            # ...constraint group controls
            self.constraintGroup = group = QFrame(parent=self)
            group.setLayout(QVBoxLayout(group))
            layout.addWidget(group)
            match = -1  # keep track of index and update currIndex if match found
            index = 0
            self.constraintCombo = combo = QComboBox(group)

            # ...add constraints
            for (allowed, constraints) in [
                (VisibleSourceDialog.AllowPrimaryKey, self.table.keys),
                (VisibleSourceDialog.AllowOutboundForeignKey, self.table.foreign_keys),
                (VisibleSourceDialog.AllowInboundForeignKey, self.table.referenced_by)
            ]:
                if bool(mode & allowed):
                    for constraint in constraints:
                        if self.entry == _constraint_name(constraint):
                            match = index
                        combo.addItem(
                            constraint.constraint_name,
                            constraint
                        )
                        index += 1

            # ...set curr index if match
            if match > -1:
                self.constraintCombo.setCurrentIndex(match)

            group.layout().addWidget(combo)
            group.setEnabled(enabled)
            self.controlGroups.append(group)

        # ...pseudo
        if bool(mode & VisibleSourceDialog.AllowPseudoColumn):
            enabled = isinstance(entry, dict)
            radioPseudo = QRadioButton(self.PSEUDO)
            radioPseudo.setChecked(enabled)
            radioPseudo.setEnabled(True)
            buttonGroup.addButton(radioPseudo)
            layout.addWidget(radioPseudo)

            # ...pseudo group controls
            self.pseudoGroup = group = PseudoColumnEditWidget(self.table, self.entry, parent=self)
            layout.addWidget(group)
            group.setEnabled(enabled)
            self.controlGroups.append(group)

        # ...ok/cancel
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

        self.setLayout(layout)
        
    @pyqtSlot()
    def accept(self):
        """Dialog 'accept' handler."""

        selected = self.buttonGroup.checkedButton().text()
        if selected == self.COLUMN:
            data = self.columnCombo.currentData()
            assert isinstance(data, _erm.Column)
            self.entry = data.name
        elif selected == self.CONSTRAINT:
            data = self.constraintCombo.currentData()
            assert isinstance(data, _erm.Key) or isinstance(data, _erm.ForeignKey)
            self.entry = _constraint_name(data)
        else:
            # update the original entry, if any
            if not isinstance(self.entry, dict):
                self.entry = {}
            self.entry.update(self.pseudoGroup.entry)
            # ...cleanup an empty source entry
            if 'source' in self.entry and len(self.entry['source']) == 0:
                del self.entry['source']

        return super(VisibleSourceDialog, self).accept()

    @pyqtSlot()
    def on_buttonGroup_clicked(self):
        """Handler for radio button selection: column, constraint, pseudo-column."""

        # disable all
        for group in self.controlGroups:
            group.setEnabled(False)

        # enable currently selected
        selected = self.buttonGroup.checkedButton().text()
        if selected == self.COLUMN:
            self.columnGroup.setEnabled(True)
        elif selected == self.CONSTRAINT:
            self.constraintGroup.setEnabled(True)
        else:
            self.pseudoGroup.setEnabled(True)


class PseudoColumnEditWidget(QGroupBox):
    """Pseudo-column edit widget.
    """

    table: _erm.Table
    entry: dict

    def __init__(self, table, entry, parent=None):
        """Initialize the pseudo-column editor widget.

        :param table: the ermrest_model.Table instance that contains this pseudo-column
        :param entry: the pseudo-column entry (can take many forms)
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
        self.sourceKeyComboBox = QComboBox(parent=self)
        self.sourceKeyComboBox.addItem('')
        self.sourceKeyComboBox.addItems(sourcekeys)
        self.sourceKeyComboBox.setPlaceholderText('Select a source key')
        self.sourceKeyComboBox.setCurrentIndex(
            self.sourceKeyComboBox.findText(display.get('sourcekey', '')) or -1
        )
        self.sourceKeyComboBox.currentIndexChanged.connect(self.on_sourcekey_changed)
        form.addRow('Source Key', self.sourceKeyComboBox)

        # source entry widget
        self.sourceEntry = SourceEntryWidget(self.table, self.entry, self)
        self.sourceEntry.setEnabled(bool(self.sourceKeyComboBox.currentIndex() == -1))  # enable if no sourcekey selected
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
        self.waitForWidget = WaitForWidget(
            display.get('wait_for', []),
            sourcekeys,
            self
        )
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
    def on_sourcekey_changed(self):
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
        wait_for = self.waitForWidget.value
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
                self.sourceList.addItem(_source_component_to_str(item))
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
                "%s:%s (outbound)" % tuple(_constraint_name(fkey)),
                userData={'outbound': fkey}
            )
        for ref in table.referenced_by:
            self.availableSource.addItem(
                "%s:%s (inbound)" % tuple(_constraint_name(ref)),
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
                'outbound': _constraint_name(fkey)
            })
        else:
            fkey = data['inbound']
            assert isinstance(fkey, _erm.ForeignKey)
            context = fkey.table
            self._updateAvailableSourcesFromTable(context)
            self.entry['source'].append({
                'inbound': _constraint_name(fkey)
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


class WaitForWidget(QListWidget):
    """Widget for manipulating `wait_for` lists of source keys.
    """

    value: list[str]
    valueChanged = pyqtSignal()

    def __init__(self, value: list[str], sourcekeys: list[str], parent: QWidget):
        """Initialize the widget.

        :param value: list of selected sourcekeys
        :param sourcekeys: list of available sourcekeys
        :param parent: parent widget
        """
        super(WaitForWidget, self).__init__(parent=parent)
        self.value = value

        self.setSortingEnabled(True)
        for sourcekey in sourcekeys:
            item = QListWidgetItem(sourcekey)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if sourcekey in value else Qt.Unchecked)
            self.addItem(item)
        self.itemClicked.connect(self._on_item_clicked)

    @pyqtSlot()
    def _on_item_clicked(self):
        """Handles changes to the `value` list.
        """
        self.value.clear()
        for row in range(self.count()):
            item = self.item(row)
            if item.checkState():
                self.value.append(item.text())

        self.valueChanged.emit()
