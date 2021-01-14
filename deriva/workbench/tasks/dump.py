"""Background tasks for dumping and restoring annotations.
"""
import json
import logging
import os
import re
from deriva.core import format_exception, ermrest_model as _erm
from deriva.qt import Task
from .base import WorkbenchTask

__annotations_json__ = 'annotations.json'
__meta_json__ = '.meta.json'

logger = logging.getLogger(__name__)


def _safe_model_name(name: str) -> str:
    """Returns a 'safe' model name for use in file system paths.
    """
    return re.sub('\W', '_', name)


def _dirname_for_model_object(model_obj, root: str):
    """Returns the (meta, dirname) for a given model object.

    Where:
     - 'meta' is a dictionary of metadata, mostly the unaltered names, of the model object
     - 'dirname' is a directory path name string

    :param model_obj: an ermrest model object
    :param root: the root directory name string
    :return: the (meta, dirname) pair
    """

    def _rel_path(*names: str) -> str:
        return os.sep.join([_safe_model_name(name) for name in names])

    if isinstance(model_obj, _erm.Model):
        meta = {
            'type': 'catalog'
        }
        dirname = root

    elif isinstance(model_obj, _erm.Schema):
        meta = {
            'type': 'schema',
            'name': model_obj.name
        }
        dirname = root + os.sep + _rel_path('schemas', model_obj.name)

    elif isinstance(model_obj, _erm.Table):
        meta = {
            'type': 'table',
            'schema': model_obj.schema.name,
            'table': model_obj.name
        }
        dirname = root + os.sep + _rel_path('schemas', model_obj.schema.name, 'tables', model_obj.name)

    elif isinstance(model_obj, _erm.Column):
        meta = {
            'type': 'column',
            'schema': model_obj.table.schema.name,
            'table': model_obj.table.name,
            'column': model_obj.name
        }
        dirname = root + os.sep + _rel_path('schemas', model_obj.table.schema.name, 'tables', model_obj.table.name,
                                            'columns', model_obj.name)

    elif isinstance(model_obj, _erm.Key):
        meta = {
            'type': 'key',
            'schema': model_obj.table.schema.name,
            'table': model_obj.table.name,
            'key': model_obj.constraint_name
        }
        dirname = root + os.sep + _rel_path('schemas', model_obj.table.schema.name, 'tables', model_obj.table.name,
                                            'keys', model_obj.constraint_name)

    elif isinstance(model_obj, _erm.ForeignKey):
        meta = {
            'type': 'foreign_key',
            'schema': model_obj.table.schema.name,
            'table': model_obj.table.name,
            'foreign_key': model_obj.constraint_name
        }
        dirname = root + os.sep + _rel_path('schemas', model_obj.table.schema.name, 'tables', model_obj.table.name,
                                            'foreign_keys', model_obj.constraint_name)

    else:
        raise TypeError('Unknown model object type %s' % type(model_obj))

    return meta, dirname


#
# Dump
#

class DumpAnnotationsTask(WorkbenchTask):
    """Serialize and save annotations for the selected model object.
    """

    def __init__(self, model_obj, connection, parent=None):
        super(DumpAnnotationsTask, self).__init__(connection, parent)
        assert connection.get('catalog')
        self.model_obj = model_obj

    def result_callback(self, success, result):
        self.set_status(success,
                        "Save annotations task success." if success else "Save annotations task failed.",
                        "" if success else format_exception(result),
                        result if success else None)

    def start(self):
        self.task = Task(
            dump_annotations_recursive,
            [self.model_obj, self.connection['directory']],
            self.result_callback
        )
        super(DumpAnnotationsTask, self).start()


