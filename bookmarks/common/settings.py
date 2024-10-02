"""Defines a customized QSettings object used to store user settings.

The user settings are stored in an ini file stored at :func:`.get_user_settings_path`.
The current ui state, current active paths, and app settings are all stored in here.

"""
import json
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
        'user/bookmarks',
        'user/favourites',
    ),
    'settings': (
        'settings/ui_scale',
        'settings/show_menu_icons',
        'settings/paint_thumbnail_bg',
        'settings/disable_oiio',
        'settings/hide_item_descriptions',
        'settings/default_to_scenes_folder',
        'settings/always_always_on_top',
        'settings/bin_ffmpeg',
        'settings/bin_rv',
        'settings/bin_rvpush',
        'settings/bin_oiiotool',
    ),
    'servers': (
        'servers/job_style',
        'value'
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
    'ffmpeg': (
        'ffmpeg/preset',
        'ffmpeg/size',
        'ffmpeg/timecode_preset',
        'ffmpeg/sourcecolorspace',
        'ffmpeg/targetcolorspace',
        'ffmpeg/pushtorv',
    ),
    'akaconvert': (
        'akaconvert/preset',
        'akaconvert/size',
        'akaconvert/acesprofile',
        'akaconvert/inputcolor',
        'akaconvert/outputcolor',
        'akaconvert/videoburnin',
        'akaconvert/pushtorv',
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
        'publish/copy_path',
        'publish/reveal',
    ),
}

#: all keys
KEYS = set()
for __k in SECTIONS:
    KEYS.update({f for f in SECTIONS[__k]})
del __k


def init_settings():
    """Initializes the :class:`UserSettings` instance.

    """

    # Initialize the user settings instance
    common.settings = UserSettings()

    v = common.settings.value('servers/value')
    if not isinstance(v, dict):
        v = {}
    common.servers = v
    common.signals.serversChanged.emit()

    v = common.settings.value('user/favourites')
    if not v or not isinstance(v, dict):
        v = {}
    common.favourites = v
    common.signals.favouritesChanged.emit()

    from bookmarks.server.lib import ServerAPI
    ServerAPI.load_bookmarks()


def get_user_settings_path():
    """Returns the path to the user settings file."""
    v = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.GenericDataLocation
    )
    return f'{v}/{common.product}/{common.user_settings}'


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
        try:
            v = super().value(key, default)
        except:
            log.error(f'Could not get value for {key}: {self.status()}')
            super().setValue(key, default)
            super().setValue(f'{key}_type', default)
            return default

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
            elif t == 'dict' and not isinstance(v, dict):
                v = json.loads(v)
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
        # Skip saving private active values
        if common.active_mode == common.PrivateActivePaths and key in common.ActivePathSegmentTypes:
            return

        if key == 'settings/disable_oiio':
            common.signals.generateThumbnailsChanged.emit(v)
        if key == 'settings/paint_thumbnail_bg':
            common.signals.paintThumbnailBGChanged.emit(v)
        if key == 'servers/value':
            common.signals.serversChanged.emit()

        super().setValue(key, v)
        super().setValue(f'{key}_type', type(v).__name__)
