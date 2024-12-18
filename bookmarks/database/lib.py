"""
This module provides the :class:`BookmarkDB` class, which interfaces with an SQLite database for managing bookmark data.

The app stores various bookmark-related properties (for example, descriptions, dimensions, flags, configuration
values) in an SQLite database keyed by a path hash. Each bookmark's database file resides at the root of its cache folder.


Use :func:`get` to retrieve a cached, thread-specific database controller:

.. code-block:: python
    :linenos:

    from bookmarks import database

    db = database.get(server, job, root)
    width = db.value(db.source(), 'width', database.BookmarkTable)

    db = database.get(*common.active('root', args=True))
    height = db.value(db.source(), 'height', database.BookmarkTable)

You can group multiple database changes using the built-in context manager:

.. code-block:: python
    :linenos:

    from bookmarks import database

    db = database.get(*common.active('root', args=True))
    with db.connection():
        db.set_value(source, 'description', 'New description', database.AssetTable)
        db.set_value(source, 'width', 1920, database.BookmarkTable)
        db.set_value(source, 'height', 1080, database.BookmarkTable)

"""

import base64
import functools
import json
import sqlite3

from PySide2 import QtCore

from .. import common
from .. import log

__all__ = [
    'AssetTable',
    'BookmarkTable',
    'TemplateDataTable',
    'InfoTable',
    'TABLES',
    'get',
    'remove_db',
    'remove_all_connections',
    'b64encode',
    'b64decode',
    'sleep',
    'set_flag',
    'load_json',
    'convert_return_values',
    'BookmarkDB',
]

AssetTable = 'AssetData'
BookmarkTable = 'BookmarkData'
TemplateDataTable = 'TemplateData'
InfoTable = 'InfoData'

TABLES = {
    AssetTable: {
        'id': {'sql': 'TEXT PRIMARY KEY COLLATE NOCASE', 'type': str},
        'description': {'sql': 'TEXT', 'type': str},
        'notes': {'sql': 'TEXT', 'type': dict},
        'flags': {'sql': 'INT DEFAULT 0', 'type': int},
        'sg_id': {'sql': 'INT', 'type': int},
        'sg_name': {'sql': 'TEXT', 'type': str},
        'sg_type': {'sql': 'TEXT', 'type': str},
        'sg_task_id': {'sql': 'INT', 'type': int},
        'sg_task_name': {'sql': 'TEXT', 'type': str},
        'cut_in': {'sql': 'INT', 'type': int},
        'cut_out': {'sql': 'INT', 'type': int},
        'cut_duration': {'sql': 'INT', 'type': int},
        'edit_in': {'sql': 'INT', 'type': int},
        'edit_out': {'sql': 'INT', 'type': int},
        'edit_duration': {'sql': 'INT', 'type': int},
        'asset_framerate': {'sql': 'REAL', 'type': float},
        'asset_width': {'sql': 'INT', 'type': int},
        'asset_height': {'sql': 'INT', 'type': int},
        'url1': {'sql': 'TEXT', 'type': str},
        'url2': {'sql': 'TEXT', 'type': str},
        'progress': {'sql': 'TEXT', 'type': dict}
    },
    BookmarkTable: {
        'id': {'sql': 'TEXT PRIMARY KEY COLLATE NOCASE', 'type': str},
        'width': {'sql': 'INT', 'type': int},
        'height': {'sql': 'INT', 'type': int},
        'framerate': {'sql': 'REAL', 'type': float},
        'prefix': {'sql': 'TEXT', 'type': str},
        'startframe': {'sql': 'INT', 'type': int},
        'duration': {'sql': 'INT', 'type': int},
        'sg_domain': {'sql': 'TEXT', 'type': str},
        'sg_scriptname': {'sql': 'TEXT', 'type': str},
        'sg_api_key': {'sql': 'TEXT', 'type': str},
        'sg_id': {'sql': 'INT', 'type': int},
        'sg_name': {'sql': 'TEXT', 'type': str},
        'sg_type': {'sql': 'TEXT', 'type': str},
        'sg_episode_id': {'sql': 'INT', 'type': int},
        'sg_episode_name': {'sql': 'TEXT', 'type': str},
        'url1': {'sql': 'TEXT', 'type': str},
        'url2': {'sql': 'TEXT', 'type': str},
        'config_file_format': {'sql': 'TEXT', 'type': dict},
        'config_scene_names': {'sql': 'TEXT', 'type': dict},
        'config_publish': {'sql': 'TEXT', 'type': dict},
        'config_tasks': {'sql': 'TEXT', 'type': dict},
        'config_asset_folders': {'sql': 'TEXT', 'type': dict},
        'config_burnin': {'sql': 'TEXT', 'type': dict},
        'applications': {'sql': 'TEXT', 'type': dict},
        'bookmark_display_token': {'sql': 'TEXT', 'type': str},
        'asset_display_token': {'sql': 'TEXT', 'type': str},
        'asset_link_presets': {'sql': 'TEXT', 'type': dict},
    },
    TemplateDataTable: {
        'id': {'sql': 'TEXT PRIMARY KEY COLLATE NOCASE', 'type': str},
        'data': {'sql': 'BLOB', 'type': bytes},
    },
}


