# -*- coding: utf-8 -*-
"""The asset config module allows basic folder and file-type definitions of asset items.

This information can be used to suggest default paths in DCCs (e.g. what the default scene folder is
called), to filter file-types when browsing task folders (e.g. hide cache files when browsing the `scenes`
folder), and to define the token values for generating templated file names (see
:func:`common.asset_config.asset_config.AssetConfig.expand_tokens()`).

The default values are stored in `asset_config.DEFAULT_ASSET_CONFIG` but each bookmark item can be
configured independently using the `asset_config.asset_config_editor` widget. The custom configuration
values are stored in the bookmark's database using `ASSET_CONFIG_KEY` column as encoded JSON data.

The module is backed by a cache. Use `asset_config.get(server, job, root)` to retrieve asset_config
instances.


Example:

    code-block:: python

        config = asset_config.get(server, job, root)
        config.set_data(
            {
                'custom_data': {
                    'value': 'hello_world',
                    'description': 'A test description to say hi.'
                }
            }
        )
        data = config.data()
        config.get_description('geo')
        config.dump_json('C:/temp/data.json')

        s = asset_info.expand_tokens(
            '{asset_root}/{scene}/{prefix}_{asset}_{task}_{user}_{version}.{ext}', ext='exr')

"""
import collections
import getpass
import json
import re
import socket
import string

import OpenImageIO
from PySide2 import QtCore

from .. import common
from .. import database
from .. import log

ASSET_CONFIG_KEY = 'asset_config'

FileFormatConfig = 'FileFormatConfig'
FileNameConfig = 'FileNameConfig'
AssetFolderConfig = 'AssetFolderConfig'

NoFormat = 0
SceneFormat = 0b100000
ImageFormat = 0b1000000
CacheFormat = 0b10000000
MiscFormat = 0b100000000
AllFormat = SceneFormat | ImageFormat | CacheFormat | MiscFormat

__INSTANCES = {}

INVALID_TOKEN = '{invalid_token}'

SceneDir = 'scene'
ExportDir = 'export'
DataDir = 'data'
ReferenceDir = 'reference'
RenderDir = 'render'


def _sort(s):
    return ', '.join(sorted(re.findall(r"[\w']+", s)))


def _get_key(*args):
    return '/'.join(args)


def get(server, job, root, force=False):
    """Returns an AssetConfig instance associated with the current bookmark.

    Args:
        server (type): Description of parameter `server`.
        job (type): Description of parameter `job`.
        root (type): Description of parameter `root`.

    Returns:
        type: Description of returned object.

    """
    for arg in (server, job, root):
        common.check_type(arg, str)

    key = _get_key(server, job, root)
    global __INSTANCES
    if key in __INSTANCES:
        if force:
            __INSTANCES[key].data(force=True)
        return __INSTANCES[key]

    try:
        # Fetch the currently stored data from the database
        v = AssetConfig(server, job, root)
        v.data(force=True)

        __INSTANCES[key] = v
        return __INSTANCES[key]
    except:
        __INSTANCES[key] = None
        if key in __INSTANCES:
            del __INSTANCES[key]
        raise


