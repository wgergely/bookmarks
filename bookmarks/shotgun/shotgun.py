"""The module contains the classes and methods needed to provide linkage
with ShotGrid.

In the simplest of cases (e.g. when a bookmark item is active and have already been
linked with ShotGrid) we can initiate a connection using a :class:`SGProperties`
instance:

.. code-block:: python
    :linenos:

    import bookmarks.shotgun.shotgun as shotgun

    sg_properties = shotgun.SGProperties(active=True)
    sg_properties.init() # loads data from the bookmark database

    # Verify properties before connecting
    if not sg_properties.verify(connection=True):
        raise ValueError('Bookmark not configured to use ShotGrid.')

    with sg_properties.connection() as sg:
        schema = sg.schema_field_read('Shot')


The current implementation needs to authenticate using an API Script Name/Key.
These values must be set in the bookmark database before initiating a connection.

https://developer.shotgunsoftware.com/python-api/reference.html

"""
import contextlib
import pprint
import uuid

import shotgun_api3
from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import database
from .. import images
from .. import log
from ..threads import threads

EntityRole = QtCore.Qt.UserRole + 1000
IdRole = QtCore.Qt.UserRole + 1001
TypeRole = QtCore.Qt.UserRole + 1002
NameRole = QtCore.Qt.UserRole + 1003

#: ShotGrid entity url pattern
ENTITY_URL = '{domain}/detail/{entity_type}/{entity_id}'

#: A list of entity and field definitions used to assist entity data queries
entity_fields = {
    'LocalStorage': ['type', 'id', 'code', 'description', 'mac_path', 'windows_path', 'linux_path'],
    'PublishedFileType': ['type', 'id', 'code', 'description', 'short_name'],
    'Project': ['type', 'id', 'name', 'is_template', 'is_demo', 'is_template_project', 'archived'],
    'Asset': ['type', 'id', 'code', 'project', 'description', 'notes'],
    'Sequence': ['type', 'id', 'code', 'project', 'description', 'notes'],
    'Shot': ['type', 'id', 'code', 'project', 'description', 'notes', 'cut_in', 'cut_out', 'cut_duration',
             'sg_cut_in', 'sg_cut_out', 'sg_cut_duration'],
    'Task': ['type', 'id', 'content', 'sg_description', 'project', 'entity', 'notes', 'color', 'task_assignees',
             'start_date', 'due_date'],
    'Status': ['id', 'name', 'type', 'code', 'bg_color'],
    'HumanUser': ['type', 'id', 'name', 'firstname', 'lastname', 'projects'],
    'Version': ['type', 'id', 'code', 'description', 'sg_task', 'sg_path_to_frames', 'sg_path_to_movie',
                'sg_path_to_geometry', 'sg_status_list', 'project', 'entity', 'tasks', 'user'],
    'PublishedFile': ['type', 'id', 'code', 'name', 'description', 'entity', 'version', 'version_number',
                      'project'],
}

#: ShotGrid connection instance cache
SG_CONNECTIONS = {}

sg_connecting_message = None


# A function that replaces all instances of either '/' or '\' with the given separator in the given path


def sanitize_path(path, separator):
    """Function replaces all instances of either '/' or '\' with the given separator in the given path.

    Args:
        path (str): The path to sanitize.
        separator (str): The separator to replace '/' or '\' with.

    Returns:
        str: The sanitized path.

    """
    common.check_type(path, str)
    common.check_type(separator, str)

    path = path.strip()
    return path.replace('/', separator).replace('\\', separator)


def get_sg(domain, script, key, auth_as_user=False):
    """Method for retrieving a thread specific `ScriptConnection` instance,
    backed by a cache.

    Args:
        domain (str): The base url or domain where the shotgun server is located.
        script (str): A valid ShotGrid API Script's name or username.
        key (str): A valid ShotGrid Script's API Key or password.
        auth_as_user (bool): Whether to authenticate as a user. Defaults to False.

    """
    common.check_type(auth_as_user, bool)
    for arg in (domain, script, key):
        common.check_type(arg, str)

    k = _get_thread_key(domain, script, key, str(auth_as_user))

    if k in SG_CONNECTIONS and SG_CONNECTIONS[k]:
        return SG_CONNECTIONS[k]

    _script = script if not auth_as_user else None
    _key = key if not auth_as_user else None
    login = script if auth_as_user else None
    password = key if auth_as_user else None

    if not all((domain, login, password)):
        if not all((domain, script, key)):
            raise ValueError(
                f'You must provide a valid domain, {"script" if not auth_as_user else "login"}'
                f' name and {"api key" if not auth_as_user else "password"} to connect to ShotGrid:'
                f'\ndomain: {domain}\nscript: {_script}\nkey: {_key}\nlogin: {login}\npassword: {password}'
            )

    try:
        sg = SG(
            domain, script_name=_script, api_key=_key, login=login, password=password,
            connect=False, convert_datetimes_to_utc=True, http_proxy=None, ensure_ascii=False,
            ca_certs=None, sudo_as_login=None, session_token=None, auth_token=None
        )

        SG_CONNECTIONS[k] = sg
        return SG_CONNECTIONS[k]
    except:
        SG_CONNECTIONS[k] = None
        if key in SG_CONNECTIONS:
            del SG_CONNECTIONS[k]
        raise


