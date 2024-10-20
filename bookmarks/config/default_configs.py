import copy

from .lib import *
from .. import common, log

__all__ = [
    'default_file_format_config',
    'default_scene_name_config',
    'default_publish_config',
    'default_task_config',
    'default_asset_folder_config',
    'default_burnin_config'
]

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

default_task_state = {
    State.NotStarted: {
        'icon': 'state_not_started',
        'description': 'The task has not been started yet',
        'color': common.Color.SecondaryText(),
        'enabled': True
    },
    State.InProgress: {
        'icon': 'state_in_progress',
        'description': 'The task is currently being worked on',
        'color': common.Color.Blue(),
        'enabled': True
    },
    State.PendingReview: {
        'icon': 'state_pending_review',
        'description': 'The task is completed and awaiting review',
        'color': common.Color.Yellow(),
        'enabled': True
    },
    State.Priority: {
        'icon': 'state_priority',
        'description': 'The task has been marked as high priority',
        'color': common.Color.Red(),
        'enabled': True
    },
    State.Approved: {
        'icon': 'state_approved',
        'description': 'The task has been reviewed and approved',
        'color': common.Color.Green(),

    },
    State.Completed: {
        'icon': 'state_completed',
        'description': 'The task is finished and no further action is required',
        'color': common.Color.Green()
    },
    State.OnHold: {
        'icon': 'state_on_hold',
        'description': 'The task is temporarily paused',
        'color': common.Color.Yellow()
    },
    State.Omitted: {
        'icon': 'state_omitted',
        'description': 'The task is skipped or not required',
        'color': common.Color.VeryDarkBackground()
    },
}

