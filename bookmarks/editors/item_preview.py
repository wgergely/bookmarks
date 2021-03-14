# -*- coding: utf-8 -*-
"""Widget used to display a preview of the current item.

For Bookmarks and Asset items, this is the current thumbnail, however, for image
files, we'll use OpenImageIO to open and display the image in a `QGraphicsView`.


"""
import OpenImageIO
from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import ui
from .. import images
from .. import log


class Viewer(QtWidgets.QGraphicsView):
    """The graphics view used to display a QPixmap read using OpenImageIO.

    """

    def __init__(self, parent=None):
        super(Viewer, self).__init__(parent=parent)
        self.item = QtWidgets.QGraphicsPixmapItem()
        self.item.setTransformationMode(QtCore.Qt.SmoothTransformation)
        self.setScene(QtWidgets.QGraphicsScene(parent=self))
        self.scene().addItem(self.item)

        self._track = True
        self._pos = None

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setBackgroundBrush(QtGui.QColor(0, 0, 0, 0))
        self.setInteractive(True)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

    def index(self):
        return self.parent().index()

    def paintEvent(self, event):
        """Custom paint event"""
        super(Viewer, self).paintEvent(event)

        index = self.index()
        if not index.isValid():
            return

        painter = QtGui.QPainter()
        painter.begin(self.viewport())

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.MARGIN()
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))

        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        rect.setHeight(metrics.height())

        # Filename
        text = index.data(QtCore.Qt.StatusTipRole)
        if text:
            common.draw_aliased_text(painter, font, QtCore.QRect(
                rect), text, QtCore.Qt.AlignLeft, common.TEXT)
            rect.moveTop(rect.center().y() + metrics.lineSpacing())

        text = index.data(common.DescriptionRole)
        if text:
            text = text if text else u''
            common.draw_aliased_text(painter, font, QtCore.QRect(
                rect), text, QtCore.Qt.AlignLeft, common.BLUE)
            rect.moveTop(rect.center().y() + metrics.lineSpacing())
        text = index.data(common.FileDetailsRole)
        if text:
            text = u'{}'.format(text)
            text = u'   |   '.join(text.split(u';')) if text else u'-'
            common.draw_aliased_text(painter, font, QtCore.QRect(
                rect), text, QtCore.Qt.AlignLeft, common.TEXT)
            rect.moveTop(rect.center().y() + metrics.lineSpacing())

        # Image info
        ext = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole)).suffix()
        if ext.lower() in images.get_oiio_extensions():
            font, metrics = common.font_db.secondary_font(
                common.SMALL_FONT_SIZE())

            path = index.data(QtCore.Qt.StatusTipRole)
            path = common.get_sequence_endpath(path)
            img = OpenImageIO.ImageBuf(path)
            image_info = img.spec().serialize().split('\n')
            image_info = [f.strip() for f in image_info if f]
            for n, text in enumerate(image_info):
                if n > 2:
                    break
                common.draw_aliased_text(
                    painter,
                    font,
                    QtCore.QRect(rect),
                    text,
                    QtCore.Qt.AlignLeft,
                    common.SECONDARY_TEXT
                )
                rect.moveTop(rect.center().y() + int(metrics.lineSpacing()))
        painter.end()

    def set_image(self, path):
        """Loads an image using OpenImageIO and displays the contents as a
        QPoxmap item.

        """
        image = images.oiio_get_qimage(path)

        if not image:
            return None
        if image.isNull():
            return None

        # Let's make sure we're not locking the resource
        images.oiio_cache.invalidate(path, force=True)

        pixmap = QtGui.QPixmap.fromImage(image)
        if pixmap.isNull():
            log.error('Could not convert QImage to QPixmap')
            return None

        self.item.setPixmap(pixmap)
        self.item.setShapeMode(QtWidgets.QGraphicsPixmapItem.MaskShape)
        self.item.setTransformationMode(QtCore.Qt.SmoothTransformation)

        size = self.item.pixmap().size()
        if size.height() > self.height() or size.width() > self.width():
            self.fitInView(self.item, QtCore.Qt.KeepAspectRatio)
        return self.item

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


class ImageViewer(QtWidgets.QDialog):
    """Used to view an image.

    The image data is loaded using OpenImageIO and is then wrapped in a QGraphicsScene,
    using a QPixmap. See ``Viewer``.

    """

    def __init__(self, path, parent=None):
        global _viewer_widget
        _viewer_widget = self
        super(ImageViewer, self).__init__(parent=parent)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )

        self.delete_timer = common.Timer(parent=self)
        self.delete_timer.setSingleShot(True)
        self.delete_timer.setInterval(50)
        self.delete_timer.timeout.connect(self.close)
        self.delete_timer.timeout.connect(self.delete_timer.deleteLater)
        self.delete_timer.timeout.connect(self.deleteLater)

        self.load_timer = common.Timer(parent=self)
        self.load_timer.setSingleShot(True)
        self.load_timer.setInterval(10)
        self.load_timer.timeout.connect(self.load_timer.deleteLater)

        if not isinstance(path, unicode):
            self.done(QtWidgets.QDialog.Rejected)
            raise ValueError(
                u'Expected <type \'unicode\'>, got {}'.format(type(path)))

        self.path = path

        if not self.parent():
            common.set_custom_stylesheet(self)

        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            s = u'{} does not exists.'.format(path)
            ui.ErrorBox(
                u'Error previewing image.', s).open()
            log.error(s)
            self.done(QtWidgets.QDialog.Rejected)
            raise RuntimeError(s)

        if not images.oiio_get_buf(path, force=True):
            s = u'{} seems invalid.'.format(path)
            ui.ErrorBox(
                u'Error previewing image.', s).open()
            log.error(s)
            self.done(QtWidgets.QDialog.Rejected)
            raise RuntimeError(s)

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
        self.load_timer.timeout.connect(self.load_timer.deleteLater)
        self.load_timer.timeout.connect(lambda: self.viewer.set_image(path))

        self.layout().addWidget(self.viewer, 1)

    def index(self):
        if self.parent():
            return self.parent().selectionModel().currentIndex()
        return QtCore.QModelIndex()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidth(common.ROW_SEPARATOR())
        painter.setPen(pen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        color = images.ImageCache.get_color(self.path)
        if not color:
            color = images.ImageCache.make_color(self.path)
        if not color:
            color = QtGui.QColor(20, 20, 20, 240)
        painter.setBrush(color)
        painter.drawRect(self.rect())

        painter.end()

    def mousePressEvent(self, event):
        event.accept()
        self.close()
        self.deleteLater()

    def keyPressEvent(self, event):
        """We're mapping the key press events to the parent list."""
        if self.parent():
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

        self.delete_timer.start()

    def showEvent(self, event):
        common.fit_screen_geometry(self)
        self.load_timer.start()
