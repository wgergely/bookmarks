"""The module contains the interface used to get and modify a bookmark item's token
values.

"""
import json

try:
    import OpenImageIO
    oiio_extensions = OpenImageIO.get_string_attribute('extension_list')
except ImportError:
    oiio_extensions = ''

from PySide2 import QtCore

from . import common
from . import database
from . import log

FileFormatConfig = 'FileFormatConfig'
FileNameConfig = 'FileNameConfig'
PublishConfig = 'PublishConfig'
AssetFolderConfig = 'AssetFolderConfig'
TasksConfig = 'TasksConfig'
FFMpegTCConfig = 'FFMpegTCConfig'

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

#: Principal asset folders
SceneFolder = 'scenes'
CacheFolder = 'caches'
CaptureFolder = 'captures'
RenderFolder = 'renders'
DataFolder = 'data'
ReferenceFolder = 'references'
PublishFolder = 'publish'
TextureFolder = 'textures'
MiscFolder = 'other'

#: The default token value configuration
DEFAULT_TOKEN_CONFIG = {
    FileFormatConfig: {
        common.idx(reset=True, start=0): {
            'name': 'Scene Formats',
            'flag': SceneFormat,
            'value': common.sort_words(
                'aep, ai, blend, eps, fla, ppj, prproj, psb, psd, psq, xfl, c4d, hud, '
                'hip, hiplc, hipnc, ma, mb, nk, nk~, spm, mocha, rcproj, rv, tvpp, zbr, zpr, ztl, zpac, zprj'
            ),
            'description': 'Scene file formats'
        },
        common.idx(): {
            'name': 'Image Formats',
            'flag': ImageFormat,
            'value': common.sort_words(oiio_extensions),
            'description': 'Image file formats'
        },
        common.idx(): {
            'name': 'Cache Formats',
            'flag': CacheFormat,
            'value': common.sort_words(
                'abc, ass, bgeo, fbx, geo, ifd, obj, rs, sc, sim, vdb, usd, usda, '
                'usdc, usdz'
            ),
            'description': 'CG cache formats'
        },
        common.idx(): {
            'name': 'Movie Formats',
            'flag': MovieFormat,
            'value': common.sort_words(
                'mov, avi, mp4, m4v'
            ),
            'description': 'Movie file formats'
        },
        common.idx(): {
            'name': 'Audio Formats',
            'flag': AudioFormat,
            'value': common.sort_words(
                'mp3, aac, m4a, wav'
            ),
            'description': 'Audio file formats'
        },
        common.idx(): {
            'name': 'Document Formats',
            'flag': DocFormat,
            'value': common.sort_words(
                'txt, doc, docx, pdf, ppt, pptx, rtf'
            ),
            'description': 'Audio file formats'
        },
        common.idx(): {
            'name': 'Script Formats',
            'flag': ScriptFormat,
            'value': common.sort_words(
                'py, pyc, pyo, pyd, jsx, js, vex, mel, env, bat, bash, json, xml'
            ),
            'description': 'Various script file formats'
        },
        common.idx(): {
            'name': 'Miscellaneous Formats',
            'flag': MiscFormat,
            'value': common.sort_words(
                'zip, rar, zipx, 7z, tar, bz2, gz, exe, app'
            ),
            'description': 'Miscellaneous file formats'
        },
    },
    FileNameConfig: {
        common.idx(reset=True, start=0): {
            'name': 'Asset Scene',
            'value': '{prefix}_{asset}_{element}.{version}.{ext}',
            'description': 'Uses the project prefix, asset, task, element, '
                           'user and version names',
        },
        common.idx(): {
            'name': 'Shot Scene',
            'value': '{prefix}_{seq}_{shot}_{mode}_{element}.{version}.{ext}',
            'description': 'Template name used save shot scene files',
        }
    },
    PublishConfig: {
        common.idx(): {
            'name': 'Publish: Asset Item',
            'value': '{server}/{job}/{root}/{asset}/publish/{prefix}_{asset}_{task}_{element}.{ext}',
            'description': 'Publish an asset scene',
        },
        common.idx(): {
            'name': 'Publish: Shot Item',
            'value': '{server}/{job}/{root}/{asset}/publish/{prefix}_{seq}_{shot}_{element}.{ext}',
            'description': 'Publish a shot scene',
        },
    },
    AssetFolderConfig: {
        common.idx(reset=True, start=0): {
            'name': CacheFolder,
            'value': CacheFolder,
            'description': 'Alembic, FBX, OBJ and other CG caches',
            'filter': SceneFormat | ImageFormat | MovieFormat | AudioFormat | CacheFormat,
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
        common.idx(): {
            'name': DataFolder,
            'value': DataFolder,
            'description': 'Temporary data files, or content generated by '
                           'applications',
            'filter': AllFormat,
        },
        common.idx(): {
            'name': ReferenceFolder,
            'value': ReferenceFolder,
            'description': 'References, for example, images, videos or sound files',
            'filter': ImageFormat | DocFormat | AudioFormat | MovieFormat,
        },
        common.idx(): {
            'name': RenderFolder,
            'value': RenderFolder,
            'description': 'Render layer outputs',
            'filter': ImageFormat | AudioFormat | MovieFormat,
        },
        common.idx(): {
            'name': SceneFolder,
            'value': SceneFolder,
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
        common.idx(): {
            'name': PublishFolder,
            'value': PublishFolder,
            'description': 'Asset publish files',
            'filter': SceneFormat | ImageFormat | MovieFormat | AudioFormat
        },
        common.idx(): {
            'name': CaptureFolder,
            'value': CaptureFolder,
            'description': 'Viewport captures and preview files',
            'filter': ImageFormat | MovieFormat | AudioFormat
        },
        common.idx(): {
            'name': TextureFolder,
            'value': TextureFolder,
            'description': '2D and 3D texture files',
            'filter': ImageFormat | MovieFormat | AudioFormat,
        },
        common.idx(): {
            'name': MiscFolder,
            'value': MiscFolder,
            'description': 'Miscellaneous asset files',
            'filter': AllFormat,
        }
    },
    TasksConfig: {
        common.idx(reset=True, start=0): {
            'name': 'Design',
            'value': 'design',
            'description': 'Design task',
            'icon': 'task_design',
        },
        common.idx(): {
            'name': 'Modeling',
            'value': 'model',
            'description': 'Modeling task',
            'icon': 'task_modeling',
        },
        common.idx(): {
            'name': 'Rigging',
            'value': 'rig',
            'description': 'Rigging task',
            'icon': 'task_rigging',
        },
        common.idx(): {
            'name': 'Animation',
            'value': 'anim',
            'description': 'Animation task',
            'icon': 'task_animation',
        },
        common.idx(): {
            'name': 'Layout',
            'value': 'layout',
            'description': 'Layout task',
            'icon': 'task_layout',
        },
        common.idx(): {
            'name': 'FX',
            'value': 'fx',
            'description': 'FX task',
            'icon': 'task_fx',
        },
        common.idx(): {
            'name': 'Lighting',
            'value': 'lighting',
            'description': 'Lighting task',
            'icon': 'task_lighting',
        },
        common.idx(): {
            'name': 'Rendering',
            'value': 'render',
            'description': 'Rendering task',
            'icon': 'task_rendering',
        },
        common.idx(): {
            'name': 'Compositing',
            'value': 'comp',
            'description': 'Compositing task',
            'icon': 'task_compositing',
        },
        common.idx(): {
            'name': 'Tracking',
            'value': 'tracking',
            'description': 'Tracking task',
            'icon': 'task_tracking',
        },
        common.idx(): {
            'name': 'Audio',
            'value': 'audio',
            'description': 'Audio task',
            'icon': 'task_audio',
        },
        common.idx(): {
            'name': 'Texture',
            'value': 'texture',
            'description': 'Texture task',
            'icon': 'task_texture',
        },
    },
    FFMpegTCConfig: {
        common.idx(reset=True, start=0): {
            'name': 'Shot',
            'value': '{job} | {sequence}-{shot}-{task}-{version} | {date} {user} | {in_frame}-{out_frame}',
            'description': 'Timecode to use for shots'
        },
        common.idx(): {
            'name': 'Asset',
            'value': '{job} | {asset}-{task}-{version} | {date} {user}',
            'description': 'Timecode to use for assets'
        },
        common.idx(): {
            'name': 'Date and user',
            'value': '{job} | {date} {user}',
            'description': 'Sparse timecode with the date and username'
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


def get_folder(token, server=None, job=None, root=None, force=False):
    """Find the value an asset folder token based on
    the bookmark item's token configuration.

    Returns:
        str: The current folder value.

    """
    if not all((server, job, root)):
        server = common.active('server')
        job = common.active('job')
        root = common.active('root')

    if not all((server, job, root)):
        raise RuntimeError('No active bookmark item found.')

    config = get(server, job, root)
    v = config.get_asset_folder(token, force=force)
    return v if v else token


def get_subfolder(token, name):
    """Find the value an asset subfolder based on the bookmark item's token
    configuration.

    Args:
        token (str): Asset folder token, for example, `tokens.CacheFolder`.
        name (str): Sub-folder token.

    Returns:
        str: The value of the current asset subfolder.

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
    """Find all asset subfolder values based on the bookmark item's token configuration.

    Args:
        token (str): Asset folder token, for example, `tokens.CacheFolder`.

    Returns:
        list: A list of current asset subfolder values.

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
        token (str): A token, for example, `tokens.SceneFormat`.

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

    As token config data might be used in performance-sensitive sections,
    the instance is shutdownd until :meth:`data` is called. This will load
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
            db = database.get(self.server, self.job, self.root)
            v = db.value(
                db.source(),
                'tokens',
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
            log.error(__name__, 'Failed to get token config from the database.')
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

        db = database.get(self.server, self.job, self.root)
        db.set_value(
            db.source(),
            'tokens',
            data,
            database.BookmarkTable
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
            log.error(__name__, 'Failed to convert data to JSON.')
            raise

        with open(file_info.filePath(), 'w') as f:
            f.write(json_data)
            log.info(__name__, f'Asset folder configuration saved to {file_info.filePath()}')

    def get_description(self, token, force=False):
        """Utility method used to get the description of a token.

        Args:
            token (str): A file-format or a folder name, for example, 'anim'.
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
            if v['flag'] == 0:
                v['flag'] = AllFormat

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
        """Returns the value of an asset subfolder based on the current token config
        values.

        Args:
            token (str): An asset folder name (not value!),
                for example`config.ExportFolder`.
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
        """Returns the value of an asset subfolder based on the current token config
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
