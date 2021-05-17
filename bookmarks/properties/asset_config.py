# -*- coding: utf-8 -*-
"""`Asset config` describes the folder structure, and accepted file-types of
assets.

The default values are stored in `DEFAULT_ASSET_CONFIG` but each bookmark can be
configured independently using the `asset_config_editor` widget. The custom
configuration values are stored in the bookmark's database using `ASSET_CONFIG_KEY`
column as encoded JSON data.

The asset config values can be used as tokens for generating file names.
See `AssetConfig.expand_tokens()`.

To instances are backed by a cache and should be created using the `get(*arg)` method.
Example:

    code-block:: python

        asset_config = get(
            u'//gw-workstation/jobs',
            u'myjob',
            u'data/assets'
        )
        asset_config.set_data(
            {
                'custom_data': {
                    'value': u'hello_world',
                    'description': u'A test description to say hi.'
                }
            }
        )
        data = asset_config.data()
        asset_config.get_description(u'geo')
        asset_config.dump_json(u'C:/temp/data.json')

        s = asset_info.expand_tokens(u'{asset_root}/{scene}/{prefix}_{asset}_{task}_{user}_{version}.{ext}', ext='exr')

"""
import re
import getpass
import socket
import json
import string
import collections

from PySide2 import QtCore

import OpenImageIO

from .. import log
from .. import bookmark_db
from .. import images


ASSET_CONFIG_KEY = u'asset_config'

FileFormatConfig = u'FileFormatConfig'
FileNameConfig = u'FileNameConfig'
AssetFolderConfig = u'AssetFolderConfig'

NoFormat = 0
SceneFormat = 0b100000
ImageFormat = 0b1000000
CacheFormat = 0b10000000
MiscFormat = 0b100000000
AllFormat = SceneFormat | ImageFormat | CacheFormat | MiscFormat

__INSTANCES = {}

INVALID_TOKEN = u'{invalid_token}'


def _sort(s):
    return u', '.join(sorted(re.findall(r"[\w']+", s)))


def _get_key(*args):
    return u'/'.join(args)


def get(server, job, root):
    """Returns an AssetConfig instance associated with the current bookmark.

    Args:
        server (type): Description of parameter `server`.
        job (type): Description of parameter `job`.
        root (type): Description of parameter `root`.

    Returns:
        type: Description of returned object.

    """
    for arg in (server, job, root):
        if isinstance(arg, unicode):
            continue
        raise TypeError(
            u'Invalid type, expected <type \'unicode\'>, got {}'.format(type(arg)))

    key = _get_key(server, job, root)
    global __INSTANCES
    if key in __INSTANCES:
        return __INSTANCES[key]

    try:
        asset_config = AssetConfig(server, job, root)
        # Fetch the currently stored data from the database
        asset_config.data(force=True)
        __INSTANCES[key] = asset_config
        return __INSTANCES[key]
    except:
        __INSTANCES[key] = None
        if key in __INSTANCES:
            del __INSTANCES[key]
        raise


