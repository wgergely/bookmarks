# -*- coding: utf-8 -*-
"""

"""
import uuid
import functools
import datetime

from PySide2 import QtCore, QtGui, QtWidgets

from .. import log
from .. import common
from .. import ui
from .. import images
from .. import bookmark_db
from .. import contextmenu
from ..shotgun import shotgun


THUMBNAIL_EDITOR_SIZE = common.MARGIN() * 10
HEIGHT = common.ROW_HEIGHT() * 0.8
TEMP_THUMBNAIL_PATH = u'{temp}/{product}/temp/{uuid}.{ext}'

ProjectTypes = ('Project',)
AssetTypes = ('Asset', 'Sequence', 'Shot')


@common.error
@common.debug
def process_image(source):
    """Converts, resizes and loads an image file as a QImage.

    Args:
        source (unicode): Path to an image file.

    Returns:
        QImage: The resized QImage, or `None` if the image was not processed successfully.

    """
    destination = TEMP_THUMBNAIL_PATH.format(
        temp=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        product=common.PRODUCT,
        uuid=uuid.uuid1().get_hex(),
        ext=images.THUMBNAIL_FORMAT
    )
    f = QtCore.QFileInfo(destination)
    if not f.dir().exists():
        if not f.dir().mkpath(u'.'):
            raise RuntimeError(u'Could not create temp folder')

    res = images.ImageCache.oiio_make_thumbnail(
        source,
        destination,
        images.THUMBNAIL_IMAGE_SIZE
    )

    if not res:
        raise RuntimeError(u'Failed to convert the thumbnail')

    images.ImageCache.flush(destination)
    image = images.ImageCache.get_image(
        destination,
        int(images.THUMBNAIL_IMAGE_SIZE),
        force=True
    )
    if not image or image.isNull():
        raise RuntimeError(u'Failed to load converted image')

    if not QtCore.QFile(destination).remove():
        log.error('Could not remove temp image.')

    return image


class BaseComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(BaseComboBox, self).__init__(parent=parent)
        self.setFixedHeight(HEIGHT)
        self.init_items()

    @common.error
    @common.debug
    def init_items(self):
        pass

    def addItem(self, *args, **kwargs):
        super(BaseComboBox, self).addItem(*args, **kwargs)
        self.decorate_item()

    def decorate_item(self, error=False):
        idx = self.count() - 1
        sg_pixmap = images.ImageCache.get_rsc_pixmap(
            u'shotgun', common.SEPARATOR, common.MARGIN() * 2)
        check_pixmap = images.ImageCache.get_rsc_pixmap(
            u'check', common.GREEN, common.MARGIN() * 2)
        error_pixmap = images.ImageCache.get_rsc_pixmap(
            u'close', common.RED, common.MARGIN() * 2)

        error_icon = QtGui.QIcon(error_pixmap)

        icon = QtGui.QIcon()
        icon.addPixmap(sg_pixmap, mode=QtGui.QIcon.Normal)
        icon.addPixmap(check_pixmap, mode=QtGui.QIcon.Active)
        icon.addPixmap(check_pixmap, mode=QtGui.QIcon.Selected)

        self.setItemData(
            idx,
            QtCore.QSize(1, HEIGHT),
            role=QtCore.Qt.SizeHintRole
        )

        self.setItemData(
            idx,
            error_icon if error else icon,
            role=QtCore.Qt.DecorationRole
        )


class ProjectTypesWidget(BaseComboBox):
    def init_items(self):
        for entity_type in ProjectTypes:
            self.addItem(entity_type)


class AssetTypesWidget(BaseComboBox):
    def init_items(self):
        for entity_type in AssetTypes:
            self.addItem(entity_type)


class ThumbnailContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with the ThumbnailEditorWidget.

    """

    def setup(self):
        add_pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.GREEN, common.MARGIN())
        remove_pixmap = images.ImageCache.get_rsc_pixmap(
            u'close', common.RED, common.MARGIN())

        self.menu[u'Capture...'] = {
            u'icon': add_pixmap,
            u'action': self.parent().capture
        }
        self.menu[u'Pick...'] = {
            u'icon': add_pixmap,
            u'action': self.parent().pick_image
        }

        self.separator()

        self.menu[u'Reset'] = {
            u'icon': remove_pixmap,
            u'action': self.parent().reset_image
        }


class ThumbnailEditorWidget(ui.ClickableIconButton):
    """Widget used to edit item thumbnails.

    """

    def __init__(self, server, job, root, source=None, fallback_thumb=u'placeholder', parent=None):
        super(ThumbnailEditorWidget, self).__init__(
            u'pick_image',
            (common.BLUE, common.DARK_BG),
            size=THUMBNAIL_EDITOR_SIZE,
            description=u'Drag-and-drop an image to add, click to capture, or right-click to pick a custom thumbnail...',
            parent=parent
        )

        self.server = server
        self.job = job
        self.root = root
        self.source = source
        self.fallback_thumb = fallback_thumb

        self._window_pos = None

        self._image = QtGui.QImage()
        self._image.setDevicePixelRatio(images.pixel_ratio)

        self.setAcceptDrops(True)
        self._drag_in_progress = False

        self.clicked.connect(self.capture)

    def image(self):
        return self._image

    def process_image(self, source):
        image = process_image(source)
        self.set_image(image)

    @QtCore.Slot()
    def set_image(self, image):
        if not isinstance(image, QtGui.QImage) or image.isNull():
            self._image = QtGui.QImage()
            self._image.setDevicePixelRatio(images.pixel_ratio)
        else:
            self._image = image
        self.update()

    def save_image(self, destination=None):
        """Save the selected thumbnail image to the disc."""
        if not isinstance(self._image, QtGui.QImage) or self._image.isNull():
            return

        args = (
            self.server,
            self.job,
            self.root,
            self.source
        )

        if not all(args) and destination is None:
            return

        if destination is None:
            destination = images.get_cached_thumbnail_path(*args)

        if not self._image.save(destination):
            raise RuntimeError(u'Failed to save thumbnail.')

        images.ImageCache.flush(destination)

    @QtCore.Slot()
    def reset_image(self):
        self.set_image(None)

    @common.error
    @common.debug
    def pick_image(self):
        from ..editors import thumb_picker as editor
        widget = editor.show()
        widget.fileSelected.connect(self.process_image)

    @common.error
    @common.debug
    def capture(self):
        """Captures a thumbnail and save it as a QImage.

        The captured image is stored internally in `self._image` and saved to
        disk when `self.save_image()` is called.

        """
        self._window_pos = self.window().saveGeometry()
        self.save_window()
        self.hide_window()

        try:
            from ..editors import thumb_capture as editor
            widget = editor.show()
            widget.accepted.connect(self.restore_window)
            widget.rejected.connect(self.restore_window)
            widget.captureFinished.connect(self.process_image)
        except:
            self.restore_window()
            raise

    def hide_window(self):
        app = QtWidgets.QApplication.instance()
        pos = app.primaryScreen().geometry().bottomRight()
        self.window().move(pos)

    def save_window(self):
        self._window_pos = self.window().saveGeometry()

    def restore_window(self):
        self.window().restoreGeometry(self._window_pos)

    def _paint_proposed_thumbnail(self, painter):
        o = common.ROW_SEPARATOR()
        rect = self.rect().adjusted(o, o, -o, -o)

        color = common.SEPARATOR
        pen = QtGui.QPen(color)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)

        image = images.ImageCache.resize_image(
            self._image, int(self.rect().height()))

        s = float(self.rect().height())
        longest_edge = float(max((self._image.width(), self._image.height())))
        ratio = s / longest_edge
        w = self._image.width() * ratio
        h = self._image.height() * ratio

        rect = QtCore.QRect(
            0, 0,
            int(w) - (o * 2), int(h) - (o * 2)
        )
        rect.moveCenter(self.rect().center())

        painter.drawImage(rect, image, image.rect())

    def _paint_background(self, painter):
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SEPARATOR)
        painter.drawRect(self.rect())

    def _paint_current_thumbnail(self, painter):
        if not all((self.server, self.job, self.root)):
            pixmap, color = images.get_thumbnail(
                u'',
                u'',
                u'',
                u'',
                self.rect().height(),
                fallback_thumb=self.fallback_thumb
            )
        else:
            pixmap, color = images.get_thumbnail(
                self.server,
                self.job,
                self.root,
                self.source,
                self.rect().height(),
                fallback_thumb=self.fallback_thumb
            )

        if not isinstance(pixmap, QtGui.QPixmap) or pixmap.isNull():
            return

        o = common.ROW_SEPARATOR()

        color = color if color else common.SEPARATOR
        pen = QtGui.QPen(color)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)

        s = float(self.rect().height())
        longest_edge = float(max((pixmap.width(), pixmap.height())))
        ratio = s / longest_edge
        w = pixmap.width() * ratio
        h = pixmap.height() * ratio

        rect = QtCore.QRect(0, 0,
                            int(w) - (o * 2),
                            int(h) - (o * 2)
                            )
        rect.moveCenter(self.rect().center())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    def contextMenuEvent(self, event):
        menu = ThumbnailContextMenu(QtCore.QModelIndex(), parent=self)
        pos = self.rect().center()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        _ = painter.setOpacity(1.0) if hover else painter.setOpacity(0.8)

        try:
            self._paint_background(painter)
            if not self._image or self._image.isNull():
                self._paint_current_thumbnail(painter)
            else:
                self._paint_proposed_thumbnail(painter)
        except:
            log.error(u'Error painting.')
        finally:
            painter.end()

    def enterEvent(self, event):
        app = QtWidgets.QApplication.instance()
        if self.isEnabled():
            if app.overrideCursor():
                app.changeOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            else:
                app.restoreOverrideCursor()
                app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

        super(ThumbnailEditorWidget, self).enterEvent(event)

    def leaveEvent(self, event):
        super(ThumbnailEditorWidget, self).leaveEvent(event)
        app = QtWidgets.QApplication.instance()
        if self.isEnabled():
            if app.overrideCursor():
                app.restoreOverrideCursor()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self._drag_in_progress = True
            self.repaint()
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            self._drag_in_progress = True
            event.accept()
            return

        self._drag_in_progress = False
        event.ignore()

    def dragLeaveEvent(self, event):
        self._drag_in_progress = False
        self.repaint()
        return True

    def dropEvent(self, event):
        self._drag_in_progress = False
        self.repaint()

        for url in event.mimeData().urls():
            s = url.toLocalFile()
            self.process_image(s)
            break

        self.repaint()

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction
