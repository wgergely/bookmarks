# -*- coding: utf-8 -*-
"""Item delegate used to draw bookmark, asset and file items.

Defines :class:`ItemDelegate`, the base delegate class, subclasses and helper functions.

The list views have a number of custom features, such as clickable in-line icons,
folder names, custom thumbnails that the delegate implements. Since we're using list
views with a single column, the item layout is defined by a series of custom rectangles
(see :meth:`ItemDelegate.get_rectangles`.). These are used by the paint methods use to
drawn elements and the views to define interactive regions.

The downside of painting manually a complex layout is performance and no doubt the
module could be more optimised. Still, most of the expensive functions are backed by
caches.

"""
import functools
import re

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common
from .. import database
from .. import images
from .. import ui

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
AddItemRect = 5
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


def save_painter(func):
    """Decorator used to save and restore the painter state.

    """

    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        """Function wrapper.
        
        """
        painter = None
        for arg in args:
            if isinstance(arg, QtGui.QPainter):
                painter = arg
                break

        if painter:
            painter.save()

        res = func(self, *args, **kwargs)

        if painter:
            painter.restore()

        return res

    return func_wrapper


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
    if k in common.elided_text:
        return common.elided_text[k]
    v = metrics.elidedText(
        text,
        elide_mode,
        width
    )
    common.elided_text[k] = v
    return v


def draw_painter_path(painter, x, y, font, text):
    """Paints the given text using QPainterPath.

    This exists to ensure consistent aliased text rendering across all platforms.
    The path rendering comes with a performance trade-off so the QPainterPaths
    are cached and stored for later use.

    Args:
        painter (QPainter): The painter used to draw the text.
        x (float): Horizontal position.
        y (float): Vertical position.
        font (QFont): The font used to render the path.
        text (str): The text to render.

    """
    k = f'[{font.family(), font.pixelSize()}]{text}'

    if k not in common.delegate_paths:
        path = QtGui.QPainterPath()
        path.addText(0, 0, font, text)
        common.delegate_paths[k] = path

    # Let's move the cached path to position
    path = common.delegate_paths[k].translated(x, y)
    painter.drawPath(path)


def get_description_rectangle(index, rect, button):
    """Returns a cached interactive rectangle region.

    Args:
        index (QtCore.QModelIndex): The item's index.
        rect (QRect): The item's visual rectangle.
        button (bool): Button visibility state.

    Returns:
        tuple: A tuple of (QRect, str) pairs.

    """
    k = get_description_cache_key(index, rect, button)
    if k in common.delegate_description_rectangles:
        return common.delegate_description_rectangles[k]
    return None


def get_clickable_rectangles(index, rect):
    """Returns a cached interactive rectangle region.

    Args:
        index (QtCore.QModelIndex): The item's index.
        rect (QRect): The item's visual rectangle.

    Returns:
        tuple: A tuple of (QRect, str) pairs.

    """
    k = get_clickable_cache_key(index, rect)
    if k in common.delegate_clickable_rectangles:
        return common.delegate_clickable_rectangles[k]
    return None


def add_clickable_rectangle(index, option, rect, text):
    """Add a clickable rectangle and its contents.

    Args:
        index (QModelIndex): The item's index.
        option (QStyleOption): Style option instance.
        rect (QRect): The clickable area.
        text (str): The text of the rectangle.

    """
    if text and '|' in text:
        return
    if text and '•' in text:
        return
    if not rect:
        return
    if not text:
        return
    if not index.isValid():
        return
    k = get_clickable_cache_key(index, option.rect)
    v = (rect, text)
    if k not in common.delegate_clickable_rectangles:
        common.delegate_clickable_rectangles[k] = ()
    if v not in common.delegate_clickable_rectangles[k]:
        common.delegate_clickable_rectangles[k] += (v,)


@functools.lru_cache(maxsize=4194304)
def _get_pixmap_rect(rect_height, pixmap_width, pixmap_height):
    s = float(rect_height)
    longest_edge = float(max((pixmap_width, pixmap_height)))
    ratio = s / longest_edge
    w = pixmap_width * ratio
    h = pixmap_height * ratio
    return QtCore.QRect(0, 0, int(w), int(h))


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

    k = f'{text}{label}'
    if k in common.delegate_text_segments:
        return common.delegate_text_segments[k]

    text = text.upper().strip().strip('/').strip('\\')
    if not text:
        return {}

    d = {}
    v = text.split('|')

    s_color = common.color(common.color_dark_blue)

    for i, s in enumerate(v):
        if i == 0:
            c = common.color(common.color_text)
            if '/' in s:
                s = s.split('/')[-1]
        else:
            c = s_color

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
        d[len(d)] = ('    |    ', common.color(common.color_dark_background))
        v = label.split('•')
        for __i, s in enumerate(v):
            s = s.strip()

            d[len(d)] = (s, s_color)
            if __i != len(v) - 1:
                d[len(d)] = (', ', s_color)

    common.delegate_text_segments[k] = d
    return common.delegate_text_segments[k]


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

    s_color = common.color(common.color_dark_blue)

    # Process each sub-folder as a separate text segment
    v = text.split('/')

    for i, s in enumerate(v):
        c = common.color(common.color_text)

        # Check if subdir contains sequence and shot markers
        sequence, shot = common.get_sequence_and_shot(s)
        for ss in [f for f in common.get_sequence_and_shot(s) if f]:
            d[len(d)] = (ss, common.color(common.color_text))

            s = s.replace(ss, '').strip('_').strip('-').strip()
            if s:
                d[len(d)] = ('  •  ', common.color(common.color_dark_background))

        # For ecosystems where folder names are prefixed with numbers
        s = re.sub(r'^[0-9]+_', '', s)
        s = s.strip().strip('_').strip('.')

        d[len(d)] = (s, c)

        # Add separator
        if i < (len(v) - 1) or i < (len(v) - 1):
            if i == 0:
                d[len(d)] = ('  |  ', s_color)
            else:
                d[len(d)] = ('  /  ', s_color)

    # Add
    if label:
        if len(v) == 1:
            d[len(d)] = ('  |  ', s_color)
        else:
            d[len(d)] = ('  •  ', s_color)

        if '#' in label:
            d[len(d)] = (label, common.color(common.color_text))
        else:
            d[len(d)] = (label, s_color)

    common.delegate_text_segments[k] = d
    return common.delegate_text_segments[k]


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


