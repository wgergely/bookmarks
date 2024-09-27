"""This module provides the :class:`BookmarkDB` class, which offers an interface to an SQLite database for storing
properties related to bookmark items. These properties include custom descriptions, flags, dimensions (width and
height), and values from :mod:`bookmarks.tokens.tokens`, among others.

The database file for each bookmark item is located at the root of the item's cache folder, as specified by
:attr:`common.bookmark_item_cache_dir`. The database path is constructed as follows:

.. code-block:: python
    :linenos:

    f'{server}/{job}/{root}/{common.bookmark_item_cache_dir}/{common.bookmark_item_database}'

The database table structure is defined by :attr:`TABLES`, which maps SQLite column types to the corresponding Python
types used in the app.

To get an instance of the database interface, use the :func:`.get` function, which retrieves cached, thread-specific
database controllers.

**Example usage:**

.. code-block:: python
    :linenos:

    from bookmarks import database

    # Get the database interface for a specific bookmark item
    db = database.get(server, job, root)
    value = db.value(db.source(), 'width', database.BookmarkTable)

    # Get the database interface of the active bookmark item
    db = database.get(*common.active('root', args=True))
    value = db.value(db.source(), 'height', database.BookmarkTable)

Every call to :meth:`BookmarkDB.value` and :meth:`BookmarkDB.set_value` triggers an automatic commit. To group
multiple commits together, use the built-in context manager:

.. code-block:: python
    :linenos:

    from bookmarks import database

    db = database.get(server, job, root)
    with db.connection():
        db.set_value(*args)

The database contains two tables for storing item data: :attr:`common.BookmarkTable` and :attr:`common.AssetTable`.
The `AssetTable` is intended for general descriptions and notes applicable to all items, while the `BookmarkTable`
contains properties specific to the bookmark item.

**Note:** Bookmark items should ideally store their descriptions in the `AssetTable` since it is a general property.
However, they currently use the 'description' column in the `BookmarkTable`, which is redundant. This is a known
issue that may be addressed in future versions of the software.

The module also provides utility functions for creating and managing the database, handling connections, encoding and
decoding data, and managing item flags. For more details, refer to the docstrings of the specific functions.

"""

import base64
import functools
import json
import platform
import sqlite3
import time

from PySide2 import QtCore, QtWidgets

from . import common
from . import log

#: Table used for storing asset and file properties
AssetTable = 'AssetData'
#: Table used for storing bookmark item properties
BookmarkTable = 'BookmarkData'
#: Table used for storing asset template data
TemplateDataTable = 'TemplateData'
#: Special table used for storing general information about the database
InfoTable = 'InfoData'

