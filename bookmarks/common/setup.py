import os
import sys
import json
import importlib

from PySide2 import QtWidgets, QtGui

from .. import common


dependencies = (
    'PySide2',
    'OpenImageIO',
    'alembic',
    'numpy',
    'psutil',
    'shotgun_api3',
    'slack_sdk',
)


def initialize(mode):
    """Initializes the components required to run Bookmarks.

    Args:
            mode (int):    The initialization mode. One of ``common.StandaloneMode`` or ``common.EmbeddedMode``.

    """
    from . import verify_dependecies
    verify_dependecies()

    if common.init_mode is not None:
        raise RuntimeError(f'Already initialized as "{common.init_mode}"!')
    if mode not in (common.StandaloneMode, common.EmbeddedMode):
        raise ValueError(
            f'Invalid initalization mode. Got "{mode}", expected `common.StandaloneMode` or `common.EmbeddedMode`')

    common.init_mode = mode

    _init_config()

    common.cursor = QtGui.QCursor()
    common.itemdata = common.DataDict()

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


def uninitialize():
    """Uninitialize the components used by Bookmarks.

    """
    from .. threads import threads
    threads.quit_threads()

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

    from .. import images
    for k, v in images.__initial_values__.items():
        setattr(images, k, v)


def _init_config():
    """Load the config values from common.CONFIG and set them in the `common` module as
    public properties.

    """
    p = common.get_rsc(common.CONFIG)

    with open(p, 'r', encoding='utf8') as f:
        config = json.loads(f.read())

    # Set config values in the common module
    for k, v in config.items():
        setattr(common, k, v)


def _init_ui_scale():
    v = common.settings.value(
        common.SettingsSection,
        common.UIScaleKey
    )

    if v is None or not isinstance(v, str):
        common.ui_scale = 1.0
        return

    if '%' not in v:
        v = 1.0
    else:
        v = v.strip('%')
    try:
        v = float(v) * 0.01
    except:
        v = 1.0

    if not common.ui_scale_factors or v not in common.ui_scale_factors:
        v = 1.0

    common.ui_scale = v


def _init_dpi():
    if common.get_platform() == common.PlatformWindows:
        common.dpi = 72.0
    elif common.get_platform() == common.PlatformMacOS:
        common.dpi = 96.0
    elif common.get_platform() == common.PlatformUnsupported:
        common.dpi = 72.0


def init_environment(env_key, add_private=False):
    """Add the dependencies to the Python environment.

    The method requires that `common.env_key` is set. The key is usually set
    by the Bookmark installer to point to the installation root directory.
    The

    Raises:
            EnvironmentError: When the `common.env_key` is not set.
            RuntimeError: When the `common.env_key` is invalid or a directory missing.

    """
    if env_key not in os.environ:
        raise EnvironmentError(
            f'"{env_key}" environment variable is not set.')

    v = os.environ[env_key]

    if not os.path.isdir(v):
        raise RuntimeError(
            f'"{v}" is not a falid folder. Is "{env_key}" environment variable set?')

    # Add `common.env_key` to the PATH
    v = os.path.normpath(os.path.abspath(v)).strip()
    if v.lower() not in os.environ['PATH'].lower():
        os.environ['PATH'] = v + ';' + os.environ['PATH'].strip(';')

    def _add_path_to_sys(p):
        _v = f'{v}{os.path.sep}{p}'
        if not os.path.isdir(_v):
            raise RuntimeError(f'{_v} does not exist.')

        if _v in sys.path:
            return
        sys.path.append(_v)

    _add_path_to_sys('shared')
    if add_private:
        _add_path_to_sys('private')
    sys.path.append(v)


def verify_dependecies():
    """Checks the presence of all required python modules.

    Raises:
        ModuleNotFoundError: When a required python library was not found.

    """
    for mod in dependencies:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f'Bookmarks cannot be run. A required dependency was not found\n>> {mod}') from e
