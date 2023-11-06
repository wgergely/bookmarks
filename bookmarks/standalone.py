"""The module contains the elements used when initialized in :attr:`~bookmarks.common.core.StandaloneMode`.

It defines :class:`.BookmarksApp`, Bookmark's custom QApplication, and
:class:`.BookmarksAppWindow`, a modified :class:`.main.MainWidget`.

Note, in :attr:`~bookmarks.common.core.EmbeddedMode`, Bookmarks uses :class:`.main.MainWidget` as the main
widget.

"""
import ctypes
import os

from PySide2 import QtWidgets, QtGui, QtCore

from . import __version__
from . import actions
from . import common
from . import contextmenu
from . import main
from . import ui

MODEL_ID = f'{common.product}App'


def init():
    """Initializes the main application window.

    """
    if common.init_mode == common.EmbeddedMode:
        raise RuntimeError("Cannot be initialized in `EmbeddedMode`.")

    if isinstance(common.main_widget, BookmarksAppWindow):
        raise RuntimeError("MainWidget already exists.")
    common.main_widget = BookmarksAppWindow()


def init_tray():
    """Initializes the main application tray widget.

    """
    if not common.tray_widget:
        common.tray_widget = Tray()
        common.tray_widget.show()


@QtCore.Slot()
def show():
    """Shows the main application window.

    """
    if common.init_mode != common.StandaloneMode or not isinstance(
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


def _set_application_properties(app=None):
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
            'action': common.uninitialize,
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


class MinimizeButton(ui.ClickableIconButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super().__init__(
            'minimize',
            (common.color(common.color_red), common.color(common.color_secondary_text)),
            common.size(common.size_margin) -
            common.size(common.size_indicator),
            description='Click to minimize the window...',
            parent=parent
        )


class CloseButton(ui.ClickableIconButton):
    """Button used to close/hide a widget or window."""

    def __init__(self, parent=None):
        super().__init__(
            'close',
            (common.color(common.color_red), common.color(common.color_secondary_text)),
            common.size(common.size_margin) -
            common.size(common.size_indicator),
            description='Click to close the window...',
            parent=parent
        )


class HeaderWidget(QtWidgets.QWidget):
    """Horizontal widget for controlling the position of the active window."""
    widgetMoved = QtCore.Signal(QtCore.QPoint)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.label = None
        self.closebutton = None
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self.double_click_timer = common.Timer(parent=self)
        self.double_click_timer.setInterval(
            QtWidgets.QApplication.instance().doubleClickInterval()
        )
        self.double_click_timer.setSingleShot(True)

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setFixedHeight(
            common.size(common.size_margin) +
            (common.size(common.size_indicator) * 2)
        )

        self._create_ui()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        menu_bar = QtWidgets.QMenuBar(parent=self)
        self.layout().addWidget(menu_bar)
        menu_bar.hide()
        menu = menu_bar.addMenu(common.product)

        action = menu.addAction('Quit')
        action.triggered.connect(common.uninitialize)

        self.layout().addStretch()
        self.layout().addWidget(MinimizeButton(parent=self))
        self.layout().addSpacing(common.size(common.size_indicator) * 2)
        self.layout().addWidget(CloseButton(parent=self))
        self.layout().addSpacing(common.size(common.size_indicator) * 2)

    def mousePressEvent(self, event):
        """Event handler.

        """
        if self.double_click_timer.isActive():
            return
        if not isinstance(event, QtGui.QMouseEvent):
            return

        self.double_click_timer.start(self.double_click_timer.interval())
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(
            self.geometry().topLeft()
        )

    def mouseMoveEvent(self, event):
        """Event handler.

        """
        if self.double_click_timer.isActive():
            return
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if self.move_start_widget_pos:
            margins = self.window().layout().contentsMargins()
            offset = (event.pos() - self.move_start_event_pos)
            pos = self.window().mapToGlobal(self.geometry().topLeft()) + offset
            self.parent().move(
                pos.x() - margins.left(),
                pos.y() - margins.top()
            )
            bl = self.window().rect().bottomLeft()
            bl = self.window().mapToGlobal(bl)
            self.widgetMoved.emit(bl)

    def contextMenuEvent(self, event):
        """Event handler.

        """
        widget = TrayMenu(parent=self.window())
        pos = self.window().mapToGlobal(event.pos())
        widget.move(pos)
        common.move_widget_to_available_geo(widget)
        widget.show()

    def mouseDoubleClickEvent(self, event):
        """Event handler.

        """
        event.accept()
        actions.toggle_maximized()


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


class BookmarksApp(QtWidgets.QApplication):
    """A customized QApplication used by Bookmarks to run in standalone mode.

    The app will start with OpenGL and high dpi support and initializes
    the submodules.

    See :func:`bookmarks.exec`.

    """

    def __init__(self, args):
        _set_application_properties()

        super().__init__([__file__, ])
        _set_application_properties(app=self)
        self.setApplicationVersion(__version__)

        self.setApplicationName(common.product.title())
        self.setOrganizationName(common.organization)
        self.setOrganizationDomain(common.organization_domain)

        self.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

        self._set_model_id()
        self._set_window_icon()
        self.installEventFilter(self)

    def _set_window_icon(self):
        """Set the application icon."""
        path = common.rsc(
            f'{common.GuiResource}{os.path.sep}icon.{common.thumbnail_format}'
        )
        pixmap = QtGui.QPixmap(path)
        icon = QtGui.QIcon(pixmap)
        self.setWindowIcon(icon)

    def _set_model_id(self):
        """Setting this is needed to add custom window icons on windows.
        https://github.com/cztomczak/cefpython/issues/395

        """
        if QtCore.QSysInfo().productType() in ('windows', 'winrt'):
            hresult = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                MODEL_ID
            )
            # An identifier that is globally unique for all apps running on Windows
            assert hresult == 0, "SetCurrentProcessExplicitAppUserModelID failed"

    def eventFilter(self, widget, event):
        """Event filter handler.

        """
        if event.type() == QtCore.QEvent.Enter:
            if hasattr(widget, 'statusTip') and widget.statusTip():
                common.signals.showStatusTipMessage.emit(widget.statusTip())
        if event.type() == QtCore.QEvent.Leave:
            if not common.signals:
                return False
            common.signals.clearStatusBarMessage.emit()

        return False
