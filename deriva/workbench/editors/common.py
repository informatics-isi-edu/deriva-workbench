"""Widgets and utility functions shared by multiple editors.
"""
from collections.abc import Callable
import logging
from typing import Any
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QCheckBox, QListWidget, QListWidgetItem, QComboBox, QLineEdit
from PyQt5.QtGui import QValidator
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

logger = logging.getLogger(__name__)


def set_value_or_del_key(container: dict, cond: bool, key: str, value):
    """Conditionally, set the value of the property or delete the key from the containing dict.

    :param container: the dictionary that contains the key-value pair
    :param cond: indicates if the key should be set to the value or dropped from the container
    :param key: dictionary key (i.e., 'wait_for')
    :param value: valid value for the key
    """
    # set or delete value
    if cond:
        container[key] = value
    elif key in container:
        del container[key]


def constraint_name(constraint):
    """Returns the annotation-friendly form of the constraint name.
    """
    return [constraint.constraint_schema.name if constraint.constraint_schema else '', constraint.constraint_name]


def is_constraint_name(value):
    """Tests if the value looks like a constraint name.
    """
    return isinstance(value, list) and len(value) == 2 and all(isinstance(elem, str) for elem in value)


def source_component_to_str(component):
    """Readable string representation of a `source` path component.
    """
    return (
        component if isinstance(component, str) else
        '%s:%s (inbound)' % tuple(component['inbound']) if 'inbound' in component else
        '%s:%s (outbound)' % tuple(component['outbound']) if 'outbound' in component else
        '%s <<unexpected structure>>' % component
    )


def source_path_to_str(source):
    """Readable string representation of a `source` path.
    """
    if isinstance(source, str):
        return source
    elif is_constraint_name(source):
        return source[1]
    elif isinstance(source, list) and len(source):
        return ' > '.join(source_component_to_str(component) for component in source)
    else:
        raise ValueError('%s is not a valid source path' % str(source))


class SubsetSelectionWidget(QListWidget):
    """Widget for selecting a subset of values from a list of available options.
    """

    selected_values: []
    valueChanged = pyqtSignal()

    def __init__(self, selected_values: [], all_values: [], to_string: Callable = None, parent: QWidget = None):
        """Initialize the widget.

        :param selected_values: list of selected values
        :param all_values: list of all available values
        :param to_string: a function that takes a value and returns a string representation
        :param parent: parent widget
        """
        super(SubsetSelectionWidget, self).__init__(parent=parent)
        self.selected_values = selected_values
        to_string = to_string or (lambda v: str(v))

        self.setSortingEnabled(True)
        for value in all_values:
            item = QListWidgetItem(to_string(value))
            item.setData(Qt.UserRole, value)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if value in selected_values else Qt.Unchecked)
            self.addItem(item)
        self.itemClicked.connect(self._on_item_clicked)

    @pyqtSlot()
    def _on_item_clicked(self):
        """Handles changes to the `value` list.
        """
        self.selected_values.clear()
        for row in range(self.count()):
            item = self.item(row)
            if item.checkState():
                self.selected_values.append(item.data(Qt.UserRole))

        self.valueChanged.emit()


class SomeOrAllSelectorWidget(QWidget):
    """Widget for selecting all or a subset of available options.
    """

    selected_values: bool or []
    valueChanged = pyqtSignal()

    def __init__(self, selected_values: bool or [], all_values: [], to_string: Callable = None, parent: QWidget = None):
        """Initialize the widget.

        :param selected_values: list of selected values
        :param all_values: list of all available values
        :param to_string: a function that takes a value and returns a string representation
        :param parent: parent widget
        """
        super(SomeOrAllSelectorWidget, self).__init__(parent=parent)
        self.selected_values = selected_values

        # layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

        # all checkbox
        self.allCheckBox = QCheckBox('All', parent=self)
        self.allCheckBox.clicked.connect(self._on_checkbox_clicked)
        layout.addWidget(self.allCheckBox)

        # subset list
        self.subsetSelectionWidget = SubsetSelectionWidget(
            selected_values if isinstance(selected_values, list) else [],
            all_values,
            to_string=to_string,
            parent=self
        )
        self.subsetSelectionWidget.valueChanged.connect(self._on_subset_changed)
        layout.addWidget(self.subsetSelectionWidget)

        if self.selected_values is True:
            self.allCheckBox.setChecked(True)
            self.subsetSelectionWidget.setEnabled(False)

    @pyqtSlot()
    def _on_checkbox_clicked(self):
        """Handles checkbox clicked event.
        """
        if self.allCheckBox.isChecked():
            self.selected_values = True
            self.subsetSelectionWidget.setEnabled(False)
        else:
            self.selected_values = self.subsetSelectionWidget.selected_values
            self.subsetSelectionWidget.setEnabled(True)

        self.valueChanged.emit()

    @pyqtSlot()
    def _on_subset_changed(self):
        """Propagates the valueChanged signal from the subset selection widget.
        """
        self.valueChanged.emit()


