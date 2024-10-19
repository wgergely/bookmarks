"""The module contains the classes needed to initialize in :attr:`~bookmarks.common.Mode.Standalone` mode.

It defines :class:`.BookmarksAppWindow`, the app's main window based on :class:`.main.MainWidget` (in
:attr:`~bookmarks.common.Mode.Embedded`, Bookmarks uses :class:`.main.MainWidget` as the main widget).

"""
import ctypes
import os
import uuid

from PySide2 import QtWidgets, QtGui, QtCore

from . import actions
from . import common
from . import contextmenu
from . import main


def init():
    """Initializes the main app window.

    """
    if common.init_mode != common.Mode.Standalone:
        raise RuntimeError('Must be initialized in StandaloneMode!')

    if isinstance(common.main_widget, BookmarksAppWindow):
        raise RuntimeError('MainWidget already exists!')

    common.main_widget = BookmarksAppWindow()


def init_tray():
    """Initializes the app's tray widget.

    """
    if not common.tray_widget:
        common.tray_widget = Tray()
        common.tray_widget.show()


@QtCore.Slot()
def show():
    """Shows the main app window.

    """
    if common.init_mode != common.Mode.Standalone or not isinstance(
            common.main_widget,
            BookmarksAppWindow
    ):
        raise RuntimeError('Window can only be show in StandaloneMode.')

    dict_key = common.main_widget.__class__.__name__
    v = common.settings.value('state/state')

    state = v[dict_key] if v and dict_key in v else None
    state = QtCore.Qt.WindowNoState if state is None else QtCore.Qt.WindowState(state)

    common.main_widget.activateWindow()
    common.restore_window_geometry(common.main_widget)

    if state == QtCore.Qt.WindowNoState:
        common.main_widget.showNormal()
    elif state & QtCore.Qt.WindowMaximized:
        common.main_widget.showMaximized()
    elif state & QtCore.Qt.WindowFullScreen:
        common.main_widget.showFullScreen()
    else:
        common.main_widget.showNormal()


def set_application_properties(app=None):
    """Enables OpenGL and high-dpi support.

    """
    if app:
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
        return

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseOpenGLES, True)
    QtWidgets.QApplication.setAttribute(
        QtCore.Qt.AA_EnableHighDpiScaling, True
    )
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class TrayMenu(contextmenu.BaseContextMenu):
    """The context menu associated with :class:`.Tray`.

    """

    def __init__(self, parent=None):
        super().__init__(QtCore.QModelIndex(), parent=parent)

        self.stays_always_on_top = False
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self.setStyleSheet(None)

    def setup(self):
        """Creates the context menu.

        """
        try:
            self.scripts_menu()
            self.separator()
            self.window_menu()
            self.separator()
            self.tray_menu()
        except:
            pass

    def tray_menu(self):
        """Actions associated with the visibility of the widget."""
        self.menu['Quit'] = {
            'action': common.shutdown,
        }
        return


class Tray(QtWidgets.QSystemTrayIcon):
    """A system tray icon used to control Bookmarks from the Windows Task Bar
    (on Windows).

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        p = common.rsc(
            f'{common.GuiResource}{os.path.sep}icon.{common.thumbnail_format}'
        )
        pixmap = QtGui.QPixmap(p)
        icon = QtGui.QIcon(pixmap)
        self.setIcon(icon)

        w = TrayMenu(parent=self.window())
        self.setContextMenu(w)

        self.setToolTip(common.product.title())

        self.activated.connect(self.tray_activated)

    def window(self):
        """Returns the main application window.

        """
        return common.main_widget.window()

    def tray_activated(self, reason):
        """Slot connected to the custom tray activation signals.

        """
        if reason == QtWidgets.QSystemTrayIcon.Unknown:
            self.window().show()
            self.window().activateWindow()
            self.window().raise_()
        if reason == QtWidgets.QSystemTrayIcon.Context:
            return
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.window().show()
            self.window().activateWindow()
            self.window().raise_()
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            return
        if reason == QtWidgets.QSystemTrayIcon.MiddleClick:
            return


class BookmarksAppWindow(main.MainWidget):
    """The main application window.

    """

    def __init__(self, parent=None):
        if isinstance(common.main_widget, self.__class__):
            raise RuntimeError(f'{self.__class__.__name__} already exists.')

        super().__init__(parent=None)

        self._always_on_top = False

        common.set_stylesheet(self)

        self.installEventFilter(self)

        self.initialized.connect(self._connect_standalone_signals)
        self.initialized.connect(init_tray)

        self.adjustSize()
        self.update_window_flags()

    def update_window_flags(self, v=None):
        """Load previously saved window flag values from user setting files.

        """
        self._always_on_top = common.settings.value('settings/always_always_on_top')

        if self._always_on_top:
            self.setWindowFlags(
                self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
            )
        else:
            self.setWindowFlags(
                self.windowFlags() & ~ QtCore.Qt.WindowStaysOnTopHint
            )

    @QtCore.Slot()
    def _connect_standalone_signals(self):
        """Extra signal connections when Bookmarks runs in standalone mode.

        """
        self.files_widget.activated.connect(actions.execute)
        self.favourites_widget.activated.connect(actions.execute)

    def hideEvent(self, event):
        """Event handler.

        """
        common.save_window_state(self)
        super().hideEvent(event)

    def closeEvent(self, event):
        """Event handler.

        """
        event.ignore()
        self.hide()
        try:
            common.tray_widget.showMessage(
                'Bookmarks',
                'Bookmarks will continue running in the background. Use this icon to restore its visibility.',
                QtWidgets.QSystemTrayIcon.Information,
                3000
            )
        except:
            pass
        common.save_window_state(self)

    def changeEvent(self, event):
        """Event handler.

        """
        if event.type() == QtCore.QEvent.WindowStateChange:
            common.save_window_state(self)
        super().changeEvent(event)

    def showEvent(self, event):
        """Event handler.

        """
        if not self.is_initialized:
            QtCore.QTimer.singleShot(100, self.initialize)
        super().showEvent(event)


def set_window_icon(app):
    """Set the app icon."""
    path = common.rsc(
        f'{common.GuiResource}{os.path.sep}icon.{common.thumbnail_format}'
    )

    pixmap = QtGui.QPixmap(path)
    if pixmap.isNull():
        return None

    icon = QtGui.QIcon(pixmap)
    app.setWindowIcon(icon)


def set_model_id():
    """Set windows model id to add custom window icons on windows.
    https://github.com/cztomczak/cefpython/issues/395

    """
    if QtCore.QSysInfo().productType() in ('windows', 'winrt'):
        hresult = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f'{common.product}-{uuid.uuid4()}'.encode('utf-8')
        )
        # An identifier that's globally unique for all apps running on Windows
        assert hresult == 0, "SetCurrentProcessExplicitAppUserModelID failed"


def global_event_filter(widget, event):
    """Event filter handler.

    """
    if not common.signals:
        return False

    if event.type() == QtCore.QEvent.Enter:
        if hasattr(widget, 'statusTip') and widget.statusTip():
            common.signals.showStatusTipMessage.emit(widget.statusTip())
    if event.type() == QtCore.QEvent.Leave:
        common.signals.clearStatusBarMessage.emit()

    return False