DEFAULT_ASSET_CONFIG = {
    FileFormatConfig: {
        0: {
            'name': 'Scene Formats',
            'flag': SceneFormat,
            'value': _sort(
                'aep, ai, eps, fla, ppj, prproj, psb, psd, psq, xfl, c4d, hud, hip, hiplc, hipnc, ma, mb, nk, nk~,spm, mocha, rv'),
            'description': 'Scene file formats'
        },
        1: {
            'name': 'Image Formats',
            'flag': ImageFormat,
            'value': _sort(OpenImageIO.get_string_attribute('extension_list')),
            'description': 'Image formats understood by OpenImageIO'
        },
        2: {
            'name': 'Cache Formats',
            'flag': CacheFormat,
            'value': _sort('abc, ass, bgeo, fbx, geo, ifd, obj, rs, sc, sim, vdb, usd, usda, usdc, usdz'),
            'description': 'CG cache formats'
        },
        3: {
            'name': 'Miscellaneous Formats',
            'flag': MiscFormat,
            'value': _sort('txt, pdf, zip, rar, exe, app, m4v, m4a, mov, mp4'),
            'description': 'Miscellaneous file formats'
        },
    },
    FileNameConfig: {
        0: {
            'name': 'Default',
            'value': '{prefix}_{asset}_{mode}_{element}_{user}_{version}.{ext}',
            'description': 'File name with prefix, asset, mode, user name and version number.'
        },
        1: {
            'name': 'Versioned Element with User Name',
            'value': '{element}_{user}_{version}.{ext}',
            'description': 'File name with element name, user name and version number.'
        },
        2: {
            'name': 'Versioned Element',
            'value': '{element}_{version}.{ext}',
            'description': 'File name with element name and version number.'
        },
        4: {
            'name': 'Element Only',
            'value': '{element}.{ext}',
            'description': 'File name with the element name.'
        },
        5: {
            'name': 'Custom 1',
            'value': 'MyCustomFile.ma',
            'description': 'A custom file name'
        },
        6: {
            'name': 'Custom 2',
            'value': 'MyCustomFile.ma',
            'description': 'A custom file name'
        }
    },
    AssetFolderConfig: {
        0: {
            'name': ExportDir,
            'value': ExportDir,
            'description': 'Alembic, FBX, OBJ and other CG caches',
            'filter': SceneFormat | ImageFormat | CacheFormat,
            'subfolders': {
                0: {
                    'name': 'abc',
                    'value': 'abc',
                    'description': 'Folder used to store Alembic caches.'
                },
                1: {
                    'name': 'obj',
                    'value': 'obj',
                    'description': 'Folder used to store Waveform OBJ files.'
                },
                2: {
                    'name': 'fbx',
                    'value': 'fbx',
                    'description': 'Folder used to store Autodesk FBX exports.'
                },
                3: {
                    'name': 'ass',
                    'value': 'ass',
                    'description': 'Folder used to store Arnold ASS exports.'
                },
                4: {
                    'name': 'usd',
                    'value': 'usd',
                    'description': 'Folder used to store USD files.'
                },
                5: {
                    'name': 'bgeo',
                    'value': 'bgeo',
                    'description': 'Folder used to store Houdini geometry caches.'
                }
            }
        },
        1: {
            'name': DataDir,
            'value': DataDir,
            'description': 'Folder used to store temporary cache files, or other generated content.',
            'filter': SceneFormat | ImageFormat | CacheFormat | MiscFormat
        },
        2: {
            'name': ReferenceDir,
            'value': ReferenceDir,
            'description': 'Folder used to store visual references, images and videos and sound files.',
            'filter': ImageFormat | MiscFormat
        },
        3: {
            'name': RenderDir,
            'value': RenderDir,
            'description': 'Folder used to store 2D and 3D renders.',
            'filter': ImageFormat,
        },
        4: {
            'name': SceneDir,
            'value': SceneDir,
            'description': 'Folder used to store scene files.',
            'filter': SceneFormat,
            'subfolders': {
                0: {
                    'name': 'anim',
                    'value': 'anim',
                    'description': 'Folder used to store 2D and 3D animation scene files.'
                },
                1: {
                    'name': 'fx',
                    'value': 'fx',
                    'description': 'Folder used to store FX scene files.'
                },
                2: {
                    'name': 'audio',
                    'value': 'audio',
                    'description': 'Folder used to store sound and music project files.'
                },
                3: {
                    'name': 'comp',
                    'value': 'comp',
                    'description': 'Folder used to store compositing project files.'
                },
                4: {
                    'name': 'block',
                    'value': 'block',
                    'description': 'Folder used to store layout, animatic and blocking scenes.'
                },
                5: {
                    'name': 'layout',
                    'value': 'layout',
                    'description': 'Folder used to store layout, animatic and blocking scenes.'
                },
                6: {
                    'name': 'tracking',
                    'value': 'tracking',
                    'description': 'Folder used to store motion tracking project files.'
                },
                7: {
                    'name': 'look',
                    'value': 'look',
                    'description': 'Folder used to store lighting & visual development scene files.'
                },
                8: {
                    'name': 'model',
                    'value': 'model',
                    'description': 'Folder used to store modeling & sculpting scene files.'
                },
                9: {
                    'name': 'rig',
                    'value': 'rig',
                    'description': 'Folder used to store rigging and other technical scene files.'
                },
                10: {
                    'name': 'render',
                    'value': 'render',
                    'description': 'Folder used to store render scene files.'
                }
            },
            5: {
                'name': 'final',
                'value': 'final',
                'description': 'Folder used to store final and approved render files.',
                'filter': ImageFormat
            },
            6: {
                'name': 'image',
                'value': 'image',
                'description': 'Folder used to store 2D and 3D texture files.',
                'filter': ImageFormat
            },
            7: {
                'name': 'other',
                'value': 'other',
                'description': 'Folder used to store miscellaneous files.',
                'filter': MiscFormat
            }
        }
    }
}