class SimpleTextPropertyWidget(QLineEdit):
    """A simple property editor widget extending QLineEdit.
    """

    valueChanged = pyqtSignal()

    def __init__(
            self,
            key: str,
            body: {},
            placeholder: str = '',
            validator: QValidator = None,
            parent: QWidget = None):
        """Initialize the widget.

        :param key: annotation key
        :param body: annotation body (container)
        :param placeholder: text to display when no value set in the widget
        :param parent: parent widget
        """
        super(SimpleTextPropertyWidget, self).__init__(parent=parent)
        self.key, self.body = key, body
        self.setText(self.body.get(key, ''))
        self.setPlaceholderText(placeholder)
        self.textChanged.connect(self._on_textChanged)
        if validator:
            self.setValidator(validator)

    @pyqtSlot()
    def _on_textChanged(self):
        """Handles textChanged events.
        """
        value = self.text()
        set_value_or_del_key(
            self.body,
            bool(value),
            self.key,
            value
        )
        self.valueChanged.emit()


class SimpleBooleanPropertyWidget(QCheckBox):
    """A simple boolean property editor widget.
    """

    valueChanged = pyqtSignal()

    def __init__(
            self,
            text: str,
            key: str,
            body: {},
            parent: QWidget = None):
        """Initialize the widget

        :param text: checkbox text label
        :param key: annotation key
        :param body: annotation body (container)
        :param parent: parent widget
        """
        super(SimpleBooleanPropertyWidget, self).__init__(text, parent=parent)
        self.key, self.body = key, body
        self.setChecked(self.body.get(key, False))
        self.clicked.connect(self._on_clicked)

    @pyqtSlot()
    def _on_clicked(self):
        """Handles clicked events.
        """
        value = self.isChecked()
        set_value_or_del_key(
            self.body,
            bool(value),
            self.key,
            value
        )
        self.valueChanged.emit()


class SimpleComboBoxPropertyWidget(QComboBox):
    """A simple combobox property editor widget.
    """

    valueChanged = pyqtSignal()

    def __init__(
            self,
            key: str,
            body: {},
            choices: [str],
            placeholder: str = '',
            parent: QWidget = None):
        """Initialize the widget.

        Limitation: this widget treats `''` as a non-selectable value.

        :param key: annotation key
        :param body: annotation body (container)
        :param choices: list of values that may be selected
        :param placeholder: text to display when no value is selected
        :param parent: parent widget
        """
        super(SimpleComboBoxPropertyWidget, self).__init__(parent=parent)
        self.key, self.body = key, body
        self.addItems([''] + choices)
        self.setPlaceholderText(placeholder)
        self.setCurrentIndex(
            self.findText(self.body.get(self.key, '')) or -1
        )
        self.currentIndexChanged.connect(self._on_index_changed)

    @pyqtSlot()
    def _on_index_changed(self):
        value = self.currentText()
        set_value_or_del_key(
            self.body,
            bool(value),
            self.key,
            value
        )
        self.valueChanged.emit()


class TemplateEngineWidget(SimpleComboBoxPropertyWidget):
    """Widget for the `template_engine` property.
    """

    def __init__(self, body: {}, parent: QWidget = None):
        """Initialize the widget.

        :param body: annotation body (container)
        :param parent: parent widget
        """
        super(TemplateEngineWidget, self).__init__(
            'template_engine',
            body,
            ['handlebars', 'mustache'],
            'Select a template engine',
            parent=parent)
