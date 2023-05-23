"""A list of widgets and methods used by :class:`bookmarks.editor.base.BasePropertyEditor`.

"""
import uuid

from PySide2 import QtCore, QtGui, QtWidgets

import pyimageutil

from .. import common
from .. import contextmenu
from .. import images
from .. import log
from .. import ui

THUMBNAIL_EDITOR_SIZE = common.size(common.size_margin) * 10
HEIGHT = common.size(common.size_row_height) * 0.8
TEMP_THUMBNAIL_PATH = '{temp}/{product}/temp/{uuid}.{ext}'

ProjectTypes = ('Project',)
AssetTypes = ('Episode', 'Asset', 'Sequence', 'Shot')


@common.error
@common.debug
def process_image(source):
    """Converts, resizes and loads an image file as a QImage.

    Args:
        source (str): Path to an image file.

    Returns:
        QImage: The resized QImage, or `None` if the image was not processed
        successfully.

    """
    destination = TEMP_THUMBNAIL_PATH.format(
        temp=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation
        ),
        product=common.product,
        uuid=uuid.uuid1().hex,
        ext=common.thumbnail_format
    )
    f = QtCore.QFileInfo(destination)
    if not f.dir().exists():
        if not f.dir().mkpath('.'):
            raise RuntimeError('Could not create temp folder')

    res = pyimageutil.convert_image(
        source,
        destination,
        max_size=int(common.thumbnail_size)
    )
    if not res:
        raise RuntimeError('Failed to convert the thumbnail')

    images.ImageCache.flush(destination)
    image = images.ImageCache.get_image(
        destination,
        int(common.thumbnail_size),
        force=True
    )
    if not image or image.isNull():
        raise RuntimeError('Failed to load converted image')

    images.ImageCache.flush(destination)
    if not QtCore.QFile(destination).remove():
        log.error('Could not remove temp image.')

    return image


class BaseComboBox(QtWidgets.QComboBox):
    """Base combobox used by :class:`~bookmarks.editor.base.BasePropertyEditor`.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_items()

    @common.error
    @common.debug
    def init_items(self):
        """Initializes the items.

        """
        pass

    def addItem(self, *args, **kwargs):
        """Custom add item function.

        """
        super().addItem(*args, **kwargs)
        self.decorate_item()

    def decorate_item(self, error=False):
        """Changes the appearance of the item.

        """
        idx = self.count() - 1
        sg_pixmap = images.rsc_pixmap(
            'sg', common.color(common.color_separator),
            common.size(common.size_margin) * 2
        )
        check_pixmap = images.rsc_pixmap(
            'check', common.color(common.color_green),
            common.size(common.size_margin) * 2
        )
        error_pixmap = images.rsc_pixmap(
            'close', common.color(common.color_red),
            common.size(common.size_margin) * 2
        )

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


class SGProjectTypesWidget(BaseComboBox):
    """ShotGrid entity type picker.

    """

    def init_items(self):
        """Initialize items.
        
        """
        for entity_type in ProjectTypes:
            self.addItem(entity_type)


class SGAssetTypesWidget(BaseComboBox):
    """ShotGrid entity type picker.

    """

    def init_items(self):
        """Initialize items.

        """
        for entity_type in AssetTypes:
            self.addItem(entity_type)


class ThumbnailContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with the :class:`ThumbnailEditorWidget`.

    """

    def setup(self):
        """Creates the context menu.

        """
        add_pixmap = images.rsc_pixmap(
            'add', common.color(common.color_green), common.size(common.size_margin)
        )
        remove_pixmap = images.rsc_pixmap(
            'close', common.color(common.color_red), common.size(common.size_margin)
        )

        self.menu['Capture...'] = {
            'icon': add_pixmap,
            'action': self.parent().capture
        }
        self.menu['Pick...'] = {
            'icon': add_pixmap,
            'action': self.parent().pick_image
        }

        self.separator()

        self.menu['Reset'] = {
            'icon': remove_pixmap,
            'action': self.parent().reset_image
        }


