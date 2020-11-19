"""Visible-Columns annotation editor."""
from copy import deepcopy

from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFrame, QWidget, QTableView, QComboBox, QFormLayout, \
    QPushButton, QGroupBox, QHBoxLayout, QTabWidget, QLineEdit, QDialog, QButtonGroup, QRadioButton, \
    QCheckBox, QListWidget, QHeaderView, QDialogButtonBox
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, pyqtSlot

from deriva.core import tag, ermrest_model as _erm


def _constraint_name(constraint):
    """Returns the annotation-friendly form of the constraint name."""
    return [constraint.constraint_schema.name if constraint.constraint_schema else '', constraint.constraint_name]


class VisibleColumnsEditor(QWidget):
    """Visible columns annotation editor."""

    def __init__(self, data):
        super(VisibleColumnsEditor, self).__init__()
        assert data and isinstance(data, dict) and 'parent' in data
        self.table = data['parent']
        assert isinstance(self.table, _erm.Table)
        self.body = self.table.annotations[tag.visible_columns]

        # create tabs for each context
        self.tabs = QTabWidget()
        for context in self.body:
            if context == 'filter':
                contents = self.body[context].get('and', [])
            else:
                contents = self.body[context]
            tab = VisibleColumnsContextEditor(self.table, context, contents, self.on_remove_context)
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
        tab = VisibleColumnsContextEditor(self.table, context, contents, self.on_remove_context)
        self.tabs.insertTab(len(self.tabs)-1, tab, context)


