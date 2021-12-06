# -*- coding: utf-8 -*-
"""BookmarkDB stores all item information Bookmarks needs
to work.

This includes file descriptions, properties like `width`, `height`, asset
configs, etc. The database file itself is stored in the given bookmark's root,
at `//server/job/root/.bookmark/bookmark.db`

The sqlite3 database table definitions are stored in `database.json`.

Usage
-----

    Use the thread-safe `database.get_db()` to create thread-specific
    connections to a database

The bookmark databases have currently 3 tables. The `data` table is used to
store information about folders and files, e.g. assets would store their
visibility flags, cut information and Shotgun data here.
The `info` and `properties` tables are linked to the bookmark.

"""
import time
import platform
import sqlite3
import base64
import json

from PySide2 import QtCore, QtWidgets

from . import log
from . import common


AssetTable = 'AssetData'
BookmarkTable = 'BookmarkData'
InfoTable = 'InfoData'

IdColumn = 'id'
DescriptionColumn = 'description'
NotesColumn = 'notes'

DATABASE = 'bookmark.db'

database_connect_retries = 100


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
        'asset_config': {
            'sql': 'TEXT',
            'type': dict
        },
        'applications': {
            'sql': 'TEXT',
            'type': dict,
        }
    }
}

__DB_CONNECTIONS = {}

CLIPBOARD = {
    BookmarkTable: {},
    AssetTable: {},
}


def close():
    """Closes and deletes all connections to the bookmark database files.

    """
    for k in list(__DB_CONNECTIONS):
        __DB_CONNECTIONS[k].close()
        __DB_CONNECTIONS[k].deleteLater()
        del __DB_CONNECTIONS[k]


@common.debug
@common.error
def copy_properties(server, job, root, asset=None, table=BookmarkTable):
    """Copies the given bookmark's properties from the database to `CLIPBOARD`.

    Args:
        server (str):   The server's name.
        job (str):   The job's name.
        root (str):   The root's name.

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
    """Pastes the saved bookmark properties from `CLIPBOARD` to the given
    bookmark's properties.

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


def b64encode(v):
    common.check_type(v, str)
    return base64.b64encode(v.encode('utf-8')).decode('utf-8')


def b64decode(v):
    common.check_type(v, bytes)
    return base64.b64decode(v).decode('utf-8')


def sleep():
    """Waits a little before trying to open the database.

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


def get_db(server, job, root, force=False):
    """Creates a database controller associated with a bookmark item.

    SQLite cannot share the same connection between different threads, hence we
    will create and cache controllers per thread. The cached entries are stored
    in `__DB_CONNECTIONS`.

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

    key = _get_thread_key(server, job, root)

    global __DB_CONNECTIONS
    if key in __DB_CONNECTIONS:
        if force:
            __DB_CONNECTIONS[key]._connect_with_retries()
        return __DB_CONNECTIONS[key]

    db = BookmarkDB(server, job, root)
    __DB_CONNECTIONS[key] = db
    return __DB_CONNECTIONS[key]


def remove_db(server, job, root):
    """Removes and closes a cached a bookmark database connection.

    Args:
        server (str):   A server.
        job (str):      A job.
        root (str):     A root.

    """
    global __DB_CONNECTIONS
    key = '/'.join((server, job, root))

    for k in list(__DB_CONNECTIONS):
        if key.lower() not in k.lower():
            continue

        try:
            __DB_CONNECTIONS[k].close()
            __DB_CONNECTIONS[k].deleteLater()
            del __DB_CONNECTIONS[k]
        except:
            log.error('Error removing the database.')


def _get_thread_key(*args):
    t = repr(QtCore.QThread.currentThread())
    return '/'.join(args) + t


def _verify_args(source, key, table, value=None):
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