#: sqlite3 database structure definition
TABLES = {
    AssetTable: {
        'id': {
            'sql': 'TEXT PRIMARY KEY COLLATE NOCASE',
            'type': str,
        },
        'description': {
            'sql': 'TEXT',
            'type': str
        },
        'notes': {
            'sql': 'TEXT',
            'type': dict
        },
        'flags': {
            'sql': 'INT DEFAULT 0',
            'type': int
        },
        'sg_id': {
            'sql': 'INT',
            'type': int
        },
        'sg_name': {
            'sql': 'TEXT',
            'type': str
        },
        'sg_type': {
            'sql': 'TEXT',
            'type': str
        },
        'sg_task_id': {
            'sql': 'INT',
            'type': int
        },
        'sg_task_name': {
            'sql': 'TEXT',
            'type': str
        },
        'cut_in': {
            'sql': 'INT',
            'type': int,
        },
        'cut_out': {
            'sql': 'INT',
            'type': int
        },
        'cut_duration': {
            'sql': 'INT',
            'type': int
        },
        'edit_in': {
            'sql': 'INT',
            'type': int,
        },
        'edit_out': {
            'sql': 'INT',
            'type': int
        },
        'edit_duration': {
            'sql': 'INT',
            'type': int
        },
        'asset_framerate': {
            'sql': 'REAL',
            'type': float
        },
        'asset_width': {
            'sql': 'INT',
            'type': int
        },
        'asset_height': {
            'sql': 'INT',
            'type': int
        },
        'url1': {
            'sql': 'TEXT',
            'type': str
        },
        'url2': {
            'sql': 'TEXT',
            'type': str
        },
        'progress': {
            'sql': 'TEXT',
            'type': dict
        }

    },
    InfoTable: {
        'id': {
            'sql': 'TEXT PRIMARY KEY COLLATE NOCASE',
            'type': str
        },
        'server': {
            'sql': 'TEXT NOT NULL',
            'type': str
        },
        'job': {
            'sql': 'TEXT NOT NULL',
            'type': str,
        },
        'root': {
            'sql': 'TEXT NOT NULL',
            'type': str
        },
        'user': {
            'sql': 'TEXT NOT NULL',
            'type': str,
        },
        'host': {
            'sql': 'TEXT NOT NULL',
            'type': str
        },
        'created': {
            'sql': 'REAL NOT NULL',
            'type': float
        }
    },
    BookmarkTable: {
        'id': {
            'sql': 'TEXT PRIMARY KEY COLLATE NOCASE',
            'type': str
        },
        'description': {
            'sql': 'TEXT',
            'type': str
        },
        'width': {
            'sql': 'INT',
            'type': int
        },
        'height': {
            'sql': 'INT',
            'type': int
        },
        'framerate': {
            'sql': 'REAL',
            'type': float
        },
        'prefix': {
            'sql': 'TEXT',
            'type': str
        },
        'startframe': {
            'sql': 'INT',
            'type': int
        },
        'duration': {
            'sql': 'INT',
            'type': int
        },
        'sg_domain': {
            'sql': 'TEXT',
            'type': str
        },
        'sg_scriptname': {
            'sql': 'TEXT',
            'type': str
        },
        'sg_api_key': {
            'sql': 'TEXT',
            'type': str
        },
        'sg_id': {
            'sql': 'INT',
            'type': int
        },
        'sg_name': {
            'sql': 'TEXT',
            'type': str
        },
        'sg_type': {
            'sql': 'TEXT',
            'type': str
        },
        'sg_episode_id': {
            'sql': 'INT',
            'type': int
        },
        'sg_episode_name': {
            'sql': 'TEXT',
            'type': str
        },
        'url1': {
            'sql': 'TEXT',
            'type': str,
        },
        'url2': {
            'sql': 'TEXT',
            'type': str
        },
        'tokens': {
            'sql': 'TEXT',
            'type': dict
        },
        'applications': {
            'sql': 'TEXT',
            'type': dict,
        },
        'bookmark_display_token': {
            'sql': 'TEXT',
            'type': str
        },
        'asset_display_token': {
            'sql': 'TEXT',
            'type': str
        },
        'asset_link_presets': {
            'sql': 'TEXT',
            'type': dict
        },
    },
    TemplateDataTable: {
        'id': {
            'sql': 'TEXT PRIMARY KEY COLLATE NOCASE',
            'type': str
        },
        'data': {
            'sql': 'BLOB',
            'type': bytes
        },
    }
}


def get(server, job, root, force=False):
    """Retrieve an SQLite database controller associated with a bookmark item.

    Since SQLite connections can't be shared between threads, controllers are cached per thread. The cached entries
    are stored in `common.db_connections`.

    Args:
        server (str): The `server` path segment.
        job (str): The `job` path segment.
        root (str): The `root` path segment.
        force (bool): If `True`, forces a retry in connecting to the database.

    Returns:
        BookmarkDB: An instance of the database controller.

    Raises:
        RuntimeError: If the database is locked.
        OSError: If the database is missing.
    """
    for k in (server, job, root):
        common.check_type(k, str)

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
    """Remove and close a cached bookmark database connection.

    Args:
        server (str): The `server` path segment.
        job (str): The `job` path segment.
        root (str): The `root` path segment.
    """
    key = '/'.join((server, job, root))

    for k in list(common.db_connections):
        if key.lower() not in k.lower():
            continue

        try:
            common.db_connections[k].close()
            common.db_connections[k].deleteLater()
            del common.db_connections[k]
        except:
            log.error('Error removing the database.')


def remove_all_connections():
    """Close and delete all database controller instances."""
    for k in list(common.db_connections):
        common.db_connections[k].close()
        common.db_connections[k].deleteLater()
        del common.db_connections[k]
    common.db_connections = {}