class VisibleColumnsContextEditor(QWidget):
    """Editor for the visible columns context."""

    @staticmethod
    def _entry2row(entry):
        """Converts a visible columns entry into a tuple for use in the table model."""

        if isinstance(entry, str):
            return (
                'Column',
                entry,
                ''
            )
        elif isinstance(entry, list):
            assert len(entry) == 2
            return (
                'Constraint',
                entry[1],
                ''
            )
        else:
            assert isinstance(entry, dict)
            return (
                'Pseudo',
                str(entry.get('source', entry.get('sourcekey', 'virtual'))),
                str(entry)
            )

    class TableModel(QAbstractTableModel):
        """Internal table model for a context."""

        def __init__(self, body):
            super(VisibleColumnsContextEditor.TableModel, self).__init__()
            self.headers = ["Type", "Source", "Additional Details"]
            self.rows = [
                VisibleColumnsContextEditor._entry2row(entry) for entry in body
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

    def __init__(self, table, context, body, on_remove_context):
        """Initialize the VisibleColumnsContextEditor."""
        super(VisibleColumnsContextEditor, self).__init__()
        self.table, self.context, self.body, self.on_remove_context = table, context, body, on_remove_context

        # table view
        self.model = model = VisibleColumnsContextEditor.TableModel(body)
        self.tableView = tableView = QTableView()
        tableView.setModel(model)
        tableView.setWordWrap(True)

        # controls frame
        controls = QFrame()
        hlayout = QHBoxLayout()
        # ...add column button
        addColumn = QPushButton('+', parent=controls)
        addColumn.clicked.connect(self.on_add_vizcol_click)
        hlayout.addWidget(addColumn)
        # ...remove column button
        self.removeColumn = QPushButton('-', parent=controls)
        self.removeColumn.clicked.connect(self.on_remove_vizcol_click)
        hlayout.addWidget(self.removeColumn)
        # ...duplicate column button
        self.duplicateColumn = QPushButton('dup', parent=controls)
        self.duplicateColumn.clicked.connect(self.on_duplicate_vizcol_click)
        hlayout.addWidget(self.duplicateColumn)
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
        layout.addWidget(tableView)
        layout.addWidget(controls)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        # table selection change
        self.tableView.clicked.connect(self.on_click)
        self.tableView.doubleClicked.connect(self.on_doubleclick)

        # table view styling
        self.tableView.setAlternatingRowColors(True)
        for index in [1, 2]:
            self.tableView.horizontalHeader().setSectionResizeMode(index, QHeaderView.Stretch)

    @pyqtSlot()
    def on_add_vizcol_click(self):
        """Handler for adding visible column."""

        dialog = VisibleColumnDialog(self.table, allow_pseudocolumns=(self.context != 'entry'))
        code = dialog.exec_()
        if code == QDialog.Accepted:
            assert isinstance(self.body, list)
            self.body.append(dialog.entry)
            self.tableView.setModel(
                VisibleColumnsContextEditor.TableModel(self.body)
            )

    @pyqtSlot()
    def on_duplicate_vizcol_click(self):
        """Handler for duplicating visible column."""

        assert isinstance(self.body, list)
        index = self.tableView.currentIndex().row()
        if index >= 0:
            duplicate = deepcopy(self.body[index])
            print(duplicate)
            self.body.append(duplicate)
            self.tableView.setModel(
                VisibleColumnsContextEditor.TableModel(self.body)
            )

    @pyqtSlot()
    def on_remove_vizcol_click(self):
        """Handler for removing a visible column."""

        assert isinstance(self.body, list)
        index = self.tableView.currentIndex().row()
        if index >= 0:
            del self.body[index]
            self.tableView.setModel(
                VisibleColumnsContextEditor.TableModel(self.body)
            )
            index = index if index < len(self.body) else index - 1
            self.tableView.selectRow(index)

    @pyqtSlot()
    def on_move_up_click(self):
        """Handler for reordering (up) a visible column."""

        assert isinstance(self.body, list)
        i = self.tableView.currentIndex().row()
        if i > 0:
            temp = self.body[i]
            del self.body[i]
            self.body.insert(i-1, temp)
            self.tableView.setModel(
                VisibleColumnsContextEditor.TableModel(self.body)
            )
            self.tableView.selectRow(i - 1)

    @pyqtSlot()
    def on_move_down_click(self):
        """Handler for reordering (down) a visible column."""

        assert isinstance(self.body, list)
        i = self.tableView.currentIndex().row()
        if -1 < i < len(self.body)-1:
            temp = self.body[i]
            del self.body[i]
            self.body.insert(i+1, temp)
            self.tableView.setModel(
                VisibleColumnsContextEditor.TableModel(self.body)
            )
            self.tableView.selectRow(i + 1)

    @pyqtSlot()
    def on_doubleclick(self):
        """Handler for double-click event on a visible-column which opens the editor dialog."""

        assert isinstance(self.body, list)
        i = self.tableView.currentIndex().row()
        dialog = VisibleColumnDialog(self.table, entry=self.body[i], allow_pseudocolumns=(self.context != 'entry'))
        code = dialog.exec_()
        if code == QDialog.Accepted:
            self.body[i] = dialog.entry
            self.tableView.setModel(
                VisibleColumnsContextEditor.TableModel(self.body)
            )

    @pyqtSlot()
    def on_click(self):
        """Handler for click event on a visible-column which records its index for use in combination with other commands."""

        idx = self.tableView.currentIndex()
        # todo: enable/disable the up/down/- buttons


class VisibleColumnDialog(QDialog):
    """Dialog for editing or defining a visible column entry."""

    COLUMN, CONSTRAINT, PSEUDO = 'Column', 'Constraint', 'Pseudo-Column'

    def __init__(self, table, entry=None, allow_pseudocolumns=True):
        """Init the dialog.

        :param table: the ERMrest table model object that contains the entry
        :param entry: a visible column entry
        """
        super(VisibleColumnDialog, self).__init__()
        assert isinstance(table, _erm.Table)
        self.table = table
        self.entry = entry
        self.allow_pseudocolumns = allow_pseudocolumns

        self.setWindowTitle(("Edit" if entry else "Add") + " Visible Column Entry")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the type of visible column and complete its details."))

        # ...setup button group for radio buttons
        self.buttonGroup = buttonGroup = QButtonGroup(self)
        buttonGroup.buttonClicked.connect(self.on_buttonGroup_clicked)

        # ...column
        enabled = entry is None or isinstance(entry, str)
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

        # ...constraint
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
        # ...add keys
        for key in self.table.keys:
            if self.entry == _constraint_name(key):
                match = index
            combo.addItem(
                key.constraint_name,
                key
            )
            index += 1
        # ...add fkeys
        for fkey in self.table.foreign_keys:
            if self.entry == _constraint_name(fkey):
                match = index
            combo.addItem(
                fkey.constraint_name,
                fkey
            )
            index += 1
        # ...set curr index if match
        if match > -1:
            self.constraintCombo.setCurrentIndex(match)
        group.layout().addWidget(combo)
        group.setEnabled(enabled)

        # ...pseudo
        enabled = self.allow_pseudocolumns and isinstance(entry, dict)
        radioPseudo = QRadioButton(self.PSEUDO)
        radioPseudo.setChecked(enabled)
        radioPseudo.setEnabled(self.allow_pseudocolumns)
        buttonGroup.addButton(radioPseudo)
        layout.addWidget(radioPseudo)

        # ...pseudo group controls
        self.pseudoGroup = group = PseudoColumnEditWidget(self.table, self.entry, parent=self)
        layout.addWidget(group)
        group.setEnabled(enabled)

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

        return super(VisibleColumnDialog, self).accept()

    @pyqtSlot()
    def on_buttonGroup_clicked(self):
        """Handler for radio button selection: column, constraint, pseudo-column."""

        selected = self.buttonGroup.checkedButton().text()
        if selected == self.COLUMN:
            self.columnGroup.setEnabled(True)
            self.constraintGroup.setEnabled(False)
            self.pseudoGroup.setEnabled(False)
        elif selected == self.CONSTRAINT:
            self.columnGroup.setEnabled(False)
            self.constraintGroup.setEnabled(True)
            self.pseudoGroup.setEnabled(False)
        else:
            self.columnGroup.setEnabled(False)
            self.constraintGroup.setEnabled(False)
            self.pseudoGroup.setEnabled(True)


class PseudoColumnEditWidget(QGroupBox):
    """Pseudo-column edit widget."""

    def __init__(self, table, entry, parent=None):
        super(PseudoColumnEditWidget, self).__init__(parent=parent)
        self.table, self.entry = table, entry
        self.context = [table]

        # ...initialize entry if not starting from an existing pseudo-column
        if self.entry is None or not isinstance(self.entry, dict):
            self.entry = {
                'source': []
            }
        elif 'source' not in self.entry:
            # ...add blank source, if none found... will clean this up later, if not used
            self.entry['source'] = []

        # ...use form layout
        form = QFormLayout()

        # ...markdown name line edit
        self.markdownLineEdit = QLineEdit(self.entry.get('markdown_name', ''), parent=self)
        self.markdownLineEdit.textChanged.connect(self.on_markdown_name_change)
        form.addRow('Markdown Name', self.markdownLineEdit)

        # ...entity checkbox
        self.entityCheckbox = QCheckBox(parent=self)
        self.entityCheckbox.setChecked(self.entry.get('entity', False))
        self.entityCheckbox.clicked.connect(self.on_entity_clicked)
        form.addRow('Entity', self.entityCheckbox)

        # ...source list widget
        source = QWidget(self)
        sourceLayout = QVBoxLayout(self)
        sourceLayout.setContentsMargins(0, 0, 0, 0)
        self.sourceList = QListWidget(parent=self)
        sourceLayout.addWidget(self.sourceList)

        # ...populate source list and update context
        for item in self.entry['source']:
            self.sourceList.addItem(self._source2str(item))
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

        # ...available sources combobox
        self.availableSource = QComboBox(parent=self)
        context = self.context[-1]
        if isinstance(context, _erm.Table):
            self._updateAvailableSourcesFromTable(context)
        sourceLayout.addWidget(self.availableSource)

        # ...setup source push and pop buttons
        controls = QWidget(self)
        controls.setLayout(QHBoxLayout(controls))
        controls.layout().setContentsMargins(0, 0, 0, 5)
        # ...push button
        self.pushButton = QPushButton('push')
        self.pushButton.setEnabled(len(self.availableSource) > 0)  # disable if not sources (lik
        self.pushButton.clicked.connect(self.on_push)
        controls.layout().addWidget(self.pushButton)
        # ...pop button
        self.popButton = QPushButton('pop')
        self.popButton.clicked.connect(self.on_pop)
        controls.layout().addWidget(self.popButton)
        # ...add remaining controls to form
        sourceLayout.addWidget(controls)
        source.setLayout(sourceLayout)
        form.addRow('Source', source)

        self.setLayout(form)

    @classmethod
    def _source2str(cls, source):
        """Readable string from source entry."""

        return (
            source if isinstance(source, str) else
            '%s:%s (inbound)' % tuple(source['inbound']) if 'inbound' in source else
            '%s:%s (outbound)' % tuple(source['outbound']) if 'outbound' in source else
            '<<unexpected entry>>'
        )

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
    def on_markdown_name_change(self):
        """Handles changes to the `markdown_name` field."""

        markdown_name = self.markdownLineEdit.text()
        if markdown_name:
            self.entry['markdown_name'] = markdown_name
        elif 'markdown_name' in self.entry:
            del self.entry['markdown_name']

    @pyqtSlot()
    def on_entity_clicked(self):
        """Handler for the `entity` checkbox field."""

        self.entry['entity'] = self.entityCheckbox.isChecked()

    @pyqtSlot()
    def on_push(self):
        """Handler for pushing a path element onto the source entry."""

        # update the source list display
        self.sourceList.addItem(
            self.availableSource.currentText()
        )

        # update the available sources, source entry, and append to the context
        data = self.availableSource.currentData()
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
