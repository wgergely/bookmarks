""":mod:`This module<bookmarks.common>` contains key attributes, classes,
and methods used across the app.

Initialization methods for the app can be found in :mod:`~bookmarks.common.setup`. Hard-coded default
properties are contained within :mod:`~bookmarks.common.core`.

This module allows for direct submodule access. For example:

.. code-block:: python
    :linenos:

    # bookmarks.common.setup.initialize(mode=common.Mode.Embedded) from the top level module as:
    from bookmarks import common
    common.initialize(mode=common.Mode.Embedded)

The Bookmarks app operates in two modes: standalone and embedded in a PySide environment. The app's base layers
are initialized using:

.. code-block:: python
    :linenos:

    from bookmarks import common
    common.initialize(mode=common.Mode.Embedded)

To start the app in :meth:`~bookmarks.common.Mode.Standalone`, use :func:`bookmarks.exec_()`. The
:attr:`~bookmarks.common.Mode.Embedded` is designed for running the app within a host DCC, a feature
currently used only by the Maya plugin. Refer to :mod:bookmarks.maya and :mod:`bookmarks.common` for related
methods.

This module also houses widget instance bindings for various components of the app, such as the main widget,
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

color_manager = None

servers = None
env_bookmark_items = {}
bookmarks = {}
favourites = {}
timers = {}

font_cache = {}
metrics_cache = {}

db_connections = {}

active_paths = None

item_data = {}
watchers = {}

viewer_widgets = {}

pixel_ratio = None
oiio_cache = None

image_resource_list = {}
image_resource_data = {}
image_cache = {}

token_configs = {}

parser = None

# Widget instance bindings
main_widget = None
tray_widget = None
maya_widget = None
maya_button_widget = None
gallery_widget = None
launcher_widget = None
message_widget = None
preference_editor_widget = None
server_editor = None
templates_editor = None
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
add_job_widget = None


# Save the initial module values for later use
__initial_values__ = {
    k: (v.copy() if isinstance(v, dict) else v) for (k, v) in
    locals().copy().items() if not k.startswith('__')
}

from .active import *
from .clipboard import *
from .color import *
# Make submodules available from this top module
from .core import *
from .data import *
from .dcc import *
from .env import *
from .filter import *
from .font import *
from .hash import *
from .monitor import *
from .parser import *
from .seqshot import *
from .sequence import *
from .settings import *
from .setup import *
from .signals import *
from .ui import *
