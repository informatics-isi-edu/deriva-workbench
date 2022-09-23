"""Workbench configuration options dialog.
"""
import os
import re
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, \
    QGroupBox, QComboBox, QCheckBox, QMessageBox, QDialogButtonBox, QFormLayout, QFileDialog
from deriva.core import stob

__servers__ = 'servers'
__deboog__ = 'debug'
__host__ = 'host'
__desc__ = 'desc'
__catalog_id__ = 'catalog_id'
__directory__ = 'directory'
__default__ = 'default'
__cookie_persistence__ = 'cookie_persistence'

def _warningMessageBox(parent, text, detail):
    """Displays a warning message.
    """
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle("Attention Required")
    msg.setText(text)
    msg.setInformativeText(detail)
    msg.exec_()


def _server_display_name(server):
    """Returns a display name for the server entry.
    """
    return "%s [host: %s, catalog id: %s]" % (
        server.get(__desc__, "none"),
        server.get(__host__, "none"),
        server.get(__catalog_id__, "none")
    )


class OptionsDialog(QDialog):
    """Configuration options dialog."""

    def __init__(self, parent, selected, config):
        """Initialize the options dialog.

        :param parent: parent widget
        :param selected: selected connection dictionary
        :param config: configuration dictionary
        """
        super(OptionsDialog, self).__init__(parent)
        assert config is not None and isinstance(config, dict), "Invalid server configuration object"
        assert selected is None or isinstance(selected, dict), "Invalid selected server configuration"

        # Window and title
        self.setWindowTitle(self.tr("Configuration Options"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.addStretch(1)

        # Servers Group Box
        serversGroupBox = QGroupBox(self.tr("Servers"), self)
        serversLayout = QHBoxLayout()
        serversLayout.addWidget(QLabel(self.tr("Server")))
        # ...combo box
        self.serverComboBox = QComboBox()
        self.serverComboBox.setEditable(False)
        self.serverComboBox.setMinimumContentsLength(50)
        serversLayout.addWidget(self.serverComboBox)
        serversLayout.addStretch(1)
        # ...add button
        addServerButton = QPushButton(self.tr("Add"), self)
        addServerButton.clicked.connect(self.onServerAdd)
        serversLayout.addWidget(addServerButton)
        # ...edit button
        self.editServerButton = QPushButton(self.tr("Edit"), self)
        self.editServerButton.clicked.connect(self.onServerEdit)
        serversLayout.addWidget(self.editServerButton)
        # ...remove button
        self.removeServerButton = QPushButton(self.tr("Remove"), self)
        self.removeServerButton.clicked.connect(self.onServerRemove)
        serversLayout.addWidget(self.removeServerButton)
        # ...groupbox layout
        serversGroupBox.setLayout(serversLayout)
        layout.addWidget(serversGroupBox)

        # Populate servers from configuration
        servers = config.get(__servers__, [])
        if not servers:
            self.editServerButton.setEnabled(False)
            self.removeServerButton.setEnabled(False)
        else:
            index = selected_index = default_index = 0
            for server in servers:
                self.serverComboBox.insertItem(index, _server_display_name(server), server.copy())
                if selected and not selected_index and all(server.get(key) == selected.get(key) for key in [__host__, __catalog_id__]):
                    selected_index = index
                if not default_index and server.get(__default__, False):
                    default_index = index
                index += 1
            self.editServerButton.setEnabled(index > 0)
            self.serverComboBox.setCurrentIndex(selected_index or default_index)

        # Miscellaneous Group Box
        miscGroupBox = QGroupBox(self.tr("Miscellaneous"), self)
        miscLayout = QHBoxLayout()
        self.debugCheckBox = QCheckBox(self.tr("Enable debug logging"))
        self.debugCheckBox.setChecked(config.get(__deboog__, False))
        miscLayout.addWidget(self.debugCheckBox)
        miscGroupBox.setLayout(miscLayout)
        layout.addWidget(miscGroupBox)

        # Button Box
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    @property
    def config(self):
        """Configuration results."""
        return {
            __deboog__: self.debugCheckBox.isChecked(),
            __servers__: [
                self.serverComboBox.itemData(i, Qt.UserRole) for i in range(self.serverComboBox.count())
            ]
        }

    @property
    def selected(self):
        """Selected server entry."""
        return self.serverComboBox.currentData(Qt.UserRole)

    @pyqtSlot()
    def onServerAdd(self):
        """Handle server add signal.
        """
        server = {}
        dialog = ServerDialog(self, server)
        ret = dialog.exec_()
        if QDialog.Accepted == ret:
            if not server:
                return  # this should never happen, since the dialog validates

            # check for identical entry
            index = self.serverComboBox.findText(_server_display_name(server), Qt.MatchExactly)
            if index > -1:
                _warningMessageBox(self.parent(), self.tr("Server entry already exists!"),
                                   "A connection configuration for this hostname already exists. "
                                   "Please edit that configuration directly if you wish to make changes to it.")
                return

            # update ui controls
            index = self.serverComboBox.count()
            self.serverComboBox.insertItem(index, _server_display_name(server), server)
            self.serverComboBox.setCurrentIndex(index)
            self.editServerButton.setEnabled(True)
            self.removeServerButton.setEnabled(True)

    @pyqtSlot()
    def onServerEdit(self):
        """Handle server edit signal.
        """
        index = self.serverComboBox.currentIndex()
        server = self.serverComboBox.itemData(index, Qt.UserRole)
        dialog = ServerDialog(self, server)
        ret = dialog.exec_()
        if QDialog.Accepted == ret:
            self.serverComboBox.setItemText(index, _server_display_name(server))

    @pyqtSlot()
    def onServerRemove(self):
        """Handle server remove signal.
        """
        # Remove server entry
        index = self.serverComboBox.currentIndex()
        self.serverComboBox.removeItem(index)
        # ...set next default
        for x in range(self.serverComboBox.count()):
            current = self.serverComboBox.itemData(x, Qt.UserRole)
            if current[__default__] is True:
                self.serverComboBox.setCurrentIndex(x)

        # Disable server edit button if none left
        if not self.serverComboBox.count():
            self.editServerButton.setEnabled(False)
            self.removeServerButton.setEnabled(False)


class ServerDialog(QDialog):
    """Server settings configuration dialog.
    """

    def __init__(self, parent, server):
        super(ServerDialog, self).__init__(parent)
        assert server is not None and isinstance(server, dict)
        self.server = server

        # window title and layout
        self.setWindowTitle(self.tr("Server Configuration"))
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Server group box
        serversLayout = QFormLayout(self)
        self.serverGroupBox = QGroupBox(self.tr("Server Connection Settings"), self)
        self.serverGroupBox.setLayout(serversLayout)
        layout.addWidget(self.serverGroupBox)
        # ...hostname
        self.hostnameTextBox = QLineEdit()
        self.hostnameTextBox.setText(server.get(__host__, ""))
        serversLayout.addRow("Host", self.hostnameTextBox)
        # ...description
        self.descriptionTextBox = QLineEdit()
        self.descriptionTextBox.setText(server.get(__desc__, ""))
        serversLayout.addRow("Description", self.descriptionTextBox)
        # ...catalog id
        self.catalogIDTextBox = QLineEdit()
        self.catalogIDTextBox.setText(str(server.get(__catalog_id__, 1)))
        serversLayout.addRow("Catalog ID", self.catalogIDTextBox)

        # Dump/Restore location group box
        dumpLocationGroupBox = QGroupBox("Dump and Restore Directory", parent=self)
        dumpLocationLayout = QHBoxLayout(dumpLocationGroupBox)
        dumpLocationGroupBox.setLayout(dumpLocationLayout)
        layout.addWidget(dumpLocationGroupBox)
        # ...path
        self.pathLine = QLineEdit(server.get(__directory__), dumpLocationGroupBox)
        self.pathLine.setReadOnly(True)
        dumpLocationLayout.addWidget(self.pathLine)
        # ...browse
        browseButton = QPushButton(self.tr("Browse"), parent=dumpLocationGroupBox)
        browseButton.clicked.connect(self._on_browseButton_clicked)
        dumpLocationLayout.addWidget(browseButton)

        # Options group box
        self.serverOptionsGroupBox = QGroupBox(self.tr("Options"), self)
        optionsLayout = QHBoxLayout()
        self.serverOptionsGroupBox.setLayout(optionsLayout)
        layout.addWidget(self.serverOptionsGroupBox)
        # ...default
        self.defaultServer = QCheckBox(self.tr("Set as &Default"), parent)
        self.defaultServer.setChecked(stob(server.get(__default__, False)))
        optionsLayout.addWidget(self.defaultServer)
        # ...cookie persistence
        self.cookie_persistence = QCheckBox(self.tr("&Stay logged in"), parent)
        self.cookie_persistence.setChecked(stob(server.get(__cookie_persistence__, False)))
        optionsLayout.addWidget(self.cookie_persistence)

        # Button Box
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    @pyqtSlot()
    def _on_browseButton_clicked(self):
        """Handle browse button clicked event.
        """
        path = QFileDialog.getExistingDirectory(
            parent=self,
            caption=self.tr("Select Directory"),
            directory=self.pathLine.text(),
            options=QFileDialog.ShowDirsOnly)

        if path:
            self.pathLine.setText(os.path.normpath(path))


    def accept(self):
        """Handle dialog accept.
        """
        # validate host name
        host = self.hostnameTextBox.text()
        hostname = re.sub("(?i)^.*https?://", '', host)
        if not hostname:
            _warningMessageBox(self.parent(),
                               self.tr("Please enter a valid hostname."),
                               "For example: \'www.host.com\' or \'localhost\', etc.")
            return False

        # validate catalog identifier
        catalog_id = self.catalogIDTextBox.text()
        if not catalog_id:
            _warningMessageBox(self.parent(),
                               self.tr("Please enter a valid catalog identifier or alias."),
                               "This field cannot be left blank.")
            return False

        # validate description
        desc = self.descriptionTextBox.text()
        if not desc:
            _warningMessageBox(self.parent(),
                               self.tr("Please enter a short description."),
                               "The short description is used throughout the application to help you quickly identify "
                               "the server connection.")
            return False

        # validate path
        path = self.pathLine.text()
        if not path:
            _warningMessageBox(self.parent(),
                               self.tr("Please pick a directory for local dump and restore"),
                               "The directory is used to dump and restore annotations from a local copy on disk.")
            return False

        # take checkbox settings
        self.server[__host__] = hostname
        self.server[__catalog_id__] = catalog_id
        self.server[__desc__] = desc
        self.server[__directory__] = path
        self.server[__default__] = self.defaultServer.isChecked()
        self.server[__cookie_persistence__] = self.cookie_persistence.isChecked()
        super(ServerDialog, self).accept()
