# -*- coding: utf-8 -*-
"""The module contains the elements used when initialized in ``StandaloneMode``.

It defines :class:`.BookmarksApp`, Bookmark's custom QApplication, and
:class:`.BookmarksAppWindow`, a modified :class:`.main.MainWidget`.

Note, in ``EmbeddedMode``, Bookmarks uses :class:`.main.MainWidget` as the main
widget.

"""
import os
import ctypes

from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import ui
from . import contextmenu
from . import main

from . import actions
from . import __version__

MODEL_ID = f'{common.product}App'


def init():
    if common.init_mode == common.EmbeddedMode:
        raise RuntimeError("Cannot be initialized in `EmbeddedMode`.")

    if isinstance(common.main_widget, BookmarksAppWindow):
        raise RuntimeError("MainWidget already exists.")
    common.main_widget = BookmarksAppWindow()


def init_tray():
    if not common.tray_widget:
        common.tray_widget = Tray()
        common.tray_widget.show()



@QtCore.Slot()
def show():
    """Shows the main window.

    """
    if common.init_mode != common.StandaloneMode or not isinstance(common.main_widget, BookmarksAppWindow):
        raise RuntimeError('Window can only be show in StandaloneMode.')

    state = common.settings.value(
        common.UIStateSection,
        common.WindowStateKey,
    )
    state = QtCore.Qt.WindowNoState if state is None else QtCore.Qt.WindowState(
        state)

    common.main_widget.activateWindow()
    common.main_widget.restore_window()
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
        QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class TrayMenu(contextmenu.BaseContextMenu):
    """The context menu associated with :class:`.Tray`.

    """

    def __init__(self, parent=None):
        super().__init__(QtCore.QModelIndex(), parent=parent)

        self.stays_on_top = False
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self.setStyleSheet(None)

    def setup(self):
        try:
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

        p = common.get_rsc(f'{common.GuiResource}{os.path.sep}icon.{common.thumbnail_format}')
        pixmap = QtGui.QPixmap(p)
        icon = QtGui.QIcon(pixmap)
        self.setIcon(icon)

        w = TrayMenu(parent=self.window())
        self.setContextMenu(w)

        self.setToolTip(common.product)

        self.activated.connect(self.tray_activated)

    def window(self):
        return common.main_widget.window()

    def tray_activated(self, reason):
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
            (common.color(common.RedColor), common.color(common.TextSecondaryColor)),
            common.size(common.WidthMargin) -
            common.size(common.WidthIndicator),
            description='Click to minimize the window...',
            parent=parent
        )


