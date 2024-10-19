import copy

from .lib import *
from .. import common, log

try:
    import OpenImageIO

    oiio_extensions = OpenImageIO.get_string_attribute('extension_list')
except ImportError:
    log.error('OpenImageIO not found. Cannot get extensions list.')
    oiio_extensions = ''

MOVIE_FORMATS = {
    'mov',
    'mp4',
    'm4v',
    'avi'
}

DOCUMENT_FORMATS = {
    'pdf',
    'doc',
    'docx',
    'xls',
    'xlsx',
    'ppt',
    'pptx',
    'txt'
}

AUDIO_FORMATS = {
    'wav',
    'mp3',
    'ogg',
    'flac',
    'aac',
    'm4a'
}

SCRIPT_FORMATS = {
    'py',
    'mel',
    'js',
    'vbs',
    'sh',
    'bat',
    'json',
    'xml',
    'yaml',
    'yml'
    'ini',
    'cfg',
    'conf',
    'config',
    'preset',
    'vex',
    'vfl',
    'vflib',
    'vexlib'
}

MISC_FORMATS = {
    'zip',
    'rar',
    '7z',
    'tar',
    'gz',
    'bz2',
    'xz',
    'lzma',
    'zst',
    'lz4',
}

default_file_format_config = {
    common.idx(reset=True, start=0): {
        'name': 'Scene Formats',
        'flag': Format.SceneFormat,
        'value': ', '.join(sorted(common.get_all_known_dcc_formats())),
        'description': 'Scene file formats'
    },
    common.idx(): {
        'name': 'Image Formats',
        'flag': Format.ImageFormat,
        'value': common.sort_words(oiio_extensions),
        'description': 'Image file formats'
    },
    common.idx(): {
        'name': 'Cache Formats',
        'flag': Format.CacheFormat,
        'value': ', '.join(tuple(sorted(common.CACHE_FORMATS))),
        'description': 'CG cache formats'
    },
    common.idx(): {
        'name': 'Movie Formats',
        'flag': Format.MovieFormat,
        'value': ', '.join(tuple(sorted(MOVIE_FORMATS))),
        'description': 'Movie file formats'
    },
    common.idx(): {
        'name': 'Audio Formats',
        'flag': Format.AudioFormat,
        'value': ', '.join(tuple(sorted(MOVIE_FORMATS))),
        'description': 'Audio file formats'
    },
    common.idx(): {
        'name': 'Document Formats',
        'flag': Format.DocFormat,
        'value': ', '.join(tuple(sorted(DOCUMENT_FORMATS))),
        'description': 'Document formats'
    },
    common.idx(): {
        'name': 'Script Formats',
        'flag': Format.ScriptFormat,
        'value': ', '.join(tuple(sorted(SCRIPT_FORMATS))),
        'description': 'Script file formats'
    },
    common.idx(): {
        'name': 'Miscellaneous Formats',
        'flag': Format.MiscFormat,
        'value': ', '.join(tuple(sorted(MISC_FORMATS))),
        'description': 'Miscellaneous file formats'
    },
}

default_scene_name_config = {
    common.idx(reset=True, start=0): {
        'name': 'Asset Scene',
        'value': '{prefix}_{asset}_{element}.{version}.{ext}',
        'description': 'Uses the project prefix, asset, task, element, '
                       'user and version names',
    },
    common.idx(): {
        'name': 'Shot Scene',
        'value': '{prefix}_{sequence}_{shot}_{mode}_{element}.{version}.{ext}',
        'description': 'Template name used save shot scene files',
    }
}

default_publish_config = {
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
}