def _get_thread_key(*args):
    """Returns a unique key for the current thread. Used to cache shotgun connections.

    """
    t = repr(QtCore.QThread.currentThread())
    return ''.join(args) + t


class SG(shotgun_api3.Shotgun):
    """ShotGrid connection class override.

    """

    def find(self, entity_type, filters, fields=None, **kwargs):
        """Override of the `find` method to ensure that all requested fields are returned.

        Args:
            entity_type (str): The entity type to search for.
            filters (list): A list of filters to apply to the query.
            fields (list): A list of fields to return in the query.
            **kwargs: Additional keyword arguments to pass to the `shotgun_api3.Shotgun.find` method.

        Returns:
            list: A list of dictionaries containing the requested fields.

        """
        fields = fields or []
        if entity_type in entity_fields:
            fields.extend(entity_fields[entity_type])

        entities = super().find(entity_type, filters, fields=fields, **kwargs)
        if not entities:
            return entities

        # We want to make sure that all the fields we requested are present in the returned entities
        for entity in entities:
            missing_fields = list(set(fields) - set(entity.keys()))
            if missing_fields:
                _f = '", "'.join(missing_fields)
                log.error(f'Missing fields: "{_f}" in return data. Check if you have permission to access these '
                          f'fields.')
        return entities

    def find_one(self, entity_type, filters, fields=None, **kwargs):
        """Override of the `find_one` method to ensure that all requested fields are returned.

        Args:
            entity_type (str): The entity type to search for.
            filters (list): A list of filters to apply to the query.
            fields (list): A list of fields to return in the query.
            **kwargs: Additional keyword arguments to pass to the `shotgun_api3.Shotgun.find_one` method.

        Returns:
            dict: A dictionary containing the requested fields.

        """
        kwargs['limit'] = 1
        entities = self.find(entity_type, filters, fields=fields, **kwargs)
        if entities:
            return entities[0]
        return None


