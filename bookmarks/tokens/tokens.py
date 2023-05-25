"""The module contains interface used to get and modify a bookmark item's token
values.

The default values are stored in :attr:`.DEFAULT_TOKEN_CONFIG` but each
bookmark item can be configured independently using the
:mod:`tokens.tokens_editor` widget. The custom configuration values are
stored in the bookmark's database using `TOKENS_DB_KEY` column as encoded JSON
data. 

Use :func:`.get` to retrieve token config controller instances.

.. code-block:: python
    :linenos:

    from bookmarks.tokens import tokens

    tokens_config = tokens.get(server, job, root)
    data = tokens_config.data()

    # Try to find a description for an item named 'geo'
    v = tokens_config.get_description('geo')

    # Expands all tokens using values set in the bookmark database
    s = tokens_config.expand_tokens(
        '{asset_root}/{scene}/{prefix}_{asset}_{task}_{user}_{version}.{ext}',
        ext='exr'
    )

"""
import collections
import json
import socket
import string

import OpenImageIO
from PySide2 import QtCore

from .. import common
from .. import database
from .. import log

#: The database column name
TOKENS_DB_KEY = 'tokens'

FileFormatConfig = 'FileFormatConfig'
FileNameConfig = 'FileNameConfig'
PublishConfig = 'PublishConfig'
AssetFolderConfig = 'AssetFolderConfig'

SceneFormat = 0b1
ImageFormat = 0b10
CacheFormat = 0b100
MovieFormat = 0b1000
AudioFormat = 0b10000
DocFormat = 0b100000
ScriptFormat = 0b1000000
MiscFormat = 0b10000000
NoFormat = 0
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

#: Invalid token marker string
invalid_token = '{invalid_token}'

SceneFolder = 'scene'
CacheFolder = 'cache'
RenderFolder = 'render'
DataFolder = 'data'
ReferenceFolder = 'reference'
PublishFolder = 'publish'
TextureFolder = 'textures'
MiscFolder = 'other'

