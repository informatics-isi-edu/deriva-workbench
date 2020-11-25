"""Visible-Sources annotation editor.
"""
from copy import deepcopy
import logging
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFrame, QWidget, QTableView, QComboBox, QPushButton, QHBoxLayout, \
    QDialog, QButtonGroup, QRadioButton, QDialogButtonBox
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, pyqtSlot
from deriva.core import tag as _tag, ermrest_model as _erm
from .common import constraint_name, source_path_to_str
from .tabbed_contexts import TabbedContextsWidget
from .pseudo_column import PseudoColumnEditWidget

logger = logging.getLogger(__name__)


class VisibleSourcesEditor(TabbedContextsWidget):
    """Visible sources (column or foreign key) annotation editor.
    """

    table: _erm.Table
    tag: str

    def __init__(self, table, tag, parent: QWidget = None):
        """Initialize visible sources editor.
        """
        super(VisibleSourcesEditor, self).__init__(parent=parent)
        assert isinstance(table, _erm.Table)
        self.table, self.tag = table, tag
        self.body: dict = self.table.annotations[tag]
        self.createContextRequested.connect(self._on_creatContext)
        self.removeContextRequested.connect(self._on_removeContext)

        # create tabs for each context
        for context in self.body:
            if context == 'filter':
                contents = self.body[context].get('and', [])
            else:
                contents = self.body[context]
            tab = VisibleSourcesContextEditor(self.table, self.tag, context, contents)
            self.addContext(tab, context)

        # set first context active
        if self.body:
            self.setActiveContext(list(self.body.keys())[0])

    @pyqtSlot(str)
    def _on_creatContext(self, context):
        """Handles the 'createContextRequested' signal.
        """
        # create new context entry
        if context == 'filter':
            self.body[context] = {'and': []}
            contents = self.body[context]['and']
        else:
            self.body[context] = []
            contents = self.body[context]

        # create and add new context editor
        contextEditor = VisibleSourcesContextEditor(self.table, self.tag, context, contents)
        self.addContext(contextEditor, context)

    @pyqtSlot(str)
    def _on_removeContext(self, context):
        """Handles the 'removeContextRequested' signal.
        """
        del self.body[context]
        self.removeContext(context)


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
                source_path_to_str(entry.get('source', entry.get('sourcekey', 'virtual')))
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
    body: list

    def __init__(self, table, tag, context, body):
        """Initialize the VisibleSourcesContextEditor.
        """
        super(VisibleSourcesContextEditor, self).__init__()
        self.table, self.context, self.body = table, context, body

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

        # ...table row selection
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
        self.duplicateSource = QPushButton('copy', parent=controls)
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
        controls.setLayout(hlayout)

        # tab layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.tableView)
        layout.addWidget(controls)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

    @pyqtSlot()
    def on_add_click(self):
        """Handler for adding visible source.
        """
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
        """Handler for duplicating visible source.
        """
        index = self.tableView.currentIndex().row()
        if index >= 0:
            duplicate = deepcopy(self.body[index])
            self.body.append(duplicate)
            self.tableView.setModel(
                VisibleSourcesContextEditor.TableModel(self.body)
            )

    @pyqtSlot()
    def on_remove_click(self):
        """Handler for removing a visible source.
        """
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
        """Handler for reordering (up) a visible source.
        """
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
        """Handler for reordering (down) a visible source.
        """
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
        """Handler for double-click event on a visible-source which opens the editor dialog.
        """
        i = self.tableView.currentIndex().row()
        dialog = VisibleSourceDialog(self.table, entry=deepcopy(self.body[i]), mode=self.mode)
        code = dialog.exec_()
        if code == QDialog.Accepted:
            self.body[i] = dialog.entry
            self.tableView.setModel(
                VisibleSourcesContextEditor.TableModel(self.body)
            )


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
        :param mode: flags to indicate the allowable forms of the visible-source
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
                        if self.entry == constraint_name(constraint):
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
            self.entry = constraint_name(data)
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
