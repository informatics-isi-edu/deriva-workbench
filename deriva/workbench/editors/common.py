"""Widgets and utility functions shared by multiple editors.
"""
import logging
from typing import Any, Union, Callable
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QCheckBox, QListWidget, QListWidgetItem, QComboBox, QLineEdit, \
    QButtonGroup, QBoxLayout, QHBoxLayout, QRadioButton
from PyQt5.QtGui import QValidator
from PyQt5.QtCore import Qt, QObject, pyqtSlot, pyqtSignal

logger = logging.getLogger(__name__)


def raise_on_invalid(model_obj, valid, tag: str):
    """Raises type error for tags applied to invalid model object types.

    :param model_obj: an ermrest model object
    :param valid: one or a list of ermrest model classes
    :param tag: the annotation tag name
    """
    valid_types = valid if isinstance(valid, list) else [valid]
    if not any(isinstance(model_obj, valid_type) for valid_type in valid_types):
        raise TypeError(
            'The "%s" annotation should only be used on resources of type %s.' % (
                tag,
                ', '.join([valid_type.__name__ for valid_type in valid_types])
            )
        )


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

    selected_values: list
    valueChanged = pyqtSignal()

    def __init__(self, selected_values: list, all_values: list, to_string: Callable = None, parent: QWidget = None):
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

    selected_values: Union[bool, list]
    valueChanged = pyqtSignal()

    def __init__(self, selected_values: Union[bool, list], all_values: list, to_string: Callable = None, parent: QWidget = None):
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

    value: str
    valueChanged = pyqtSignal()

    def __init__(
            self,
            key: str,
            body: {},
            placeholder: str = '',
            validator: QValidator = None,
            truth_fn: Callable = bool,
            parent: QWidget = None):
        """Initialize the widget.

        :param key: annotation key
        :param body: annotation body (container)
        :param placeholder: text to display when no value set in the widget
        :param validator: optional validator for the line editor
        :param truth_fn: function applied to value to determine whether it should be set or dropped from body
        :param parent: parent widget
        """
        super(SimpleTextPropertyWidget, self).__init__(parent=parent)
        self.key, self.body = key, body
        self._truth_fn = truth_fn
        self.value = self.body.get(key, '')
        if isinstance(self.value, str):
            self.setText(self.value)
        self.setPlaceholderText(placeholder)
        self.textChanged.connect(self._on_textChanged)
        if validator:
            self.setValidator(validator)

    @pyqtSlot()
    def _on_textChanged(self):
        """Handles textChanged events.
        """
        self.value = self.text()
        set_value_or_del_key(
            self.body,
            self._truth_fn(self.value),
            self.key,
            self.value
        )
        self.valueChanged.emit()


class SimpleBooleanPropertyWidget(QCheckBox):
    """A simple boolean property editor widget.
    """

    value: bool
    valueChanged = pyqtSignal()

    def __init__(
            self,
            text: str,
            key: str,
            body: {},
            truth_fn: Callable = bool,  # todo: change this to x is not None
            parent: QWidget = None):
        """Initialize the widget

        :param text: checkbox text label
        :param key: annotation key
        :param body: annotation body (container)
        :param truth_fn: function applied to value to determine whether it should be set or dropped from body
        :param parent: parent widget
        """
        super(SimpleBooleanPropertyWidget, self).__init__(text, parent=parent)
        self.key, self.body, self._truth_fn = key, body, truth_fn
        self.value = self.body.get(key, False)
        self.setChecked(self.value)
        self.clicked.connect(self._on_clicked)

    @pyqtSlot()
    def _on_clicked(self):
        """Handles clicked events.
        """
        self.value = self.isChecked()
        set_value_or_del_key(
            self.body,
            self._truth_fn(self.value),
            self.key,
            self.value
        )
        self.valueChanged.emit()


class SimpleComboBoxPropertyWidget(QComboBox):
    """A simple combobox property editor widget.
    """

    value: str
    valueChanged = pyqtSignal()

    def __init__(
            self,
            key: str,
            body: {},
            choices: [str],
            placeholder: str = '',
            truth_fn: Callable = bool,
            parent: QWidget = None):
        """Initialize the widget.

        Limitation: this widget treats `''` as a non-selectable value.

        :param key: annotation key
        :param body: annotation body (container)
        :param choices: list of values that may be selected
        :param placeholder: text to display when no value is selected
        :param truth_fn: function applied to value to determine whether it should be set or dropped from body
        :param parent: parent widget
        """
        super(SimpleComboBoxPropertyWidget, self).__init__(parent=parent)
        self.key, self.body = key, body
        self._truth_fn = truth_fn
        self.value = self.body.get(self.key, '')
        self.addItem('')
        self.addItems(choices)
        self.setPlaceholderText(placeholder)
        if isinstance(self.value, str):  # ignore non-str values
            self.setCurrentIndex(self.findText(self.value) or -1)
        self.currentIndexChanged.connect(self._on_index_changed)

    @pyqtSlot()
    def _on_index_changed(self):
        self.value = self.currentText()
        set_value_or_del_key(
            self.body,
            self._truth_fn(self.value),
            self.key,
            self.value
        )
        self.valueChanged.emit()


class CommentDisplayWidget(SimpleComboBoxPropertyWidget):
    """Widget for `comment_display` property.
    """

    def __init__(
            self,
            body: dict,
            key: str = 'comment_display',
            choices: iter = frozenset(['inline', 'tooltip']),
            placeholder: str = 'Select a comment display mode',
            truth_fn: Callable = bool,
            parent: QWidget = None
    ):
        """Initialize the widget.
        """
        super(CommentDisplayWidget, self).__init__(
            key,
            body,
            choices,
            placeholder=placeholder,
            truth_fn=truth_fn,
            parent=parent
        )


