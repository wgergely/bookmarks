# -*- coding: utf-8 -*-
"""The module contains interface used to get and modify a bookmark item's token
values.

The default values are stored in :attr:`.DEFAULT_TOKEN_CONFIG` but each
bookmark item can be configured independently using the
:mod:`tokens.tokens_editor` widget. The custom configuration values are
stored in the bookmark's database using `TOKENS_DB_KEY` column as encoded JSON
data. 

Use :func:`.get` to retrieve token config controller instances.

.. code-block:: python

    tokens_config = tokens.get(server, job, root)
    data = tokens_config.data()

    # Try to find a description for an item named 'geo'
    v = tokens_config.get_description('geo')

    # Expands all tokens using values set in the bookmark database
    s = tokens_config.expand_tokens(
        '{asset_root}/{scene}/{prefix}_{asset}_{task}_{user}_{version}.{ext}',
        ext='exr'
    )

Attributes:
    DEFAULT_TOKEN_CONFIG (dict): The default token configuration structure.
    TOKENS_DB_KEY (str): The database column name used to store the token
        configuration data.
    invalid_token (str): The default string to mark a token invalid.

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

TOKENS_DB_KEY = 'tokens'

FileFormatConfig = 'FileFormatConfig'
FileNameConfig = 'FileNameConfig'
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

invalid_token = '{invalid_token}'

SceneDir = 'scene'
ExportDir = 'export'
DataDir = 'data'
ReferenceDir = 'reference'
RenderDir = 'render'

DEFAULT_TOKEN_CONFIG = {
    FileFormatConfig: {
        0: {
            'name': 'Scene Formats',
            'flag': SceneFormat,
            'value': common.sort_words(
                'aep, ai, eps, fla, ppj, prproj, psb, psd, psq, xfl, c4d, hud, '
                'hip, hiplc, hipnc, ma, mb, nk, nk~,spm, mocha, rv, tvpp'
            ),
            'description': 'Scene file formats'
        },
        1: {
            'name': 'Image Formats',
            'flag': ImageFormat,
            'value': common.sort_words(OpenImageIO.get_string_attribute('extension_list')),
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
                'doc, docx, pdf, ppt, pptx, rtf'
            ),
            'description': 'Audio file formats'
        },
        6: {
            'name': 'Script Formats',
            'flag': ScriptFormat,
            'value': common.sort_words(
                'py, jsx, js, vex, mel, env, bat, bash'
            ),
            'description': 'Audio file formats'
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
            'name': 'Default File Name',
            'value': '{prefix}_{asset}_{mode}_{element}_{user}_{version}.{ext}',
            'description': 'File name with prefix, asset, mode, user name and '
                           'version number.'
        },
        1: {
            'name': 'Versioned with element and user name',
            'value': '{element}_{user}_{version}.{ext}',
            'description': 'File name with element name, user name and version '
                           'number.'
        },
        2: {
            'name': 'Versioned with element',
            'value': '{element}_{version}.{ext}',
            'description': 'File name with element name and version number.'
        },
        3: {
            'name': 'Element name only',
            'value': '{element}.{ext}',
            'description': 'File name with the element name.'
        },
        5: {
            'name': 'Custom name #1',
            'value': 'MyCustomFile.ma',
            'description': 'A custom file name'
        },
        6: {
            'name': 'Custom name #2',
            'value': 'MyCustomFile.ma',
            'description': 'A custom file name'
        }
    },
    AssetFolderConfig: {
        0: {
            'name': ExportDir,
            'value': ExportDir,
            'description': 'Alembic, FBX, OBJ and other CG caches',
            'filter': SceneFormat | ImageFormat | MovieFormat | AudioFormat | CacheFormat,
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
            'description': 'Folder used to store temporary cache files, or other '
                           'generated content.',
            'filter': AllFormat
        },
        2: {
            'name': ReferenceDir,
            'value': ReferenceDir,
            'description': 'Folder used to store visual references, images and '
                           'videos and sound files.',
            'filter': ImageFormat | DocFormat | AudioFormat | MovieFormat
        },
        3: {
            'name': RenderDir,
            'value': RenderDir,
            'description': 'Folder used to store 2D and 3D renders.',
            'filter': ImageFormat | AudioFormat | MovieFormat,
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
                    'description': 'Folder used to store 2D and 3D animation scene'
                                   ' files.'
                },
                1: {
                    'name': 'fx',
                    'value': 'fx',
                    'description': 'Folder used to store FX scene files.'
                },
                2: {
                    'name': 'audio',
                    'value': 'audio',
                    'description': 'Folder used to store sound and music project '
                                   'files.'
                },
                3: {
                    'name': 'comp',
                    'value': 'comp',
                    'description': 'Folder used to store compositing project files.'
                },
                4: {
                    'name': 'block',
                    'value': 'block',
                    'description': 'Folder used to store layout, animatic and '
                                   'blocking scenes.'
                },
                5: {
                    'name': 'layout',
                    'value': 'layout',
                    'description': 'Folder used to store layout, animatic and '
                                   'blocking scenes.'
                },
                6: {
                    'name': 'tracking',
                    'value': 'tracking',
                    'description': 'Folder used to store motion tracking project '
                                   'files.'
                },
                7: {
                    'name': 'look',
                    'value': 'look',
                    'description': 'Folder used to store lighting & visual '
                                   'development scene files.'
                },
                8: {
                    'name': 'model',
                    'value': 'model',
                    'description': 'Folder used to store modeling & sculpting '
                                   'scene files.'
                },
                9: {
                    'name': 'rig',
                    'value': 'rig',
                    'description': 'Folder used to store rigging and other '
                                   'technical scene files.'
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
                'description': 'Folder used to store final and approved render '
                               'files.',
                'filter': ImageFormat | MovieFormat | AudioFormat
            },
            6: {
                'name': 'image',
                'value': 'image',
                'description': 'Folder used to store 2D and 3D texture files.',
                'filter': ImageFormat | MovieFormat | AudioFormat
            },
            7: {
                'name': 'other',
                'value': 'other',
                'description': 'Folder used to store miscellaneous files.',
                'filter': AllFormat
            }
        }
    }
}


def get(server, job, root, force=False):
    """Returns the :class:`.TokenConfig` of the specified
    bookmark item.

    Args:
        server (str): Server path segment.
        job (str): Job path segment.
        root (str): Root path segment.
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
    except:
        common.token_configs[key] = None
        if key in common.token_configs:
            del common.token_configs[key]
        raise


