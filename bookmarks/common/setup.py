# -*- coding: utf-8 -*-
"""Various methods used to initialize Bookmarks, mainly, :func:`.initialize()` and
:func:`.uninitialize()`.

"""
import importlib
import json
import os
import sys
import time

from PySide2 import QtWidgets, QtGui

from .. import common

dependencies = (
    'PySide2',
    'OpenImageIO',
    'numpy',
    'psutil',
    'shotgun_api3',
    'slack_sdk',
)


def initialize(mode):
    """Initialize the components required to run Bookmarks.

    Args:
        mode (str): The initialization mode. One of ``common.StandaloneMode``
                or ``common.EmbeddedMode``.

    """
    from . import verify_dependencies
    verify_dependencies()

    if common.init_mode is not None:
        raise RuntimeError(f'Already initialized as "{common.init_mode}"!')
    if mode not in (common.StandaloneMode, common.EmbeddedMode):
        raise ValueError(
            f'Invalid initialization mode. Got "{mode}", expected '
            f'`common.StandaloneMode` or `common.EmbeddedMode`'
        )

    common.init_mode = mode

    _init_config()

    common.cursor = QtGui.QCursor()
    common.item_data = common.DataDict()

    if not os.path.isdir(common.temp_path()):
        os.makedirs(os.path.normpath(common.temp_path()))

    common.init_signals()
    common.prune_lock()
    common.init_lock()  # Sets the current active mode
    common.init_settings()

    _init_ui_scale()
    _init_dpi()

    from .. import images
    images.init_imagecache()
    images.init_resources()

    from .. import standalone
    if not QtWidgets.QApplication.instance() and mode == common.StandaloneMode:
        standalone.BookmarksApp([])
    elif not QtWidgets.QApplication.instance():
        raise RuntimeError('No QApplication instance found.')

    images.init_pixel_ratio()
    common.init_font()

    if mode == common.StandaloneMode:
        standalone.init()
    elif mode == common.EmbeddedMode:
        from .. import main
        main.init()

    common.init_monitor()

    # Start non-model linked worker threads
    _threads = []
    from ..threads import threads
    thread = threads.get_thread(threads.QueuedDatabaseTransaction)
    thread.start()
    _threads.append(thread)
    thread = threads.get_thread(threads.QueuedShotgunQuery)
    thread.start()
    _threads.append(thread)

    # Wait for all threads to spin up before continuing
    n = 0.0
    while not all(f.isRunning() for f in _threads):
        n += 0.1
        time.sleep(0.1)
        if n > 2.0:
            break


def uninitialize():
    """Un-initialize all app components.

    """
    from ..threads import threads
    threads.quit_threads()

    from .. import database
    database.remove_all_connections()

    try:
        common.main_widget.hide()
        common.main_widget.deleteLater()
    except:
        pass
    common.main_widget = None

    if common.init_mode == common.StandaloneMode:
        QtWidgets.QApplication.instance().quit()

    common.Timer.delete_timers()

    for k, v in common.__initial_values__.items():
        setattr(common, k, v)

    common.remove_lock()


def _init_config():
    """Load the config values from common.CONFIG and set them in the `common`
    module as properties.

    """
    p = common.get_rsc(common.CONFIG)

    with open(p, 'r', encoding='utf8') as f:
        config = json.loads(f.read())

    # Set config values in the common module
    for k, v in config.items():
        setattr(common, k, v)


def _init_ui_scale():
    v = common.settings.value('settings/ui_scale')

    if v is None or not isinstance(v, str):
        common.ui_scale_factor = 1.0
        return

    if '%' not in v:
        v = 1.0
    else:
        v = v.strip('%')
    try:
        v = float(v) * 0.01
    except:
        v = 1.0
    v = round(v, 2)
    if not common.ui_scale_factors or v not in common.ui_scale_factors:
        v = 1.0

    common.ui_scale_factor = v


def _init_dpi():
    if common.get_platform() == common.PlatformWindows:
        common.dpi = 72.0
    elif common.get_platform() == common.PlatformMacOS:
        common.dpi = 96.0
    elif common.get_platform() == common.PlatformUnsupported:
        common.dpi = 72.0


def _add_path_to_path(v, p):
    _v = os.path.normpath(f'{v}{os.path.sep}{p}')
    if not os.path.isdir(_v):
        raise RuntimeError(f'{_v} does not exist.')

    # Windows DLL loading has changed in Python 3.8+ and PATH is no longer used
    if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
        os.add_dll_directory(_v)

    if _v.lower() not in os.environ['PATH'].lower():
        os.environ['PATH'] = f'{os.path.normpath(_v)};{os.environ["PATH"].strip(";")}'


def init_environment(key, add_private=False):
    """Add the dependencies to the Python environment.

    The method requires that `env_key` is set. The key is usually set
    by the Bookmark installer to point to the installation root directory.

    Raises:
            EnvironmentError: When the `key` environment is not set.
            RuntimeError: When the `key` environment is invalid or points to a missing
                            directory.

    """
    if key not in os.environ:
        raise EnvironmentError(
            f'"{key}" environment variable is not set.'
        )
    v = os.environ[key]
    if not os.path.isdir(v):
        raise RuntimeError(
            f'"{v}" is not a valid folder. Is "{key}" environment variable set?'
        )

    _add_path_to_path(v, '.')
    _add_path_to_path(v, 'bin')

    _add_path_to_sys(v, 'shared')
    if add_private:
        _add_path_to_sys(v, 'core')
    if v not in sys.path:
        sys.path.append(v)


def verify_dependencies():
    """Checks the presence of all required python modules.

    Raises:
        ModuleNotFoundError: When a required python library was not found.

    """
    for mod in dependencies:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f'Bookmarks cannot be run. A required dependency was not found\n>> {mod}'
            ) from e
