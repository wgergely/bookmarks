# -*- coding: utf-8 -*-
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
        'settings/jobs_have_clients',
        'settings/job_scan_depth',
        'settings/ui_scale',
        'settings/show_menu_icons',
        'settings/paint_thumbnail_bg',
        'settings/disable_oiio',
        'settings/always_always_on_top',
        'settings/frameless',
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
        'filters/sort_by_basename',
        'filters/sort_by',
        'filters/sort_order',
        'filters/row_heights',
        'filters/selection_file',
        'filters/selection_sequence',
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
    'shotgrid': (
        'shotgrid/link_multiple_filter',
        'shotgrid/publish_task',
        'shotgrid/publish_type',
        'shotgrid/publish_version',
        'shotgrid/current_user',
        'shotgrid/current_asset',
        'shotgrid/current_selection',
        'shotgrid/sg_user',
        'shotgrid/sg_storage',
        'shotgrid/sg_type',
    ),
    'file_saver': (
        'file_saver/task',
        'file_saver/element',
        'file_saver/extension',
        'file_saver/template',
        'file_saver/user',
    ),
    'bookmark_editor': (
        'bookmark_editor/server',
        'bookmark_editor/job',
        'bookmark_editor/root',
    ),
    'ffmpeg': (
        'ffmpeg/preset',
        'ffmpeg/size',
        'ffmpeg/timecode',
    ),
    'maya': (
        'maya/sync_workspace',
        'maya/workspace_save_warnings',
        'maya/push_capture_to_rv',
        'maya/reveal_capture',
        'maya/publish_capture',
    ),
    'maya_export': (
        'maya_export/type',
        'maya_export/set',
        'maya_export/timeline',
        'maya_export/version',
        'maya_export/keep_open',
    ),
    'publish': (
        'publish/template',
        'publish/task',
        'publish/copy_path',
        'publish/reveal',
    ),
}

KEYS = set()
for __k in SECTIONS:
    KEYS.update({f for f in SECTIONS[__k]})
del __k

SynchronisedActivePaths = 0
PrivateActivePaths = 1


def init_settings():
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
    """Get the current active item.

    Args:
        k (str): The name of the path segment, e.g. `'server'`.
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
        v = tuple(common.active_paths[common.active_mode][k]
                  for k in SECTIONS['active'][:idx + 1])

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
        QtCore.QStandardPaths.GenericDataLocation)
    return f'{v}/{common.product}/{common.user_settings}'


def get_default_bookmarks():
    """Loads any preconfigured bookmark items from the json config file.

    Returns:
        dict: The parsed data.

    """
    source = common.get_rsc(
        f'{common.TemplateResource}/{common.default_bookmarks_template}')

    data = {}
    try:
        with open(source, 'r', encoding='utf8') as f:
            data = json.loads(f.read())
    except (ValueError, TypeError):
        log.error(f'Could not decode `{source}`')
    except RuntimeError:
        log.error(f'Error opening `{source}`')
    return data


def strip(s):
    return re.sub(
        r'\\', '/',
        s,
        flags=re.UNICODE | re.IGNORECASE
    ).strip().rstrip('/')


def bookmark_key(*args):
    k = '/'.join([strip(f) for f in args]).rstrip('/')
    return k


def update_private_values():
    for k in SECTIONS['active']:
        common.active_paths[PrivateActivePaths][k] = \
            common.active_paths[SynchronisedActivePaths][k]


_true = {'True', 'true', '1', True}
_false = {'False', 'false', 'None', 'none', '0', '', False, None}


class UserSettings(QtCore.QSettings):
    """An `ini` config file to store all local user common.

    This is where the current bookmarks, saved favourites, active bookmark,
    assets and files and other widget states are kept.

    Active Path:
        The active path is saved in the following segments:

        * active/server (str):    Server, e.g. '//server/data'.
        * active/job (str):       Job folder name inside the server.
        * active/root (str):      Job-relative bookmark path, e.g. 'seq_010/shots'.
        * active/asset (str):     Job folder name inside the root, e.g. 'shot_010'.
        * active/task (str):      A folder, e.g. 'scenes', 'renders', etc.
        * active/file (str):      A relative file path.

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
        common.check_type(v, dict)
        common.servers = v.copy()
        self.setValue('user/servers', v)

    def set_bookmarks(self, v):
        common.check_type(v, dict)
        common.bookmarks = v
        self.setValue('user/bookmarks', v)

    def set_favourites(self, v):
        common.check_type(v, dict)
        self.setValue('user/favourites', v)

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

        super().setValue(key, v)
        super().setValue(f'{key}_type', type(v).__name__)