def get(server, job, root, force=False):
    """
    Retrieve an SQLite database controller for a specific bookmark.

    Controllers are cached per thread in :mod:`common.db_connections`. If `force` is True,
    a new controller is created even if one is cached.

    Args:
        server (str): Server path segment.
        job (str): Job path segment.
        root (str): Root path segment.
        force (bool): If True, forces re-connection to the database.

    Returns:
        :class:`BookmarkDB`: An instance of the database controller.

    Raises:
        RuntimeError: If the database is locked and cannot be accessed.
        OSError: If the database file is missing or inaccessible.
    """
    key = common.get_thread_key(server, job, root)

    if key in common.db_connections:
        if force:
            common.db_connections[key].deleteLater()
            common.db_connections[key] = BookmarkDB(server, job, root)
        return common.db_connections[key]

    db = BookmarkDB(server, job, root)
    common.db_connections[key] = db
    return common.db_connections[key]


def remove_db(server, job, root):
    """
    Remove and close a cached database connection for a specified bookmark.

    Args:
        server (str): Server path segment.
        job (str): Job path segment.
        root (str): Root path segment.
    """
    key = '/'.join((server, job, root))

    for k in list(common.db_connections):
        if key.lower() not in k.lower():
            continue

        try:
            common.db_connections[k].close()
            common.db_connections[k].deleteLater()
            del common.db_connections[k]
        except Exception:
            log.error(__name__, 'Error removing the database.')


def remove_all_connections():
    """
    Close and delete all cached database controllers.
    """
    for k in list(common.db_connections):
        common.db_connections[k].close()
        common.db_connections[k].deleteLater()
        del common.db_connections[k]
    common.db_connections = {}


@functools.lru_cache(maxsize=4194304)
def b64encode(v):
    """
    Encode a string using Base64.

    Args:
        v (str): The string to encode.

    Returns:
        str: The Base64-encoded string.
    """
    return base64.b64encode(v.encode('utf-8')).decode('utf-8')


@functools.lru_cache(maxsize=4194304)
def b64decode(v):
    """
    Decode a Base64-encoded string.

    Args:
        v (str): The Base64-encoded string.

    Returns:
        str: The decoded string.
    """
    return base64.b64decode(v).decode('utf-8')


def sleep(attempt=1):
    """
    Sleep for a short exponential-backoff interval.

    This is used during database retry operations when the database is locked.

    Args:
        attempt (int): The current attempt number.
    """
    delay = min(0.1 * (2 ** attempt), 1.0)
    QtCore.QThread.msleep(int(delay * 1000))


def set_flag(server, job, root, k, mode, flag):
    """
    Set or unset a specific bit flag for an item in the database.

    Args:
        server (str): Server path segment.
        job (str): Job path segment.
        root (str): Root path segment.
        k (str): The source identifier for the item.
        mode (bool): True to set the flag, False to unset it.
        flag (int): The integer flag value to manipulate.
    """
    db = get(server, job, root)
    f = db.value(k, 'flags', AssetTable)
    f = 0 if f is None else f
    f = f | flag if mode else f & ~flag
    db.set_value(k, 'flags', f, AssetTable)


