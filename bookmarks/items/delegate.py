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
from dataclasses import dataclass

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common, images
from .. import database
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

BackgroundRect = common.idx(start=1024, reset=True)
IndicatorRect = common.idx()
ThumbnailRect = common.idx()
DataRect = common.idx()

# Button rectangles
PropertiesRect = common.idx(start=1024, reset=True)
RevealRect = common.idx()
TodoRect = common.idx()
AddItemRect = common.idx()
FavouriteRect = common.idx()
ArchiveRect = common.idx()

clickable_rectangles = {
    PropertiesRect,
    RevealRect,
    TodoRect,
    AddItemRect,
    FavouriteRect,
    ArchiveRect
}


@dataclass
class PaintContext:
    painter: QtGui.QPainter
    option: QtWidgets.QStyleOptionViewItem
    index: QtCore.QModelIndex
    selected: bool
    focused: bool
    active: bool
    archived: bool
    favourite: bool
    hover: bool
    font: QtGui.QFont
    metrics: QtGui.QFontMetrics
    x: float
    y: float
    cursor_position: QtCore.QPoint
    buttons_hidden: bool
    # Rectangles
    BackgroundRect: QtCore.QRect
    IndicatorRect: QtCore.QRect
    ThumbnailRect: QtCore.QRect
    DataRect: QtCore.QRect
    # Button rectangles
    PropertiesRect: QtCore.QRect
    RevealRect: QtCore.QRect
    TodoRect: QtCore.QRect
    AddItemRect: QtCore.QRect
    FavouriteRect: QtCore.QRect
    ArchiveRect: QtCore.QRect


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
        font = None
        metrics = None

        for arg in args:
            if isinstance(arg, PaintContext):
                painter = arg.painter
                font = arg.font
                metrics = arg.metrics
                break

        if painter:
            painter.save()

        res = func(self, *args, **kwargs)

        if painter:
            painter.restore()
            for arg in args:
                if isinstance(arg, PaintContext):
                    arg.font.setUnderline(False)
                    arg.font.setBold(False)
                    arg.font.setItalic(False)
                    arg.font.setStrikeOut(False)
                    arg.font = font
                    arg.metrics = metrics
                    break
        return res

    return func_wrapper