default_task_config = {
    common.idx(reset=True, start=0): {
        'name': 'Design',
        'value': 'design',
        'color': common.color_manager.get_color('design', qcolor=True, base_hue=180),
        'description': 'Design concepts, visual styles, and visual plans.',
        'icon': 'task_design',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Storyboarding',
        'value': 'storyboard',
        'color': common.color_manager.get_color('storyboard', qcolor=True, base_hue=180),
        'description': 'Create storyboards and animatics to visualize narrative flow and key scenes.',
        'icon': 'task_storyboarding',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Concept Art',
        'value': 'concept',
        'color': common.color_manager.get_color('concept', qcolor=True, base_hue=180),
        'description': 'Develop concept artworks depicting backgrounds, characters, and props.',
        'icon': 'task_concept_art',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Previz',
        'value': 'previz',
        'color': common.color_manager.get_color('previz', qcolor=True, base_hue=180),
        'description': 'Create preliminary visualizations and block-o-matics to plan and refine scenes.',
        'icon': 'task_previs',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Motion Capture',
        'value': 'mocap',
        'color': common.color_manager.get_color('mocap', qcolor=True, base_hue=30),
        'description': 'Capture and process motion data for realistic character animations.',
        'icon': 'task_mocap',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Motion Cleanup',
        'value': 'cleanup',
        'color': common.color_manager.get_color('cleanup', qcolor=True, base_hue=30),
        'description': 'Animation and motion capture cleanup',
        'icon': 'task_cleanup',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Modeling',
        'value': 'model',
        'color': common.color_manager.get_color('model', qcolor=True, base_hue=-100),
        'description': 'Build detailed 3D models of characters, props, and environments.',
        'icon': 'task_modeling',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Rigging',
        'value': 'rigging',
        'color': common.color_manager.get_color('rigging', qcolor=True, base_hue=-100),
        'description': 'Develop rigging systems for characters and props to enable animation.',
        'icon': 'task_rigging',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Animation',
        'value': 'anim',
        'color': common.color_manager.get_color('anim', qcolor=True, base_hue=-100),
        'description': 'Animate characters and props using keyframe and motion capture techniques.',
        'icon': 'task_animation',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Layout',
        'value': 'layout',
        'color': common.color_manager.get_color('layout', qcolor=True, base_hue=-100),
        'description': 'Arrange camera placement, staging, shot composition, and scene assembly.',
        'icon': 'task_layout',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Effects',
        'value': 'fx',
        'color': common.color_manager.get_color('fx', qcolor=True, base_hue=-100),
        'description': 'Create atmospheric effects such as smoke, fire, dust, and water.',
        'icon': 'task_fx',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Texture',
        'value': 'texture',
        'color': common.color_manager.get_color('texture', qcolor=True, base_hue=-100),
        'description': 'Perform 2D and 3D texture painting to add surface details to models.',
        'icon': 'task_texture',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Shading & Surfacing',
        'value': 'surfacing',
        'color': common.color_manager.get_color('surfacing', qcolor=True, base_hue=-100),
        'description': 'Apply shading and surfacing techniques to achieve realistic material appearances.',
        'icon': 'task_surfacing',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Compositing',
        'value': 'comp',
        'color': common.color_manager.get_color('comp', qcolor=True, base_hue=0),
        'description': 'Combine rendered elements and assets to create final composite shots.',
        'icon': 'task_compositing',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Tracking',
        'value': 'tracking',
        'color': common.color_manager.get_color('tracking', qcolor=True, base_hue=0),
        'description': 'Perform camera and object tracking to align CGI elements with live-action footage.',
        'icon': 'task_tracking',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Match-moving',
        'value': 'matchmove',
        'color': common.color_manager.get_color('matchmove', qcolor=True, base_hue=0),
        'description': 'Execute camera and object matchmoving to integrate CGI seamlessly.',
        'icon': 'task_matchmove',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Music & Audio',
        'value': 'audio',
        'color': common.color_manager.get_color('audio', qcolor=True, base_hue=0),
        'description': 'Manage sound and music production, including recording, editing, and mixing.',
        'icon': 'task_audio',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Sound FX',
        'value': 'sfx',
        'color': common.color_manager.get_color('sfx', qcolor=True, base_hue=0),
        'description': 'Design, record, and integrate sound effects to enhance the auditory experience.',
        'icon': 'task_sfx',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Conform',
        'value': 'conform',
        'color': common.color_manager.get_color('conform', qcolor=True, base_hue=0),
        'description': 'Ensure source data and footage conform to project specifications for consistency.',
        'icon': 'task_conform',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Grading',
        'value': 'grading',
        'color': common.color_manager.get_color('grading', qcolor=True, base_hue=0),
        'description': 'Perform color grading to adjust and enhance color, contrast, and overall tone.',
        'icon': 'task_grading',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Lighting',
        'value': 'lighting',
        'color': common.color_manager.get_color('lighting', qcolor=True, base_hue=0),
        'description': 'Execute scene and asset lighting to achieve the desired mood and realism.',
        'icon': 'task_lighting',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'Rendering',
        'value': 'render',
        'color': common.color_manager.get_color('render', qcolor=True, base_hue=0),
        'description': 'Conduct final imaging and rendering processes to produce high-quality outputs.',
        'icon': 'task_rendering',
        'status': {},
        'step': None,
        'enabled': True
    },
    common.idx(): {
        'name': 'RnD',
        'value': 'rnd',
        'color': common.color_manager.get_color('rnd', qcolor=True, base_hue=0),
        'description': 'Conduct research and development to innovate techniques, tools, and workflows.',
        'icon': 'task_rnd',
        'status': {},
        'step': None,
        'enabled': True
    },
}

default_file_format_config = {
    common.idx(reset=True, start=0): {
        'name': 'Scene Formats',
        'flag': Format.SceneFormat,
        'value': ', '.join(sorted(common.get_all_known_dcc_formats())),
        'description': 'Scene file formats',
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

default_asset_folder_config = {
    common.idx(reset=True, start=0): {
        'name': AssetFolder.CacheFolder,
        'value': AssetFolder.CacheFolder,
        'description': 'USD, Alembic, and other cache files',
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