#: The default token value configuration
DEFAULT_TOKEN_CONFIG = {
    FileFormatConfig: {
        0: {
            'name': 'Scene Formats',
            'flag': SceneFormat,
            'value': common.sort_words(
                'aep, ai, blend, eps, fla, ppj, prproj, psb, psd, psq, xfl, c4d, hud, '
                'hip, hiplc, hipnc, ma, mb, nk, nk~,spm, mocha, rv, tvpp, zprj'
            ),
            'description': 'Scene file formats'
        },
        1: {
            'name': 'Image Formats',
            'flag': ImageFormat,
            'value': common.sort_words(
                OpenImageIO.get_string_attribute('extension_list')
            ),
            'description': 'Image file formats'
        },
        2: {
            'name': 'Cache Formats',
            'flag': CacheFormat,
            'value': common.sort_words(
                'abc, ass, bgeo, fbx, geo, ifd, obj, rs, sc, sim, vdb, usd, usda, '
                'usdc, usdz'
            ),
            'description': 'CG cache formats'
        },
        3: {
            'name': 'Movie Formats',
            'flag': MovieFormat,
            'value': common.sort_words(
                'mov, avi, mp4, m4v'
            ),
            'description': 'Movie file formats'
        },
        4: {
            'name': 'Audio Formats',
            'flag': AudioFormat,
            'value': common.sort_words(
                'mp3, aac, m4a, wav'
            ),
            'description': 'Audio file formats'
        },
        5: {
            'name': 'Document Formats',
            'flag': DocFormat,
            'value': common.sort_words(
                'txt, doc, docx, pdf, ppt, pptx, rtf'
            ),
            'description': 'Audio file formats'
        },
        6: {
            'name': 'Script Formats',
            'flag': ScriptFormat,
            'value': common.sort_words(
                'py, pyc, pyo, pyd, jsx, js, vex, mel, env, bat, bash, json, xml'
            ),
            'description': 'Various script file formats'
        },
        7: {
            'name': 'Miscellaneous Formats',
            'flag': MiscFormat,
            'value': common.sort_words(
                'zip, rar, zipx, 7z, tar, bz2, gz, exe, app'
            ),
            'description': 'Miscellaneous file formats'
        },
    },
    FileNameConfig: {
        0: {
            'name': 'Asset Scene Task',
            'value': '{prefix}_{asset}_{mode}_{element}_{user}_{version}.{ext}',
            'description': 'Uses the project prefix, asset, task, element, '
                           'user and version names'
        },
        1: {
            'name': 'Asset Scene File (without task and element)',
            'value': '{prefix}_{asset}_{user}_{version}.{ext}',
            'description': 'Uses the project prefix, asset, user and version names'
        },
        2: {
            'name': 'Shot Scene Task',
            'value': '{prefix}_{seq}_{shot}_{mode}_{element}_{user}_{version}.{ext}',
            'description': 'Uses the project prefix, sequence, shot, mode, element, '
                           'user and version names'
        },
        3: {
            'name': 'Shot Scene Task (without task and element)',
            'value': '{prefix}_{seq}_{shot}_{user}_{version}.{ext}',
            'description': 'Uses the project prefix, sequence, shot, user and '
                           'version names'
        },
        4: {
            'name': 'Versioned Element',
            'value': '{element}_{version}.{ext}',
            'description': 'File name with an element and version name'
        },
        5: {
            'name': 'Non-Versioned Element',
            'value': '{element}.{ext}',
            'description': 'A non-versioned element file'
        },
        6: {
            'name': 'Studio Aka - Shot',
            'value': '{prefix}_{seq}_{shot}_{mode}_{element}.{version}.{ext}',
            'description': 'Studio Aka - ShotGrid file template'
        },
        7: {
            'name': 'Studio Aka - Asset',
            'value': '{prefix}_{asset1}_{mode}_{element}.{version}.{ext}',
            'description': 'Studio Aka - ShotGrid file template'
        }
    },
    PublishConfig: {
        0: {
            'name': 'Shot Task',
            'value': '{server}/{job}/publish/{sequence}_{shot}/{task}/{element}/{prefix}_{sequence}_{shot}_{task}_{element}.{ext}',
            'description': 'Publish a shot task element',
            'filter': SceneFormat | ImageFormat | MovieFormat | CacheFormat,
        },
        1: {
            'name': 'Asset Task',
            'value': '{server}/{job}/publish/asset_{asset}/{task}/{element}/{prefix}_{asset}_{task}_{element}.{ext}',
            'description': 'Publish an asset task element',
            'filter': SceneFormat | ImageFormat | MovieFormat | CacheFormat,
        },
        3: {
            'name': 'Shot Thumbnail',
            'value': '{server}/{job}/publish/{sequence}_{shot}/thumbnail.{ext}',
            'description': 'Publish an shot thumbnail',
            'filter': ImageFormat,
        },
        4: {
            'name': 'Asset Thumbnail',
            'value': '{server}/{job}/publish/asset_{asset}/thumbnail.{ext}',
            'description': 'Publish an asset thumbnail',
            'filter': ImageFormat,
        },
        5: {
            'name': 'Studio Aka - Asset',
            'value': '{server}/{job}/{root}/{asset}/publish/{prefix}_{asset_alt1}_{task}_{element}.{ext}',
            'description': 'Publish an asset',
            'filter': SceneFormat | ImageFormat | MovieFormat | CacheFormat,
        },
        6: {
            'name': 'Studio Aka - Shot',
            'value': '{server}/{job}/{root}/{asset}/publish/{prefix}_{seq}_{shot}_{element}.{ext}',
            'description': 'Publish a shot element',
            'filter': SceneFormat | ImageFormat | MovieFormat | CacheFormat,
        },
    },
    AssetFolderConfig: {
        0: {
            'name': CacheFolder,
            'value': CacheFolder,
            'description': 'Alembic, FBX, OBJ and other CG caches',
            'filter': SceneFormat | ImageFormat | MovieFormat | AudioFormat |
                      CacheFormat,
            'subfolders': {
                0: {
                    'name': 'abc',
                    'value': 'alembic',
                    'description': 'Alembic (*.abc) cache files'
                },
                1: {
                    'name': 'obj',
                    'value': 'obj',
                    'description': 'OBJ cache files'
                },
                2: {
                    'name': 'fbx',
                    'value': 'fbx',
                    'description': 'FBX cache files'
                },
                3: {
                    'name': 'ass',
                    'value': 'arnold',
                    'description': 'Arnold (*.ass) cache files'
                },
                4: {
                    'name': 'usd',
                    'value': 'usd',
                    'description': 'USD stage and cache files'
                },
                5: {
                    'name': 'usda',
                    'value': 'usd',
                    'description': 'USD stage and cache files'
                },
                6: {
                    'name': 'usdc',
                    'value': 'usd',
                    'description': 'USD stage and cache files'
                },
                7: {
                    'name': 'usdz',
                    'value': 'usd',
                    'description': 'USD stage and cache files'
                },
                8: {
                    'name': 'geo',
                    'value': 'geo',
                    'description': 'Houdini cache files'
                },
                9: {
                    'name': 'bgeo',
                    'value': 'geo',
                    'description': 'Houdini cache files'
                },
                10: {
                    'name': 'vdb',
                    'value': 'vdb',
                    'description': 'Volume caches'
                },
                11: {
                    'name': 'ma',
                    'value': 'maya',
                    'description': 'Maya scene exports'
                },
                12: {
                    'name': 'mb',
                    'value': 'maya',
                    'description': 'Maya scene exports'
                }
            }
        },
        1: {
            'name': DataFolder,
            'value': DataFolder,
            'description': 'Temporary data files, or content generated by '
                           'applications',
            'filter': AllFormat,
            'subfolders': {},
        },
        2: {
            'name': ReferenceFolder,
            'value': ReferenceFolder,
            'description': 'References, e.g., images, videos or sound files',
            'filter': ImageFormat | DocFormat | AudioFormat | MovieFormat,
            'subfolders': {},
        },
        3: {
            'name': RenderFolder,
            'value': 'images',
            'description': 'Render layer outputs',
            'filter': ImageFormat | AudioFormat | MovieFormat,
            'subfolders': {},
        },
        4: {
            'name': SceneFolder,
            'value': 'scenes',
            'description': 'Project and scene files',
            'filter': SceneFormat,
            'subfolders': {
                0: {
                    'name': 'layout',
                    'value': 'layout',
                    'description': 'Layout, blockomatic & animatics scenes'
                },
                1: {
                    'name': 'model',
                    'value': 'model',
                    'description': 'Modeling & sculpting scenes'
                },
                2: {
                    'name': 'rig',
                    'value': 'rig',
                    'description': 'Character rigging scenes'
                },
                3: {
                    'name': 'render',
                    'value': 'render',
                    'description': 'Render and lighting projects'
                },
                4: {
                    'name': 'anim',
                    'value': 'anim',
                    'description': 'Animation scenes'
                },
                5: {
                    'name': 'fx',
                    'value': 'fx',
                    'description': 'FX project files'
                },
                6: {
                    'name': 'comp',
                    'value': 'comp',
                    'description': 'Compositing project files'
                },
                7: {
                    'name': 'audio',
                    'value': 'audio',
                    'description': 'Audio and SFX project files'
                },
                8: {
                    'name': 'tracking',
                    'value': 'tracking',
                    'description': 'Motion tracking projects'
                },
            },
        },
        5: {
            'name': PublishFolder,
            'value': 'publish',
            'description': 'Asset publish files',
            'filter': ImageFormat | MovieFormat | AudioFormat
        },
        6: {
            'name': TextureFolder,
            'value': 'sourceimages',
            'description': '2D and 3D texture files',
            'filter': ImageFormat | MovieFormat | AudioFormat,
            'subfolders': {},
        },
        7: {
            'name': MiscFolder,
            'value': 'other',
            'description': 'Miscellaneous asset files',
            'filter': AllFormat,
            'subfolders': {},
        }
    }
}