class ItemDelegate(QtWidgets.QStyledItemDelegate):
    """The main delegate used to represent lists derived from `base.BaseItemView`.

    """
    fallback_thumb = 'placeholder'

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._min = 0
        self._max = 0

        self._filter_rectangles = {}

        self._filter_candidate_rectangle = None

    def createEditor(self, parent, option, index):
        if not index.isValid():
            return None

        if index.column() != 2:
            return None

        if not index.data(common.FileInfoLoaded):
            return None

        editor = ui.LineEdit(parent=parent)
        editor.setPlaceholderText('Enter an item description...')
        editor.returnPressed.connect(lambda: self.commitData.emit(editor))
        editor.returnPressed.connect(lambda: self.closeEditor.emit(editor))
        return editor

    def updateEditorGeometry(self, editor, option, index):
        if not index.isValid():
            return

        if index.column() != 2:
            return

        rect = QtCore.QRect(option.rect)
        o = common.Size.Separator(2.0)
        rect = rect.adjusted(o, o, -o, -o * 2.0)
        editor.setGeometry(rect)
        editor.setStyleSheet(
            f'background-color: {common.Color.VeryDarkBackground(qss=True)};'
            f'height: {rect.height()}px;'
            'border: none;'
        )

    def setEditorData(self, editor, index):
        """Sets the data to be displayed and edited by the editor from the data model item specified by the model index.

        """
        if not index.isValid():
            return

        if index.column() != 2:
            return

        v = index.data(common.DescriptionRole)
        v = v if v else ''
        editor.setText(v)
        editor.selectAll()
        editor.setFocus()

    def setModelData(self, editor, model, index):
        """Sets the model data for the given index to the given value.

        """
        if not index.isValid():
            return

        if index.column() != 2:
            pass

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

    def paint(self, painter, option, index):
        return super().paint(painter, option, index)

        self.clear_filter_candidate_rectangle()
        self.clear_filter_rectangles()

    def sizeHint(self, option, index):
        return index.data(QtCore.Qt.SizeHintRole)

    @staticmethod
    def get_rectangles(visual_rect, index, icon_count=0):
        """Return all rectangles needed to paint an item.

        Args:
            visual_rect (QRect): The visual rectangle of the item.
            index (QModelIndex): An item index.
            icon_count (int): The number of inline icons.

        Returns:
            dict: Dictionary containing `count` number of rectangles.

        """
        r = QtCore.QRect(visual_rect)
        # Gridline
        r = r.adjusted(0, 0, 0, -common.Size.Separator(2.0))

        rects = {
            BackgroundRect: null_rect,
            IndicatorRect: null_rect,
            ThumbnailRect: null_rect,
            AddItemRect: null_rect,
            TodoRect: null_rect,
            RevealRect: null_rect,
            ArchiveRect: null_rect,
            FavouriteRect: null_rect,
            DataRect: null_rect,
            PropertiesRect: null_rect,
        }

        if index.column() == 0:
            rects[IndicatorRect] = r

        if index.column() == 1:
            rects[ThumbnailRect] = r

        if index.column() == 2:
            r.setRight(r.right() - common.Size.Indicator())
            if index.row() == (index.model().rowCount() - 1):
                r.setBottom(r.bottom() - common.Size.Separator())
            rects[DataRect] = r

        if icon_count == 0:
            return rects

        if index.column() == 3:

            # Inline icons rect
            spacing = common.Size.Indicator(2.5)

            button_rect = QtCore.QRect()
            button_rect.setWidth(common.Size.Margin())
            button_rect.setHeight(common.Size.Margin())
            button_rect.moveCenter(r.center())

            # Align left to the edge (rect is out of bounds now)
            button_rect.moveLeft(r.right())

            for n in range(icon_count):
                # Move rect by its own width and add spacing and save it
                button_rect.moveRight(button_rect.right() - button_rect.width() - spacing)
                rects[1024 + n] = QtCore.QRect(button_rect)

            return rects

    @property
    def filter_candidate_rectangle(self):
        return self._filter_candidate_rectangle

    @QtCore.Slot(QtCore.QRect)
    def set_filter_candidate_rectangle(self, rect):
        self._filter_candidate_rectangle = rect

    @QtCore.Slot()
    def clear_filter_candidate_rectangle(self):
        self._filter_candidate_rectangle = None

    def filter_rectangles(self):
        return self._filter_rectangles

    def add_filter_rectangle(self, row, idx, rect, text):
        if row not in self._filter_rectangles:
            self._filter_rectangles[row] = {}
        self._filter_rectangles[row][idx] = (rect, text)

    def clear_filter_rectangles(self):
        self._filter_rectangles = {}

    def get_filter_rectangle(self, row, pos):
        if row not in self._filter_rectangles:
            return None, None
        for rect, text in self._filter_rectangles[row].values():
            if rect.contains(pos):
                return rect, text
        return None, None

    def gradient_pixmap(self, width, reverse=False):

        # 1. Set up the linear gradient
        gradient = QtGui.QLinearGradient()
        gradient.setStart(QtCore.QPoint(0, 0))
        gradient.setFinalStop(QtCore.QPoint(width, 0))

        # 2. Define the color stops
        gradient.setSpread(QtGui.QGradient.PadSpread)

        if reverse:
            gradient.setColorAt(0.0, common.Color.Transparent())
            gradient.setColorAt(1.0, common.Color.DarkBackground().darker(130))
        else:
            gradient.setColorAt(0.0, common.Color.DarkBackground().darker(130))
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

    def get_paint_context(self, painter, option, index, track_cursor=True, antialiasing=False):
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
        rectangles = self.get_rectangles(option.rect, index)

        if option.rect.height() < common.Size.RowHeight(1.5):
            font, metrics = common.Font.MediumFont(common.Size.SmallText())
        else:
            font, metrics = common.Font.BoldFont(common.Size.MediumText())
        painter.setFont(font)

        if track_cursor:
            cursor_position = self.parent().viewport().mapFromGlobal(common.cursor.pos())
        else:
            cursor_position = None

        option.rect = option.rect.adjusted(0, 0, 0, -(common.Size.Separator(1.0)))

        x = option.rect.left()
        y = option.rect.center().y() + metrics.ascent() / 2.0 - (metrics.descent() / 4.0)

        ctx = PaintContext(
            painter=painter,
            option=option,
            index=index,
            selected=selected,
            focused=focused,
            active=active,
            archived=archived,
            favourite=favourite,
            hover=hover,
            font=font,
            metrics=metrics,
            x=x,
            y=y,
            cursor_position=cursor_position,
            buttons_hidden=self.parent().buttons_hidden(),
            BackgroundRect=rectangles[BackgroundRect],
            IndicatorRect=rectangles[IndicatorRect],
            ThumbnailRect=rectangles[ThumbnailRect],
            DataRect=rectangles[DataRect],
            PropertiesRect=rectangles[PropertiesRect],
            RevealRect=rectangles[RevealRect],
            TodoRect=rectangles[TodoRect],
            AddItemRect=rectangles[AddItemRect],
            FavouriteRect=rectangles[FavouriteRect],
            ArchiveRect=rectangles[ArchiveRect]

        )
        return ctx

    @save_painter
    def paint_indicator(self, ctx):
        pass

    @save_painter
    def paint_background(self, ctx):
        """Paints the background for all list items."""
        if not ctx.index.isValid():
            return

        if ctx.index.flags() == QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return
        if ctx.archived:
            return

        ctx.painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        if ctx.index.column() == 0:
            pass
        elif ctx.index.column() == 1:
            color = common.Color.VeryDarkBackground().darker(120)
            color = color.lighter(105) if ctx.hover else color
            ctx.painter.setBrush(color)
            ctx.painter.drawRoundedRect(ctx.option.rect, common.Size.Indicator(1.5), common.Size.Indicator(1.5))
        elif ctx.index.column() == 2:
            color = common.Color.DarkBackground()
            color = common.Color.LightBackground() if ctx.selected else color
            color = color.lighter(105) if ctx.hover else color

            r = QtCore.QRect(ctx.option.rect)
            r.setLeft(r.center().x())
            ctx.painter.fillRect(r, color)

            ctx.painter.setBrush(color)
            r = QtCore.QRect(ctx.option.rect)
            r.setLeft(r.left() + common.Size.Separator(2.0))
            r.setRight(r.center().x() + common.Size.Indicator(1.5))
            ctx.painter.drawRoundedRect(r, common.Size.Indicator(1.5), common.Size.Indicator(1.5))
        elif ctx.index.column() == 3:
            color = common.Color.DarkBackground().darker(130)

            r = QtCore.QRect(ctx.option.rect)
            r.setRight(r.center().x())
            ctx.painter.fillRect(r, color)

            ctx.painter.setBrush(color)
            ctx.painter.drawRoundedRect(ctx.option.rect, common.Size.Indicator(1.5), common.Size.Indicator(1.5))

    @save_painter
    def paint_shadows(self, ctx):
        """Paints the item's thumbnail shadow.

        """
        r = QtCore.QRect(ctx.option.rect)
        r.setLeft(r.left() + common.Size.Separator(2.0))

        if ctx.index.column() == 2:
            ctx.painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, on=True)

            clip_path = QtGui.QPainterPath()
            clip_path.addRoundedRect(r, common.Size.Indicator(1.5), common.Size.Indicator(1.5))

            ctx.painter.save()
            ctx.painter.setClipPath(clip_path)

            pixmap = self.gradient_pixmap(common.Size.Margin(2.0))
            r.setWidth(common.Size.Margin(2.0))
            ctx.painter.drawPixmap(r, pixmap, pixmap.rect())
            ctx.painter.restore()

            pixmap = self.gradient_pixmap(common.Size.Margin(6.0), reverse=True)
            r = QtCore.QRect(ctx.option.rect)
            r.setLeft(r.right() - common.Size.Margin(6.0))
            ctx.painter.drawPixmap(r, pixmap, pixmap.rect())

    @save_painter
    def paint_clickable_filter_segments(
            self, ctx,
            rect=None,
            stretch=True,
            role=QtCore.Qt.DisplayRole,
            default_text='',
            font=None,
            metrics=None,
            draw_outline=True,
            opacity=1.0,
            accent_first=True,
            align_right=False,
            clickable_id_offset=0
    ):
        """Paints name of the `AssetWidget`'s items with performance optimizations and requested features."""

        # Early exit conditions
        if not ctx.index.isValid():
            return QtCore.QRect()
        if not ctx.index.data(QtCore.Qt.DisplayRole):
            return QtCore.QRect()
        if not ctx.index.data(common.ParentPathRole):
            return QtCore.QRect()
        if ctx.index.column() != 2:
            return QtCore.QRect()

        # Set rendering hints and opacity
        ctx.painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        ctx.painter.setOpacity(opacity)

        # Initialize font cache if it doesn't exist
        if not hasattr(self, '_font_cache'):
            self._font_cache = {}

        # Determine font size factor based on the height of the rect
        rect_height = ctx.option.rect.height()
        size_factor = 1.0  # default size factor

        if rect_height < common.Size.RowHeight():
            size_factor = 0.9
        elif rect_height > common.Size.RowHeight(8.0):
            size_factor = 1.3
        elif rect_height > common.Size.RowHeight(4.0):
            size_factor = 1.15
        elif rect_height > common.Size.RowHeight():
            size_factor = 1.0

        # Use cached fonts and metrics if available
        if not font and not metrics:
            font_key = f'bold_{size_factor}'
            if font_key in self._font_cache:
                font, metrics = self._font_cache[font_key]
            else:
                font, metrics = common.Font.BoldFont(common.Size.MediumText(size_factor))
                self._font_cache[font_key] = (font, metrics)
        elif font and metrics:
            ctx.font = font
            ctx.metrics = metrics

        # Calculate padding based on font pixel size
        font_pixel_size = font.pixelSize()
        horizontal_padding = int(font_pixel_size * 0.7)
        vertical_padding = int(font_pixel_size * 0.5)

        # Adjust font for provided rect
        if rect:
            font, _ = common.Font.LightFont(font_pixel_size)
            ctx.font = font

        # Prepare and elide the text
        text = ctx.index.data(role) or default_text
        max_text_width = ctx.option.rect.width() - (horizontal_padding * 2)
        text = metrics.elidedText(text, QtCore.Qt.ElideRight, max_text_width)

        # Split text into segments and strip whitespace
        text_segments = text.replace('\\', '/').split('/')
        text_segments = [segment.strip() for segment in text_segments if segment.strip()]

        # Calculate widths of each text segment and total width
        segment_widths = []
        total_text_width = 0
        for segment in text_segments:
            width = metrics.horizontalAdvance(segment)
            segment_widths.append(width)
            total_text_width += width

        # Calculate total width including padding
        num_segments = len(text_segments)
        width = total_text_width + (horizontal_padding * 2 * num_segments)

        # Adjust width to fit within the available space
        max_width = ctx.option.rect.width() - (horizontal_padding * 2)
        if width > max_width:
            width = max_width

        if rect:
            available_width = abs(rect.right() - ctx.option.rect.right()) - (horizontal_padding * 1.5)
            if width > available_width:
                width = available_width

        # Determine the starting x position based on alignment
        if align_right:
            x = ctx.option.rect.right() - width
            x = x if (x - horizontal_padding) > rect.right() else rect.right() + horizontal_padding
        else:
            x = ctx.x + (horizontal_padding * 2)

        # Create the background rectangle for the text
        y = ctx.y
        text_bg_rect = QtCore.QRectF(
            x - horizontal_padding,
            y - metrics.ascent(),
            width,
            metrics.height()
        )
        text_bg_rect.adjust(0, -vertical_padding, 0, vertical_padding)

        # Adjust the background rectangle based on stretching and alignment
        if stretch and not align_right:
            text_bg_rect.setRight(ctx.option.rect.right() - horizontal_padding)
        elif stretch and align_right:
            text_bg_rect.setLeft(rect.right() + common.Size.Separator(4.0))
            text_bg_rect.setRight(ctx.option.rect.right() - (horizontal_padding * 2.0))

        if align_right and text_bg_rect.width() < horizontal_padding * 2.0:
            return text_bg_rect

        # Set clipping path to the text background rectangle
        painter_path = QtGui.QPainterPath()
        painter_path.setFillRule(QtCore.Qt.WindingFill)
        painter_path.addRoundedRect(
            text_bg_rect,
            common.Size.Indicator(1.5),
            common.Size.Indicator(1.5)
        )
        ctx.painter.setClipPath(painter_path)

        # Draw the background
        ctx.painter.save()
        if draw_outline:
            background_color = common.Color.VeryDarkBackground().lighter(140)
            pen_color = common.Color.VeryDarkBackground().darker(130)
            ctx.painter.setBrush(background_color)
            ctx.painter.setPen(pen_color)
        else:
            ctx.painter.setBrush(QtCore.Qt.NoBrush)
            ctx.painter.setPen(QtCore.Qt.NoPen)
        ctx.painter.drawPath(painter_path.simplified())
        ctx.painter.restore()

        # Set the initial text color
        text_color = common.Color.Text()
        if ctx.selected or ctx.hover:
            text_color = common.Color.SelectedText()
        _text_color = text_color.darker(130)

        if not accent_first:
            text_color = text_color.darker(115)
            _text_color = text_color

        if draw_outline:
            pen = QtGui.QPen(common.Color.VeryDarkBackground())
            pen.setWidthF(common.Size.Separator())

        # Get keyboard modifiers
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        shift = modifiers & QtCore.Qt.ShiftModifier
        alt = modifiers & QtCore.Qt.AltModifier

        # Pre-calculate x positions for each text segment
        x_positions = []
        current_x = x
        for segment_width in segment_widths:
            x_positions.append(current_x)
            current_x += segment_width + (horizontal_padding * 2)

        # Reuse text bounding rectangle
        text_bounding_rect = QtCore.QRectF()

        # Loop over text segments and render them
        for n, (segment_text, segment_width, x_pos) in enumerate(zip(text_segments, segment_widths, x_positions)):
            # Update text color for non-leading segments
            if n > 0:
                text_color = _text_color

            # Set up the text bounding rectangle
            text_bounding_rect.setRect(
                x_pos - horizontal_padding,
                y - metrics.ascent() - vertical_padding,
                segment_width + (horizontal_padding * 2),
                metrics.height() + (vertical_padding * 2)
            )

            # Add the rectangle to the filter for interaction
            if n < 1024:
                self.add_filter_rectangle(
                    ctx.index.data(common.IdRole),
                    n + clickable_id_offset,
                    text_bounding_rect.toRect(),
                    segment_text
                )

            # Adjust the segment text if it exceeds the available space
            segment_max_width = text_bg_rect.right() - x_pos - horizontal_padding
            if not align_right and text_bounding_rect.right() > text_bg_rect.right():
                segment_text = metrics.elidedText(segment_text, QtCore.Qt.ElideRight, segment_max_width)
                segment_width = metrics.horizontalAdvance(segment_text)
                text_bounding_rect.setWidth(segment_width + (horizontal_padding * 2))

            if align_right and text_bounding_rect.right() > ctx.option.rect.right():
                segment_max_width = ctx.option.rect.right() - x_pos - horizontal_padding
                segment_text = metrics.elidedText(segment_text, QtCore.Qt.ElideRight, segment_max_width)
                segment_width = metrics.horizontalAdvance(segment_text)
                text_bounding_rect.setWidth(segment_width + (horizontal_padding * 2))

            # Stretch the last segment if needed
            if not align_right and n == num_segments - 1 and stretch:
                text_bounding_rect.setRight(ctx.option.rect.right())

            # Stretch the first segment if aligned right
            if align_right and n == 0 and stretch:
                text_bounding_rect.setLeft(rect.right())

            # Fill the background for the leading item to give prominence
            if n == 0 and accent_first:
                ctx.painter.fillRect(text_bounding_rect, common.Color.Opaque())

            # Check if the text segment matches the filter criteria
            if self.parent().model().filter.has_string(f'"{segment_text}"', positive_terms=True):
                text_color = common.Color.Green()
                font.setUnderline(True)
            else:
                font.setUnderline(False)

            # Set font and pen for drawing text
            ctx.painter.setFont(font)
            ctx.painter.setPen(text_color)

            # Draw the text
            ctx.painter.drawText(
                x_pos,
                y,
                segment_text
            )

            # Draw separator and filter intent indicator
            ctx.painter.save()

            if text_bounding_rect.toRect() == self.filter_candidate_rectangle:
                color = common.Color.Text()
                color = common.Color.Green() if shift else color
                color = common.Color.Red() if alt else color
                alpha = 30 if no_modifier else 80
                color.setAlpha(alpha)
                ctx.painter.setBrush(color)
                ctx.painter.setPen(QtCore.Qt.NoPen)
            else:
                ctx.painter.setBrush(QtCore.Qt.NoBrush)
                if draw_outline:
                    ctx.painter.setPen(pen)
                else:
                    ctx.painter.setPen(QtCore.Qt.NoPen)

            ctx.painter.drawRect(text_bounding_rect)
            ctx.painter.restore()

        return text_bg_rect

    @save_painter
    def paint_outlines(self, ctx):
        """Paints the background for all list items."""

        def _draw_outline(ctx, color):
            ctx.painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

            painter_path = QtGui.QPainterPath()
            painter_path.setFillRule(QtCore.Qt.WindingFill)

            r = QtCore.QRect(ctx.option.rect).adjusted(common.Size.Separator(), common.Size.Separator(),
                                                       -common.Size.Separator(), -common.Size.Separator())

            if ctx.index.column() == 0:
                pass
            elif ctx.index.column() == 1:

                r_left = QtCore.QRect(r)
                r_left.setRight(r.center().x())

                r_right = QtCore.QRect(r)
                r_right.setLeft(ctx.option.rect.center().x() - common.Size.Indicator(1.5))
                r_right.setRight(r.right() + common.Size.Indicator(1.5))

                painter_path.addRoundedRect(
                    r_left, common.Size.Indicator(1.5), common.Size.Indicator(1.5),
                )
                painter_path.addRect(r_right)

            elif ctx.index.column() == 2 and not ctx.buttons_hidden:
                _r = QtCore.QRect(r)
                _r.setLeft(r.left() - common.Size.Indicator(1.5))
                _r.setRight(r.right() + common.Size.Indicator(1.5))
                painter_path.addRoundedRect(
                    _r, common.Size.Indicator(1.5), common.Size.Indicator(1.5),
                )
            elif ctx.index.column() == 2 and ctx.buttons_hidden:
                r_left = QtCore.QRect(r)
                r_left.setRight(r.center().x())
                r_left.setLeft(r.left() - common.Size.Indicator(1.5))

                r_right = QtCore.QRect(r)
                r_right.setLeft(ctx.option.rect.center().x() - common.Size.Indicator(1.5))
                r_right.setRight(r.right())

                painter_path.addRoundedRect(
                    r_right, common.Size.Indicator(1.5), common.Size.Indicator(1.5),
                )
                painter_path.addRect(r_left)
            elif ctx.index.column() == 3:
                r_right = QtCore.QRect(r)
                r_right.setLeft(r.center().x())

                r_left = QtCore.QRect(r)
                r_left.setRight(ctx.option.rect.center().x() + common.Size.Indicator(1.5))
                r_left.setLeft(r.left() - common.Size.Indicator(1.5))

                painter_path.addRoundedRect(
                    r_right, common.Size.Indicator(1.5), common.Size.Indicator(1.5),
                )
                painter_path.addRect(r_left)

            clip_path = QtGui.QPainterPath()
            clip_path.addRect(ctx.option.rect)
            ctx.painter.setClipPath(clip_path)

            ctx.painter.setBrush(QtCore.Qt.NoBrush)
            pen = QtGui.QPen(color)
            pen.setWidthF(common.Size.Separator(2.0))
            ctx.painter.setPen(pen)
            ctx.painter.drawPath(painter_path.simplified())

            if ctx.index.column() == 1:
                return

            ctx.painter.setPen(QtCore.Qt.NoPen)
            ctx.painter.setBrush(color)
            ctx.painter.setOpacity(0.22)
            ctx.painter.drawPath(painter_path.simplified())

        if ctx.index.flags() == QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return

        # Active indicator
        if ctx.active:
            _draw_outline(ctx, common.Color.Green())

        if ctx.selected:
            _draw_outline(ctx, common.Color.Blue())

    @save_painter
    def paint_thumbnail(self, ctx):
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
        if not ctx.index.isValid():
            return

        if ctx.index.column() != 1:
            return

        if not ctx.index.data(common.ParentPathRole):
            return

        pp = ctx.index.data(common.ParentPathRole)
        if not pp:
            return

        server, job, root = pp[0:3]
        source = ctx.index.data(common.PathRole)
        if not source:
            return
        size_role = ctx.index.data(QtCore.Qt.SizeHintRole)
        if not size_role:
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

        ctx.painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, on=True)
        ctx.painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        mask_path = QtGui.QPainterPath()
        mask_path.addRoundedRect(
            ctx.option.rect.adjusted(common.Size.Separator(2.0), common.Size.Separator(2.0),
                                     -common.Size.Separator(2.0), -common.Size.Separator(2.0)),
            common.Size.Indicator(1.5), common.Size.Indicator(1.5))
        ctx.painter.setClipPath(mask_path.simplified())

        # Background
        if not common.settings.value('settings/paint_thumbnail_bg'):

            if color:
                ctx.painter.setOpacity(0.5)
            color = color if color else QtGui.QColor(0, 0, 0, 50)
            ctx.painter.setBrush(color)
            if ctx.archived:
                ctx.painter.setOpacity(0.1)
            ctx.painter.drawRect(ctx.option.rect)

        o = 0.8 if ctx.selected or ctx.active or ctx.hover else 0.65
        ctx.painter.setOpacity(o)

        if not pixmap:
            return

        # Let's make sure the image is fully fitted, even if the image's size
        # doesn't match ThumbnailRect
        s = float(ctx.option.rect.height())
        longest_edge = float(max((pixmap.width(), pixmap.height())))
        ratio = s / longest_edge
        w = pixmap.width() * ratio
        h = pixmap.height() * ratio
        r = QtCore.QRect(0, 0, int(w), int(h))

        r.moveCenter(ctx.option.rect.center())
        if ctx.archived:
            ctx.painter.setOpacity(0.1)
        ctx.painter.drawPixmap(r, pixmap, pixmap.rect())


