"""Components for the schema browser.
"""
from typing import Any, Union, Optional
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QModelIndex, QPoint, QItemSelectionModel
from PyQt5.QtWidgets import QVBoxLayout, QTreeView, QWidget, QGroupBox, QMenu, QMessageBox
from PyQt5.Qt import QStandardItemModel, QStandardItem
from PyQt5.QtGui import QFont, QColor
from deriva.core import ermrest_model as _erm, tag as tags

# colors for menu items by type
_annotationColor = QColor(102, 153, 0)
_columnColor = QColor(51, 102, 204)
_keyColor = QColor(204, 102, 0)
_fkeyColor = QColor(153, 51, 102)

# keys
__annotations__ = 'annotations'
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

    clicked = pyqtSignal()
    doubleClicked = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        """Initialize the widget.

        :param parent: the parent widget
        """
        super(SchemaBrowser, self).__init__('Schema Browser', parent=parent)
        self._ermrest_model: Union[_erm.Model, None] = None
        self.current_selection = self._last_openned = None
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
                deleteAction = menu.addAction('Delete "%s"' % tag)
                action = menu.exec_(self.mapToGlobal(pos))
                if action == deleteAction:
                    reply = QMessageBox.question(
                        self,
                        'Confirmation Required',
                        'Are you sure you want to delete "%s"?' % tag
                    )
                    if reply == QMessageBox.Yes:
                        # delete the specified annotation
                        del model_obj.annotations[tag]
                        index.model().removeRow(index.row(), index.parent())
                        # if current_select is this tag or the parent 'annotations', force refresh of the editor
                        if (
                                self._last_openned == {__parent__: model_obj} or
                                self._last_openned == {__parent__: model_obj, __tag__: tag}
                        ):
                            selection = self._treeView.selectionModel()
                            selection.clear()
                            selection.select(index.parent(), QItemSelectionModel.Select | QItemSelectionModel.Rows)
                            self.current_selection = self._last_openned = {__parent__: model_obj}
                            self.clicked.emit()
                            self.doubleClicked.emit()

            else:
                # case: all annotations selected
                for tag in [tag for tag in tags.values() if tag not in data[__parent__].annotations]:
                    addAction = menu.addAction('Add "%s"' % tag)
                    addAction.setData(tag)
                action = menu.exec_(self.mapToGlobal(pos))
                if action and action.data():
                    tag = action.data()
                    model_obj.annotations[tag] = {}
                    item.appendRow(
                        _SchemaBrowserItem(tag, {__parent__: model_obj, __tag__: tag}, 12, color=_annotationColor)
                    )
                    # if current_select is the parent 'annotations', for refresh of the editor
                    if self.current_selection == {__parent__: model_obj}:
                        self.doubleClicked.emit()

    @pyqtSlot(QModelIndex)
    def _on_double_clicked(self, index: QModelIndex):
        """Double-click handler.
        """
        self.current_selection = self._last_openned = index.data(Qt.UserRole)
        self.doubleClicked.emit()

    @pyqtSlot(QModelIndex)
    def _on_clicked(self, index: QModelIndex):
        """Click handler.
        """
        self.current_selection = index.data(Qt.UserRole)
        self.clicked.emit()

    def setModel(self, model: _erm.Model) -> None:
        """Sets the ermrest model for the browser.

        The function may be called to set or update the model.

        :param model: an ermrest Model instance
        """
        self._ermrest_model = model
        self.current_selection = self._last_openned = None

        treeModel = QStandardItemModel()
        rootNode = treeModel.invisibleRootItem()

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

        if model:
            # add schemas
            for schema in model.schemas.values():
                schemaItem = _SchemaBrowserItem(schema.name, schema, 12, set_bold=True)
                add_annotations(schemaItem, schema)

                # add tables
                tablesItem = _SchemaBrowserItem('tables', None, 12)
                schemaItem.appendRow(tablesItem)
                for table in schema.tables.values():
                    tableItem = _SchemaBrowserItem(table.name, table, 12)
                    add_annotations(tableItem, table)

                    # add columns
                    colsItem = _SchemaBrowserItem('columns', None, 12, color=_columnColor)
                    tableItem.appendRow(colsItem)
                    for col in table.columns:
                        colItem = _SchemaBrowserItem(col.name, col, 12, color=_columnColor)
                        add_annotations(colItem, col)
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
                        fkeysItem.appendRow(fkeyItem)

                    tablesItem.appendRow(tableItem)
                rootNode.appendRow(schemaItem)

            rootNode.sortChildren(0)

        # create new and replace old treeview
        treeView = self._create_treeView(treeModel)
        self.layout().replaceWidget(self._treeView, treeView)
        self._treeView = treeView
