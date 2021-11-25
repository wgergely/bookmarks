# -*- coding: utf-8 -*-
"""Widget used to display a preview of the current item.

For Bookmarks and Asset items, this is the current thumbnail, however, for image
files, we'll use OpenImageIO to open and display the image in a `QGraphicsView`.


"""
import weakref
import functools

import OpenImageIO
from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import images


CACHE = {}


def show(path, ref, parent):
    k = repr(parent)
    if k not in CACHE:
        CACHE[k] = ImageViewer(parent=parent)

    CACHE[k].show()
    QtCore.QTimer.singleShot(1, functools.partial(CACHE[k].set_image, path, ref))


def get_item_info(ref):
    info = []

    if not ref or not ref():
        return info

    s = ref()[QtCore.Qt.StatusTipRole]
    s = s if isinstance(s, str) else ''
    info.append((common.TEXT, s if s else ''))

    if not ref or not ref():
        return info

    s = ref()[common.DescriptionRole]
    s = s if isinstance(s, str) else ''
    info.append((common.GREEN, s if s else ''))

    if not ref or not ref():
        return info

    s = ref()[common.FileDetailsRole]
    s = s if isinstance(s, str) else ''
    s = '   |   '.join(s.split(';')) if s else '-'
    info.append((common.TEXT, s if s else '-'))

    if not ref or not ref():
        return info

    s = ref()[QtCore.Qt.StatusTipRole]
    s = common.get_sequence_endpath(s)

    buf = images.oiio_get_buf(s)
    if not buf:
        return info

    s = buf.spec().serialize()
    if not s:
        return
    for n, _s in enumerate([f.strip() for f in s.split('\n') if f]):
        if n > 32:
            break
        info.append((common.SECONDARY_TEXT, _s if _s else ''))

    return info



class Viewer(QtWidgets.QGraphicsView):
    """The graphics view used to display a QPixmap read using OpenImageIO.

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

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        """Custom paint event"""
        super().paintEvent(event)

        painter = QtGui.QPainter()
        painter.begin(self.viewport())
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        o = common.MARGIN()
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))

        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        rect.setHeight(metrics.height())

        for color, text in get_item_info(self.parent()._ref):
            common.draw_aliased_text(painter, font, QtCore.QRect(
                rect), text, QtCore.Qt.AlignLeft, color)
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
    """Used to view an image.

    The image data is loaded using OpenImageIO and is then wrapped in a QGraphicsScene,
    using a QPixmap. See ``Viewer``.

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
        height = common.ROW_HEIGHT() * 0.6
        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        def get_row(parent=None):
            row = QtWidgets.QWidget(parent=parent)
            row.setFixedHeight(height)
            QtWidgets.QHBoxLayout(row)
            row.layout().setContentsMargins(0, 0, 0, 0)
            row.layout().setSpacing(0)
            parent.layout().addWidget(row)
            row.setStyleSheet('background-color: rgba(0, 0, 0, 255);')
            return row

        self.viewer = Viewer(parent=self)
        self.layout().addWidget(self.viewer, 1)

    @QtCore.Slot(str)
    @QtCore.Slot(weakref.ref)
    def set_image(self, source, ref):
        """Loads an image using OpenImageIO and displays the contents as a
        QPixmap item.

        """
        self._source = source
        self._ref = ref

        oiio = QtCore.QFileInfo(source).suffix().lower() in images.QT_IMAGE_FORMATS
        pixmap = images.ImageCache.get_pixmap(source, -1, oiio=oiio)

        # Wait for the thread to finish loading the thumbnail
        images.wait_for_lock(source)

        if pixmap and not pixmap.isNull():
            images.ImageCache.flush(source)
            self.viewer.item.setPixmap(pixmap)
            self.viewer.repaint()
            return

        size = self.viewer.item.pixmap().size()
        if size.height() > self.height() or size.width() > self.width():
            self.fitInView(self.viewer.item, QtCore.Qt.KeepAspectRatio)


    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidth(common.ROW_SEPARATOR())
        painter.setPen(pen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        #
        # color = images.ImageCache.get_color(self.path)
        # if not color:
        #     color = images.ImageCache.make_color(self.path)
        # if not color:
        #     color = QtGui.QColor(20, 20, 20, 240)

        painter.setBrush(common.SEPARATOR)
        painter.drawRect(self.rect())

        painter.end()

    def mousePressEvent(self, event):
        event.accept()
        self.hide()

    def keyPressEvent(self, event):
        """We're mapping the key press events to the parent list."""
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
        else:
            self.hide()


    def showEvent(self, event):
        common.fit_screen_geometry(self)
