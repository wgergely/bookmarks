"""Defines a customized QSettings object used to store user settings.

The user settings are stored in an ini file stored at :func:`.get_user_settings_path`.
The current ui state, current active paths and application settings are all stored in here.

"""
import collections
import json
import os
import re

from PySide2 import QtCore

from .. import common
from .. import log

#: section/key definitions
SECTIONS = {
    'active': (
        'server',
        'job',
        'root',
        'asset',
        'task',
        'file',
    ),
    'user': (
        'user/servers',
        'user/bookmarks',
        'user/favourites',
    ),
    'settings': (
        'settings/job_scan_depth',
        'settings/ui_scale',
        'settings/show_menu_icons',
        'settings/paint_thumbnail_bg',
        'settings/disable_oiio',
        'settings/always_always_on_top',
        'settings/bin_ffmpeg',
        'settings/bin_rv',
        'settings/bin_rvpush',
        'settings/bin_oiiotool',
    ),
    'filters': (
        'filters/active',
        'filters/archived',
        'filters/favourites',
        'filters/buttons',
        'filters/collapsed',
        'filters/text',
        'filters/text_history',
        'filters/sort_by',
        'filters/sort_order',
        'filters/row_heights',
        'filters/selection_file',
        'filters/selection_sequence',
        'filters/progress',
    ),
    'selection': (
        'selection/current_tab',
    ),
    'state': (
        'state/geometry',
        'state/state',
    ),
    'slack': (
        'slack/user',
    ),
    'sg_auth': (
        'sg_auth/login',
        'sg_auth/password',
    ),
    'sg_link_multiple': (
        'sg_link_multiple/filter',
    ),
    'shotgrid_publish': (
        'shotgrid_publish/task',
        'shotgrid_publish/type',
    ),
    'file_saver': (
        'file_saver/task',
        'file_saver/element',
        'file_saver/extension',
        'file_saver/template',
        'file_saver/user',
    ),
    'bookmarker': (
        'bookmarker/server',
        'bookmarker/job',
        'bookmarker/root',
    ),
    'ffmpeg': (
        'ffmpeg/preset',
        'ffmpeg/size',
        'ffmpeg/add_timecode',
        'ffmpeg/timecode_preset',
        'ffmpeg/pushtorv',
    ),
    'maya': (
        'maya/sync_workspace',
        'maya/workspace_save_warnings',
        'maya/push_capture_to_rv',
        'maya/reveal_capture',
        'maya/publish_capture',
        'maya/set_sg_context'
    ),
    'maya_export': (
        'maya_export/type',
        'maya_export/set',
        'maya_export/timeline',
        'maya_export/version',
        'maya_export/keep_open',
    ),
    'publish': (
        'publish/archive_existing',
        'publish/template',
        'publish/task',
        'publish/copy_path',
        'publish/reveal',
        'publish/teams_notification',
    ),
}

KEYS = set()
for __k in SECTIONS:
    KEYS.update({f for f in SECTIONS[__k]})
del __k

SynchronisedActivePaths = 0
PrivateActivePaths = 1


def init_settings():
    """Initializes the :class:`UserSettings` instance.

    """
    # Initialize the active_paths object
    common.active_paths = {
        SynchronisedActivePaths: collections.OrderedDict(),
        PrivateActivePaths: collections.OrderedDict(),
    }
    for mode in common.active_paths:
        for key in SECTIONS['active']:
            common.active_paths[mode][key] = None

    # Create the setting object, this will load the previously saved active
    # paths from the ini file.
    common.settings = UserSettings()
    common.settings.load_active_values()
    common.update_private_values()

    v = common.settings.value('user/servers')
    if not isinstance(v, dict):
        v = {}
    common.servers = v

    v = common.settings.value('user/favourites')
    if not v or not isinstance(v, dict):
        v = {}
    common.favourites = v
    common.signals.favouritesChanged.emit()

    _init_bookmarks()


def _init_bookmarks():
    """Loads all previously saved bookmarks to memory.

    The list of bookmark items is made up of a list of default items, defined in
    `common.default_bookmarks_template`, and bookmarks added by the user, stored in
    the user setting.

    """
    _static = get_default_bookmarks()
    _static = _static if _static else {}

    # Save default items to cache
    common.default_bookmarks = _static

    _custom = common.settings.value('user/bookmarks')
    _custom = _custom if _custom else {}

    # Merge static and custom bookmarks
    v = _static.copy()
    v.update(_custom)

    # Remove invalid values before adding
    for k in list(v.keys()):
        if (
                'server' not in v[k]
                or 'job' not in v[k]
                or 'root' not in v[k]
        ):
            del v[k]
            continue
        # Add servers defined in the bookmark items:
        common.servers[v[k]['server']] = v[k]['server']

    common.bookmarks = v


def active(k, path=False, args=False):
    """Get an active path segment stored in the user settings.

    Args:
        k (str): One of the following segment names: `'server', 'job', 'root', 'asset', 'task', 'file'`
        path (bool, optional): If True, will return a path to the active item.
        args (bool, optional): If `True`, will return all components that make up the active path.

    Returns:
        * str: The name of the active item.
        * str (when path=True): Path to the active item.
        * tuple (when args=True): Active path elements.

    """
    if k not in SECTIONS['active']:
        raise KeyError('Invalid key')

    if path or args:
        _path = None
        _args = None
        idx = SECTIONS['active'].index(k)
        v = tuple(
            common.active_paths[common.active_mode][k]
            for k in SECTIONS['active'][:idx + 1]
        )

        if path:
            _path = '/'.join(v) if all(v) else None
            if args:
                return _path, _args
            return _path

        if args:
            _args = v if all(v) else None
            if path:
                return _path, _args
            return _args

    return common.active_paths[common.active_mode][k]


