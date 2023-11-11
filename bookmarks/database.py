"""This module defines the :class:`BookmarkDB` class, which provides an SQLite database interface for storing
properties related to bookmark items. Properties can include custom descriptions, flags, dimensions (width, height),
and values from :mod:bookmarks.tokens.tokens, among others.

The database file for each bookmark item is stored at the root of the item's cache folder, as defined by
:attr:`common.bookmark_cache_dir`. The location of the database file is represented as follows:

.. code-block:: python
    :linenos:

    f'{server}/{job}/{root}/{common.bookmark_cache_dir}/{common.bookmark_database}'

The database table layout is determined by :attr:`TABLES`, which maps SQLite column types to the Python types used in
the application.

To get an instance of the database interface, use the :func:`.get` function. This function retrieves cached,
thread-specific database controllers.

Example usage:

.. code-block:: python
    :linenos:

    from bookmarks import database

    # Get the database interface for a specific bookmark item
    db = database.get(server, job, root)
    v = db.value(db.source(), 'width', database.BookmarkTable)

    # Get the database interface of the active bookmark item db = database.get(*common.active('root', args=True)) v =
    db.value(db.source(), 'height', database.BookmarkTable)

Every :meth:`BookmarkDB.value` and :meth:`BookmarkDB.set_value` call triggers an automatic commit. To group commits
together, use the built-in context manager:

.. code-block:: python
    :linenos:

    from bookmarks import database

    db = database.get(server, job, root)
    with db.connection():
        db.set_value(*args)

The database contains two tables that hold item data: :attr:`common.BookmarkTable` and :attr:`common.AssetTable`. The
AssetTable is intended to hold general descriptions and notes for all items, while the BookmarkTable contains
properties specifically related to the bookmark item.

Note: Bookmark items should ideally store their descriptions in the AssetTable as it is a general property. However,
currently, they use the 'description' column in the BookmarkTable, which is redundant. This behavior is a known issue
and may be corrected in future versions of the software.

The module also provides utility functions for creating and managing the database, handling connections, encoding and
decoding data, and managing items' flags. For more details, refer to the specific function's docstring."""
import base64
import functools
import json
import platform
import sqlite3
import time

from PySide2 import QtCore, QtWidgets

from . import common
from . import log

#: Database table name
AssetTable = 'AssetData'
#: Database table name
BookmarkTable = 'BookmarkData'
#: Database table name
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
        'shotgun_id': {
            'sql': 'INT',
            'type': int
        },
        'shotgun_name': {
            'sql': 'TEXT',
            'type': str
        },
        'shotgun_type': {
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
        'shotgun_domain': {
            'sql': 'TEXT',
            'type': str
        },
        'shotgun_scriptname': {
            'sql': 'TEXT',
            'type': str
        },
        'shotgun_api_key': {
            'sql': 'TEXT',
            'type': str
        },
        'shotgun_id': {
            'sql': 'INT',
            'type': int
        },
        'shotgun_name': {
            'sql': 'TEXT',
            'type': str
        },
        'shotgun_type': {
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
    }
}


def get(server, job, root, force=False):
    """Returns an SQLite database controller associated with a bookmark item.

    sqlite3 cannot share the same connection instance between threads, hence we
    create and cache controllers per thread. The cached entries are stored
    in `common.db_connections`.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.
        force (bool): Force retry connecting to the database.

    Returns:
        BookmarkDB:     Database controller instance.

    Raises:
        RuntimeError:   When the database is locked.
        OSError:        When the database is missing.

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
    """Removes and closes a cached a bookmark database connection.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.

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
    """Closes and deletes all database controller instances.

    """
    for k in list(common.db_connections):
        common.db_connections[k].close()
        common.db_connections[k].deleteLater()
        del common.db_connections[k]
    common.db_connections = {}


@functools.lru_cache(maxsize=4194304)
def b64encode(v):
    """Base64 encode function.

    """
    common.check_type(v, str)
    return base64.b64encode(v.encode('utf-8')).decode('utf-8')