class ThumbnailEditorWidget(ui.ClickableIconButton):
    """Widget used to edit item thumbnails.

    """

    def __init__(
            self, size=THUMBNAIL_EDITOR_SIZE,
            fallback_thumb='placeholder', parent=None
    ):
        super().__init__(
            'pick_image',
            (common.color(common.color_blue),
             common.color(common.color_dark_background)),
            size=size,
            description='Drag-and-drop an image to add, click to capture, '
                        'or right-click to pick a custom thumbnail...',
            parent=parent
        )

        self.fallback_thumb = fallback_thumb

        self._window_pos = None

        self._image = QtGui.QImage()
        self._image.setDevicePixelRatio(common.pixel_ratio)

        self.setAcceptDrops(True)
        self._drag_in_progress = False

        self.clicked.connect(self.capture)

    def image(self):
        """The current thumbnail image.
        
        """
        return self._image

    def process_image(self, source):
        """Load and set an image from a source file.
        
        Args:
            source (str): The path to the image file.
            
        """
        image = process_image(source)
        self.set_image(image)

    @QtCore.Slot()
    def set_image(self, image):
        """Sets the given QImage as the current image.
        
        Args:
            image (QImage): The image to set.            
            
        """
        if not isinstance(image, QtGui.QImage) or image.isNull():
            self._image = QtGui.QImage()
            self._image.setDevicePixelRatio(common.pixel_ratio)
        else:
            self._image = image
        self.update()

    def save_image(self, destination=None):
        """Saves the selected thumbnail image to the file.
        
        """
        if not isinstance(self._image, QtGui.QImage) or self._image.isNull():
            return

        args = (
            self.window().server,
            self.window().job,
            self.window().root,
            self.window().db_source()
        )

        if not all(args) and destination is None:
            return

        if destination is None:
            destination = images.get_cached_thumbnail_path(*args)

        if not self._image.save(destination):
            raise RuntimeError('Failed to save thumbnail.')

        images.ImageCache.flush(destination)
        images.ImageCache.flush(self.window().db_source())

    @QtCore.Slot()
    def reset_image(self):
        """Clears the selected thumbnail image.
        
        """
        self.set_image(None)

    @common.error
    @common.debug
    def pick_image(self):
        """Pick image action.
        
        """
        from ..items.widgets import thumb_picker as editor
        widget = editor.show()
        widget.fileSelected.connect(self.process_image)

    @common.error
    @common.debug
    def capture(self):
        """Captures a thumbnail and save it as a QImage.

        The captured image is stored internally in `self._image` and saved to
        disk when `self.save_image()` is called.

        """
        geo = self.window().saveGeometry()

        def _restore_geo(v):
            self.window().restoreGeometry(v)

        try:
            from ..items.widgets import thumb_capture as editor
            widget = editor.show()
            self.hide_window()
            widget.accepted.connect(lambda: _restore_geo(geo))
            widget.rejected.connect(lambda: _restore_geo(geo))
            widget.captureFinished.connect(self.process_image)
        except:
            _restore_geo(geo)
            raise

    def hide_window(self):
        """Move the window out of view.
        
        """
        app = QtWidgets.QApplication.instance()
        pos = app.primaryScreen().geometry().bottomRight()
        self.window().move(pos)

    def _paint_proposed_thumbnail(self, painter):
        painter.setBrush(QtGui.QColor(0, 0, 0, 75))
        painter.drawRect(self.rect())

        o = common.size(common.size_separator)

        color = common.color(common.color_separator)
        pen = QtGui.QPen(color)
        pen.setWidthF(common.size(common.size_separator))
        painter.setPen(pen)

        image = images.resize_image(
            self._image, int(self.rect().height())
        )

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

        # Paint new indicator
        size = common.size(common.size_font_large) * 0.5
        rect = QtCore.QRect(0, 0, size, size)

        pos = QtCore.QPoint(
            size * 0.5,
            size * 0.5,
        )
        rect.moveTopLeft(pos)
        painter.setBrush(common.color(common.color_green))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, size, size)

    def _paint_background(self, painter):
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.color_separator))
        painter.drawRect(self.rect())

    def _paint_current_thumbnail(self, painter):
        """Paints the current thumbnail of the given source.

        """
        if not all((self.window().server, self.window().job, self.window().root)):
            pixmap = images.rsc_pixmap(
                self.fallback_thumb, None, self.rect().height()
            )
        else:
            pixmap, color = images.get_thumbnail(
                self.window().server,
                self.window().job,
                self.window().root,
                self.window().db_source(),
                self.rect().height(),
                fallback_thumb=self.fallback_thumb
            )

            if color:
                painter.setBrush(color)
                painter.drawRect(self.rect())

        if not isinstance(pixmap, QtGui.QPixmap) or pixmap.isNull():
            return

        o = common.size(common.size_separator)

        color = common.color(common.color_separator)
        pen = QtGui.QPen(color)
        pen.setWidthF(common.size(common.size_separator))
        painter.setPen(pen)

        s = float(self.rect().height())
        longest_edge = float(max((pixmap.width(), pixmap.height())))
        ratio = s / longest_edge
        w = pixmap.width() * ratio
        h = pixmap.height() * ratio

        rect = QtCore.QRect(
            0, 0,
            int(w) - (o * 2),
            int(h) - (o * 2)
        )
        rect.moveCenter(self.rect().center())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    def contextMenuEvent(self, event):
        """Context menu event handler.
        
        """
        menu = ThumbnailContextMenu(QtCore.QModelIndex(), parent=self)
        pos = self.rect().center()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def paintEvent(self, event):
        """Paint event handler.
        
        """
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
            log.error('Error painting.')
        finally:
            painter.end()

    def enterEvent(self, event):
        """Enter event handler.
        
        """
        app = QtWidgets.QApplication.instance()
        if self.isEnabled():
            if app.overrideCursor():
                app.changeOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            else:
                app.restoreOverrideCursor()
                app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

        super().enterEvent(event)

    def leaveEvent(self, event):
        """Leave event handler.
        
        """
        super().leaveEvent(event)
        app = QtWidgets.QApplication.instance()
        if self.isEnabled():
            if app.overrideCursor():
                app.restoreOverrideCursor()

    def dragEnterEvent(self, event):
        """Drag event handler.
        
        """
        if event.mimeData().hasUrls():
            self._drag_in_progress = True
            self.repaint()
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Drag move event handler.
        
        """
        if event.mimeData().hasUrls():
            self._drag_in_progress = True
            event.accept()
            return

        self._drag_in_progress = False
        event.ignore()

    def dragLeaveEvent(self, event):
        """Drag leave event handler.
        
        """
        self._drag_in_progress = False
        self.repaint()
        return True

    def dropEvent(self, event):
        """Drop event handler.
        
        """
        self._drag_in_progress = False
        self.repaint()

        for url in event.mimeData().urls():
            s = url.toLocalFile()
            self.process_image(s)
            break

        self.repaint()
