import copy
import enum
import threading

from PySide2 import QtCore

from .. import common, log, database

__all__ = [
    'Config',
    'Section',
    'Format',
    'AssetFolder',
    'State'
]


class State(enum.IntEnum):
    Omitted = common.idx(reset=True, start=0)
    OnHold = common.idx()
    NotStarted = common.idx()
    InProgress = common.idx()
    PendingReview = common.idx()
    Priority = common.idx()
    Approved = common.idx()
    Completed = common.idx()


class Section(enum.Enum):
    """Database column enums with additional info."""

    FileFormatConfig = {
        'db_column': 'config_file_format',
        'title': 'File Format Whitelist',
        'description': 'Configure which file formats are allowed to be shown in the files tab.',
        'icon': 'multiples_files',
        'color': common.Color.SecondaryText()
    }

    SceneNameConfig = {
        'db_column': 'config_scene_names',
        'title': 'Scene Name Presets',
        'description': 'Configure the presets for saving scene files.',
        'icon': 'file',
        'color': common.Color.Blue()
    }

    PublishConfig = {
        'db_column': 'config_publish',
        'title': 'Publish Paths',
        'description': 'Configure path for publishing local files.',
        'icon': 'arrow_right',
        'color': common.Color.SecondaryText()
    }

    TaskConfig = {
        'db_column': 'config_tasks',
        'title': 'Tasks',
        'description': 'The list of production tasks.',
        'icon': 'tasks',
        'color': common.Color.SecondaryText()
    }

    AssetFolderConfig = {
        'db_column': 'config_asset_folders',
        'title': 'Asset Folders',
        'description': 'Configure the asset folders.',
        'icon': 'folder',
        'color': common.Color.SecondaryText()
    }

    BurninConfig = {
        'db_column': 'config_burnin',
        'title': 'Burn-in',
        'description': 'Configure the burn-in presets.',
        'icon': 'video',
        'color': common.Color.SecondaryText()
    }

    def __init__(self, data):
        self.db_column = data['db_column']
        self.title = data['title']
        self.description = data['description']
        self.icon = data.get('icon')
        self.color = data.get('color')


class Format(enum.Flag):
    NoFormat = 0
    SceneFormat = enum.auto()
    ImageFormat = enum.auto()
    CacheFormat = enum.auto()
    MovieFormat = enum.auto()
    AudioFormat = enum.auto()
    DocFormat = enum.auto()
    ScriptFormat = enum.auto()
    MiscFormat = enum.auto()
    AllFormat = (
            SceneFormat |
            ImageFormat |
            CacheFormat |
            MovieFormat |
            AudioFormat |
            DocFormat |
            ScriptFormat |
            MiscFormat
    )


class AssetFolder(enum.StrEnum):
    SceneFolder = 'scenes'
    CacheFolder = 'caches'
    CaptureFolder = 'captures'
    RenderFolder = 'renders'
    ReferenceFolder = 'references'
    PublishFolder = 'publishes'
    TextureFolder = 'textures'
    ScriptFolder = 'scripts'
    DataFolder = 'data'


class Config(QtCore.QObject):
    """The class is used to interface with bookmark property configuration values.

    """
    #: Cache to store item instances
    _cache = {}

    #: Item's cache lock
    _lock = threading.Lock()

    def __repr__(self):
        return (
            f'<Config ('
            f'server={self._server}, '
            f'job={self._job}, '
            f'root={self._root}, '
            f'asset={self._asset}, '
            f')>'
        )

    def __str__(self):
        return self.__repr__()

    def __new__(cls, *args, **kwargs):
        """Creates a new item instance backed by a cache.

        """
        if args:
            raise ValueError('Item cannot be created with positional arguments')

        _valid_args = []
        for kwarg in kwargs:
            if not kwargs[kwarg]:
                break
            _valid_args.append(kwargs[kwarg])

        cache_key = '/'.join(_valid_args) if len(_valid_args) >= 3 else None

        # Null-item
        if not cache_key:
            cache_key = 'null'

        cls._lock.acquire(blocking=True)
        try:
            if cache_key in cls._cache:
                return cls._cache[cache_key]
            instance = super(Config, cls).__new__(cls)
            cls._cache[cache_key] = instance
            return instance
        finally:
            cls._lock.release()

    @classmethod
    def clear_cache(cls):
        """Remove all previously cached item instances from the internal item cache.

        """
        cls._lock.acquire(blocking=True)
        try:
            for key in list(cls._cache.keys()):
                del cls._cache[key]
            cls._cache = {}
        finally:
            cls._lock.release()

    def __init__(self, server, job, root, force=False, parent=None):
        super().__init__(parent=parent)

        self._server = server
        self._job = job
        self._root = root

        self._initialized = {}

        for k in Section:
            self._initialized[k] = False

        self._data = self.default_data()

        if force:
            self.data(force=True)

    @property
    def server(self):
        return self._server

    @property
    def job(self):
        return self._job

    @property
    def root(self):
        return self._root

    def is_valid(self):
        return all([self._server, self._job, self._root])

    @classmethod
    def default_data(cls):
        """Returns the default token config values.

        Returns:
            dict: Token config values.

        """
        from . import default_configs
        return {
            Section.FileFormatConfig: copy.deepcopy(default_configs.default_file_format_config),
            Section.SceneNameConfig: copy.deepcopy(default_configs.default_scene_name_config),
            Section.PublishConfig: copy.deepcopy(default_configs.default_publish_config),
            Section.TaskConfig: copy.deepcopy(default_configs.default_task_config),
            Section.AssetFolderConfig: copy.deepcopy(default_configs.default_asset_folder_config),
            Section.BurninConfig: copy.deepcopy(default_configs.default_burnin_config),
        }

    def data(self, section, force=False):
        """Returns config values of the given section.

        The results fetched from the database are cached to
        `self._data`. To re-query the values `force=True` must be set.

        Args:
            section (Section): The section to retrieve.
            force (bool, optional): Force retrieve load data from the database.

         Returns:
             dict: config values of the given section.

        """
        if section not in Section:
            raise ValueError(f'Invalid section: {section}. Expected one of {Section}')

        if not self.is_valid():
            return self._data[section]

        if not force and self._initialized[section] and section in self._data:
            return self._data[section]

        try:
            db = database.get(self.server, self.job, self.root)
            v = db.value(
                db.source(),
                section.db_column,
                database.BookmarkTable
            )

            # If no data is found, return the default values
            if not v or not isinstance(v, dict):
                return self._data[section]

            # If the data structure differs from default values, return default values
            if not v.keys() == self._data[section].keys():
                log.error('Malformed data, data structure differs from default values.')
                return self._data[section]

            self._data[section] = v

        except (RuntimeError, ValueError, TypeError):
            log.error('Failed to get token config from the database.')
        finally:
            self._initialized[section] = True

        return self._data[section]

    def set_data(self, section, data):
        """Saves the given section data to the database.

        Args:
            section (Section): The section to save.
            data (dict): The token config data to save.

        """
        common.check_type(data, dict)
        if section not in Section:
            raise ValueError(f'Invalid section: {section}. Expected one of {Section}')

        if data.keys() != self._data[section].keys():
            raise ValueError('Data structure does not match the default values.')

        try:
            db = database.get(self.server, self.job, self.root)
            db.set_value(
                db.source(),
                section.db_column,
                data,
                database.BookmarkTable
            )
        except Exception as e:
            log.error(f'Failed to save token config to the database: {e}')

        self._data[section].update(copy.deepcopy(data))

    # def get_description(self, section, token, force=False):
    #     """Returns the description of the given token.
    #
    #     Args:
    #         section (Section): The section to retrieve.
    #         token (str): A file-format or a folder name, for example, 'anim'.
    #         force (bool, optional): Force retrieve tokens from the database.
    #
    #     Returns:
    #         str: The description of the token.
    #
    #     """
    #     common.check_type(token, str)
    #
    #     if section not in Section:
    #         raise ValueError(f'Invalid section: {section}. Expected one of {Section}')
    #
    #     if section not in self._data:
    #         raise KeyError(f'Malformed data, `{section}` not found.')
    #
    #     if force:
    #         self.data(section, force=True)
    #
    #     for v in self._data[section].values():
    #         if v['name'] == token and 'description' in v:
    #             return v['description']
    #
    #     return ''
    #
    # def get_extensions(self, flag, force=False):
    #     """Returns a list of accepted extensions based on the given flag.
    #
    #     Args:
    #         flag (Format): A format flag.
    #         force (bool, optional): Force retrieve tokens from the database.
    #
    #     Returns:
    #         tuple:           A tuple of file format extensions.
    #
    #     """
    #     if flag not in Format:
    #         raise ValueError(f'Invalid flag: {flag}. Expected one of {Format}')
    #
    #     section = Section.FileFormatConfig
    #
    #     if force:
    #         self.data(section, force=True)
    #
    #     formats = []
    #
    #     # No flags
    #     if flag == Format.NoFormat:
    #         return tuple(formats)
    #
    #     # All flags
    #     if flag == Format.AllFormat:
    #         for v in self._data[section].values():
    #             if not isinstance(v['value'], str):
    #                 continue
    #             formats += [f.strip() for f in v['value'].split(',') if f.strip()]
    #         return tuple(sorted(set(formats)))
    #
    #     # Specific flags
    #     for v in self._data[section].values():
    #         if not (v['flag'] & flag):
    #             continue
    #
    #         if not isinstance(v['value'], str):
    #             continue
    #
    #         formats += [f.strip() for f in v['value'].split(',') if f.strip()]
    #
    #     return tuple(sorted(set(formats)))
    #
    # def is_asset_folder(self, folder, force=False):
    #     """Returns True if the given folder is an asset folder.
    #
    #     Args:
    #         folder (str): A folder name.
    #         force (bool, optional): Force retrieve tokens from the database.
    #
    #     Returns:
    #         bool: True if the folder is an asset folder.
    #
    #     """
    #     common.check_type(folder, str)
    #
    #     if not folder or not isinstance(folder, str):
    #         return False
    #
    #     section = Section.AssetFolderConfig
    #
    #     if force:
    #         self.data(section, force=True)
    #
    #     # Check if any of the current values match the given folder
    #     for v in self._data[section].values():
    #         if v['value'].lower() == folder.lower():
    #             return True
    #
    #         if 'subfolders' not in v:
    #             continue
    #
    #         for subfolder in v['subfolders'].values():
    #             if subfolder['value'].lower() == folder.lower():
    #                 return True
    #
    #     return False
    #
    # def get_allowed_extensions(self, folder, force=False):
    #     """Returns a list of allowed extensions for the given asset folder.
    #
    #     Args:
    #         folder (str): The name of a task folder.
    #         force (bool, optional): Force retrieve tokens from the database.
    #
    #     Returns:
    #         set: A set of file format extensions.
    #
    #     """
    #     common.check_type(folder, str)
    #
    #     if not folder or not isinstance(folder, str):
    #         return set()
    #
    #     if not self.is_asset_folder(folder, force=force):
    #         return set()
    #
    #     section = Section.AssetFolderConfig
    #
    #     if force:
    #         self.data(section, force=True)
    #
    #     for v in self._data[section].values():
    #         if v['value'].lower() == folder.lower():
    #             flag = v['flag']
    #             if flag not in Format:
    #                 log.error(f'Invalid flag: {flag}. Expected one of {Format}. Skipping...')
    #                 continue
    #             return set(self.get_extensions(flag, force=force))
    #     return set()
    #
    # def get_asset_folder(self, asset_folder, force=False):
    #     """Return the name of an asset folder based on the current token config
    #     values.
    #
    #     Args:
    #         asset_folder (AssetFolder): An asset folder name, for example `AssetFolder.SceneFolder`.
    #         force (bool, optional): Force reload data from the database.
    #
    #     Returns:
    #         str: The name of the asset folder.
    #
    #     """
    #     if asset_folder not in AssetFolder:
    #         raise ValueError(f'Invalid asset folder: {asset_folder}. Expected one of {AssetFolder}')
    #
    #     data = self.data(force=force)
    #     if not data:
    #         return None
    #
    #     section = Section.AssetFolderConfig
    #
    #     if force:
    #         self.data(section, force=True)
    #
    #     for v in self._data[section].values():
    #         if v['name'] == asset_folder.value:
    #             return v['value']
    #     return None
    #
    # def get_asset_subfolder(self, asset_folder, subfolder, force=False):
    #     """Returns the value of an asset subfolder based on the current token config
    #     values.
    #
    #     Args:
    #         asset_folder (AssetFolder): An asset folder name, for example, `AssetFolder.SceneFolder`.
    #         subfolder (str): A subfolder name, for example, `anim`.
    #         force (bool, optional): Force reload data from the database.
    #
    #     Returns:
    #         str: A custom value set in config settings, or None.
    #
    #     """
    #     if asset_folder not in AssetFolder:
    #         raise ValueError(f'Invalid asset folder: {asset_folder}. Expected one of {AssetFolder}')
    #
    #     common.check_type(subfolder, str)
    #
    #     if not subfolder or not isinstance(subfolder, str):
    #         return None
    #
    #     section = Section.AssetFolderConfig
    #
    #     if force:
    #         self.data(section, force=True)
    #
    #     if section not in self._data:
    #         return None
    #
    #     for v in self._data[section].values():
    #         if v['name'] == asset_folder:
    #             if 'subfolders' not in v:
    #                 return None
    #             for sub in v['subfolders'].values():
    #                 if sub['name'] == subfolder:
    #                     return sub['value']
    #
    #     return None
    #
    # def get_asset_subfolders(self, asset_folder, force=False):
    #     """Returns the subfolders of the given asset folder.
    #
    #     Args:
    #     Returns:
    #         list: A tuple of folder names.
    #
    #     """
    #     if asset_folder not in AssetFolder:
    #         raise ValueError(f'Invalid asset folder: {asset_folder}. Expected one of {AssetFolder}')
    #
    #     section = Section.AssetFolderConfig
    #
    #     if force:
    #         self.data(section, force=True)
    #
    #     for v in self._data[section].values():
    #         if v['name'] != asset_folder:
    #             continue
    #         if 'subfolders' not in v:
    #             continue
    #         return sorted({_v['value'] for _v in v['subfolders'].values()})
    #
    #     return []
