"""Various methods used to initialize Bookmarks, mainly, :func:`.initialize()` and
:func:`.shutdown()`.

"""
import io
import logging
import os
import sys
import time

from PySide2 import QtWidgets, QtCore

from .. import common

#: Required dependencies for the app to run
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

    This function must be called before any other Bookmarks functions. It's responsible for loading resource variables
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

            with common.initialize(mode=common.Mode.Standalone) as app:  # automatically calls exec_() on exit
                asset = common.active('asset')

    Args:
        mode (common.Mode): The mode in which to initialize Bookmarks.
        run_app (bool): If True, the QApplication will be executed on exit. Default is False.

    """

    def __new__(
            cls,
            mode=common.Mode.Standalone,
            run_app=False,
            log_level=logging.INFO,
            log_to_console=False,
            log_to_file=False,
            show_ui_logs=False,
            server=None,
            job=None,
            root=None,
            asset=None,
            task=None
    ):
        initialize_func(
            mode=mode,
            log_level=log_level,
            log_to_console=log_to_console,
            log_to_file=log_to_file,
            show_ui_logs=show_ui_logs,
            server=server,
            job=job,
            root=root,
            asset=asset,
            task=task
        )

        return super().__new__(cls)

    def __init__(
            self,
            mode=common.Mode.Standalone,
            run_app=False,
            log_level=logging.INFO,
            log_to_console=False,
            log_to_file=False,
            show_ui_logs=False,
            server=None,
            job=None,
            root=None,
            asset=None,
            task=None
    ):
        self.mode = mode
        self.run_app = run_app

        self.log_level = log_level
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.show_ui_logs = show_ui_logs

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

        shutdown()

        return False


def initialize_func(
        mode=common.Mode.Standalone,
        log_level=logging.INFO,
        log_to_console=False,
        log_to_file=False,
        show_ui_logs=False,
        server=None,
        job=None,
        root=None,
        asset=None,
        task=None
):
    """Initializes all app components.

    """
    from .. import log
    log.init_log(
        log_level=log_level,
        init_console=log_to_console,
        init_file=log_to_file,
    )

    if server:
        os.environ['Bookmarks_ACTIVE_SERVER'] = server
    if job:
        os.environ['Bookmarks_ACTIVE_JOB'] = job
    if root:
        os.environ['Bookmarks_ACTIVE_ROOT'] = root
    if asset:
        os.environ['Bookmarks_ACTIVE_ASSET'] = asset
    if task:
        os.environ['Bookmarks_ACTIVE_TASK'] = task

    if common.init_mode is not None:
        raise RuntimeError(f'Already initialized as "{common.init_mode}"!')

    if mode not in common.Mode:
        raise ValueError(
            f'Invalid initialization mode. Got "{mode}", '
            f'expected one of {", ".join([f"{m}" for m in common.Mode])}.'
        )

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
        i = 0.01
        timeout = time.time() + 10.0
        while not all(f.isRunning() for f in _threads):
            time.sleep(i)
            if time.time() >= timeout:
                break

        if show_ui_logs:
            from ..log import view as editor
            editor.show()
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

        from .. import log
        log.teardown_log()
    except Exception as e:
        print(f'Error during shutdown: {e}')
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
