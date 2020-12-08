"""Editor for `source-definitions` annotation.
"""
from copy import deepcopy
import logging
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFrame, QWidget, QTableView, QGroupBox, QFormLayout, \
    QPushButton, QHBoxLayout, QDialog, QDialogButtonBox, QMessageBox, QComboBox, QLineEdit
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, pyqtSlot
from deriva.core import tag as _tag, ermrest_model as _erm
from .pseudo_column import PseudoColumnEditWidget
from .common import source_path_to_str, constraint_name, SomeOrAllSelectorWidget

logger = logging.getLogger(__name__)

_search_box_key = 'search-box'


class SourceDefinitionsEditor(QWidget):
    """Editor for the `source-definitions` annotation.
    """

    table: _erm.Table
    body: dict

    def __init__(self, table):
        """Initialize the SourceDefinitionsEditor.
        """
        super(SourceDefinitionsEditor, self).__init__()
        self.table = table
        self.body = self.table.annotations[_tag.source_definitions]

        # layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        # ...columns
        columnsGroup = QGroupBox('Columns: select the columns desired for use in templating environments')
        columnsGroup.setLayout(QVBoxLayout(columnsGroup))
        columnsGroup.layout().setContentsMargins(0, 0, 0 , 0)
        self.someOrAllColumns = SomeOrAllSelectorWidget(self.body.get('columns', True),
                                                        [c.name for c in self.table.columns],
                                                        parent=self)
        self.someOrAllColumns.valueChanged.connect(self._on_columns_changed)
        columnsGroup.layout().addWidget(self.someOrAllColumns)
        layout.addWidget(columnsGroup)

        # ...fkeys
        fkeysGroup = QGroupBox('FKeys: select the foreign keys desired for use in templating environments')
        fkeysGroup.setLayout(QVBoxLayout(fkeysGroup))
        fkeysGroup.layout().setContentsMargins(0, 0, 0 , 0)
        self.someOrAllFKeys = SomeOrAllSelectorWidget(self.body.get('fkeys', True),
                                                      [constraint_name(c) for c in self.table.foreign_keys],
                                                      lambda c: '%s:%s' % (c[0], c[1]),
                                                      parent=self)
        self.someOrAllFKeys.valueChanged.connect(self._on_fkeys_changed)
        fkeysGroup.layout().addWidget(self.someOrAllFKeys)
        layout.addWidget(fkeysGroup)

        # ...sources
        sourcesGroup = QGroupBox('Sources: configure source definitions for use in other annotations', parent=self)
        sourcesGroup.setLayout(QVBoxLayout(sourcesGroup))
        sourcesGroup.layout().setContentsMargins(0, 0, 0 , 0)
        sourcesGroup.layout().addWidget(_SourcesWidget(self.table, parent=self))
        layout.addWidget(sourcesGroup)

        # ...search-box
        searchBoxGroup = QGroupBox('Search Box: configure the search columns')
        searchBoxGroup.setLayout(QVBoxLayout(searchBoxGroup))
        searchBoxGroup.layout().setContentsMargins(0, 0, 0 , 0)
        searchBoxGroup.layout().addWidget(_SearchBoxEditWidget(self.table, parent=self))
        layout.addWidget(searchBoxGroup)

    @pyqtSlot()
    def _on_columns_changed(self):
        """Handles changes to the 'columns' property.
        """
        self.body['columns'] = self.someOrAllColumns.selected_values

    @pyqtSlot()
    def _on_fkeys_changed(self):
        """Handles changes to the 'fkeys' property.
        """
        self.body['fkeys'] = self.someOrAllFKeys.selected_values