def _verify_args(source, key, table, value=None):
    """
    Validate arguments for database operations.

    Checks that the source, key, and value types and existence match the expected database schema.

    Args:
        source (str): The source identifier.
        key (str|tuple): The column name or tuple of column names.
        table (str): The table name.
        value (optional): The value to be stored.

    Raises:
        TypeError: If source is not a string or value has the wrong type.
        ValueError: If key is not a valid column name in the table.
    """
    if not isinstance(source, str):
        raise TypeError(f'Source "{source}" is not of type str.')

    if isinstance(key, str):
        if key not in TABLES[table]:
            t = ', '.join(TABLES[table])
            raise ValueError(f'Key "{key}" is invalid. Expected one of {t}.')
    elif isinstance(key, tuple):
        t = ', '.join(TABLES[table])
        for k in key:
            if k not in TABLES[table]:
                raise ValueError(f'Key "{k}" is invalid. Expected one of {t}.')

    if value is None:
        return

    if isinstance(key, str):
        if not isinstance(value, TABLES[table][key]['type']):
            raise TypeError(f'Value "{value}" is not of type {TABLES[table][key]["type"]}.')
    elif isinstance(key, tuple):
        for k in key:
            if not isinstance(value, TABLES[table][k]['type']):
                raise TypeError(f'Value "{value}" is not of type {TABLES[table][k]["type"]}.')


@functools.lru_cache(maxsize=4194304)
def load_json(value):
    """
    Load a JSON object from a Base64-encoded string.

    Args:
        value (str): A Base64-encoded string representing a JSON object.

    Returns:
        dict: The decoded JSON object as a dictionary.

    Raises:
        Exception: If decoding fails, returns an empty dictionary.
    """
    try:
        return json.loads(
            b64decode(value.encode('utf-8')),
            parse_int=int,
            parse_float=float,
            object_hook=common.int_key
        )
    except UnicodeDecodeError as e:
        log.error(__name__, e)
        return {}


def convert_return_values(table, key, value):
    """
    Convert database return values to their proper Python types based on the table schema.

    Args:
        table (str): The name of the database table.
        key (str): The column name.
        value (object): The value retrieved from the database.

    Returns:
        object: The value converted to the appropriate Python type.
    """
    if key == 'id':
        return value

    if value is None or key not in TABLES[table]:
        return None

    _type = TABLES[table][key]['type']

    if _type is dict:
        try:
            value = load_json(value)
        except Exception as e:
            log.debug(__name__, e)
            value = None
    elif _type is str:
        try:
            value = b64decode(value.encode('utf-8'))
        except Exception:
            value = None
    elif _type is float:
        try:
            value = float(value)
        except Exception as e:
            log.debug(__name__, e)
            value = None
    elif _type is int:
        try:
            value = int(value)
        except Exception as e:
            log.debug(__name__, e)
            value = None
    elif _type is bytes:
        pass
    return value


