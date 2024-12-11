"""Various methods used to initialize Bookmarks, mainly, :func:`.initialize()` and
:func:`.shutdown()`.

"""
import io
import os
import sys
import time

from PySide2 import QtWidgets, QtCore

from .. import common

dependencies = (
    'PySide2',
    'OpenImageIO',
    'numpy',
    'psutil',
    'shotgun_api3',
)


class initialize:
    """
    Initializes the components required to run Bookmarks.

    This function must be called before any other Bookmarks functions. It is responsible for loading resource variables
    and starting helper threads that item models use to load information. When using Bookmarks inside a compatible DCC,
    the mode should be :attr:`~bookmarks.common.Mode.Embedded`. For running as a standalone app,
    use :attr:`~bookmarks.common.Mode.Standalone`. Remember to call :func:`shutdown` before terminating the app to
    gracefully stop threads and remove previously initialized components from memory.

    Example:

        .. code-block:: python
            :linenos:

            from bookmarks import common

            common.initialize(common.Mode.Standalone)
            common.shutdown()

            # or as a context manager

            with common.initialize(common.Mode.Standalone) as app:  # automatically calls exec_() on exit
                asset = common.active('asset')

    Args:
        mode (common.Mode): The mode in which to initialize Bookmarks.
        run_app (bool): If True, the QApplication will be executed on exit. Default is False.

    """

    def __new__(
            cls,
            mode=common.Mode.Standalone,
            run_app=False,
            server=None,
            job=None,
            root=None,
            asset=None,
            task=None
    ):
        from bookmarks import log
        log.debug(__name__, f'Initializing Bookmarks in {mode} mode...')
        initialize_func(mode=mode, server=server, job=job, root=root, asset=asset, task=task)
        return super().__new__(cls)

    def __init__(
            self,
            mode=common.Mode.Standalone,
            run_app=False,
            server=None,
            job=None,
            root=None,
            asset=None,
            task=None
    ):
        self.mode = mode
        self.run_app = run_app

        self.server = server
        self.job = job
        self.root = root
        self.asset = asset
        self.task = task

    def __enter__(self):
        return QtWidgets.QApplication.instance()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            shutdown()
            return False

        if self.mode == common.Mode.Standalone and self.run_app:
            QtWidgets.QApplication.instance().exec_()

        from bookmarks import log
        log.debug(__name__, f'Bookmarks is shutting down...')

        shutdown()

        return False


def get_active_overrides_from_env():
    """Get active overrides from the environment."""
    # Check and verify that the active overrides are set and are pointing to a valid path
    overrides = {}

    for k in common.ActivePathSegmentTypes:
        v = os.environ.get(f'Bookmarks_ACTIVE_{k.upper()}', None)
        overrides[k] = v

        # Check if the path exists
        path = '/'.join([v for v in overrides.values() if v])
        if path and not os.path.exists(path):
            continue

    return overrides