default_task_config = {
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
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'Rigging',
        'value': 'rig',
        'description': 'Rigging task',
        'icon': 'task_rigging',
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'Animation',
        'value': 'anim',
        'description': 'Animation task',
        'icon': 'task_animation',
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'Layout',
        'value': 'layout',
        'description': 'Layout task',
        'icon': 'task_layout',
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'FX',
        'value': 'fx',
        'description': 'FX task',
        'icon': 'task_fx',
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'Lighting',
        'value': 'lighting',
        'description': 'Lighting task',
        'icon': 'task_lighting',
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'Rendering',
        'value': 'render',
        'description': 'Rendering task',
        'icon': 'task_rendering',
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'Compositing',
        'value': 'comp',
        'description': 'Compositing task',
        'icon': 'task_compositing',
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'Tracking',
        'value': 'tracking',
        'description': 'Tracking task',
        'icon': 'task_tracking',
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'Audio',
        'value': 'audio',
        'description': 'Audio task',
        'icon': 'task_audio',
        'status': copy.deepcopy(default_task_status)
    },
    common.idx(): {
        'name': 'Texture',
        'value': 'texture',
        'description': 'Texture task',
        'icon': 'task_texture',
        'status': copy.deepcopy(default_task_status)
    },
}

default_asset_folder_config = {
    common.idx(reset=True, start=0): {
        'name': AssetFolder.CacheFolder,
        'value': AssetFolder.CacheFolder,
        'description': 'Alembic, FBX, OBJ and other CG caches',
        'filter': Format.SceneFormat | Format.ImageFormat | Format.MovieFormat | Format.AudioFormat | Format.CacheFormat,
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
        'name': AssetFolder.DataFolder,
        'value': AssetFolder.DataFolder,
        'description': 'Temporary data files, or content generated by '
                       'applications',
        'filter': Format.AllFormat,
    },
    common.idx(): {
        'name': AssetFolder.ReferenceFolder,
        'value': AssetFolder.ReferenceFolder,
        'description': 'References, for example, images, videos or sound files',
        'filter': Format.ImageFormat | Format.DocFormat | Format.AudioFormat | Format.MovieFormat,
    },
    common.idx(): {
        'name': AssetFolder.RenderFolder,
        'value': AssetFolder.RenderFolder,
        'description': 'Render layer outputs',
        'filter': Format.ImageFormat | Format.AudioFormat | Format.MovieFormat,
        'subfolders': {
            1: {
                'name': 'passes',
                'value': 'passes',
                'description': 'Render passes'
            },
            2: {
                'name': 'comp',
                'value': 'comp',
                'description': 'Compositing files'
            },
            3: {
                'name': 'preview',
                'value': 'preview',
                'description': 'Preview render outputs'
            },
            4: {
                'name': 'tmp',
                'value': 'tmp',
                'description': 'Temporary render files'
            }
        }
    },
    common.idx(): {
        'name': AssetFolder.SceneFolder,
        'value': AssetFolder.SceneFolder,
        'description': 'Project and scene files',
        'filter': Format.SceneFormat,
        'subfolders': copy.deepcopy(default_task_config)
    },
    common.idx(): {
        'name': AssetFolder.PublishFolder,
        'value': AssetFolder.PublishFolder,
        'description': 'Asset publish files',
        'filter': Format.SceneFormat | Format.ImageFormat | Format.MovieFormat | Format.AudioFormat
    },
    common.idx(): {
        'name': AssetFolder.CaptureFolder,
        'value': AssetFolder.CaptureFolder,
        'description': 'Viewport captures and preview files',
        'filter': Format.ImageFormat | Format.MovieFormat | Format.AudioFormat
    },
    common.idx(): {
        'name': AssetFolder.TextureFolder,
        'value': AssetFolder.TextureFolder,
        'description': '2D and 3D texture files',
        'filter': Format.ImageFormat | Format.MovieFormat | Format.AudioFormat,
    }
}

default_burnin_config = {
    common.idx(reset=True, start=0): {
        'name': 'Shot',
        'value': '{job} | {sequence}-{shot}-{task}-{version} | {date} {user} | {cut_in}-{cut_out}',
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
        'description': 'Sparse timecode with the date and username only'
    }
}
