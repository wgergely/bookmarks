# -*- coding: utf-8 -*-
"""A pop-up widget used to display an image preview of a selected item.

"""
import weakref

from PySide2 import QtCore, QtWidgets, QtGui

from ... import common
from ... import images


def show(path, ref, parent, oiio=False, max_size=-1):
    k = repr(parent)
    if k not in common.VIEWER_WIDGET_CACHE:
        common.VIEWER_WIDGET_CACHE[k] = ImageViewer(parent=parent)

    common.VIEWER_WIDGET_CACHE[k].show()
    common.VIEWER_WIDGET_CACHE[k].set_image(path, ref, max_size=max_size, oiio=oiio)


def get_item_info(ref):
    info = []

    if not ref or not ref():
        return info

    s = ref()[common.PathRole]
    s = s if isinstance(s, str) else ''
    info.append((common.color(common.TextColor), s if s else ''))

    if not ref or not ref():
        return info

    s = ref()[common.DescriptionRole]
    s = s if isinstance(s, str) else ''
    info.append((common.color(common.GreenColor), s if s else ''))

    if not ref or not ref():
        return info

    s = ref()[common.FileDetailsRole]
    s = s if isinstance(s, str) else ''
    s = '   |   '.join(s.split(';')) if s else '-'
    info.append((common.color(common.TextColor), s if s else '-'))

    if not ref or not ref():
        return info

    s = ref()[common.PathRole]
    s = common.get_sequence_end_path(s)

    buf = images.oiio_get_buf(s)
    if not buf:
        return info

    s = buf.spec().serialize()
    if not s:
        return
    for n, _s in enumerate([f.strip() for f in s.split('\n') if f]):
        if n > 32:
            break
        info.append((common.color(common.TextSecondaryColor), _s if _s else ''))

    return info


class Viewer(QtWidgets.QGraphicsView):
    """The graphics view used to display a QPixmap.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._track = True
        self._pos = None

        self.item = QtWidgets.QGraphicsPixmapItem()
        self.item.setTransformationMode(QtCore.Qt.SmoothTransformation)
        self.item.setShapeMode(QtWidgets.QGraphicsPixmapItem.MaskShape)

        self.setScene(QtWidgets.QGraphicsScene(parent=self))

        self.scene().addItem(self.item)

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setBackgroundBrush(QtGui.QColor(0, 0, 0, 0))
        self.setInteractive(True)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        self.setMouseTracking(True)

    def paintEvent(self, event):
        """Custom paint event"""
        super().paintEvent(event)

        painter = QtGui.QPainter()
        painter.begin(self.viewport())
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        o = common.size(common.WidthMargin)
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))

        font, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium)
        )
        rect.setHeight(metrics.height())

        for color, text in get_item_info(self.parent()._ref):
            common.draw_aliased_text(
                painter, font, QtCore.QRect(
                    rect
                ), text, QtCore.Qt.AlignLeft, color
            )
            rect.moveTop(rect.center().y() + metrics.lineSpacing())

        painter.end()

    def wheelEvent(self, event):
        # Zoom Factor
        zoom_in_factor = 1.25
        zoom_out_factor = 1.0 / zoom_in_factor

        # Set Anchors
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)

        # Save the scene pos
        original_pos = self.mapToScene(event.pos())

        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

        # Get the new position
        new_position = self.mapToScene(event.pos())

        # Move scene to old position
        delta = new_position - original_pos
        self.translate(delta.x(), delta.y())

    def keyPressEvent(self, event):
        event.ignore()


class ImageViewer(QtWidgets.QWidget):
    """The top-level widget containing the QGraphicsScene items.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.viewer = None
        self._source = None
        self._ref = None

        self._create_ui()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)

        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        self.viewer = Viewer(parent=self)
        self.layout().addWidget(self.viewer, 1)

    @QtCore.Slot(str)
    @QtCore.Slot(weakref.ref)
    def set_image(self, source, ref, max_size=-1, oiio=False):
        """Loads an image and displays the contents as a QPixmap item.

        """
        self.viewer.item.setPixmap(QtGui.QPixmap())

        self._source = source
        self._ref = ref

        if (
                oiio is False and
                QtCore.QFileInfo(source).suffix().lower() not in images.QT_IMAGE_FORMATS
        ):
            raise RuntimeError('Qt cannot display the source image.')

        # Wait for the thread to finish loading the thumbnail
        images.wait_for_lock(source)
        with images.lock:
            pixmap = images.ImageCache.get_pixmap(source, -1, oiio=oiio)

        if pixmap and not pixmap.isNull():
            with images.lock:
                images.ImageCache.flush(source)

            self.viewer.scale(1.0, 1.0)
            self.viewer.setSceneRect(self.rect())
            self.viewer.scene().setSceneRect(self.rect())
            self.viewer.item.setPixmap(pixmap)
            self.viewer.repaint()

        br = self.viewer.item.sceneBoundingRect()
        self.viewer.item.setPos(
            self.window().rect().center().x() - (br.width() / 2),
            self.window().rect().center().y() - (br.height() / 2)
        )

    def keyPressEvent(self, event):
        """Catching and forward key press events."""
        event.accept()

        if event.key() == QtCore.Qt.Key_Down:
            self.parent().key_down()
            self.parent().key_space()
        elif event.key() == QtCore.Qt.Key_Up:
            self.parent().key_up()
            self.parent().key_space()
        elif event.key() == QtCore.Qt.Key_Tab:
            self.parent().key_up()
            self.parent().key_space()
        elif event.key() == QtCore.Qt.Key_Backtab:
            self.parent().key_down()
            self.parent().key_space()
        elif event.key() == QtCore.Qt.Key_Escape:
            self.hide()
        elif event.key() == QtCore.Qt.Key_Space:
            self.hide()
        elif event.key() == QtCore.Qt.Key_Enter:
            self.hide()

    def showEvent(self, event):
        common.fit_screen_geometry(self)
