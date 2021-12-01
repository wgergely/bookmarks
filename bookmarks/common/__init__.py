"""The modules contains a list of core parameters, classes and methods
used to define the look and behaviour of Bookmarks.

"""
debug_on = False       # Print debug messages
typecheck_on = True   # Check types
init_mode = None    # App startup mode
active_mode = None # Session mode can be private or syncronised
ui_scale_factor = 1.0      # Global ui scaling factor
dpi = 72.0
sort_by_basename = False # Sort models by a item basename instead of full name
stylesheet = None
signals = None
settings = None
cursor = None
font_db = None

servers = {}
static_bookmarks = {}
bookmarks = {}
favourites = {}
hashes = {}
timers = {}
font_cache = {}

ActiveSectionCache = None

itemdata = {}
monitors = {}

PATH_CACHE = {}
RECTANGLE_CACHE = {}
TEXT_SEGMENT_CACHE = {}
DESCRIPTION_RECTS = {}
SUBDIR_RECTS = {}
SUBDIR_BG_RECTS = {}
SUBDIR_BG_BRUSHES = {}

VIEWER_WIDGET_CACHE = {}

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

# Save the initial module values for later use
__initial_values__ = {k:v for (k,v) in locals().copy().items() if not k.startswith('__')}

import collections

from . core import *
from . font import *
from . settings import *
from . signals import *
from . sessionlock import *
from . ui import *
from . data import *
from . sequence import *
from . tabs import *
from . filemonitor import *