@save_painter
def draw_file_text_segments(it, font, metrics, offset, *args):
    """Draws the given list of text segments.

    """
    (
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
        _,
        _,
        cursor_position
    ) = args

    x = 0

    rect = QtCore.QRect(rectangles[DataRect])
    rect.setRight(
        rectangles[DataRect].right() -
        common.size(common.size_indicator) * 3
    )

    o = 0.95 if selected else 0.9
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
        draw_painter_path(painter, x, y, font, text)

        rect.translate(-width, 0)

    return x


def get_subdir_cache_key(index, rect):
    """Returns the cache key used to store sub-folder rectangles.

    Returns:
        str: The cache key.

    """
    return f'{index.data(common.PathRole)}_subdir_{rect.size()}'


def get_subdir_bg_cache_key(index, rect):
    """Returns the cache key used to store sub-folder background rectangles.

    Returns:
        str: The cache key.

    """
    p = index.data(common.PathRole)
    d = index.data(common.DescriptionRole)
    return f'{p}:{d}:[{rect.x()},{rect.y()},{rect.width()},{rect.height()}]'


def get_clickable_cache_key(index, rect):
    """Returns the cache key used to store sub-folder background rectangles.

    Args:
        index (QModelIndex): Item index.
        rect (QRect): The item's rectangle.

    Returns:
        str: The cache key.

    """
    p = index.data(common.PathRole)
    f = index.data(common.FileDetailsRole)
    d = index.data(common.DescriptionRole)
    return f'{p}{f}{d}[{rect.x()},{rect.y()},{rect.width()},{rect.height()}]'


def get_description_cache_key(index, rect, button):
    """Returns the cache key used to store sub-folder background rectangles.

    Args:
        index (QModelIndex): Item index.
        rect (QRect): The item's rectangle.
        button (bool): Inline icon visibility state.

    Returns:
        str: The cache key.

    """
    p = index.data(common.PathRole)
    f = index.data(common.FileDetailsRole)
    d = index.data(common.DescriptionRole)
    return f'{p}{f}{d}{button}[{rect.x()},{rect.y()},{rect.width()},{rect.height()}]'


def get_subdir_rectangles(option, index, rectangles, metrics):
    """Returns the rectangles used to render sub-folder item labels.

    """
    k = get_subdir_cache_key(index, option.rect)
    if k in common.delegate_subdir_rectangles:
        return common.delegate_subdir_rectangles[k]

    common.delegate_subdir_rectangles[k] = []

    pp = index.data(common.ParentPathRole)
    if not pp:
        return common.delegate_subdir_rectangles[k]

    padding = common.size(common.size_indicator)
    rect = QtCore.QRect(
        rectangles[ThumbnailRect].right() + (padding * 2.0),
        0,
        0,
        metrics.height() + (padding * 2.0),
    )

    max_n = 6
    max_chars = 28
    min_chars = int((max_chars - len('...')) / 2.0)

    for n, text in enumerate(subdir_text_it(pp)):
        if not text:
            continue

        # Limit the number of rectangles to draw
        if n >= max_n:
            break

        # Trim text to a maximum number of characters
        if len(text) > max_chars:
            _text = text[0:min_chars] + '...' + text[-min_chars:]
            width = metrics.horizontalAdvance(_text) + (padding * 4.0)
        else:
            width = metrics.horizontalAdvance(text) + (padding * 4.0)

        rect.setWidth(width)

        common.delegate_subdir_rectangles[k].append(
            (QtCore.QRect(rect), text)
        )
        rect.moveLeft(rect.left() + rect.width() + padding)
    return common.delegate_subdir_rectangles[k]


def subdir_text_it(pp):
    """Yields text elements to be rendered as sub-folder item labels.

    """
    if len(pp) == 3:  # Bookmark items
        yield pp[1].upper()  # job name
        return
    elif len(pp) == 4:  # Asset items
        yield
        return
    elif len(pp) > 5:  # File items
        for s in pp[5].upper().split('/'):
            yield s


def get_text_segments(index):
    """Returns a list of text segments used to paint item names.

    Text segments mimic rich text like rendering where each
    segment can be coloured individually.

    Args:
        index (QModelIndex): A QModelIndex instance.

    Returns:
        dict: The text / colour pairs used to paint segments.

    """
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


def get_asset_subdir_bg(rectangles, metrics, text):
    rect = QtCore.QRect(rectangles[DataRect])
    rect.setLeft(rect.left() + common.size(common.size_margin))

    o = common.size(common.size_indicator)

    text_width = metrics.width(text)
    r = QtCore.QRect(rect)
    r.setWidth(text_width)
    center = r.center()
    r.setHeight(metrics.height() + (common.size(common.size_separator) * 4))
    r.moveCenter(center)
    r = r.adjusted(-(o * 3), -o, o * 3, o)
    if (r.right() + o) > rect.right():
        r.setRight(rect.right() - o)

    return rect, r


@save_painter
def draw_subdir_bg_rectangles(text_edge, *args):
    """Draws the rectangle behind the subdir item labels.

    Args:
        text_edge (float): The left edge of the text to avoid clipping.

    """
    (
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
    ) = args

    subdir_rects = get_subdir_rectangles(option, index, rectangles, metrics)
    if not subdir_rects:
        return QtCore.QRect()

    _k = get_subdir_bg_cache_key(index, option.rect)

    # Calculate and cache the subdir rectangles background rectangle
    if _k in common.delegate_bg_subdir_rectangles:
        bg_rect = common.delegate_bg_subdir_rectangles[_k]
    elif _k not in common.delegate_bg_subdir_rectangles:
        left = min([f[0].left() for f in subdir_rects])
        right = max([f[0].right() for f in subdir_rects])
        height = max([f[0].height() for f in subdir_rects])
        bg_rect = QtCore.QRect(left, 0, right - left, height)

        # Add margin
        o = common.size(common.size_indicator)
        bg_rect = bg_rect.adjusted(-o, -o, o * 1.5, o)

        common.delegate_bg_subdir_rectangles[_k] = bg_rect
    else:
        return QtCore.QRect()

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


@save_painter
def draw_gradient_background(*args):
    """Helper method used to draw file items' gradient background.

    Args:
        text_edge (float): The left edge of the text to avoid clipping.

    """
    (
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
    ) = args

    text_edge = rectangles[DataRect].right()

    k = get_subdir_bg_cache_key(index, option.rect)

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
        color = QtGui.QColor(common.color(common.color_dark_background))
        color.setAlpha(240)
        gradient.setSpread(QtGui.QGradient.PadSpread)
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(1.0, common.color(common.color_transparent))
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