@functools.lru_cache(maxsize=4194304)
def b64decode(v):
    """Base64 decode function.

    """
    common.check_type(v, bytes)
    return base64.b64decode(v).decode('utf-8')


def sleep():
    """Utility script used to sleep for a certain amount of time.

    """
    app = QtWidgets.QApplication.instance()
    if app and app.thread() == QtCore.QThread.currentThread():
        QtCore.QThread.msleep(25)
        return
    QtCore.QThread.msleep(50)


def set_flag(server, job, root, k, mode, flag):
    """A utility method used by the base view to set an item flag to the database.

    """
    db = get(server, job, root)
    f = db.value(k, 'flags', AssetTable)
    f = 0 if f is None else f
    f = f | flag if mode else f & ~flag
    db.set_value(k, 'flags', f, AssetTable)


def _verify_args(source, key, table, value=None):
    """Verify input arguments.

    """
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
    """Load a base 64 encoded json value.

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
    """Utility function used enforce data types.

    """
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
        except:
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
    return value


class BookmarkDB(QtCore.QObject):
    """Database connector used to interface with the bookmark item's sqlite3 database.

    """

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
        self._bookmark_root = f'{self._bookmark}/{common.bookmark_cache_dir}'
        self._database_path = f'{self._bookmark_root}/{common.bookmark_database}'

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
        """Connects to the database file.

        The database can be locked for a brief period of time whilst it is being
        used by another other controller instance in another thread. This might
        raise an exception, but it is safe to wait on a little and re-try before deeming
        the operation unsuccessful.

        When a database is unreachable, we'll create an in-memory database instead, and
        mark the instance ``invalid`` (:meth:`BookmarkDB.is_valid` will return `False`).

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
        """Creates the `bookmark_cache_dir` if it does not yet exist.

        Returns:
            bool: True if the folder already exists or successfully created, False when
                can't create the folder.

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
        """Creates a table based on the passed table definition.

        """
        args = []

        for k, v in TABLES[table].items():
            args.append(f'{k} {v["sql"]}')

        sql = f'CREATE TABLE IF NOT EXISTS {table} ({",".join(args)})'
        self._connection.execute(sql)

        sql = f'CREATE UNIQUE INDEX IF NOT EXISTS {table}_id_idx ON {table} (id)'
        self._connection.execute(sql)

    def _patch_table(self, table):
        """Patches the table for backwards compatibility using ALTER if we encounter
        missing columns.

        """
        sql = f'PRAGMA table_info(\'{table}\');'
        res = self._connection.execute(sql)
        data = res.fetchall()

        columns = [c[1] for c in data]
        missing = list(set(TABLES[table]) - set(columns))

        for column in missing:
            sql = f'ALTER TABLE {table} ADD COLUMN {column};'
            self._connection.execute(sql)
            log.success(f'Added missing column "{missing}"')

    def _add_info(self):
        """Adds information about who and when created the database.

        """
        sql = 'INSERT OR IGNORE INTO {table} ({args}) VALUES ({kwargs});'.format(
            table=InfoTable,
            args=','.join(sorted(TABLES[InfoTable])),
            kwargs='\'{{{}}}\''.format(
                '}\', \'{'.join(
                    sorted(TABLES[InfoTable])
                )
            )
        ).format(
            id=common.get_hash(self._bookmark),
            server=b64encode(self.server),
            job=b64encode(self.job),
            root=b64encode(self.root),
            user=b64encode(common.get_username()),
            host=b64encode(platform.node()),
            created=time.time(),
        )

        self._connection.execute(sql)

    def connection(self):
        """Returns the connection instance.

        """
        return self._connection

    def is_valid(self):
        """Returns the database's status.

        Returns:
            bool: True if the database is valid, False otherwise.

        """
        if self._is_memory:
            return False
        return self._is_valid

    def close(self):
        """Closes the connection.

        """
        try:
            self._connection.commit()
            self._connection.close()
        except sqlite3.Error as e:
            log.error(e)
            self._is_valid = False
        finally:
            self._connection = None

    def source(self, *args):
        """The source path of the database.

        Args:
            args (tuple): A tuple of path segments to be added to the base path.

        Returns:
            str: The source path of the bookmark database.

        """
        if args:
            return f'{self._bookmark}/{"/".join(args)}'
        return self._bookmark

    def get_row(self, source, table):
        """Gets a row from the database.

        Args:
            source (str): A source file path.
            table (str): A database table name.

        Returns:
            dict: A dictionary of column/value pairs.

        """
        common.check_type(source, str)
        common.check_type(table, str)

        def _get_empty_row():
            _values = {}
            for k in columns:
                if k == 'id':
                    continue
                _values[k] = None
            return _values

        _hash = common.get_hash(source)
        sql = f'SELECT * FROM {table} WHERE id=\'{_hash}\''

        try:
            res = self._connection.execute(sql)
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

    def value(self, source, key, table):
        """Returns a value from the `database`.

        Args:
            source (str): Path to a file or folder.
            key (str): A column, or a list of columns.
            table (str, optional): Optional table parameter, defaults to `AssetTable`.

        Returns:
            object: The value stored in the database, or None.

        """
        if not self.is_valid():
            return None

        _verify_args(source, key, table, value=None)

        @functools.lru_cache(maxsize=4194304)
        def _get_sql(_source, _key, _table):
            """Returns a cached SQL statement for the value query."""
            _hash = common.get_hash(_source)
            return f'SELECT {_key} FROM {_table} WHERE id=\'{_hash}\''

        sql = _get_sql(source, key, table)

        value = None
        try:
            res = self._connection.execute(sql)
            row = res.fetchone()
            value = row[0] if row else None
            self._is_valid = True
        except sqlite3.Error as e:
            self._is_valid = False
            log.error(e)
        return convert_return_values(table, key, value)

    def set_value(self, source, key, value, table=AssetTable):
        """Sets the given value in the database.

        .. code-block:: python
            :linenos:

            db = database.get(server, job, root)
            source = f'//{server}/{job}/{root}/sh0010/scenes/my_scene.ma'
            db.set_value(source, 'description', 'hello world')

        Args:
            source (str): Source file path.
            key (str): A database column name.
            value (object): The value to set in the database.
            table (str): A database table.

        """
        if not self.is_valid():
            return

        _verify_args(source, key, table, value=value)

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

        _hash = common.get_hash(source)

        # Versions earlier than 3.24.0 lack `UPSERT` so based on
        # the following article, we'll use a `INSERT OR REPLACE` instead
        # https://stackoverflow.com/questions/418898/sqlite-upsert-not-insert-or-replace
        if self._version < [3, 24, 0]:
            values = []
            for k in TABLES[table]:
                if k == key:
                    v = '\n null' if value is None else '\n \'' + value + '\''
                    values.append(v)
                    continue

                v = '\n(SELECT ' + k + ' FROM ' + table + \
                    ' WHERE id =\'' + _hash + '\')'
                values.append(v)

            sql = 'INSERT OR REPLACE INTO {table} (id, {allkeys}) VALUES (\'{hash}\', {values});'.format(
                hash=_hash,
                allkeys=', '.join(TABLES[table]),
                values=','.join(values),
                table=table
            )
        else:  # use upsert for versions 3.24.0 and above
            sql = 'INSERT INTO {table} (id, {key}) VALUES (\'{hash}\', \'{value}\')' \
                  ' ON CONFLICT(id) DO UPDATE SET {key}=excluded.{key};'.format(
                hash=_hash,
                key=key,
                value=value,
                table=table
            )

        try:
            self._connection.execute(sql)
            self._is_valid = True

            # Emit change signal with the value set in the database
            _value = self.value(source, key, table=table)
            common.signals.databaseValueUpdated.emit(
                table, source, key, _value
            )
        except sqlite3.Error as e:
            log.error(f'Error setting value:\n{e}')
            self._is_valid = False
