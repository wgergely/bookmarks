# -*- coding: utf-8 -*-
"""The delegate used to visualise bookmark, asset and file items derived from
`base.BaseListWidget`.

The delegate is responsible for painting the thumbnails, names, and clickable
buttons of the list items. The base list widget has a number of custom features,
such as, clickable in-line-buttons that the deleagate is aware of.

We're painting text using `QPainterPaths` for a high-quality, aliased display
but the approach comes with a huge performance hit and therefore any
QPainterPath paint operation is backed by a cache (see `common.PATH_CACHE`).

"""
import re
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from .. import common
from .. import images


regex_remove_version = re.compile(
    rf'(.*)(v)([\{common.SEQSTART}0-9\-\{common.SEQEND}]+.*)',
    flags=re.IGNORECASE | re.UNICODE
)
regex_remove_seq_marker = re.compile(
    rf'[\{common.SEQSTART}\{common.SEQEND}]*',
    flags=re.IGNORECASE | re.UNICODE
)


HOVER_COLOR = QtGui.QColor(255, 255, 255, 10)


BackgroundRect = 0
IndicatorRect = 1
ThumbnailRect = 2
AssetNameRect = 3
AssetDescriptionRect = 4
AddAssetRect = 5
TodoRect = 6
RevealRect = 7
ArchiveRect = 8
FavouriteRect = 9
DataRect = 10
PropertiesRect = 11
InlineBackgroundRect = 12


def paintmethod(func):
    """Decorator used to manage painter states."""
    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        args[1].save()
        res = func(self, *args, **kwargs)
        args[1].restore()
        return res
    return func_wrapper


def subdir_rects_key(index, option):
    return index.data(QtCore.Qt.StatusTipRole) + '{}'.format(option.rect.height())


def subdir_bg_rect_key(index, option):
    return index.data(QtCore.Qt.StatusTipRole) + '{}'.format(option.rect.size())


def get_painter_path(x, y, font, text):
    """Creates, populates and caches a QPainterPath instance."""
    k = f'{x}{y}{font}{text}'
    if k not in common.PATH_CACHE:
        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)
        common.PATH_CACHE[k] = path
    return common.PATH_CACHE[k]


null_rect = QtCore.QRect()


def get_rectangles(rectangle, count):
    """Returns the paintable/clickable regions based on the number of
    inline icons and the source rectangle.

    Args:
        rectangle (QtCore.QRect):   An list item's visual rectangle.
        count (int):                The number of inline icons.

    Returns:
        dict:  Dictionary containing `count` number of rectangles.

    """
    k = f'{rectangle}{count}'
    if k in common.RECTANGLE_CACHE:
        return common.RECTANGLE_CACHE[k]

    def adjusted():
        return rectangle.adjusted(0, 0, 0, -common.size(common.HeightSeparator))

    background_rect = adjusted()
    background_rect.setLeft(common.size(common.WidthIndicator))

    indicator_rect = QtCore.QRect(rectangle)
    indicator_rect.setWidth(common.size(common.WidthIndicator))

    thumbnail_rect = QtCore.QRect(rectangle)
    thumbnail_rect.setWidth(thumbnail_rect.height())
    thumbnail_rect.moveLeft(common.size(common.WidthIndicator))

    # Inline icons rect
    inline_icon_rects = []
    inline_icon_rect = adjusted()
    spacing = common.size(common.WidthIndicator) * 2
    center = inline_icon_rect.center()
    size = QtCore.QSize(common.size(common.WidthMargin),
                        common.size(common.WidthMargin))
    inline_icon_rect.setSize(size)
    inline_icon_rect.moveCenter(center)
    inline_icon_rect.moveRight(rectangle.right() - spacing)

    inline_background_rect = QtCore.QRect(background_rect)
    inline_background_rect.setLeft(inline_background_rect.right() - ((common.size(common.WidthMargin) + (
        common.size(common.WidthIndicator) * 2)) * count + common.size(common.WidthMargin)))

    offset = 0
    for _ in range(count):
        r = inline_icon_rect.translated(offset, 0)
        inline_icon_rects.append(r)
        offset -= inline_icon_rect.width() + spacing
    offset -= spacing

    data_rect = adjusted()
    data_rect.setLeft(thumbnail_rect.right() + spacing)
    data_rect.setRight(rectangle.right() + offset)

    common.RECTANGLE_CACHE[k] = {
        BackgroundRect: background_rect,
        IndicatorRect: indicator_rect,
        ThumbnailRect: thumbnail_rect,
        FavouriteRect: inline_icon_rects[0] if count > 0 else null_rect,
        ArchiveRect: inline_icon_rects[1] if count > 1 else null_rect,
        RevealRect: inline_icon_rects[2] if count > 2 else null_rect,
        TodoRect: inline_icon_rects[3] if count > 3 else null_rect,
        AddAssetRect: inline_icon_rects[4] if count > 4 else null_rect,
        PropertiesRect: inline_icon_rects[5] if count > 5 else null_rect,
        InlineBackgroundRect: inline_background_rect if count else null_rect,
        DataRect: data_rect
    }
    return common.RECTANGLE_CACHE[k]


def draw_segments(it, font, metrics, offset, *args):
    rectangles, painter, _, _, selected, _, _, _, _, hover, _, _, _ = args
    x = 0

    rect = QtCore.QRect(rectangles[DataRect])
    rect.setRight(rectangles[DataRect].right() -
                  common.size(common.WidthMargin) * 1.5)

    o = 0.9 if selected else 0.8
    o = 1.0 if hover else o
    painter.setOpacity(o)
    painter.setPen(QtCore.Qt.NoPen)
    for v in it:
        text, color = v

        color = common.color(common.TextSelectedColor) if selected else color
        color = common.color(common.TextColor) if hover else color

        width = metrics.horizontalAdvance(text)
        rect.setLeft(rect.right() - width)

        if (rectangles[DataRect].left()) >= rect.left():
            rect.setLeft(
                rectangles[DataRect].left())
            text = metrics.elidedText(
                text,
                QtCore.Qt.ElideLeft,
                rect.width()
            )
            width = metrics.horizontalAdvance(text)
            rect.setLeft(rect.right() - width)

        x = rect.center().x() - (width / 2.0) + common.size(common.HeightSeparator)
        y = rect.center().y() + offset

        painter.setBrush(color)
        path = get_painter_path(x, y, font, text)
        painter.drawPath(path)

        rect.translate(-width, 0)

    return x


