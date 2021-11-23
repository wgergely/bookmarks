# -*- coding: utf-8 -*-
"""Widgets required to run Bookmarks in standalone-mode.

"""
import ctypes
from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import ui
from . import contextmenu
from . import main
from . import settings
from . import images
from . import actions
from . import __version__

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseOpenGLES, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

_instance = None
_tray_instance = None


@QtCore.Slot()
def show():
    """Shows the main window.

    """
    global _instance
    if not _instance:
        _instance = StandaloneMainWidget()

    state = settings.instance().value(
        settings.UIStateSection,
        settings.WindowStateKey,
    )
    state = QtCore.Qt.WindowNoState if state is None else QtCore.Qt.WindowState(state)

    _instance.activateWindow()
    _instance.restore_window()
    if state == QtCore.Qt.WindowNoState:
        _instance.showNormal()
    elif state & QtCore.Qt.WindowMaximized:
        _instance.showMaximized()
    elif state & QtCore.Qt.WindowFullScreen:
        _instance.showFullScreen()
    else:
        _instance.showNormal()


def instance():
    return _instance



class TrayMenu(contextmenu.BaseContextMenu):
    """The context-menu associated with the our custom tray menu.

    """

    def __init__(self, parent=None):
        super(TrayMenu, self).__init__(QtCore.QModelIndex(), parent=parent)

        self.stays_on_top = False
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

    def setup(self):
        self.window_menu()
        self.separator()
        self.tray_menu()

    def tray_menu(self):
        """Actions associated with the visibility of the widget."""
        self.menu['Quit'] = {
            'action': actions.quit,
        }
        return


