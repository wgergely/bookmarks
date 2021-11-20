# -*- coding: utf-8 -*-
"""Defines the customized QSettings instance used to
store favourites, server, and ui states.

"""
import collections
import os
import json
import re


from PySide2 import QtCore

from . import log
from . import common


LOCAL_SETTINGS_FILE_NAME = 'local_settings.ini'

_instance = None


def instance():
    global _instance
    if _instance is None:
        _instance = Settings()
    return _instance


def delete():
    global _instance
    try:
        _instance.deleteLater()
    except:
        pass
    _instance = None


ActiveSection = 'Active'
ServerKey = 'Server'
JobKey = 'Job'
RootKey = 'Root'
AssetKey = 'Asset'
TaskKey = 'Task'
FileKey = 'File'


ACTIVE = None
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
    return ACTIVE[k]


class Settings(QtCore.QSettings):
    """An `ini` config file to store all local user settings.

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
        self.config_path = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        self.config_path = '{}/{}/{}'.format(
            self.config_path,
            common.PRODUCT,
            LOCAL_SETTINGS_FILE_NAME
        )

        super(Settings, self).__init__(
            self.config_path,
            QtCore.QSettings.IniFormat,
            parent=parent
        )

        # Internal data storage to use when `SESSION_MODE` is PrivateActivePaths
        self.PRIVATE_SESSION_MODE_VALUES = {
            ActiveSection + '/' + ServerKey: None,
            ActiveSection + '/' + JobKey: None,
            ActiveSection + '/' + RootKey: None,
            ActiveSection + '/' + AssetKey: None,
            ActiveSection + '/' + TaskKey: None,
            ActiveSection + '/' + FileKey: None,
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
        self.init_servers()
        self.init_bookmarks()
        self.init_favourites()

        # Save the current active paths as our private paths
        self.init_private_data()

    def init_private_data(self):
        self.PRIVATE_SESSION_MODE_VALUES = {
            ActiveSection + '/' + ServerKey: active(ServerKey),
            ActiveSection + '/' + JobKey: active(JobKey),
            ActiveSection + '/' + RootKey: active(RootKey),
            ActiveSection + '/' + AssetKey: active(AssetKey),
            ActiveSection + '/' + TaskKey: active(TaskKey),
            ActiveSection + '/' + FileKey: active(FileKey),
        }

    def init_servers(self):
        """Loads and caches a list of user-saved servers.

        """
        val = self.value(CurrentUserPicksSection, ServersKey)
        if not val:
            common.SERVERS = []
            return common.SERVERS

        # Make sure we always return a list, even if there's only one items
        # saved
        if isinstance(val, (str, str)):
            common.SERVERS = [strip(val), ]
            return common.SERVERS

        common.SERVERS = sorted(set(val))
        return common.SERVERS

    def init_favourites(self):
        """Load saved favourites from the settings fils.

        Favourites are stored as dictionary items:

        .. code-block:: python
            {
                '//myserver/jobs/job1234/assets/scenes/myfile.ma': {
                    ServerKey: '//myserver/jobs',
                    JobKey: 'job1234',
                    RootKey: 'assets'
                }
            }

        Returns:
            dict: A dictionary of favourites

        """
        v = self.value(CurrentUserPicksSection, FavouritesKey)

        if not v:
            common.FAVOURITES = {}
            common.FAVOURITES_SET = set()
            return {}

        if not isinstance(v, dict):
            common.FAVOURITES = {}
            common.FAVOURITES_SET = set()
            return {}

        common.FAVOURITES = v
        common.FAVOURITES_SET = set(v)

        # Emit signal to indicate the favourite items have been loaded
        common.signals.favouritesChanged.emit()

        return v

    def init_bookmarks(self):
        """Loads all previously saved bookmarks to memory.

        The list of bookmarks is made up of a list of persistent bookmarks,
        defined in `persistent_bookmarks.json`, and bookmarks added manually by
        the user, stored in the `local_settings`.

        Each bookmark is represented as a dictionary entry:

        .. code-block:: python

            v = {
                '//my_server/my_job/path/to/my_root_folder': {
                    ServerKey: '//my_server',
                    JobKey: 'my_job',
                    RootKey: 'path/to/my_root_folder'
                }
            }

        Returns:
            dict:   A dictionary containing all currently available bookmarks.

        """
        _persistent = self.persistent_bookmarks()
        _persistent = _persistent if _persistent else {}

        # Save persistent items to cache
        common.PERSISTENT_BOOKMARKS = _persistent

        _custom = self.value(CurrentUserPicksSection, BookmarksKey)
        _custom = _custom if _custom else {}

        v = _persistent.copy()
        v.update(_custom)

        for k in v.keys():
            if (
                ServerKey not in v[k]
                or JobKey not in v[k]
                or RootKey not in v[k]
            ):
                del v[k]
            # Add server from bookmarks
            common.SERVERS.append(v[k][ServerKey])

        common.SERVERS = sorted(set(common.SERVERS))
        common.BOOKMARKS = v
        return v

    def set_servers(self, v):
        common.check_type(v, (tuple, list))
        servers = sorted(set(v))
        common.SERVERS = servers
        self.setValue(CurrentUserPicksSection, ServersKey, servers)

    def set_bookmarks(self, v):
        common.check_type(v, dict)
        common.BOOKMARKS = v
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

        for k in ACTIVE_KEYS:
            ACTIVE[k] = self.value(ActiveSection, k)

        # Let's check the path and unset any invalid parts
        path = str()
        for k in ACTIVE:
            if ACTIVE[k]:
                path += ACTIVE[k]
            if not QtCore.QFileInfo(path).exists():
                ACTIVE[k] = None
                self.setValue(ActiveSection, k, None)
            path += '/'
        return ACTIVE

    def persistent_bookmarks(self):
        """Loads any preconfigured bookmarks from the json config file.

        Returns:
            dict: The parsed data.

        """
        if not os.path.isfile(common.PERSISTENT_BOOKMARKS_SOURCE):
            log.error('persistent_bookmarks.json not found.')
            return {}

        data = {}
        try:
            with open(common.PERSISTENT_BOOKMARKS_SOURCE, 'r', encoding='utf8') as f:
                data = json.load(f)
        except (ValueError, TypeError):
            log.error('Could not decode `persistent_bookmarks.json`')
        except RuntimeError:
            log.error('Error opening `persistent_bookmarks.json`')
        return data

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
        if common.SESSION_MODE == common.PrivateActivePaths and section == ActiveSection:
            return self.PRIVATE_SESSION_MODE_VALUES[k]

        t = super(Settings, self).value(k + '_type')
        v = super(Settings, self).value(k)
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
        if common.SESSION_MODE == common.PrivateActivePaths and section == ActiveSection:
            self.PRIVATE_SESSION_MODE_VALUES[k] = v
            return

        super(Settings, self).setValue(k, v)
        super(Settings, self).setValue(k + '_type', type(v).__name__)