def draw_subdirs(bg_rect, clickable_rectangles, filter_text, text_edge, *args):
    """Helper method used to draw the subdirectories of file items.

    """
    rectangles, painter, option, index, selected, _, active, _, _, hover, font, metrics, cursor_position = args

    if not bg_rect:
        return

    font, metrics = common.font_db.primary_font(
        font_size=common.size(common.FontSizeSmall))

    # Paint the background rectangle of the subfolder
    modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
    alt_modifier = modifiers & QtCore.Qt.AltModifier
    shift_modifier = modifiers & QtCore.Qt.ShiftModifier
    control_modifier = modifiers & QtCore.Qt.ControlModifier

    k = subdir_rects_key(index, option)
    if k not in common.SUBDIR_RECTS:
        return

    n = -1
    for rect, text in common.SUBDIR_RECTS[k]:
        n += 1
        # Move the rectangle in-place
        rect = QtCore.QRect(rect)
        rect.moveCenter(
            QtCore.QPoint(rect.center().x(),
                          rectangles[DataRect].center().y())
        )

        # add the rectangle as a clickable rectangle
        clickable_rectangles[index.row()].append((rect, text))

        # Skip rectangles that fall out of bounds
        if rect.left() > bg_rect.right():
            continue

        if rect.right() > bg_rect.right():
            rect.setRight(bg_rect.right() - common.size(common.WidthIndicator))

        # Set the hover color based on the keyboard modifier and the fitler text
        o = 0.6 if hover else 0.5
        color = common.color(common.BackgroundDarkColor)

        # Green the subfolder is set as a text filter
        ftext = '"/' + text + '/"'
        if (filter_text and ftext.lower() in filter_text.lower()):
            color = common.color(common.GreenColor)

        if rect.contains(cursor_position):
            o = 1.0
            if alt_modifier:
                color = common.color(common.RedColor)
            if shift_modifier or control_modifier:
                color = common.color(common.GreenColor)

        painter.setOpacity(o)
        painter.setBrush(color)
        o = common.size(common.WidthIndicator)
        if n == 0:
            pen = QtGui.QPen(common.color(common.SeparatorColor))
        else:
            pen = QtGui.QPen(common.color(common.OpaqueColor))

        pen.setWidth(common.size(common.HeightSeparator) * 2.0)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, o, o)

        if metrics.horizontalAdvance(text) > rect.width():
            text = metrics.elidedText(
                text,
                QtCore.Qt.ElideRight,
                rect.width() - (common.size(common.WidthIndicator) * 2)
            )

        x = rect.center().x() - (metrics.horizontalAdvance(text) / 2.0)
        y = option.rect.center().y() + (metrics.ascent() / 2.0)

        color = color.lighter(250)
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        path = get_painter_path(x, y, font, text)
        painter.drawPath(path)


def draw_subdir_background(text_edge, *args):
    """Helper method used to draw file items' subdirectory background."""
    rectangles, painter, option, index, selected, _, active, _, _, hover, font, metrics, cursor_position = args

    k = subdir_rects_key(index, option)
    if k not in common.SUBDIR_RECTS:
        return QtCore.QRect()

    _k = subdir_bg_rect_key(index, option)

    # Calculate and cache the subdir retangles background rectangle
    if common.SUBDIR_RECTS[k] and _k in common.SUBDIR_BG_RECTS:
        bg_rect = common.SUBDIR_BG_RECTS[_k]
    elif common.SUBDIR_RECTS[k] and _k not in common.SUBDIR_BG_RECTS:
        left = min([f[0].left() for f in common.SUBDIR_RECTS[k]])
        right = max([f[0].right() for f in common.SUBDIR_RECTS[k]])
        height = max([f[0].height() for f in common.SUBDIR_RECTS[k]])
        bg_rect = QtCore.QRect(left, 0, right - left, height)

        # Add margin
        o = common.size(common.WidthIndicator)
        bg_rect = bg_rect.adjusted(-o, -o, o * 1.5, o)

        common.SUBDIR_BG_RECTS[_k] = bg_rect

    if common.SUBDIR_RECTS[k]:
        # We have to move the rectangle in-place before painting it
        rect = QtCore.QRect(bg_rect)
        rect.moveCenter(
            QtCore.QPoint(
                rect.center().x(),
                rectangles[BackgroundRect].center().y()
            )
        )
        # Make sure we don't draw over the fle name
        o = common.size(common.WidthIndicator) * 2
        if rect.right() > (text_edge + o):
            rect.setRight(text_edge)
        # Make sure we don't shrink the rectangle too small
        if rect.left() + common.size(common.WidthMargin) < text_edge + o:
            if rect.contains(cursor_position):
                painter.setBrush(QtGui.QColor(0, 0, 0, 80))
            else:
                painter.setBrush(QtGui.QColor(0, 0, 0, 40))
            pen = QtGui.QPen(common.color(common.OpaqueColor))
            pen.setWidthF(common.size(common.HeightSeparator))
            painter.setPen(pen)
            painter.drawRoundedRect(rect, o * 0.66, o * 0.66)
            return rect

    return QtCore.QRect()


def draw_gradient_background(text_edge, *args):
    """Helper method used to draw file items' gradient background."""
    rectangles, painter, option, index, selected, _, active, _, _, hover, font, metrics, cursor_position = args
    k = subdir_bg_rect_key(index, option)

    if k in common.SUBDIR_BG_BRUSHES:
        rect, brush = common.SUBDIR_BG_BRUSHES[k]
    else:
        rect = QtCore.QRect(
            rectangles[ThumbnailRect].right(),
            0,
            text_edge - rectangles[ThumbnailRect].right(),
            option.rect.height(),
        )
        if rectangles[DataRect].center().x() + (rectangles[DataRect].height() * 2) >= text_edge:
            start_x = text_edge - (rectangles[DataRect].height() * 2)
        else:
            start_x = rectangles[DataRect].center().x()

        gradient = QtGui.QLinearGradient()
        gradient.setStart(
            QtCore.QPoint(
                start_x,
                0,
            )
        )
        gradient.setFinalStop(
            QtCore.QPoint(
                text_edge,
                0
            )
        )
        gradient.setSpread(QtGui.QGradient.PadSpread)
        gradient.setColorAt(0, common.color(common.BackgroundDarkColor))
        gradient.setColorAt(1.0, common.color(common.Transparent))
        brush = QtGui.QBrush(gradient)

        common.SUBDIR_BG_BRUSHES[k] = (rect, brush)

    rect.moveCenter(
        QtCore.QPoint(
            rect.center().x(),
            rectangles[BackgroundRect].center().y()
        )
    )
    painter.setBrush(brush)
    painter.drawRect(rect)