class CloseButton(ui.ClickableIconButton):
    """Button used to close/hide a widget or window."""

    def __init__(self, parent=None):
        super().__init__(
            'close',
            (common.color(common.RedColor), common.color(common.TextSecondaryColor)),
            common.size(common.WidthMargin) -
            common.size(common.WidthIndicator),
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
            QtWidgets.QApplication.instance().doubleClickInterval())
        self.double_click_timer.setSingleShot(True)

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setFixedHeight(common.size(common.WidthMargin) +
                            (common.size(common.WidthIndicator) * 2))

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
        self.layout().addSpacing(common.size(common.WidthIndicator) * 2)
        self.layout().addWidget(CloseButton(parent=self))
        self.layout().addSpacing(common.size(common.WidthIndicator) * 2)

    def mousePressEvent(self, event):
        """Custom ``movePressEvent``.
        We're setting the properties needed to moving the main window.

        """
        if self.double_click_timer.isActive():
            return
        if not isinstance(event, QtGui.QMouseEvent):
            return

        self.double_click_timer.start(self.double_click_timer.interval())
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(
            self.geometry().topLeft())

    def mouseMoveEvent(self, event):
        """Moves the the parent window when clicked.

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
        """Shows the context menu associated with the tray in the header."""
        widget = TrayMenu(parent=self.window())
        pos = self.window().mapToGlobal(event.pos())
        widget.move(pos)
        common.move_widget_to_available_geo(widget)
        widget.show()

    def mouseDoubleClickEvent(self, event):
        event.accept()
        actions.toggle_maximized()


class BookmarksAppWindow(main.MainWidget):
    """The main application window is an adapted
    :class:`bookmarks.main.MainWidget` that adds custom sizing and frameless
    mode.

    Custom resizing and positioning is implemented using the
    :func:`mousePressEvent`, :func:`mouseMoveEvent` and
    :func:`mouseReleaseEvent` methods.

    """

    def __init__(self, parent=None):
        if isinstance(common.main_widget, self.__class__):
            raise RuntimeError(f'{self.__class__.__name__} already exists.')

        super().__init__(parent=None)

        self._frameless = False
        self._ontop = False
        self.headerwidget = None

        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None
        self.resize_overlay = None
        self.resize_distance = QtWidgets.QApplication.instance().startDragDistance() * 2
        self.resize_override_icons = {
            1: QtCore.Qt.SizeFDiagCursor,
            2: QtCore.Qt.SizeBDiagCursor,
            3: QtCore.Qt.SizeBDiagCursor,
            4: QtCore.Qt.SizeFDiagCursor,
            5: QtCore.Qt.SizeVerCursor,
            6: QtCore.Qt.SizeHorCursor,
            7: QtCore.Qt.SizeVerCursor,
            8: QtCore.Qt.SizeHorCursor,
        }

        common.set_custom_stylesheet(self)

        self.installEventFilter(self)
        self.setMouseTracking(True)

        self.aboutToInitialize.connect(self.init_header)
        self.aboutToInitialize.connect(self.toggle_header)
        self.initialized.connect(self._connect_standalone_signals)
        self.initialized.connect(init_tray)

        self.adjustSize()
        self.update_window_flags()

    @QtCore.Slot()
    def init_header(self):
        """Adds a header widget used to move the window around when the
        *frameless* mode is on.

        """
        self.headerwidget = HeaderWidget(parent=self)
        self.layout().insertWidget(0, self.headerwidget, 1)
        self.headerwidget.setHidden(True)

    @QtCore.Slot()
    def toggle_header(self):
        """Adjust the header visibility based on the current window flags."""
        if self._frameless and self.layout():
            self.headerwidget.setHidden(False)
            o = common.size(common.WidthIndicator)
            self.layout().setContentsMargins(o, o, o, o)
        elif not self._frameless and self.layout():
            self.headerwidget.setHidden(True)
            self.layout().setContentsMargins(0, 0, 0, 0)

    def update_window_flags(self, v=None):
        """Load previously saved window flag values from user common.

        """
        self._frameless = common.settings.value(
            common.UIStateSection,
            common.WindowFramelessKey,
        )

        if not self._frameless:
            self.setWindowFlags(
                self.windowFlags() & ~ QtCore.Qt.FramelessWindowHint)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground, False)
        else:
            self.setWindowFlags(
                self.windowFlags() |
                QtCore.Qt.FramelessWindowHint
            )
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)

        self._ontop = common.settings.value(
            common.UIStateSection,
            common.WindowAlwaysOnTopKey
        )

        if self._ontop:
            self.setWindowFlags(
                self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(
                self.windowFlags() & ~ QtCore.Qt.WindowStaysOnTopHint)

    def _paint_background(self, painter):
        if not self._frameless:
            super()._paint_background(painter)
            return

        rect = QtCore.QRect(self.rect())
        pen = QtGui.QPen(QtGui.QColor(35, 35, 35, 255))
        pen.setWidth(common.size(common.HeightSeparator) * 2)
        painter.setPen(pen)
        painter.setBrush(common.color(common.SeparatorColor).darker(110))

        o = common.size(common.WidthIndicator)
        rect = rect.adjusted(o, o, -o, -o)
        painter.drawRoundedRect(rect, o * 3, o * 3)

    @common.error
    @common.debug
    @QtCore.Slot()
    def save_window(self, *args, **kwargs):
        common.settings.setValue(
            common.UIStateSection,
            common.WindowGeometryKey,
            self.saveGeometry()
        )
        common.settings.setValue(
            common.UIStateSection,
            common.WindowStateKey,
            int(self.windowState())
        )

    @common.error
    @common.debug
    def restore_window(self, *args, **kwargs):
        geometry = common.settings.value(
            common.UIStateSection,
            common.WindowGeometryKey,
        )
        if geometry is not None:
            self.restoreGeometry(geometry)

    def _get_offset_rect(self, offset):
        """Returns an expanded/contracted edge rectangle based on the widget's
        geomtery. Used to get the valid area for resize-operations."""
        rect = self.rect()
        center = rect.center()
        rect.setHeight(rect.height() + offset)
        rect.setWidth(rect.width() + offset)
        rect.moveCenter(center)
        return rect

    def _accept_resize_event(self, event):
        """Returns `True` if the event can be a window resize event."""
        if self._get_offset_rect(self.resize_distance * -1).contains(event.pos()):
            return False
        if not self._get_offset_rect(self.resize_distance).contains(event.pos()):
            return False
        return True

    def _set_resize_icon(self, event, clamp=True):
        """Sets an override icon to indicate the draggable area."""
        app = QtWidgets.QApplication.instance()
        k = self._get_resize_hotspot(event, clamp=clamp)
        if k:
            self.grabMouse()
            icon = self.resize_override_icons[k]
            if app.overrideCursor():
                app.changeOverrideCursor(QtGui.QCursor(icon))
                return k
            app.restoreOverrideCursor()
            app.setOverrideCursor(QtGui.QCursor(icon))
            return k
        self.releaseMouse()
        app.restoreOverrideCursor()
        return k

    def _get_resize_hotspot(self, event, clamp=True):
        """Returns the resizable area from the event's current position.
        If clamp is True we will only check in near the areas near the edges.

        """
        if clamp:
            if not self._accept_resize_event(event):
                return None

        # First we have to define the 8 areas showing an indicator icon when
        # hovered. Edges:
        rect = self.rect()
        p = event.pos()
        edge_hotspots = {
            5: QtCore.QPoint(p.x(), rect.top()),
            6: QtCore.QPoint(rect.right(), p.y()),
            7: QtCore.QPoint(p.x(), rect.bottom()),
            8: QtCore.QPoint(rect.left(), p.y()),
        }

        # Corners:
        topleft_corner = QtCore.QRect(0, 0,
                                      self.resize_distance, self.resize_distance)
        topright_corner = QtCore.QRect(topleft_corner)
        topright_corner.moveRight(rect.width())
        bottomleft_corner = QtCore.QRect(topleft_corner)
        bottomleft_corner.moveTop(rect.height() - self.resize_distance)
        bottomright_corner = QtCore.QRect(topleft_corner)
        bottomright_corner.moveRight(rect.width())
        bottomright_corner.moveTop(rect.height() - self.resize_distance)

        corner_hotspots = {
            1: topleft_corner,
            2: topright_corner,
            3: bottomleft_corner,
            4: bottomright_corner,
        }

        # We check if the cursor is currently inside one of the corners or edges
        if any([f.contains(p) for f in corner_hotspots.values()]):
            return max(corner_hotspots, key=lambda k: corner_hotspots[k].contains(p))
        return min(edge_hotspots, key=lambda k: (p - edge_hotspots[k]).manhattanLength())

    @QtCore.Slot()
    def _connect_standalone_signals(self):
        """Extra signal connections when Bookmarks runs in standalone mode.

        """
        self.headerwidget.widgetMoved.connect(self.save_window)
        self.headerwidget.findChild(MinimizeButton).clicked.connect(
            actions.toggle_minimized)
        self.headerwidget.findChild(CloseButton).clicked.connect(
            common.uninitialize)

        self.files_widget.activated.connect(actions.execute)
        self.favourites_widget.activated.connect(actions.execute)

    def hideEvent(self, event):
        """Custom hide event."""
        self.save_window()
        super().hideEvent(event)

    def closeEvent(self, event):
        """Bookmarks won't close when the main window is closed.
        Instead, it will be hidden to the taskbar and a pop up notice will be shown to the user.

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
        self.save_window()

    def mousePressEvent(self, event):
        """The mouse press event responsible for setting the properties needed
        by the custom resize methods.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            event.ignore()
            return

        if self._accept_resize_event(event):
            self.resize_area = self._set_resize_icon(event, clamp=False)
            self.resize_initial_pos = event.pos()
            self.resize_initial_rect = self.rect()
            event.accept()
            return

        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None
        event.ignore()

    def mouseMoveEvent(self, event):
        """Custom mouse move event responsible for resizing the frameless
        widget's geometry.

        It identifies the dragable edge area, and sets the cursor overrides.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            return

        if self.resize_initial_pos == QtCore.QPoint(-1, -1):
            self._set_resize_icon(event, clamp=True)
            return

        if self.resize_area is None:
            return

        o = event.pos() - self.resize_initial_pos
        geo = self.geometry()

        g_topleft = self.mapToGlobal(
            self.resize_initial_rect.topLeft())
        g_bottomright = self.mapToGlobal(
            self.resize_initial_rect.bottomRight())

        if self.resize_area in (1, 2, 5):
            geo.setTop(g_topleft.y() + o.y())
        if self.resize_area in (3, 4, 7):
            geo.setBottom(g_bottomright.y() + o.y())
        if self.resize_area in (1, 3, 8):
            geo.setLeft(g_topleft.x() + o.x())
        if self.resize_area in (2, 4, 6):
            geo.setRight(g_bottomright.x() + o.x())

        original_geo = self.geometry()
        self.move(geo.topLeft())
        self.setGeometry(geo)
        if self.geometry().width() > geo.width():
            self.setGeometry(original_geo)

    def mouseReleaseEvent(self, event):
        """Resets the custom resize properties to their initial values.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            event.ignore()
            return

        if self.resize_initial_pos != QtCore.QPoint(-1, -1):
            self.save_window()
            if hasattr(common.widget(), 'reset'):
                common.widget().reset()

        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None

        app = QtWidgets.QApplication.instance()
        app.restoreOverrideCursor()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            self.save_window()

    def showEvent(self, event):
        if not self.is_initialized:
            QtCore.QTimer.singleShot(100, self.initialize)


class BookmarksApp(QtWidgets.QApplication):
    """A customized QApplication used by Bookmarks to run in standalone mode.

    The app will start with OpenGL and high dpi support and initializes
    the submodules.

    See :func:`bookmarks.exec_`.

    """

    def __init__(self, args):
        _set_application_properties()
        super().__init__(args)
        _set_application_properties(app=self)
        self.setApplicationVersion(__version__)
        self.setApplicationName(common.product)
        self.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, bool=True)

        self._set_model_id()
        self._set_window_icon()
        self.installEventFilter(self)

    def _set_window_icon(self):
        """Set the application icon."""
        path = common.get_rsc(f'{common.GuiResource}{os.path.sep}icon.{common.thumbnail_format}')
        pixmap = QtGui.QPixmap(path)
        icon = QtGui.QIcon(pixmap)
        self.setWindowIcon(icon)

    def _set_model_id(self):
        """Setting this is needed to add custom window icons on windows.
        https://github.com/cztomczak/cefpython/issues/395

        """
        if QtCore.QSysInfo().productType() in ('windows', 'winrt'):
            hresult = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                MODEL_ID)
            # An identifier that is globally unique for all apps running on Windows
            assert hresult == 0, "SetCurrentProcessExplicitAppUserModelID failed"

    def eventFilter(self, widget, event):
        if event.type() == QtCore.QEvent.Enter:
            if hasattr(widget, 'statusTip') and widget.statusTip():
                common.signals.showStatusTipMessage.emit(widget.statusTip())
        if event.type() == QtCore.QEvent.Leave:
            common.signals.clearStatusBarMessage.emit()

        return False
