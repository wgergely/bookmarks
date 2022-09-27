# -*- coding: utf-8 -*-
"""Core attributes, classes and methods used to define the look and behaviour of
Bookmarks.


See the :mod:`~bookmarks.common.setup` module for the initialization methods.
Hard-coded default properties are defined in :mod:`~bookmarks.common.core`.
Configurable properties, such as colors and size settings are loaded from
``./rsc/conf.json`` at runtime.

Tip:

    Submodules can be accessed directly from this top module, like so:

    .. code-block:: python

        # bookmarks.common.setup.initialize(common.EmbeddedMode) can be imported as
        from bookmarks import common
        common.initialize(common.EmbeddedMode)


Attributes:

    debug_on (bool): Debug logging is on when True. See :func:`~bookmarks.common.core.debug()`.
    typecheck_on (bool): Type checking on when True. See :func:`~bookmarks.common.core.check_type()`.
    init_mode (int): Initialization mode. See :func:`~bookmarks.common.setup.initialize()`
    active_mode (int): Determines how the active paths are saved and loaded.
        See :mod:`~bookmarks.common.sessionlock` and :mod:`~bookmarks.common.settings`.
    signals (QtCore.QObject): A QObject that holds common application signals.
        See :mod:`~bookmarks.common.signals`.
    settings (QtCore.QSettings): The user settings instance. See :mod:`~bookmarks.common.settings`.
    item_data (common.DataDict): Cache used to store item data. See :mod:`~bookmarks.common.data`.

"""
debug_on = False
typecheck_on = True
init_mode = None
active_mode = None

signals = None
settings = None

ui_scale_factor = 1.0  # Global ui scaling factor
dpi = 72.0
sort_by_basename = False  # Sort models by item basename instead of full name
stylesheet = None
cursor = None
font_db = None

servers = {}
default_bookmarks = {}
bookmarks = {}
favourites = {}
hashes = {}
timers = {}
font_cache = {}
db_connections = {}

active_paths = None

item_data = {}
monitors = {}

delegate_paths = {}
delegate_rectangles = {}
delegate_text_segments = {}
delegate_subdir_rects = {}
delegate_bg_subdir_rects = {}
delegate_bg_brushes = {}

color_cache = {}
color_cache_str = {}

VIEWER_WIDGET_CACHE = {}

pixel_ratio = None
oiio_cache = None

image_resource_list = {}
image_resource_data = {}
image_cache = {}

token_configs = {}

# These values will be overridden by the values in config.json:
documentation_url = 'https://bookmarks.gergely-wootsch.com/html/index.html'
github_url = 'https://github.com/wgergely/bookmarks'
product = 'Bookmarks'
env_key = 'BOOKMARKS_ROOT'
bookmark_cache_dir = '.bookmark'
bookmark_database = 'bookmark.db'
favorite_file_ext = 'bfav'
user_settings = 'user_settings.ini'
stylesheet_file = 'stylesheet.qss'
default_bookmarks_template = 'default_bookmark_items.json'
job_template = 'Job.zip'
asset_template = 'Asset.zip'
max_list_items = 999999
ui_scale_factors = [0.7, 0.8, 0.9, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
bold_font = 'bmRobotoBold'
medium_font = 'bmRobotoMedium'
FontSizeSmall = 11.0
FontSizeMedium = 12.0
FontSizeLarge = 16.0
HeightRow = 34.0
HeightBookmark = 40.0
HeightAsset = 64.0
HeightSeparator = 1.0
WidthMargin = 18.0
WidthIndicator = 4.0
DefaultWidth = 640.0
DefaultHeight = 480.0
BackgroundColor = [75, 75, 85, 255]
BackgroundLightColor = [145, 140, 145, 255]
BackgroundDarkColor = [65, 60, 65, 255]
TextColor = [220, 220, 225, 255]
TextSecondaryColor = [170, 170, 175, 255]
TextSelectedColor = [250, 250, 255, 255]
TextDisabledColor = [140, 140, 145, 255]
SeparatorColor = [35, 35, 40, 255]
BlueLightColor = [50, 50, 195, 180]
BlueColor = [107, 135, 185, 255]
RedLightColor = [190, 50, 50, 180]
RedColor = [219, 114, 114, 255]
GreenLightColor = [80, 150, 100, 180]
GreenColor = [90, 200, 155, 255]
GreenAltColor = [110, 190, 160, 255]
OpaqueColor = [0, 0, 15, 30]
Transparent = [0, 0, 0, 0]
thumbnail_size = 512.0
thumbnail_format = 'png'

# Widget instance bindings
main_widget = None
tray_widget = None
maya_widget = None
maya_button_widget = None
slack_widget = None
gallery_widget = None
launcher_widget = None
message_widget = None
preference_editor_widget = None
bookmark_editor_widget = None
bookmark_property_editor = None
asset_property_editor = None
file_saver_widget = None

sg_connecting_message = None
sg_error_message = None

# Save the initial module values for later use
__initial_values__ = {
    k: (v.copy() if isinstance(v, dict) else v) for (k, v) in
    locals().copy().items() if not k.startswith('__')
}

# Make submodules available from this top module
from .core import *
from .data import *
from .env import *
from .filemonitor import *
from .font import *
from .lists import *
from .sequence import *
from .sessionlock import *
from .settings import *
from .setup import *
from .signals import *
from .ui import *
