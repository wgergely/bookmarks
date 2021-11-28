# -*- coding: utf-8 -*-
"""The editor used to capture a part of the screen to use it as an item's
thumbnail.

"""
import uuid

from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import images


instance = None


def close():
    global instance
    if instance is None:
        return
    try:
        instance.close()
        instance.deleteLater()
    except:
        pass
    instance = None


def show(server=None, job=None, root=None, source=None, proxy=False):
    global instance

    close()
    instance = ScreenCapture(
        server,
        job,
        root,
        source,
        proxy
    )
    instance.open()
    return instance


class ScreenCapture(QtWidgets.QDialog):
    """Screen capture widget.

    Signals:
        captureFinished (str): Emited with a filepath to the captured image.

    """
    captureFinished = QtCore.Signal(str)

    def __init__(self, server, job, root, source, proxy, parent=None):
        super(ScreenCapture, self).__init__(parent=parent)

        self.server = server
        self.job = job
        self.root = root
        self.source = source
        self.proxy = proxy

        self.capture_path = None

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_in = QtCore.QPropertyAnimation(
            effect,
            QtCore.QByteArray('opacity'.encode('utf-8'))
        )
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(0.5)
        self.fade_in.setDuration(500)
        self.fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self._mouse_pos = None
        self._click_pos = None
        self._offset_pos = None

        self._capture_rect = QtCore.QRect()

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setCursor(QtCore.Qt.CrossCursor)

        self.setMouseTracking(True)
        self.installEventFilter(self)

        self._connect_signals()

    def _connect_signals(self):
        self.accepted.connect(self.capture)

    @common.error
    @common.debug
    def capture(self):
        """Capture the screen using the current `capture_rectangle`.

        Saves the resulting pixmap as `png` and emits the `captureFinished`
        signal with the file's path. The slot is called by the dialog's
        accepted signal.

        """
        app = QtWidgets.QApplication.instance()
        if not app:
            return

        screen = app.screenAt(self._capture_rect.topLeft())
        if not screen:
            raise RuntimeError('Unable to find screen.')

        geo = screen.geometry()
        pixmap = screen.grabWindow(
            0,
            self._capture_rect.x() - geo.x(),
            self._capture_rect.y() - geo.y(),
            self._capture_rect.width(),
            self._capture_rect.height()
        )
        if pixmap.isNull():
            raise RuntimeError('Unknown error occured capturing the pixmap.')

        temp_image_path = '{}/{}.{}'.format(
            common.temp_path(),
            uuid.uuid1().hex,
            common.thumbnail_format
        )
        f = QtCore.QFileInfo(temp_image_path)
        if not f.dir().exists():
            if not f.dir().mkpath('.'):
                raise RuntimeError('Could not create temp folder.')

        if not pixmap.save(temp_image_path, format='png', quality=100):
            raise RuntimeError('Could not save the capture.')

        self.captureFinished.emit(temp_image_path)

    @common.error
    @common.debug
    def save_image(self, image):
        if not all((self.server, self.job, self.root, self.source)):
            return
        images.load_thumbnail_from_image(
            self.server,
            self.job,
            self.root,
            self.source,
            image
        )
        QtCore.QFile(self.capture_path).remove()

    def fit_screen_geometry(self):
        """Compute the union of all screen geometries, and resize to fit.

        """
        app = QtWidgets.QApplication.instance()
        geo = app.primaryScreen().geometry()
        x = []
        y = []
        w = 0
        h = 0

        try:
            for screen in app.screens():
                g = screen.geometry()
                x.append(g.topLeft().x())
                y.append(g.topLeft().y())
                w += g.width()
                h += g.height()
            topleft = QtCore.QPoint(
                min(x),
                min(y)
            )
            size = QtCore.QSize(w - min(x), h - min(y))
            geo = QtCore.QRect(topleft, size)
        except:
            pass

        self.setGeometry(geo)

    def paintEvent(self, event):
        # Convert click and current mouse positions to local space.
        if not self._mouse_pos:
            mouse_pos = self.mapFromGlobal(common.cursor.pos())
        else:
            mouse_pos = self.mapFromGlobal(self._mouse_pos)

        click_pos = None
        if self._click_pos is not None:
            click_pos = self.mapFromGlobal(self._click_pos)

        painter = QtGui.QPainter()
        painter.begin(self)

        # Draw background. Aside from aesthetics, this makes the full
        # tool region accept mouse events.
        painter.setBrush(QtGui.QColor(0, 0, 0, 255))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())

        # Clear the capture area
        if click_pos is not None:
            capture_rect = QtCore.QRect(click_pos, mouse_pos)
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode_Clear)
            painter.drawRect(capture_rect)
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode_SourceOver)

        pen = QtGui.QPen(
            QtGui.QColor(255, 255, 255, 64),
            common.size(common.HeightSeparator),
            QtCore.Qt.DotLine
        )
        painter.setPen(pen)

        # Draw cropping markers at click position
        if click_pos is not None:
            painter.drawLine(
                event.rect().left(),
                click_pos.y(),
                event.rect().right(),
                click_pos.y()
            )
            painter.drawLine(
                click_pos.x(),
                event.rect().top(),
                click_pos.x(),
                event.rect().bottom()
            )

        # Draw cropping markers at current mouse position
        painter.drawLine(
            event.rect().left(),
            mouse_pos.y(),
            event.rect().right(),
            mouse_pos.y()
        )
        painter.drawLine(
            mouse_pos.x(),
            event.rect().top(),
            mouse_pos.x(),
            event.rect().bottom()
        )
        painter.end()

    def keyPressEvent(self, event):
        """Cancel the capture on keypress."""
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()

    def mousePressEvent(self, event):
        """Start the capture"""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self._click_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        """Finalise the caputre"""
        if not isinstance(event, QtGui.QMouseEvent):
            return

        if event.button() != QtCore.Qt.NoButton and self._click_pos is not None and self._mouse_pos is not None:
            # End click drag operation and commit the current capture rect
            self._capture_rect = QtCore.QRect(
                self._click_pos,
                self._mouse_pos
            ).normalized()
            self._click_pos = None
            self._offset_pos = None
            self._mouse_pos = None
            self.accept()

    def mouseMoveEvent(self, event):
        """Constrain and resize the capture window."""
        self.update()

        if not isinstance(event, QtGui.QMouseEvent):
            return

        if not self._click_pos:
            return

        self._mouse_pos = event.globalPos()

        app = QtWidgets.QApplication.instance()
        modifiers = app.queryKeyboardModifiers()

        no_modifier = modifiers == QtCore.Qt.NoModifier

        control_modifier = modifiers & QtCore.Qt.ControlModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier

        const_mod = modifiers & QtCore.Qt.ShiftModifier
        move_mod = (not not control_modifier) or (not not alt_modifier)

        if no_modifier:
            self.__click_pos = None
            self._offset_pos = None
            self.update()
            return

        # Allowing the shifting of the rectagle with the modifier keys
        if move_mod:
            if not self._offset_pos:
                self.__click_pos = QtCore.QPoint(self._click_pos)
                self._offset_pos = QtCore.QPoint(event.globalPos())

            self._click_pos = QtCore.QPoint(
                self.__click_pos.x() - (self._offset_pos.x() - event.globalPos().x()),
                self.__click_pos.y() - (self._offset_pos.y() - event.globalPos().y())
            )

        # Shift constrains the rectangle to a square
        if const_mod:
            rect = QtCore.QRect()
            rect.setTopLeft(self._click_pos)
            rect.setBottomRight(event.globalPos())
            rect.setHeight(rect.width())
            self._mouse_pos = rect.bottomRight()

        self.update()

    def showEvent(self, event):
        self.fit_screen_geometry()
        self.fade_in.start()
