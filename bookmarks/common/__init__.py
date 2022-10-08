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
watchers = {}

delegate_paths = {}
delegate_rectangles = {}
delegate_text_segments = {}
delegate_subdir_rectangles = {}
delegate_bg_subdir_rectangles = {}
delegate_bg_brushes = {}
delegate_clickable_rectangles = {}
delegate_description_rectangles = {}

color_cache = {}
color_cache_str = {}

elided_text = {}

VIEWER_WIDGET_CACHE = {}

pixel_ratio = None
oiio_cache = None

image_resource_list = {}
image_resource_data = {}
image_cache = {}

token_configs = {}


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
from .font import *
from .monitor import *
from .sequence import *
from .session_lock import *
from .settings import *
from .setup import *
from .signals import *
from .ui import *