@functools.lru_cache(maxsize=4194304)
def b64encode(v):
    """Encode a string using Base64."""
    common.check_type(v, str)
    return base64.b64encode(v.encode('utf-8')).decode('utf-8')


@functools.lru_cache(maxsize=4194304)
def b64decode(v):
    """Decode a Base64-encoded string."""
    common.check_type(v, bytes)
    return base64.b64decode(v).decode('utf-8')


def sleep():
    """Utility function to pause execution for a short duration."""
    app = QtWidgets.QApplication.instance()
    if app and app.thread() == QtCore.QThread.currentThread():
        QtCore.QThread.msleep(25)
        return
    QtCore.QThread.msleep(50)


def set_flag(server, job, root, k, mode, flag):
    """Utility method to set a flag for an item in the database."""
    db = get(server, job, root)
    f = db.value(k, 'flags', AssetTable)
    f = 0 if f is None else f
    f = f | flag if mode else f & ~flag
    db.set_value(k, 'flags', f, AssetTable)


def _verify_args(source, key, table, value=None):
    """Verify the input arguments for database operations."""
    common.check_type(source, (str, tuple))

    if isinstance(key, str) and key not in TABLES[table]:
        t = ', '.join(TABLES[table])
        raise ValueError(f'Key "{key}" is invalid. Expected one of {t}.')
    elif isinstance(key, tuple):
        t = ', '.join(TABLES[table])
        for k in key:
            if k not in TABLES[table]:
                raise ValueError(f'Key "{k}" is invalid. Expected one of {t}.')

    # Check type
    if value is None:
        return

    if isinstance(key, str):
        common.check_type(value, TABLES[table][key]['type'])
    elif isinstance(key, tuple):
        for k in key:
            common.check_type(value, TABLES[table][k]['type'])


@functools.lru_cache(maxsize=4194304)
def load_json(value):
    """Load a JSON object from a Base64-encoded string.

    Args:
        value (str): A Base64-encoded string.

    Returns:
        dict: A dictionary object.

    """
    try:
        return json.loads(
            b64decode(value.encode('utf-8')),
            parse_int=int,
            parse_float=float,
            object_hook=common.int_key
        )
    except UnicodeDecodeError as e:
        log.error(e)
        return {}


def convert_return_values(table, key, value):
    """Utility function to enforce data types on returned database values.

    Args:
        table (str): The database table name.
        key (str): The column name.
        value (object): The value to convert.

    Returns:
        object: The converted value.

    """
    if key == 'id':
        return value

    if value is None:
        return None
    if key not in TABLES[table]:
        return None
    _type = TABLES[table][key]['type']

    if _type is dict:
        try:
            value = load_json(value)
        except Exception as e:
            log.debug(e)
            value = None
    elif _type is str:
        try:
            value = b64decode(value.encode('utf-8'))
        except Exception as e:
            value = None
    elif _type is float:
        try:
            value = float(value)
        except Exception as e:
            log.debug(e)
            value = None
    elif _type is int:
        try:
            value = int(value)
        except Exception as e:
            log.debug(e)
            value = None
    elif _type is bytes:
        pass
    return value


