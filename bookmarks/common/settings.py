# -*- coding: utf-8 -*-
"""Defines the customized QSettings instance used to
store user and app common.

"""
import os
import json
import re

from PySide2 import QtCore

from .. import log
from .. import common


ActiveSection = 'Active'
ServerKey = 'Server'
JobKey = 'Job'
RootKey = 'Root'
AssetKey = 'Asset'
TaskKey = 'Task'
FileKey = 'File'

ACTIVE_KEYS = (
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
    common.settings = UserSettings()

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
    return v


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


def active(k):
    return common.ACTIVE[k]


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
        self._active_section_values = {
            f'{ActiveSection}/{ServerKey}': None,
            f'{ActiveSection}/{JobKey}': None,
            f'{ActiveSection}/{RootKey}': None,
            f'{ActiveSection}/{AssetKey}': None,
            f'{ActiveSection}/{TaskKey}': None,
            f'{ActiveSection}/{FileKey}': None,
        }

        # Simple timer to verify active paths every 30 seconds
        self.verify_timer = common.Timer(parent=self)
        self.verify_timer.setInterval(30000)
        self.verify_timer.setSingleShot(False)
        self.verify_timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.verify_timer.timeout.connect(self.verify_active)

        # Make sure all saved active paths are valid
        self.verify_active()
        # Load and cache values from the settings file
        # Save the current active paths as our private paths
        self.init_private_values()

    def init_private_values(self):
        self._active_section_values = {
            f'{ActiveSection}/{ServerKey}': active(ServerKey),
            f'{ActiveSection}/{JobKey}': active(JobKey),
            f'{ActiveSection}/{RootKey}': active(RootKey),
            f'{ActiveSection}/{AssetKey}': active(AssetKey),
            f'{ActiveSection}/{TaskKey}': active(TaskKey),
            f'{ActiveSection}/{FileKey}': active(FileKey),
        }

    def set_servers(self, v):
        common.check_type(v, (tuple, list))
        servers = sorted(set(v))
        common.servers = servers
        self.setValue(CurrentUserPicksSection, ServersKey, servers)

    def set_bookmarks(self, v):
        common.check_type(v, dict)
        common.bookmarks = v
        self.setValue(CurrentUserPicksSection, BookmarksKey, v)

    def set_favourites(self, v):
        """Adds the given list to the currently saved favourites.

        """
        common.check_type(v, dict)
        self.setValue(CurrentUserPicksSection, FavouritesKey, v)

    @QtCore.Slot()
    def verify_active(self):
        """This slot verifies and returns the saved ``active paths`` wrapped in
        a dictionary.

        If the resulting active path is not an existing file, we will
        progressively unset the invalid path segments until we get a valid file
        path.

        Returns:
            OrderedDict:    Path segments of an existing file.

        """
        self.sync()

        for k in common.ACTIVE_KEYS:
            common.ACTIVE[k] = self.value(ActiveSection, k)

        # Let's check the path and unset any invalid parts
        path = str()
        for k in common.ACTIVE:
            if common.ACTIVE[k]:
                path += common.ACTIVE[k]
            if not QtCore.QFileInfo(path).exists():
                common.ACTIVE[k] = None
                self.setValue(ActiveSection, k, None)
            path += '/'
        return common.ACTIVE

    def value(self, section, key):
        """Used to retrieve a values from the local settings object.

        Overrides the default `value()` method to provide type checking.
        Types are saved in `{key}_type`.

        Args:
            section (str):  A section name.
            key (str): A key name.

        Returns:
            The value stored in `local_settings` or `None` if not found.

        """
        k = '{}/{}'.format(section, key)

        # If PrivateActivePaths is on, we won't query the settings file and
        # intead load and save from our private
        if common.session_mode == common.PrivateActivePaths and section == ActiveSection:
            return self._active_section_values[k]

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
        """Override to allow redirecting `ActiveSection` keys to be saved in memory
        when solo mode is on.

        """
        k = '{}/{}'.format(section, key)

        # Save active path values in our private data instead of the settings file
        if common.session_mode == common.PrivateActivePaths and section == ActiveSection:
            self._active_section_values[k] = v
            return

        super().setValue(k, v)
        super().setValue(k + '_type', type(v).__name__)
