"""JSON editors for bare schema viewing and bare annotation editing.
"""
import json
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSlot
from deriva.qt.common.json_editor import CodeEditor, JSONSyntaxHighlighter


class JSONEditor(CodeEditor):
    """A simple JSON code editor."""

    def __init__(self, data=None):
        super(JSONEditor, self).__init__()
        self.highlighter = JSONSyntaxHighlighter(self.document())
        self.setReadOnly(True)
        font = QFont()
        font.setFamily('Courier')
        font.setFixedPitch(True)
        font.setPointSize(12)
        self.setFont(font)
        if data:
            self.data = data

    @property
    def data(self):
        return json.loads(
            self.toPlainText()
        )

    @data.setter
    def data(self, value):
        self.setPlainText(
            json.dumps(value, indent=2)
        )


class AnnotationEditor(JSONEditor):
    """A JSON editor for schema annotations."""

    def __init__(self, data=None):
        super(AnnotationEditor, self).__init__()
        self.setReadOnly(False)
        self.textChanged.connect(self.on_textChanged)
        self._data = None
        self._parent = None
        self._tag = None
        self._body = None
        if data:
            self.data = data

    @property
    def data(self):
        if self._data is None:
            return None

        assert isinstance(self._data, dict)
        self._data.update(
            body=json.loads(self.toPlainText())
        )
        return self._data

    @data.setter
    def data(self, value):
        assert isinstance(value, dict) and 'parent' in value
        self._data = value
        self._parent = value['parent']
        self._tag = value.get('tag')
        if self._tag:
            self._body = self._parent.annotations[self._tag]
        else:
            self._body = self._parent.annotations

        self.setPlainText(
            json.dumps(self._body, indent=2)
        )

    @pyqtSlot()
    def on_textChanged(self):
        try:
            self._body = json.loads(self.toPlainText())
            if self._tag:
                self._parent.annotations[self._tag] = self._body
            else:
                self._parent.annotations = self._body
        except Exception:
            pass
