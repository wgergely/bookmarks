# -*- coding: utf-8 -*-
"""Item delegate used to draw bookmark, asset and file items.

Defines :class:`ItemDelegate`, the base delegate class, subclasses and helper functions.

The list views have a number of custom features, such as clickable in-line icons,
folder names, custom thumbnails that the delegate implements. Since we're using list
views with a single column, the item layout is defined by a series of custom rectangles
(see :func:`get_rectangles`.). These are used by the paint methods use to drawn
elements and the views to define interactive regions.

The downside of painting manually a complex layout is performance and no doubt the
module could be more optimised. Still, most of the expensive functions are backed by
caches.

"""
import functools
import re

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common
from .. import images

#: Regex used to sanitize version numbers
regex_remove_version = re.compile(
    rf'(.*)(v)([{common.SEQSTART}0-9\-{common.SEQEND}]+.*)',
    flags=re.IGNORECASE
)

#: Regex used to sanitize collapsed sequence items
regex_remove_seq_marker = re.compile(
    rf'[{common.SEQSTART}{common.SEQEND}]*',
    flags=re.IGNORECASE
)

HOVER_COLOR = QtGui.QColor(255, 255, 255, 10)

null_rect = QtCore.QRect()

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

#: Used to paint a DCC icon if the asset name contains any of these names
DCC_ICONS = {
    'hou': 'hip',
    'maya': 'ma',
    'afx': 'aep',
    'aftereffects': 'aep',
    'photoshop': 'psd',
    'cinema4d': 'c4d',
    'c4d': 'c4d',
    'blender': 'blend',
    'nuke': 'nk'
}


def paintmethod(func):
    """Decorator used to manage painter states."""

    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        """Function wrapper.
        
        """
        args[1].save()
        res = func(self, *args, **kwargs)
        args[1].restore()
        return res

    return func_wrapper


__elided_text = {}


def elided_text(metrics, text, elide_mode, width):
    """Utility function used to elide the given text to fit to the given width.
    
    Args:
        metrics (QFontMetrics): A font metrics instance.
        text (str): The text to elide.
        elide_mode (int): A text elide mode flag.
        width (float): The width to text must fit.
        
    Returns:
        str: The elided text.
        
    """
    k = f'{text}{elide_mode}{width}'
    if k in __elided_text:
        return __elided_text[k]
    v = metrics.elidedText(
        text,
        elide_mode,
        width
    )
    __elided_text[k] = v
    return v


def _subdir_rects_key(index, option):
    return index.data(common.PathRole) + str(option.rect.height())


def _subdir_bg_rect_key(index, option):
    return index.data(common.PathRole) + str(option.rect.size())


def get_painter_path(x, y, font, text):
    """Creates, populates and caches QPainterPath instances.

    """
    k = f'{x}{y}{font}{text}'
    if k in common.delegate_paths:
        return common.delegate_paths[k]
    path = QtGui.QPainterPath()
    path.addText(x, y, font, text)
    common.delegate_paths[k] = path
    return common.delegate_paths[k]