DEFAULT_ASSET_CONFIG = {
    FileFormatConfig: {
        0: {
            'name': u'Scene Formats',
            'flag': SceneFormat,
            'value': _sort(u'aep, ai, eps, fla, ppj, prproj, psb, psd, psq, xfl, c4d, hud, hip, hiplc, hipnc, ma, mb, nk, nk~,spm, mocha, rv'),
            'description': 'Scene file formats'
        },
        1: {
            'name': u'Image Formats',
            'flag': ImageFormat,
            'value': _sort(OpenImageIO.get_string_attribute(u'extension_list')),
            'description': 'Image formats understood by OpenImageIO'
        },
        2: {
            'name': u'Cache Formats',
            'flag': CacheFormat,
            'value': _sort(u'abc, ass, bgeo, fbx, geo, ifd, obj, rs, sc, sim, vdb, usd, usda, usdc, usdz'),
            'description': 'CG cache formats'
        },
        3: {
            'name': 'Miscellaneous Formats',
            'flag': MiscFormat,
            'value': _sort(u'txt, pdf, zip, rar, exe, app, m4v, m4a, mov, mp4'),
            'description': 'Miscellaneous file formats'
        },
    },
    FileNameConfig: {
        0: {
            'name': u'Default',
            'value': u'{prefix}_{asset}_{mode}_{element}_{user}_{version}.{ext}',
            'description': 'File name with prefix, asset, mode, user name and version number.'
        },
        1: {
            'name': u'Versioned Element with User Name',
            'value': u'{element}_{user}_{version}.{ext}',
            'description': 'File name with element name, user name and version number.'
        },
        2: {
            'name': u'Versioned Element',
            'value': u'{element}_{version}.{ext}',
            'description': 'File name with element name and version number.'
        },
        4: {
            'name': u'Element Only',
            'value': u'{element}.{ext}',
            'description': 'File name with the element name.'
        },
        5: {
            'name': u'Custom 1',
            'value': u'MyCustomFile.ma',
            'description': 'A custom file name'
        },
        6: {
            'name': u'Custom 2',
            'value': u'MyCustomFile.ma',
            'description': 'A custom file name'
        }
    },
    AssetFolderConfig: {
        0: {
            'name': u'export',
            'value': 'export',
            'description': u'Alembic, FBX, OBJ and other CG caches',
            'filter': SceneFormat | ImageFormat | CacheFormat,
            'subfolders': {
                0: {
                    'name': u'abc',
                    'value': 'abc',
                    'description': u'Folder used to store Alembic caches.'
                },
                1: {
                    'name': u'obj',
                    'value': 'obj',
                    'description': u'Folder used to store Waveform OBJ files.'
                },
                2: {
                    'name': u'fbx',
                    'value': 'fbx',
                    'description': u'Folder used to store Autodesk FBX exports.'
                },
                3: {
                    'name': u'ass',
                    'value': 'ass',
                    'description': u'Folder used to store Arnold ASS exports.'
                },
                4: {
                    'name': 'usd',
                    'value': 'usd',
                    'description': u'Folder used to store USD files.'
                },
                5: {
                    'name': 'geo',
                    'value': 'geo',
                    'description': u'Folder used to store Houdini geometry caches.'
                },
                6: {
                    'name': 'sc',
                    'value': 'sc',
                    'description': 'Folder used to store Houdini geometry caches.'
                }
            }
        },
        1: {
            'name': u'data',
            'value': u'data',
            'description': u'Folder used to store temporary cache files, or other generated content.',
            'filter': SceneFormat | ImageFormat | CacheFormat | MiscFormat
        },
        2: {
            'name': 'reference',
            'value': 'reference',
            'description': u'Folder used to store visual references, images and videos and sound files.',
            'filter': ImageFormat | MiscFormat
        },
        3: {
            'name': 'render',
            'value': 'render',
            'description': u'Folder used to store 2D and 3D renders.',
            'filter': ImageFormat,
        },
        4: {
            'name': 'scene',
            'value': 'scene',
            'description': u'Folder used to store scene files.',
            'filter': SceneFormat,
            'subfolders': {
                0: {
                    'name': 'anim',
                    'value': 'anim',
                    'description': u'Folder used to store 2D and 3D animation scene files.'
                },
                1: {
                    'name': 'fx',
                    'value': 'fx',
                    'description': u'Folder used to store FX scene files.'
                },
                2: {
                    'name': 'audio',
                    'value': 'audio',
                    'description': u'Folder used to store sound and music project files.'
                },
                3: {
                    'name': 'comp',
                    'value': 'comp',
                    'description': u'Folder used to store compositing project files.'
                },
                4: {
                    'name': 'block',
                    'value': 'block',
                    'description': u'Folder used to store layout, animatic and blocking scenes.'
                },
                5: {
                    'name': 'layout',
                    'value': 'layout',
                    'description': u'Folder used to store layout, animatic and blocking scenes.'
                },
                6: {
                    'name': 'tracking',
                    'value': 'tracking',
                    'description': u'Folder used to store motion tracking project files.'
                },
                7: {
                    'name': 'look',
                    'value': 'look',
                    'description': u'Folder used to store lighting & visual development scene files.'
                },
                8: {
                    'name': 'model',
                    'value': 'model',
                    'description': u'Folder used to store modeling & sculpting scene files.'
                },
                9: {
                    'name': 'rig',
                    'value': 'rig',
                    'description': u'Folder used to store rigging and other technical scene files.'
                },
                10: {
                    'name': 'render',
                    'value': 'render',
                    'description': u'Folder used to store render scene files.'
                }
            },
            5: {
                'name': 'final',
                'value': 'final',
                'description': u'Folder used to store final and approved render files.',
                'filter': ImageFormat
            },
            6: {
                'name': 'image',
                'value': 'image',
                'description': u'Folder used to store 2D and 3D texture files.',
                'filter': ImageFormat
            },
            7: {
                'name': 'other',
                'value': 'other',
                'description': u'Folder used to store miscellaneous files.',
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
        super(AssetConfig, self).__init__(parent=parent)

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
            db = bookmark_db.get_db(self.server, self.job, self.root)
            v = db.value(
                db.source(),
                ASSET_CONFIG_KEY,
                table=bookmark_db.BookmarkTable
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
            log.error(u'Failed to get asset config from the database.')
            return self._data
        finally:
            self._initialised = True

    def set_data(self, data):
        """Saves a data dictionary to the bookmark database as an encoded
        JSON object.

        Args:
            data (dict):    A dictionary contaning new values.

        """
        if not isinstance(data, dict):
            raise TypeError(
                u'Invalid type, expected <type \'dict\'>, got {}'.format(type(data)))

        db = bookmark_db.get_db(self.server, self.job, self.root)
        with db.connection():
            db.setValue(
                db.source(),
                ASSET_CONFIG_KEY,
                data,
                table=bookmark_db.BookmarkTable
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
            log.error(u'Failed to convert data to JSON.')
            raise

        with open(file_info.filePath(), 'w') as f:
            f.write(json_data)
            log.success(u'Asset folder configuration saved to {}'.format(
                file_info.filePath()))

    def get_description(self, item, force=False):
        """Utility method for returning a description of an item.

        Args:
            item (unicode):    A value, eg. 'anim'.

        """
        data = self.data(force=force)

        if not isinstance(item, (str, unicode)):
            raise TypeError('value must be str or unicode.')

        for value in data.itervalues():
            for v in value.itervalues():
                if item.lower() == v['value'].lower():
                    return v['description']

                if 'subfolders' not in v:
                    continue

                for _v in v['subfolders'].itervalues():
                    if item.lower() == _v['value'].lower():
                        return _v['description']
        return u''

    def expand_tokens(self, s, user=getpass.getuser(), version=u'v001', host=socket.gethostname(), task=u'anim', ext=images.THUMBNAIL_FORMAT, prefix=None, **_kwargs):
        """Expands all valid tokens in the given string, based on the current
        asset config values.

        Invalid tokens will be marked as `INVALID_TOKEN`.

        Args:
            s (unicode):    The string containing tokens to be expanded.

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
        for k, v in data[AssetFolderConfig].iteritems():
            tokens[v['name']] = v['value']

        tokens['server'] = self.server
        tokens['job'] = self.job
        tokens['root'] = self.root

        tokens['bookmark'] = u'{}/{}/{}'.format(
            self.server,
            self.job,
            self.root
        )

        for k, v in kwargs.iteritems():
            tokens[k] = v

        def _get(k):
            if k not in kwargs or not kwargs[k]:
                v = db.value(db.source(), k, table=bookmark_db.BookmarkTable)
                v = v if v else INVALID_TOKEN
                tokens[k] = v

        # We can also use some of the bookmark properties as tokens.
        # Let's load the values from the database:
        db = bookmark_db.get_db(self.server, self.job, self.root)
        _get('width')
        _get('height')
        _get('framerate')
        _get('prefix')
        _get('startframe')
        _get('duration')

        # The asset root token will only be available when the asset is manually
        # specified
        if 'asset' in kwargs and kwargs['asset']:
            tokens['asset_root'] = u'{}/{}/{}/{}'.format(
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
            raise KeyError(u'Key section missing from data.')

        extensions = []
        for v in data[FileFormatConfig].itervalues():
            if not (v['flag'] & flag):
                continue
            value = v[u'value']
            if not isinstance(value, (str, unicode)):
                continue
            extensions += [f.strip() for f in value.split(u',')]
        return tuple(sorted(list(set(extensions))))

    def check_task(self, task, force=False):
        if not isinstance(task, (str, unicode)):
            raise TypeError(
                u'Expected <type \'unicode\'>, got {}'.format(type(task)))

        data = self.data(force=force)
        if AssetFolderConfig not in data:
            raise KeyError(u'Data is missing a required key.')

        for v in data[AssetFolderConfig].itervalues():
            if v['value'].lower() == task.lower():
                return True
        return False

    def get_task_extensions(self, task, force=False):
        """Returns a list of allowed extensions for the given task folder.

        Args:
            task (unicode): The name of a task folder.

        Returns:
            set: A set of file format extensions.

        """
        if not isinstance(task, (str, unicode)):
            raise TypeError(
                u'Expected <type \'unicode\'>, got {}'.format(type(task)))

        data = self.data(force=force)
        if AssetFolderConfig not in data:
            raise KeyError(u'Data is missing a required key.')

        for v in data[AssetFolderConfig].itervalues():
            if v['value'].lower() != task.lower():
                continue
            if 'filter' not in v:
                continue
            return set(self.get_extensions(v['filter']))
        return set()
