"""Core attributes, classes and methods used to define the look and behaviour of Bookmarks.


See the :mod:`bookmarks.common.setup` module for the initialization methods. Hard-coded default
properties are defined in :mod:`bookmarks.common.core`. Configurable properties, such as colours and
size settings are loaded from ``./rsc/conf.json`` at runtime.

Tip:

    Submodules can be accessed directly from this top module, like so:

    .. code-block:: python

        # bookmarks.common.setup.initialize(common.EmbeddedMode) can be imported as
        from bookmarks import common
        common.initialize(common.EmbeddedMode)


Attributes:

    debug_on (bool): Debug logging is on when True. See :func:`bookmarks.common.core.debug()`.
    typecheck_on (bool): Type checking on when True. See :func:`bookmarks.common.core.check_type()`.
    init_mode (int): Initialization mode. See :func:`bookmarks.common.setup.initialize()`
    active_mode (int): Determines how the active paths are saved and loaded.
        See :mod:`bookmarks.common.sessionlock` and :mod:`bookmarks.common.settings`.
    signals (QtCore.QObject): A QObject that holds common application signals.
        See :mod:`bookmarks.common.signals`.
    settings (QtCore.QSettings): The user settings instance. See :mod:`bookmarks.common.settings`.
    item_data (common.DataDict): Cache used to store item data. See :mod:`bookmarks.common.data`.

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
static_bookmarks = {}
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
delegate_description_rects = {}
delegate_subdir_rects = {}
delegate_bg_subdir_rects = {}
delegate_bg_brushes = {}

color_cache = {}

VIEWER_WIDGET_CACHE = {}

pixel_ratio = None
oiio_cache = None

image_resource_list = {}
image_resource_data = {}
image_cache = {}



# Values to be initialized by the config.json file.
product = None
env_key = None
bookmark_cache_dir = None
favorite_file_ext = None
static_bookmarks_template = None
job_template = None
asset_template = None
max_list_items = None
ui_scale_factors = None
bold_font = None
medium_font = None
FontSizeSmall = None
FontSizeMedium = None
FontSizeLarge = None
HeightRow = None
HeightBookmark = None
HeightAsset = None
HeightSeparator = None
WidthMargin = None
WidthIndicator = None
DefaultWidth = None
DefaultHeight = None
BackgroundColor = None
BackgroundLightColor = None
BackgroundDarkColor = None
TextColor = None
TextSecondaryColor = None
TextSelectedColor = None
TextDisabledColor = None
SeparatorColor = None
BlueColor = None
RedColor = None
GreenColor = None
OpaqueColor = None

# Widget instance bindings
main_widget = None
tray_widget = None
maya_widget = None
maya_button_widget = None
slack_widget = None
gallery_widget = None
launcher_widget = None
message_widget = None

sg_connecting_message = None
sg_error_message = None

# Save the initial module values for later use
__initial_values__ = {k: (v.copy() if isinstance(v, dict) else v) for (k, v) in locals().copy().items() if not k.startswith('__')}

from .core import *
from .data import *
from .filemonitor import *
from .font import *
from .sequence import *
from .sessionlock import *
from .settings import *
from .setup import *
from .signals import *
from .lists import *
from .ui import *
