"""Workbench main window.
"""
import json
import logging
import os
import urllib.parse

from PyQt5.QtCore import Qt, QMetaObject, QThreadPool, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import qApp, QMainWindow, QWidget, QAction, QSizePolicy, QStyle, QSplitter, \
    QToolBar, QStatusBar, QVBoxLayout, QMessageBox, QDialog
from deriva.core import write_config, read_config, stob, DerivaServer, get_credential
from deriva.qt import EmbeddedAuthWindow, QPlainTextEditLogger, Task

from . import __version__
from .options import OptionsDialog
from .browser import SchemaBrowser
from .editor import SchemaEditor
from .tasks import SessionQueryTask, FetchCatalogModelTask, ModelApplyTask, ValidateAnnotationsTask


class WorkbenchWindow(QMainWindow):
    """Main window of the Workbench.
    """

    progress_update_signal = pyqtSignal(str)

    def __init__(self,
                 hostname,
                 catalog_id,
                 config_file,
                 credential_file=None,
                 cookie_persistence=True):
        super(WorkbenchWindow, self).__init__()
        qApp.aboutToQuit.connect(self.quitEvent)

        # auth properties
        self.auth_window = None
        self.identity = None

        # ui properties
        self.ui = _WorkbenchWindowUI(self)
        self.ui.browser.clicked.connect(self._on_browser_clicked)
        self.ui.browser.doubleClicked.connect(self._on_browser_double_clicked)
        self.setWindowTitle(self.ui.title)
        self.progress_update_signal.connect(self.updateProgress)

        # options
        self.config_file = config_file
        self.credential_file = credential_file
        self.cookie_persistence = cookie_persistence

        # connection properties
        self.connection = None

        # show and then run the configuration function
        self.show()
        self.config = None
        self.configure(hostname, catalog_id)

    @pyqtSlot()
    def _on_browser_double_clicked(self):
        self.ui.editor.data = self.ui.browser.current_selection

    @pyqtSlot()
    def _on_browser_clicked(self):
        if self.ui.browser.current_selection and hasattr(self.ui.browser.current_selection, 'annotations'):
            self.ui.actionValidate.setEnabled(True)
        else:
            self.ui.actionValidate.setEnabled(False)

    def configure(self, hostname, catalog_id):
        """Configures the connection properties.
        """
        if hostname:
            # if a hostname has been provided, it overrides whatever default host a given uploader is configured for
            self.connection = dict()
            self.connection["catalog_id"] = catalog_id
            if hostname.startswith("http"):
                url = urllib.parse.urlparse(hostname)
                self.connection["protocol"] = url.scheme
                self.connection["host"] = url.netloc
            else:
                self.connection["protocol"] = "https"
                self.connection["host"] = hostname
        elif not os.path.isfile(self.config_file):
            # create default config file
            self.updateStatus('Configuration file "%s" not found.' % self.config_file)
            self.config = {
                'debug': False,
                'servers': []
            }
        else:
            # load config file
            self.updateStatus('Loading configuration file "%s".' % self.config_file)
            try:
                self.config = read_config(config_file=self.config_file)
                if not self.config or not isinstance(self.config, dict):
                    raise Exception("Configuration file does not contain a valid workbench configuration.")
                for entry in self.config.get('servers', []):
                    self.connection = entry.copy()
                    if entry.get('default'):
                        break
            except IOError:
                raise IOError('IO error while attempting to read configuration file "%s"' % self.config_file)
            except json.JSONDecodeError as e:
                raise Exception('JSON parsing error while attempting to decode configuration file "%s": %s' % (self.config_file, str(e)))

        # instantiate the server...
        if not self.checkValidServer():
            return

        # setup debug logging
        if self.config.get('debug', False):
            logging.getLogger().setLevel(logging.DEBUG)

        # setup connection
        self.connection["server"] = DerivaServer(self.connection.get('protocol', 'https'),
                                                 self.connection['host'],
                                                 credentials=get_credential(self.connection['host']))

        # revise the window title to indicate host name
        self.setWindowTitle("%s (%s)" % (self.ui.title, self.connection["host"]))

        # auth window and get the session
        self.getNewAuthWindow()
        self.getSession()

    def checkValidServer(self):
        """Check for valid server connection properties.
        """
        self.restoreCursor()
        if self.connection and self.connection.get("host") and self.connection.get("catalog_id"):
            return True
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("No Server Configured")
        msg.setText("Add connection configuration now?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            self.on_actionOptions_triggered()  # todo: no return statement (?!)
        else:
            return False

    def getNewAuthWindow(self):
        if self.auth_window:
            if self.auth_window.authenticated():
                self.on_actionLogout_triggered()
            self.auth_window.destroy()
            del self.auth_window

        self.auth_window = \
            EmbeddedAuthWindow(self,
                               config=self.connection,
                               cookie_persistence=self.connection.get("cookie_persistence", self.cookie_persistence),
                               authentication_success_callback=self.onLoginSuccess,
                               log_level=logging.getLogger().getEffectiveLevel())
        self.ui.actionLogin.setEnabled(True)

    def onLoginSuccess(self, **kwargs):
        """On login success, setup the connection properties.
        """
        self.auth_window.hide()
        self.connection["credential"] = kwargs["credential"]
        server = DerivaServer(self.connection.get('protocol', 'https'), self.connection['host'], credentials=kwargs["credential"])
        self.connection["server"] = server
        self.connection["catalog"] = server.connect_ermrest(self.connection["catalog_id"])
        self.getSession()

    def getSession(self):
        """Get the user login 'session' resource.
        """
        qApp.setOverrideCursor(Qt.WaitCursor)
        logging.debug("Validating session: %s" % self.connection["host"])
        queryTask = SessionQueryTask(self.connection)
        queryTask.status_update_signal.connect(self.onSessionResult)
        queryTask.query()

    def enableControls(self):
        self.ui.actionUpdate.setEnabled(self.connection.get("catalog") is not None and self.identity is not None)  # and self.auth_window.authenticated())
        self.ui.actionRefresh.setEnabled(self.connection.get("catalog") is not None)
        self.ui.actionValidate.setEnabled(hasattr(self.ui.browser.current_selection, 'annotations'))
        self.ui.actionCancel.setEnabled(False)
        self.ui.actionOptions.setEnabled(True)
        self.ui.actionLogin.setEnabled(self.identity is None)  # not self.auth_window.authenticated())
        self.ui.actionLogout.setEnabled(self.identity is not None)  # self.auth_window.authenticated())
        self.ui.actionExit.setEnabled(True)
        # self.ui.browseButton.setEnabled(True)

    def disableControls(self):
        self.ui.actionUpdate.setEnabled(False)
        self.ui.actionRefresh.setEnabled(False)
        self.ui.actionValidate.setEnabled(False)
        self.ui.actionOptions.setEnabled(False)
        self.ui.actionLogin.setEnabled(False)
        self.ui.actionLogout.setEnabled(False)
        self.ui.actionExit.setEnabled(False)
        # self.ui.browseButton.setEnabled(False)

    def closeEvent(self, event=None):
        """Window close event handler.
        """
        self.disableControls()
        self.cancelTasks()
        if event:
            event.accept()

    def cancelTasks(self):
        """Cancel background tasks.
        """
        if not Task.INSTANCES:
            return

        qApp.setOverrideCursor(Qt.WaitCursor)
        Task.shutdown_all()
        self.statusBar().showMessage("Waiting for background tasks to terminate...")

        while True:
            qApp.processEvents()
            if QThreadPool.globalInstance().waitForDone(10):
                break

        self.statusBar().showMessage("All background tasks terminated successfully")
        self.restoreCursor()

    def restoreCursor(self):
        qApp.restoreOverrideCursor()
        qApp.processEvents()

    @pyqtSlot(str)
    def updateProgress(self, status):
        if status:
            self.statusBar().showMessage(status)

    @pyqtSlot(str, str)
    def updateStatus(self, status, detail=None, success=True):
        msg = status + ((": %s" % detail) if detail else "")
        logging.info(msg) if success else logging.error(msg)
        self.statusBar().showMessage(status)

    @pyqtSlot(str, str)
    def resetUI(self, status, detail=None, success=True):
        self.updateStatus(status, detail, success)
        self.enableControls()

    @pyqtSlot(str)
    def updateLog(self, text):
        self.ui.logTextBrowser.widget.appendPlainText(text)

    @pyqtSlot(bool, str, str, object)
    def onSessionResult(self, success, status, detail, result):
        self.restoreCursor()
        if success:
            self.identity = result["client"]["id"]
            display_name = result["client"]["full_name"]
            self.setWindowTitle("%s (%s - %s)" % (self.ui.title, self.connection["host"], display_name))
            self.updateStatus("Logged in.")
            self.connection["catalog"] = self.connection["server"].connect_ermrest(self.connection["catalog_id"])
            self.enableControls()
            self.fetchCatalogModel()
        else:
            self.updateStatus("Login required.")

    @pyqtSlot()
    def on_actionRefresh_triggered(self):
        # check if connected to a catalog
        if not self.connection["catalog"]:
            self.updateStatus("Cannot fetch model. Not connected to a catalog.")
            return

        # initiate fetch
        self.fetchCatalogModel()

    def fetchCatalogModel(self, reset=False):
        if reset:
            self.connection["catalog"] = self.connection["server"].connect_ermrest(self.connection["catalog_id"])
        fetchTask = FetchCatalogModelTask(self.connection)
        fetchTask.status_update_signal.connect(self.onFetchCatalogModelResult)
        fetchTask.fetch()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.ui.actionCancel.setEnabled(True)

    @pyqtSlot(bool, str, str, object)
    def onFetchCatalogModelResult(self, success, status, detail, result):
        self.restoreCursor()
        if success:
            self.ui.browser.setModel(result)
            self.ui.editor.data = None
            self.resetUI("Fetched catalog model...")
        else:
            self.resetUI(status, detail, success)

    @pyqtSlot()
    def on_actionValidate_triggered(self):
        """Triggered on "validate" action.
        """
        # check if connected to a catalog
        if not self.connection["catalog"]:
            self.updateStatus("Cannot validate annotations. Not connected to a catalog.")
            return

        # check if current selection has 'annotations' container
        current_selection = self.ui.browser.current_selection
        if not hasattr(current_selection, 'annotations'):
            self.updateStatus("Cannot validate annotations. Current selected object does not have 'annotations'.")

        # do validation
        self.validatAnnotations(current_selection)

    def validatAnnotations(self, current_selection):
        """Fires off annotation validation task.
        """
        assert hasattr(current_selection, 'annotations'), "Current selection does not have 'annotations'."
        task = ValidateAnnotationsTask(current_selection, self.connection)
        task.status_update_signal.connect(self.onValidateAnnotationsResult)
        task.validate()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.ui.actionCancel.setEnabled(True)

    @pyqtSlot(bool, str, str, object)
    def onValidateAnnotationsResult(self, success, status, detail, result):
        """Handles annotations validation results.
        """
        self.restoreCursor()
        if success:
            msg = "Found %d error(s) in the current object's annotations. See log display for additional details." % len(result)
            QMessageBox.information(
                self,
                "Validation Results",
                msg,
                QMessageBox.Ok
            )
            self.resetUI(msg)
        else:
            self.resetUI(status, detail, success)

    @pyqtSlot()
    def on_actionUpdate_triggered(self):
        model = self.ui.browser.model
        task = ModelApplyTask(model, self.connection)
        task.status_update_signal.connect(self.onModelApplyResult)
        task.apply()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.ui.actionCancel.setEnabled(True)

    @pyqtSlot(bool, str, str, object)
    def onModelApplyResult(self, success, status, detail, result):
        self.restoreCursor()
        if success:
            self.resetUI("Successfully updated catalog ACLs and annotations.")
        else:
            self.resetUI(status, detail, success)

    @pyqtSlot()
    def on_actionCancel_triggered(self):
        self.cancelTasks()
        self.resetUI("Ready.")

    @pyqtSlot()
    def on_actionLogin_triggered(self):
        if not self.auth_window:
            if self.checkValidServer():
                self.getNewAuthWindow()
            else:
                return
        self.auth_window.show()
        self.auth_window.login()

    @pyqtSlot()
    def on_actionLogout_triggered(self):
        self.setWindowTitle("%s (%s)" % (self.ui.title, self.connection["host"]))
        self.auth_window.logout()
        self.identity = None
        # todo: should reset the server object, remove credential
        self.enableControls()
        self.updateStatus("Logged out.")

    @pyqtSlot()
    def on_actionOptions_triggered(self):
        """Options button handler.
        """
        dialog = OptionsDialog(self, self.connection, self.config)
        ret = dialog.exec_()
        if QDialog.Accepted == ret:
            # ...save to file
            result = dialog.config
            if self.config != result:
                self.config = result
                self.updateStatus('Saving configuration to "%s"' % self.config_file)
                write_config(config_file=self.config_file, config=self.config)

            # ...update debug logging
            debug = dialog.config.get('default', False)
            logging.getLogger().setLevel(logging.DEBUG if debug else logging.INFO)

            # ...update selected connection
            selected = dialog.selected
            if selected and (not self.connection or any(self.connection.get(key) != selected.get(key) for key in ['host', 'catalog_id'])):
                self.updateStatus('Connecting to "%s" (catalog: %s).' % (selected['host'], str(selected['catalog_id'])))
                # initialize connection and deriva server
                self.connection = selected.copy()
                self.connection["server"] = DerivaServer(self.connection.get('protocol', 'https'),
                                                         self.connection['host'],
                                                         credentials=get_credential(self.connection['host']))

                # clear out any schema editor state
                self.ui.browser.setModel(None)
                self.ui.editor.data = None

                # begin login sequence
                qApp.setOverrideCursor(Qt.WaitCursor)
                self.restoreCursor()
                if not self.checkValidServer():
                    return
                self.setWindowTitle("%s (%s)" % (self.ui.title, self.connection["host"]))
                self.getNewAuthWindow()
                self.getSession()

    @pyqtSlot()
    def on_actionExit_triggered(self):
        self.closeEvent()
        qApp.quit()

    def quitEvent(self):
        if self.auth_window:
            self.auth_window.logout(self.logoutConfirmation())
        qApp.closeAllWindows()

    def logoutConfirmation(self):
        if self.auth_window and (not self.auth_window.authenticated() or not self.auth_window.cookie_persistence):
            return
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirm Action")
        msg.setText("Do you wish to completely logout of the system?")
        msg.setInformativeText("Selecting \"Yes\" will clear the login state and invalidate the editor user identity."
                               "\n\nSelecting \"No\" will keep your editor identity cached, which will allow you to "
                               "log back in without authenticating until your session expires.\n\nNOTE: Select \"Yes\" "
                               "if this is a shared system using a single user account.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            return True
        return False


class _WorkbenchWindowUI(object):
    """Main workbench window UI layout and controls.
    """

    def __init__(self, mainWin):
        """Initialize the main window UI.

        :param mainWin: QMainWindow widget for the application.
        """
        self.title = "DERIVA Workbench v%s" % __version__

        # Main Window
        mainWin.setObjectName("WorkbenchWindow")
        mainWin.setWindowTitle(mainWin.tr(self.title))
        mainWin.resize(1280, 1024)

        # Central Widget
        centralWidget = QWidget(mainWin)
        centralWidget.setObjectName("centralWidget")
        mainWin.setCentralWidget(centralWidget)
        self.verticalLayout = QVBoxLayout(centralWidget)
        self.verticalLayout.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")

        # Setup main body splitter
        self.browser = SchemaBrowser()
        self.editor = SchemaEditor()
        hsplitter = QSplitter(Qt.Horizontal)
        hsplitter.addWidget(self.browser)
        hsplitter.addWidget(self.editor)
        hsplitter.setSizes([300, 900])

        # Splitter for Log messages
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(hsplitter)

        # Log Widget
        self.logTextBrowser = QPlainTextEditLogger(centralWidget)
        self.logTextBrowser.widget.setObjectName("logTextBrowser")
        self.logTextBrowser.widget.setBackgroundVisible(False)
        self.logTextBrowser.widget.setStyleSheet(
            """
            QPlainTextEdit {
                    border: 1px solid grey;
                    border-radius: 3px;
            }
            """)
        self.splitter.addWidget(self.logTextBrowser.widget)

        # add splitter
        self.splitter.setSizes([800, 200])
        self.verticalLayout.addWidget(self.splitter)

        #
        # Actions
        #

        # Update
        self.actionUpdate = QAction(mainWin)
        self.actionUpdate.setObjectName("actionUpdate")
        self.actionUpdate.setText(mainWin.tr("Update"))
        self.actionUpdate.setToolTip(mainWin.tr("Update the catalog ACLs and annotations only"))
        self.actionUpdate.setShortcut(mainWin.tr("Ctrl+U"))
        self.actionUpdate.setEnabled(False)

        # Refresh
        self.actionRefresh = QAction(mainWin)
        self.actionRefresh.setObjectName("actionRefresh")
        self.actionRefresh.setText(mainWin.tr("Refresh"))
        self.actionRefresh.setToolTip(mainWin.tr("Refresh the catalog model from the server"))
        self.actionRefresh.setShortcut(mainWin.tr("Ctrl+R"))
        self.actionRefresh.setEnabled(False)

        # Validate
        self.actionValidate = QAction(mainWin)
        self.actionValidate.setObjectName("actionValidate")
        self.actionValidate.setText(mainWin.tr("Validate"))
        self.actionValidate.setToolTip(mainWin.tr("Validate annotations for the currently selected model object"))
        self.actionValidate.setShortcut(mainWin.tr("Ctrl+I"))
        self.actionValidate.setEnabled(False)

        # Cancel
        self.actionCancel = QAction(mainWin)
        self.actionCancel.setObjectName("actionCancel")
        self.actionCancel.setText(mainWin.tr("Cancel"))
        self.actionCancel.setToolTip(mainWin.tr("Cancel pending tasks"))
        self.actionCancel.setShortcut(mainWin.tr("Ctrl+P"))

        # Options
        self.actionOptions = QAction(mainWin)
        self.actionOptions.setObjectName("actionOptions")
        self.actionOptions.setText(mainWin.tr("Options"))
        self.actionOptions.setToolTip(mainWin.tr("Configure the application settings"))
        self.actionOptions.setShortcut(mainWin.tr("Ctrl+P"))

        # Login
        self.actionLogin = QAction(mainWin)
        self.actionLogin.setObjectName("actionLogin")
        self.actionLogin.setText(mainWin.tr("Login"))
        self.actionLogin.setToolTip(mainWin.tr("Login to the server"))
        self.actionLogin.setShortcut(mainWin.tr("Ctrl+G"))
        self.actionLogin.setEnabled(False)

        # Logout
        self.actionLogout = QAction(mainWin)
        self.actionLogout.setObjectName("actionLogout")
        self.actionLogout.setText(mainWin.tr("Logout"))
        self.actionLogout.setToolTip(mainWin.tr("Logout of the server"))
        self.actionLogout.setShortcut(mainWin.tr("Ctrl+O"))
        self.actionLogout.setEnabled(False)

        # Exit
        self.actionExit = QAction(mainWin)
        self.actionExit.setObjectName("actionExit")
        self.actionExit.setText(mainWin.tr("Exit"))
        self.actionExit.setToolTip(mainWin.tr("Exit the application"))
        self.actionExit.setShortcut(mainWin.tr("Ctrl+Z"))

        # Help
        self.actionHelp = QAction(mainWin)
        self.actionHelp.setObjectName("actionHelp")
        self.actionHelp.setText(mainWin.tr("Help"))
        self.actionHelp.setToolTip(mainWin.tr("Help"))
        self.actionHelp.setShortcut(mainWin.tr("Ctrl+H"))

        #
        # Tool Bar
        #

        # Main toolbar widget
        self.mainToolBar = QToolBar(mainWin)
        self.mainToolBar.setObjectName("mainToolBar")
        self.mainToolBar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.mainToolBar.setContextMenuPolicy(Qt.PreventContextMenu)
        mainWin.addToolBar(Qt.TopToolBarArea, self.mainToolBar)

        # Update
        self.mainToolBar.addAction(self.actionUpdate)
        self.actionUpdate.setIcon(qApp.style().standardIcon(QStyle.SP_FileDialogToParent))

        # Refresh
        self.mainToolBar.addAction(self.actionRefresh)
        self.actionRefresh.setIcon(qApp.style().standardIcon(QStyle.SP_BrowserReload))

        # Validate
        self.mainToolBar.addAction(self.actionValidate)
        self.actionValidate.setIcon(qApp.style().standardIcon(QStyle.SP_DialogApplyButton))

        # Cancel
        self.mainToolBar.addAction(self.actionCancel)
        self.actionCancel.setIcon(qApp.style().standardIcon(QStyle.SP_BrowserStop))
        self.actionCancel.setEnabled(False)

        # Options
        self.mainToolBar.addAction(self.actionOptions)
        self.actionOptions.setIcon(qApp.style().standardIcon(QStyle.SP_FileDialogDetailedView))

        # ...this spacer right justifies everything that comes after it
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mainToolBar.addWidget(spacer)

        # Login
        self.mainToolBar.addAction(self.actionLogin)
        self.actionLogin.setIcon(qApp.style().standardIcon(QStyle.SP_DialogApplyButton))

        # Logout
        self.mainToolBar.addAction(self.actionLogout)
        self.actionLogout.setIcon(qApp.style().standardIcon(QStyle.SP_DialogOkButton))

        # Exit
        self.mainToolBar.addAction(self.actionExit)
        self.actionExit.setIcon(qApp.style().standardIcon(QStyle.SP_DialogCancelButton))

        #
        # Status Bar
        #

        self.statusBar = QStatusBar(mainWin)
        self.statusBar.setToolTip("")
        self.statusBar.setStatusTip("")
        self.statusBar.setObjectName("statusBar")
        mainWin.setStatusBar(self.statusBar)

        # Configure logging
        self.logTextBrowser.widget.log_update_signal.connect(mainWin.updateLog)
        self.logTextBrowser.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self.logTextBrowser)

        # Finalize UI setup
        QMetaObject.connectSlotsByName(mainWin)