class SGProperties(QtCore.QObject):
    """Returns all ShotGrid properties saved in the bookmark item database.

    These properties define the linkage between ShotGrid entities and local assets
    and are required to make ShotGrid connections.

    The instance is uninitialized by default, use self.init() to load the values
    from the bookmark database.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.
        asset (str): `asset` path segment.
        active (bool): Use the active paths when `True`. `False` by default.
        auth_as_user (bool): Authenticate as a user when `True`. `False` by default.

    """

    def __init__(self, *args, **kwargs):
        self.active = kwargs['active'] if 'active' in kwargs else False

        self.auth_as_user = kwargs['auth_as_user'] if 'auth_as_user' in kwargs else False

        self._server = args[0] if len(args) > 0 else None
        self._job = args[1] if len(args) > 1 else None
        self._root = args[2] if len(args) > 2 else None
        self._asset = args[3] if len(args) > 3 else None

        self.domain = None
        self.key = None
        self.script = None

        # Save optional user and password for user authentication
        self.login = kwargs['login'] if 'login' in kwargs else common.settings.value('sg_auth/login', None)
        self.password = kwargs['password'] if 'password' in kwargs else common.settings.value('sg_auth/password', None)

        self.bookmark_type = 'Project'
        self.bookmark_id = None
        self.bookmark_name = None

        self.episode_id = None
        self.episode_name = None

        self.asset_type = None
        self.asset_id = None
        self.asset_name = None

        self.asset_cut_in = None
        self.asset_cut_out = None
        self.asset_cut_duration = None

        self.asset_task_name = None
        self.asset_task_id = None

    @property
    def server(self):
        """`Server` path segment.

        """
        return common.active('server') if self.active else self._server

    @property
    def job(self):
        """`Job` path segment.

        """
        return common.active('job') if self.active else self._job

    @property
    def root(self):
        """`Root` path segment.

        """
        return common.active('root') if self.active else self._root

    @property
    def asset(self):
        """`Asset` path segment.

        """
        return common.active('asset') if self.active else self._asset

    def _load_values_from_database(self, db):
        t = database.BookmarkTable
        s = db.source()

        self.domain = db.value(s, 'shotgun_domain', t)
        self.key = db.value(s, 'shotgun_api_key', t)
        self.script = db.value(s, 'shotgun_scriptname', t)

        self.bookmark_id = db.value(s, 'shotgun_id', t)
        self.bookmark_name = db.value(s, 'shotgun_name', t)

        self.episode_id = db.value(s, 'sg_episode_id', t)
        self.episode_name = db.value(s, 'sg_episode_name', t)

        if not self.asset:
            return

        t = database.AssetTable
        s = db.source(self.asset)

        self.asset_type = db.value(s, 'shotgun_type', t)
        self.asset_id = db.value(s, 'shotgun_id', t)
        self.asset_name = db.value(s, 'shotgun_name', t)
        self.asset_task_id = db.value(s, 'sg_task_id', t)
        self.asset_task_name = db.value(s, 'sg_task_name', t)

    @common.debug
    @common.error
    def init(self, db=None):
        """Load all current shotgun values from the bookmark item database.

        """
        if not all((self.server, self.job, self.root)):
            return
        if db is None:
            db = database.get(self.server, self.job, self.root)
        self._load_values_from_database(db)

    def verify(self, connection=False, bookmark=False, asset=False, task=False):
        """Checks the validity of the current configuration.

        Args:
            connection (bool, optional): Verifies the connection information if True.
            bookmark (bool, optional):
                Checks only the bookmark item's configuration if True.
            asset (bool, optional):
                Checks only the asset item's configuration if True.

        Returns:
            bools: True if the configuration is valid, False otherwise.

        """
        # Verify credentials
        if not all((self.domain, self.login, self.password)):
            if not all((self.domain, self.key, self.script)):
                return False

        # We can connect
        if connection:
            return True

        # Verify project entity
        if not all((self.bookmark_type, self.bookmark_name, self.bookmark_id)):
            return False

        # We have an associated entity
        if bookmark:
            return True

        # Verify asset entity
        if not self.asset and asset:
            return False
        if not self.asset and not asset:
            return True
        if not all((self.asset_type, self.asset_id, self.asset_name)):
            return False

        if not self.asset and task:
            return False
        if not all((self.asset_type, self.asset_id, self.asset_name, self.asset_task_id, self.asset_task_name)):
            return False

        return True

    @contextlib.contextmanager
    def connection(self):
        """Context manager used for connecting to ShotGrid using an API Script.

        The context manager will connect to shotgun on entering and close the
        connection when exiting.

        Yields:
            ScriptConnection: A connected shotgun connection instance

        """
        if not self.verify(connection=True):
            s = 'Bookmark not yet configured to use ShotGrid. You set a valid domain' \
                'name, script/key, or username/password before connecting.'
            if QtWidgets.QApplication.instance():
                common.signals.sgConnectionFailed.emit(s)

        try:
            if self.auth_as_user and all((self.domain, self.login, self.password)):
                sg = get_sg(self.domain, self.login, self.password, auth_as_user=self.auth_as_user)

            elif self.auth_as_user and not all((self.domain, self.login, self.password)):
                raise ValueError(
                    f'Invalid ShotGrid properties:\n'
                    f'domain: {self.domain}\n'
                    f'login: {self.login}\n'
                    f'password: {self.password}'
                )

            elif not self.auth_as_user and all((self.domain, self.script, self.key)):
                sg = get_sg(self.domain, self.script, self.key, auth_as_user=self.auth_as_user)

            elif not self.auth_as_user and not all((self.domain, self.script, self.key)):
                raise ValueError(
                    f'Invalid ShotGrid properties:\n'
                    f'domain: {self.domain}\n'
                    f'script: {self.script}\n'
                    f'key: {self.key}'
                )

            else:
                raise ValueError(
                    f'Invalid ShotGrid properties:\n'
                    f'domain: {self.domain}\n'
                    f'script: {self.script}\n'
                    f'key: {self.key}\n'
                    f'login: {self.login}\n'
                    f'password: {self.password}'
                )

            if QtWidgets.QApplication.instance():
                common.signals.sgConnectionAttemptStarted.emit()
            sg.connect()
            if QtWidgets.QApplication.instance():
                common.signals.sgConnectionSuccessful.emit()
            yield sg
        except Exception as e:
            if QtWidgets.QApplication.instance():
                common.signals.sgConnectionFailed.emit(f'{e}')
            raise
        else:
            sg.close()
            if QtWidgets.QApplication.instance():
                common.signals.sgConnectionClosed.emit()

    def urls(self):
        """Returns a list of available urls based on the sg_properties provided.

        Returns:
            list:   A list of urls.

        """
        if not self.domain:
            return []

        urls = []

        urls.append(self.domain)
        if all((self.bookmark_id, self.bookmark_type)):
            urls.append(ENTITY_URL.format(domain=self.domain, entity_type=self.bookmark_type, entity_id=self.bookmark_id))
        if not self.episode_id is None:
            urls.append(ENTITY_URL.format(domain=self.domain, entity_type='Episode', entity_id=self.episode_id))
        if all((self.asset_id, self.asset_type)):
            urls.append(ENTITY_URL.format(domain=self.domain, entity_type=self.asset_type, entity_id=self.asset_id))
        if not self.asset_task_id is None:
            urls.append(ENTITY_URL.format(domain=self.domain, entity_type='Task', entity_id=self.asset_task_id))

        return urls