class _SourcesWidget(QWidget):
    """Sources widget for the Source Definitions Editor.
    """

    class TableModel(QAbstractTableModel):
        """Internal table model.
        """

        def __init__(self, sources):
            super(_SourcesWidget.TableModel, self).__init__()
            self.headers = ["Source Key", "Source"]
            self.rows = [
                (key, source_path_to_str(sources[key].get('source', sources[key].get('sourcekey', 'virtual')))) for key in sources
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
    body: dict

    def __init__(self, table, parent: QWidget = None):
        """Initialize the _SourcesWidget.
        """
        super(_SourcesWidget, self).__init__(parent=parent)
        self.table = table
        self.body = self.table.annotations[_tag.source_definitions]
        self.sources = self.body['sources'] = self.body.get('sources', {})
        self.column_names = set([c.name for c in self.table.columns])

        # table view
        self.model = model = _SourcesWidget.TableModel(self.sources)
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
        hlayout.setContentsMargins(0, 0, 0, 0)
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
        controls.setLayout(hlayout)

        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.tableView)
        layout.addWidget(controls)
        self.setLayout(layout)

    @pyqtSlot()
    def on_add_click(self):
        """Handler for adding source def.
        """
        dialog = SourceDefinitionDialog(self.table, reserved_keys=self.column_names | {_search_box_key} | self.sources.keys(), parent=self)
        code = dialog.exec_()
        if code == QDialog.Accepted:
            self.sources[dialog.sourcekey] = dialog.entry
            self.tableView.setModel(
                _SourcesWidget.TableModel(self.sources)
            )

    @pyqtSlot()
    def on_duplicate_click(self):
        """Handler for duplicating source def.
        """
        index = self.tableView.currentIndex().row()
        if index >= 0:
            sourcekey = orig = self.tableView.model().rows[index][0]
            duplicate = deepcopy(self.sources[sourcekey])
            disambig = 1
            while sourcekey in self.sources:
                sourcekey = orig + '_copy_' + str(disambig)
                disambig += 1
            self.sources[sourcekey] = duplicate
            self.tableView.setModel(
                _SourcesWidget.TableModel(self.sources)
            )

    @pyqtSlot()
    def on_remove_click(self):
        """Handler for removing a source def.
        """
        index = self.tableView.currentIndex().row()
        if index >= 0:
            sourcekey = self.tableView.model().rows[index][0]
            del self.sources[sourcekey]
            self.tableView.setModel(
                _SourcesWidget.TableModel(self.sources)
            )
            index = index if index < len(self.body) else index - 1
            self.tableView.selectRow(index)

    @pyqtSlot()
    def on_doubleclick(self):
        """Handler for double-click event which opens the source editor dialog.
        """
        index = self.tableView.currentIndex().row()
        sourcekey = self.tableView.model().rows[index][0]
        dialog = SourceDefinitionDialog(self.table,
                                        sourcekey=sourcekey,
                                        entry=deepcopy(self.sources[sourcekey]),
                                        reserved_keys=self.column_names | {_search_box_key} | self.sources.keys() - {sourcekey},
                                        parent=self)
        code = dialog.exec_()
        if code == QDialog.Accepted:
            del self.sources[sourcekey]
            self.sources[dialog.sourcekey] = dialog.entry
            self.tableView.setModel(
                _SourcesWidget.TableModel(self.sources)
            )

    @pyqtSlot()
    def on_click(self):
        """Handler for click event on a source which records its index for use in combination with other commands.
        """
        idx = self.tableView.currentIndex()


class SourceDefinitionDialog(QDialog):
    """Dialog for defining or editing a source definition.
    """

    table: _erm.Table
    entry: dict
    reserved_keys = [str]

    def __init__(self, table: _erm.Table, sourcekey: str = '', entry: dict = None, reserved_keys: set or iter = None, parent: QWidget = None):
        super(SourceDefinitionDialog, self).__init__(parent=parent)
        self.table = table
        self.sourcekey = sourcekey
        self.entry = entry or {}
        self.reserved_keys = reserved_keys or []

        self.setWindowTitle("Source Definition")
        self.setMinimumWidth(640)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Define or modify the source definition."))

        # ...pseudo-column widget
        self.entry['sourcekey'] = sourcekey  # inject sourcekey into entry for the pseudocolumn widget
        self.pseudoWidget = PseudoColumnEditWidget(self.table, self.entry, mode=PseudoColumnEditWidget.SourceDefinition,
                                                   parent=self)
        layout.addWidget(self.pseudoWidget)

        # ...ok/cancel
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

        self.setLayout(layout)

    def accept(self) -> None:
        """Overrides the default accept to perform validation before accepting.
        """
        if not self.entry.get('sourcekey'):
            QMessageBox.critical(
                self,
                'Validation Error',
                'Source Key required.',
                QMessageBox.Ok
            )
            return

        if self.entry['sourcekey'] in self.reserved_keys:
            QMessageBox.critical(
                self,
                'Validation Error',
                'Source Key must be unique. Current keys defined: %s.' % (
                    ', '.join(map(lambda s: '"%s"' % s, self.reserved_keys))
                ),
                QMessageBox.Ok
            )
            return

        if not self.entry.get('source'):
            QMessageBox.critical(
                self,
                'Validation Error',
                'Source Entry required.',
                QMessageBox.Ok
            )
            return

        # valid if this point reached
        # ...remove sourcekey from entry before returning
        self.sourcekey = self.entry['sourcekey']
        del self.entry['sourcekey']
        return super(SourceDefinitionDialog, self).accept()