class AssetConfig(QtCore.QObject):
    """Used to load the current asset config values of a bookmark.

    The instance is uninitialised until `get_data()` is called first.

    """

    def __init__(self, server, job, root, asset=None, parent=None):
        super().__init__(parent=parent)

        self.server = server
        self.job = job
        self.root = root
        self.asset = asset

        self._initialised = False
        self._data = DEFAULT_ASSET_CONFIG.copy()

    def data(self, force=False):
        """Returns the current asset config values stored in the bookmark database.

        The results fetched from the bookmark database are cached to
        `self._data`. To re-querry the values from the bookmark database, an
        optional `force=True` can be passed.

        """
        if not force and self._initialised:
            return self._data

        try:
            db = database.get_db(self.server, self.job, self.root)
            v = db.value(
                db.source(),
                ASSET_CONFIG_KEY,
                database.BookmarkTable
            )
            # Let's do some very basic sanity check for the returned data
            if (
                    isinstance(v, dict) and
                    FileFormatConfig in v and
                    FileNameConfig in v and
                    AssetFolderConfig in v
            ):
                self._data = v
            return self._data
        except:
            log.error('Failed to get asset config from the database.')
            return self._data
        finally:
            self._initialised = True

    def set_data(self, data):
        """Saves a data dictionary to the bookmark database as an encoded
        JSON object.

        Args:
            data (dict):    A dictionary contaning new values.

        """
        common.check_type(data, dict)

        db = database.get_db(self.server, self.job, self.root)
        with db.connection():
            db.setValue(
                db.source(),
                ASSET_CONFIG_KEY,
                data,
                table=database.BookmarkTable
            )

        # Refetching the data from the database
        return self.data(force=True)

    def dump_json(self, destination, force=False):
        """Save the current configuration as a JSON file.

        """
        file_info = QtCore.QFileInfo(destination)
        if not file_info.dir().exists():
            raise OSError('{} does not exists. Specify a valid destination.'.format(
                file_info.dir().path()
            ))

        data = self.data(force=force)
        try:
            json_data = json.dumps(data, sort_keys=True, indent=4)
        except:
            log.error('Failed to convert data to JSON.')
            raise

        with open(file_info.filePath(), 'w') as f:
            f.write(json_data)
            log.success('Asset folder configuration saved to {}'.format(
                file_info.filePath()))

    def get_description(self, item, force=False):
        """Utility method for returning a description of an item.

        Args:
            item (str):    A value, eg. 'anim'.

        """
        data = self.data(force=force)

        common.check_type(item, str)

        for value in data.values():
            for v in value.values():
                if item.lower() == v['value'].lower():
                    return v['description']

                if 'subfolders' not in v:
                    continue

                for _v in v['subfolders'].values():
                    if item.lower() == _v['value'].lower():
                        return _v['description']
        return ''

    def expand_tokens(self, s, user=getpass.getuser(), version='v001', host=socket.gethostname(), task='anim',
                      ext=common.thumbnail_format, prefix=None, **_kwargs):
        """Expands all valid tokens in the given string, based on the current
        asset config values.

        Invalid tokens will be marked as `INVALID_TOKEN`.

        Args:
            s (str):    The string containing tokens to be expanded.

        """
        kwargs = self.get_tokens(
            user=user,
            version=version,
            host=host,
            task=task,
            ext=ext,
            prefix=prefix,
            **_kwargs
        )

        # To avoid KeyErrors when invalid tokens are passed we will replace
        # the wrong tokens with `INVALID_TOKEN`
        # via https://stackoverflow.com/questions/17215400/format-string-unused-named-arguments
        return string.Formatter().vformat(
            s,
            (),
            collections.defaultdict(lambda: INVALID_TOKEN, **kwargs)
        )

    def get_tokens(self, force=False, **kwargs):
        """Get token/value mapping for the format() method.

        """
        data = self.data(force=force)
        tokens = {}
        for k, v in data[AssetFolderConfig].items():
            tokens[v['name']] = v['value']

        tokens['server'] = self.server
        tokens['job'] = self.job
        tokens['root'] = self.root

        tokens['bookmark'] = f'{self.server}/{self.job}/{self.root}'

        for k, v in kwargs.items():
            tokens[k] = v

        def _get(k):
            if k not in kwargs or not kwargs[k]:
                v = db.value(db.source(), k, database.BookmarkTable)
                v = v if v else INVALID_TOKEN
                tokens[k] = v

        # We can also use some bookmark item properties as tokens.
        # Let's load the values from the database:
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
        return tokens

    def get_extensions(self, flag, force=False):
        """Returns a list of extensions associated with the given flag.

        Args:
            flag (int):     A format filter flag.

        Returns:
            tuple:           A tuple of file format extensions.

        """
        data = self.data(force=force)
        if FileFormatConfig not in data:
            raise KeyError('Invalid data, `FileFormatConfig` not found.')

        extensions = []
        for v in data[FileFormatConfig].values():
            if not (v['flag'] & flag):
                continue
            if not isinstance(v['value'], str):
                continue
            extensions += [f.strip() for f in v['value'].split(',')]
        return tuple(sorted(list(set(extensions))))

    def check_task(self, task, force=False):
        common.check_type(task, str)

        data = self.data(force=force)
        if AssetFolderConfig not in data:
            raise KeyError('{}/{}/{}')

        for v in data[AssetFolderConfig].values():
            if v['value'].lower() == task.lower():
                return True
        return False

    def get_task_extensions(self, task, force=False):
        """Returns a list of allowed extensions for the given task folder.

        Args:
            task (str): The name of a task folder.

        Returns:
            set: A set of file format extensions.

        """
        common.check_type(task, str)

        data = self.data(force=force)
        if AssetFolderConfig not in data:
            raise KeyError('{}/{}/{}')

        for v in data[AssetFolderConfig].values():
            if v['value'].lower() != task.lower():
                continue
            if 'filter' not in v:
                continue
            return set(self.get_extensions(v['filter']))
        return set()

    def get_asset_folder_name(self, k, force=False):
        """Return the name of an asset folder based on the current asset config
        values.

        """
        data = self.data(force=force)
        if not data:
            return None

        for v in data[AssetFolderConfig].values():
            if v['name'] == k:
                return v['value']
        return None

    def get_export_subdir(self, v, force=False):
        data = self.data(force=force)
        if not data:
            return v

        for _v in data[AssetFolderConfig].values():
            if _v['name'] == ExportDir:
                if 'subfolders' not in _v:
                    return None
                for v_ in _v['subfolders'].values():
                    if v_['name'] == v:
                        return v_['value']
        return v

    def get_export_dir(self):
        v = self.get_asset_folder_name(ExportDir)
        if not v:
            return '{}/{}/{}'
        return v
