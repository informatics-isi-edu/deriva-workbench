"""Widgets for editing visible-sources annotations.
"""
from copy import deepcopy
import logging
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFrame, QWidget, QComboBox, QDialog, QButtonGroup, QRadioButton, QDialogButtonBox
from PyQt5.QtCore import pyqtSlot
from deriva.core import tag as _tag, ermrest_model as _erm
from .common import constraint_name, source_path_to_str, raise_on_invalid
from .tabbed_contexts import EasyTabbedContextsWidget
from .pseudo_column import PseudoColumnEditWidget
from .table import CommonTableWidget


logger = logging.getLogger(__name__)


def _create_context_value(tag: str, context: str):
    """Create initial value for the given visible sources tag and context.

    :param tag: the specific annotation key (e.g., `...visible-columns`)
    :param context: the context name
    """
    # create new context entry
    if tag == _tag.visible_columns and context == 'filter':
        return {'and': []}
    else:
        return []


def _create_visible_source_context_editor(table: _erm.Table, tag: str, body: dict, context: str, parent: QWidget = None):
    """Create visible sources context editor for the given context.

    :param table: the ermrest table that contains the annotation
    :param tag: the specific annotation key (e.g., `...visible-columns`)
    :param body: the context body
    :param context: the context name
    :param parent: the parent widget for the context editor
    """
    # adjust the key, body to be used based on context
    if tag == _tag.visible_columns and context == 'filter':
        key = 'and'
        body = body[context]
    else:
        key = context
        body = body

    # determine visible-source dialog editor mode
    if tag == _tag.visible_columns:
        mode = VisibleSourceDialog.VisibleColumns
        if context == 'entry':
            mode &= ~VisibleSourceDialog.AllowPseudoColumn
        elif context == 'filter':
            mode = VisibleSourceDialog.AllowPseudoColumn
    else:
        mode = VisibleSourceDialog.VisibleForeignKeys

    # dialog exec function
    def visible_source_dialog_exec_fn(value, parent: QWidget = None):
        dialog = VisibleSourceDialog(table, entry=value, mode=mode, parent=parent)
        code = dialog.exec_()
        value = deepcopy(dialog.entry)
        dialog.hide()
        del dialog
        return code, value

    # create and add new context editor
    return CommonTableWidget(
        key,
        body,
        editor_dialog_exec_fn=visible_source_dialog_exec_fn,
        headers_fn=lambda sources: ["Type", "Source"],
        row_fn=_source_entry_to_row,
        truth_fn=lambda x: x is not None,
        parent=parent
    )


class VisibleSourcesEditor(EasyTabbedContextsWidget):
    """Visible sources (column or foreign key) annotation editor.
    """

    def __init__(self, table: _erm.Table, tag: str, parent: QWidget = None):
        """Initialize visible sources editor.

        :param table: the ermrest table that contains the annotation
        :param tag: the specific annotation key (e.g., `...visible-columns`)
        :param parent: the parent widget
        """
        raise_on_invalid(table, _erm.Table, tag)
        super(VisibleSourcesEditor, self).__init__(
            tag,
            table.annotations,
            create_context_value=lambda context: _create_context_value(tag, context),
            create_context_widget_fn=lambda context, parent=None: _create_visible_source_context_editor(table, tag, table.annotations[tag], context, parent=parent),
            purge_on_empty=False,
            allow_context_reference=True,
            parent=parent
        )


def _source_entry_to_row(entry):
    """Converts a visible sources entry into a tuple for use in the table view model.
    """
    if isinstance(entry, str):
        return (
            'Column',
            entry
        )
    elif isinstance(entry, list):
        assert len(entry) == 2, 'List values in source entry must be pairs (length == 2) only'
        return (
            'Constraint',
            entry[1]
        )
    else:
        assert isinstance(entry, dict), "Source entry type should be a dictionary if not string or list"
        return (
            'Pseudo',
            source_path_to_str(entry.get('source', entry.get('sourcekey', 'virtual')))
        )


class VisibleSourceDialog(QDialog):
    """Dialog for editing or defining a visible source entry.
    """

    # Types of visible-source entries, also used as radio button labels
    COLUMN, CONSTRAINT, PSEUDO = 'Column', 'Constraint', 'Pseudo-Column'

    # Modes for visible-source entry
    AllowColumn, AllowPrimaryKey, AllowInboundForeignKey, AllowOutboundForeignKey, AllowPseudoColumn \
        = 2**0, 2**1, 2**2, 2**3, 2**4

    # Short-hand for common combinations of visible-source entry modes
    AllowAll = AllowColumn | AllowPrimaryKey | AllowOutboundForeignKey | AllowInboundForeignKey | AllowPseudoColumn
    VisibleColumns = AllowColumn | AllowPrimaryKey | AllowOutboundForeignKey | AllowPseudoColumn
    VisibleForeignKeys = AllowInboundForeignKey | AllowPseudoColumn

    def __init__(self, table: _erm.Table, entry: dict = None, mode: int = AllowAll, parent: QWidget = None):
        """Initializes the dialog.

        :param table: the ERMrest table model object that contains the entry
        :param entry: a visible source entry
        :param mode: flags to indicate the allowable forms of the visible-source
        :param parent: the parent widget
        """
        super(VisibleSourceDialog, self).__init__(parent=parent)
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
