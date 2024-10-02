"""Various methods used to initialize Bookmarks, mainly, :func:`.initialize()` and
:func:`.shutdown()`.

"""
import io
import os
import sys
import time

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common

dependencies = (
    'PySide2',
    'OpenImageIO',
    'numpy',
    'psutil',
    'shotgun_api3',
)


class initialize:

    def __new__(cls, mode, *args, **kwargs):
        print('[Bookmarks] Initializing...')
        initialize_func(mode)
        return super().__new__(cls)

    def __init__(self, mode):
        self.mode = mode

    def __enter__(self):
        return QtWidgets.QApplication.instance()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            shutdown()
            return False

        if self.mode == common.StandaloneMode:
            QtWidgets.QApplication.instance().exec_()

        print('[Bookmarks] Shutting down...')
        shutdown()

        return False


def initialize_func(mode):
    """Initializes the components required to run Bookmarks.

    It's important to call this function before running the app as it's responsible
    for loading the resource variables and starting the helper threads item models use
    to load information.

    Note:
        Don't forget to call :func:`shutdown` before terminating the application,
        to gracefully stop threads and remove previously initialized components from the
        memory.

    When Bookmarks is used inside a compatible DCC, the mode should be
    :attr:`~bookmarks.common.core.EmbeddedMode`. When running as a standalone application, use
    :attr:`~bookmarks.common.core.StandaloneMode`.


    .. code-block:: python
        :linenos:

        from bookmarks import common

        common.initialize(common.StandaloneMode)
        common.main_widget.show()
        common.shutdown()


    Args:
        mode (str): The initialization mode. One of :attr:`~bookmarks.common.core.StandaloneMode`,
            :attr:`~bookmarks.common.core.EmbeddedMode`, or :attr:`~bookmarks.common.core.CoreMode`.

    """
    try:
        if common.init_mode is not None:
            raise RuntimeError(f'Already initialized as "{common.init_mode}"!')
        if mode not in (common.StandaloneMode, common.EmbeddedMode, common.CoreMode):
            raise ValueError(
                f'Invalid initialization mode. Got "{mode}", expected '
                f'`StandaloneMode` or `EmbeddedMode` or `CoreMode`.'
            )

        common.init_mode = mode
        common.item_data = common.DataDict()

        from . import parser
        common.parser = parser.Parser()


        if not os.path.isdir(common.temp_path()):
            os.makedirs(os.path.normpath(common.temp_path()))

        common.init_signals(connect_signals=mode != common.CoreMode)
        common.init_active_mode()
        common.init_settings()
        common.init_active()

        if mode == common.CoreMode:
            return

        common.cursor = QtGui.QCursor()

        from . import ui
        ui._init_ui_scale()
        ui._init_dpi()

        from .. import images
        images.init_image_cache()
        images.init_resources()

        from .. import standalone
        if not QtWidgets.QApplication.instance() and mode == common.StandaloneMode:
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

        if mode == common.StandaloneMode:
            standalone.init()
        elif mode == common.EmbeddedMode:
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
        from bookmarks import log
        log.error(f'Error during initialization: {e}')
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
        log.error(f'Error during shutdown: {e}')
    finally:
        if _init_mode == common.StandaloneMode and QtWidgets.QApplication.instance():
            QtWidgets.QApplication.instance().exit(0)




def _add_path_to_path(v, p):
    _v = os.path.normpath(f'{v}{os.path.sep}{p}')
    if not os.path.isdir(_v):
        raise RuntimeError(f'{_v} does not exist.')

    # Windows DLL loading has changed in Python 3.8+ and PATH is no longer used
    if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
        os.add_dll_directory(_v)

    if _v.lower() not in os.environ['PATH'].lower():
        os.environ['PATH'] = f'{os.path.normpath(_v)};{os.environ["PATH"].strip(";")}'
