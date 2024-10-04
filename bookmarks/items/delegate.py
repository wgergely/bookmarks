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
AddItemRect = 3
TodoRect = 4
RevealRect = 5
ArchiveRect = 6
FavouriteRect = 7
DataRect = 8
PropertiesRect = 9
InlineBackgroundRect = 10

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
            for arg in args:
                if isinstance(arg, QtGui.QFont):
                    arg.setUnderline(False)

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
    k = f'[{font.family(), font.pixelSize(), font.underline()}]{text}'

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
    if not text or not rect or not index.isValid() or any(c in text for c in '|/\\•'):
        return

    k = get_clickable_cache_key(index, option.rect)
    v = (rect, text)
    common.delegate_clickable_rectangles.setdefault(k, []).append(v)


@functools.lru_cache(maxsize=4194304)
def _get_pixmap_rect(rect_height, pixmap_width, pixmap_height):
    s = float(rect_height)
    longest_edge = float(max((pixmap_width, pixmap_height)))
    ratio = s / longest_edge
    w = pixmap_width * ratio
    h = pixmap_height * ratio
    return QtCore.QRect(0, 0, int(w), int(h))


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

    s_color = common.Color.VeryDarkBackground()

    # Process each subfolder as a separate text segment
    v = text.split('/')

    for i, s in enumerate(v):
        if i == 0:
            c = common.Color.Text()
        else:
            c = common.Color.SecondaryText()

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
            d[len(d)] = (label, common.Color.Text())
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
        s = '.'.join(s[:-1]) + '.' + s[-1].lower()
        d[len(d)] = (s, common.Color.Text())

        # Frame-range without the "[]" characters
        s = match.group(2)
        s = regex_remove_seq_marker.sub('', s)
        if len(s) > 17:
            s = s[0:8] + '...' + s[-8:]
        if len(f) > 1:
            d[len(d)] = (s, common.Color.Red())
        else:
            d[len(d)] = (s, common.Color.Text())

        # Filename
        d[len(d)] = (
            match.group(1), common.Color.SelectedText())
        common.delegate_text_segments[k] = d
        return d

    # Item is a non-collapsed sequence
    match = common.get_sequence(s)
    if match:
        # The extension and the suffix
        if match.group(4):
            s = match.group(3) + '.' + match.group(4).lower()
        else:
            s = match.group(3)
        d[len(d)] = (s, common.Color.SelectedText())

        # Sequence
        d[len(d)] = (match.group(
            2
        ), common.Color.SecondaryText())

        # Prefix
        d[len(d)] = (
            match.group(1), common.Color.SelectedText())
        common.delegate_text_segments[k] = d
        return d

    # Item is not collapsed, and isn't a sequence either
    s = s.split('.')
    if len(s) > 1:
        s = '.'.join(s[:-1]) + '.' + s[-1].lower()
    else:
        s = s[0]
    d[len(d)] = (s, common.Color.SelectedText())
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
        d[len(d)] = ('...', common.Color.SecondaryText())
        return d

    text = index.data(common.FileDetailsRole)
    texts = text.split(';')
    for n, text in enumerate(reversed(texts)):
        d[len(d)] = (text, common.Color.SecondaryText())
        if n == (len(texts) - 1) and not index.data(common.DescriptionRole):
            break
        d[len(d)] = ('  |  ', common.Color.DarkBackground())

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
        common.Size.Indicator(3.0)
    )

    o = 0.95 if selected else 0.9
    o = 1.0 if hover else o
    painter.setOpacity(o)
    painter.setPen(QtCore.Qt.NoPen)

    for v in it:
        text, color = v

        color = common.Color.SelectedText() if selected else color
        color = common.Color.Text() if hover else color

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

        x = rect.center().x() - (width / 2.0) + common.Size.Separator()
        y = rect.center().y() + offset

        painter.setBrush(color)
        draw_painter_path(painter, x, y, font, text)

        rect.translate(-width, 0)

    return x


def get_subdir_cache_key(index, rect):
    """Returns the cache key used to store subfolder rectangles.

    Returns:
        str: The cache key.

    """
    return f'{index.data(QtCore.Qt.DisplayRole)}_subdir:[{rect.x()},{rect.y()},{rect.width()},{rect.height()}]'


def get_subdir_bg_cache_key(index, rect, text_edge=None):
    """Returns the cache key used to store subfolder background rectangles.

    Returns:
        str: The cache key.

    """
    p = index.data(QtCore.Qt.DisplayRole)
    d = index.data(common.DescriptionRole) if not common.settings.value('settings/hide_item_descriptions') else ''
    return f'{p}:{d}:[{rect.x()},{rect.y()},{rect.width()},{rect.height()},{text_edge}]'


def get_clickable_cache_key(index, rect):
    """Returns the cache key used to store subfolder background rectangles.

    Args:
        index (QModelIndex): Item index.
        rect (QRect): The item's rectangle.

    Returns:
        str: The cache key.

    """
    p = index.data(common.QtCore.Qt.DisplayRole)
    f = index.data(common.FileDetailsRole)
    d = index.data(common.DescriptionRole) if not common.settings.value('settings/hide_item_descriptions') else ''
    return f'{p}:{f}:{d}:[{rect.x()},{rect.y()},{rect.width()},{rect.height()}]'