class ItemDelegate(QtWidgets.QAbstractItemDelegate):
    """The main delegate used to represent lists derived from `base.BaseItemView`.

    """
    fallback_thumb = 'placeholder'

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._min = 0
        self._max = 0

    def createEditor(self, parent, option, index):
        if not index.data(common.FileInfoLoaded):
            return None

        description_rect = get_description_rectangle(
            index, option.rect, self.parent().buttons_hidden())
        if not description_rect:
            return None

        editor = ui.LineEdit(parent=parent)
        editor.setPlaceholderText('Enter an item description...')
        return editor

    def updateEditorGeometry(self, editor, option, index):
        rectangles = self.get_rectangles(index)
        editor.setStyleSheet(f'height: {rectangles[DataRect].height()}px;')
        editor.setGeometry(rectangles[DataRect])

    def setEditorData(self, editor, index):
        v = index.data(common.DescriptionRole)
        v = v if v else ''
        editor.setText(v)
        editor.selectAll()
        editor.setFocus()

    def setModelData(self, editor, model, index):
        text = f'{index.data(common.DescriptionRole)}'
        if text.lower() == editor.text().lower():
            return
        source_path = index.data(common.ParentPathRole)
        if not source_path:
            return

        p = index.data(common.PathRole)
        if common.is_collapsed(p):
            k = common.proxy_path(index)
        else:
            k = p

        # Set the database value
        # Note that we don't need to set the data directly as
        # the database will emit a value changed signal that will
        # automatically update the views and model data caches
        db = database.get_db(*source_path[0:3])
        db.set_value(k, 'description', editor.text())

    def paint(self, painter, option, index):
        """Paints an item.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    def get_rectangles(self, index):
        """Return all rectangles needed to paint an item.

        Args:
            index (QModelIndex): An item index.

        Returns:
            dict: Dictionary containing `count` number of rectangles.

        """
        r = self.parent().visualRect(index)
        count = self.parent().inline_icons_count()
        k = f'{r.x()},{r.y()},{r.width()},{r.height()},{count}'

        if k in common.delegate_rectangles:
            return common.delegate_rectangles[k]

        def _adjusted():
            return r.adjusted(0, 0, 0, -common.size(common.size_separator))

        background_rect = _adjusted()
        background_rect.setLeft(common.size(common.size_indicator))

        indicator_rect = QtCore.QRect(r)
        indicator_rect.setWidth(common.size(common.size_indicator))

        thumbnail_rect = QtCore.QRect(r)
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
        inline_icon_rect.moveRight(r.right() - spacing)

        offset = 0
        for _ in range(count):
            _r = inline_icon_rect.translated(offset, 0)
            inline_icon_rects.append(_r)
            offset -= inline_icon_rect.width() + spacing

        if count:
            offset -= spacing

        data_rect = _adjusted()
        data_rect.setLeft(thumbnail_rect.right())
        data_rect.setRight(r.right() + offset)

        inline_background_rect = QtCore.QRect(background_rect)
        inline_background_rect.setLeft(data_rect.right())

        tab_idx = index.data(common.ItemTabRole)
        n = (f for f in range(0, 10))
        _n = (f for f in range(0, 10))
        if tab_idx in {common.FavouriteTab, common.FileTab}:
            common.delegate_rectangles[k] = {
                BackgroundRect: background_rect,
                IndicatorRect: indicator_rect,
                ThumbnailRect: thumbnail_rect,
                ArchiveRect: inline_icon_rects[next(n)] if count > next(
                    _n) else null_rect,
                RevealRect: inline_icon_rects[next(n)] if count > next(_n) else null_rect,
                TodoRect: inline_icon_rects[next(n)] if count > next(_n) else null_rect,
                FavouriteRect: inline_icon_rects[next(n)] if count > next(
                    _n) else null_rect,
                AddItemRect: inline_icon_rects[next(n)] if count > next(
                    _n) else null_rect,
                PropertiesRect: inline_icon_rects[next(n)] if count > next(
                    _n) else null_rect,
                InlineBackgroundRect: inline_background_rect if count else null_rect,
                DataRect: data_rect
            }
        else:
            common.delegate_rectangles[k] = {
                BackgroundRect: background_rect,
                IndicatorRect: indicator_rect,
                ThumbnailRect: thumbnail_rect,
                ArchiveRect: inline_icon_rects[next(n)] if count > next(
                    _n) else null_rect,
                RevealRect: inline_icon_rects[next(n)] if count > next(_n) else null_rect,
                TodoRect: inline_icon_rects[next(n)] if count > next(_n) else null_rect,
                AddItemRect: inline_icon_rects[next(n)] if count > next(
                    _n) else null_rect,
                PropertiesRect: inline_icon_rects[next(n)] if count > next(
                    _n) else null_rect,
                FavouriteRect: inline_icon_rects[next(n)] if count > next(
                    _n) else null_rect,
                InlineBackgroundRect: inline_background_rect if count else null_rect,
                DataRect: data_rect
            }
        return common.delegate_rectangles[k]

    def _get_asset_description_rect(self, index, option, rectangles, metrics, offset):
        if not index.isValid():
            return None

        text_segments = get_text_segments(index)
        text = ''.join([text_segments[f][0] for f in text_segments])

        rect, r = get_asset_subdir_bg(rectangles, metrics, text)

        _rect = QtCore.QRect()
        _rect.setLeft(r.right() + common.size(common.size_margin) + offset)
        _rect.setTop(r.top())
        _rect.setBottom(r.bottom())
        _rect.setRight(rect.right() - common.size(common.size_margin))

        # Cache the calculated rectangle
        k = get_description_cache_key(index, option.rect, self.parent().buttons_hidden())
        common.delegate_description_rectangles[k] = _rect

        return common.delegate_description_rectangles[k]

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
        rectangles = self.get_rectangles(index)
        font, metrics = common.font_db.bold_font(common.size(common.size_font_medium))
        painter.setFont(font)

        cursor_position = self.parent().viewport().mapFromGlobal(common.cursor.pos())

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

    @save_painter
    def draw_subdir_rectangles(self, bg_rect, *args):
        """Helper method used to draw the subdirectories of file items.

        """
        (
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
        ) = args

        if not bg_rect:
            return

        font, metrics = common.font_db.bold_font(
            common.size(common.size_font_small)
        )

        filter_text = self.parent().model().filter_text()

        # Paint the background rectangle of the sub-folder
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        n = -1
        for rect, text in get_subdir_rectangles(option, index, rectangles, metrics):
            n += 1

            # Move the rectangle in-place
            rect = QtCore.QRect(rect)
            rect.moveCenter(
                QtCore.QPoint(
                    rect.center().x(),
                    rectangles[DataRect].center().y()
                )
            )

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

            # add the rectangle as a clickable rectangle
            add_clickable_rectangle(index, option, rect, text)

            if metrics.horizontalAdvance(text) > rect.width():
                text = elided_text(
                    metrics,
                    text,
                    QtCore.Qt.ElideRight,
                    rect.width() - (common.size(common.size_indicator) * 2)
                )

            x = rect.center().x() - (metrics.horizontalAdvance(text) / 2.0)
            y = (
                    rectangles[DataRect].center().y() +
                    (metrics.ascent() * 0.5) - common.size(common.size_separator)
            )

            color = color.lighter(250)
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            draw_painter_path(painter, x, y, font, text)

    @save_painter
    def paint_name(self, *args):
        """Paints the name of the item.

        """
        (
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
        ) = args

        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        pp = index.data(common.ParentPathRole)
        if len(pp) == 3:
            return self.paint_bookmark_name(*args)
        elif len(pp) == 4:
            return self.paint_asset_name(*args,
                                         offset=common.size(common.size_indicator) * 2)
        elif len(pp) > 4:
            return self.paint_file_name(*args)

    @save_painter
    def draw_file_description(self, font, metrics, left_limit, right_limit, offset,
                              large_mode, *args):
        """Draws file items' descriptions.

        """
        (
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
            _,
            _,
            cursor_position
        ) = args

        if large_mode:
            _o = (common.size(common.size_indicator) * 2)
            right_limit = rectangles[DataRect].right() - _o
            left_limit = rectangles[DataRect].left() + _o
        else:
            right_limit -= common.size(common.size_indicator)
            left_limit += common.size(common.size_margin)
        if left_limit < rectangles[DataRect].left():
            left_limit = rectangles[DataRect].left()

        rect = get_description_rectangle(
            index, option.rect, self.parent().buttons_hidden())

        if not rect:
            rect = self._get_file_description_rect(
                left_limit, right_limit, offset, large_mode,
                rectangles, metrics, index, option
            )

        color = common.color(common.color_green)
        color = common.color(common.color_selected_text) if selected else color

        if hover:
            painter.setOpacity(0.3)
            painter.setBrush(common.color(common.color_separator))
            _rect = QtCore.QRect(rect)
            _rect.setHeight(common.size(common.size_separator))
            _rect.moveTop(rect.center().y())
            painter.drawRect(_rect)

            painter.setOpacity(1.0)
            color = common.color(common.color_selected_text)

        text = index.data(common.DescriptionRole)
        text = elided_text(
            metrics,
            text,
            QtCore.Qt.ElideLeft,
            rect.width()
        )

        # Let's paint the descriptions, and tags as labels
        it = re.split(f'\s', text, flags=re.IGNORECASE)
        x = right_limit
        o = metrics.horizontalAdvance('  ')
        y = rect.center().y()

        label_bg_color = common.color(common.color_blue)
        label_text_color = common.color(common.color_text)

        filter_text = self.parent().model().filter_text()
        filter_text = filter_text.lower() if filter_text else ''
        filter_texts = re.split(f'\s', filter_text, flags=re.IGNORECASE)
        filter_texts = {f.lower().strip('"').strip('-').strip() for f in filter_texts}

        for s in reversed(it):
            width = metrics.horizontalAdvance(s)

            if '#' in s:
                width += o * 2

            x -= width

            if '#' in s:
                _o = common.size(common.size_separator) * 2
                rect = QtCore.QRect(
                    x,
                    y - metrics.ascent() - (_o / 2.0),
                    width,
                    metrics.lineSpacing() + _o
                )
                painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

                painter.setBrush(label_bg_color)

                if s.lower() in filter_texts:
                    painter.setBrush(common.color(common.color_green))
                if rect.contains(cursor_position):
                    painter.setBrush(common.color(common.color_light_background))

                add_clickable_rectangle(index, option, rect, s)

                painter.drawRoundedRect(rect, o * 0.5, o * 0.5)

                painter.setBrush(label_text_color)
                draw_painter_path(
                    painter,
                    x + o + (metrics.horizontalAdvance('#') * 0.5),
                    y,
                    font,
                    s.replace('#', '')
                )
            else:
                painter.setBrush(color)
                draw_painter_path(painter, x, y, font, s)

            # Space
            x -= metrics.horizontalAdvance(' ')

    def _get_file_description_rect(
            self, left_limit, right_limit, offset, large_mode,
            rectangles, metrics, index, option,
    ):
        y = rectangles[DataRect].center().y() + offset

        if large_mode:
            left_limit = rectangles[DataRect].left() + common.size(common.size_margin)
            right_limit = rectangles[DataRect].right() - common.size(common.size_margin)
            y += metrics.lineSpacing()

        rect = QtCore.QRect()
        rect.setHeight(metrics.lineSpacing())
        center = QtCore.QPoint(rectangles[DataRect].center().x(), y)
        rect.moveCenter(center)
        rect.setLeft(left_limit)
        rect.setRight(right_limit)

        # Cache the calculated rectangle
        k = get_description_cache_key(index, option.rect, self.parent().buttons_hidden())
        common.delegate_description_rectangles[k] = rect

        return common.delegate_description_rectangles[k]

    @save_painter
    def paint_description_editor_background(self, *args, **kwargs):
        """Paints the background of the item.

        """
        (
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
        ) = args

        if index != self.parent().selectionModel().currentIndex():
            return
        if not self.parent().state() == QtWidgets.QAbstractItemView.EditingState:
            return

        painter.setBrush(common.color(common.color_dark_background))
        painter.setPen(QtCore.Qt.NoPen)
        rect = QtCore.QRect(rectangles[DataRect])

        o = common.size(common.size_indicator) * 0.5
        painter.setOpacity(0.9)
        painter.drawRoundedRect(rect, o, o)

    @save_painter
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
        (
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
        ) = args

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
        painter.setOpacity(o)
        if not common.settings.value('settings/paint_thumbnail_bg'):
            if color:
                painter.setOpacity(1.0)
            color = color if color else QtGui.QColor(0, 0, 0, 50)
            painter.setBrush(color)
            if archived:
                painter.setOpacity(0.1)
            painter.drawRect(rectangles[ThumbnailRect])

        if not pixmap:
            return

        # Let's make sure the image is fully fitted, even if the image's size
        # doesn't match ThumbnailRect
        _rect = _get_pixmap_rect(
            rectangles[ThumbnailRect].height(), pixmap.width(), pixmap.height()
        )
        _rect.moveCenter(rectangles[ThumbnailRect].center())
        if archived:
            painter.setOpacity(0.1)
        painter.drawPixmap(_rect, pixmap, pixmap.rect())

    @save_painter
    def paint_thumbnail_drop_indicator(self, *args):
        """Paints a drop indicator used when dropping thumbnail onto the item.

        """
        (
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
        ) = args

        drop = self.parent()._thumbnail_drop

        if drop[1] and drop[0] == index.row():
            painter.setOpacity(0.9)
            painter.setBrush(common.color(common.color_separator))
            painter.drawRect(option.rect)

            painter.setPen(common.color(common.color_green))
            font, metrics = common.font_db.medium_font(
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
            pixmap = images.rsc_pixmap(
                'add', common.color(common.color_green), rect.height() * 0.5
            )
            painter.drawRect(rect)
            irect = pixmap.rect()
            irect.moveCenter(rect.center())
            painter.drawPixmap(irect, pixmap, pixmap.rect())

    @save_painter
    def paint_active(self, *args):
        """Paints the background for all list items."""
        (
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
        ) = args

        if index.flags() == QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return

        # Active indicator
        if not active:
            return

        rect = QtCore.QRect(rectangles[BackgroundRect])
        if index.row() == (self.parent().model().rowCount() - 1):
            rect.setHeight(rect.height() + common.size(common.size_separator))

        op = 0.5 if selected else 0.2

        rect.setLeft(
            option.rect.left() +
            common.size(common.size_indicator) + option.rect.height()
        )
        painter.setOpacity(op)
        painter.setBrush(common.color(common.color_green))
        painter.drawRoundedRect(
            rect, common.size(common.size_indicator),
            common.size(common.size_indicator)
        )
        painter.setOpacity(op)
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

    @save_painter
    def paint_background(self, *args):
        """Paints the background for all list items."""
        (
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
        ) = args

        if index.flags() == QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return

        rect = QtCore.QRect(rectangles[BackgroundRect])
        if index.row() == (self.parent().model().rowCount() - 1):
            rect.setHeight(rect.height() + common.size(common.size_separator))

        color = common.color(common.color_light_background)
        color = color if selected else common.color(common.color_background)
        painter.setBrush(color)

        painter.setOpacity(0.7)
        painter.drawRect(rect)

    @save_painter
    def paint_hover(self, *args):
        """Paints the background for all list items."""
        (
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
        ) = args

        if not hover:
            return
        if index.flags() == QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return

        rect = QtCore.QRect(rectangles[BackgroundRect])
        if index.row() == (self.parent().model().rowCount() - 1):
            rect.setHeight(rect.height() + common.size(common.size_separator))

        color = common.color(common.color_light_background)
        color = color if selected else common.color(common.color_background)
        painter.setBrush(color)

        painter.setOpacity(0.7)
        painter.setBrush(HOVER_COLOR)
        painter.drawRect(rect)

    @save_painter
    def paint_inline_background(self, *args):
        """Paints the item's inline buttons background.

        """
        (
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
        ) = args

        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        if rectangles[InlineBackgroundRect].left() < rectangles[ThumbnailRect].right():
            return

        if index.row() == (self.parent().model().rowCount() - 1):
            rect = QtCore.QRect(rectangles[InlineBackgroundRect])
            rect.setHeight(rect.height() + common.size(common.size_separator))
        else:
            rect = rectangles[InlineBackgroundRect]

        # Inline bg rect
        o = common.size(common.size_indicator)
        _o = common.size(common.size_separator) * 4

        r = QtCore.QRect(rect)
        r.setHeight(metrics.height() + _o)
        r.moveCenter(QtCore.QPoint(r.center().x(), rect.center().y()))
        r = r.adjusted(_o, -o, -_o, o)

        color = common.color(common.color_light_background)
        color = common.color(common.color_secondary_text) if hover else color
        color = common.color(common.color_text) if selected else color
        color = common.color(common.color_separator) if archived else color
        painter.setBrush(color)

        pen = QtGui.QPen(color.darker(200))
        if not archived:
            pen.setWidth(common.size(common.size_separator) * 2)
        painter.setPen(pen)

        if rect.contains(cursor_position):
            painter.setOpacity(0.8)
        else:
            painter.setOpacity(0.4)

        painter.drawRoundedRect(r, o, o)

    @save_painter
    def paint_inline_icons(self, *args):
        """Paints the item's inline buttons background.

        """
        (
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
        ) = args

        if index.flags() == QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return
        if rectangles[InlineBackgroundRect].left() < rectangles[ThumbnailRect].right():
            return

        painter.setOpacity(1) if hover else painter.setOpacity(0.66)

        self._paint_inline_favourite(*args)
        self._paint_inline_archived(*args)
        self._paint_inline_reveal(*args)
        self._paint_inline_todo(*args)
        self._paint_inline_add(*args)
        self._paint_inline_properties(*args)

    @save_painter
    def _paint_inline_favourite(self, *args, _color=common.color(common.color_separator)):
        (
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
        ) = args

        rect = rectangles[FavouriteRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position) or favourite:
            painter.setOpacity(1.0)

        color = QtGui.QColor(255, 255, 255, 150)
        color = color if rect.contains(cursor_position) else _color
        color = common.color(common.color_selected_text) if favourite else color

        pixmap = images.rsc_pixmap(
            'favourite', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

    @save_painter
    def _paint_inline_archived(self, *args, _color=common.color(common.color_separator)):
        (
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
        ) = args

        rect = rectangles[ArchiveRect]
        if not rect:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(common.color_green)
        color = color if archived else common.color(common.color_red)
        color = color if rect.contains(cursor_position) else _color
        if archived:
            pixmap = images.rsc_pixmap(
                'archivedVisible', common.color(common.color_green),
                common.size(common.size_margin)
            )
        else:
            pixmap = images.rsc_pixmap(
                'archivedHidden', color, common.size(common.size_margin)
            )
        painter.drawPixmap(rect, pixmap)

    @save_painter
    def _paint_inline_reveal(self, *args, _color=common.color(common.color_separator)):
        (
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
        ) = args

        rect = rectangles[RevealRect]

        if not rect or archived:
            return
        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(common.color_selected_text)
        color = color if rect.contains(cursor_position) else _color

        pixmap = images.rsc_pixmap(
            'folder', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

    @save_painter
    def _paint_inline_todo(self, *args, _color=common.color(common.color_separator)):
        (
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
        ) = args

        rect = rectangles[TodoRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(common.color_selected_text)
        color = color if rect.contains(cursor_position) else _color

        pixmap = images.rsc_pixmap(
            'todo', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

        count = index.data(common.TodoCountRole)
        self.paint_inline_count(painter, rect, cursor_position, count, 'add')

    @save_painter
    def _paint_inline_add(self, *args, _color=common.color(common.color_separator)):
        (
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
        ) = args

        rect = rectangles[AddItemRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(common.color_green)
        color = color if rect.contains(cursor_position) else _color

        pixmap = images.rsc_pixmap(
            'add_circle', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

        if len(index.data(common.ParentPathRole)) == 3:
            count = index.data(common.AssetCountRole)
            self.paint_inline_count(painter, rect, cursor_position, count, 'asset')

    @save_painter
    def _paint_inline_properties(self, *args,
                                 _color=common.color(common.color_separator)):
        (
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
        ) = args

        rect = rectangles[PropertiesRect]
        if not rect or archived:
            return

        if rect.contains(cursor_position):
            painter.setOpacity(1.0)

        color = common.color(common.color_selected_text)
        color = color if rect.contains(cursor_position) else _color

        pixmap = images.rsc_pixmap(
            'settings', color, common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap)

    def paint_inline_count(self, painter, rect, cursor_position, count, icon):
        """Paints an item count.

        """
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        if not isinstance(count, (float, int)):
            return

        size = common.size(common.size_font_large)
        count_rect = QtCore.QRect(0, 0, size, size)
        count_rect.moveCenter(rect.bottomRight())

        if rect.contains(cursor_position):
            pixmap = images.rsc_pixmap(
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
        _font, _metrics = common.font_db.bold_font(
            common.size(common.size_font_small)
        )
        x = count_rect.center().x() - (_metrics.horizontalAdvance(text) / 2.0) + \
            common.size(common.size_separator)
        y = count_rect.center().y() + (_metrics.ascent() / 2.0)

        painter.setBrush(common.color(common.color_text))
        draw_painter_path(painter, x, y, _font, text)

    @save_painter
    def paint_selection_indicator(self, *args):
        """Paints the leading rectangle indicating the selection."""
        (
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
        ) = args

        rect = rectangles[IndicatorRect]
        color = common.color(common.color_transparent)
        color = common.color(common.color_green) if active else color
        color = common.color(common.color_selected_text) if selected else color
        painter.setBrush(color)
        painter.drawRect(rect)

    @save_painter
    def paint_thumbnail_shadow(self, *args):
        """Paints the item's thumbnail shadow.

        """
        (
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
        ) = args

        if active:
            return

        rect = QtCore.QRect(rectangles[ThumbnailRect])
        rect.moveLeft(rect.right() + 1)

        painter.setOpacity(0.5)

        pixmap = images.rsc_pixmap(
            'gradient', None, rect.height()
        )

        rect.setWidth(common.size(common.size_margin))
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.size(common.size_margin) * 0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.size(common.size_margin) * 1.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @save_painter
    def paint_archived(self, *args):
        """Paints a gray overlay when an item is archived."""
        (
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
        ) = args
        if not archived:
            return
        painter.setBrush(common.color(common.color_separator))
        painter.setOpacity(0.8)
        painter.drawRect(option.rect)

    @save_painter
    def paint_default(self, *args):
        """Paints a gray overlay when an item is archived."""
        (
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
        ) = args

        if not index.data(common.FlagsRole) & common.MarkedAsDefault:
            return
        painter.setBrush(common.color(common.color_blue))
        painter.setOpacity(0.5)
        painter.drawRect(option.rect)

    @save_painter
    def paint_shotgun_status(self, *args):
        """Paints the item's ShotGrid configuration status.

        """
        (
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
        ) = args

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

        painter.setOpacity(1.0) if hover else painter.setOpacity(0.9)

        pixmap = images.rsc_pixmap(
            'sg', common.color(common.color_text), common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @save_painter
    def paint_slack_status(self, *args):
        """Paints the item's Slack configuration status.

        """
        (
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
        ) = args

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

        pixmap = images.rsc_pixmap(
            'slack', common.color(common.color_text), common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())


    @save_painter
    def paint_db_status(self, *args):
        """Paints the item's Slack configuration status.

        """
        (
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
        ) = args

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return

        db = database.get_db(*index.data(common.ParentPathRole)[0:3])
        if db.is_valid():
            return

        rect = QtCore.QRect(
            0, 0, common.size(
                common.size_margin
            ), common.size(common.size_margin)
        )
        rect.moveCenter(rectangles[BackgroundRect].center())

        painter.setOpacity(1.0) if hover else painter.setOpacity(0.9)

        pixmap = images.rsc_pixmap(
            'alert', common.color(common.color_red), common.size(common.size_margin)
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        painter.setBrush(common.color(common.color_red))
        painter.setPen(QtCore.Qt.NoPen)
        painter.setOpacity(0.1)
        painter.drawRect(rectangles[BackgroundRect])

    @save_painter
    def paint_drag_source(self, *args, **kwargs):
        """Overlay do indicate the source of a drag operation."""
        (
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
        ) = args

        if self.parent().drag_source_row == -1:
            return

        if (
                index.flags() & QtCore.Qt.ItemIsDropEnabled and
                option.rect.contains(cursor_position) and
                self.parent().drag_source_row != index.row()
        ):
            painter.setOpacity(0.5)
            painter.setBrush(common.color(common.color_separator))
            painter.drawRect(rectangles[DataRect])

            painter.setOpacity(1.0)
            painter.setBrush(QtCore.Qt.NoBrush)
            pen = QtGui.QPen(common.color(common.color_selected_text))
            pen.setWidthF(common.size(common.size_separator) * 2)
            painter.setPen(pen)
            painter.drawRect(rectangles[DataRect])

            font, metrics = common.font_db.medium_font(
                common.size(common.size_font_small)
            )
            painter.setFont(font)
            text = 'Paste item properties'
            painter.setPen(common.color(common.color_green))
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
            return

        if index.row() == self.parent().drag_source_row:
            painter.setBrush(common.color(common.color_separator))
            painter.drawRect(option.rect)

            painter.setPen(common.color(common.color_background))
            font, metrics = common.font_db.medium_font(
                common.size(common.size_font_small)
            )
            painter.setFont(font)

            text = ''
            if index.data(common.ItemTabRole) in (common.FileTab, common.FavouriteTab):
                text = '"Drag+Shift" grabs all files    |    "Drag+Alt" grabs the ' \
                       'first file    |    "Drag+Shift+Alt" grabs the parent folder'
            if index.data(common.ItemTabRole) in (common.BookmarkTab, common.AssetTab):
                text = 'Copied properties'

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
            painter.setOpacity(0.33)
            painter.setBrush(common.color(common.color_separator))
            painter.drawRect(option.rect)

    @save_painter
    def paint_deleted(self, *args, **kwargs):
        """Paints a deleted item.

        """
        (
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
        ) = args

        if index.flags() != QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return

        rect = QtCore.QRect(option.rect)
        rect.setHeight(common.size(common.size_separator) * 2)
        rect.moveCenter(option.rect.center())
        painter.setBrush(common.color(common.color_separator))
        painter.drawRect(rect)

    @save_painter
    def paint_bookmark_name(self, *args):
        """Paints name of the ``BookmarkWidget``'s items."""
        (
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
        ) = args

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return

        # Paint the job as a clickable floating rectangle
        bg_rect = draw_subdir_bg_rectangles(rectangles[DataRect].right(), *args)
        text = index.data(common.ParentPathRole)[1]
        add_clickable_rectangle(index, option, bg_rect, text)

        self.draw_subdir_rectangles(bg_rect, *args)

        self.paint_asset_name(
            *args, offset=(bg_rect.right() - rectangles[DataRect].left()))

    @save_painter
    def paint_asset_name(self, *args, offset=0):
        """Paints name of the ``AssetWidget``'s items."""
        (
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
        ) = args

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

        description_rect = get_description_rectangle(
            index, option.rect, self.parent().buttons_hidden())

        if not description_rect:
            description_rect = self._get_asset_description_rect(
                index, option, rectangles, metrics, offset)

        if description_rect and description_rect.contains(cursor_position):
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
            draw_painter_path(painter, x, y, font, text)

        # Monkey patch
        data_rect = QtCore.QRect(rectangles[DataRect])
        rectangles[DataRect].setRight(rectangles[DataRect].right() - offset)

        if not self.parent().buttons_hidden():
            rectangles[DataRect].setRight(
                rectangles[DataRect].right() - common.size(common.size_margin)
            )

        if hover or selected or active:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.66)

        # If the text segments role has not yet been set, we'll set it here
        text_segments = get_text_segments(index)
        text = ''.join([text_segments[f][0] for f in text_segments])

        # Get the label background rectangle
        rect, r = get_asset_subdir_bg(rectangles, metrics, text)

        # Apply offset
        r.moveLeft(r.left() + offset)
        rect.moveLeft(rect.left() + offset)

        color = common.color(common.color_dark_green)
        color = color if active else common.color(common.color_blue)
        color = common.color(common.color_green).darker(150) if r.contains(
            cursor_position) else color
        color = common.color(common.color_separator) if archived else color

        if r.contains(cursor_position):
            if alt_modifier or control_modifier:
                color = common.color(common.color_red)
            elif shift_modifier or control_modifier:
                color = common.color(common.color_green)

        painter.setBrush(color)
        pen = QtGui.QPen(color.darker(220))
        pen.setWidth(common.size(common.size_separator))
        if not archived:
            painter.setPen(pen)

        if r.width() > common.size(common.size_margin):
            painter.drawRoundedRect(
                r, common.size(common.size_indicator), common.size(common.size_indicator)
            )

        _offset = 0

        o = common.size(common.size_indicator)
        painter.setPen(QtCore.Qt.NoPen)

        filter_text = self.parent().model().filter_text()
        overlay_rect_left_edge = None

        for segment in text_segments.values():
            text, _color = segment

            _text = text
            width = metrics.width(text)
            _r = QtCore.QRect(rect)
            _r.setWidth(width)
            center = _r.center()
            _r.setHeight(metrics.ascent())
            _r.moveCenter(center)
            _r.moveLeft(_r.left() + _offset)

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
                if hover or active or selected:
                    _color = common.color(common.color_green).lighter(150)
                else:
                    _color = common.color(common.color_green)
            _color = common.color(common.color_disabled_text) if archived else _color

            # Skip painting separator characters but mark the center of the rectangle
            # for alter use
            if '|' in text:
                overlay_rect_left_edge = _r.x() + (metrics.width(text) / 2.0)
            else:
                # Let's save the rectangle as a clickable rect
                add_clickable_rectangle(index, option, _r, _text)

                painter.setBrush(_color)
                x = _r.x()
                y = (
                        rectangles[DataRect].center().y() +
                        (metrics.ascent() * 0.5) - common.size(common.size_separator)
                )
                draw_painter_path(painter, x, y, font, text)

            _offset += width

        if overlay_rect_left_edge:
            __r = QtCore.QRect(r)
            __r.setLeft(overlay_rect_left_edge)

            painter.setOpacity(0.2)
            painter.setBrush(common.color(common.color_dark_blue))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(__r)

        rectangles[DataRect] = data_rect

    @save_painter
    def paint_file_name(self, *args):
        """Paints the clickable sub-folders and the filename of file items.

        """
        (
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
        ) = args

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return

        large_mode = option.rect.height() >= (common.size(common.size_row_height) * 2)

        it = get_text_segments(index).values()

        if large_mode:
            font, metrics = common.font_db.bold_font(
                common.size(common.size_font_small) * 1.1
            )
        else:
            font, metrics = common.font_db.bold_font(
                common.size(common.size_font_small)
            )
        left = draw_file_text_segments(it, font, metrics, 0, *args)

        # Clickable labels rectangles
        bg_rect = draw_subdir_bg_rectangles(
            left - common.size(common.size_margin), *args
        )

        it = get_file_detail_text_segments(index).values()
        if large_mode:
            font, metrics = common.font_db.light_font(
                common.size(common.size_font_small - 0.5)
            )
        else:
            font, metrics = common.font_db.light_font(
                common.size(common.size_font_small - 0.5)
            )
        left = draw_file_text_segments(it, font, metrics, metrics.height(), *args)

        if large_mode:
            font, metrics = common.font_db.bold_font(
                common.size(common.size_font_small)
            )
        else:
            font, metrics = common.font_db.medium_font(
                common.size(common.size_font_small)
            )
        self.draw_file_description(
            font,
            metrics,
            bg_rect.right(),
            left,
            metrics.height(),
            large_mode,
            *args
        )

        self.draw_subdir_rectangles(
            bg_rect,
            *args
        )

    @save_painter
    def paint_dcc_icon(self, *args):
        """Paints the item's DCC icon.

        """
        (
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
        ) = args

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

        pixmap = images.rsc_pixmap(
            icon,
            None,
            common.size(common.size_margin),
            resource=common.FormatResource
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())