def get_rectangles(rectangle, count):
    """Return all rectangles needed to paint an item.

    Args:
        rectangle (QtCore.QRect): An list item's visual rectangle.
        count (int): The number of inline icons.

    Returns:
        dict: Dictionary containing `count` number of rectangles.

    """
    k = f'{rectangle}{count}'
    if k in common.delegate_rectangles:
        return common.delegate_rectangles[k]

    def _adjusted():
        return rectangle.adjusted(0, 0, 0, -common.size(common.size_separator))

    background_rect = _adjusted()
    background_rect.setLeft(common.size(common.size_indicator))

    indicator_rect = QtCore.QRect(rectangle)
    indicator_rect.setWidth(common.size(common.size_indicator))

    thumbnail_rect = QtCore.QRect(rectangle)
    thumbnail_rect.setWidth(thumbnail_rect.height())
    thumbnail_rect.moveLeft(common.size(common.size_indicator))

    # Inline icons rect
    inline_icon_rects = []
    inline_icon_rect = _adjusted()
    spacing = common.size(common.size_indicator) * 2.5
    center = inline_icon_rect.center()
    size = QtCore.QSize(
        common.size(common.size_margin),
        common.size(common.size_margin)
    )
    inline_icon_rect.setSize(size)
    inline_icon_rect.moveCenter(center)
    inline_icon_rect.moveRight(rectangle.right() - spacing)

    offset = 0
    for _ in range(count):
        r = inline_icon_rect.translated(offset, 0)
        inline_icon_rects.append(r)
        offset -= inline_icon_rect.width() + spacing

    if count:
        offset -= spacing

    data_rect = _adjusted()
    data_rect.setLeft(thumbnail_rect.right())
    data_rect.setRight(rectangle.right() + offset)

    inline_background_rect = QtCore.QRect(background_rect)
    inline_background_rect.setLeft(data_rect.right())

    common.delegate_rectangles[k] = {
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
    return common.delegate_rectangles[k]


@functools.lru_cache(maxsize=4194304)
def _get_pixmap_rect(rect_height, pixmap_width, pixmap_height):
    s = float(rect_height)
    longest_edge = float(max((pixmap_width, pixmap_height)))
    ratio = s / longest_edge
    w = pixmap_width * ratio
    h = pixmap_height * ratio
    return QtCore.QRect(0, 0, int(w), int(h))


@functools.lru_cache(maxsize=4194304)
def get_file_text_segments(s, k, f):
    """Caches and returns the text segments used to paint file items.

    Used to mimic rich-text like coloring of individual text elements.

    Args:
        s (str): Item's display name.
        k (str): Item's file path.
        f (str): Item's frame role data.

    Returns:
        dict: A dict of (str, QColor) pairs.

    """
    if not s:
        return {}

    if k in common.delegate_text_segments:
        return common.delegate_text_segments[k]

    s = regex_remove_version.sub(r'\1\3', s)
    d = {}
    # Item is a collapsed sequence
    match = common.is_collapsed(s)
    if match:
        # Suffix + extension
        s = match.group(3).split('.')
        s = '.'.join(s[:-1]).upper() + '.' + s[-1].lower()
        d[len(d)] = (s, common.color(common.color_text))

        # Frame-range without the "[]" characters
        s = match.group(2)
        s = regex_remove_seq_marker.sub('', s)
        if len(s) > 17:
            s = s[0:8] + '...' + s[-8:]
        if len(f) > 1:
            d[len(d)] = (s, common.color(common.color_red))
        else:
            d[len(d)] = (s, common.color(common.color_text))

        # Filename
        d[len(d)] = (
            match.group(1).upper(), common.color(common.color_selected_text))
        common.delegate_text_segments[k] = d
        return d

    # Item is a non-collapsed sequence
    match = common.get_sequence(s)
    if match:
        # The extension and the suffix
        if match.group(4):
            s = match.group(3).upper() + '.' + match.group(4).lower()
        else:
            s = match.group(3).upper()
        d[len(d)] = (s, common.color(common.color_selected_text))

        # Sequence
        d[len(d)] = (match.group(
            2
        ).upper(), common.color(common.color_secondary_text))

        # Prefix
        d[len(d)] = (
            match.group(1).upper(), common.color(common.color_selected_text))
        common.delegate_text_segments[k] = d
        return d

    # Item is not collapsed, and isn't a sequence either
    s = s.split('.')
    if len(s) > 1:
        s = '.'.join(s[:-1]).upper() + '.' + s[-1].lower()
    else:
        s = s[0].upper()
    d[len(d)] = (s, common.color(common.color_selected_text))
    common.delegate_text_segments[k] = d
    return d


def get_file_detail_text_segments(index):
    """Returns the `FileItemView` item `common.FileDetailsRole` segments
    associated with custom colors.

    Args:
        index (QModelIndex): The index currently being painted.

    Returns:
        dict: A dictionary of tuples "{0: (str, QtGui.QColor)}".

    """
    k = index.data(common.FileDetailsRole)
    if k in common.delegate_text_segments:
        return common.delegate_text_segments[k]

    d = {}

    if not index.data(common.FileInfoLoaded):
        d[len(d)] = ('...', common.color(common.color_secondary_text))
        return d

    text = index.data(common.FileDetailsRole)
    texts = text.split(';')
    for n, text in enumerate(reversed(texts)):
        d[len(d)] = (text, common.color(common.color_secondary_text))
        if n == (len(texts) - 1) and not index.data(common.DescriptionRole):
            break
        d[len(d)] = ('  |  ', common.color(common.color_dark_background))

    common.delegate_text_segments[k] = d
    return common.delegate_text_segments[k]


def _get_asset_subdir_bg(rectangles, metrics, text):
    rect = QtCore.QRect(rectangles[DataRect])
    rect.setLeft(rect.left() + common.size(common.size_margin))

    # First let's paint the background rectangle
    o = common.size(common.size_indicator)

    text_width = metrics.width(text)
    r = QtCore.QRect(rect)
    r.setWidth(text_width)
    center = r.center()
    r.setHeight(metrics.height())
    r.moveCenter(center)
    r = r.adjusted(-(o * 3), -o, o * 3, o)
    if (r.right() + o) > rect.right():
        r.setRight(rect.right() - o)

    return rect, r


@functools.lru_cache(maxsize=4194304)
def get_asset_text_segments(text, label):
    """Caches and returns the text segments used to paint asset items.

    Used to mimic rich-text like coloring of individual text elements.

    Args:
        text (str): The source text.
        label (str): Item's label string.

    Returns:
        dict: A dict of (str, QColor) pairs.

    """
    if not text:
        return {}

    label = label if label else ''
    k = f'{text}{label}'

    # Return cached item
    if k in common.delegate_text_segments:
        return common.delegate_text_segments[k]

    # Segments dictionary
    d = {}

    s_color = common.color(common.color_blue).darker(300)

    # Process each sub-folder as a separate text segment
    v = text.split('/')

    for i, s in enumerate(v):
        if i == 0:
            c = common.color(common.color_blue).darker(300)
        else:
            c = common.color(common.color_text)

        # Check if subdir contains sequence and shot markers
        sequence, shot = common.get_sequence_and_shot(s)
        for ss in [f for f in common.get_sequence_and_shot(s) if f]:
            d[len(d)] = (ss, common.color(common.color_text))

            s = s.replace(ss, '').strip('_').strip('-').strip()
            if s:
                d[len(d)] = ('  |  ', s_color)

        # For ecosystems where folder names are prefixed with numbers
        s = re.sub(r'^[0-9]+_', '', s)
        s = s.strip().strip('_').strip('.')

        d[len(d)] = (s, c)

        # Add separator
        if i < (len(v) - 1) or i < (len(v) - 1):
            d[len(d)] = ('  |  ', s_color)

    # Add
    if label:
        d[len(d)] = ('  |  ', s_color)
        if '#' in label:
            d[len(d)] = (label, common.color(common.color_text))
        else:
            d[len(d)] = (label, s_color)

    common.delegate_text_segments[k] = d
    return common.delegate_text_segments[k]


@functools.lru_cache(maxsize=4194304)
def get_bookmark_text_segments(text, label):
    """Caches and returns the text segments used to paint bookmark items.

    Used to mimic rich-text like coloring of individual text elements.

    Args:
        text (str): The source text.
        label (str): Item's label string.

    Returns:
        dict: A dict of (str, QColor) pairs.

    """
    if not text:
        return {}
    label = label if label else ''

    k = text + label
    if k in common.delegate_text_segments:
        return common.delegate_text_segments[k]

    text = text.strip().strip('/').strip('\\')
    if not text:
        return {}

    d = {}
    v = text.split('|')

    s_color = common.color(common.color_blue).darker(300)

    for i, s in enumerate(v):
        if i == 0:
            c = common.color(common.color_blue).darker(300)
        else:
            c = common.color(common.color_text)

        _v = s.split('/')
        for _i, _s in enumerate(_v):
            _s = _s.strip()
            # In the AKA ecosystem folder names are prefixed with numbers, but we
            # don't want to show these
            _s = re.sub(r'^[0-9]+_', '', _s)

            d[len(d)] = (_s, c)
            if _i < (len(_v) - 1):
                d[len(d)] = (' / ', s_color)
        if i < (len(v) - 1):
            d[len(d)] = ('   |    ', s_color)

    if label:
        d[len(d)] = ('   |   ', s_color)
        d[len(d)] = (label, s_color)

    common.delegate_text_segments[k] = d
    return common.delegate_text_segments[k]


def _draw_segments(it, font, metrics, offset, *args):
    rectangles, painter, _, _, selected, _, _, _, _, hover, _, _, _ = args
    x = 0

    rect = QtCore.QRect(rectangles[DataRect])
    rect.setRight(
        rectangles[DataRect].right() -
        common.size(common.size_indicator) * 3
    )

    o = 0.9 if selected else 0.8
    o = 1.0 if hover else o
    painter.setOpacity(o)
    painter.setPen(QtCore.Qt.NoPen)
    for v in it:
        text, color = v

        color = common.color(common.color_selected_text) if selected else color
        color = common.color(common.color_text) if hover else color

        width = metrics.horizontalAdvance(text)
        rect.setLeft(rect.right() - width)

        if (rectangles[DataRect].left()) >= rect.left():
            rect.setLeft(
                rectangles[DataRect].left()
            )
            text = elided_text(
                metrics,
                text,
                QtCore.Qt.ElideLeft,
                rect.width()
            )
            width = metrics.horizontalAdvance(text)
            rect.setLeft(rect.right() - width)

        x = rect.center().x() - (width / 2.0) + common.size(common.size_separator)
        y = rect.center().y() + offset

        painter.setBrush(color)
        path = get_painter_path(x, y, font, text)
        painter.drawPath(path)

        rect.translate(-width, 0)

    return x


def draw_subdirs(bg_rect, clickable_rectangles, filter_text, *args):
    """Helper method used to draw the subdirectories of file items.

    """
    rectangles, painter, option, index, selected, _, active, _, _, hover, font, \
    metrics, cursor_position = args

    if not bg_rect:
        return

    font, metrics = common.font_db.primary_font(
        common.size(common.size_font_small)
    )

    # Paint the background rectangle of the sub-folder
    modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
    alt_modifier = modifiers & QtCore.Qt.AltModifier
    shift_modifier = modifiers & QtCore.Qt.ShiftModifier
    control_modifier = modifiers & QtCore.Qt.ControlModifier

    k = _subdir_rects_key(index, option)
    if k not in common.delegate_subdir_rectangles:
        return

    n = -1
    for rect, text in common.delegate_subdir_rectangles[k]:
        n += 1
        # Move the rectangle in-place
        rect = QtCore.QRect(rect)
        rect.moveCenter(
            QtCore.QPoint(
                rect.center().x(),
                rectangles[DataRect].center().y()
            )
        )

        # add the rectangle as a clickable rectangle
        clickable_rectangles[index.row()].append((rect, text))

        # Skip rectangles that fall out of bounds
        if rect.left() > bg_rect.right():
            continue

        if rect.right() > bg_rect.right():
            rect.setRight(bg_rect.right() - common.size(common.size_indicator))

        # Set the hover color based on the keyboard modifier and the filter text
        o = 0.6 if hover else 0.5
        color = common.color(common.color_dark_background)

        # Green the sub-folder is set as a text filter
        ftext = f'"{text}"'
        if filter_text and ftext.lower() in filter_text.lower():
            color = common.color(common.color_green)

        if rect.contains(cursor_position):
            o = 1.0
            if alt_modifier or control_modifier:
                color = common.color(common.color_red)
            elif shift_modifier or control_modifier:
                color = common.color(common.color_green)

        painter.setOpacity(o)
        painter.setBrush(color)
        o = common.size(common.size_indicator)
        if n == 0:
            pen = QtGui.QPen(common.color(common.color_separator))
        else:
            pen = QtGui.QPen(common.color(common.color_opaque))

        pen.setWidth(common.size(common.size_separator) * 2.0)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, o, o)

        if metrics.horizontalAdvance(text) > rect.width():
            text = elided_text(
                metrics,
                text,
                QtCore.Qt.ElideRight,
                rect.width() - (common.size(common.size_indicator) * 2)
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
    rectangles, painter, option, index, selected, _, active, _, _, hover, font, \
    metrics, cursor_position = args

    k = _subdir_rects_key(index, option)
    if k not in common.delegate_subdir_rectangles:
        return QtCore.QRect()

    _k = _subdir_bg_rect_key(index, option)

    # Calculate and cache the subdir rectangles background rectangle
    if common.delegate_subdir_rectangles[
        k] and _k in common.delegate_bg_subdir_rectangles:
        bg_rect = common.delegate_bg_subdir_rectangles[_k]
    elif common.delegate_subdir_rectangles[
        k] and _k not in common.delegate_bg_subdir_rectangles:
        left = min([f[0].left() for f in common.delegate_subdir_rectangles[k]])
        right = max([f[0].right() for f in common.delegate_subdir_rectangles[k]])
        height = max([f[0].height() for f in common.delegate_subdir_rectangles[k]])
        bg_rect = QtCore.QRect(left, 0, right - left, height)

        # Add margin
        o = common.size(common.size_indicator)
        bg_rect = bg_rect.adjusted(-o, -o, o * 1.5, o)

        common.delegate_bg_subdir_rectangles[_k] = bg_rect
    else:
        return QtCore.QRect()

    if common.delegate_subdir_rectangles[k]:
        # We have to move the rectangle in-place before painting it
        rect = QtCore.QRect(bg_rect)
        rect.moveCenter(
            QtCore.QPoint(
                rect.center().x(),
                rectangles[BackgroundRect].center().y()
            )
        )
        # Make sure we don't draw over the fle name
        o = common.size(common.size_indicator) * 2
        if rect.right() > (text_edge + o):
            rect.setRight(text_edge)
        # Make sure we don't shrink the rectangle too small
        if rect.left() + common.size(common.size_margin) < text_edge + o:
            if rect.contains(cursor_position):
                painter.setBrush(QtGui.QColor(0, 0, 0, 80))
            else:
                painter.setBrush(QtGui.QColor(0, 0, 0, 40))
            pen = QtGui.QPen(common.color(common.color_opaque))
            pen.setWidthF(common.size(common.size_separator))
            painter.setPen(pen)
            painter.drawRoundedRect(rect, o * 0.66, o * 0.66)
            return rect

    return QtCore.QRect()


def draw_gradient_background(text_edge, *args):
    """Helper method used to draw file items' gradient background."""
    rectangles, painter, option, index, selected, _, active, _, _, hover, font, \
    metrics, cursor_position = args

    k = _subdir_bg_rect_key(index, option)

    if k in common.delegate_bg_brushes:
        rect, brush = common.delegate_bg_brushes[k]
    else:
        rect = QtCore.QRect(
            rectangles[ThumbnailRect].right(),
            0,
            text_edge - rectangles[ThumbnailRect].right(),
            option.rect.height(),
        )
        margin = rectangles[DataRect].width() * 0.1
        if rectangles[DataRect].center().x() + margin >= text_edge:
            start_x = text_edge - margin
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
        gradient.setColorAt(0, common.color(common.color_dark_background))
        gradient.setColorAt(1.0, common.color(common.Transparent))
        brush = QtGui.QBrush(gradient)

        common.delegate_bg_brushes[k] = (rect, brush)

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
    rectangles, painter, option, index, selected, _, active, _, _, hover, font, \
    metrics, cursor_position = args

    color = common.color(common.color_selected_text) if selected else common.color(
        common.color_green
    )

    large_mode = option.rect.height() >= (common.size(common.size_row_height) * 2)
    if large_mode:
        left_limit = rectangles[DataRect].left()
        right_limit = rectangles[DataRect].right(
        ) - common.size(common.size_margin)
        font, metrics = common.font_db.primary_font(
            common.size(common.size_font_medium)
        )
    else:
        font, metrics = common.font_db.primary_font(
            common.size(common.size_font_small)
        )

    text = index.data(common.DescriptionRole)
    text = elided_text(
        metrics,
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
        0, (rect, index.data(common.DescriptionRole))
    )

    if rectangles[DataRect].contains(cursor_position):
        rect = QtCore.QRect(rectangles[DataRect])
        rect.setHeight(common.size(common.size_separator))
        rect.moveTop(y)
        rect.setLeft(left_limit)
        rect.setRight(right_limit)

        painter.setOpacity(0.3)
        painter.setBrush(common.color(common.color_separator))
        painter.drawRect(rect)
        painter.setOpacity(1.0)
        color = common.color(common.color_selected_text)

    painter.setBrush(color)
    path = get_painter_path(x, y, font, text)
    painter.drawPath(path)


class ItemDelegate(QtWidgets.QAbstractItemDelegate):
    """The main delegate used to represent lists derived from `base.BaseItemView`.

    """
    fallback_thumb = 'placeholder'

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._clickable_rectangles = {}

    def paint(self, painter, option, index):
        """Paint function.
        
        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    def _get_file_description_rect(self, rectangles, index):
        k = '/'.join([repr(v) for v in rectangles.values()])

        if self.parent().buttons_hidden():
            rect = self._get_simple_description_rectangle(rectangles, index)
        else:
            clickable = self.get_clickable_rectangles(index)
            if not clickable:
                rect = QtCore.QRect()
            else:
                rect = clickable[0][0]

        return rect

    def _get_simple_description_rectangle(self, rectangles, index):
        if not index.isValid():
            return

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + (common.size(common.size_indicator) * 2))

        _, metrics = common.font_db.primary_font(
            common.size(common.size_font_medium)
        )

        # File-name
        name_rect = QtCore.QRect(rect)
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(rect.center())
        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(
                    name_rect.center().x(),
                    name_rect.center().y() - (metrics.lineSpacing() / 2.0)
                )
            )

        text_segments = self._get_text_segments(index)
        font, metrics = common.font_db.primary_font(
            common.size(common.size_font_small) * 1.1
        )

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
                r.setRight(rect.right() - (common.size(common.size_indicator)))

        font, metrics = common.font_db.secondary_font(
            common.size(common.size_font_small) * 1.2
        )

        description_rect = QtCore.QRect(rect)
        description_rect.setHeight(metrics.height())
        description_rect.moveCenter(rect.center())
        description_rect.moveCenter(
            QtCore.QPoint(
                description_rect.center().x(),
                name_rect.center().y() + metrics.lineSpacing()
            )
        )
        return description_rect

    def get_description_rect(self, rectangles, index):
        """Returns the rectangle used to draw the description of an item.

        """
        pp = index.data(common.ParentPathRole)
        if not pp:
            return QtCore.QRect()

        if len(pp) == 3:
            return QtCore.QRect()
        elif len(pp) == 4:
            return self._get_asset_description_rect(rectangles, index)
        elif len(pp) > 4:
            return self._get_file_description_rect(rectangles, index)

    def _get_text_segments(self, index):
        pp = index.data(common.ParentPathRole)
        if not pp:
            return {}

        if len(pp) == 3:
            return get_bookmark_text_segments(
                index.data(QtCore.Qt.DisplayRole),
                index.data(common.DescriptionRole)
            )
        elif len(pp) == 4:
            return get_asset_text_segments(
                index.data(QtCore.Qt.DisplayRole),
                index.data(common.DescriptionRole)
            )
        elif len(pp) > 4:
            return get_file_text_segments(
                index.data(QtCore.Qt.DisplayRole),
                index.data(common.PathRole),
                tuple(index.data(common.FramesRole))
            )

    def get_paint_arguments(self, painter, option, index, antialiasing=False):
        """A utility class for gathering all the arguments needed to paint
        the individual list elements.

        """
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=antialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, on=antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, on=antialiasing)

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
            option.rect, self.parent().inline_icons_count()
        )
        font, metrics = common.font_db.primary_font(
            common.size(common.size_font_medium)
        )
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
        """Clickable rectangles are used by the QListView to identify
        interactive/clickable regions.

        The delegate is responsible for painting any pseudo item buttons, such
        as item names or in-line buttons and hence, we rely on the delegate
        to calculate where these rectangles are.

        Because calculating these rectangles on each paint operation would come with
        a performance hit we back the operation with a cache and return
        only already cached result when a request is made.

        Args:
            index (QtCore.QModelIndex): The item's index.

        Returns:
            dict: The item's clickable areas as QRect objects.

        """
        if index.row() in self._clickable_rectangles:
            return self._clickable_rectangles[index.row()]
        return {}

    def get_subdir_rectangles(
            self, option, index, rectangles, metrics,
            padding=common.size(common.size_indicator)
    ):
        """Returns the available mode rectangles for FileWidget index."""
        k = _subdir_rects_key(index, option)
        if k in common.delegate_subdir_rectangles:
            return common.delegate_subdir_rectangles[k]

        common.delegate_subdir_rectangles[k] = []

        subdirs = index.data(common.ParentPathRole)
        if not subdirs:
            return common.delegate_subdir_rectangles[k]

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

            common.delegate_subdir_rectangles[k].append((QtCore.QRect(rect), text))
            rect.moveLeft(rect.left() + rect.width() + padding)

        return common.delegate_subdir_rectangles[k]

    def _get_asset_description_rect(self, rectangles, index):
        k = '/'.join([repr(v) for v in rectangles.values()])

        if not index.isValid():
            return

        text_segments = self._get_text_segments(index)
        text = ''.join([text_segments[f][0] for f in text_segments])

        font, metrics = common.font_db.primary_font(
            common.size(common.size_font_medium)
        )
        rect, r = _get_asset_subdir_bg(rectangles, metrics, text)

        _rect = QtCore.QRect()
        _rect.setLeft(r.right() + common.size(common.size_margin))
        _rect.setTop(r.top())
        _rect.setBottom(r.bottom())
        _rect.setRight(rect.right() - common.size(common.size_margin))

        return _rect

    @paintmethod
    def paint_name(self, *args):
        """Paints the name of the item.
        
        """
        _, painter, _, index, _, _, _, _, _, _, _, _, _ = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        pp = index.data(common.ParentPathRole)
        if len(pp) == 3:
            return self.paint_bookmark_name(*args)
        elif len(pp) == 4:
            return self.paint_asset_name(*args)
        elif len(pp) > 4:
            return self.paint_file_name(*args)

    @paintmethod
    def paint_description_editor_background(self, *args, **kwargs):
        """Paints the background of the item.
        
        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        if index != self.parent().selectionModel().currentIndex():
            return
        if not self.parent().description_editor_widget.isVisible():
            return

        painter.setBrush(common.color(common.color_dark_background))
        painter.setPen(QtCore.Qt.NoPen)
        rect = QtCore.QRect(rectangles[BackgroundRect])
        rect.setLeft(rectangles[ThumbnailRect].right())

        o = common.size(common.size_indicator) * 0.5
        painter.drawRoundedRect(rect, o, o)

    @paintmethod
    def paint_thumbnail(self, *args):
        """Paints an item's thumbnail.

        If a requested QPixmap has never been drawn before we will create and
        store it by calling :func:`bookmarks.images.get_thumbnail`. This method is
        backed
        by :class:`bookmarks.images.ImageCache` and stores the requested pixmap
        for future use.

        If no associated image data is available, we will use a generic
        thumbnail associated with the item's type, or a fallback thumbnail set
        by the delegate.

        See the :mod:`bookmarks.images` module for implementation details.

        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        painter.setBrush(common.color(common.color_separator))
        painter.drawRect(rectangles[ThumbnailRect])

        if self.parent().verticalScrollBar().isSliderDown():
            return

        if not index.data(common.ParentPathRole):
            return

        server, job, root = index.data(common.ParentPathRole)[0:3]
        source = index.data(common.PathRole)

        size_role = index.data(QtCore.Qt.SizeHintRole)
        if not source or not size_role:
            return

        pixmap, color = images.get_thumbnail(
            server,
            job,
            root,
            source,
            size_role.height(),
            fallback_thumb=self.fallback_thumb
        )

        o = 1.0 if selected or active or hover else 0.9

        # Background
        if common.settings.value('settings/paint_thumbnail_bg'):
            painter.setOpacity(o)
            color = color if color else common.color(common.color_separator)
            painter.setBrush(color)
            painter.drawRect(rectangles[ThumbnailRect])

        if not pixmap:
            return

        # Let's make sure the image is fully fitted, even if the image's size
        # doesn't match ThumbnailRect
        _rect = _get_pixmap_rect(
            rectangles[ThumbnailRect].height(), pixmap.width(), pixmap.height()
        )
        _rect.moveCenter(rectangles[ThumbnailRect].center())
        painter.drawPixmap(_rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_thumbnail_drop_indicator(self, *args):
        """Paints a drop indicator used when dropping thumbnail onto the item.
        
        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        drop = self.parent()._thumbnail_drop
        if drop[1] and drop[0] == index.row():
            painter.setOpacity(0.9)
            painter.setBrush(common.color(common.color_separator))
            painter.drawRect(option.rect)

            painter.setPen(common.color(common.color_green))
            font, metrics = common.font_db.secondary_font(
                common.size(common.size_font_small)
            )
            painter.setFont(font)

            text = 'Drop image to add as thumbnail'
            painter.drawText(
                option.rect.adjusted(
                    common.size(
                        common.size_margin
                    ), 0, -common.size(common.size_margin), 0
                ),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter |
                QtCore.Qt.TextWordWrap,
                text,
                boundingRect=option.rect,
            )

            o = common.size(common.size_separator) * 2.0
            rect = rectangles[ThumbnailRect].adjusted(o, o, -o, -o)
            painter.drawRect(rect)

            pen = QtGui.QPen(common.color(common.color_green))
            pen.setWidth(o)
            painter.setPen(pen)
            painter.setBrush(common.color(common.color_green))
            painter.setOpacity(0.5)
            pixmap = images.ImageCache.rsc_pixmap(
                'add', common.color(common.color_green), rect.height() * 0.5
            )
            painter.drawRect(rect)
            irect = pixmap.rect()
            irect.moveCenter(rect.center())
            painter.drawPixmap(irect, pixmap, pixmap.rect())

    @paintmethod
    def paint_background(self, *args):
        """Paints the background for all list items."""
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        if index.flags() == QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return

        rect = QtCore.QRect(rectangles[BackgroundRect])
        if index.row() == (self.parent().model().rowCount() - 1):
            rect.setHeight(rect.height() + common.size(common.size_separator))

        color = common.color(
            common.color_light_background
        ) if selected else common.color(
            common.color_background
        )
        painter.setBrush(color)

        painter.setOpacity(1.0)
        painter.drawRect(rect)

        # Setting the opacity of the separator
        if index.row() != (self.parent().model().rowCount() - 1):
            painter.setOpacity(0.5)
            painter.setBrush(color)
            _rect = QtCore.QRect(rect)
            _rect.setBottom(
                _rect.bottom() +
                common.size(common.size_indicator)
            )
            _rect.setTop(_rect.bottom() - common.size(common.size_indicator))
            _rect.setLeft(
                common.size(common.size_indicator) +
                option.rect.height() - common.size(common.size_separator)
            )
            painter.drawRect(_rect)

        # Active indicator
        if active:
            rect.setLeft(
                option.rect.left() +
                common.size(common.size_indicator) + option.rect.height()
            )
            painter.setOpacity(0.5)
            painter.setBrush(common.color(common.color_green))
            painter.drawRoundedRect(
                rect, common.size(common.size_indicator),
                common.size(common.size_indicator)
            )
            painter.setOpacity(0.8)
            pen = QtGui.QPen(common.color(common.color_green))
            pen.setWidth(common.size(common.size_separator) * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            o = common.size(common.size_separator)
            rect = rect.adjusted(o, o, -(o * 1.5), -(o * 1.5))
            painter.drawRoundedRect(
                rect, common.size(common.size_indicator),
                common.size(common.size_indicator)
            )

        # Hover indicator
        if hover:
            painter.setBrush(HOVER_COLOR)
            painter.drawRect(rect)

    @paintmethod
    def paint_inline_background(self, *args):
        """Paints the item's inline buttons background.
        
        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        if rectangles[InlineBackgroundRect].left() < rectangles[
            ThumbnailRect].right():
            return

        if index.row() == (self.parent().model().rowCount() - 1):
            rect = QtCore.QRect(rectangles[InlineBackgroundRect])
            rect.setHeight(rect.height() + common.size(common.size_separator))
        else:
            rect = rectangles[InlineBackgroundRect]

        painter.setBrush(common.color(common.color_separator))
        painter.setOpacity(0.6) if rect.contains(
            cursor_position
        ) else painter.setOpacity(0.4)
        painter.drawRect(rect)

    @paintmethod
    def paint_inline_icons(self, *args):
        """Paints the item's inline buttons background.

        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        if index.flags() == QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return
        if rectangles[InlineBackgroundRect].left() < rectangles[
            ThumbnailRect].right():
            return

        painter.setOpacity(1) if hover else painter.setOpacity(0.66)

        self._paint_inline_favourite(*args)
        self._paint_inline_archived(*args)
        self._paint_inline_reveal(*args)
        self._paint_inline_todo(*args)
        self._paint_inline_add(*args)
        self._paint_inline_properties(*args)

    @paintmethod
    def _paint_inline_favourite(self, *args, _color=common.color(common.color_separator)):
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[FavouriteRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position) or favourite:
            painter.setOpacity(1.0)

        color = QtGui.QColor(255, 255, 255, 150) if rect.contains(
            cursor_position
        ) else _color
        color = common.color(common.color_selected_text) if favourite else color
        pixmap = images.ImageCache.rsc_pixmap(
            'favourite', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

    @paintmethod
    def _paint_inline_archived(self, *args, _color=common.color(common.color_separator)):
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[ArchiveRect]
        if not rect:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(
            common.color_green
        ) if archived else common.color(common.color_red)
        color = color if rect.contains(
            cursor_position
        ) else _color
        if archived:
            pixmap = images.ImageCache.rsc_pixmap(
                'archivedVisible', common.color(common.color_green),
                common.size(common.size_margin)
            )
        else:
            pixmap = images.ImageCache.rsc_pixmap(
                'archivedHidden', color, common.size(common.size_margin)
            )
        painter.drawPixmap(rect, pixmap)

    @paintmethod
    def _paint_inline_reveal(self, *args, _color=common.color(common.color_separator)):
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[RevealRect]
        if not rect or archived:
            return
        if rect.contains(cursor_position):
            painter.setOpacity(1.0)
        color = common.color(common.color_selected_text) if rect.contains(
            cursor_position
        ) else _color
        pixmap = images.ImageCache.rsc_pixmap(
            'folder', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

    @paintmethod
    def _paint_inline_todo(self, *args, _color=common.color(common.color_separator)):
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        rect = rectangles[TodoRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(common.color_selected_text) if rect.contains(
            cursor_position
        ) else _color
        pixmap = images.ImageCache.rsc_pixmap(
            'todo', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

        count = index.data(common.TodoCountRole)
        self.paint_count(painter, rect, cursor_position, count, 'add')

    @paintmethod
    def _paint_inline_add(self, *args, _color=common.color(common.color_separator)):
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[AddAssetRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(common.color_green) if rect.contains(
            cursor_position
        ) else _color
        pixmap = images.ImageCache.rsc_pixmap(
            'add_circle', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

        if len(index.data(common.ParentPathRole)) == 3:
            count = index.data(common.AssetCountRole)
            self.paint_count(painter, rect, cursor_position, count, 'asset')

    @paintmethod
    def _paint_inline_properties(self, *args,
                                 _color=common.color(common.color_separator)):
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        rect = rectangles[PropertiesRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)
        color = common.color(common.color_selected_text) if rect.contains(
            cursor_position
        ) else _color
        pixmap = images.ImageCache.rsc_pixmap(
            'settings', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

    def paint_count(self, painter, rect, cursor_position, count, icon):
        """Paints an item count.
        
        """
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        if not isinstance(count, (float, int)):
            return

        size = common.size(common.size_font_large)
        count_rect = QtCore.QRect(0, 0, size, size)
        count_rect.moveCenter(rect.bottomRight())

        if rect.contains(cursor_position):
            pixmap = images.ImageCache.rsc_pixmap(
                icon, common.color(common.color_green), size
            )
            painter.drawPixmap(count_rect, pixmap)
            return

        if count < 1:
            return

        color = common.color(common.color_green)
        painter.setBrush(color)
        painter.drawRoundedRect(
            count_rect, count_rect.width() / 2.0, count_rect.height() / 2.0
        )

        text = str(count)
        _font, _metrics = common.font_db.primary_font(
            common.size(common.size_font_small)
        )
        x = count_rect.center().x() - (_metrics.horizontalAdvance(text) / 2.0) + \
            common.size(common.size_separator)
        y = count_rect.center().y() + (_metrics.ascent() / 2.0)

        painter.setBrush(common.color(common.color_text))
        path = get_painter_path(x, y, _font, text)
        painter.drawPath(path)

    @paintmethod
    def paint_selection_indicator(self, *args):
        """Paints the leading rectangle indicating the selection."""
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        rect = rectangles[IndicatorRect]
        color = common.color(common.Transparent)
        color = common.color(common.color_green) if active else color
        color = common.color(common.color_selected_text) if selected else color
        painter.setBrush(color)
        painter.drawRect(rect)

    @paintmethod
    def paint_thumbnail_shadow(self, *args):
        """Paints the item's thumbnail shadow.
        
        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        if active:
            return

        rect = QtCore.QRect(rectangles[ThumbnailRect])
        rect.moveLeft(rect.right() + 1)

        painter.setOpacity(0.5)

        pixmap = images.ImageCache.rsc_pixmap(
            'gradient', None, rect.height()
        )

        rect.setWidth(common.size(common.size_margin))
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.size(common.size_margin) * 0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.size(common.size_margin) * 1.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_inline_background_shadow(self, *args):
        """Paints a drop-shadow"""
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        if active:
            return

        if self.parent().buttons_hidden():
            return
        if rectangles[InlineBackgroundRect].left() < rectangles[
            ThumbnailRect].right():
            return

        rect = QtCore.QRect(rectangles[InlineBackgroundRect])
        rect.setHeight(rect.height() + common.size(common.size_separator))

        painter.setOpacity(0.5)
        pixmap = images.ImageCache.rsc_pixmap(
            'gradient', None, rect.height()
        )

        rect.setWidth(common.size(common.size_margin))
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.size(common.size_margin) * 0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_archived(self, *args):
        """Paints a gray overlay when an item is archived."""
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        if not archived:
            return
        painter.setBrush(common.color(common.color_separator))
        painter.setOpacity(0.8)
        painter.drawRect(option.rect)

    @paintmethod
    def paint_default(self, *args):
        """Paints a gray overlay when an item is archived."""
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        if not index.data(common.FlagsRole) & common.MarkedAsDefault:
            return
        painter.setBrush(common.color(common.color_blue))
        painter.setOpacity(0.5)
        painter.drawRect(option.rect)

    @paintmethod
    def paint_shotgun_status(self, *args):
        """Paints the item's ShotGrid configuration status.
        
        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return
        if not index.data(common.ShotgunLinkedRole):
            return

        rect = QtCore.QRect(
            0, 0, common.size(
                common.size_margin
            ), common.size(common.size_margin)
        )

        offset = QtCore.QPoint(
            common.size(common.size_indicator),
            common.size(common.size_indicator)
        )
        rect.moveBottomRight(
            rectangles[ThumbnailRect].bottomRight() - offset
        )

        painter.setOpacity(0.9) if hover else painter.setOpacity(0.8)

        pixmap = images.ImageCache.rsc_pixmap(
            'sg', common.color(common.color_text), common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_slack_status(self, *args):
        """Paints the item's Slack configuration status.
        
        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return
        if not index.data(common.SlackLinkedRole):
            return

        rect = QtCore.QRect(
            0, 0, common.size(
                common.size_margin
            ), common.size(common.size_margin)
        )

        offset = QtCore.QPoint(
            common.size(common.size_indicator),
            common.size(common.size_indicator)
        )
        rect.moveBottomRight(
            rectangles[ThumbnailRect].bottomRight() - offset
        )

        if index.data(common.ShotgunLinkedRole):
            rect.moveLeft(
                rect.left() - (common.size(common.size_margin) * 0.66)
            )

        painter.setOpacity(0.9) if hover else painter.setOpacity(0.8)

        pixmap = images.ImageCache.rsc_pixmap(
            'slack', common.color(common.color_text), common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_drag_source(self, *args, **kwargs):
        """Overlay do indicate the source of a drag operation."""
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        if not self.parent().drag_source_index.isValid():
            return
        if index == self.parent().drag_source_index:
            painter.setBrush(common.color(common.color_separator))
            painter.drawRect(option.rect)

            painter.setPen(common.color(common.color_background))
            font, metrics = common.font_db.secondary_font(
                common.size(common.size_font_small)
            )
            painter.setFont(font)

            text = '"Drag+Shift" grabs all files    |    "Drag+Alt" grabs the ' \
                   'first file    |    "Drag+Shift+Alt" grabs the parent folder'
            painter.drawText(
                option.rect.adjusted(
                    common.size(
                        common.size_margin
                    ), 0, -common.size(common.size_margin), 0
                ),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter |
                QtCore.Qt.TextWordWrap,
                text,
                boundingRect=option.rect,
            )
        else:
            painter.setOpacity(0.66)
            painter.setBrush(common.color(common.color_separator))
            painter.drawRect(option.rect)

    @paintmethod
    def paint_deleted(self, *args, **kwargs):
        """Paints a deleted item.
        
        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        if index.flags() != QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return

        rect = QtCore.QRect(option.rect)
        rect.setHeight(common.size(common.size_separator) * 2)
        rect.moveCenter(option.rect.center())
        painter.setBrush(common.color(common.color_separator))
        painter.drawRect(rect)

    @paintmethod
    def paint_bookmark_name(self, *args):
        """Paints name of the ``BookmarkWidget``'s items."""
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
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
                rectangles[DataRect].right() - common.size(common.size_margin)
            )

        if hover or selected or active:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.66)

        # If the text segments role has not yet been set, we'll set it here
        text_segments = self._get_text_segments(index)
        text = ''.join([text_segments[f][0] for f in text_segments])

        rect = rectangles[DataRect]
        rect.setLeft(rect.left() + common.size(common.size_margin))

        # First let's paint the background rectangle
        o = common.size(common.size_indicator)

        text_width = metrics.horizontalAdvance(text)
        r = QtCore.QRect(rect)
        r.setWidth(text_width)
        center = r.center()
        r.setHeight(metrics.height())
        r.moveCenter(center)
        r = r.adjusted(-(o * 3), -o, o * 3, o)
        if (r.right() + o) > rect.right():
            r.setRight(rect.right() - o)

        if r.left() + common.size(common.size_margin) > r.right():
            rectangles[DataRect] = _datarect
            return

        # Let's save the rectangle as a clickable rect
        self._clickable_rectangles[index.row()].append(
            (r, index.data(common.ParentPathRole)[1])
        )

        # Let's paint the background rectangle
        color = common.color(common.color_green).darker(
            120
        ) if active else common.color(common.color_blue).darker(120)
        color = common.color(common.color_green).darker(150) if r.contains(
            cursor_position
        ) else color
        f_subpath = '"/' + index.data(common.ParentPathRole)[1] + '/"'

        filter_text = self.parent().model().filter_text()
        if filter_text:
            if f_subpath.lower() in filter_text.lower():
                color = common.color(common.color_green).darker(120)

        painter.setBrush(color)
        pen = QtGui.QPen(color.darker(220))
        pen.setWidth(common.size(common.size_separator))
        painter.setPen(pen)

        painter.drawRoundedRect(
            r, common.size(common.size_indicator), common.size(common.size_indicator)
        )

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
                text = elided_text(
                    metrics,
                    text,
                    QtCore.Qt.ElideRight,
                    _r.width()
                )

            painter.setBrush(color)
            x = _r.x()
            y = _r.bottom()
            path = get_painter_path(x, y, font, text)
            painter.drawPath(path)

            offset += width

        rectangles[DataRect] = _datarect

    @paintmethod
    def paint_asset_name(self, *args):
        """Paints name of the ``AssetWidget``'s items."""
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        # The description rectangle for bookmark items is not clickable,
        # unlike on asset and files items
        description_rect = self.get_description_rect(rectangles, index)
        self._clickable_rectangles[index.row()] = [
            (description_rect, index.data(common.DescriptionRole))]

        if description_rect.contains(cursor_position):
            underline_rect = QtCore.QRect(description_rect)
            underline_rect.setTop(underline_rect.bottom())
            underline_rect.moveTop(
                underline_rect.top() + common.size(common.size_separator)
            )
            painter.setOpacity(0.5)
            painter.setBrush(common.color(common.color_separator))
            painter.drawRect(underline_rect)

            painter.setOpacity(1.0)
            painter.setBrush(common.color(common.color_secondary_text))
            text = elided_text(
                metrics,
                'Double-click to edit...',
                QtCore.Qt.ElideRight,
                description_rect.width(),
            )
            x = description_rect.left()
            y = description_rect.center().y() + (metrics.ascent() / 2.0)
            path = get_painter_path(x, y, font, text)
            painter.drawPath(path)

        _datarect = QtCore.QRect(rectangles[DataRect])
        if not self.parent().buttons_hidden():
            rectangles[DataRect].setRight(
                rectangles[DataRect].right() - common.size(common.size_margin)
            )

        if hover or selected or active:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.66)

        # If the text segments role has not yet been set, we'll set it here
        text_segments = self._get_text_segments(index)
        text = ''.join([text_segments[f][0] for f in text_segments])

        rect, r = _get_asset_subdir_bg(rectangles, metrics, text)

        color = common.color(common.color_green).darker(
            120
        ) if active else common.color(common.color_blue).darker(120)
        color = common.color(common.color_green).darker(150) if r.contains(
            cursor_position
        ) else color

        if r.contains(cursor_position):
            if alt_modifier or control_modifier:
                color = common.color(common.color_red)
            elif shift_modifier or control_modifier:
                color = common.color(common.color_green)

        painter.setBrush(color)
        pen = QtGui.QPen(color.darker(220))
        pen.setWidth(common.size(common.size_separator))
        painter.setPen(pen)

        painter.drawRoundedRect(
            r, common.size(common.size_indicator), common.size(common.size_indicator)
        )

        offset = 0
        o = common.size(common.size_indicator)
        painter.setPen(QtCore.Qt.NoPen)

        filter_text = self.parent().model().filter_text()

        for segment in text_segments.values():
            text, color = segment
            _text = text
            width = metrics.width(text)
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
                text = elided_text(
                    metrics,
                    text,
                    QtCore.Qt.ElideRight,
                    _r.width()
                )
            if _text.lower() in filter_text.lower():
                color = common.color(common.color_green)

            # Let's save the rectangle as a clickable rect
            self._clickable_rectangles[index.row()].append(
                (_r, _text)
            )

            painter.setBrush(color)
            x = _r.x()
            y = _r.bottom()
            path = get_painter_path(x, y, font, text)
            painter.drawPath(path)

            offset += width

        rectangles[DataRect] = _datarect

    @paintmethod
    def paint_file_name(self, *args):
        """Paints the folders and the filename of the current file inside the
        ``FileItemView``."""
        rectangles, painter, option, index, _, _, _, _, _, _, font, metrics, _ = args
        self._clickable_rectangles[index.row()] = []

        font, metrics = common.font_db.primary_font(
            common.size(common.size_font_small) + 1
        )
        offset = 0

        self.get_subdir_rectangles(option, index, rectangles, metrics)

        painter.save()
        it = self._get_text_segments(index).values()
        left = _draw_segments(it, font, metrics, offset, *args)
        painter.restore()

        painter.save()
        draw_gradient_background(left - common.size(common.size_margin), *args)
        painter.restore()

        painter.save()
        bg_rect = draw_subdir_background(
            left - common.size(common.size_margin), *args
        )
        painter.restore()

        painter.save()
        it = get_file_detail_text_segments(index).values()
        offset = metrics.ascent()
        font, metrics = common.font_db.primary_font(
            common.size(common.size_font_small) * 0.95
        )
        left = _draw_segments(it, font, metrics, offset, *args)
        painter.restore()

        painter.save()
        draw_description(
            self._clickable_rectangles, bg_rect.right(),
            left - common.size(common.size_indicator),
            offset,
            *args
        )
        painter.restore()

        painter.save()
        filter_text = self.parent().model().filter_text()
        draw_subdirs(
            bg_rect,
            self._clickable_rectangles,
            filter_text,
            *args
        )
        painter.restore()

    @paintmethod
    def paint_dcc_icon(self, *args):
        """Paints the item's DCC icon.

        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return

        d = index.data(QtCore.Qt.DisplayRole)
        icon = next((DCC_ICONS[f] for f in DCC_ICONS if f.lower() in d.lower()), None)
        if not icon:
            return

        rect = QtCore.QRect(
            0, 0, common.size(
                common.size_margin
            ), common.size(common.size_margin)
        )

        offset = QtCore.QPoint(
            common.size(common.size_indicator),
            common.size(common.size_indicator)
        )
        rect.moveTopLeft(
            rectangles[ThumbnailRect].topLeft() + offset
        )

        painter.setOpacity(0.9) if hover else painter.setOpacity(0.8)

        pixmap = images.ImageCache.rsc_pixmap(
            icon,
            None,
            common.size(common.size_margin),
            resource=common.FormatResource
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())


class BookmarkItemViewDelegate(ItemDelegate):
    """The delegate used to paint the bookmark items."""
    fallback_thumb = 'bookmark_item'

    def paint(self, painter, option, index):
        """Defines how the ``BookmarkItemView`` should be painted."""
        args = self.get_paint_arguments(painter, option, index)

        self.paint_background(*args)
        self.paint_default(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_name(*args)
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        self.paint_inline_background(*args)
        self.paint_inline_background_shadow(*args)
        self.paint_inline_icons(*args)
        self.paint_description_editor_background(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)
        self.paint_slack_status(*args)
        self.paint_shotgun_status(*args)

    def sizeHint(self, option, index):
        """Returns the item's size hint.

        """
        return self.parent().model().sourceModel().row_size


class AssetItemViewDelegate(ItemDelegate):
    """Delegate used by the ``AssetItemView`` to display the collected assets."""
    fallback_thumb = 'asset_item'

    def paint(self, painter, option, index):
        """Defines how the ``AssetItemView``'s' items should be painted."""
        # The index might still be populated...
        if index.data(QtCore.Qt.DisplayRole) is None:
            return
        args = self.get_paint_arguments(painter, option, index)
        self.paint_background(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_name(*args)
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        self.paint_description_editor_background(*args)
        self.paint_inline_background(*args)
        self.paint_inline_background_shadow(*args)
        self.paint_inline_icons(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)
        self.paint_shotgun_status(*args)
        self.paint_dcc_icon(*args)

    def sizeHint(self, option, index):
        """Returns the item's size hint.

        """
        return self.parent().model().sourceModel().row_size


class FileItemViewDelegate(ItemDelegate):
    """QAbstractItemDelegate associated with ``FileItemView``."""
    MAX_SUBDIRS = 6
    fallback_thumb = 'file_item'

    def __init__(self, parent=None):
        super(FileItemViewDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """Defines how the ``FileItemView``'s' items should be painted."""

        args = self.get_paint_arguments(painter, option, index)

        if not index.data(QtCore.Qt.DisplayRole):
            return
        p_role = index.data(common.ParentPathRole)
        if p_role:
            self.paint_background(*args)
            self.paint_name(*args)

        # self.paint_inline_background_shadow(*args)
        # self.paint_thumbnail_shadow(*args)

        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        self.paint_inline_background(*args)
        self.paint_inline_icons(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)
        self.paint_description_editor_background(*args)
        self.paint_drag_source(*args)
        self.paint_deleted(*args)

    def sizeHint(self, option, index):
        """Returns the item's size hint.

        """
        return self.parent().model().sourceModel().row_size


class FavouriteItemViewDelegate(FileItemViewDelegate):
    """Delegate used to paint favourite items.

    """
    fallback_thumb = 'favourite_item'

    def paint_background(self, *args):
        """Paints the favourite item's background.

        """
        return

    @paintmethod
    def paint_inline_icons(self, *args):
        """Paints the favourite item's inline icons.

        """
        rectangles, painter, option, index, selected, focused, active, archived, \
        favourite, hover, font, metrics, cursor_position = args

        if index.flags() == QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return
        if rectangles[InlineBackgroundRect].left() < rectangles[
            ThumbnailRect].right():
            return

        painter.setOpacity(1) if hover else painter.setOpacity(0.66)
        color = common.color(common.color_dark_background)
        self._paint_inline_favourite(*args, _color=color)
        self._paint_inline_archived(*args, _color=color)
        self._paint_inline_reveal(*args, _color=color)
        self._paint_inline_todo(*args, _color=color)
        self._paint_inline_add(*args, _color=color)
        self._paint_inline_properties(*args, _color=color)