def convert_return_values(table, key, value):
    if value is None:
        return None
    _type = TABLES[table][key]['type']
    if _type is dict:
        try:
            value = json.loads(
                b64decode(value.encode('utf-8')),
                parse_int=int,
                parse_float=float,
            )
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
    """Database connector used to interface with the SQLite database.

    Use `BookmarkDB.value()` and `BookmarkDB.setValue()` to get and set data.

    """

    def __init__(self, server, job, root, parent=None):
        super(BookmarkDB, self).__init__(parent=parent)
        for arg in (server, job, root):
            common.check_type(arg, str)

        self._is_valid = False
        self._connection = None

        self._server = server.encode('utf-8')
        self._server_u = server
        self._job = job.encode('utf-8')
        self._job_u = job
        self._root = root.encode('utf-8')
        self._root_u = root

        self._bookmark = '/'.join((server, job, root))
        self._bookmark_root = '{}/{}'.format(
            self._bookmark, common.bookmark_cache_dir)
        self._database_path = '{}/{}'.format(self._bookmark_root, DATABASE)

        if self._create_bookmark_dir():
            self._connect_with_retries()
        else:
            self._connect_to_memory_db()

        self._init_tables()

        self.destroyed.connect(self.close)

    def _connect_to_memory_db(self):
        """Creates in-memory database used, when we're unable to connect to the
        bookmark database.

        """
        self._connection = sqlite3.connect(
            ':memory:',
            isolation_level=None,
            check_same_thread=False
        )
        self._is_valid = False
        return self._connection

    def _connect_with_retries(self):
        """Connects to the database file.

        The database can be locked for a brief period of time whilst it is being
        used by an another controller instance in another thread. This normally
        will raise an exception, but it is safe to wait on this a little and try
        a few times before deeming it permanently unopenable.

        When a database is unopenable, we'll create an in-memory database, and
        mark the instance invalid (`self.is_valid()` returns `False`).

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
                n += 1
            except (RuntimeError, ValueError, TypeError, OSError):
                log.error('Error.')
                raise

    def _create_bookmark_dir(self):
        """Creates the `bookmark_cache_dir` if does not yet exist.

        Returns:
            bool:   `True` if the folder already exists, or successfully created.
                    `False` if can't create the folder.

        """
        file_info = QtCore.QFileInfo(self.root())
        if file_info.exists():
            return True
        _dir = file_info.dir()
        if _dir.exists() and _dir.mkdir(common.bookmark_cache_dir):
            return True
        return False

    def _create_table(self, table):
        """Creates a table based on the TABLES definition.

        """
        args = []

        for k, v in TABLES[table].items():
            args.append('{} {}'.format(k, v['sql']))

        sql = 'CREATE TABLE IF NOT EXISTS {table} ({args})'.format(
            table=table,
            args=','.join(args)
        )
        self.connection().execute(sql)

    def _patch_table(self, table):
        """For backwards compatibility, we will ALTER the database if any of the
        required columns are missing.

        """
        sql = 'PRAGMA table_info(\'{}\');'.format(table)

        table_info = self.connection().execute(sql).fetchall()

        columns = [c[1] for c in table_info]
        missing = list(set(TABLES[table]) - set(columns))

        for column in missing:
            cmd = 'ALTER TABLE {} ADD COLUMN {};'.format(table, column)
            try:
                self.connection().execute(cmd)
                log.success('Added missing column {}'.format(missing))
            except Exception as e:
                log.error(
                    'Failed to add missing column {}\n{}'.format(column, e))
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
            server=b64encode(self._server_u),
            job=b64encode(self._job_u),
            root=b64encode(self._root_u),
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
            log.error('Failed to get value from database.\n{}'.format(e))
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

        _hash = common.get_hash(source)
        sql = f'SELECT {key} FROM {table} WHERE id=\'{_hash}\''

        try:
            row = self.connection().execute(sql).fetchone()
        except Exception as e:
            log.error('Failed to get value from database.\n{}'.format(e))
            raise

        if not row:
            return None

        value = row[0]
        return convert_return_values(table, key, value)

    def setValue(self, source, key, value, table=AssetTable):
        """Sets a value in the database.

        The method does NOT commit the transaction! Use ``transactions`` context
        manager to issue a BEGIN statement. The transactions will be committed
        once the context manager goes out of scope.

        Example:

        .. code-block:: python

            with db.transactions:
                source = '//SERVER/MY_JOB/shots/sh0010/scenes/my_scene.ma'
                db.setValue(source, 'description', 'hello world')

        Args:
            table:
            source (str):       A row id, usually a file or folder path.
            key (str):          A database column name.
            value (*):              The value to set.

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
            log.error('Failed to set value.\n{}'.format(e))
