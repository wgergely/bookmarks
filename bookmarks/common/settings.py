# -*- coding: utf-8 -*-
"""Defines the customized QSettings instance used to
store user and app common.

"""
import os
import json
import re
import collections

from PySide2 import QtCore

from .. import log
from .. import common


SyncronisedActivePaths = 0
PrivateActivePaths = 1

ActiveSection = 'Active'
ServerKey = 'Server'
JobKey = 'Job'
RootKey = 'Root'
AssetKey = 'Asset'
TaskKey = 'Task'
FileKey = 'File'

ActiveSectionCacheKeys = (
    ServerKey,
    JobKey,
    RootKey,
    AssetKey,
    TaskKey,
    FileKey,
)

CurrentUserPicksSection = 'UserPicks'
ServersKey = 'Servers'
BookmarksKey = 'Bookmarks'
FavouritesKey = 'Favourites'

SettingsSection = 'Settings'
FFMpegKey = 'FFMpegPath'
RVKey = 'RVPath'
UIScaleKey = 'UIScale'
ShowMenuIconsKey = 'ShowMenuIcons'
ShowThumbnailBackgroundKey = 'ShowThumbnailBackgroundKey'
WorkspaceSyncKey = 'WorkspaceSync'
WorksapceWarningsKey = 'WorkspaceWarnings'
SaveWarningsKey = 'SaveWarnings'
PushCaptureToRVKey = 'PushCaptureToRV'
RevealCaptureKey = 'RevealCapture'
PublishCaptureKey = 'PublishCapture'


ListFilterSection = 'ListFilters'
ActiveFlagFilterKey = 'ActiveFilter'
ArchivedFlagFilterKey = 'ArchivedFilter'
FavouriteFlagFilterKey = 'FavouriteFilter'
TextFilterKey = 'TextFilter'
TextFilterKeyHistory = 'TextFilterHistory'

UIStateSection = 'UIState'
WindowGeometryKey = 'WindowGeometry'
WindowStateKey = 'WindowState'
SortByBaseNameKey = 'SortByBaseName'
WindowAlwaysOnTopKey = 'WindowAlwaysOnTop'
WindowFramelessKey = 'WindowFrameless'
InlineButtonsHidden = 'InlineButtonsHidden'
CurrentRowHeight = 'CurrentRowHeight'
CurrentList = 'CurrentListIdx'
CurrentSortRole = 'CurrentSortRole'
CurrentSortOrder = 'CurrentSortOrder'
CurrentDataType = 'CurrentDataType'
GenerateThumbnails = 'GenerateThumbnails'
FileSelectionKey = 'FileSelection'
SequenceSelectionKey = 'FileSequenceSelection'
BookmarkEditorServerKey = 'BookmarkEditorServer'
BookmarkEditorJobKey = 'BookmarkEditorJob'
SlackUserKey = 'SlackUser'
LinkMultipleCurrentFilter = 'LinkMultipleCurrentFilter'
PublishTask = 'PublishTask'
PublishFileType = 'PublishFileType'

FileSaverSection = 'FileSaver'
CurrentFolderKey = 'CurrentFolder'
CurrentTemplateKey = 'CurrentTemplate'

PublishVersionSection = 'PublishVersion'
CurrentUserKey = 'CurrentUser'
CurrentAssetKey = 'CurrentAsset'
CurrentSelectionKey = 'CurrentSelection'

SGUserKey = 'SGUser'
SGStorageKey = 'SGStorage'
SGTypeKey = 'SGType'


def init_settings():
    # Initialize the ActiveSectionCache object
    common.ActiveSectionCache = {
        SyncronisedActivePaths: collections.OrderedDict(),
        PrivateActivePaths: collections.OrderedDict(),
    }
    for mode in common.ActiveSectionCache:
        for key in ActiveSectionCacheKeys:
            common.ActiveSectionCache[mode][key] = None

    # Create the setting object, this will load the previously saved active
    # paths from the ini file.
    common.settings = UserSettings()
    common.settings.load_active_values()
    common.settings.update_private_values()

    v = common.settings.value(CurrentUserPicksSection, ServersKey)
    if not isinstance(v, dict):
        v = {}
    common.servers = v

    v = common.settings.value(CurrentUserPicksSection, FavouritesKey)
    if not v or not isinstance(v, dict):
        v = {}
    common.favourites = v
    common.signals.favouritesChanged.emit()

    _init_bookmarks()


def _init_bookmarks():
    """Loads all previously saved bookmarks to memory.

    The list of bookmarks is made up of a list of persistent bookmarks, defined
    in `static_bookmarks.json`, and bookmarks added by the user, stored in the
    user setting.

    """
    _static = get_static_bookmarks()
    _static = _static if _static else {}

    # Save persistent items to cache
    common.static_bookmarks = _static

    _custom = common.settings.value(CurrentUserPicksSection, BookmarksKey)
    _custom = _custom if _custom else {}

    # Merge static and custom bookmarks
    v = _static.copy()
    v.update(_custom)

    # Remove invalid values before adding
    for k in list(v.keys()):
        if (
            ServerKey not in v[k]
            or JobKey not in v[k]
            or RootKey not in v[k]
        ):
            del v[k]
            continue
        # Add servers defined in the bookmark items:
        common.servers[v[k][ServerKey]] = v[k][ServerKey]

    common.bookmarks = v


