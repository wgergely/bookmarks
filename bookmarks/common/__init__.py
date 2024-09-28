"""This module, bookmarks, serves as the core of the Bookmarks application, defining key attributes, classes,
and methods that shape the app's functionality and aesthetics. This module also houses the application's configurable
properties and default settings.

Initialization methods for the application can be found in :mod:`~bookmarks.common.setup`. Hard-coded default
properties are contained within :mod:`~bookmarks.common.core`. Configurable properties, including color schemes and
size settings, are loaded from ./rsc/conf.json during runtime.

This module allows for direct submodule access. For example:

.. code-block:: python
    :linenos:

    # bookmarks.common.setup.initialize(common.EmbeddedMode) can be imported as
    from bookmarks import common
    common.initialize(common.EmbeddedMode)

The Bookmarks application operates in two modes: standalone and embedded in a PySide2 environment. The app's base layers
are initialized using:

.. code-block:: python
    :linenos:

    from bookmarks import common
    common.initialize(common.EmbeddedMode) # or common.StandaloneMode

To start Bookmarks in :attr:`~bookmarks.common.core.StandaloneMode`, use :func:`bookmarks.exec_()`. The
:attr:`~bookmarks.common.core.EmbeddedMode` is designed for running the application within a host DCC, a feature
currently utilized only by the Maya plugin. Refer to :mod:bookmarks.maya and :mod:`bookmarks.common` for related
methods.

This module also houses widget instance bindings for various components of the application, such as the main widget,
tray widget, and several editor widgets. The initial values of module-level variables are stored in the
`__initial_values__` dictionary for potential later use.

This top module additionally makes various submodules available, including those related to core functionalities,
data handling, environment settings, font settings, UI elements, and more.

"""
debug_on = False
typecheck_on = False
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
timers = {}

font_cache = {}
metrics_cache = {}

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

elided_text = {}

viewer_widgets = {}

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
gallery_widget = None
launcher_widget = None
message_widget = None
preference_editor_widget = None
job_editor = None
bookmark_property_editor = None
asset_property_editor = None
clipboard_editor = None
file_saver_widget = None
publish_widget = None
maya_export_widget = None
ffmpeg_export_widget = None
akaconvert_widget = None
screen_capture_widget = None
pick_thumbnail_widget = None
notes_widget = None


# Save the initial module values for later use
__initial_values__ = {
    k: (v.copy() if isinstance(v, dict) else v) for (k, v) in
    locals().copy().items() if not k.startswith('__')
}

# Make submodules available from this top module
from .core import *
from .hash import *
from .data import *
from .env import *
from .font import *
from .monitor import *
from .sequence import *
from .active_mode import *
from .clipboard import *
from .settings import *
from .setup import *
from .signals import *
from .ui import *