class TokenConfig(QtCore.QObject):
    """The class is used to interface with token configuration stored in the
    bookmark item's database.

    As token config data might be used in performance sensitive sections,
    the instance is uninitialized until :meth:`data` is called. This will load
    values from the database and cache it internally. Data won't be updated
    until :meth:`.data(force=True)` is called.

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
            log.error('Failed to get token config from the database.')
            return self._data
        finally:
            self._initialized = True

    def set_data(self, data):
        """Saves a data dictionary to the bookmark database as an encoded
        JSON object.

        Args:
            data (dict):  The token config data to save.

        """
        common.check_type(data, dict)

        db = database.get_db(self.server, self.job, self.root)
        with db.connection():
            db.setValue(
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
        except:
            log.error('Failed to convert data to JSON.')
            raise

        with open(file_info.filePath(), 'w') as f:
            f.write(json_data)
            log.success(
                'Asset folder configuration saved to {}'.format(
                    file_info.filePath()
                )
            )

    def get_description(self, item, force=False):
        """Utility method used to get the description of an item.

        Args:
            item (str):    A file-format or a folder name, e.g. 'anim'.
            force (bool, optional): Force retrieve tokens from the database.

        Returns:
            str: The description of the item.

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

    def expand_tokens(
            self, s, user=getpass.getuser(), version='v001',
            host=socket.gethostname(), task='anim',
            ext=common.thumbnail_format, prefix=None, **_kwargs
    ):
        """Expands all valid tokens of the given string, based on the current
        database values.

        Invalid tokens will be marked :attr:`.invalid_token`.

        Args:
            s (str):    The string containing tokens to be expanded.
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
            host=host,
            task=task,
            ext=ext,
            prefix=prefix,
            **_kwargs
        )

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
                v = v if v else invalid_token
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
            raise KeyError('Invalid token config data.')

        for v in data[AssetFolderConfig].values():
            if v['value'].lower() != task.lower():
                continue
            if 'filter' not in v:
                continue
            return set(self.get_extensions(v['filter']))
        return set()

    def get_asset_folder_name(self, k, force=False):
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