class MinimizeButton(ui.ClickableIconButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(MinimizeButton, self).__init__(
            'minimize',
            (common.RED, common.SECONDARY_TEXT),
            common.MARGIN() - common.INDICATOR_WIDTH(),
            description='Click to minimize the window...',
            parent=parent
        )


class CloseButton(ui.ClickableIconButton):
    """Button used to close/hide a widget or window."""

    def __init__(self, parent=None):
        super(CloseButton, self).__init__(
            'close',
            (common.RED, common.SECONDARY_TEXT),
            common.MARGIN() - common.INDICATOR_WIDTH(),
            description='Click to close the window...',
            parent=parent
        )


class HeaderWidget(QtWidgets.QWidget):
    """Horizontal widget for controlling the position of the active window."""
    widgetMoved = QtCore.Signal(QtCore.QPoint)

    def __init__(self, parent=None):
        super(HeaderWidget, self).__init__(parent=parent)
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
        self.setFixedHeight(common.MARGIN() +
                            (common.INDICATOR_WIDTH() * 2))

        self._create_ui()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        menu_bar = QtWidgets.QMenuBar(parent=self)
        self.layout().addWidget(menu_bar)
        menu_bar.hide()
        menu = menu_bar.addMenu(common.PRODUCT)

        action = menu.addAction('Quit')
        action.triggered.connect(actions.quit)

        self.layout().addStretch()
        self.layout().addWidget(MinimizeButton(parent=self))
        self.layout().addSpacing(common.INDICATOR_WIDTH() * 2)
        self.layout().addWidget(CloseButton(parent=self))
        self.layout().addSpacing(common.INDICATOR_WIDTH() * 2)

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


class StandaloneMainWidget(main.MainWidget):
    """Modified ``MainWidget``adapted to run as a standalone
    application, with or without window borders.

    When the window mode is 'frameless' the ``HeaderWidget`` is used to move the
    window around.

    """

    def __init__(self, parent=None):
        """Init method.

        Adding the `HeaderWidget` here - this is the widget responsible for
        moving the widget around and providing the close and hide buttons.

        Also, the properties necessary to resize the frameless window are also
        defines here. These properties work in conjunction with the mouse events

        """
        global _instance
        if _instance is not None:
            raise RuntimeError(
                '{} cannot be initialised more than once.'.format(self.__class__.__name__))
        _instance = self

        super(StandaloneMainWidget, self).__init__(parent=None)

        self.tray = None
        self._frameless = False
        self._ontop = False
        self.headerwidget = None

        common.set_custom_stylesheet(self)

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

        self.installEventFilter(self)
        self.setMouseTracking(True)

        self.connectExtraSignals.connect(self.connect_extra_signals)
        self.connectExtraSignals.connect(self.update_layout)

        self.adjustSize()
        self.init_window_flags()
        self.init_tray()

    def _create_ui(self):
        super(StandaloneMainWidget, self)._create_ui()

        self.headerwidget = HeaderWidget(parent=self)
        self.layout().insertWidget(0, self.headerwidget, 1)
        self.headerwidget.setHidden(True)

    def update_layout(self):
        if self._frameless and self.layout():
            self.headerwidget.setHidden(False)
            o = common.INDICATOR_WIDTH()
            self.layout().setContentsMargins(o, o, o, o)
        elif not self._frameless and self.layout():
            self.headerwidget.setHidden(True)
            self.layout().setContentsMargins(0, 0, 0, 0)

    def init_window_flags(self, v=None):
        self._frameless = settings.instance().value(
            settings.UIStateSection,
            settings.WindowFramelessKey,
        )
        if self._frameless:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.FramelessWindowHint)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground, False)

        self._ontop = settings.instance().value(
            settings.UIStateSection,
            settings.WindowAlwaysOnTopKey
        )
        if self._ontop:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)

    def init_tray(self):
        pixmap = images.ImageCache.get_rsc_pixmap(
            'logo_bw', None, common.ROW_HEIGHT() * 7.0)
        icon = QtGui.QIcon(pixmap)

        self.tray = QtWidgets.QSystemTrayIcon(parent=self)
        self.tray.setIcon(icon)
        self.tray.setContextMenu(TrayMenu(parent=self))
        self.tray.setToolTip(common.PRODUCT)

        self.tray.activated.connect(self.trayActivated)

        self.tray.show()

    def _paint_background(self, painter):
        if not self._frameless:
            super(StandaloneMainWidget, self)._paint_background(painter)
            return

        rect = QtCore.QRect(self.rect())
        pen = QtGui.QPen(QtGui.QColor(35, 35, 35, 255))
        pen.setWidth(common.ROW_SEPARATOR() * 2)
        painter.setPen(pen)
        painter.setBrush(common.SEPARATOR.darker(110))

        o = common.INDICATOR_WIDTH()
        rect = rect.adjusted(o, o, -o, -o)
        painter.drawRoundedRect(rect, o * 3, o * 3)

    @common.error
    @common.debug
    @QtCore.Slot()
    def save_window(self, *args, **kwargs):
        """Saves window's position to the local settings."""
        settings.instance().setValue(
            settings.UIStateSection,
            settings.WindowGeometryKey,
            self.saveGeometry()
        )
        settings.instance().setValue(
            settings.UIStateSection,
            settings.WindowStateKey,
            int(self.windowState())
        )

    @common.error
    @common.debug
    def restore_window(self, *args, **kwargs):
        geometry = settings.instance().value(
            settings.UIStateSection,
            settings.WindowGeometryKey,
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

    def accept_resize_event(self, event):
        """Returns `True` if the event can be a window resize event."""
        if self._get_offset_rect(self.resize_distance * -1).contains(event.pos()):
            return False
        if not self._get_offset_rect(self.resize_distance).contains(event.pos()):
            return False
        return True

    def set_resize_icon(self, event, clamp=True):
        """Sets an override icon to indicate the draggable area."""
        app = QtWidgets.QApplication.instance()
        k = self.get_resize_hotspot(event, clamp=clamp)
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

    def get_resize_hotspot(self, event, clamp=True):
        """Returns the resizable area from the event's current position.
        If clamp is True we will only check in near the areas near the edges.

        """
        if clamp:
            if not self.accept_resize_event(event):
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
    def connect_extra_signals(self):
        """Modifies layout for display in standalone-mode."""
        self.headerwidget.widgetMoved.connect(self.save_window)
        self.headerwidget.findChild(MinimizeButton).clicked.connect(
            actions.toggle_minimized)
        self.headerwidget.findChild(CloseButton).clicked.connect(
            actions.quit)

        self.fileswidget.activated.connect(actions.execute)
        self.favouriteswidget.activated.connect(actions.execute)

    def trayActivated(self, reason):
        """Slot called by the QSystemTrayIcon when clicked."""
        if reason == QtWidgets.QSystemTrayIcon.Unknown:
            self.show()
            self.activateWindow()
            self.raise_()
        if reason == QtWidgets.QSystemTrayIcon.Context:
            return
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
            self.raise_()
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            return
        if reason == QtWidgets.QSystemTrayIcon.MiddleClick:
            return

    def hideEvent(self, event):
        """Custom hide event."""
        self.save_window()
        super(StandaloneMainWidget, self).hideEvent(event)

    def closeEvent(self, event):
        """Custom close event will minimize the widget to the tray."""
        event.ignore()
        self.hide()
        self.tray.showMessage(
            'Bookmarks',
            'Bookmarks will continue running in the background, you can use this icon to restore it\'s visibility.',
            QtWidgets.QSystemTrayIcon.Information,
            3000
        )
        self.save_window()

    def mousePressEvent(self, event):
        """The mouse press event responsible for setting the properties needed
        by the resize methods.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            event.ignore()
            return

        if self.accept_resize_event(event):
            self.resize_area = self.set_resize_icon(event, clamp=False)
            self.resize_initial_pos = event.pos()
            self.resize_initial_rect = self.rect()
            event.accept()
            return

        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None
        event.ignore()

    def mouseMoveEvent(self, event):
        """Custom mouse move event - responsible for resizing the frameless
        widget's geometry.
        It identifies the dragable edge area, sets the cursor override.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            return

        if self.resize_initial_pos == QtCore.QPoint(-1, -1):
            self.set_resize_icon(event, clamp=True)
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
        """Restores the mouse resize properties."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not self.window().windowFlags() & QtCore.Qt.FramelessWindowHint:
            event.ignore()
            return

        if self.resize_initial_pos != QtCore.QPoint(-1, -1):
            self.save_window()
            if hasattr(self.stackedwidget.currentWidget(), 'reset'):
                self.stackedwidget.currentWidget().reset()

        self.resize_initial_pos = QtCore.QPoint(-1, -1)
        self.resize_initial_rect = None
        self.resize_area = None

        app = QtWidgets.QApplication.instance()
        app.restoreOverrideCursor()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            self.save_window()

    def showEvent(self, event):
        QtCore.QTimer.singleShot(100, self.initialize)

class StandaloneApp(QtWidgets.QApplication):
    """This is the app used to run the browser as a standalone widget."""
    MODEL_ID = '{}App'.format(common.PRODUCT)

    def __init__(self, args):
        super(StandaloneApp, self).__init__(args)

        self.setApplicationVersion(__version__)
        self.setApplicationName(common.PRODUCT)

        self.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, bool=True)
        self.set_model_id()
        self.init_modules()
        self.set_window_icon()

        self.installEventFilter(self)

    def init_modules(self):
        common.init_signals()
        common.init_standalone()
        common.init_dirs_dir()
        common.init_settings()
        common.init_ui_scale()
        common.init_resources()
        common.init_session_lock()
        common.init_font_db()
        common.init_pixel_ratio()

    def set_window_icon(self):
        pixmap = images.ImageCache.get_rsc_pixmap(
            'icon', None, common.ROW_HEIGHT() * 7.0)
        icon = QtGui.QIcon(pixmap)
        self.setWindowIcon(icon)


    def set_model_id(self):
        """Setting this is needed to add custom window icons on windows.
        https://github.com/cztomczak/cefpython/issues/395

        """
        if QtCore.QSysInfo().productType() in ('windows', 'winrt'):
            hresult = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.MODEL_ID)
            # An identifier that is globally unique for all apps running on Windows
            assert hresult == 0, "SetCurrentProcessExplicitAppUserModelID failed"

    def eventFilter(self, widget, event):
        if event.type() == QtCore.QEvent.Enter:
            if hasattr(widget, 'statusTip') and widget.statusTip():
                common.signals.showStatusTipMessage.emit(widget.statusTip())
        if event.type() == QtCore.QEvent.Leave:
            common.signals.clearStatusBarMessage.emit()

        return False
