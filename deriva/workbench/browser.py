"""Components for the schema browser.
"""
from typing import Any, Union, Optional
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QModelIndex, QPoint, QItemSelectionModel
from PyQt5.QtWidgets import QVBoxLayout, QTreeView, QWidget, QGroupBox, QMenu, QMessageBox
from PyQt5.Qt import QStandardItemModel, QStandardItem
from PyQt5.QtGui import QFont, QColor
from deriva.core import ermrest_model as _erm, tag as tags

# colors for menu items by type (ordered alphabetically as they will be displayed)
#   palette: 581845, 900C3F, C70039, FF5733, FFC300
_aclBindingsColor = QColor('#581845')
_aclsColor = QColor('#900C3F')
_annotationColor = QColor(102, 153, 0)  # green
_columnColor = QColor(51, 102, 204)  # blue
_fkeyColor = QColor('#C70039')  # previous: 153, 51, 102
_keyColor = QColor('#FF5733')  # previous: 204, 102, 0

# keys
__annotations__ = 'annotations'
__acls__ = 'acls'
__acl_bindings__ = 'acl_bindings'
__parent__ = 'parent'
__tag__ = 'tag'


class _SchemaBrowserItem(QStandardItem):
    """Internal schema browser item.
    """
    def __init__(self,
                 txt: str = '',
                 data: Any = None,
                 font_size: int = 12,
                 set_bold: bool = False,
                 color: QColor = None):
        """Initializes the item.

        :param txt: label for the item
        :param data: user data for the item
        :param font_size: font size for the text label
        :param set_bold: set bold for the text label
        :param color: foreground color
        """
        super().__init__(txt)

        fnt = QFont('Open Sans', font_size)
        fnt.setBold(set_bold)

        self.setEditable(False)
        self.setFont(fnt)
        self.setData(data, Qt.UserRole)
        if color:
            self.setForeground(color)