class BookmarkItemViewDelegate(ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.bookmark_items.BookmarkItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'bookmark_item'

    def setEditorData(self, editor, index):
        source_path = index.data(common.ParentPathRole)
        if not source_path:
            return

        p = index.data(common.PathRole)
        if common.is_collapsed(p):
            k = common.proxy_path(index)
        else:
            k = p

        # Get the database value
        db = database.get_db(*source_path[0:3])
        v = db.value(k, 'description', database.BookmarkTable)

        editor.setText(v)

    def setModelData(self, editor, model, index):
        text = f'{index.data(common.DescriptionRole)}'
        if text.lower() == editor.text().lower():
            return
        source_path = index.data(common.ParentPathRole)
        if not source_path:
            return

        p = index.data(common.PathRole)
        if common.is_collapsed(p):
            k = common.proxy_path(index)
        else:
            k = p

        # Set the database value
        db = database.get_db(*source_path[0:3])
        with db.connection():
            db.set_value(k, 'description', editor.text(), table=database.BookmarkTable)
            bookmark_row_data = db.get_row(db.source(), database.BookmarkTable)

        # Set value to cached data
        source_index = index.model().mapToSource(index)
        data = source_index.model().model_data()
        idx = source_index.row()

        from ..threads import workers
        data[idx][common.DescriptionRole] = editor.text()
        data[idx][common.DescriptionRole] = workers.get_bookmark_description(
            bookmark_row_data)

    def paint(self, painter, option, index):
        """Paints a :class:`bookmarks.items.bookmark_items.BookmarkItemView`
        item.

        """
        if index.column() == 0:
            args = self.get_paint_arguments(painter, option, index)
            self.paint_background(*args)
            self.paint_default(*args)
            draw_gradient_background(*args)
            self.paint_active(*args)
            self.paint_hover(*args)
            self.paint_thumbnail_shadow(*args)
            self.paint_name(*args)
            self.paint_archived(*args)
            self.paint_inline_background(*args)
            self.paint_inline_icons(*args)
            self.paint_thumbnail(*args)
            self.paint_thumbnail_drop_indicator(*args)
            self.paint_description_editor_background(*args)
            self.paint_selection_indicator(*args)
            self.paint_slack_status(*args)
            self.paint_shotgun_status(*args)
            self.paint_db_status(*args)
            self.paint_drag_source(*args)
            self.paint_deleted(*args)

    def sizeHint(self, option, index):
        """Returns the item's size hint.

        """
        return self.parent().model().sourceModel().row_size


class AssetItemViewDelegate(ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.asset_items.AssetItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'asset_item'

    def paint(self, painter, option, index):
        """Paints a :class:`bookmarks.items.asset_items.AssetItemView`
        item.

        """
        if index.column() == 0:
            if index.data(QtCore.Qt.DisplayRole) is None:
                return  # The index might still be populated...
            args = self.get_paint_arguments(painter, option, index)
            self.paint_background(*args)
            draw_gradient_background(*args)
            self.paint_active(*args)
            self.paint_hover(*args)
            self.paint_thumbnail_shadow(*args)
            self.paint_name(*args)
            self.paint_archived(*args)
            self.paint_description_editor_background(*args)
            self.paint_inline_background(*args)
            self.paint_inline_icons(*args)
            self.paint_thumbnail(*args)
            self.paint_thumbnail_drop_indicator(*args)
            self.paint_selection_indicator(*args)
            self.paint_shotgun_status(*args)
            self.paint_db_status(*args)
            self.paint_dcc_icon(*args)
            self.paint_drag_source(*args)
            self.paint_deleted(*args)

    def sizeHint(self, option, index):
        """Returns the item's size hint.

        """
        return self.parent().model().sourceModel().row_size


class FileItemViewDelegate(ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.file_items.FileItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'file_item'

    def __init__(self, parent=None):
        super(FileItemViewDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """Paints a :class:`bookmarks.items.file_items.FileItemView`
        item.

        """
        if index.column() == 0:
            args = self.get_paint_arguments(painter, option, index)
            if not index.data(QtCore.Qt.DisplayRole):
                return
            p_role = index.data(common.ParentPathRole)
            if p_role:
                self.paint_background(*args)
                draw_gradient_background(*args)
                self.paint_active(*args)
                self.paint_hover(*args)
                self.paint_name(*args)

            self.paint_thumbnail_shadow(*args)

            self.paint_archived(*args)
            self.paint_inline_background(*args)
            self.paint_inline_icons(*args)
            self.paint_selection_indicator(*args)
            self.paint_thumbnail(*args)
            self.paint_thumbnail_drop_indicator(*args)
            self.paint_description_editor_background(*args)
            self.paint_drag_source(*args)
            self.paint_deleted(*args)
            self.paint_db_status(*args)

    def sizeHint(self, option, index):
        """Returns the item's size hint.

        """
        return self.parent().model().sourceModel().row_size


class FavouriteItemViewDelegate(FileItemViewDelegate):
    """The delegate used to render
    :class:`bookmarks.items.favourite_items.FavouriteItemView` items.

    """
    fallback_thumb = 'favourite_item'