def get_user_settings_path():
    """Returns the path to the user settings file."""
    v = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.GenericDataLocation
    )
    return f'{v}/{common.product}/{common.user_settings}'


def get_default_bookmarks():
    """Loads any preconfigured bookmark items from the json config file.

    Returns:
        dict: The parsed data.

    """
    source = common.rsc(
        f'{common.TemplateResource}/{common.default_bookmarks_template}'
    )

    data = {}
    try:
        with open(source, 'r', encoding='utf8') as f:
            data = json.loads(
                f.read(),
                parse_int=int,
                parse_float=float,
                object_hook=common.int_key
            )
    except (ValueError, TypeError):
        log.error(f'Could not decode `{source}`')
    except RuntimeError:
        log.error(f'Error opening `{source}`')
    return data


def strip(s):
    """Replace and strip backslashes.

    Args:
        s (str): The string to modify.

    Returns:
        str: The modified string.

    """
    return re.sub(
        r'\\', '/',
        s,
        flags=re.IGNORECASE
    ).strip().rstrip('/')


def bookmark_key(server, job, root):
    """Returns a generic string representation of a bookmark item.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.

    Returns:
        str: The bookmark item key.

    """
    k = '/'.join([strip(f) for f in (server, job, root)]).rstrip('/')
    return k


def update_private_values():
    """Copy the ``SynchronisedActivePaths`` values to ``PrivateActivePaths``.

    """
    for k in SECTIONS['active']:
        common.active_paths[PrivateActivePaths][k] = \
            common.active_paths[SynchronisedActivePaths][k]


_true = {'True', 'true', '1', True}
_false = {'False', 'false', 'None', 'none', '0', '', False, None}


class UserSettings(QtCore.QSettings):
    """An INI config file used to store local user settings.

    """

    def __init__(self, parent=None):
        super().__init__(
            get_user_settings_path(),
            QtCore.QSettings.IniFormat,
            parent=parent
        )

        # Simple timer to verify active paths every 30 seconds
        self.verify_timer = common.Timer(parent=self)
        self.verify_timer.setInterval(30000)
        self.verify_timer.setSingleShot(False)
        self.verify_timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.verify_timer.timeout.connect(self.load_active_values)

    def load_active_values(self):
        """Load previously saved active path elements from the settings file.

        If the resulting path is invalid, we'll progressively unset the invalid
        path segments until we find a valid path.

        """
        self.sync()
        for k in SECTIONS['active']:
            v = self.value(f'active/{k}')
            if not isinstance(v, str) or not v:
                v = None
            common.active_paths[SynchronisedActivePaths][k] = v
        self.verify_active(SynchronisedActivePaths)
        self.verify_active(PrivateActivePaths)

    def verify_active(self, m):
        """Verify the active path values and unset any item, that refers to an invalid path.

        Args:
            m (int): The active mode.

        """
        p = str()
        for k in SECTIONS['active']:
            if common.active_paths[m][k]:
                p += common.active_paths[m][k]
            if not os.path.exists(p):
                common.active_paths[m][k] = None
                if m == SynchronisedActivePaths:
                    self.setValue(f'active/{k}', None)
            p += '/'

    def set_servers(self, v):
        """Set and save the given server values.

        Args:
            v (dict):

        """
        common.check_type(v, dict)
        common.servers = v.copy()
        self.setValue('user/servers', v)
        common.signals.serversChanged.emit()

    def set_bookmarks(self, v):
        """Set and save the given bookmark item values.

        Args:
            v (dict): The bookmark item values.

        """
        common.check_type(v, dict)
        common.bookmarks = v
        self.setValue('user/bookmarks', v)
        common.signals.bookmarksChanged.emit()

    def set_favourites(self, v):
        """Set and save the given favourite item values.

        Args:
            v (dict): The favourite item values.

        """
        common.check_type(v, dict)
        common.favourites = v
        self.setValue('user/favourites', v)
        common.signals.favouritesChanged.emit()

    def value(self, key, default=None):
        """Get a value from the user settings file.

        Overrides the default `value()` method to provide type checking.
        Types are saved in `{key}_type`.

        Args:
            key (str): A settings key.
            default (object, optional): The default value if value not set.

        Returns:
            The value stored in settings or `None` if not found.

        """
        v = super().value(key, devault=default)
        t = super().value(f'{key}_type')
        if v is None:
            return None

        try:
            if t == 'NoneType':
                v = None
            elif t == 'bool' and not isinstance(v, bool):
                v = True if v in _true else (False if v in _false else v)
            elif t == 'str' and not isinstance(v, str):
                v = str(v)
            elif t == 'int' and not isinstance(v, int):
                v = int(v)
            elif t == 'float' and not isinstance(v, float):
                v = float(v)
        except:
            log.error(f'Could not convert {type(v)} to {t}')

        return v

    def setValue(self, key, v):
        """Set a value to the user settings file.

        Overrides the default `value()` method to provide type checking.
        Types are saved in `{key}_type`.

        Args:
            key (str): A settings key.
            v (object): The value to save.

        """
        # Skip saving active values when PrivateActivePaths is on
        if common.active_mode == PrivateActivePaths and key in SECTIONS['active']:
            return

        if key == 'settings/disable_oiio':
            common.signals.generateThumbnailsChanged.emit(v)
        if key == 'settings/paint_thumbnail_bg':
            common.signals.paintThumbnailBGChanged.emit(v)

        super().setValue(key, v)
        super().setValue(f'{key}_type', type(v).__name__)
