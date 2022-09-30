# -*- coding: utf-8 -*-
"""Defines :class:`BookmarkDB`, the sqlite3 database interface used to store item properties,
such as custom descriptions, flags, ``width``, ``height``, :mod:`bookmarks.tokens.tokens`
values, etc.

Each bookmark item has its own database file and are stored in ``common.bookmark_cache_dir``, in
the root of the bookmark item. E.g.:

.. code-block:: python

    path = f'//server/job/root/{common.bookmark_cache_dir}/{common.bookmark_database}'


The database table layout is defined in :attr:`.TABLES`, which defines the sqlite and python types
for each column.


Don't create DatabaseDB instances directly, instead use :func:`.get_db` to get cached,
thread-specific database controllers. E.g.:

.. code-block:: python

    from bookmarks import database
    db = database.get_db(server, job, root)
    with db.connection():
        v = db.value(*args)

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

#: Database table name
AssetTable = 'AssetData'
#: Database table name
BookmarkTable = 'BookmarkData'
#: Database table name
InfoTable = 'InfoData'

#: Database column name
IdColumn = 'id'
#: Database column name
DescriptionColumn = 'description'
#: Database column name
NotesColumn = 'notes'

database_connect_retries = 100

#: SQLite database structure definition
TABLES = {
    AssetTable: {
        IdColumn: {
            'sql': 'TEXT PRIMARY KEY COLLATE NOCASE',
            'type': str
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
        'thumbnail_stamp': {
            'sql': 'REAL',
            'type': float
        },
        'user': {
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
        'cut_duration': {
            'sql': 'INT',
            'type': int
        },
        'cut_in': {
            'sql': 'INT',
            'type': int,
        },
        'cut_out': {
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
    },
    InfoTable: {
        IdColumn: {
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
        IdColumn: {
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
        'identifier': {
            'sql': 'TEXT',
            'type': str
        },
        'slacktoken': {
            'sql': 'TEXT',
            'type': str
        },
        'teamstoken': {
            'sql': 'TEXT',
            'type': str,
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
        }
    }
}

#: Database clipboard
CLIPBOARD = {
    BookmarkTable: {},
    AssetTable: {},
}


def get_db(server, job, root, force=False):
    """Creates a database controller associated with a bookmark item.

    SQLite cannot share the same connection instance between threads, hence we
    create and cache controllers per thread. The cached entries are stored
    in `common.db_connections`.

    Args:
        server (str): The name of the `server`.
        job (str): The name of the `job`.
        root (str): The name of the `root`.
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
            common.db_connections[key].connect_with_retries()
        return common.db_connections[key]

    db = BookmarkDB(server, job, root)
    common.db_connections[key] = db
    return common.db_connections[key]