def get(server, job, root, force=False):
    """Returns the :class:`.TokenConfig` of the specified
    bookmark item.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.
        force (bool, optional): Force retrieve tokens from the database.

    Returns:
        TokenConfig: The token config controller instance.

    """
    for arg in (server, job, root):
        common.check_type(arg, str)

    key = common.get_thread_key(server, job, root)
    if key in common.token_configs:
        if force:
            common.token_configs[key].data(force=True)
        return common.token_configs[key]

    try:
        # Fetch the currently stored data from the database
        v = TokenConfig(server, job, root)
        v.data(force=True)
        common.token_configs[key] = v
        return common.token_configs[key]
    except Exception:
        common.token_configs[key] = None
        if key in common.token_configs:
            del common.token_configs[key]
        raise


def get_folder(token):
    """Find the value an asset folder token based on
    the bookmark item's token configuration.

    Returns:
        str: The current folder value.

    """
    server = common.active('server')
    job = common.active('job')
    root = common.active('root')

    if not all((server, job, root)):
        raise RuntimeError('No active bookmark item found.')

    config = get(server, job, root)
    v = config.get_asset_folder(token)
    return v if v else token


def get_subfolder(token, name):
    """Find the value an asset sub-folder based on the bookmark item's token
    configuration.

    Args:
        token (str): Asset folder token, e.g. `tokens.CacheFolder`.
        name (str): Sub-folder token.

    Returns:
        str: The value of the current asset sub-folder.

    """
    server = common.active('server')
    job = common.active('job')
    root = common.active('root')

    if not all((server, job, root)):
        raise RuntimeError('No active bookmark item found.')

    config = get(server, job, root)
    v = config.get_asset_subfolder(token, name)
    return v if v else name


