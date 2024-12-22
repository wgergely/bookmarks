from PySide2 import QtWidgets, QtGui, QtCore

from ... import common, images


class DragPixmapFactory(QtWidgets.QWidget):
    """Widget used to define the appearance of an item being dragged."""

    def __init__(self, pixmap, text, parent=None):
        super().__init__(parent=parent)
        self._pixmap = pixmap
        self._text = text

        _, metrics = common.Font.MediumFont(common.Size.MediumText())
        self._text_width = metrics.horizontalAdvance(text)

        width = self._text_width + common.Size.Margin()
        width = (
            common.Size.DefaultWidth() + common.Size.Margin()
            if width > common.Size.DefaultWidth() else width
        )

        self.setFixedHeight(common.Size.RowHeight())

        longest_edge = max((pixmap.width(), pixmap.height()))
        o = common.Size.Indicator()
        self.setFixedWidth(
            longest_edge + (o * 2) + width
        )

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.adjustSize()

    @classmethod
    def pixmap(cls, pixmap, text):
        """Returns the widget as a rendered pixmap."""
        w = cls(pixmap, text)
        pixmap = QtGui.QPixmap(w.size() * common.pixel_ratio, )
        pixmap.setDevicePixelRatio(common.pixel_ratio)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        w.render(painter, QtCore.QPoint(), QtGui.QRegion())
        return pixmap

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.Color.DarkBackground())
        painter.setOpacity(0.6)
        o = common.Size.Indicator()
        painter.drawRoundedRect(self.rect(), o, o)
        painter.setOpacity(1.0)

        pixmap_rect = QtCore.QRect(
            0, 0, common.Size.RowHeight(), common.Size.RowHeight()
        )
        painter.drawPixmap(pixmap_rect, self._pixmap, self._pixmap.rect())

        width = self._text_width + common.Size.Indicator()
        max_width = common.Size.DefaultWidth()
        width = max_width if width > max_width else width
        rect = QtCore.QRect(
            common.Size.RowHeight() + common.Size.Indicator(),
            0,
            width,
            self.height()
        )
        common.draw_aliased_text(
            painter,
            common.Font.MediumFont(common.Size.MediumText())[0],
            rect,
            self._text,
            QtCore.Qt.AlignCenter,
            common.Color.SelectedText()
        )
        painter.end()


class ItemDrag(QtGui.QDrag):
    """A utility class used to start a drag operation.

    """

    def __init__(self, index, widget):
        super().__init__(widget)

        model = index.model().sourceModel()
        self.setMimeData(model.mimeData([index, ]))

        def _get(s, color=common.Color.Green()):
            return images.rsc_pixmap(
                s, color,
                common.Size.Margin() * common.pixel_ratio
            )

        # Set drag icon
        self.setDragCursor(_get('add_circle'), QtCore.Qt.CopyAction)
        self.setDragCursor(_get('file'), QtCore.Qt.MoveAction)
        self.setDragCursor(
            _get('close', color=common.Color.Red()),
            QtCore.Qt.ActionMask
        )
        self.setDragCursor(
            _get('close', color=common.Color.Red()),
            QtCore.Qt.IgnoreAction
        )

        # Set file item apperance
        if index.data(common.ItemTabRole) in (common.BookmarkTab, common.AssetTab):
            pixmap = images.rsc_pixmap(
                'copy',
                common.Color.DisabledText(),
                common.Size.RowHeight()
            )
            pixmap = DragPixmapFactory.pixmap(pixmap, '< Item Properties >')
            self.setPixmap(pixmap)

        if index.data(common.ItemTabRole) in (common.FileTab, common.FavouriteTab):
            source = index.data(common.PathRole)

            modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
            no_modifier = modifiers == QtCore.Qt.NoModifier
            alt_modifier = modifiers & QtCore.Qt.AltModifier
            shift_modifier = modifiers & QtCore.Qt.ShiftModifier

            if no_modifier:
                source = common.get_sequence_end_path(source)
                pixmap, _ = images.get_thumbnail(
                    index.data(common.ParentPathRole)[0],
                    index.data(common.ParentPathRole)[1],
                    index.data(common.ParentPathRole)[2],
                    source,
                    size=common.Size.RowHeight(),
                )
            elif alt_modifier and shift_modifier:
                pixmap = images.rsc_pixmap(
                    'folder', common.Color.SecondaryText(),
                    common.Size.RowHeight()
                )
                source = QtCore.QFileInfo(source).dir().path()
            elif alt_modifier:
                pixmap = images.rsc_pixmap(
                    'file', common.Color.SecondaryText(),
                    common.Size.RowHeight()
                )
                source = common.get_sequence_start_path(source)
            elif shift_modifier:
                source = common.get_sequence_start_path(source) + ', ++'
                pixmap = images.rsc_pixmap(
                    'multiples_files', common.Color.SecondaryText(),
                    common.Size.RowHeight()
                )
            else:
                return

            if pixmap and not pixmap.isNull():
                pixmap = DragPixmapFactory.pixmap(pixmap, source)
                self.setPixmap(pixmap)