def draw_description(clickable_rectangles, left_limit, right_limit, offset, *args):
    """Helper method used to draw file items' descriptions."""
    rectangles, painter, option, index, selected, _, active, _, _, hover, font, metrics, cursor_position = args

    color = common.color(common.TextSelectedColor) if selected else common.color(
        common.GreenColor)

    large_mode = option.rect.height() >= (common.size(common.HeightRow) * 2)
    if large_mode:
        left_limit = rectangles[DataRect].left()
        right_limit = rectangles[DataRect].right(
        ) - common.size(common.WidthMargin)
        font, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium))
    else:
        font, metrics = common.font_db.primary_font(
            common.size(common.FontSizeSmall))

    text = index.data(common.DescriptionRole)
    text = metrics.elidedText(
        text,
        QtCore.Qt.ElideLeft,
        right_limit - left_limit
    )
    width = metrics.horizontalAdvance(text)

    x = right_limit - width
    y = rectangles[DataRect].center().y() + offset
    if large_mode:
        y += metrics.lineSpacing()

    rect = QtCore.QRect()
    rect.setHeight(metrics.height())
    center = QtCore.QPoint(rectangles[DataRect].center().x(), y)
    rect.moveCenter(center)
    rect.setLeft(left_limit)
    rect.setRight(right_limit)
    clickable_rectangles[index.row()].insert(
        0, (rect, index.data(common.DescriptionRole)))

    if rectangles[DataRect].contains(cursor_position):
        rect = QtCore.QRect(rectangles[DataRect])
        rect.setHeight(common.size(common.HeightSeparator))
        rect.moveTop(y)
        rect.setLeft(left_limit)
        rect.setRight(right_limit)

        painter.setOpacity(0.3)
        painter.setBrush(common.color(common.SeparatorColor))
        painter.drawRect(rect)
        painter.setOpacity(1.0)
        color = common.color(common.TextSelectedColor)

    painter.setBrush(color)
    path = get_painter_path(x, y, font, text)
    painter.drawPath(path)


class BaseDelegate(QtWidgets.QAbstractItemDelegate):
    """The main delegate used to represent lists derived from `base.BaseListWidget`.

    """
    fallback_thumb = 'placeholder'

    def __init__(self, parent=None):
        super(BaseDelegate, self).__init__(parent=parent)
        self._clickable_rectangles = {}

    def paint(self, painter, option, index):
        raise NotImplementedError(
            '`paint()` is abstract and has to be overriden in the subclass!')

    def get_paint_arguments(self, painter, option, index, antialiasing=True):
        """A utility class for gathering all the arguments needed to paint
        the individual list elements.

        """
        if antialiasing:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
            painter.setRenderHint(
                QtGui.QPainter.SmoothPixmapTransform, on=True)
        else:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, on=False)
            painter.setRenderHint(
                QtGui.QPainter.SmoothPixmapTransform, on=False)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)

        selected = option.state & QtWidgets.QStyle.State_Selected
        focused = option.state & QtWidgets.QStyle.State_HasFocus
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        flags = index.flags()
        favourite = flags & common.MarkedAsFavourite
        archived = flags & common.MarkedAsArchived
        active = flags & common.MarkedAsActive
        rectangles = get_rectangles(
            option.rect, self.parent().inline_icons_count())
        font, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium))
        painter.setFont(font)

        cursor_position = self.parent().mapFromGlobal(common.cursor.pos())

        args = (
            rectangles,
            painter,
            option,
            index,
            selected,
            focused,
            active,
            archived,
            favourite,
            hover,
            font,
            metrics,
            cursor_position
        )
        return args

    def get_clickable_rectangles(self, index):
        """Clickable rectangles are used by the the QListView to identify
        interactive/clickable regions.

        The delegate is responsible for painting any pseudo item buttons, such
        as item names or in-line buttons and hence, we rely on the delegate
        to calculate where these rectagles are.

        Because calculating these rectangles on each paint operation would come with
        a performance hit we back the operation with a cache and return
        only already cached result when a request is made.

        Args:
            index (QtCore.QModelIndex):

        Returns:
            dict: A list of QRects where clickable regions are found.

        """
        if index.row() in self._clickable_rectangles:
            return self._clickable_rectangles[index.row()]
        return {}

    @paintmethod
    def paint_name(self, *args):
        pass

    @paintmethod
    def paint_description_editor_background(self, *args, **kwargs):
        """Overlay do indicate the source of a drag operation."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        if index != self.parent().selectionModel().currentIndex():
            return
        if not self.parent().description_editor_widget.isVisible():
            return

        painter.setBrush(common.color(common.BackgroundDarkColor))
        painter.setPen(QtCore.Qt.NoPen)
        rect = QtCore.QRect(rectangles[BackgroundRect])
        rect.setLeft(rectangles[ThumbnailRect].right())

        o = common.size(common.WidthIndicator) * 0.5
        painter.drawRoundedRect(rect, o, o)

    @paintmethod
    def paint_thumbnail(self, *args):
        """Paints an item's thumbnail.

        If a requested QPixmap has never been drawn before we will create and
        store it by calling `images.get_thumbnail(*args)`. This method is backed
        by `images.ImageCache` and stores the requested pixmaps for future use.

        If no associated image data is available, we will use a generic
        thumbnail associated with the item's type, or a fallback thumbnail set
        by the delegate. at `self.fallback_thumb`.

        See the `images` module for implementation details.

        """
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        painter.setBrush(common.color(common.SeparatorColor))
        painter.drawRect(rectangles[ThumbnailRect])

        if not index.data(common.ParentPathRole):
            return

        server, job, root = index.data(common.ParentPathRole)[0:3]
        source = index.data(QtCore.Qt.StatusTipRole)

        _h = index.data(QtCore.Qt.SizeHintRole)
        if not source or not _h:
            return
        size = _h.height()

        pixmap, color = images.get_thumbnail(
            server,
            job,
            root,
            source,
            size,
            fallback_thumb=self.fallback_thumb
        )

        # Background
        o = 1.0 if selected or active or hover else 0.9
        painter.setOpacity(o)

        color = color if color else common.color(common.SeparatorColor)
        # Paint a generic thumbnail background color
        painter.setBrush(color)
        painter.drawRect(rectangles[ThumbnailRect])

        if not pixmap:
            return

        # Let's make sure the image is fully fitted, even if the image's size
        # doesn't match ThumbnailRect
        s = float(rectangles[ThumbnailRect].height())
        longest_edge = float(max((pixmap.width(), pixmap.height())))
        ratio = s / longest_edge
        w = pixmap.width() * ratio
        h = pixmap.height() * ratio

        _rect = QtCore.QRect(0, 0, int(w), int(h))
        _rect.moveCenter(rectangles[ThumbnailRect].center())
        painter.drawPixmap(_rect, pixmap, pixmap.rect())

    def paint_thumbnail_drop_indicator(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        drop = self.parent()._thumbnail_drop
        if drop[1] and drop[0] == index.row():
            painter.setOpacity(0.9)
            painter.setBrush(common.color(common.SeparatorColor))
            painter.drawRect(option.rect)

            painter.setPen(common.color(common.GreenColor))
            font, metrics = common.font_db.secondary_font(
                common.size(common.FontSizeSmall))
            painter.setFont(font)

            text = 'Drop image to add as thumbnail'
            painter.drawText(
                option.rect.adjusted(common.size(
                    common.WidthMargin), 0, -common.size(common.WidthMargin), 0),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
                text,
                boundingRect=option.rect,
            )

            o = common.size(common.HeightSeparator) * 2.0
            rect = rectangles[ThumbnailRect].adjusted(o, o, -o, -o)
            painter.drawRect(rect)

            pen = QtGui.QPen(common.color(common.GreenColor))
            pen.setWidth(o)
            painter.setPen(pen)
            painter.setBrush(common.color(common.GreenColor))
            painter.setOpacity(0.5)
            pixmap = images.ImageCache.get_rsc_pixmap(
                'add', common.color(common.GreenColor), rect.height() * 0.5)
            painter.drawRect(rect)
            irect = pixmap.rect()
            irect.moveCenter(rect.center())
            painter.drawPixmap(irect, pixmap, pixmap.rect())

    @paintmethod
    def paint_background(self, *args):
        """Paints the background for all list items."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        rect = QtCore.QRect(rectangles[BackgroundRect])
        if index.row() == (self.parent().model().rowCount() - 1):
            rect.setHeight(rect.height() + common.size(common.HeightSeparator))

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        color = common.color(common.BackgroundLightColor) if selected else common.color(
            common.BackgroundColor)
        painter.setBrush(color)

        painter.setOpacity(1.0)
        painter.drawRect(rect)

        # Setting the opacity of the separator
        if index.row() != (self.parent().model().rowCount() - 1):
            painter.setOpacity(0.5)
            painter.setBrush(color)
            _rect = QtCore.QRect(rect)
            _rect.setBottom(_rect.bottom() +
                            common.size(common.WidthIndicator))
            _rect.setTop(_rect.bottom() - common.size(common.WidthIndicator))
            _rect.setLeft(common.size(common.WidthIndicator) +
                          option.rect.height() - common.size(common.HeightSeparator))
            painter.drawRect(_rect)

        # Active indicator
        if active:
            rect.setLeft(option.rect.left() +
                         common.size(common.WidthIndicator) + option.rect.height())
            painter.setOpacity(0.5)
            painter.setBrush(common.color(common.GreenColor))
            painter.drawRoundedRect(
                rect, common.size(common.WidthIndicator), common.size(common.WidthIndicator))
            painter.setOpacity(0.8)
            pen = QtGui.QPen(common.color(common.GreenColor))
            pen.setWidth(common.size(common.HeightSeparator) * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            o = common.size(common.HeightSeparator)
            rect = rect.adjusted(o, o, -(o * 1.5), -(o * 1.5))
            painter.drawRoundedRect(
                rect, common.size(common.WidthIndicator), common.size(common.WidthIndicator))

        # Hover indicator
        if hover:
            painter.setBrush(HOVER_COLOR)
            painter.drawRect(rect)

    @paintmethod
    def paint_simple_background(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        rect = QtCore.QRect(rectangles[BackgroundRect])
        rect.setLeft(rectangles[ThumbnailRect].right() +
                     common.size(common.WidthIndicator))

        color = common.color(common.BackgroundLightColor) if selected else common.color(
            common.BackgroundDarkColor)
        painter.setBrush(color)
        painter.drawRect(rect)
        if hover:
            painter.setBrush(HOVER_COLOR)
            painter.drawRect(rect)

        # Active indicator
        if active:
            painter.setOpacity(0.5)
            painter.setBrush(common.color(common.GreenColor))
            painter.drawRoundedRect(
                rect, common.size(common.WidthIndicator), common.size(common.WidthIndicator))
            painter.setOpacity(0.8)
            pen = QtGui.QPen(common.color(common.GreenColor))
            pen.setWidth(common.size(common.HeightSeparator) * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            o = common.size(common.HeightSeparator)
            rect = rect.adjusted(o, o, -(o * 1.5), -(o * 1.5))
            painter.drawRoundedRect(
                rect, common.size(common.WidthIndicator), common.size(common.WidthIndicator))

    @paintmethod
    def paint_inline_background(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        if rectangles[InlineBackgroundRect].left() < rectangles[ThumbnailRect].right():
            return

        if index.row() == (self.parent().model().rowCount() - 1):
            rect = QtCore.QRect(rectangles[InlineBackgroundRect])
            rect.setHeight(rect.height() + common.size(common.HeightSeparator))
        else:
            rect = rectangles[InlineBackgroundRect]

        painter.setBrush(common.color(common.SeparatorColor))
        painter.setOpacity(0.6) if rect.contains(
            cursor_position) else painter.setOpacity(0.4)
        painter.drawRect(rect)

    @paintmethod
    def paint_inline_icons(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        if rectangles[InlineBackgroundRect].left() < rectangles[ThumbnailRect].right():
            return

        painter.setOpacity(1) if hover else painter.setOpacity(0.66)

        self._paint_inline_favourite(*args)
        self._paint_inline_archived(*args)
        self._paint_inline_reveal(*args)
        self._paint_inline_todo(*args)
        self._paint_inline_add(*args)
        self._paint_inline_properties(*args)

    @paintmethod
    def _paint_inline_favourite(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[FavouriteRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position) or favourite:
            painter.setOpacity(1.0)

        color = QtGui.QColor(255, 255, 255, 150) if rect.contains(
            cursor_position) else common.color(common.SeparatorColor)
        color = common.color(common.TextSelectedColor) if favourite else color
        pixmap = images.ImageCache.get_rsc_pixmap(
            'favourite', color, common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap)

    @paintmethod
    def _paint_inline_archived(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[ArchiveRect]
        if not rect:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(
            common.GreenColor) if archived else common.color(common.RedColor)
        color = color if rect.contains(
            cursor_position) else common.color(common.SeparatorColor)
        if archived:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'archivedVisible', common.color(common.GreenColor), common.size(common.WidthMargin))
        else:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'archivedHidden', color, common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap)

    @paintmethod
    def _paint_inline_reveal(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[RevealRect]
        if not rect or archived:
            return
        if rect.contains(cursor_position):
            painter.setOpacity(1.0)
        color = common.color(common.TextSelectedColor) if rect.contains(
            cursor_position) else common.color(common.SeparatorColor)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'folder', color, common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap)

    @paintmethod
    def _paint_inline_todo(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[TodoRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(common.TextSelectedColor) if rect.contains(
            cursor_position) else common.color(common.SeparatorColor)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'todo', color, common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap)

        count = index.data(common.TodoCountRole)
        self.draw_count(painter, rect, cursor_position, count, 'add')

    @paintmethod
    def _paint_inline_add(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[AddAssetRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(common.GreenColor) if rect.contains(
            cursor_position) else common.color(common.SeparatorColor)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'add_circle', color, common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap)

        if len(index.data(common.ParentPathRole)) == 3:
            count = index.data(common.AssetCountRole)
            self.draw_count(painter, rect, cursor_position, count, 'asset')

    @paintmethod
    def _paint_inline_properties(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        rect = rectangles[PropertiesRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)
        color = common.color(common.TextSelectedColor) if rect.contains(
            cursor_position) else common.color(common.SeparatorColor)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'settings', color, common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap)

    def draw_count(self, painter, rect, cursor_position, count, icon):
        if not isinstance(count, (float, int)):
            return

        size = common.size(common.FontSizeLarge)
        count_rect = QtCore.QRect(0, 0, size, size)
        count_rect.moveCenter(rect.bottomRight())
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        if rect.contains(cursor_position):
            pixmap = images.ImageCache.get_rsc_pixmap(
                icon, common.color(common.GreenColor), size)
            painter.drawPixmap(count_rect, pixmap)
            return

        if count < 1:
            return

        color = common.color(common.BlueColor)
        painter.setBrush(color)
        painter.drawRoundedRect(
            count_rect, count_rect.width() / 2.0, count_rect.height() / 2.0)

        text = '{}'.format(count)
        _font, _metrics = common.font_db.primary_font(
            font_size=common.size(common.FontSizeSmall))
        x = count_rect.center().x() - (_metrics.horizontalAdvance(text) / 2.0) + \
            common.size(common.HeightSeparator)
        y = count_rect.center().y() + (_metrics.ascent() / 2.0)

        painter.setBrush(common.color(common.TextColor))
        path = get_painter_path(x, y, _font, text)
        painter.drawPath(path)

    @paintmethod
    def paint_selection_indicator(self, *args):
        """Paints the leading rectangle indicating the selection."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[IndicatorRect]
        color = common.color(common.TextSelectedColor) if selected else common.color(
            common.Transparent)
        painter.setBrush(color)
        painter.drawRect(rect)

    @paintmethod
    def paint_thumbnail_shadow(self, *args):
        """Paints a drop-shadow"""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = QtCore.QRect(rectangles[ThumbnailRect])
        rect.moveLeft(rect.right() + 1)

        painter.setOpacity(0.5)

        pixmap = images.ImageCache.get_rsc_pixmap(
            'gradient', None, rect.height())

        rect.setWidth(common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.size(common.WidthMargin) * 0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.size(common.WidthMargin) * 1.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_inline_background_shadow(self, *args):
        """Paints a drop-shadow"""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        if self.parent().buttons_hidden():
            return
        if rectangles[InlineBackgroundRect].left() < rectangles[ThumbnailRect].right():
            return

        rect = QtCore.QRect(rectangles[InlineBackgroundRect])
        rect.setHeight(rect.height() + common.size(common.HeightSeparator))

        painter.setOpacity(0.5)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'gradient', None, rect.height())

        rect.setWidth(common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.size(common.WidthMargin) * 0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_archived(self, *args):
        """Paints a gray overlay when an item is archived."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not archived:
            return
        painter.setBrush(common.color(common.SeparatorColor))
        painter.setOpacity(0.8)
        painter.drawRect(option.rect)

    @paintmethod
    def paint_persistent(self, *args):
        """Paints a gray overlay when an item is archived."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not index.data(common.FlagsRole) & common.MarkedAsPersistent:
            return
        painter.setBrush(common.color(common.BlueColor))
        painter.setOpacity(0.5)
        painter.drawRect(option.rect)

    @paintmethod
    def paint_shotgun_status(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return
        if not index.data(common.ShotgunLinkedRole):
            return

        rect = QtCore.QRect(0, 0, common.size(
            common.WidthMargin), common.size(common.WidthMargin))

        offset = QtCore.QPoint(common.size(common.WidthIndicator),
                               common.size(common.WidthIndicator))
        rect.moveBottomRight(
            rectangles[ThumbnailRect].bottomRight() - offset)
        painter.setOpacity(0.9) if hover else painter.setOpacity(0.8)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'sg', common.color(common.TextColor), common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap, pixmap.rect())


class BookmarksWidgetDelegate(BaseDelegate):
    """The delegate used to paint the bookmark items."""
    fallback_thumb = 'thumb_bookmark0'

    def paint(self, painter, option, index):
        """Defines how the ``BookmarksWidget`` should be painted."""
        args = self.get_paint_arguments(
            painter, option, index, antialiasing=False)

        self.paint_background(*args)
        self.paint_persistent(*args)
        self.paint_thumbnail(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_name(*args)
        self.paint_archived(*args)
        self.paint_inline_background(*args)
        self.paint_inline_background_shadow(*args)
        self.paint_inline_icons(*args)
        self.paint_description_editor_background(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)
        self.paint_shotgun_status(*args)

    def get_description_rect(self, *args):
        """We don't have editable descriptions for bookmark items."""
        return QtCore.QRect()

    def get_text_segments(self, index):
        """Returns a tuple of text and colour information to be used to mimick
        rich-text like colouring of individual text elements.

        Used by the list delegate to paint the job name and root folder.

        """
        text = index.data(QtCore.Qt.DisplayRole)
        if not text:
            return {}
        description = index.data(common.DescriptionRole)
        description = description if description else ''

        k = text + description
        if k in common.TEXT_SEGMENT_CACHE:
            return common.TEXT_SEGMENT_CACHE[k]

        text = text.strip().strip('/').strip('\\')
        if not text:
            return {}

        d = {}
        v = text.split('|')

        s_color = common.color(common.BlueColor).darker(250)

        for i, s in enumerate(v):
            if i == 0:
                c = common.color(common.BlueColor).darker(250)
            else:
                c = common.color(common.TextColor)

            _v = s.split('/')
            for _i, _s in enumerate(_v):
                _s = _s.strip()
                d[len(d)] = (_s, c)
                if _i < (len(_v) - 1):
                    d[len(d)] = (' / ', s_color)
            if i < (len(v) - 1):
                d[len(d)] = ('   |    ', s_color)

        if description:
            d[len(d)] = ('   |   ', s_color)
            d[len(d)] = (description, s_color)

        common.TEXT_SEGMENT_CACHE[k] = d
        return common.TEXT_SEGMENT_CACHE[k]

    @paintmethod
    def paint_name(self, *args):
        """Paints name of the ``BookmarkWidget``'s items."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return

        # The description rectangle for bookmark items is not clickable,
        # unlike on asset and files items
        self._clickable_rectangles[index.row()] = [
            (self.get_description_rect(rectangles, index),
             index.data(common.DescriptionRole)),
        ]

        _datarect = QtCore.QRect(rectangles[DataRect])
        if not self.parent().buttons_hidden():
            rectangles[DataRect].setRight(
                rectangles[DataRect].right() - common.size(common.WidthMargin))

        if hover or selected or active:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.66)

        # If the text segments role has not yet been set, we'll set it here
        text_segments = self.get_text_segments(index)
        text = ''.join([text_segments[f][0] for f in text_segments])

        rect = rectangles[DataRect]
        rect.setLeft(rect.left() + common.size(common.WidthMargin))

        # First let's paint the background rectangle
        o = common.size(common.WidthIndicator)

        text_width = metrics.horizontalAdvance(text)
        r = QtCore.QRect(rect)
        r.setWidth(text_width)
        center = r.center()
        r.setHeight(metrics.height())
        r.moveCenter(center)
        r = r.adjusted(-(o * 3), -o, o * 3, o)
        if (r.right() + o) > rect.right():
            r.setRight(rect.right() - o)

        if r.left() + common.size(common.WidthMargin) > r.right():
            rectangles[DataRect] = _datarect
            return

        # Let's save the rectangle as a clickable rect
        self._clickable_rectangles[index.row()].append(
            (r, index.data(common.ParentPathRole)[1])
        )

        # Let's paint the background rectangle
        color = common.color(common.GreenColor).darker(
            120) if active else common.color(common.BlueColor).darker(120)
        color = common.color(common.GreenColor).darker(150) if r.contains(
            cursor_position) else color
        f_subpath = '"/' + index.data(common.ParentPathRole)[1] + '/"'

        filter_text = self.parent().model().filter_text()
        if filter_text:
            if f_subpath.lower() in filter_text.lower():
                color = common.color(common.GreenColor).darker(120)

        painter.setBrush(color)
        pen = QtGui.QPen(color.darker(220))
        pen.setWidth(common.size(common.HeightSeparator))
        painter.setPen(pen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        painter.drawRoundedRect(
            r, common.size(common.WidthIndicator), common.size(common.WidthIndicator))

        offset = 0
        painter.setPen(QtCore.Qt.NoPen)
        for segment in text_segments.values():
            text, color = segment
            width = metrics.horizontalAdvance(text)
            _r = QtCore.QRect(rect)
            _r.setWidth(width)
            center = _r.center()
            _r.setHeight(metrics.ascent())
            _r.moveCenter(center)
            _r.moveLeft(_r.left() + offset)

            if _r.left() >= rect.right():
                break

            if (_r.right() + o) > rect.right():
                _r.setRight(rect.right() - o)
                text = metrics.elidedText(
                    text,
                    QtCore.Qt.ElideRight,
                    _r.width()
                )

            painter.setBrush(color)
            x = _r.x()
            y = _r.bottom()
            path = path = get_painter_path(x, y, font, text)
            painter.drawPath(path)

            offset += width

        rectangles[DataRect] = _datarect

    def sizeHint(self, option, index):
        return self.parent().model().sourceModel().row_size()


class AssetsWidgetDelegate(BaseDelegate):
    """Delegate used by the ``AssetsWidget`` to display the collecteds assets."""
    fallback_thumb = 'thumb_asset0'

    def paint(self, painter, option, index):
        """Defines how the ``AssetsWidget``'s' items should be painted."""
        # The index might still be populated...
        if index.data(QtCore.Qt.DisplayRole) is None:
            return
        args = self.get_paint_arguments(
            painter, option, index, antialiasing=False)
        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_name(*args)
        self.paint_archived(*args)
        self.paint_description_editor_background(*args)
        self.paint_inline_background(*args)
        self.paint_inline_background_shadow(*args)
        self.paint_inline_icons(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)
        self.paint_shotgun_status(*args)

    def get_description_rect(self, rectangles, index):
        """Returns the description area of an ``AssetsWidget`` item."""
        k = '/'.join([repr(v) for v in rectangles.values()])
        if k in common.DESCRIPTION_RECTS:
            return common.DESCRIPTION_RECTS[k]

        if not index.isValid():
            return

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + common.size(common.WidthMargin))

        _, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium))

        name_rect = QtCore.QRect(rect)
        center = name_rect.center()
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(center)

        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(
                    name_rect.center().x(),
                    name_rect.center().y() - (metrics.lineSpacing() / 2.0)
                )
            )

        description_rect = QtCore.QRect(name_rect)
        description_rect.moveCenter(
            QtCore.QPoint(
                name_rect.center().x(),
                name_rect.center().y() + metrics.lineSpacing()
            )
        )
        description_rect.setRight(
            description_rect.right() - common.size(common.WidthMargin))

        common.DESCRIPTION_RECTS[k] = description_rect
        return common.DESCRIPTION_RECTS[k]

    @paintmethod
    def paint_name(self, *args):
        """Paints the item names inside the ``AssetsWidget``."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        rect = QtCore.QRect(rectangles[DataRect])
        rect.setRight(rect.right() - common.size(common.WidthMargin))
        rect.setLeft(rect.left() + common.size(common.WidthMargin))

        # Name
        color = common.color(
            common.TextSelectedColor) if hover else common.color(common.TextColor)
        color = common.color(common.TextSelectedColor) if selected else color
        painter.setBrush(color)

        name_rect = QtCore.QRect(rect)
        center = name_rect.center()
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(center)

        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        text = index.data(QtCore.Qt.DisplayRole)
        text = metrics.elidedText(
            text.upper(),
            QtCore.Qt.ElideRight,
            name_rect.width()
        )

        x = name_rect.left()
        y = name_rect.center().y() + (metrics.ascent() / 2.0)
        path = get_painter_path(x, y, font, text)
        painter.drawPath(path)

        description_rect = QtCore.QRect(name_rect)
        description_rect.moveCenter(
            QtCore.QPoint(name_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )
        description_rect.setWidth(
            description_rect.width() - common.size(common.WidthMargin))

        color = common.color(common.TextColor) if hover else common.color(
            common.TextSecondaryColor)
        color = common.color(common.TextSelectedColor) if selected else color
        painter.setBrush(color)

        text = index.data(common.DescriptionRole)
        text = text if text else ''
        font, _metrics = common.font_db.primary_font(
            font_size=common.size(common.FontSizeMedium))
        painter.setFont(font)
        text = _metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            description_rect.width()
        )

        if description_rect.contains(cursor_position):
            underline_rect = QtCore.QRect(description_rect)
            underline_rect.setTop(underline_rect.bottom())
            underline_rect.moveTop(
                underline_rect.top() + common.size(common.HeightSeparator))
            painter.setOpacity(0.5)
            painter.setBrush(common.color(common.SeparatorColor))
            painter.drawRect(underline_rect)

            painter.setOpacity(1.0)
            if not text:
                painter.setBrush(common.color(common.TextSecondaryColor))
            else:
                painter.setBrush(color)
            text = 'Double-click to edit...' if not text else text

        x = description_rect.left()
        y = description_rect.center().y() + (metrics.ascent() / 2.0)
        path = get_painter_path(x, y, font, text)
        painter.drawPath(path)

    def sizeHint(self, option, index):
        return self.parent().model().sourceModel().row_size()


class FilesWidgetDelegate(BaseDelegate):
    """QAbstractItemDelegate associated with ``FilesWidget``."""
    MAX_SUBDIRS = 6

    def __init__(self, parent=None):
        super(FilesWidgetDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """Defines how the ``FilesWidget``'s' items should be painted."""

        args = self.get_paint_arguments(
            painter, option, index, antialiasing=False)

        if not index.data(QtCore.Qt.DisplayRole):
            return

        b_hidden = self.parent().buttons_hidden()
        p_role = index.data(common.ParentPathRole)
        if p_role and not b_hidden:
            self.paint_background(*args)
        elif p_role and b_hidden:
            self.paint_simple_background(*args)

        self.paint_thumbnail(*args)

        if p_role and not b_hidden:
            self.paint_name(*args)
        elif p_role and b_hidden:
            self.paint_simple_name(*args)

        self.paint_archived(*args)
        self.paint_inline_background(*args)
        self.paint_inline_icons(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)
        self.paint_description_editor_background(*args)
        self.paint_drag_source(*args)

    def get_description_rect(self, rectangles, index):
        """The description rectangle of a file item."""
        k = '/'.join([repr(v) for v in rectangles.values()])
        if k in common.DESCRIPTION_RECTS:
            return common.DESCRIPTION_RECTS[k]

        if self.parent().buttons_hidden():
            rect = self.get_simple_description_rectangle(rectangles, index)
        else:
            clickable = self.get_clickable_rectangles(index)
            if not clickable:
                rect = QtCore.QRect()
            else:
                rect = clickable[0][0]

        common.DESCRIPTION_RECTS[k] = rect
        return common.DESCRIPTION_RECTS[k]

    @paintmethod
    def paint_name(self, *args):
        """Paints the subfolders and the filename of the current file inside the ``FilesWidget``."""
        rectangles, painter, option, index, _, _, _, _, _, _, font, metrics, _ = args
        self._clickable_rectangles[index.row()] = []

        # slider_down = self.parent().verticalScrollBar().isSliderDown()
        # if slider_down:

        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        font, metrics = common.font_db.primary_font(
            font_size=common.size(common.FontSizeSmall) + 1)
        offset = 0

        self.get_subdir_rectangles(option, index, rectangles, metrics)

        painter.save()
        it = self.get_text_segments(index).values()
        left = draw_segments(it, font, metrics, offset, *args)
        painter.restore()

        painter.save()
        draw_gradient_background(left - common.size(common.WidthMargin), *args)
        painter.restore()

        painter.save()
        bg_rect = draw_subdir_background(
            left - common.size(common.WidthMargin), *args)
        painter.restore()

        painter.save()
        it = self.get_filedetail_text_segments(index).values()
        offset = metrics.ascent()
        font, metrics = common.font_db.primary_font(
            font_size=common.size(common.FontSizeSmall) * 0.95)
        left = draw_segments(it, font, metrics, offset, *args)
        painter.restore()

        painter.save()
        draw_description(
            self._clickable_rectangles, bg_rect.right(), left - common.size(common.WidthIndicator), offset, *args)
        painter.restore()

        painter.save()
        filter_text = self.parent().model().filter_text()
        draw_subdirs(
            bg_rect,
            self._clickable_rectangles,
            filter_text,
            left - common.size(common.WidthMargin),
            *args
        )
        painter.restore()

    @paintmethod
    def paint_simple_name(self, *args):
        """Paints an the current file-names in a simpler form, with only the
        filename and the description visible.

        """
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + (common.size(common.WidthIndicator) * 2))

        # File-name
        name_rect = QtCore.QRect(rect)
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(rect.center())

        _text_segments = {}
        text_segments = self.get_text_segments(index)
        for idx in text_segments:
            _text_segments[idx] = text_segments[(len(text_segments) - 1) - idx]

        if index.data(common.DescriptionRole):
            _text_segments[len(_text_segments)] = (
                '  |  ', common.color(common.SeparatorColor))
            _text_segments[len(_text_segments)] = (
                index.data(common.DescriptionRole),
                common.color(common.GreenColor)
            )

        painter.setPen(common.color(common.TextColor))
        painter.setBrush(QtCore.Qt.NoBrush)
        font, metrics = common.font_db.primary_font(
            font_size=common.size(common.FontSizeSmall) * 1.1)

        offset = 0

        o = 0.9 if hover else 0.75
        o = 1.0 if selected else o
        painter.setOpacity(o)
        painter.setPen(QtCore.Qt.NoPen)

        for k in _text_segments:
            text, color = _text_segments[k]
            r = QtCore.QRect(name_rect)
            width = metrics.horizontalAdvance(text)
            r.setWidth(width)
            r.moveLeft(rect.left() + offset)
            offset += width

            if r.left() > rect.right():
                break
            if r.right() > rect.right():
                r.setRight(rect.right() - (common.size(common.WidthIndicator)))
                text = metrics.elidedText(
                    text,
                    QtCore.Qt.ElideRight,
                    r.width() - 6
                )

            x = r.center().x() - (metrics.horizontalAdvance(text) / 2.0)
            y = r.center().y() + (metrics.ascent() / 2.0)

            painter.setBrush(color)
            path = get_painter_path(x, y, font, text)
            painter.drawPath(path)

    @paintmethod
    def paint_drag_source(self, *args, **kwargs):
        """Overlay do indicate the source of a drag operation."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        if not self.parent().drag_source_index.isValid():
            return
        if index == self.parent().drag_source_index:
            painter.setBrush(common.color(common.SeparatorColor))
            painter.drawRect(option.rect)

            painter.setPen(common.color(common.BackgroundColor))
            font, metrics = common.font_db.secondary_font(
                common.size(common.FontSizeSmall))
            painter.setFont(font)

            text = '"Drag+Shift" grabs all files    |    "Drag+Alt" grabs the first file    |    "Drag+Shift+Alt" grabs the parent folder'
            painter.drawText(
                option.rect.adjusted(common.size(
                    common.WidthMargin), 0, -common.size(common.WidthMargin), 0),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
                text,
                boundingRect=option.rect,
            )
        else:
            painter.setOpacity(0.66)
            painter.setBrush(common.color(common.SeparatorColor))
            painter.drawRect(option.rect)

    def get_simple_description_rectangle(self, rectangles, index):
        if not index.isValid():
            return

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + (common.size(common.WidthIndicator) * 2))

        _, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium))

        # File-name
        name_rect = QtCore.QRect(rect)
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(rect.center())
        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        text_segments = self.get_text_segments(index)
        font, metrics = common.font_db.primary_font(
            font_size=common.size(common.FontSizeSmall) * 1.1)

        offset = 0
        for k in sorted(text_segments, reverse=True):
            text, _ = text_segments[k]
            r = QtCore.QRect(name_rect)
            width = metrics.horizontalAdvance(text)
            r.setWidth(width)
            r.moveLeft(rect.left() + offset)
            offset += width

            if r.left() > rect.right():
                break
            if r.right() > rect.right():
                r.setRight(rect.right() - (common.size(common.WidthIndicator)))

        font, metrics = common.font_db.secondary_font(
            font_size=common.size(common.FontSizeSmall) * 1.2)

        description_rect = QtCore.QRect(name_rect)
        description_rect = QtCore.QRect(rect)
        description_rect.setHeight(metrics.height())
        description_rect.moveCenter(rect.center())
        description_rect.moveCenter(
            QtCore.QPoint(description_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )
        return description_rect

    def get_text_segments(self, index):
        """Returns the `FilesWidget` item `DisplayRole` segments associated with
        custom colors. It is used to paint the FilesWidget items' extension,
        name, and sequence.

        Args:
            index (QModelIndex): The index currently being painted.

        Returns:
            dict: A dictionary of tuples. (str, QtGui.QColor)

        """
        if not index.isValid():
            return {}
        s = index.data(QtCore.Qt.DisplayRole)
        if not s:
            return {}

        k = index.data(QtCore.Qt.StatusTipRole)
        if k in common.TEXT_SEGMENT_CACHE:
            return common.TEXT_SEGMENT_CACHE[k]

        s = regex_remove_version.sub(r'\1\3', s)
        d = {}
        # Item is a collapsed sequence
        match = common.is_collapsed(s)
        if match:
            # Suffix + extension
            s = match.group(3).split('.')
            s = '.'.join(s[:-1]).upper() + '.' + s[-1].lower()
            d[len(d)] = (s, common.color(common.TextColor))

            # Frame-range without the "[]" characters
            s = match.group(2)
            s = regex_remove_seq_marker.sub('', s)
            if len(s) > 17:
                s = s[0:8] + '...' + s[-8:]
            if len(index.data(common.FramesRole)) > 1:
                d[len(d)] = (s, common.color(common.RedColor))
            else:
                d[len(d)] = (s, common.color(common.TextColor))

            # Filename
            d[len(d)] = (
                match.group(1).upper(), common.color(common.TextSelectedColor))
            common.TEXT_SEGMENT_CACHE[k] = d
            return d

        # Item is a non-collapsed sequence
        match = common.get_sequence(s)
        if match:
            # The extension and the suffix
            if match.group(4):
                s = match.group(3).upper() + '.' + match.group(4).lower()
            else:
                s = match.group(3).upper()
            d[len(d)] = (s, common.color(common.TextSelectedColor))

            # Sequence
            d[len(d)] = (match.group(
                2).upper(), common.color(common.TextSecondaryColor))

            # Prefix
            d[len(d)] = (
                match.group(1).upper(), common.color(common.TextSelectedColor))
            common.TEXT_SEGMENT_CACHE[k] = d
            return d

        # Items is not collapsed and it isn't a sequence either
        s = s.split('.')
        if len(s) > 1:
            s = '.'.join(s[:-1]).upper() + '.' + s[-1].lower()
        else:
            s = s[0].upper()
        d[len(d)] = (s, common.color(common.TextSelectedColor))
        common.TEXT_SEGMENT_CACHE[k] = d
        return d

    def get_filedetail_text_segments(self, index):
        """Returns the `FilesWidget` item `common.FileDetailsRole` segments
        associated with custom colors.

        Args:
            index (QModelIndex): The index currently being painted.

        Returns:
            dict: A dictionary of tuples "{0: (str, QtGui.QColor)}".

        """
        k = index.data(common.FileDetailsRole)
        if k in common.TEXT_SEGMENT_CACHE:
            return common.TEXT_SEGMENT_CACHE[k]

        d = {}

        if not index.data(common.FileInfoLoaded):
            d[len(d)] = ('...', common.color(common.TextSecondaryColor))
            return d

        text = index.data(common.FileDetailsRole)
        texts = text.split(';')
        for n, text in enumerate(reversed(texts)):
            d[len(d)] = (text, common.color(common.TextSecondaryColor))
            if n == (len(texts) - 1) and not index.data(common.DescriptionRole):
                break
            d[len(d)] = ('  |  ', common.color(common.BackgroundDarkColor))

        common.TEXT_SEGMENT_CACHE[k] = d
        return common.TEXT_SEGMENT_CACHE[k]

    def get_subdir_rectangles(self, option, index, rectangles, metrics, padding=common.size(common.WidthIndicator)):
        """Returns the available mode rectangles for FileWidget index."""
        k = subdir_rects_key(index, option)
        if k in common.SUBDIR_RECTS:
            return common.SUBDIR_RECTS[k]

        common.SUBDIR_RECTS[k] = []

        subdirs = index.data(common.ParentPathRole)
        if not subdirs:
            return common.SUBDIR_RECTS[k]

        rect = QtCore.QRect(
            rectangles[ThumbnailRect].right() + (padding * 2.0),
            0,
            0,
            metrics.height() + (padding * 2),
        )

        for n, text in enumerate(subdirs[-1].upper().split('/')):
            if not text:
                continue
            if n >= self.MAX_SUBDIRS:
                break
            if len(text) > 24:
                _text = text[0:11] + '...' + text[-11:]
                width = metrics.horizontalAdvance(_text) + (padding * 4)
            else:
                width = metrics.horizontalAdvance(text) + (padding * 4)

            rect.setWidth(width)

            common.SUBDIR_RECTS[k].append((QtCore.QRect(rect), text))
            rect.moveLeft(rect.left() + rect.width() + padding)

        return common.SUBDIR_RECTS[k]

    def sizeHint(self, option, index):
        return self.parent().model().sourceModel().row_size()


class FavouritesWidgetDelegate(FilesWidgetDelegate):
    @paintmethod
    def paint_name(self, *args):
        self.paint_simple_name(*args)

    @paintmethod
    def paint_background(self, *args):
        self.paint_simple_background(*args)

    @paintmethod
    def paint_inline_background(self, *args):
        return

    @paintmethod
    def _paint_inline_archived(self, *args):
        return

    @paintmethod
    def _paint_inline_favourite(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[FavouriteRect]
        if not rect or archived:
            return

        painter.setOpacity(0.5)
        color = common.color(common.GreenColor)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'favourite', color, common.size(common.WidthMargin))
        painter.drawPixmap(rect, pixmap)