def get_subfolders(token):
    """Find all asset sub-folder values based on the bookmark item's token configuration.

    Args:
        token (str): Asset folder token, e.g. `tokens.CacheFolder`.

    Returns:
        list: A list of current asset sub-folder values.

    """
    server = common.active('server')
    job = common.active('job')
    root = common.active('root')

    if not all((server, job, root)):
        raise RuntimeError('No active bookmark item found.')

    config = get(server, job, root)
    return config.get_asset_subfolders(token)


def get_description(token):
    """Get a description of a token.

    Args:
        token (str): A token, e.g. `tokens.SceneFormat`.

    Returns:
        str: Description of the item.

    """
    server = common.active('server')
    job = common.active('job')
    root = common.active('root')

    if not all((server, job, root)):
        raise RuntimeError('No active bookmark item found.')

    config = get(server, job, root)
    return config.get_description(token)


class TokenConfig(QtCore.QObject):
    """The class is used to interface with token configuration stored in the
    bookmark item's database.

    As token config data might be used in performance sensitive sections,
    the instance is uninitialized until :meth:`data` is called. This will load
    values from the database and cache it internally. This cached data won't be
    updated from the database until :meth:`.data(force=True)` is called.

    """

    def __init__(self, server, job, root, asset=None, parent=None):
        super().__init__(parent=parent)

        self.server = server
        self.job = job
        self.root = root
        self.asset = asset

        self._initialized = False
        self._data = DEFAULT_TOKEN_CONFIG.copy()

    def data(self, force=False):
        """Returns the current token config values stored in the bookmark database.

        The results fetched from the bookmark database are cached to
        `self._data`. To re-query the values from the bookmark database, an
        optional `force=True` can be passed.

        Args:
             force (bool, optional): Force retrieve tokens from the database.

         Returns:
             dict: Token config values.

        """
        if not force and self._initialized:
            return self._data

        try:
            db = database.get_db(self.server, self.job, self.root)
            v = db.value(
                db.source(),
                TOKENS_DB_KEY,
                database.BookmarkTable
            )
            if not v or not isinstance(v, dict):
                v = {}

            # Patch data with default values if any section is missing
            for k in DEFAULT_TOKEN_CONFIG:
                if k not in v:
                    v[k] = DEFAULT_TOKEN_CONFIG[k].copy()

            self._data = v

            return self._data
        except (RuntimeError, ValueError, TypeError):
            log.error('Failed to get token config from the database.')
            return self._data
        finally:
            self._initialized = True

    def set_data(self, data):
        """Saves a data dictionary to the bookmark database as an encoded
        JSON object.

        Args:
            data (dict): The token config data to save.

        """
        common.check_type(data, dict)

        db = database.get_db(self.server, self.job, self.root)
        db.set_value(
            db.source(),
            TOKENS_DB_KEY,
            data,
            table=database.BookmarkTable
        )

        # Re-fetching data from the database
        return self.data(force=True)

    def dump_json(self, destination, force=False):
        """Save the current configuration as a JSON file.

        Args:
            destination (str): Destination path.
            force (bool, optional): Force retrieve tokens from the database.

        """
        file_info = QtCore.QFileInfo(destination)
        if not file_info.dir().exists():
            raise OSError(
                '{} does not exists. Specify a valid destination.'.format(
                    file_info.dir().path()
                )
            )

        data = self.data(force=force)
        try:
            json_data = json.dumps(data, sort_keys=True, indent=4)
        except (RuntimeError, ValueError, TypeError):
            log.error('Failed to convert data to JSON.')
            raise

        with open(file_info.filePath(), 'w') as f:
            f.write(json_data)
            log.success(
                'Asset folder configuration saved to {}'.format(
                    file_info.filePath()
                )
            )

    def get_description(self, token, force=False):
        """Utility method used to get the description of a token.

        Args:
            token (str): A file-format or a folder name, e.g. 'anim'.
            force (bool, optional): Force retrieve tokens from the database.

        Returns:
            str: The description of the token.

        """
        common.check_type(token, str)

        data = self.data(force=force)
        if not data:
            return ''

        for value in data.values():
            for v in value.values():
                if token.lower() == v['value'].lower():
                    return v['description']

                if 'subfolders' not in v:
                    continue

                for _v in v['subfolders'].values():
                    if token.lower() == _v['value'].lower():
                        return _v['description']
        return ''

    def expand_tokens(
            self, s, user=common.get_username(), version='v001',
            host=socket.gethostname(), task='main',
            ext=None, prefix=None, **_kwargs
    ):
        """Expands all valid tokens of the given string, based on the current
        database values.

        Invalid tokens will be marked :attr:`.invalid_token`.

        Args:
            s (str): The string containing tokens to be expanded.
            user (str, optional): Username.
            version (str, optional): The version string.
            host (str, optional): The name of the current machine/host.
            task (str, optional): Task folder name.
            ext (str, optional): File format extension.
            prefix (str, optional): Bookmark item prefix.
            _kwargs (dict, optional): Optional token/value pairs.

        Returns:
            str: The expanded string. It might contain :attr:`.invalid_token` markers
            if a token does not have a corresponding value.

        """
        kwargs = self.get_tokens(
            user=user,
            version=version,
            ver=version,
            host=host,
            workstation=host,
            task=task,
            mode=task,
            ext=ext,
            extension=ext,
            format=ext,
            prefix=prefix,
            **_kwargs
        )

        for k in [f for f in kwargs if kwargs[f] is None]:
            del kwargs[k]

        # To avoid KeyErrors when invalid tokens are passed we will replace
        # the these with a custom marker
        # via https://stackoverflow.com/questions/17215400/format-string-unused
        # -named-arguments
        return string.Formatter().vformat(
            s,
            (),
            collections.defaultdict(lambda: invalid_token, **kwargs)
        )

    def get_tokens(self, force=False, **kwargs):
        """Get all available tokens.

        Args:
            force (bool, optional): Force retrieve tokens from the database.

        Returns:
            dict: A dictionary of token/value pairs.

        """
        data = self.data(force=force)

        if not data:
            return {}
        if AssetFolderConfig not in data:
            return {}

        tokens = {}

        # Populate tokens with the database values
        for k, v in data[AssetFolderConfig].items():
            tokens[v['name']] = v['value']

        # Populate tokens with the environment values
        tokens['server'] = self.server
        tokens['job'] = self.job
        tokens['root'] = self.root

        tokens['project'] = self.job
        tokens['bookmark'] = f'{self.server}/{self.job}/{self.root}'

        for k, v in kwargs.items():
            tokens[k] = v

        def _get(_k):
            if _k not in kwargs or not kwargs[_k]:
                _v = db.value(db.source(), _k, database.BookmarkTable)
                _v = _v if _v else invalid_token
                tokens[_k] = _v

        # We can also use bookmark item properties as tokens
        db = database.get_db(self.server, self.job, self.root)
        _get('width')
        _get('height')
        _get('framerate')
        _get('prefix')
        _get('startframe')
        _get('duration')

        # The asset root token will only be available when the asset is manually
        # specified
        if 'asset' in kwargs and kwargs['asset']:
            tokens['asset_root'] = '{}/{}/{}/{}'.format(
                self.server,
                self.job,
                self.root,
                kwargs['asset']
            )

        # We also want to use the path elements as tokens,
        # so we will split them and add them to the tokens dictionary
        for k in ('server', 'job', 'root', 'asset', 'task'):
            if k not in tokens:
                continue
            s = tokens[k].replace('//', '').strip('/')
            if '/' in s:
                for n, s in enumerate(s.split('/')):
                    tokens[f'{k}{n}'] = s

        return tokens

    def get_extensions(self, flag, force=False):
        """Returns a list of extensions associated with the given flag.

        Args:
            flag (int): A format filter flag.
            force (bool, optional): Force retrieve tokens from the database.

        Returns:
            tuple:           A tuple of file format extensions.

        """
        data = self.data(force=force)
        if FileFormatConfig not in data:
            raise KeyError('Malformed data, `FileFormatConfig` not found.')

        extensions = []
        for v in data[FileFormatConfig].values():
            if not (v['flag'] & flag):
                continue
            if not isinstance(v['value'], str):
                continue
            extensions += [f.strip() for f in v['value'].split(',')]
        return tuple(sorted(set(extensions)))

    def check_task(self, task, force=False):
        common.check_type(task, str)

        data = self.data(force=force)
        if AssetFolderConfig not in data:
            raise KeyError('Malformed data, `AssetFolderConfig` not found.')

        for v in data[AssetFolderConfig].values():
            if v['value'].lower() == task.lower():
                return True
        return False

    def get_task_extensions(self, task, force=False):
        """Returns a list of allowed extensions for the given task folder.

        Args:
            task (str): The name of a task folder.
            force (bool, optional): Force retrieve tokens from the database.

        Returns:
            set: A set of file format extensions.

        """
        common.check_type(task, str)

        data = self.data(force=force)
        if AssetFolderConfig not in data:
            raise KeyError('Malformed data, `AssetFolderConfig` not found.')

        for v in data[AssetFolderConfig].values():
            if v['value'].lower() != task.lower():
                continue
            if 'filter' not in v:
                continue
            return set(self.get_extensions(v['filter']))
        return set()

    def get_asset_folder(self, k, force=False):
        """Return the name of an asset folder based on the current token config
        values.

        """
        data = self.data(force=force)
        if not data:
            return None

        for v in data[AssetFolderConfig].values():
            if v['name'] == k:
                return v['value']
        return None

    def get_asset_subfolder(self, token, folder, force=False):
        """Returns the value of an asset sub-folder based on the current token config
        values.

        Args:
            token (str): An asset folder name (not value!),
                e.g.`config.ExportFolder`.
            folder (str): A sub folder name, e.g. `abc`.
            force (bool, optional): Force reload data from the database.

        Returns:
            str: A custom value set in config settings, or None.

        """
        data = self.data(force=force)
        if not data:
            return None

        for v in data[AssetFolderConfig].values():
            if v['name'] != token:
                continue
            if 'subfolders' not in v:
                return None
            for subfolder in v['subfolders'].values():
                if subfolder['name'] == folder:
                    return subfolder['value']
        return None

    def get_asset_subfolders(self, token, force=False):
        """Returns the value of an asset sub-folder based on the current token config
        values.

        Args:
            token (str): An asset folder name (not value!),
                e.g.`tokens.ExportFolder`.
            force (bool, optional): Force reload data from the database.

        Returns:
            list: A tuple of folder names.

        """
        data = self.data(force=force)
        if not data:
            return []

        for v in data[AssetFolderConfig].values():
            if v['name'] != token:
                continue
            if 'subfolders' not in v:
                continue
            return sorted({_v['value'] for _v in v['subfolders'].values()})

        return []