class BookmarkDB(QtCore.QObject):
    """Database connector for interfacing with a bookmark item's SQLite database."""

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent=parent)

        for arg in (server, job, root):
            common.check_type(arg, str)

        self._is_valid = False
        self._is_memory = False
        self._connection = None
        self._version = None

        self.server = server
        self.job = job
        self.root = root

        self._bookmark = f'{server}/{job}/{root}'
        self._bookmark_root = f'{self._bookmark}/{common.bookmark_item_cache_dir}'
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
        def _init():
            for table in TABLES:
                self._create_table(table)
                self._patch_table(table)
            self._add_info()
            self._init_version()
            self._connection.commit()

        try:
            _init()
            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(e)
            self.connect_to_db(memory=True)
            _init()

    def connect_to_db(self, memory=False):
        """Connect to the database file.

        The database might be temporarily locked if it's being used by another controller instance in a different
        thread. In such cases, it's safe to wait briefly and retry before considering the operation unsuccessful.

        If the database is unreachable, an in-memory database is created instead, and the instance is marked as
        invalid; :meth:`BookmarkDB.is_valid` returning `False`.
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
                log.error(e)

        if memory or not self._is_valid:
            self._connection = sqlite3.connect(
                ':memory:',
                isolation_level=None,
                check_same_thread=False,
            )
            self._is_valid = False
            self._is_memory = True

    def _init_version(self):
        sql = 'SELECT sqlite_version();'
        res = self._connection.execute(sql)
        v = res.fetchone()[0]
        self._version = [int(i) for i in v.split('.')] if v else [0, 0, 0]

    def _create_bookmark_dir(self):
        """Create the `bookmark_item_cache_dir` if it doesn't already exist.

        Returns:
            bool: `True` if the folder already exists or was successfully created; `False` if the folder cannot
        be created.
        """
        _root_dir = QtCore.QDir(self._bookmark)
        if not _root_dir.exists():
            log.error(f'Could not create {_root_dir.path()}')
            return False

        _cache_dir = QtCore.QDir(self._bookmark_root)
        if not _cache_dir.exists() and not _cache_dir.mkpath('.'):
            log.error(f'Could not create {_cache_dir.path()}')
            return False

        _thumb_dir = QtCore.QDir(f'{self._bookmark_root}/thumbnails')
        if not _thumb_dir.exists() and not _thumb_dir.mkpath('.'):
            log.error(f'Could not create {_thumb_dir.path()}')
            return False

        return True

    def _create_table(self, table):
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        args = []

        for k, v in TABLES[table].items():
            args.append(f'{k} {v["sql"]}')

        sql = f'CREATE TABLE IF NOT EXISTS {table} ({",".join(args)})'
        self._connection.execute(sql)

        sql = f'CREATE UNIQUE INDEX IF NOT EXISTS {table}_id_idx ON {table} (id)'
        self._connection.execute(sql)

    def _patch_table(self, table):
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'PRAGMA table_info(\'{table}\');'

        try:
            res = self._connection.execute(sql)
        except sqlite3.Error as e:
            log.error(e)
            raise

        columns = [c[1] for c in res]  # Direct iteration over the cursor without fetchall
        missing = list(set(TABLES[table]) - set(columns))

        for column in missing:
            sql_type = f'{column} {TABLES[table][column]["sql"]}'
            sql = f'ALTER TABLE {table} ADD COLUMN {sql_type};'
            try:
                self._connection.execute(sql)
                log.success(f'Added missing column "{column}"')
            except sqlite3.Error as e:
                log.error(f'Failed to add column "{column}": {e}')
                raise

    def _add_info(self):
        columns = sorted(TABLES[InfoTable])
        args = ', '.join(columns)
        placeholders = ', '.join(['?'] * len(columns))
        sql = f'INSERT OR IGNORE INTO {InfoTable} ({args}) VALUES ({placeholders});'

        values = [
            common.get_hash(self._bookmark),
            b64encode(self.server),
            b64encode(self.job),
            b64encode(self.root),
            b64encode(common.get_username()),
            b64encode(platform.node()),
            time.time()
        ]

        self._connection.execute(sql, values)

    def connection(self):
        """Return the database connection instance."""
        return self._connection

    def is_valid(self):
        """Check if the database is valid.

        Returns:
            bool: `True` if the database is valid; `False` otherwise.
        """
        if self._is_memory:
            return False
        return self._is_valid

    def close(self):
        """Close the database connection."""
        try:
            self._connection.commit()
            self._connection.close()
        except sqlite3.Error as e:
            log.error(e)
            self._is_valid = False
        finally:
            self._connection = None

    def source(self, *args):
        """Get the source path of the database.

        Args:
            tuple: Path segments to be appended to the base path.

        Returns:
            str: The source path of the bookmark database.

        """
        if args:
            return f'{self._bookmark}/{"/".join(args)}'
        return self._bookmark

    def get_column(self, column, table):
        """Retrieve all values from a column in the database.

        Args:
            column (str): The column name.
            table (str): The name of the database table.

        Yields:
            list: A list of values from the column.

        """
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'SELECT {column} FROM {table}'

        try:
            res = self._connection.execute(sql)

            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(e)
            return

        for row in res:
            yield convert_return_values(table, column, row[0])

    def get_row(self, source, table):
        """Retrieve a row from the database.

        Args:
            source (str): The source file path.
            table (str): The name of the database table.

        Returns:
            dict: A dictionary containing column-value pairs.
        """
        common.check_type(source, str)
        common.check_type(table, str)

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
            log.error(e)
            return _get_empty_row()

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
        """Delete a row from the database.

        Args:
            source (str): The source file path.
            table (str): The name of the database table.

        """
        common.check_type(source, str)
        common.check_type(table, str)

        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'DELETE FROM {table} WHERE id=?'

        try:
            self._connection.execute(sql, (common.get_hash(source),))
            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(e)

    def get_rows(self, table):
        """Retrieve all rows from the database.

        Args:
            table (str): The name of the database table.

        Yields:
            dict: A dictionary containing column-value pairs for each row.

        """
        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'SELECT * FROM {table}'

        try:
            res = self._connection.execute(sql)
            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(e)
            return

        columns = [f[0] for f in res.description]

        for row in res:
            data = {}

            for idx, column in enumerate(columns):
                if column == 'id':
                    continue
                data[column] = convert_return_values(table, column, row[idx])

            yield data

    def value(self, source, key, table):
        """Retrieve a value from the database.

        Args:
            source (str): Path to a file or folder.
            key (str): The column name (or list of column names).
            table (str): The name of the database table.

        Returns:
            object: The value stored in the database, or `None` if not found.
        """
        if not self.is_valid():
            return None

        _verify_args(source, key, table, value=None)

        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        sql = f'SELECT {key} FROM {table} WHERE id=?'

        try:
            res = self._connection.execute(sql, (common.get_hash(source),))
            row = res.fetchone()

            value = row[0] if row else None
            self._is_valid = True
        except sqlite3.Error as e:
            value = None
            self._is_valid = False

            log.error(e)

        return convert_return_values(table, key, value)

    def set_value(self, source, key, value, table):
        """Set a value in the database.

        **Example:**

        .. code-block:: python
            :linenos:

            db = database.get(server, job, root)
            source = f'{server}/{job}/{root}/sh0010/scenes/my_scene.ma'
            db.set_value(source, 'description', 'hello world', AssetTable)

        Args:
            source (str): The source file path.
            key (str): The name of the database column.
            value (object): The value to store in the database.
            table (str): The name of the database table.

        """
        if not self.is_valid():
            return

        _verify_args(source, key, table, value=value)

        if table not in TABLES:
            raise ValueError(f'Table "{table}" not found in TABLES.')

        if isinstance(value, dict):
            try:
                value = json.dumps(
                    value,
                    ensure_ascii=False,
                )
                value = b64encode(value)
            except Exception as e:
                log.error(e)
                value = None
        elif isinstance(value, str):
            value = b64encode(value)
        elif isinstance(value, (float, int)):
            try:
                value = str(value)
            except Exception as e:
                log.error(e)
                value = None
        elif isinstance(value, bytes):
            # Binary type is natively supported via BLOBs.
            if TABLES[table][key]['type'] == bytes and not TABLES[table][key]['sql'] == 'BLOB':
                raise RuntimeError(f'Error in the database schema. Binary {key} should be associated with  BLOB.')

        _hash = common.get_hash(source)

        values = []
        params = []

        # Versions earlier than 3.24.0 lack `UPSERT` so based on
        # the following article, use a `INSERT OR REPLACE` instead
        # https://stackoverflow.com/questions/418898/sqlite-upsert-not-insert-or-replace
        if self._version < [3, 24, 0]:
            # Prepare the values for the SQL query
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
        else:  # use upsert for versions => 3.24.0
            sql = (
                f'INSERT INTO {table} (id, {key}) VALUES (?, ?) '
                f'ON CONFLICT(id) DO UPDATE SET {key}=excluded.{key};'
            )
            params.append(_hash)
            params.append(value)

        # Count '?' in the SQL statement
        if sql.count('?') != len(params):
            raise ValueError(f'Parameter count mismatch. Expected {sql.count("?")}, got {len(params)}.')

        try:
            self._connection.execute(sql, params)
            self._is_valid = True

            # Emit change signal with the value set in the database
            _value = self.value(source, key, table=table)
            common.signals.databaseValueUpdated.emit(
                table, source, key, _value
            )
        except sqlite3.Error as e:
            log.error(f'Error setting value:\n{e}')
            self._is_valid = False