def get_description_cache_key(index, rect, button):
    """Returns the cache key used to store subfolder background rectangles.

    Args:
        index (QModelIndex): Item index.
        rect (QRect): The item's rectangle.
        button (bool): Inline icon visibility state.

    Returns:
        str: The cache key.

    """
    p = index.data(common.QtCore.Qt.DisplayRole)
    f = index.data(common.FileDetailsRole)
    d = index.data(common.DescriptionRole) if not common.settings.value('settings/hide_item_descriptions') else ''
    return f'{p}:{f}:{d}:{button}:[{rect.x()},{rect.y()},{rect.width()},{rect.height()}]'


def get_subdir_rectangles(option, index, rectangles, metrics):
    """Returns the rectangles used to render subfolder item labels.

    """
    k = get_subdir_cache_key(index, option.rect)
    if k in common.delegate_subdir_rectangles:
        return common.delegate_subdir_rectangles[k]

    common.delegate_subdir_rectangles[k] = []

    pp = index.data(common.ParentPathRole)
    if not pp:
        return common.delegate_subdir_rectangles[k]

    padding = common.Size.Indicator()
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
    """Yields text elements to be rendered as subfolder item labels.

    """
    if len(pp) == 3:  # Bookmark items
        yield pp[1]  # job name
        return
    elif len(pp) == 4:  # Asset items
        yield
        return
    elif len(pp) > 5:  # File items
        for s in pp[5].split('/'):
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
        return get_asset_text_segments(
            index.data(QtCore.Qt.DisplayRole),
            ''
        )
    elif len(pp) == 4:
        return get_asset_text_segments(
            index.data(QtCore.Qt.DisplayRole),
            ''
        )
    elif len(pp) > 4:
        return get_file_text_segments(
            index.data(QtCore.Qt.DisplayRole),
            index.data(common.PathRole),
            tuple(index.data(common.FramesRole))
        )


def get_asset_subdir_bg(rectangles, metrics, text):
    rect = QtCore.QRect(rectangles[DataRect])
    rect.setLeft(rect.left() + common.Size.Margin())

    o = common.Size.Indicator()

    text_width = metrics.width(text)
    r = QtCore.QRect(rect)
    r.setWidth(text_width)
    center = r.center()
    r.setHeight(metrics.height() + (common.Size.Separator(4.0)))
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
        o = common.Size.Indicator()
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
    o = common.Size.Indicator(2.0)
    if rect.right() > (text_edge + o):
        rect.setRight(text_edge)

    # Make sure not to shrink the rectangle too small
    if rect.left() + common.Size.Margin() < text_edge + o:
        if rect.contains(cursor_position):
            painter.setBrush(QtGui.QColor(0, 0, 0, 80))
        else:
            painter.setBrush(QtGui.QColor(0, 0, 0, 40))
        pen = QtGui.QPen(common.Color.Opaque())
        pen.setWidthF(common.Size.Separator())
        painter.setPen(pen)
        painter.drawRoundedRect(rect, o * 0.66, o * 0.66)
        return rect

    return QtCore.QRect()