def remove_db(server, job, root):
    """Removes and closes a cached a bookmark database connection.

    Args:
        server (str):   A server.
        job (str):      A job.
        root (str):     A root.

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


@common.debug
@common.error
def copy_properties(server, job, root, asset=None, table=BookmarkTable):
    """Copies the database properties from the specified item to ``CLIPBOARD``.

    Args:
        server (str): Source server name.
        job (str): Source job name.
        root (str): Source root name.
        asset (str, optional): Source asset name.
        table (str, optional): Source table name.

    """
    data = {}

    if asset:
        source = '/'.join((server, job, root, asset))
    else:
        source = '/'.join((server, job, root))

    db = get_db(server, job, root)
    for k in TABLES[table]:
        if k == 'id':
            continue
        data[k] = db.value(source, k, table)

    if data:
        global CLIPBOARD
        CLIPBOARD[table] = data

    return data


@common.debug
@common.error
def paste_properties(server, job, root, asset=None, table=BookmarkTable):
    """Loads the copied item properties from CLIPBOARD and saves it in the target item's database.

    Args:
        server (str): The target server name.
        job (str): The target job name.
        root (str): The target root name.
        asset (str, optional): The target asset name.
        table (str, optional): Target database table.

    """
    if not CLIPBOARD[table]:
        return

    if asset:
        source = '/'.join((server, job, root, asset))
    else:
        source = '/'.join((server, job, root))

    db = get_db(server, job, root)
    with db.connection():
        for k in CLIPBOARD[table]:
            db.setValue(source, k, CLIPBOARD[table][k], table=table)


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
    db = get_db(server, job, root)
    f = db.value(k, 'flags', AssetTable)
    f = 0 if f is None else f
    f = f | flag if mode else f & ~flag
    with db.connection():
        db.setValue(k, 'flags', f, AssetTable)


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
    return json.loads(
        b64decode(value.encode('utf-8')),
        parse_int=int,
        parse_float=float,
    )


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
            value = None
    elif _type is int:
        try:
            value = int(value)
        except Exception as e:
            value = None
    return value


class BookmarkDB(QtCore.QObject):
    """Database connector used to interface with the bookmark item's SQLite database.

    """

    def __init__(self, server, job, root, parent=None):
        super(BookmarkDB, self).__init__(parent=parent)
        for arg in (server, job, root):
            common.check_type(arg, str)

        self._is_valid = False
        self._connection = None

        self._server = server
        self._job = job
        self._root = root

        self._bookmark = '/'.join((server, job, root))
        self._bookmark_root = f'{self._bookmark}/{common.bookmark_cache_dir}'
        self._database_path = f'{self._bookmark_root}/{common.bookmark_database}'

        if self._create_bookmark_dir():
            self.connect_with_retries()
        else:
            self._connect_to_memory_db()

        self._init_tables()

        self.destroyed.connect(self.close)

    def _connect_to_memory_db(self):
        """Creates an in-memory database when we're unable to connect to the
        physical database.

        This is so that Bookmarks keeps running uninterrupted even when the database is unreachable.
        Data saved the in-memory database won't be saved to disk.

        """
        self._connection = sqlite3.connect(
            ':memory:',
            isolation_level=None,
            check_same_thread=False
        )
        self._is_valid = False
        return self._connection

    def connect_with_retries(self):
        """Connects to the database file.

        The database can be locked for a brief period of time whilst it is being
        used by another other controller instance in another thread. This might
        raise an exception, but it is safe to wait on a little and re-try before deeming
        the operation unsuccessful.

        When a database is unreachable, we'll create an in-memory database instead, and
        mark the instance ``invalid`` (:meth:`BookmarkDB.is_valid` will return `False`).

        """
        n = 0
        while True:
            try:
                self._connection = sqlite3.connect(
                    self._database_path,
                    isolation_level=None,
                    check_same_thread=False
                )
                self._is_valid = True
                return self._connection
            except sqlite3.Error:
                if n == database_connect_retries:
                    self._connect_to_memory_db()
                    return self._connection
                sleep()
                log.error('Error.')
                n += 1
            except (RuntimeError, ValueError, TypeError, OSError):
                log.error('Error.')
                raise

    def _create_bookmark_dir(self):
        """Creates the `bookmark_cache_dir` if it does not yet exist.

        Returns:
            bool: `True` if the folder already exists, or successfully created, or `False` when
                can't create the folder.

        """
        file_info = QtCore.QFileInfo(self.root())
        if file_info.exists():
            return True
        _dir = file_info.dir()
        if _dir.exists() and _dir.mkdir(common.bookmark_cache_dir):
            return True
        return False

    def _create_table(self, table):
        """Creates a table based on the passed table definition.

        """
        args = []

        for k, v in TABLES[table].items():
            args.append(f'{k} {v["sql"]}')

        sql = f'CREATE TABLE IF NOT EXISTS {table} ({",".join(args)})'
        self.connection().execute(sql)

    def _patch_table(self, table):
        """For backwards compatibility, we will ALTER the database if any of the
        required columns are missing.

        """
        sql = f'PRAGMA table_info(\'{table}\');'

        table_info = self.connection().execute(sql).fetchall()

        columns = [c[1] for c in table_info]
        missing = list(set(TABLES[table]) - set(columns))

        for column in missing:
            cmd = f'ALTER TABLE {table} ADD COLUMN {column};'
            try:
                self.connection().execute(cmd)
                log.success(f'Added missing column {missing}')
            except Exception as e:
                log.error(
                    f'Failed to add missing column {column}\n{e}')
                raise

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
            server=b64encode(self._server),
            job=b64encode(self._job),
            root=b64encode(self._root),
            user=b64encode(common.get_username()),
            host=b64encode(platform.node()),
            created=time.time(),
        )
        self.connection().execute(sql)

    def _init_tables(self):
        """Initialises the database with the default tables.

        If the database is new or empty, we will create the tables.
        If the database has tables already, we'll check the columns against
        the table definitions and add any missing ones.

        """
        n = 0
        while True:
            n += 1

            try:
                for table in TABLES:
                    self._create_table(table)
                    self._patch_table(table)
                self._add_info()
                self.connection().commit()
                return
            except:
                if n >= database_connect_retries:
                    self.connection().rollback()
                    raise
                sleep()

    def root(self):
        return self._bookmark_root

    def is_valid(self):
        """Returns the database's status.

        Returns:
            bool: True if the database is valid, False otherwise.

        """
        if not self._connection:
            return False
        return self._is_valid

    def connection(self):
        return self._connection

    def close(self):
        try:
            self._connection.commit()
            self._connection.close()
        except sqlite3.Error:
            log.error('Database error.')
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
            return self._bookmark + '/' + '/'.join(args)
        return self._bookmark

    def get_row(self, source, table):
        common.check_type(source, str)
        common.check_type(table, str)

        _hash = common.get_hash(source)
        sql = f'SELECT * FROM {table} WHERE id=\'{_hash}\''

        try:
            cursor = self.connection().execute(sql)
            columns = [f[0] for f in cursor.description]
            row = cursor.fetchone()
        except Exception as e:
            log.error(f'Failed to get value from database.\n{e}')
            raise

        values = {}

        if not row:
            for key in columns:
                # skip 'id'
                if key == 'id':
                    continue
                values[key] = None
            return values

        for idx, key in enumerate(columns):
            # skip 'id'
            if key == 'id':
                continue
            values[key] = convert_return_values(table, key, row[idx])
        return values

    def value(self, source, key, table):
        """Returns a value from the `database`.

        Args:
            source (str):       Path to a file or folder.
            key (str):  A column, or a list of columns.
            table (str, optional): Optional table parameter, defaults to `AssetTable`.

        Returns:
            data:                   The requested value or `None`.

        """
        if not self.is_valid():
            return None

        _verify_args(source, key, table, value=None)

        @functools.lru_cache(maxsize=4194304)
        def _get_sql(_source, _key, _table):
            _hash = common.get_hash(_source)
            return f'SELECT {_key} FROM {_table} WHERE id=\'{_hash}\''

        sql = _get_sql(source, key, table)

        try:
            row = self.connection().execute(sql).fetchone()
        except Exception as e:
            log.error(f'Failed to get value from database.\n{e}')
            raise

        if not row:
            return None

        value = row[0]
        return convert_return_values(table, key, value)

    def setValue(self, source, key, value, table=AssetTable):
        """Set a value in the database.

        Example:

        .. code-block:: python

            db = database.get_db(server, job, root)
            with db.connection():
                source = f'//{server}/{job}/{root}/sh0010/scenes/my_scene.ma'
                db.setValue(source, 'description', 'hello world')

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
        values = []

        # Earlier versions of the SQLITE library lack `UPSERT` or `WITH`
        # A workaround is found here:
        # https://stackoverflow.com/questions/418898/sqlite-upsert-not-insert-or-replace
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

        try:
            self.connection().execute(sql)

            # Finally, we'll notify others of the changed value
            _value = self.value(source, key, table=table)
            common.signals.databaseValueUpdated.emit(
                table, source, key, _value)

        except Exception as e:
            log.error(f'Failed to set value.\n{e}')
