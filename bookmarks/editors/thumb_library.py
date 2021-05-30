# -*- coding: utf-8 -*-
"""Widget used to select a thumbnail from Bookmark's in-built thumbnail library.

"""
import os
import _scandir
from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import ui
from .. import images

instance = None


COLUMNS = 5
RSC_DIR = u'{}/../../rsc'.format(__file__)


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


def show(server=None, job=None, root=None, source=None):
    global instance

    close()
    instance = ThumbnailLibraryWidget(
        server,
        job,
        root,
        source
    )
    instance.open()
    return instance


class ClickableItem(QtWidgets.QLabel):
    """Custom QLabel ssed by the ThumbnailLibraryWidget to display an image.

    """
    clicked = QtCore.Signal(unicode)

    def __init__(self, path, parent=None):
        super(ClickableItem, self).__init__(parent=parent)
        self._path = path
        self._pixmap = None

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setScaledContents(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        h = common.ROW_HEIGHT() * 2
        self.setMinimumSize(QtCore.QSize(h, h))

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.clicked.emit(self._path)

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        o = 1.0 if hover else 0.7
        painter.setOpacity(o)

        if not self._pixmap:
            self._pixmap = images.ImageCache.get_pixmap(
                self._path,
                self.height(),
                force=True
            )
            if not self._pixmap:
                return

        s = float(min((self.rect().height(), self.rect().width())))
        longest_edge = float(
            max((self._pixmap.width(), self._pixmap.height())))
        ratio = s / longest_edge
        w = self._pixmap.width() * ratio
        h = self._pixmap.height() * ratio
        _rect = QtCore.QRect(0, 0, w, h)
        _rect.moveCenter(self.rect().center())
        painter.drawPixmap(
            _rect,
            self._pixmap,
        )
        if not hover:
            painter.end()
            return

        painter.setPen(common.TEXT)
        rect = self.rect()
        rect.moveTopLeft(rect.topLeft() + QtCore.QPoint(1, 1))

        text = self._path.split(u'/').pop()
        text = text.replace(u'thumb_', u'')
        font, _ = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())

        common.draw_aliased_text(
            painter,
            font,
            rect,
            text,
            QtCore.Qt.AlignCenter,
            QtGui.QColor(0, 0, 0, 255),
        )

        rect = self.rect()
        common.draw_aliased_text(
            painter,
            font,
            rect,
            text,
            QtCore.Qt.AlignCenter,
            common.SELECTED_TEXT,
        )
        painter.end()


class ThumbnailLibraryWidget(QtWidgets.QDialog):
    """The widget used to browser and select a thumbnail from a set of
    predefined thumbnails.

    The thumbnail files are stored in the ./rsc folder and are prefixed by
    `thumb_*`.

    """
    thumbnailSelected = QtCore.Signal(unicode)
    label_size = common.ASSET_ROW_HEIGHT()

    def __init__(self, server, job, root, source, parent=None):
        super(ThumbnailLibraryWidget, self).__init__(parent=parent)
        self.server = server
        self.job = job
        self.root = root
        self.source = source

        self.scrollarea = None
        self.columns = COLUMNS

        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle(u'Select thumbnail')

        self._create_ui()
        self._add_thumbnails()

    def _create_ui(self):
        if not self.parent():
            common.set_custom_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()

        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        row = ui.add_row(
            None, height=common.ROW_HEIGHT(), padding=None, parent=self)
        label = ui.PaintedLabel(
            u'Select a thumbnail',
            color=common.TEXT,
            size=common.LARGE_FONT_SIZE(),
            parent=self
        )
        row.layout().addWidget(label)

        widget = QtWidgets.QWidget(parent=self)
        widget.setStyleSheet(
            u'background-color: {}'.format(common.rgb(common.SEPARATOR)))

        QtWidgets.QGridLayout(widget)
        widget.layout().setAlignment(QtCore.Qt.AlignCenter)
        widget.layout().setContentsMargins(
            common.INDICATOR_WIDTH(),
            common.INDICATOR_WIDTH(),
            common.INDICATOR_WIDTH(),
            common.INDICATOR_WIDTH())
        widget.layout().setSpacing(common.INDICATOR_WIDTH())

        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setWidget(widget)
        
        self.layout().addWidget(self.scrollarea, 1)

    def _add_thumbnails(self):
        row = 0
        path = u'{root}/{resource}'.format(
            root=RSC_DIR,
            resource=images.ThumbnailResource
        )
        path = os.path.normpath(os.path.abspath(path))

        idx = 0
        for entry in _scandir.scandir(path):
            label = ClickableItem(
                entry.path.replace(u'\\', u'/'),
                parent=self
            )

            column = idx % self.columns
            if column == 0:
                row += 1
            self.scrollarea.widget().layout().addWidget(label, row, column)
            label.clicked.connect(self.thumbnailSelected)
            label.clicked.connect(self.close)

            idx += 1

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(common.SEPARATOR)
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 50))
        pen.setWidth(common.ROW_SEPARATOR())
        painter.setPen(pen)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.INDICATOR_WIDTH() * 2.0
        painter.drawRoundedRect(
            self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o)),
            o, o
        )
        painter.end()

    def showEvent(self, event):
        common.center_window(self)

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