class ItemDelegate(QtWidgets.QStyledItemDelegate):
    """The main delegate used to represent lists derived from `base.BaseItemView`.

    """
    fallback_thumb = 'placeholder'

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._min = 0
        self._max = 0
        self._gradient_pixmap = self._create_gradient_pixmap()

    def switcher_visible(self):
        if self.parent() and hasattr(self.parent(), 'switcher_visible') and self.parent().switcher_visible:
            return True
        return False

    def _get_largest_screen_width(self):
        # Get all available screens
        screens = QtWidgets.QApplication.screens()
        # Return the width of the largest screen
        return max(screen.geometry().width() for screen in screens)

    def _create_gradient_pixmap(self):
        width = self._get_largest_screen_width()

        # 1. Set up the linear gradient
        gradient = QtGui.QLinearGradient()
        gradient.setStart(QtCore.QPoint(0, 0))
        gradient.setFinalStop(QtCore.QPoint(width, 0))

        # 2. Define the color stops
        # gradient.setSpread(QtGui.QGradient.PadSpread)
        gradient.setColorAt(0.0, common.Color.VeryDarkBackground())
        gradient.setColorAt(1.0, common.Color.Transparent())

        # 3. Create a QPixmap and fill it with transparent color
        pixmap = QtGui.QPixmap(width, 1)
        pixmap.setDevicePixelRatio(common.pixel_ratio)
        pixmap.fill(QtCore.Qt.transparent)

        # 4. Render the gradient onto the QPixmap
        painter = QtGui.QPainter(pixmap)
        painter.fillRect(pixmap.rect(), gradient)
        painter.end()

        return pixmap

    def createEditor(self, parent, option, index):
        if not index.data(common.FileInfoLoaded):
            return None

        description_rect = get_description_rectangle(
            index, option.rect, self.parent().buttons_hidden()
        )
        if not description_rect:
            return None

        editor = ui.LineEdit(parent=parent)
        editor.setPlaceholderText('Enter an item description...')
        editor.returnPressed.connect(lambda: self.commitData.emit(editor))
        editor.returnPressed.connect(lambda: self.closeEditor.emit(editor))
        return editor

    def updateEditorGeometry(self, editor, option, index):
        rectangles = self.get_rectangles(index)
        editor.setStyleSheet(f'height: {rectangles[DataRect].height()}px;')
        editor.setGeometry(rectangles[DataRect])

    def setEditorData(self, editor, index):
        """Sets the data to be displayed and edited by the editor from the data model item specified by the model index.

        """
        v = index.data(common.DescriptionRole)
        v = v if v else ''
        editor.setText(v)
        editor.selectAll()
        editor.setFocus()

    def setModelData(self, editor, model, index):
        """Sets the model data for the given index to the given value.

        """
        text = index.data(common.DescriptionRole)
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

        # Sanitize text string to remove duplicate "#" symbols

        v = editor.text().strip() if editor.text() else ''

        # Set the database value
        # Note that we don't need to set the data directly as
        # the database will emit a value changed signal that will
        # automatically update the views and model data caches
        db = database.get(*source_path[0:3])
        db.set_value(k, 'description', common.sanitize_hashtags(v), database.AssetTable)

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
            return r.adjusted(0, 0, 0, -common.Size.Separator())

        background_rect = _adjusted()
        background_rect.setLeft(common.Size.Indicator())

        indicator_rect = QtCore.QRect(r)
        indicator_rect.setWidth(common.Size.Indicator())

        thumbnail_rect = QtCore.QRect(r)
        thumbnail_rect.setWidth(thumbnail_rect.height())
        thumbnail_rect.moveLeft(common.Size.Indicator())

        # Inline icons rect
        inline_icon_rects = []
        inline_icon_rect = _adjusted()
        spacing = common.Size.Indicator(2.5)
        center = inline_icon_rect.center()
        size = QtCore.QSize(
            common.Size.Margin(),
            common.Size.Margin()
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
                    _n
                ) else null_rect,
                RevealRect: inline_icon_rects[next(n)] if count > next(_n) else null_rect,
                TodoRect: inline_icon_rects[next(n)] if count > next(_n) else null_rect,
                FavouriteRect: inline_icon_rects[next(n)] if count > next(
                    _n
                ) else null_rect,
                AddItemRect: inline_icon_rects[next(n)] if count > next(
                    _n
                ) else null_rect,
                PropertiesRect: inline_icon_rects[next(n)] if count > next(
                    _n
                ) else null_rect,
                InlineBackgroundRect: inline_background_rect if count else null_rect,
                DataRect: data_rect
            }
        else:
            common.delegate_rectangles[k] = {
                BackgroundRect: background_rect,
                IndicatorRect: indicator_rect,
                ThumbnailRect: thumbnail_rect,
                ArchiveRect: inline_icon_rects[next(n)] if count > next(
                    _n
                ) else null_rect,
                RevealRect: inline_icon_rects[next(n)] if count > next(_n) else null_rect,
                TodoRect: inline_icon_rects[next(n)] if count > next(_n) else null_rect,
                AddItemRect: inline_icon_rects[next(n)] if count > next(
                    _n
                ) else null_rect,
                PropertiesRect: inline_icon_rects[next(n)] if count > next(
                    _n
                ) else null_rect,
                FavouriteRect: inline_icon_rects[next(n)] if count > next(
                    _n
                ) else null_rect,
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
        _rect.setLeft(r.right() + common.Size.Margin() + offset)
        _rect.setTop(r.top())
        _rect.setBottom(r.bottom())
        _rect.setRight(rect.right() - common.Size.Margin())

        # Cache the calculated rectangle
        k = get_description_cache_key(index, option.rect, self.parent().buttons_hidden())
        common.delegate_description_rectangles[k] = _rect

        return common.delegate_description_rectangles[k]

    def get_paint_arguments(self, painter, option, index, track_cursor=True, antialiasing=False):
        """A utility class for gathering all the arguments needed to paint
        the individual list elements.

        """
        if antialiasing:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

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

        if option.rect.height() < common.Size.RowHeight(1.5):
            font, metrics = common.Font.MediumFont(common.Size.SmallText())
        else:
            font, metrics = common.Font.BoldFont(common.Size.MediumText())
        painter.setFont(font)

        if track_cursor:
            cursor_position = self.parent().viewport().mapFromGlobal(common.cursor.pos())
        else:
            cursor_position = None

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

        font, metrics = common.Font.MediumFont(common.Size.SmallText())

        # Paint the background rectangle of the subfolder
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
                rect.setRight(bg_rect.right() - common.Size.Indicator())

            # Set the hover color based on the keyboard modifier and the filter text
            o = 0.6 if hover else 0.5
            color = common.Color.DarkBackground()

            # Green highlight for matching subfolders
            if index.model().filter.has_string(text, positive_terms=True):
                color = common.Color.Green()

            if rect.contains(cursor_position):
                o = 1.0
                if alt_modifier or control_modifier:
                    color = common.Color.Red()
                elif shift_modifier or control_modifier:
                    color = common.Color.Green()

            painter.setOpacity(o)
            painter.setBrush(color)
            o = common.Size.Indicator()
            if n == 0:
                pen = QtGui.QPen(common.Color.VeryDarkBackground())
            else:
                pen = QtGui.QPen(common.Color.Opaque())

            pen.setWidth(common.Size.Separator(2.0))
            painter.setPen(pen)
            painter.drawRoundedRect(rect, o, o)

            # add the rectangle as a clickable rectangle
            add_clickable_rectangle(index, option, rect, text)

            if metrics.horizontalAdvance(text) > rect.width():
                text = elided_text(
                    metrics,
                    text,
                    QtCore.Qt.ElideRight,
                    rect.width() - (common.Size.Indicator(2.0))
                )

            x = rect.center().x() - (metrics.horizontalAdvance(text) / 2.0)
            y = (
                    rectangles[DataRect].center().y() +
                    (metrics.ascent() * 0.5) - common.Size.Separator()
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
        if len(pp) <= 4:
            return self.paint_asset_name(
                *args,
                offset=common.Size.Indicator()
            )
        elif len(pp) > 4:
            return self.paint_file_name(*args)

    @save_painter
    def draw_file_description(
            self, font, metrics, left_limit, right_limit, offset,
            large_mode, *args
    ):
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
            _o = (common.Size.Indicator(2.0))
            right_limit = rectangles[DataRect].right() - _o
            left_limit = rectangles[DataRect].left() + _o
        else:
            right_limit -= common.Size.Indicator()
            left_limit += common.Size.Margin()
        if left_limit < rectangles[DataRect].left():
            left_limit = rectangles[DataRect].left()

        rect = get_description_rectangle(
            index, option.rect, self.parent().buttons_hidden()
        )

        if not rect:
            rect = self._get_file_description_rect(
                left_limit, right_limit, offset, large_mode,
                rectangles, metrics, index, option
            )

        color = common.Color.Green()
        color = common.Color.SelectedText() if selected else color

        if hover:
            painter.setOpacity(0.3)
            painter.setBrush(common.Color.VeryDarkBackground())
            _rect = QtCore.QRect(rect)
            _rect.setHeight(common.Size.Separator())
            _rect.moveTop(rect.center().y())
            painter.drawRect(_rect)

            painter.setOpacity(1.0)
            color = common.Color.SelectedText()

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

        label_bg_color = common.Color.Blue()
        label_text_color = common.Color.Text()

        for s in reversed(it):
            width = metrics.horizontalAdvance(s)

            if '#' in s:
                width += o * 2

            x -= width

            if '#' in s:
                _o = common.Size.Separator(2.0)
                rect = QtCore.QRect(
                    x,
                    y - metrics.ascent() - (_o / 2.0),
                    width,
                    metrics.lineSpacing() + _o
                )
                painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

                painter.setBrush(label_bg_color)

                if index.model().filter.has_string(s, positive_terms=True):
                    painter.setBrush(common.Color.Green())
                if rect.contains(cursor_position):
                    painter.setBrush(common.Color.LightBackground())

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
            left_limit = rectangles[DataRect].left() + common.Size.Margin()
            right_limit = rectangles[DataRect].right() - common.Size.Margin()
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

        painter.setBrush(common.Color.DarkBackground())
        painter.setPen(QtCore.Qt.NoPen)
        rect = QtCore.QRect(rectangles[DataRect])

        o = common.Size.Indicator(0.5)
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

        painter.setBrush(common.Color.VeryDarkBackground())
        painter.drawRect(rectangles[ThumbnailRect])

        if not index.data(common.ParentPathRole):
            return

        server, job, root = index.data(common.ParentPathRole)[0:3]
        source = index.data(common.PathRole)

        size_role = index.data(QtCore.Qt.SizeHintRole)
        if not source or not size_role:
            return

        if self.parent().verticalScrollBar().isSliderDown():
            pixmap = images.rsc_pixmap(
                self.fallback_thumb,
                color=None,
                size=size_role.height(),
            )
            color = common.Color.Transparent()
        else:
            pixmap, color = images.get_thumbnail(
                server,
                job,
                root,
                source,
                size_role.height(),
                fallback_thumb=self.fallback_thumb
            )

        # Background
        if not common.settings.value('settings/paint_thumbnail_bg'):
            if color:
                painter.setOpacity(0.5)
            color = color if color else QtGui.QColor(0, 0, 0, 50)
            painter.setBrush(color)
            if archived:
                painter.setOpacity(0.1)
            painter.drawRect(rectangles[ThumbnailRect])

        o = 0.8 if selected or active or hover else 0.65
        painter.setOpacity(o)

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
            painter.setBrush(common.Color.VeryDarkBackground())
            painter.drawRect(option.rect)

            painter.setPen(common.Color.Green())
            font, metrics = common.Font.MediumFont(
                common.Size.SmallText()
            )
            painter.setFont(font)

            text = 'Drop image to add as thumbnail'
            painter.drawText(
                option.rect.adjusted(
                    common.Size.Margin(), 0, -common.Size.Margin(), 0
                ),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter |
                QtCore.Qt.TextWordWrap,
                text,
                boundingRect=option.rect,
            )

            o = common.Size.Separator(2.0)
            rect = rectangles[ThumbnailRect].adjusted(o, o, -o, -o)
            painter.drawRect(rect)

            pen = QtGui.QPen(common.Color.Green())
            pen.setWidth(o)
            painter.setPen(pen)
            painter.setBrush(common.Color.Green())
            painter.setOpacity(0.5)
            pixmap = images.rsc_pixmap(
                'add', common.Color.Green(), rect.height() * 0.5
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
        if index.row() == (index.model().rowCount() - 1):
            rect.setHeight(rect.height() + common.Size.Separator())

        op = 0.5 if selected else 0.2

        rect.setLeft(
            option.rect.left() +
            common.Size.Indicator() + option.rect.height()
        )
        painter.setOpacity(op)
        painter.setBrush(common.Color.Green())
        painter.drawRoundedRect(
            rect, common.Size.Indicator(),
            common.Size.Indicator()
        )
        painter.setOpacity(op)
        pen = QtGui.QPen(common.Color.Green())
        pen.setWidth(common.Size.Separator(2.0))
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        o = common.Size.Separator()
        rect = rect.adjusted(o, o, -(o * 1.5), -(o * 1.5))
        painter.drawRoundedRect(
            rect, common.Size.Indicator(),
            common.Size.Indicator()
        )

    def _draw_gradient_background(self, *args):
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
        k = get_subdir_bg_cache_key(index, option.rect, text_edge=text_edge)

        if k in common.delegate_bg_brushes:
            rect, gradient = common.delegate_bg_brushes[k]
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
                    start_x + (margin * 2),
                    0
                )
            )

            gradient.setSpread(QtGui.QGradient.PadSpread)
            color = QtGui.QColor(common.Color.Background())
            color.setAlpha(100)
            gradient.setColorAt(0.0, color)
            gradient.setColorAt(1.0, common.Color.Transparent())

            rect.moveCenter(
                QtCore.QPoint(
                    rect.center().x(),
                    rectangles[BackgroundRect].center().y()
                )
            )

        painter.setOpacity(1.0)
        painter.fillRect(rect, gradient)

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
        if index.row() == (index.model().rowCount() - 1):
            rect.setHeight(rect.height() + common.Size.Separator())

        color = common.Color.LightBackground()
        color = color if selected else common.Color.DarkBackground()
        painter.setBrush(color)

        painter.drawRect(rect)

        if selected or archived or active:
            return

        self._draw_gradient_background(*args)

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
        if index.row() == (index.model().rowCount() - 1):
            rect.setHeight(rect.height() + common.Size.Separator())

        color = common.Color.LightBackground()
        color = color if selected else common.Color.DarkBackground()
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

        if index.row() == (index.model().rowCount() - 1):
            rect = QtCore.QRect(rectangles[InlineBackgroundRect])
            rect.setHeight(rect.height() + common.Size.Separator())
        else:
            rect = rectangles[InlineBackgroundRect]

        # Inline bg rect
        o = common.Size.Indicator()
        _o = common.Size.Separator(4.0)

        r = QtCore.QRect(rect)
        r.setHeight(metrics.height() + _o)
        r.moveCenter(QtCore.QPoint(r.center().x(), rect.center().y()))
        r = r.adjusted(_o, -o, -_o, o)

        color = common.Color.LightBackground()
        color = common.Color.SecondaryText() if hover else color
        color = common.Color.Text() if selected else color
        color = common.Color.VeryDarkBackground() if archived else color
        painter.setBrush(color)

        pen = QtGui.QPen(color.darker(200))
        if not archived:
            pen.setWidth(common.Size.Separator(2.0))
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
    def _paint_inline_favourite(self, *args, _color=common.Color.VeryDarkBackground()):
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
        color = common.Color.SelectedText() if favourite else color

        pixmap = images.rsc_pixmap(
            'favourite', color, common.Size.Margin()
        )
        painter.drawPixmap(rect, pixmap)

    @save_painter
    def _paint_inline_archived(self, *args, _color=common.Color.VeryDarkBackground()):
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

        color = common.Color.Green()
        color = color if archived else common.Color.Red()
        color = color if rect.contains(cursor_position) else _color
        if archived:
            pixmap = images.rsc_pixmap(
                'archivedVisible', common.Color.Green(),
                common.Size.Margin()
            )
        else:
            pixmap = images.rsc_pixmap(
                'archivedHidden', color, common.Size.Margin()
            )
        painter.drawPixmap(rect, pixmap)

    @save_painter
    def _paint_inline_reveal(self, *args, _color=common.Color.VeryDarkBackground()):
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

        color = common.Color.SelectedText()
        color = color if rect.contains(cursor_position) else _color

        pixmap = images.rsc_pixmap(
            'folder', color, common.Size.Margin()
        )
        painter.drawPixmap(rect, pixmap)

    @save_painter
    def _paint_inline_todo(self, *args, _color=common.Color.VeryDarkBackground()):
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

        color = common.Color.SelectedText()
        color = color if rect.contains(cursor_position) else _color

        pixmap = images.rsc_pixmap(
            'todo', color, common.Size.Margin()
        )
        painter.drawPixmap(rect, pixmap)

        count = index.data(common.NoteCountRole)
        self.paint_inline_count(painter, rect, cursor_position, count, 'add')

    @save_painter
    def _paint_inline_add(self, *args, _color=common.Color.VeryDarkBackground()):
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

        color = common.Color.Green()
        color = color if rect.contains(cursor_position) else _color

        pixmap = images.rsc_pixmap(
            'add_circle', color, common.Size.Margin()
        )
        painter.drawPixmap(rect, pixmap)

        if len(index.data(common.ParentPathRole)) == 3:
            count = index.data(common.AssetCountRole)
            self.paint_inline_count(painter, rect, cursor_position, count, 'asset')

    @save_painter
    def _paint_inline_properties(
            self, *args,
            _color=common.Color.VeryDarkBackground()
    ):
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

        color = common.Color.SelectedText()
        color = color if rect.contains(cursor_position) else _color

        pixmap = images.rsc_pixmap(
            'settings', color, common.Size.Margin()
        )
        painter.drawPixmap(rect, pixmap)

    def paint_inline_count(self, painter, rect, cursor_position, count, icon):
        """Paints an item count.

        """
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        if not isinstance(count, (float, int)):
            return

        size = common.Size.LargeText()
        count_rect = QtCore.QRect(0, 0, size, size)
        count_rect.moveCenter(rect.bottomRight())

        if rect.contains(cursor_position):
            pixmap = images.rsc_pixmap(
                icon, common.Color.Green(), size
            )
            painter.drawPixmap(count_rect, pixmap)
            return

        if count < 1:
            return

        color = common.Color.Green()
        painter.setBrush(color)
        painter.drawRoundedRect(
            count_rect, count_rect.width() / 2.0, count_rect.height() / 2.0
        )

        text = str(count)
        _font, _metrics = common.Font.MediumFont(common.Size.SmallText())
        x = count_rect.center().x() - (_metrics.horizontalAdvance(text) / 2.0) + \
            common.Size.Separator()
        y = count_rect.center().y() + (_metrics.ascent() / 2.0) - (_metrics.descent() / 2.0)

        painter.setBrush(common.Color.Text())
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
        color = common.Color.Transparent()
        color = common.Color.Green() if active else color
        color = common.Color.SelectedText() if selected else color
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

        rect.setWidth(common.Size.Margin())
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.Size.Margin(0.5))
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(common.Size.Margin(1.5))
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
        painter.setBrush(common.Color.VeryDarkBackground())
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
        painter.setBrush(common.Color.Blue())
        painter.setOpacity(0.5)
        painter.drawRect(option.rect)

    @save_painter
    def paint_sg_status(self, *args):
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
        if not index.data(common.SGLinkedRole):
            return

        rect = QtCore.QRect(
            0, 0, common.Size.Margin(), common.Size.Margin()
        )

        offset = QtCore.QPoint(
            common.Size.Indicator(),
            common.Size.Indicator()
        )
        rect.moveBottomRight(
            rectangles[ThumbnailRect].bottomRight() - offset
        )

        painter.setOpacity(1.0) if hover else painter.setOpacity(0.9)

        pixmap = images.rsc_pixmap(
            'sg', common.Color.Text(), common.Size.Margin()
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @save_painter
    def paint_db_status(self, *args):
        """Paints the item's configuration status.

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

        db = database.get(*index.data(common.ParentPathRole)[0:3])
        if db.is_valid():
            return

        rect = QtCore.QRect(
            0, 0, common.Size.Margin(), common.Size.Margin()
        )
        rect.moveCenter(rectangles[BackgroundRect].center())

        painter.setOpacity(1.0) if hover else painter.setOpacity(0.9)

        pixmap = images.rsc_pixmap(
            'alert', common.Color.Red(), common.Size.Margin()
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        painter.setBrush(common.Color.Red())
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
            painter.setBrush(common.Color.VeryDarkBackground())
            painter.drawRect(rectangles[DataRect])

            painter.setOpacity(1.0)
            painter.setBrush(QtCore.Qt.NoBrush)
            pen = QtGui.QPen(common.Color.SelectedText())
            pen.setWidthF(common.Size.Separator(2.0))
            painter.setPen(pen)
            painter.drawRect(rectangles[DataRect])

            font, metrics = common.Font.MediumFont(
                common.Size.SmallText()
            )
            painter.setFont(font)
            text = 'Paste item properties'
            painter.setPen(common.Color.Green())
            painter.drawText(
                option.rect.adjusted(
                    common.Size.Margin(), 0, -common.Size.Margin(), 0
                ),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter |
                QtCore.Qt.TextWordWrap,
                text,
                boundingRect=option.rect,
            )
            return

        if index.row() == self.parent().drag_source_row:
            painter.setBrush(common.Color.VeryDarkBackground())
            painter.drawRect(option.rect)

            painter.setPen(common.Color.Background())
            font, metrics = common.Font.MediumFont(
                common.Size.SmallText()
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
                    common.Size.Margin(), 0, -common.Size.Margin(), 0
                ),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter |
                QtCore.Qt.TextWordWrap,
                text,
                boundingRect=option.rect,
            )
        else:
            painter.setOpacity(0.33)
            painter.setBrush(common.Color.VeryDarkBackground())
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
        rect.setHeight(common.Size.Separator(2.0))
        rect.moveCenter(option.rect.center())
        painter.setBrush(common.Color.VeryDarkBackground())
        painter.drawRect(rect)

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

        if option.rect.height() < common.Size.RowHeight():
            font, metrics = common.Font.BoldFont(common.Size.MediumText(0.8))
        elif option.rect.height() > common.Size.RowHeight():
            font, metrics = common.Font.BoldFont(common.Size.MediumText(1.0))
        elif option.rect.height() > common.Size.RowHeight(4.0):
            font, metrics = common.Font.BoldFont(common.Size.MediumText(1.3))
        elif option.rect.height() > common.Size.RowHeight(8.0):
            font, metrics = common.Font.BoldFont(common.Size.MediumText(2.0))

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
            index, option.rect, self.parent().buttons_hidden()
        )

        if not description_rect:
            description_rect = self._get_asset_description_rect(
                index, option, rectangles, metrics, offset
            )

        if description_rect and description_rect.contains(cursor_position):
            underline_rect = QtCore.QRect(description_rect)
            underline_rect.setTop(underline_rect.bottom())
            underline_rect.moveTop(
                underline_rect.top() + common.Size.Separator()
            )
            painter.setOpacity(0.5)
            painter.setBrush(common.Color.VeryDarkBackground())

            painter.drawRect(underline_rect)

            painter.setOpacity(1.0)
            painter.setBrush(common.Color.SecondaryText())
            text = elided_text(
                metrics,
                'Double-click to edit description...',
                QtCore.Qt.ElideRight,
                description_rect.width(),
            )
            x = description_rect.left()
            y = description_rect.center().y() + (metrics.ascent() / 2.0) - (metrics.descent() / 2.0)
            draw_painter_path(painter, x, y, font, text)

        description = (index.data(common.DescriptionRole)
                       if not common.settings.value('settings/hide_item_descriptions') else '')

        if description:
            if description_rect.contains(cursor_position):
                painter.setOpacity(0.5)
            else:
                painter.setOpacity(1.0)

            _font, _metrics = common.Font.BoldFont(common.Size.MediumText(0.9))
            painter.setBrush(common.Color.Text())
            text = elided_text(
                _metrics,
                description,
                QtCore.Qt.ElideRight,
                description_rect.width(),
            )
            x = description_rect.right() - _metrics.width(text)
            y = description_rect.center().y() + (_metrics.ascent() / 2.0) - (_metrics.descent() / 2.0)
            draw_painter_path(painter, x, y, _font, text)

        # Monkey patch
        data_rect = QtCore.QRect(rectangles[DataRect])
        rectangles[DataRect].setRight(rectangles[DataRect].right() - offset)

        if not self.parent().buttons_hidden():
            rectangles[DataRect].setRight(
                rectangles[DataRect].right() - common.Size.Margin()
            )

        # If the text segments role has not yet been set, we'll set it here
        text_segments = get_text_segments(index)
        text = ''.join([text_segments[f][0] for f in text_segments])

        # Get the label background rectangle
        rect, r = get_asset_subdir_bg(rectangles, metrics, text)

        # Apply offset
        r.moveLeft(r.left() + offset)
        rect.moveLeft(rect.left() + offset)

        color = common.Color.Opaque()
        color = common.Color.VeryDarkBackground() if archived else color

        if r.contains(cursor_position):
            if alt_modifier or control_modifier:
                color = common.Color.Red()
            elif shift_modifier or control_modifier:
                color = common.Color.Green()

        painter.setBrush(color)
        pen = QtGui.QPen(common.Color.Opaque())
        pen.setWidth(common.Size.Separator())

        if not archived:
            painter.setPen(pen)

        if r.width() > common.Size.Margin():
            painter.drawRoundedRect(
                r, common.Size.Indicator(), common.Size.Indicator()
            )

        _offset = 0

        o = common.Size.Indicator()
        painter.setPen(QtCore.Qt.NoPen)

        overlay_rect_left_edge = None

        for segment in text_segments.values():
            text, _color = segment

            if index.model().filter.has_string(text, positive_terms=True):
                font.setUnderline(True)
                if hover or active or selected:
                    _color = common.Color.SelectedText()
                else:
                    _color = common.Color.Green().lighter(150)
                font.setBold(True)
            else:
                font.setUnderline(False)
                font.setBold(False)

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

            _color = common.Color.DisabledText() if archived else _color

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
                        (metrics.ascent() * 0.5) - common.Size.Separator()
                )
                draw_painter_path(painter, x, y, font, text)

            _offset += width

        if overlay_rect_left_edge:
            __r = QtCore.QRect(r)
            __r.setLeft(overlay_rect_left_edge)

            painter.setBrush(common.Color.Opaque())
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(__r)

        rectangles[DataRect] = data_rect

    @save_painter
    def paint_file_name(self, *args):
        """Paints the clickable subfolders and the filename of file items.

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

        large_mode = option.rect.height() >= (common.Size.RowHeight(2.0))

        it = get_text_segments(index).values()

        if large_mode:
            font, metrics = common.Font.MediumFont(common.Size.SmallText(1.1))
        else:
            font, metrics = common.Font.MediumFont(common.Size.SmallText())
        left = draw_file_text_segments(it, font, metrics, 0, *args)

        # Clickable labels rectangles
        bg_rect = draw_subdir_bg_rectangles(
            left - common.Size.Margin(), *args
        )

        it = get_file_detail_text_segments(index).values()
        if large_mode:
            font, metrics = common.Font.LightFont(common.Size.SmallText(0.9))
        else:
            font, metrics = common.Font.LightFont(common.Size.SmallText(0.85))
        left = draw_file_text_segments(it, font, metrics, metrics.height(), *args)

        if large_mode:
            font, metrics = common.Font.MediumFont(common.Size.SmallText())
        else:
            font, metrics = common.Font.MediumFont(common.Size.SmallText())
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

        d = index.data(common.PathRole)
        icon = next((DCC_ICONS[f] for f in DCC_ICONS if f.lower() in d.lower()), None)
        if not icon:
            return

        rect = QtCore.QRect(
            0, 0, common.Size.Margin(), common.Size.Margin()
        )

        offset = QtCore.QPoint(
            common.Size.Indicator(),
            common.Size.Indicator()
        )
        rect.moveTopLeft(
            rectangles[ThumbnailRect].topLeft() + offset
        )

        painter.setOpacity(0.9) if hover else painter.setOpacity(0.8)

        pixmap = images.rsc_pixmap(
            icon,
            None,
            common.Size.Margin(),
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
        db = database.get(*source_path[0:3])
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
        db = database.get(*source_path[0:3])
        v = editor.text().strip() if editor.text() else ''
        with db.connection():
            db.set_value(k, 'description', common.sanitize_hashtags(v), database.BookmarkTable)
            bookmark_row_data = db.get_row(db.source(), database.BookmarkTable)

        # Set value to cached data
        source_index = index.model().mapToSource(index)
        data = source_index.model().model_data()
        idx = source_index.row()

        from ..threads import workers
        data[idx][common.DescriptionRole] = v
        data[idx][common.DescriptionRole] = workers.get_bookmark_description(
            bookmark_row_data
        )

    def paint(self, painter, option, index):
        """Paints a :class:`bookmarks.items.bookmark_items.BookmarkItemView`
        item.

        """
        if self.switcher_visible():
            painter.fillRect(option.rect, common.Color.VeryDarkBackground())
            return

        if index.column() == 0:
            args = self.get_paint_arguments(painter, option, index)
            self.paint_background(*args)
            self.paint_default(*args)
            self.paint_active(*args)
            self.paint_hover(*args)
            self.paint_thumbnail_shadow(*args)
            self.paint_name(*args)

            if common.main_widget.stacked_widget.animation_in_progress:
                return

            self.paint_archived(*args)
            self.paint_inline_background(*args)
            self.paint_inline_icons(*args)
            self.paint_thumbnail(*args)
            self.paint_thumbnail_drop_indicator(*args)
            self.paint_description_editor_background(*args)
            self.paint_selection_indicator(*args)
            self.paint_sg_status(*args)
            self.paint_db_status(*args)
            self.paint_drag_source(*args)
            self.paint_deleted(*args)

    def sizeHint(self, option, index):
        """Returns the item's size hint.

        """
        return index.model().sourceModel().row_size


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
        if self.switcher_visible():
            painter.fillRect(option.rect, common.Color.VeryDarkBackground())
            return

        if index.column() == 0:
            if index.data(QtCore.Qt.DisplayRole) is None:
                return  # The index might still be populated...
            args = self.get_paint_arguments(painter, option, index)
            self.paint_background(*args)
            self.paint_active(*args)
            self.paint_hover(*args)
            self.paint_thumbnail_shadow(*args)
            self.paint_name(*args)

            if common.main_widget.stacked_widget.animation_in_progress:
                return

            self.paint_archived(*args)
            self.paint_description_editor_background(*args)
            self.paint_inline_background(*args)
            self.paint_inline_icons(*args)
            self.paint_thumbnail(*args)
            self.paint_thumbnail_drop_indicator(*args)
            self.paint_selection_indicator(*args)
            self.paint_sg_status(*args)
            self.paint_db_status(*args)
            self.paint_dcc_icon(*args)
            self.paint_drag_source(*args)
            self.paint_deleted(*args)

    def sizeHint(self, option, index):
        """Returns the item's size hint.

        """
        return index.model().sourceModel().row_size


class FileItemViewDelegate(ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.file_items.FileItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'file_item'

    def paint(self, painter, option, index):
        """Paints a :class:`bookmarks.items.file_items.FileItemView`
        item.

        """
        if self.switcher_visible():
            painter.fillRect(option.rect, common.Color.VeryDarkBackground())
            return

        if index.column() == 0:
            args = self.get_paint_arguments(painter, option, index)
            if not index.data(QtCore.Qt.DisplayRole):
                return

            p_role = index.data(common.ParentPathRole)
            if p_role:
                self.paint_background(*args)
                self.paint_active(*args)
                self.paint_hover(*args)
                self.paint_name(*args)

            if common.main_widget.stacked_widget.animation_in_progress:
                return

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
        return index.model().sourceModel().row_size


class FavouriteItemViewDelegate(FileItemViewDelegate):
    """The delegate used to render
    :class:`bookmarks.items.favourite_items.FavouriteItemView` items.

    """
    fallback_thumb = 'favourite_item'