class SchemaBrowser(QGroupBox):
    """Schema browser widget.
    """

    itemSelected = pyqtSignal()
    itemOpened = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        """Initialize the widget.

        :param parent: the parent widget
        """
        super(SchemaBrowser, self).__init__('Schema Browser', parent=parent)
        self.model = None
        self.lastItemSelected = self.lastItemOpened = None
        self._treeView = self._create_treeView()

        # layout
        vlayout = QVBoxLayout(self)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self._treeView)
        self.setLayout(vlayout)

    def _create_treeView(self, model: Optional[QStandardItemModel] = None) -> QTreeView:
        """Returns a newly created, configured, and connected treeView for the schema browser main content widget.
        """
        treeView = QTreeView(parent=self)
        treeView.setHeaderHidden(True)
        treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        treeView.customContextMenuRequested.connect(self._on_customContextMenu)
        treeView.doubleClicked.connect(self._on_double_clicked)
        treeView.clicked.connect(self._on_clicked)
        if model:
            treeView.setModel(model)

        return treeView

    def _selectAndOpen(self, index: QModelIndex, as_source: bool = False):
        """Select and open an item.

        :param index: the tree model index to select and open
        :param as_source: flag passed in payload for editor to interpret
        """
        selection = self._treeView.selectionModel()
        selection.clear()
        selection.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        data = index.data(Qt.UserRole).copy()
        if as_source:
            data['as_source'] = as_source
        self.lastItemSelected = self.lastItemOpened = data
        self.itemOpened.emit()
        self.itemSelected.emit()

    @pyqtSlot(QPoint)
    def _on_customContextMenu(self, pos: QPoint):
        """Context event handler for displaying context menu.
        """
        # ...get index for position
        index = self._treeView.indexAt(pos)
        item: _SchemaBrowserItem = self._treeView.model().itemFromIndex(index)
        data = index.data(Qt.UserRole)
        if not data:
            return

        if isinstance(data, dict) and __parent__ in data:
            # this should be an annotations item
            model_obj = data[__parent__]
            assert hasattr(model_obj, __annotations__), 'Object must have annotations'
            menu = QMenu(parent=self)

            if __tag__ in data:
                # case: specific annotation selected
                tag = data[__tag__]
                editAction = menu.addAction('Edit')
                editAsJSONAction = menu.addAction('Edit Source')
                deleteAction = menu.addAction('Delete')
                action = menu.exec_(self.mapToGlobal(pos))
                if action == deleteAction:
                    reply = QMessageBox.question(
                        self,
                        self.tr('Confirmation Required'),
                        self.tr('Are you sure you want to delete "') + tag + '"?'
                    )
                    if reply == QMessageBox.Yes:
                        # delete the specified annotation
                        del model_obj.annotations[tag]
                        index.model().removeRow(index.row(), index.parent())
                        self._selectAndOpen(index.parent())
                elif action == editAction:
                    self._selectAndOpen(index)
                elif action == editAsJSONAction:
                    self._selectAndOpen(index, as_source=True)

            else:
                # case: all annotations selected
                for tag in [tag for tag in tags.values() if tag not in data[__parent__].annotations]:
                    addAction = menu.addAction('Add "%s"' % tag)
                    addAction.setData(tag)
                action = menu.exec_(self.mapToGlobal(pos))
                if action and action.data():
                    # add the new tag to the annotations
                    tag = action.data()
                    model_obj.annotations[tag] = {}
                    item.appendRow(
                        _SchemaBrowserItem(tag, {__parent__: model_obj, __tag__: tag}, 12, color=_annotationColor)
                    )
                    self._selectAndOpen(index)

    @pyqtSlot(QModelIndex)
    def _on_double_clicked(self, index: QModelIndex):
        """Double-click handler, updates last item opened and emits signal
        """
        self.lastItemOpened = index.data(Qt.UserRole)
        self.itemOpened.emit()

    @pyqtSlot(QModelIndex)
    def _on_clicked(self, index: QModelIndex):
        """Click handler, updates the last item selected and emits signal.
        """
        self.lastItemSelected = index.data(Qt.UserRole)
        self.itemSelected.emit()

    def clear(self) -> None:
        """Clear the state of the browser.
        """
        self.lastItemSelected = self.lastItemOpened = None
        treeView = self._create_treeView()
        self.layout().replaceWidget(self._treeView, treeView)
        self._treeView = treeView

    def reset(self) -> None:
        """Resets the state of the browser using the current 'model' property.
        """
        if self.model:
            self.setModel(self.model)

    def setModel(self, model: _erm.Model) -> None:
        """Sets the ermrest model for the browser.

        The function may be called to set or update the model.

        :param model: an ermrest Model instance
        """
        assert isinstance(model, _erm.Model), "Invalid 'model' object passed to schema browser"
        self.model = model
        self.lastItemSelected = self.lastItemOpened = None

        def add_annotations(parent: _SchemaBrowserItem, obj: Any):
            """Adds the 'annotations' container and items.

            :param parent: a standard model item
            :param obj: an ermrest model object
            """
            assert hasattr(obj, __annotations__)
            # ...add the annotations container item
            annotationsItem = _SchemaBrowserItem(__annotations__, {__parent__: obj}, 12, color=_annotationColor)
            # ...add all annotation items
            for tag, body in obj.annotations.items():
                annotationsItem.appendRow(_SchemaBrowserItem(tag, {__parent__: obj, __tag__: tag}, 12, color=_annotationColor))
            # ...append container to parent object
            parent.appendRow(annotationsItem)

        def add_acls(parent: _SchemaBrowserItem, obj: Any):
            """Adds the 'acls' and 'acl_bindings' containers.

            :param parent: a standard model item
            :param obj: an ermrest model object
            """
            if hasattr(obj, __acls__):
                # ...add the acls container item
                aclsItem = _SchemaBrowserItem(__acls__, {__acls__: obj.acls}, 12, color=_aclsColor)
                parent.appendRow(aclsItem)

            if hasattr(obj, __acl_bindings__):
                # ...add the acl_bindings container item
                aclBindingsItem = _SchemaBrowserItem(__acl_bindings__, {__acl_bindings__: obj.acl_bindings}, 12, color=_aclBindingsColor)
                parent.appendRow(aclBindingsItem)

        # create tree
        treeModel = QStandardItemModel()

        # add root
        rootNode = _SchemaBrowserItem('catalog (%s)' % model.catalog.get_server_uri(), model, 12, set_bold=True)
        schemasNode = _SchemaBrowserItem('schemas', None, 12)
        rootNode.appendRow(schemasNode)
        add_annotations(rootNode, model)
        add_acls(rootNode, model)
        treeModel.appendRow(rootNode)

        # add schemas
        for schema in model.schemas.values():
            schemaItem = _SchemaBrowserItem(schema.name, schema, 12, set_bold=True)
            add_annotations(schemaItem, schema)
            add_acls(schemaItem, schema)

            # add tables
            tablesItem = _SchemaBrowserItem('tables', None, 12)
            schemaItem.appendRow(tablesItem)
            for table in schema.tables.values():
                tableItem = _SchemaBrowserItem(table.name, table, 12)
                add_annotations(tableItem, table)
                add_acls(tableItem, table)

                # add columns
                colsItem = _SchemaBrowserItem('columns', None, 12, color=_columnColor)
                tableItem.appendRow(colsItem)
                for col in table.columns:
                    colItem = _SchemaBrowserItem(col.name, col, 12, color=_columnColor)
                    add_annotations(colItem, col)
                    add_acls(colItem, col)
                    colsItem.appendRow(colItem)

                # add keys
                keysItem = _SchemaBrowserItem('keys', None, 12, color=_keyColor)
                tableItem.appendRow(keysItem)
                for key in table.keys:
                    keyItem = _SchemaBrowserItem(key.constraint_name, key, 12, color=_keyColor)
                    add_annotations(keyItem, key)
                    keysItem.appendRow(keyItem)

                # add fkeys
                fkeysItem = _SchemaBrowserItem('foreign keys', None, 12, color=_fkeyColor)
                tableItem.appendRow(fkeysItem)
                for fkey in table.foreign_keys:
                    fkeyItem = _SchemaBrowserItem(fkey.constraint_name, fkey, 12, color=_fkeyColor)
                    add_annotations(fkeyItem, fkey)
                    add_acls(fkeyItem, fkey)
                    fkeysItem.appendRow(fkeyItem)

                tablesItem.appendRow(tableItem)
            schemasNode.appendRow(schemaItem)

        rootNode.sortChildren(0)

        # create new and replace old treeview
        treeView = self._create_treeView(treeModel)
        treeView.expand(rootNode.index())  # expand root
        self.layout().replaceWidget(self._treeView, treeView)
        self._treeView = treeView
