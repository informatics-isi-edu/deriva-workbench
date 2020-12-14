"""Workbench background tasks.
"""
from deriva.core import format_exception, annotation
from deriva.qt import Task
from .base import WorkbenchTask
from .dump import DumpAnnotationsTask, RestoreAnnotationsTask


class SessionQueryTask(WorkbenchTask):
    """Queries the server-side `session` resource.
    """

    def __init__(self, connection, parent=None):
        super(SessionQueryTask, self).__init__(connection, parent)

    def result_callback(self, success, result):
        self.set_status(success,
                        "Session query success" if success else "Session query failure",
                        "" if success else format_exception(result),
                        result.json() if success else None)

    def query(self):
        self.task = Task(self.connection["server"].get_authn_session, [], self.result_callback)
        self.start()


class FetchCatalogModelTask(WorkbenchTask):
    """Fetches the catalog schema resource.
    """

    def __init__(self, connection, parent=None):
        super(FetchCatalogModelTask, self).__init__(connection, parent)
        assert connection.get('catalog')

    def result_callback(self, success, result):
        self.set_status(success,
                        "Fetch catalog model success." if success else "Fetch catalog model failure.",
                        "" if success else format_exception(result),
                        result if success else None)

    def fetch(self):
        self.task = Task(self.connection['catalog'].getCatalogModel, [], self.result_callback)
        self.start()


class ModelApplyTask(WorkbenchTask):
    """Applies the changes to the catalog configuration (acls and annotations).
    """

    def __init__(self, model_obj, connection, parent=None):
        super(ModelApplyTask, self).__init__(connection, parent)
        assert connection.get('catalog'), 'Invalid server connection. Must have "catalog" property.'
        assert model_obj and hasattr(model_obj, 'apply'), 'Invalid catalog model object. Must have "apply" attribute.'
        self.model_obj = model_obj

    def result_callback(self, success, result):
        self.set_status(success,
                        "Update catalog model success." if success else "Update catalog model failure.",
                        "" if success else format_exception(result),
                        result if success else None)

    def start(self):
        self.task = Task(
            self.model_obj.apply,
            [],
            self.result_callback
        )
        super(ModelApplyTask, self).start()


class ValidateAnnotationsTask(WorkbenchTask):
    """Validates annotations for the selected model object.
    """

    def __init__(self, model_obj, connection, parent=None):
        super(ValidateAnnotationsTask, self).__init__(connection, parent)
        assert connection.get('catalog')
        self.model_obj = model_obj

    def result_callback(self, success, result):
        self.set_status(success,
                        "Validation task success." if success else "Validation task failed.",
                        "" if success else format_exception(result),
                        result if success else None)

    def validate(self):
        self.task = Task(annotation.validate, [self.model_obj], self.result_callback)
        self.start()
