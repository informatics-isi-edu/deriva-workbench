"""Schema browser widget.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QTreeView, QWidget
from PyQt5.Qt import QStandardItemModel, QStandardItem
from PyQt5.QtGui import QFont, QColor

_annotationColor = QColor(102, 153, 0)
_columnColor = QColor(51, 102, 204)
_keyColor = QColor(204, 102, 0)
_fkeyColor = QColor(153, 51, 102)


class _SchemaBrowserItem(QStandardItem):
    def __init__(self, txt='', data=None, font_size=12, set_bold=False, color=QColor(0, 0, 0)):
        super().__init__()

        fnt = QFont('Open Sans', font_size)
        fnt.setBold(set_bold)

        self.setEditable(False)
        self.setForeground(color)
        self.setFont(fnt)
        self.setText(txt)
        self.setData(data, Qt.UserRole)


class SchemaBrowser(QWidget):

    def __init__(self, onSelect=None):
        super(SchemaBrowser, self).__init__()
        self.onSelect = onSelect

        self.treeView = QTreeView()
        self.treeView.setHeaderHidden(True)

        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)

        vlayout.addWidget(QLabel('Schema Browser'))
        vlayout.addWidget(self.treeView)

        self.setLayout(vlayout)
        self.model = None

    def setModel(self, model):
        self.model = model

        treeModel = QStandardItemModel()
        rootNode = treeModel.invisibleRootItem()

        def add_annotations(parent, obj):
            annotationsItem = _SchemaBrowserItem('annotations', {'parent': obj}, 12, color=_annotationColor)
            for tag, body in obj.annotations.items():
                annotationsItem.appendRow(_SchemaBrowserItem(tag, {'parent': obj, 'tag': tag}, 12, color=_annotationColor))
            parent.appendRow(annotationsItem)

        if model:
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
        treeView = QTreeView()
        treeView.setHeaderHidden(True)
        treeView.setModel(treeModel)
        treeView.doubleClicked.connect(self.getValue)
        self.layout().replaceWidget(self.treeView, treeView)
        self.treeView = treeView

    def getValue(self, val):
        data = val.data(Qt.UserRole)
        if self.onSelect:
            self.onSelect(data)