def initialize_func(
        mode=common.Mode.Standalone,
        server=None,
        job=None,
        root=None,
        asset=None,
        task=None
):
    """Initializes all app components.

    """
    if common.init_mode is not None:
        raise RuntimeError(f'Already initialized as "{common.init_mode}"!')

    if mode not in common.Mode:
        raise ValueError(
            f'Invalid initialization mode. Got "{mode}", '
            f'expected one of {", ".join([f"{m}" for m in common.Mode])}.'
        )

    # Set active overrides if they're provided and/or available from the environment
    # Explicitly passed overrides take precedence over environment variables
    env_overrides = get_active_overrides_from_env()
    common.active_server_override = server or env_overrides.get('server', None) or None
    common.active_job_override = job or env_overrides.get('job', None) or None
    common.active_root_override = root or env_overrides.get('root', None) or None
    common.active_asset_override = asset or env_overrides.get('asset', None) or None
    common.active_task_override = task or env_overrides.get('task', None) or None

    try:
        common.init_mode = mode
        common.item_data = common.DataDict()

        if not os.path.isdir(common.temp_path()):
            os.makedirs(os.path.normpath(common.temp_path()))

        common.init_signals(connect_signals=mode != common.Mode.Core)
        common.init_active_mode()
        common.init_settings()
        common.init_active()

        from .parser import StringParser
        common.parser = StringParser()

        from . import color
        common.init_color_manager()

        if mode == common.Mode.Core:
            return

        from . import ui
        ui.init_ui_scale()
        ui.init_dpi()

        from .. import images
        images.init_image_cache()
        images.init_resources()

        from .. import standalone
        if not QtWidgets.QApplication.instance() and mode == common.Mode.Standalone:
            standalone.set_application_properties()

            app = QtWidgets.QApplication(sys.argv)

            standalone.set_application_properties(app=app)

            app.setApplicationName(common.product.title())

            app.setOrganizationName(common.organization)

            app.setOrganizationDomain(common.organization_domain)
            app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

            app.setEffectEnabled(QtCore.Qt.UI_AnimateCombo, False)
            app.setEffectEnabled(QtCore.Qt.UI_AnimateToolBox, False)
            app.setEffectEnabled(QtCore.Qt.UI_AnimateTooltip, False)

            standalone.set_model_id()
            standalone.set_window_icon(app)

            app.eventFilter = standalone.global_event_filter
            app.installEventFilter(app)

        elif not QtWidgets.QApplication.instance():
            raise RuntimeError('No QApplication instance found.')

        images.init_pixel_ratio()

        from . import font
        font._init_font_db()
        ui._init_stylesheet()

        if mode == common.Mode.Standalone:
            standalone.init()
        elif mode == common.Mode.Embedded:
            from .. import main
            main.init()

        # Start non-model linked worker threads
        _threads = []
        from ..threads import threads
        thread = threads.get_thread(threads.QueuedDatabaseTransaction)
        thread.start()
        _threads.append(thread)
        thread = threads.get_thread(threads.QueuedSGQuery)
        thread.start()
        _threads.append(thread)

        # Wait for all threads to spin up before continuing
        n = 0.0
        i = 0.01
        now = time.time()
        timeout = now + 10.0
        while not all(f.isRunning() for f in _threads):
            n += i
            time.sleep(i)
            if n >= timeout:
                break
    except Exception as e:
        from .. import log
        log.error(__name__, f'Error during initialization: {e}')
    finally:
        return io.BytesIO()


def shutdown():
    """Un-initializes all app components.

    """
    _init_mode = common.init_mode
    try:
        from ..threads import threads
        threads.quit_threads()

        from .. import database
        database.remove_all_connections()

        if common.main_widget:
            common.main_widget.hide()
            common.main_widget.deleteLater()
            common.main_widget = None

        if common.tray_widget:
            common.tray_widget.hide()
            common.tray_widget.deleteLater()
            common.tray_widget = None

        common.Timer.delete_timers()
        common.remove_lock()

        # This should reset all the object caches to their initial values
        for k, v in common.__initial_values__.items():
            setattr(common, k, v)

    except Exception as e:
        from . import log
        log.error(__name__, f'Error during shutdown: {e}')
    finally:
        if _init_mode == common.Mode.Standalone and QtWidgets.QApplication.instance():
            QtWidgets.QApplication.instance().exit(0)


def _add_path_to_patht(v, p):
    _v = os.path.normpath(f'{v}{os.path.sep}{p}')
    if not os.path.isdir(_v):
        raise RuntimeError(f'{_v} does not exist.')

    # Windows DLL loading has changed in Python 3.8+ and PATH is no longer used
    if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
        os.add_dll_directory(_v)

    if _v.lower() not in os.environ['PATH'].lower():
        os.environ['PATH'] = f'{os.path.normpath(_v)};{os.environ["PATH"].strip(";")}'
