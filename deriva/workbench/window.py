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
from .tasks import SessionQueryTask, FetchCatalogModelTask, ModelApplyTask, ValidateAnnotationsTask, \
    DumpAnnotationsTask, RestoreAnnotationsTask


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
        self.ui.browser.itemSelected.connect(self._on_browser_itemSelected)
        self.ui.browser.itemOpened.connect(self._on_browser_itemOpened)
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

    @classmethod
    def _connect_ermrest(cls, server, catalog_id):
        """Helper to connect ermrest catalog.
        """
        catalog = server.connect_ermrest(catalog_id)
        catalog.dcctx['cid'] = "gui/WorkbenchApp"
        return catalog

    @pyqtSlot()
    def _on_browser_itemOpened(self):
        self.ui.editor.data = self.ui.browser.lastItemOpened

    @pyqtSlot()
    def _on_browser_itemSelected(self):
        """Handles schema browser item selection event.

        The purpose is to enable actions, as appropriate for the currently selected model object.
        """
        self.enableControls()

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
        self.connection["catalog"] = self._connect_ermrest(server, self.connection["catalog_id"])
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
        """Conditionally, enable actions based on state of user session and schema browser.
        """
        # ...check the capabilities of currently selected item
        has_apply = hasattr(self.ui.browser.lastItemSelected, 'apply')
        has_annotations = hasattr(self.ui.browser.lastItemSelected, 'annotations')
        # ...enable actions
        self.ui.actionUpdate.setEnabled(has_apply and self.identity is not None)
        self.ui.actionRefresh.setEnabled(self.connection.get("catalog") is not None)
        self.ui.actionValidate.setEnabled(has_annotations)
        self.ui.actionDumpAnnotations.setEnabled(has_annotations)
        self.ui.actionRestoreAnnotations.setEnabled(has_annotations)
        self.ui.actionCancel.setEnabled(False)
        self.ui.actionOptions.setEnabled(True)
        self.ui.actionLogin.setEnabled(self.identity is None)
        self.ui.actionLogout.setEnabled(self.identity is not None)
        self.ui.actionExit.setEnabled(True)

    def disableControls(self, allow_cancel=False):
        """Disable all actions with option to allow cancel action.
        """
        self.ui.actionUpdate.setEnabled(False)
        self.ui.actionRefresh.setEnabled(False)
        self.ui.actionValidate.setEnabled(False)
        self.ui.actionDumpAnnotations.setEnabled(False)
        self.ui.actionRestoreAnnotations.setEnabled(False)
        self.ui.actionCancel.setEnabled(allow_cancel)
        self.ui.actionOptions.setEnabled(False)
        self.ui.actionLogin.setEnabled(False)
        self.ui.actionLogout.setEnabled(False)
        self.ui.actionExit.setEnabled(False)

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
            self.connection["catalog"] = self._connect_ermrest(self.connection["server"], self.connection["catalog_id"])
            self.enableControls()
            self.fetchCatalogModel()
        else:
            self.updateStatus("Login required.")

    #
    # actionRefresh
    #

    @pyqtSlot()
    def on_actionRefresh_triggered(self):
        """Handle actionRefresh event.
        """
        # check if connected to a catalog
        if not self.connection["catalog"]:
            self.updateStatus("Cannot fetch model. Not connected to a catalog.")
            return

        # initiate fetch
        self.fetchCatalogModel()

    def fetchCatalogModel(self, reset=False):
        """Fetch catalog model and refresh local state.
        """
        if reset:
            self.connection["catalog"] = self._connect_ermrest(self.connection["server"], self.connection["catalog_id"])
        fetchTask = FetchCatalogModelTask(self.connection)
        fetchTask.status_update_signal.connect(self.onFetchCatalogModelResult)
        fetchTask.fetch()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.disableControls(allow_cancel=True)

    @pyqtSlot(bool, str, str, object)
    def onFetchCatalogModelResult(self, success, status, detail, result):
        self.restoreCursor()
        if success:
            self.ui.browser.setModel(result)
            self.ui.editor.data = None
            self.resetUI("Fetched catalog model...")
        else:
            self.resetUI(status, detail, success)

    #
    # actionValidate
    #

    @pyqtSlot()
    def on_actionValidate_triggered(self):
        """Handle actionValidate event.
        """
        # check if connected to a catalog
        if not self.connection["catalog"]:
            self.updateStatus("Cannot validate annotations. Not connected to a catalog.")
            return

        # check if current selection has 'annotations' container
        model_obj = self.ui.browser.lastItemSelected
        if not hasattr(model_obj, 'annotations'):
            self.updateStatus("Cannot validate annotations. Current selected object does not have 'annotations'.")

        # do validation
        self.validatAnnotations(model_obj)

    def validatAnnotations(self, model_object):
        """Validate annotations for selected model object.
        """
        assert hasattr(model_object, 'annotations'), "Current selection does not have 'annotations' attribute."
        task = ValidateAnnotationsTask(model_object, self.connection)
        task.status_update_signal.connect(self.onValidateAnnotationsResult)
        task.validate()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.disableControls(allow_cancel=True)

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

    #
    # actionUpdate
    #

    @pyqtSlot()
    def on_actionUpdate_triggered(self):
        """Handles actionUpdate event.
        """
        # validate current selected model obj
        model_object = self.ui.browser.lastItemSelected
        if not hasattr(model_object, 'apply'):
            error = self.tr("Cannot apply annotations. Current selected object does not have 'apply' attribute.")
            QMessageBox.critical(
                self,
                self.tr("Failed to Apply Changes"),
                error
            )
            self.updateStatus(error)
        else:
            self.modelApply(model_object)

    def modelApply(self, model_object):
        """Apply model changes on model object.

        :param model_object: an ermrest model object
        """
        task = ModelApplyTask(model_object, self.connection)
        task.status_update_signal.connect(self.onModelApplyResult)
        task.start()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.disableControls(allow_cancel=True)

    @pyqtSlot(bool, str, str, object)
    def onModelApplyResult(self, success, status, detail, result):
        """Handles model apply results.
        """
        self.restoreCursor()
        if success:
            msg = self.tr("Successfully updated model annotations.")
            self.ui.editor.data = self.ui.browser.lastItemOpened
            self.resetUI(msg)
            QMessageBox.information(
                self,
                self.tr("Task Results"),
                msg,
                QMessageBox.Ok
            )
        else:
            self.resetUI(status, detail, success)

    #
    # actionDumpAnnotations
    #

    @pyqtSlot()
    def on_actionDumpAnnotations_triggered(self):
        """Handles actionDumpAnnotations event.
        """
        error = None

        # check if connected to a catalog
        if not self.connection.get("catalog"):
            error = self.tr("Not connected to a catalog.")

        # check if directory specified
        if not self.connection.get("directory"):
            error = self.tr("No directory to dump and restore annotations. Go to options and edit this server configuration.")

        # get current selected model obj
        model_object = self.ui.browser.lastItemSelected
        if not hasattr(model_object, 'annotations'):
            error = self.tr("Cannot dump annotations. Current selected object does not have 'annotations' property.")

        if error:
            QMessageBox.critical(
                self,
                self.tr("Failed to Dump Annotations"),
                error
            )
            self.updateStatus(error)
        else:
            self.dumpAnnotations(model_object)

    def dumpAnnotations(self, model_object):
        """Dumps annotations to local directory.

        :param model_object: a valid ermrest model object with 'annotations'
        """
        assert hasattr(model_object, 'annotations'), "Current selection does not have 'annotations'."
        task = DumpAnnotationsTask(model_object, self.connection)
        task.status_update_signal.connect(self.onDumpAnnotationsResult)
        task.start()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.disableControls(allow_cancel=True)

    @pyqtSlot(bool, str, str, object)
    def onDumpAnnotationsResult(self, success, status, detail, result):
        """Handles dump annotations results.
        """
        self.restoreCursor()
        if success:
            msg = self.tr("Annotations dumped successfully")
            QMessageBox.information(
                self,
                self.tr("Task Results"),
                msg,
                QMessageBox.Ok
            )
            self.resetUI(msg)
        else:
            self.resetUI(status, detail, success)

    #
    # actionRestoreAnnotations
    #

    @pyqtSlot()
    def on_actionRestoreAnnotations_triggered(self):
        """Handles actionRestoreAnnotations event.
        """
        error = None

        # check if connected to a catalog
        if not self.connection.get("catalog"):
            error = self.tr("Not connected to a catalog.")

        # check if directory specified
        if not self.connection.get("directory"):
            error = self.tr("No directory to dump and restore annotations. Go to options and edit this server configuration.")

        # get current selected model obj
        model_object = self.ui.browser.lastItemSelected
        if not hasattr(model_object, 'annotations'):
            error = self.tr("Cannot restore annotations. Current selected object does not have 'annotations' property.")

        if error:
            QMessageBox.critical(
                self,
                self.tr("Failed to Restore Annotations"),
                error
            )
            self.updateStatus(error)
        else:
            self.restoreAnnotations(model_object)

    def restoreAnnotations(self, model_object):
        """Restores annotations from local directory.

        :param model_object: a valid ermrest model object with 'annotations'
        """
        assert hasattr(model_object, 'annotations'), "Current selection does not have 'annotations'."
        task = RestoreAnnotationsTask(model_object, self.connection)
        task.status_update_signal.connect(self.onRestoreAnnotationsResult)
        task.start()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.disableControls(allow_cancel=True)

    @pyqtSlot(bool, str, str, object)
    def onRestoreAnnotationsResult(self, success, status, detail, result):
        """Handles restore annotations results.
        """
        self.restoreCursor()
        if success:
            self.ui.browser.reset()
            self.ui.editor.data = None
            msg = self.tr("Annotations restored successfully")
            QMessageBox.information(
                self,
                self.tr("Task Results"),
                msg,
                QMessageBox.Ok
            )
            self.resetUI(msg)
        else:
            self.resetUI(status, detail, success)

    #
    # actionCancel
    #

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

    #
    # actionLogout
    #

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
            if selected:
                if not self.connection or any(self.connection.get(key) != selected.get(key) for key in ['host', 'catalog_id']):
                    # case: new (host, catalog) combination... establish connection
                    self.updateStatus('Connecting to "%s" (catalog: %s).' % (selected['host'], str(selected['catalog_id'])))
                    # initialize connection and deriva server
                    self.connection = selected.copy()
                    self.connection["server"] = DerivaServer(self.connection.get('protocol', 'https'),
                                                             self.connection['host'],
                                                             credentials=get_credential(self.connection['host']))

                    # clear out any schema editor state
                    self.ui.browser.clear()
                    self.ui.editor.data = None

                    # begin login sequence
                    qApp.setOverrideCursor(Qt.WaitCursor)
                    self.restoreCursor()
                    if not self.checkValidServer():
                        return
                    self.setWindowTitle("%s (%s)" % (self.ui.title, self.connection["host"]))
                    self.getNewAuthWindow()
                    self.getSession()
                else:
                    # case: same (host, catalog_id)... still need to update the rest of the connection options
                    assert isinstance(self.connection, dict), "Invalid internal connection object"
                    self.connection.update(selected)

    #
    # actionExit
    #

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

        # Dump Annotations
        self.actionDumpAnnotations = QAction(mainWin)
        self.actionDumpAnnotations.setObjectName("actionDumpAnnotations")
        self.actionDumpAnnotations.setText(mainWin.tr("Dump"))
        self.actionDumpAnnotations.setToolTip(mainWin.tr("Dump annotations to disk for the currently selected model object hierarchy"))
        self.actionDumpAnnotations.setShortcut(mainWin.tr("Ctrl+S"))
        self.actionDumpAnnotations.setEnabled(False)

        # Restore Annotations
        self.actionRestoreAnnotations = QAction(mainWin)
        self.actionRestoreAnnotations.setObjectName("actionRestoreAnnotations")
        self.actionRestoreAnnotations.setText(mainWin.tr("Restore"))
        self.actionRestoreAnnotations.setToolTip(mainWin.tr("Restore annotations from dump files for the currently selected model object hierarchy"))
        self.actionRestoreAnnotations.setShortcut(mainWin.tr("Ctrl+S"))
        self.actionRestoreAnnotations.setEnabled(False)

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

        # separator -------------------
        self.mainToolBar.addSeparator()

        # Dump Annotations
        self.mainToolBar.addAction(self.actionDumpAnnotations)
        self.actionDumpAnnotations.setIcon(qApp.style().standardIcon(QStyle.SP_DialogSaveButton))

        # Restore Annotations
        self.mainToolBar.addAction(self.actionRestoreAnnotations)
        self.actionRestoreAnnotations.setIcon(qApp.style().standardIcon(QStyle.SP_DialogOpenButton))

        # separator -------------------
        self.mainToolBar.addSeparator()

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