def dump_annotations_recursive(model_obj, root:str) -> None:
    """Recursively dumps annotations of 'model_obj' in a model hierarchy rooted under 'root'.

    :param model_obj: an ermrest model object that has 'annotations' property
    :param root: directory path to which the annotations will be dumped
    """
    dump_annotations(model_obj, root)

    if isinstance(model_obj, _erm.Model):
        for schema in model_obj.schemas.values():
            dump_annotations_recursive(schema, root)
    elif isinstance(model_obj, _erm.Schema):
        for table in model_obj.tables.values():
            dump_annotations_recursive(table, root)
    elif isinstance(model_obj, _erm.Table):
        for column in model_obj.columns:
            dump_annotations(column, root)
        for key in model_obj.keys:
            dump_annotations(key, root)
        for fkey in model_obj.foreign_keys:
            dump_annotations(fkey, root)


def dump_annotations(model_obj, root: str) -> None:
    """Dumps annotations of 'model_obj' in a model hierarchy rooted under 'root'.

    :param model_obj: an ermrest model object that has 'annotations' property
    :param root: directory path under to the annotations will be dumped
    """
    assert hasattr(model_obj, 'annotations'), "Invalid model object"

    # ...get the dirname and metadata for the model object
    meta, dirname = _dirname_for_model_object(model_obj, root)

    # ...normalize pathname (just in case)
    dirname = os.path.normpath(dirname)

    # ...make dirs
    os.makedirs(dirname, exist_ok=True)

    # ...dump annotations
    with open(dirname + os.sep + __annotations_json__, 'w') as fp:
        json.dump(model_obj.annotations, fp, indent=2)

    # ...dump metadata
    with open(dirname + os.sep + __meta_json__, 'w') as fp:
        json.dump(meta, fp, indent=2)


#
# Restore
#

class RestoreAnnotationsTask(WorkbenchTask):
    """Serialize and Restore annotations for the selected model object.
    """

    def __init__(self, model_obj, connection, parent=None):
        super(RestoreAnnotationsTask, self).__init__(connection, parent)
        assert connection.get('catalog')
        self.model_obj = model_obj

    def result_callback(self, success, result):
        self.set_status(success,
                        "Restore annotations task success." if success else "Restore annotations task failed.",
                        "" if success else format_exception(result),
                        result if success else None)

    def start(self):
        self.task = Task(
            restore_annotations_recursive,
            [self.model_obj, self.connection['directory']],
            self.result_callback
        )
        super(RestoreAnnotationsTask, self).start()


def restore_annotations_recursive(model_obj, root: str) -> None:
    """Recursively restores annotations of 'model_obj' in a model hierarchy rooted under 'root'.

    :param model_obj: an ermrest model object that has 'annotations' property
    :param root: directory path from which the annotations will be restored
    """
    restore_annotations(model_obj, root)

    if isinstance(model_obj, _erm.Model):
        for schema in model_obj.schemas.values():
            restore_annotations_recursive(schema, root)
    elif isinstance(model_obj, _erm.Schema):
        for table in model_obj.tables.values():
            restore_annotations_recursive(table, root)
    elif isinstance(model_obj, _erm.Table):
        for column in model_obj.columns:
            restore_annotations(column, root)
        for key in model_obj.keys:
            restore_annotations(key, root)
        for fkey in model_obj.foreign_keys:
            restore_annotations(fkey, root)


def restore_annotations(model_obj, root: str) -> None:
    """Restores annotations of 'model_obj' in a model hierarchy rooted under 'root'.

    :param model_obj: an ermrest model object that has 'annotations' property
    :param root: directory path from which the annotations will be restored
    """
    assert hasattr(model_obj, 'annotations'), "Invalid model object"

    # ...get the dirname and metadata for the model object
    meta, dirname = _dirname_for_model_object(model_obj, root)

    # ...normalize pathname (just in case)
    dirname = os.path.normpath(dirname)

    # ...test if file exists
    filename = dirname + os.sep + __annotations_json__
    if not os.path.isfile(filename):
        logger.error("%s not found" % filename)
        return

    # ...restore annotations
    with open(dirname + os.sep + __annotations_json__, 'r') as fp:
        model_obj.annotations = json.load(fp)