class BookmarkItemViewDelegate(ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.bookmark_items.BookmarkItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'icon_bw_sm'

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
        # if self.switcher_visible():
        #     painter.fillRect(option.rect, common.Color.VeryDarkBackground())
        #     return
        if not common.main_widget:
            return
        if common.main_widget.stacked_widget.animation_in_progress:
            return

        ctx = self.get_paint_context(painter, option, index)
        self.paint_indicator(ctx)
        self.paint_background(ctx)
        self.paint_shadows(ctx)
        self.paint_outlines(ctx)

        rect = self.paint_clickable_filter_segments(
            ctx, role=QtCore.Qt.DisplayRole, stretch=False)

        rect = self.paint_clickable_filter_segments(
            ctx,
            rect=rect,
            role=common.DescriptionRole,
            stretch=False,
            draw_outline=False,
            opacity=1.0,
            accent_first=False,
            align_right=True,
            clickable_id_offset=1024
        )

        #     self.paint_archived(ctx)
        #     self.paint_inline_background(ctx)
        #     self.paint_inline_icons(ctx)
        self.paint_thumbnail(ctx)
    #     self.paint_thumbnail_drop_indicator(ctx)
    #     self.paint_description_editor_background(ctx)
    #     self.paint_selection_indicator(ctx)
    #     self.paint_sg_status(ctx)
    #     self.paint_db_status(ctx)
    #     self.paint_drag_source(ctx)
    #     self.paint_deleted(ctx)


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
        # if self.switcher_visible():
        #     painter.fillRect(option.rect, common.Color.VeryDarkBackground())
        #     return
        #
        # if index.column() == 0:
        #     if index.data(QtCore.Qt.DisplayRole) is None:
        #         return  # The index might still be populated...
        #     ctx = self.get_paint_context(painter, option, index)
        #     self.paint_background(ctx)
        #     self.paint_outlines(ctx)
        #     self.paint_hover(ctx)
        #     self.paint_shadows(ctx)
        #     self.paint_clickable_filter_segments(ctx)
        #
        #     if common.main_widget.stacked_widget.animation_in_progress:
        #         return
        #
        #     self.paint_archived(ctx)
        #     self.paint_description_editor_background(ctx)
        #     self.paint_inline_background(ctx)
        #     self.paint_inline_icons(ctx)
        #     self.paint_thumbnail(ctx)
        #     self.paint_thumbnail_drop_indicator(ctx)
        #     self.paint_selection_indicator(ctx)
        #     self.paint_sg_status(ctx)
        #     self.paint_db_status(ctx)
        #     self.paint_dcc_icon(ctx)
        #     self.paint_drag_source(ctx)
        #     self.paint_deleted(ctx)


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
        # if self.switcher_visible():
        #     painter.fillRect(option.rect, common.Color.VeryDarkBackground())
        #     return
        #
        # if index.column() == 0:
        #     ctx = self.get_paint_context(painter, option, index)
        #     if not index.data(QtCore.Qt.DisplayRole):
        #         return
        #
        #     p_role = index.data(common.ParentPathRole)
        #     if p_role:
        #         self.paint_background(ctx)
        #         self.paint_outlines(ctx)
        #         self.paint_hover(ctx)
        #         self.paint_clickable_filter_segments(ctx)
        #
        #     if common.main_widget.stacked_widget.animation_in_progress:
        #         return
        #
        #     self.paint_shadows(ctx)
        #
        #     self.paint_archived(ctx)
        #     self.paint_inline_background(ctx)
        #     self.paint_inline_icons(ctx)
        #     self.paint_selection_indicator(ctx)
        #     self.paint_thumbnail(ctx)
        #     self.paint_thumbnail_drop_indicator(ctx)
        #     self.paint_description_editor_background(ctx)
        #     self.paint_drag_source(ctx)
        #     self.paint_deleted(ctx)
        #     self.paint_db_status(ctx)


class FavouriteItemViewDelegate(FileItemViewDelegate):
    """The delegate used to render
    :class:`bookmarks.items.favourite_items.FavouriteItemView` items.

    """
    fallback_thumb = 'favourite_item'
