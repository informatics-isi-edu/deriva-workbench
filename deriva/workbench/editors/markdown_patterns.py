"""Widgets for markdown pattern and related properties.
"""
from typing import Callable
from PyQt5.QtWidgets import QWidget, QFormLayout, QTextEdit, QVBoxLayout
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from .common import set_value_or_del_key, SubsetSelectionWidget, SimpleComboBoxPropertyWidget


class MarkdownPatternForm(QWidget):
    """Markdown Pattern Form Widget.
    """

    valueChanged = pyqtSignal()

    def __init__(
            self, field_keys: [(str, str)],
            body: dict,
            include_template_engine: bool = False,
            include_wait_for: bool = False,
            sourcekeys: list = None,
            parent: QWidget = None):
        """Initialize the form.

        :param field_keys: list of (key, label) tuples where key is a key in the annotation body and label is a user friendly label
        :param body: the body of the annotation
        :param include_template_engine: include 'template_engine' property
        :param include_wait_for: include 'wait_for' property
        :param sourcekeys: source keys that may be selected for the value of the 'wait_for' property
        :param parent: parent widget
        """
        super(MarkdownPatternForm, self).__init__(parent=parent)
        self._field_keys, self._body = field_keys, body

        # form
        self.form = QFormLayout(self)
        self.setLayout(self.form)
        self.setAutoFillBackground(True)

        # add pattern fields
        self._markdown_pattern_fields = {}
        for key, label in self._field_keys:
            mdField = QTextEdit(self._body.get(key, ''), parent=self)
            mdField.setPlaceholderText('Enter markdown pattern')
            mdField.textChanged.connect(self._on_value_changed)
            self._markdown_pattern_fields[key] = mdField
            self.form.addRow(label, mdField)

        # template_engine
        if include_template_engine:
            widget = TemplateEngineWidget(self._body, parent=self)
            widget.valueChanged.connect(self._on_value_changed)
            self.form.addRow('Template Engine', widget)


        # wait_for
        if include_wait_for:
            widget = WaitForWidget(self._body, sourcekeys, parent=self)
            widget.valueChanged.connect(self._on_value_changed)
            self.form.addRow('Wait For', widget)

    @property
    def value(self) -> dict:
        """Returns the body since it contains the set of properties managed by this widget.
        """
        return self._body

    @pyqtSlot()
    def _on_value_changed(self):
        """Handles changes to the markdown fields.
        """
        for key, _ in self._field_keys:
            text = self._markdown_pattern_fields[key].toPlainText()
            set_value_or_del_key(
                self._body,
                bool(text),
                key,
                text
            )
            self.valueChanged.emit()


class WaitForWidget(QWidget):
    """Widget for the 'wait_for' property.
    """

    value: list
    valueChanged = pyqtSignal()

    def __init__(
            self,
            body: dict,
            sourcekeys: list,
            key: str = 'wait_for',
            truth_fn: Callable = bool,
            parent: QWidget = None):
        """Initialize the widget.

        :param body: the annotation that contains the property 'key'
        :param sourcekeys: list of source key strings to choose from
        :param key: the annotation property key (default: 'wait_for')
        :param truth_fn: truth function used for conditional set or remove decision
        :param parent: the parent widget
        """
        super(WaitForWidget, self).__init__(parent=parent)
        self.key, self.body = key, body
        self._truth_fn = truth_fn
        self.value = self.body.get(key)
        if not isinstance(self.value, list):
            self.value = []

        # layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # ...wait_for
        waitFor = SubsetSelectionWidget(
            self.value,
            sourcekeys,
            parent=self
        )
        waitFor.valueChanged.connect(self._on_waitFor_valueChanged)
        layout.addWidget(waitFor)

    @pyqtSlot()
    def _on_waitFor_valueChanged(self):
        """Handles changes to the wait_for field.
        """
        set_value_or_del_key(
            self.body,
            self._truth_fn(self.value),
            self.key,
            self.value
        )
        self.valueChanged.emit()


class TemplateEngineWidget(SimpleComboBoxPropertyWidget):
    """Widget for the `template_engine` property.
    """

    def __init__(
            self,
            body: dict,
            key: str = 'template_engine',
            choices: iter = frozenset(['handlebars', 'mustache']),
            placeholder: str = 'Select a template engine',
            truth_fn: Callable = bool,
            parent: QWidget = None
    ):
        """Initialize the widget.

        :param body: the annotation body that contains the property 'key'
        :param key: the annotation property key (default: 'template_engine')
        :param choices: options (default: standard template engines)
        :param placeholder: text when no value set
        :param truth_fn: truth function used for conditional set or remove decision
        :param parent: the parent widget
        """
        super(TemplateEngineWidget, self).__init__(
            key,
            body,
            choices,
            placeholder=placeholder,
            truth_fn=truth_fn,
            parent=parent
        )