def active(k, path=False, args=False):
    """Get the current active item.

    Args:
        k (str): The name of the path segment, eg. `common.ServerKey`.
        path (bool, optional): If True, will return a path to the active item.
        args (bool, optional): If `True`, will return all components that make up the path.

    Returns:
        str: The name of the active item.
        str (when path=True): Path to the active item.
        tuple (when args=True): Active path elements.

    """
    if path or args:
        _path = None
        _args = None
        idx = common.ActiveSectionCacheKeys.index(k)
        v = tuple(common.ActiveSectionCache[common.active_mode][k]
             for k in common.ActiveSectionCacheKeys[:idx + 1])

    if path:
        _path = '/'.join(v) if all(v) else None
        if args:
            return (_path, _args)
        return _path

    if args:
        _args = v if all(v) else None
        if path:
            return (_path, _args)
        return _args

    return common.ActiveSectionCache[common.active_mode][k]


def get_user_settings_path():
    v = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.GenericDataLocation)
    return f'{v}/{common.product}/{common.user_settings}'


def get_static_bookmarks():
    """Loads any preconfigured bookmark items from the json config file.

    Returns:
        dict: The parsed data.

    """
    source = common.get_template_file_path(
        common.static_bookmarks_template)
    if not os.path.isfile(source):
        log.error(f'{source} not found.')
        return {}

    data = {}
    try:
        with open(source, 'r', encoding='utf8') as f:
            data = json.load(f)
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


class UserSettings(QtCore.QSettings):
    """An `ini` config file to store all local user common.

    This is where the current bookmarks, saved favourites, active bookmark,
    assets and files and other widget states are kept.

    Active Path:
        The active path is saved in the following segments:

        * ActiveSection/ServerKey (str):    Server, eg. '//server/data'.
        * ActiveSection/JobKey (str):       Job folder name inside the server.
        * ActiveSection/RootKey (str):      Job-relative bookmark path, eg. 'seq_010/shots'.
        * ActiveSection/AssetKey (str):     Job folder name inside the root, eg. 'shot_010'.
        * ActiveSection/TaskKey (str):      A folder, eg. 'scenes', 'renders', etc.
        * ActiveSection/FileKey (str):      A relative file path.

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
        """Load previously saved active path elements from the `ini` file.

        If the resulting path is invalid, we'll progressively unset the invalid
        path segments until we find a valid path.

        """
        self.sync()
        for k in ActiveSectionCacheKeys:
            common.ActiveSectionCache[SyncronisedActivePaths][k] = self.value(ActiveSection, k)
        self.verify_active(SyncronisedActivePaths)
        self.verify_active(PrivateActivePaths)

        # for m in (SyncronisedActivePaths, PrivateActivePaths):

    def verify_active(self, m):
        """Verify the load active section values.

        Args:
                m (int): The active mode.

        """
        p = str()
        for k in ActiveSectionCacheKeys:
            if common.ActiveSectionCache[m][k]:
                p += common.ActiveSectionCache[m][k]
            if not os.path.exists(p):
                common.ActiveSectionCache[m][k] = None
                if m == SyncronisedActivePaths:
                    self.setValue(ActiveSection, k, None)
            p += '/'

    def update_private_values(self):
        for k in ActiveSectionCacheKeys:
            common.ActiveSectionCache[PrivateActivePaths][k] = common.ActiveSectionCache[SyncronisedActivePaths][k]

    def set_servers(self, v):
        common.check_type(v, dict)
        common.servers = v
        self.setValue(CurrentUserPicksSection, ServersKey, v)

    def set_bookmarks(self, v):
        common.check_type(v, dict)
        common.bookmarks = v
        self.setValue(CurrentUserPicksSection, BookmarksKey, v)

    def set_favourites(self, v):
        """Adds the given list to the currently saved favourites.

        """
        common.check_type(v, dict)
        self.setValue(CurrentUserPicksSection, FavouritesKey, v)

    def value(self, section, key):
        """Used to retrieve a values from the user settings object.

        Overrides the default `value()` method to provide type checking.
        Types are saved in `{key}_type`.

        Args:
            section (str):  A section name.
            key (str): A key name.

        Returns:
            The value stored in `user_settings` or `None` if not found.

        """
        k = f'{section}/{key}'

        t = super().value(k + '_type')
        v = super().value(k)
        if v is None:
            return

        try:
            if t == 'NoneType':
                v = None
            elif t == 'bool':
                # Convert any loose representation back to `bool()`
                if not isinstance(v, bool):
                    if v.lower() in ['true', '1']:
                        v = True
                    elif v.lower() in ['false', '0', 'none']:
                        v = False
            elif t == 'str' and not isinstance(v, str):
                v = v.encode('utf-8')
            elif t == 'str' and not isinstance(v, str):
                try:
                    v = str(v)
                except:
                    pass
            elif t == 'int' and not isinstance(v, int):
                v = int(v)
            elif t == 'float' and not isinstance(v, float):
                v = float(v)
        except:
            log.error('Type converion failed')

        return v

    def setValue(self, section, key, v):
        k = f'{section}/{key}'

        if section == common.ActiveSection and common.active_mode == PrivateActivePaths:
            return
        #     raise RuntimeError('The saved active path cannot be changed when the mode is `PrivateActivePaths`')

        super().setValue(k, v)
        super().setValue(k + '_type', type(v).__name__)