class EntityModel(QtCore.QAbstractItemModel):
    """Our custom model used to store ShotGrid entities.

    The model itself does not load any data but instead uses a secondary worker
    thread to do the heavy lifting. The `entityDataRequested` and
    `entityDataReceived` signals are responsible for requesting and retrieving
    ShotGrid data.

    Each instance has a unique uuid used to match data requests with retrieved
    data.

    """
    #: Signal used to request data from ShotGrid. Must be emitted with the following arguments:
    # `uuid` (str)
    # `server` (str)
    # `job`  (str)
    # `root` (str),
    # `asset` (str),
    # `user` (bool),
    # `entity_type` (str),
    # `filters` (list),
    # `fields` (list).
    entityDataRequested = QtCore.Signal(str, str, str, str, str, bool, str, list, list)

    #: Signal used by the worker thread when data is ready, with the data's uuid,
    #: and list of entities.
    entityDataReceived = QtCore.Signal(str, list)

    def __init__(self, items, parent=None):
        super().__init__(parent=parent)

        self.uuid = uuid.uuid1().hex
        self._waiting_for_data = False

        self._original_items = items
        self.internal_data = items

        self.sg_icon = self.get_sg_icon()
        self.spinner_icon = self.get_spinner()

        common.signals.sgEntityDataReady.connect(self.entityDataReceived)

        self.entityDataRequested.connect(self.start_waiting_for_data)
        self.entityDataRequested.connect(threads.queue_shotgun_query)

        self.entityDataReceived.connect(self.set_entity_data)
        self.entityDataReceived.connect(self.end_waiting_for_data)

    def set_entity_data(self, idx, v):
        if idx != self.uuid:
            return

        self.beginResetModel()
        self.internal_data = self.internal_data + v
        self.endResetModel()

    def start_waiting_for_data(self):
        self.beginResetModel()
        self._waiting_for_data = True
        self.endResetModel()

    def end_waiting_for_data(self):
        self._waiting_for_data = False

    def get_sg_icon(self):
        icon = QtGui.QIcon()
        pixmap = images.rsc_pixmap('sg', common.color(common.color_separator), common.size(common.size_row_height))
        icon.addPixmap(pixmap, QtGui.QIcon.Normal)
        pixmap = images.rsc_pixmap('sg', common.color(common.color_selected_text), common.size(common.size_row_height))
        icon.addPixmap(pixmap, QtGui.QIcon.Active)
        icon.addPixmap(pixmap, QtGui.QIcon.Selected)
        pixmap = images.rsc_pixmap(
            'sg', common.color(common.color_disabled_text), common.size(common.size_row_height),
            opacity=0.66
        )
        icon.addPixmap(pixmap, QtGui.QIcon.Disabled)
        return icon

    def get_spinner(self):
        icon = QtGui.QIcon()
        pixmap = images.rsc_pixmap('spinner', common.color(common.color_text), common.size(common.size_row_height))
        icon.addPixmap(pixmap, QtGui.QIcon.Normal)
        icon.addPixmap(pixmap, QtGui.QIcon.Active)
        icon.addPixmap(pixmap, QtGui.QIcon.Selected)
        icon.addPixmap(pixmap, QtGui.QIcon.Disabled)
        return icon

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if self._waiting_for_data:
            return self.createIndex(row, column, None)
        try:
            return self.createIndex(row, column, self.internal_data[row])
        except:
            return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if self._waiting_for_data:
            return 1
        if not self.internal_data:
            return 0
        return len(self.internal_data)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        data = index.internalPointer()

        if role == IdRole:
            if isinstance(data, dict) and 'id' in data:
                return data['id']
        if role == TypeRole:
            if isinstance(data, dict) and 'type' in data:
                return data['type']
        if role == NameRole:
            if isinstance(data, dict):
                return self._name(data)

        if role == QtCore.Qt.DisplayRole:
            return self._name(data)
        if role == EntityRole and isinstance(data, dict):
            return data
        if role == QtCore.Qt.StatusTipRole:
            return self._description(data)
        if role == QtCore.Qt.ToolTipRole:
            return self._description(data)
        if role == QtCore.Qt.WhatsThisRole:
            return self._description(data)
        if role == QtCore.Qt.DecorationRole:
            return self._icon(data)
        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(1, common.size(common.size_row_height))
        return None

    def _description(self, v):
        if isinstance(v, str):
            return v
        if not isinstance(v, dict):
            return None
        return pprint.pformat(v, indent=1, depth=3, width=2)

    def _name(self, v):
        if isinstance(v, str):
            return v
        if not isinstance(v, dict):
            return None

        if 'name' in v:
            name = v['name']
        elif 'code' in v:
            name = v['code']
        elif 'content' in v:
            name = v['content']
        elif 'type' in v:
            name = f'Type {v["type"]}'
        elif 'id' in v:
            name = f'Id {v["id"]}'
        else:
            name = str(v)

        if 'entity' in v and v['entity']:
            if 'name' in v['entity']:
                _name = v['entity']['name']
            elif 'code' in v['entity']:
                _name = v['entity']['code']
            elif 'content' in v['entity']:
                _name = v['entity']['content']
            elif 'type' in v['entity']:
                _name = f'{v["entity"]["type"]}'
            else:
                _name = str(v['entity'])
            name = f'{name}  |  {_name}'

        return name

    def _icon(self, v):
        if self._waiting_for_data:
            return self.spinner_icon
        if isinstance(v, str):
            return None

        # In case the entity contains color information we can set
        # our SG icon to that color
        k = 'bg_color'
        if k in v and v[k]:
            args = [int(f) for f in v['bg_color'].split(',')]
            color = QtGui.QColor(*args)
            pixmap = images.rsc_pixmap('sg', color, common.size(common.size_margin))
            return QtGui.QIcon(pixmap)

        # Otherwise return the standard shotgun icon
        return self.sg_icon

    def flags(self, index, parent=QtCore.QModelIndex()):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def parent(self, index):
        return QtCore.QModelIndex()