class _SearchBoxEditWidget(QWidget):
    """Editor widget for the Search Box source.
    """

    class TableModel(QAbstractTableModel):
        """Internal table model.
        """

        def __init__(self, searchcolumns):
            super(_SearchBoxEditWidget.TableModel, self).__init__()
            self.headers = ["Source", "Markdown Name"]
            self.rows = [
                (searchcol['source'], searchcol.get('markdown_name')) for searchcol in searchcolumns
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
    body: dict

    def __init__(self, table, parent: QWidget = None):
        """Initialize the _SearchBoxEditWidget.
        """
        super(_SearchBoxEditWidget, self).__init__(parent=parent)
        self.table = table
        self.body = self.table.annotations[_tag.source_definitions]
        self.sources = self.body['sources'] = self.body.get('sources', {})
        self.column_names = set([c.name for c in self.table.columns])

        # table view
        self.model = model = _SearchBoxEditWidget.TableModel(self.sources.get(_search_box_key, {}).get('or', []))
        self.tableView = QTableView(parent=self)
        self.tableView.setModel(model)

        # ...table selection change
        self.tableView.clicked.connect(self.on_click)

        # ...table view styling
        self.tableView.setWordWrap(True)
        self.tableView.setAlternatingRowColors(True)
        self.tableView.horizontalHeader().setStretchLastSection(True)

        # controls frame
        controls = QFrame()
        hlayout = QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        # ...add column button
        addSource = QPushButton('+', parent=controls)
        addSource.clicked.connect(self.on_add_click)
        hlayout.addWidget(addSource)
        # ...remove column button
        self.removeSource = QPushButton('-', parent=controls)
        self.removeSource.clicked.connect(self.on_remove_click)
        hlayout.addWidget(self.removeSource)
        controls.setLayout(hlayout)

        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.tableView)
        layout.addWidget(controls)
        self.setLayout(layout)

    @pyqtSlot()
    def on_add_click(self):
        """Handler for adding source def.
        """
        dialog = _SearchColumnDialog(self.column_names, parent=self)
        code = dialog.exec_()
        if code == QDialog.Accepted:
            # get search column from dialog
            searchcolumn = {
                'source': dialog.source
            }
            if dialog.markdown_name:
                searchcolumn['markdown_name'] = dialog.markdown_name

            # update annotation
            if _search_box_key in self.sources:
                # append to existing search columns
                self.sources[_search_box_key]['or'].append(searchcolumn)
            else:
                # initialize the search-box source
                self.sources[_search_box_key] = {
                    'or': [
                        searchcolumn
                    ]
                }

            # update display model
            self.tableView.setModel(
                _SearchBoxEditWidget.TableModel(self.sources[_search_box_key]['or'])
            )

    @pyqtSlot()
    def on_remove_click(self):
        """Handler for removing a source def.
        """
        index = self.tableView.currentIndex().row()
        if index >= 0:
            del self.sources[_search_box_key]['or'][index]

            # update display model
            self.tableView.setModel(
                _SearchBoxEditWidget.TableModel(self.sources[_search_box_key]['or'])
            )
            index = index if index < len(self.body) else index - 1
            self.tableView.selectRow(index)

            # purge 'search-box' source, if empty
            if not self.sources[_search_box_key]['or']:
                del self.sources[_search_box_key]

    @pyqtSlot()
    def on_click(self):
        """Handler for click event on a source which records its index for use in combination with other commands.
        """
        idx = self.tableView.currentIndex()


class _SearchColumnDialog(QDialog):
    """Dialog for adding a searchcolumn to the `search-box`.
    """

    source = str or None
    markdown_name = str or None

    def __init__(self, column_names: [str], parent: QWidget = None):
        super(_SearchColumnDialog, self).__init__(parent=parent)
        self.source = None
        self.markdown_name = None

        self.setWindowTitle("Search Column")
        form = QFormLayout(self)
        form.addWidget(QLabel("Select a column and enter an optional markdown_name."))

        # source combobox
        self._sourceComboBox = QComboBox(parent=self)
        self._sourceComboBox.setPlaceholderText('Select a column')
        self._sourceComboBox.addItems(column_names)
        form.addRow('Source', self._sourceComboBox)

        # markdown name edit
        self._markdownNameLineEdit = QLineEdit(parent=self)
        self._markdownNameLineEdit.setPlaceholderText("Enter a markdown pattern")
        form.addRow('Markdown Name', self._markdownNameLineEdit)

        # ...ok/cancel
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        form.addWidget(buttonBox)
        self.setLayout(form)

    def accept(self) -> None:
        """Overrides the default accept to perform validation before accepting.
        """
        index = self._sourceComboBox.currentIndex()
        if index < 0:
            QMessageBox.critical(
                self,
                'Validation Error',
                'Source required.',
                QMessageBox.Ok
            )
            return

        # valid if this point reached
        self.source = self._sourceComboBox.itemText(index)
        self.markdown_name = self._markdownNameLineEdit.text()
        return super(_SearchColumnDialog, self).accept()


class _SearchColumnWidget(QWidget):
    """Widget for adding a `searchcolumn` to the `search-box` property.
    """

    source = str or None
    markdown_name = str or None

    def __init__(self, column_names: list, parent: QWidget = None):
        super(_SearchColumnWidget, self).__init__(parent=parent)
        self._value = {}
        self.source = None
        self.markdown_name = None
