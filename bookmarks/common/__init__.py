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


The app can be run in two modes. As a standalone application, or embedded in a
PySide2 environment. The base-layers can be initialized with:

.. code-block:: python

    from bookmarks import common
    common.initialize(common.EmbeddedMode) # or common.StandaloneMode

:func:`bookmarks.exec_()` is a utility method for starting Bookmarks in
:attr:`common.StandaloneMode`, whilst :attr:`common.EmbeddedMode` is useful when
running from inside a host DCC. Currently only the Maya plugin makes use of this mode.
See :mod:`bookmarks.maya` and :mod:`bookmarks.common` for the related methods.

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
delegate_subdir_rectangles = {}
delegate_bg_subdir_rectangles = {}
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

size_font_small = 11.0
size_font_medium = 12.0
size_font_large = 16.0
size_row_height = 34.0
size_bookmark_row_height = 40.0
size_asset_row_height = 64.0
size_separator = 1.0
size_margin = 18.0
size_indicator = 4.0
size_width = 640.0
size_height = 480.0

color_background = [75, 75, 85, 255]
color_light_background = [145, 140, 145, 255]
color_dark_background = [65, 60, 65, 255]
color_text = [220, 220, 225, 255]
color_secondary_text = [170, 170, 175, 255]
color_selected_text = [250, 250, 255, 255]
color_disabled_text = [140, 140, 145, 255]
color_separator = [35, 35, 40, 255]
color_light_blue = [50, 50, 195, 180]
color_blue = [107, 135, 185, 255]
color_red = [219, 114, 114, 255]
color_red2 = [190, 50, 50, 180]
color_green = [90, 200, 155, 255]
color_dark_green = [110, 190, 160, 255]
color_light_green = [80, 150, 100, 180]
color_opaque = [0, 0, 15, 30]
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
bookmarker_widget = None
bookmark_property_editor = None
asset_property_editor = None
file_saver_widget = None
publish_widget = None
maya_export_widget = None
ffmpeg_export_widget = None
screen_capture_widget = None
pick_thumbnail_widget = None

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
from .monitor import *
from .font import *
from .sequence import *
from .session_lock import *
from .settings import *
from .setup import *
from .signals import *
from .ui import *