class BookmarkDB(QtCore.QObject):
    """
    A database controller for a single bookmark, backed by an SQLite database.

    This class manages reading and writing bookmark data, handles connection retries,
    and provides convenience methods for reading and writing typed values.

    Attributes:
        server (str): Server path segment.
        job (str): Job path segment.
        root (str): Root path segment.
        retries (int): Number of connection retry attempts.
    """
    retries = 6

    def __init__(self, server, job, root, parent=None):
        """
        Initialize the database controller.

        Args:
            server (str): Server path segment.
            job (str): Job path segment.
            root (str): Root path segment.
            parent (QObject): Optional parent for Qt object hierarchy.
        """
        super().__init__(parent=parent)

        self._is_valid = False
        self._is_memory = False
        self._connection = None
        self._version = None

        self.server = server
        self.job = job
        self.root = root

        self._bookmark = f'{server}/{job}/{root}'
        self._bookmark_root = f'{self._bookmark}/{common.bookmark_item_data_dir}'
        self._database_path = f'{self._bookmark_root}/{common.bookmark_item_database}'

        if not self._create_bookmark_dir():
            self.connect_to_db(memory=True)
        else:
            self.connect_to_db(memory=False)

        self.init_tables()
        self._connect_signals()

    def _connect_signals(self):
        self.destroyed.connect(self.close)

    def init_tables(self):
        """
        Initialize the database tables defined in :data:`TABLES`, creating missing tables and columns.
        """

        def _init():
            for table in TABLES:
                self._create_table(table)
                self._patch_table(table)
            self._init_version()
            self._connection.commit()

        try:
            _init()
            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(__name__, e)
            self.connect_to_db(memory=True)
            _init()

    def connect_to_db(self, memory=False):
        """
        Connect to the SQLite database.

        Args:
            memory (bool): If True, use an in-memory database as a fallback.

        If the database is locked or unavailable, this method retries briefly before
        switching to an in-memory database. If in-memory mode is used, the database
        is considered invalid.
        """
        if not memory:
            try:
                self._connection = sqlite3.connect(
                    self._database_path,
                    isolation_level=None,
                    check_same_thread=False,
                    cached_statements=1000,
                    timeout=2
                )
                self._is_valid = True
            except sqlite3.Error as e:
                self._is_valid = False
                log.error(__name__, e)

        if memory or not self._is_valid:
            log.warning(__name__, 'Switching to in-memory database mode due to persistent failure.')
            self._connection = sqlite3.connect(
                ':memory:',
                isolation_level=None,
                check_same_thread=False,
            )
            self._is_valid = False
            self._is_memory = True

    def _init_version(self):
        """
        Retrieve the SQLite version and store it internally for later reference.
        """
        sql = 'SELECT sqlite_version();'
        res = self._connection.execute(sql)
        v = res.fetchone()[0]
        self._version = [int(i) for i in v.split('.')] if v else [0, 0, 0]

    def _create_bookmark_dir(self):
        """
        Create the bookmark data directory if it does not exist.

        Returns:
            bool: True if the directory exists or was created successfully, False otherwise.
        """
        _root_dir = QtCore.QDir(self._bookmark)
        if not _root_dir.exists():
            log.error(__name__, f'Could not create {_root_dir.path()}')
            return False

        _cache_dir = QtCore.QDir(self._bookmark_root)
        if not _cache_dir.exists() and not _cache_dir.mkpath('.'):
            log.error(__name__, f'Could not create {_cache_dir.path()}')
            return False

        _thumb_dir = QtCore.QDir(f'{self._bookmark_root}/thumbnails')
        if not _thumb_dir.exists() and not _thumb_dir.mkpath('.'):
            log.error(__name__, f'Could not create {_thumb_dir.path()}')
            return False

        return True

    def _create_table(self, table):
        """
        Create a database table if it doesn't exist.

        Args:
            table (str): The table name.

        Raises:
            ValueError: If the table name isn't defined in :data:`TABLES`.
            sqlite3.OperationalError: If the table can't be created due to a locked database.
        """
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql_check = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
        attempt = 0
        while attempt <= self.retries:
            try:
                res = self._connection.execute(sql_check, (table,))
                if res.fetchone():
                    return
                break
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    attempt += 1
                    log.debug(__name__, f'Database is locked during table check, retrying {attempt}/{self.retries}...')
                    sleep(attempt=attempt)
                    continue
                else:
                    log.error(__name__, f'OperationalError during table check:\n{e}')
                    raise
            except sqlite3.Error as e:
                log.error(__name__, f'Error during table check:\n{e}')
                raise
        else:
            log.error(__name__, 'Failed to check table existence after multiple retries due to database lock.')
            raise sqlite3.OperationalError('Failed to check table existence due to database lock.')

        args = []
        for k, v in TABLES[table].items():
            args.append(f'{k} {v["sql"]}')

        sql = f'CREATE TABLE IF NOT EXISTS {table} ({",".join(args)})'
        self._connection.execute(sql)

        sql = f'CREATE UNIQUE INDEX IF NOT EXISTS {table}_id_idx ON {table} (id)'
        self._connection.execute(sql)

    def _patch_table(self, table):
        """
        Add missing columns to a database table.

        Args:
            table (str): The table name.

        Raises:
            ValueError: If the table name is not defined in :data:`TABLES`.
            sqlite3.OperationalError: If columns cannot be added due to a locked database.
        """
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'PRAGMA table_info(\'{table}\');'
        attempt = 0
        while attempt <= self.retries:
            try:
                res = self._connection.execute(sql)
                break
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    attempt += 1
                    log.debug(__name__, f'Database is locked during table patching (PRAGMA table_info), '
                                        f'retrying {attempt}/{self.retries}...')
                    sleep(attempt=attempt)
                    continue
                else:
                    log.error(__name__, f'OperationalError during table patching (PRAGMA table_info):\n{e}')
                    raise
            except sqlite3.Error as e:
                log.error(__name__, f'Error during table patching (PRAGMA table_info):\n{e}')
                raise
        else:
            log.error(__name__, 'Failed to get table info after multiple retries due to database lock.')
            raise sqlite3.OperationalError('Failed to get table info due to database lock.')

        columns = [c[1] for c in res]
        missing = list(set(TABLES[table]) - set(columns))

        for column in missing:
            sql_type = f'{column} {TABLES[table][column]["sql"]}'
            sql_alter = f'ALTER TABLE {table} ADD COLUMN {sql_type};'
            attempt = 0
            while attempt <= self.retries:
                try:
                    self._connection.execute(sql_alter)
                    log.debug(__name__, f'Added missing column "{column}"')
                    break
                except sqlite3.OperationalError as e:
                    if 'database is locked' in str(e):
                        attempt += 1
                        log.debug(__name__, f'Database is locked during adding column "{column}", '
                                            f'retrying {attempt}/{self.retries}...')
                        sleep(attempt=attempt)
                        continue
                    else:
                        log.error(__name__, f'OperationalError adding column "{column}":\n{e}')
                        raise
                except sqlite3.Error as e:
                    log.error(__name__, f'Error adding column "{column}":\n{e}')
                    raise
            else:
                log.error(__name__, f'Failed to add column "{column}" after multiple retries due to database lock.')
                raise sqlite3.OperationalError(f'Failed to add column "{column}" due to database lock.')

    def connection(self):
        """
        Return the active database connection instance.

        This can be used as a context manager for transaction handling.

        Returns:
            sqlite3.Connection: The active database connection.
        """
        return self._connection

    def is_valid(self):
        """
        Check if the database connection is valid.

        If the database is running in in-memory mode, it is considered invalid.

        Returns:
            bool: True if the database is valid and file-backed, False otherwise.
        """
        if self._is_memory:
            return False
        return self._is_valid

    def close(self):
        """
        Close the database connection, committing any pending changes.
        """
        try:
            self._connection.commit()
            self._connection.close()
        except sqlite3.Error as e:
            log.error(__name__, e)
            self._is_valid = False
        finally:
            self._connection = None

    def source(self, *args):
        """
        Get a source path related to this bookmark.

        Args:
            *args: Additional path segments to append.

        Returns:
            str: The constructed source path.
        """
        if args:
            return f'{self._bookmark}/{"/".join(args)}'
        return self._bookmark

    def get_column(self, column, table):
        """
        Retrieve all values from a specific column in a table.

        Args:
            column (str): The column name.
            table (str): The table name.

        Yields:
            object: Values from the specified column in the table.

        Raises:
            ValueError: If the table name is not defined in :data:`TABLES`.
        """
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'SELECT {column} FROM {table}'
        try:
            res = self._connection.execute(sql)
            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(__name__, e)
            return

        for row in res:
            yield convert_return_values(table, column, row[0])

    def get_row(self, source, table):
        """
        Retrieve a row of data from a table by source.

        Args:
            source (str): The source path identifier.
            table (str): The table name.

        Returns:
            dict: A dictionary of column-value pairs. If no row is found, returns a dict with all None values.

        Raises:
            ValueError: If the table name is not defined in :data:`TABLES`.
        """
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        def _get_empty_row():
            _values = {}
            for k in columns:
                if k == 'id':
                    continue
                _values[k] = None
            return _values

        sql = f'SELECT * FROM {table} WHERE id=?'
        try:
            res = self._connection.execute(sql, (common.get_hash(source),))
            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(__name__, e)
            res = None

        if not res:
            return {}

        columns = [f[0] for f in res.description]
        row = res.fetchone()
        if not row:
            return _get_empty_row()

        values = {}
        for idx, key in enumerate(columns):
            if key == 'id':
                continue
            values[key] = convert_return_values(table, key, row[idx])
        return values

    def delete_row(self, source, table):
        """
        Delete a row from a table by source.

        Args:
            source (str): The source path identifier.
            table (str): The table name.

        Raises:
            ValueError: If the table name is not defined in :data:`TABLES`.
        """
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'DELETE FROM {table} WHERE id=?'
        try:
            self._connection.execute(sql, (common.get_hash(source),))
            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(__name__, e)

    def get_rows(self, table):
        """
        Retrieve all rows from a given table.

        Args:
            table (str): The table name.

        Yields:
            dict: A dictionary of column-value pairs for each row.

        Raises:
            ValueError: If the table name is not defined in :data:`TABLES`.
        """
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'SELECT * FROM {table}'
        try:
            res = self._connection.execute(sql)
            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(__name__, e)
            return

        columns = [f[0] for f in res.description]

        for row in res:
            data = {}
            for idx, column in enumerate(columns):
                if column == 'id':
                    continue
                data[column] = convert_return_values(table, column, row[idx])
            yield data

    @common.debug
    def value(self, source, key, table):
        """
        Retrieve a single value from the database by source and column.

        Args:
            source (str): Path identifier for the row.
            key (str): Column name to retrieve.
            table (str): Table name.

        Returns:
            object: The value, or None if not found.

        Raises:
            ValueError: If the table or key is invalid.
        """
        if not self.is_valid():
            return None

        _verify_args(source, key, table, value=None)

        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'SELECT {key} FROM {table} WHERE id=?'

        attempt = 0
        value = None
        while attempt <= self.retries:
            try:
                res = self._connection.execute(sql, (common.get_hash(source),))
                row = res.fetchone()
                value = row[0] if row else None
                self._is_valid = True
                break
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    attempt += 1
                    log.debug(__name__, f'Database is locked, retrying {attempt}/{self.retries}...')
                    sleep(attempt=attempt)
                    continue
                else:
                    self._is_valid = False
                    log.error(__name__, e)
                    break
            except sqlite3.Error as e:
                self._is_valid = False
                log.error(__name__, e)
                break
        else:
            log.error(__name__, 'Failed to retrieve value after multiple retries due to database lock.')

        return convert_return_values(table, key, value)

    @common.debug
    def set_value(self, source, key, value, table):
        """
        Set a value in the database for a given source and key.

        Args:
            source (str): The source path identifier.
            key (str): The database column name.
            value (object): The value to store.
            table (str): The table name.

        Raises:
            ValueError: If the table or key is invalid.
            TypeError: If the value type does not match the schema.
            RuntimeError: If a BLOB column is incorrectly configured.
        """
        if not self.is_valid():
            return

        _verify_args(source, key, table, value=value)

        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        if isinstance(value, dict):
            try:
                value = json.dumps(value, ensure_ascii=False)
                value = b64encode(value)
            except Exception as e:
                log.error(__name__, e)
                value = None
        elif isinstance(value, str):
            value = b64encode(value)
        elif isinstance(value, (float, int)):
            try:
                value = str(value)
            except Exception as e:
                log.error(__name__, e)
                value = None
        elif isinstance(value, bytes):
            if TABLES[table][key]['type'] == bytes and TABLES[table][key]['sql'] != 'BLOB':
                raise RuntimeError(f'Error in the database schema. Binary {key} should be associated with BLOB.')

        _hash = common.get_hash(source)

        if self._version < [3, 24, 0]:
            values = []
            params = []
            for k in TABLES[table]:
                if k == 'id':
                    continue
                if k == key:
                    values.append('null' if value is None else '?')
                    if value is not None:
                        params.append(value)
                    continue

                values.append(f'(SELECT {k} FROM {table} WHERE id = ?)')
                params.append(_hash)

            keys = ', '.join(TABLES[table])
            values.insert(0, '?')
            params.insert(0, _hash)
            sql = f'INSERT OR REPLACE INTO {table} ({keys}) VALUES ({", ".join(values)});'
        else:
            sql = (
                f'INSERT INTO {table} (id, {key}) VALUES (?, ?) '
                f'ON CONFLICT(id) DO UPDATE SET {key}=excluded.{key};'
            )
            params = [_hash, value]

        if sql.count('?') != len(params):
            raise ValueError(f'Parameter count mismatch. Expected {sql.count("?")}, got {len(params)}.')

        attempt = 0
        while attempt <= self.retries:
            try:
                self._connection.execute(sql, params)
                self._is_valid = True
                _value = self.value(source, key, table=table)
                common.signals.databaseValueChanged.emit(table, source, key, _value)
                break
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    attempt += 1
                    log.debug(__name__, f'Database is locked, retrying {attempt}/{self.retries}...')
                    sleep(attempt=attempt)
                    continue
                else:
                    log.error(__name__, f'OperationalError setting value:\n{e}')
                    self._is_valid = False
                    break
            except sqlite3.Error as e:
                log.error(__name__, f'Error setting value:\n{e}')
                self._is_valid = False
                break
        else:
            log.error(__name__, 'Failed to set value after multiple retries due to database lock.')