class EntityFilterModel(QtCore.QSortFilterProxyModel):
    """A filter model to wrap our EntityModel.

    Use it to filter entities by type. `self.set_entity_type`
    sets the filter entity type.

    """

    def __init__(self, model, parent=None):
        super().__init__(parent=None)
        self.setSourceModel(model)
        self._entity_type = 'Shot'

    def set_entity_type(self, v):
        self._entity_type = v
        self.invalidate()

    def filterAcceptsColumn(self, source_column, parent=QtCore.QModelIndex()):
        return True

    def filterAcceptsRow(self, source_row, parent=QtCore.QModelIndex()):
        if not self._entity_type:
            return True
        index = self.sourceModel().index(source_row, 0)
        entity = index.data(EntityRole)

        if not entity:
            return True
        if 'type' in entity and entity['type'] != self._entity_type:
            return False
        return True


class EntityComboBox(QtWidgets.QComboBox):
    """A ShotGrid specific combobox, intended to be used with the `EntityFilterModel`.
    Use `self.set_model` to set a new `EntityModel`.

    """

    def __init__(self, items, fixed_height=common.size(common.size_row_height), parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        if not self.parent():
            common.set_stylesheet(self)
        if fixed_height:
            self.setFixedHeight(fixed_height)

        self.set_model(EntityModel(items))

    def set_model(self, model):
        """Sets a new EntityModel for the combobox.

        """
        common.check_type(model, EntityModel)
        self.setModel(EntityFilterModel(model))
        self.model().sourceModel().entityDataRequested.connect(self.select_first)
        self.model().sourceModel().entityDataReceived.connect(self.model().invalidate)

    def select_first(self):
        self.blockSignals(True)
        self.setCurrentIndex(0)
        self.blockSignals(False)

    def append_entity(self, entity):
        """Appends a new row to the end of the model.

        """
        model = self.model().sourceModel()

        model.beginInsertRows(QtCore.QModelIndex(), model.rowCount(), model.rowCount())
        model.internal_data.append(entity)
        model.endInsertRows()
        self.setCurrentIndex(self.count() - 1)