class MultipleChoicePropertyWidget(QWidget):
    """A multiple choice property editor widget.
    """

    value: Any
    valueChanged = pyqtSignal()

    def __init__(
            self,
            key: str,
            body: {},
            choices: dict,
            other_key: str = 'Other',
            other_widget: QWidget = None,
            layout: QBoxLayout = None,
            truth_fn: Callable = lambda x: x is not None,
            parent: QWidget = None):
        """Initialize the widget.

        Limitation: 'other_widget' must have a 'value' attribute.

        :param key: annotation key
        :param body: annotation body (container)
        :param choices: key-value pairs of choices
        :param other_key: the label and key for the 'other' selection; must not collide with keys in 'choices'
        :param other_widget: another widget for handling 'other'
        :param layout: the desired layout of the child widgets (defaults to QHBoxLayout)
        :param truth_fn: function applied to value to determine whether it should be set or dropped from body
        :param parent: parent widget
        """
        super(MultipleChoicePropertyWidget, self).__init__(parent=parent)
        self.key, self.body, self.choices = key, body, choices
        self.other_key, self.other_widget = other_key, other_widget
        self._truth_fn = truth_fn
        self.value = self.body.get(key)

        # apply layout
        if layout is None:
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
        layout.setParent(self)
        self.setLayout(layout)

        # button group
        self.buttonGroup = QButtonGroup(self)
        self.buttonGroup.buttonClicked.connect(self._on_buttonGroup_clicked)

        # choices
        for k, v in choices.items():
            rbutton = QRadioButton(k, parent=self)
            self.buttonGroup.addButton(rbutton)
            layout.addWidget(rbutton)
            if self.value == v:  # test if this button's value is found
                rbutton.setChecked(True)

        # other
        if other_widget:
            assert hasattr(other_widget, 'value'), "'other_widget' must have 'value' attribute"
            if hasattr(other_widget, 'valueChanged'):
                self.other_widget.valueChanged.connect(self._on_other_widget_valueChanged)
            rbutton = QRadioButton(other_key, parent=self)
            self.buttonGroup.addButton(rbutton)
            layout.addWidget(rbutton)
            layout.addWidget(other_widget)
            if self.value and self.value not in choices.values():  # test if 'other' value found
                rbutton.setChecked(True)
            else:
                other_widget.setEnabled(False)

    @pyqtSlot()
    def _on_other_widget_valueChanged(self):
        """Handle changes from other_widget.
        """
        self.value = self.other_widget.value
        # ...set value in annotation
        set_value_or_del_key(
            self.body,
            self._truth_fn(self.value),
            self.key,
            self.value
        )
        # ...emit signal
        self.valueChanged.emit()

    @pyqtSlot()
    def _on_buttonGroup_clicked(self):
        """Handles buttonGroup click even.
        """
        # ...get currently selected choice
        choice_key = self.buttonGroup.checkedButton().text()
        # ...get value from control state
        if choice_key == self.other_key:
            self.value = self.other_widget.value
            self.other_widget.setEnabled(True)
        else:
            self.value = self.choices[choice_key]
            if self.other_widget:
                self.other_widget.setEnabled(False)
        # ...set value in annotation
        set_value_or_del_key(
            self.body,
            self._truth_fn(self.value),
            self.key,
            self.value
        )
        # ...emit signal
        self.valueChanged.emit()


class SimpleNestedPropertyManager(QObject):
    """A simple manager for nested properties.

    In an annotation `body`, such as:
    ```
    {...
        "foo": { "bar": 1, "baz": 2 }
    ...}
    ```
    Here `foo` is the name of the nested property container, while `bar` and `baz` are its nested properties. The
    container will listen for signals from components and if `foo` is empty (`{}`) it will remove `foo` from the
    parent annotation `body`. If `foo` is non-empty it will add itself into the annotation `body`.

    In order to manage the nested properties passed to edit widgets, the manager must be instantiated first, and its
    `value` attribute should be passed to other edit widgets as the container for the specific nested property that
    they manage.

    ```
    manager = SimpleNestedPropertyManager('foo', annotations, parent=fooWidget)
    barWidget = SimpleWidget('bar', manager.value, ...)
    barWidget.valueChanged.connect(mgr.onValueChanged)
    ```

    Managers can be nested and listen for changes from subordinate managers by connecting to their `valueChanged`
    signal.

    *Note*: This object is not a display widget.
    """

    value: dict
    valueChanged = pyqtSignal()

    def __init__(self, key: str, body: dict, truth_fn: Callable = bool, parent: Union[QObject, QWidget, None] = None):
        """Initialize the container.

        :param key: the key of the nested property container.
        :param body: the annotation body, in which `key` _may_ be found
        :param truth_fn: function applied to value to determine whether it should be set or dropped from body
        :param parent: the parent object
        """
        super(SimpleNestedPropertyManager, self).__init__(parent=parent)
        self.key, self.body = key, body
        self._truth_fn = truth_fn
        # ...defensively get the value, ensuring that it is a dictionary
        self.value = self.body.get(self.key)
        if not isinstance(self.value, dict):
            self.value = {}

    @pyqtSlot()
    def onValueChanged(self):
        """Listens for changes and sets or removes nested property if it satisfies truth function.
        """
        set_value_or_del_key(
            self.body,
            self._truth_fn(self.value),
            self.key,
            self.value
        )
        self.valueChanged.emit()
