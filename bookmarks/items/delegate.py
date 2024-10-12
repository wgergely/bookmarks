"""Item delegate used to by the item views to display and edit items.

"""
import copy
import functools
from dataclasses import dataclass

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common, images, progress
from .. import database
from .. import ui

HOVER_COLOR = QtGui.QColor(255, 255, 255, 10)


@dataclass
class PaintContext:
    painter: QtGui.QPainter
    index: QtCore.QModelIndex
    option: QtWidgets.QStyleOptionViewItem
    rect: QtCore.QRect
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
    buttons_hidden: bool
    link_selected: bool = False


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

        self._filter_rectangles = {}
        self._button_rectangles = {}

        self._filter_candidate_rectangle = None
        self._button_candidate_rectangle = None

        self._indicator_link = None

    @QtCore.Slot(str)
    def set_indicator_link(self, link):
        self._indicator_link = link

    @QtCore.Slot()
    def clear_rectangles(self, *args, **kwargs):
        self.clear_filter_candidate_rectangle()
        self.clear_button_candidate_rectangle()
        self.clear_filter_rectangles()
        self.clear_button_rectangles()

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
        if not common.main_widget:
            return None
        if common.main_widget.stacked_widget.animation_in_progress:
            return None

        ctx = self.get_paint_context(painter, option, index)

        self.paint_background(ctx)
        self.paint_indicator(ctx)

        self.paint_thumbnail(ctx)
        self.paint_outlines(ctx)

        rect = self.paint_clickable_filter_segments(
            ctx, role=QtCore.Qt.DisplayRole, stretch=False)

        self.paint_clickable_filter_segments(
            ctx,
            rect=rect,
            role=common.DescriptionRole,
            stretch=False,
            draw_outline=False,
            opacity=1.0,
            accent_first=False,
            align_right=True,
            draw_background=False,
            clickable_id_offset=1024
        )

        self.paint_buttons(ctx)

        self.paint_db_status(ctx)
        self.paint_deleted(ctx)

        self.paint_drag_items(ctx)

        return ctx

    def sizeHint(self, option, index):
        return QtCore.QSize(index.data(QtCore.Qt.SizeHintRole))

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

    @property
    def filter_candidate_rectangle(self):
        return self._filter_candidate_rectangle

    @QtCore.Slot(QtCore.QRect)
    def set_filter_candidate_rectangle(self, rect):
        self._filter_candidate_rectangle = rect

    @QtCore.Slot()
    def clear_filter_candidate_rectangle(self):
        self._filter_candidate_rectangle = None

    @property
    def button_candidate_rectangle(self):
        return self._button_candidate_rectangle

    @QtCore.Slot(QtCore.QRect)
    def set_button_candidate_rectangle(self, rect):
        self._button_candidate_rectangle = rect

    @QtCore.Slot()
    def clear_button_candidate_rectangle(self):
        self._button_candidate_rectangle = None

    def button_rectangles(self):
        return self._button_rectangles

    def add_button_rectangle(self, row, idx, rect):
        if row not in self._button_rectangles:
            self._button_rectangles[row] = {}
        self._button_rectangles[row][idx] = rect

    def clear_button_rectangles(self):
        self._button_rectangles = {}

    def get_button_rectangle(self, row, pos):
        if row not in self._button_rectangles:
            return None, None
        for idx in self._button_rectangles[row]:
            if self._button_rectangles[row][idx].contains(pos):
                return self._button_rectangles[row][idx], idx
        return None, None

    def get_paint_context(self, painter, option, index, antialiasing=False):
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

        if option.rect.height() < common.Size.RowHeight(1.5):
            font, metrics = common.Font.MediumFont(common.Size.SmallText())
        else:
            font, metrics = common.Font.BoldFont(common.Size.MediumText())
        painter.setFont(font)

        separator_height = int(common.Size.Separator(option.rect.height() / common.Size.RowHeight(1.0)))
        rect = option.rect.adjusted(0, 0, 0, -separator_height)
        x = rect.left()
        y = rect.center().y() + metrics.ascent() / 2.0 - (metrics.descent() / 4.0)

        try:
            link_selected = index.data(common.AssetLinkRole) == self._indicator_link
        except (AttributeError, KeyError):
            link_selected = None

        ctx = PaintContext(
            painter=painter,
            index=index,
            option=option,
            rect=rect,
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
            buttons_hidden=self.parent().buttons_hidden(),
            link_selected=link_selected,
        )
        return ctx

    @save_painter
    def paint_indicator(self, ctx):
        if not ctx.index.isValid():
            return

        if not ctx.index.data(common.ParentPathRole):
            return
        if len(ctx.index.data(common.ParentPathRole)) != 4:
            return

        if not ctx.index.data(common.AssetLinkRole):
            return
        if not ctx.link_selected:
            return

        if ctx.index.column() != 0:
            return

        rgba = common.color_manager.get_color(ctx.index.data(common.AssetLinkRole))
        color = QtGui.QColor(*rgba)
        rect = QtCore.QRect(ctx.rect)
        rect.setBottom(ctx.option.rect.bottom())

        rect.setRight(rect.left() + common.Size.Separator(1.0))
        ctx.painter.fillRect(rect, color)

    @save_painter
    def paint_background(self, ctx):
        """Paints the background for all list items."""
        if not ctx.index.isValid():
            return

        if ctx.index.flags() == QtCore.Qt.NoItemFlags:
            return
        if ctx.index.flags() & common.MarkedAsArchived:
            return

        ctx.painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        if ctx.index.column() == 0:
            return

        if ctx.index.column() == 1:
            color = common.Color.VeryDarkBackground().darker(120)
            color = color.lighter(105) if ctx.hover else color
            ctx.painter.setBrush(color)
            ctx.painter.drawRoundedRect(ctx.rect, common.Size.Indicator(1.5), common.Size.Indicator(1.5))
        elif ctx.index.column() == 2:
            color = common.Color.DarkBackground()
            color = common.Color.LightBackground() if ctx.selected else color
            color = color.lighter(105) if ctx.hover else color

            if not ctx.buttons_hidden:
                r = QtCore.QRect(ctx.rect)
                r.setLeft(r.center().x())
                ctx.painter.fillRect(r, color)

            ctx.painter.setBrush(color)
            r = QtCore.QRect(ctx.rect)
            r.setLeft(r.left() + common.Size.Separator(2.0))
            if not ctx.buttons_hidden:
                r.setRight(r.center().x() + common.Size.Indicator(1.5))
            ctx.painter.drawRoundedRect(r, common.Size.Indicator(1.5), common.Size.Indicator(1.5))
        elif ctx.index.column() == 3:
            color = common.Color.DarkBackground()
            color = common.Color.LightBackground() if ctx.selected else color
            color = color.lighter(105) if ctx.hover else color

            r = QtCore.QRect(ctx.rect)
            r.setRight(r.center().x())
            ctx.painter.fillRect(r, color)

            ctx.painter.setBrush(color)
            r = QtCore.QRect(ctx.rect)
            r.setLeft(r.center().x() - common.Size.Indicator(1.5))
            ctx.painter.drawRoundedRect(r, common.Size.Indicator(1.5), common.Size.Indicator(1.5))

    @save_painter
    def paint_clickable_filter_segments(
            self, ctx,
            rect=None,
            stretch=True,
            role=QtCore.Qt.DisplayRole,
            default_text='',
            draw_background=True,
            draw_outline=True,
            opacity=1.0,
            accent_first=True,
            align_right=False,
            clickable_id_offset=0
    ):
        """Paints name of the `AssetWidget`'s items with performance optimizations and requested features."""

        if ctx.index.flags() & common.MarkedAsArchived:
            opacity *= 0.5

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

        # Determine font size factor based on the height of the rect
        rect_height = ctx.rect.height()
        size_factor = 0.9  # default size factor

        if rect_height <= common.Size.RowHeight():
            size_factor = 0.8
        elif rect_height > common.Size.RowHeight(8.0):
            size_factor = 1.2
        elif rect_height > common.Size.RowHeight(4.0):
            size_factor = 1.1
        elif rect_height > common.Size.RowHeight():
            size_factor = 0.9

        # Use cached fonts and metrics if available
        font, metrics = common.Font.BoldFont(common.Size.MediumText(size_factor))
        ctx.font = font
        ctx.metrics = metrics

        # Calculate padding based on font pixel size
        font_pixel_size = font.pixelSize()
        horizontal_padding = int(font_pixel_size * 1.3)
        vertical_padding = int(horizontal_padding * 0.5)

        # Adjust font for provided rect
        if rect:
            font, _ = common.Font.LightFont(font_pixel_size)
            ctx.font = font

        # Prepare and elide the text
        text = ctx.index.data(role) or default_text
        max_text_width = ctx.rect.width() - (horizontal_padding * 2)
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
        max_width = ctx.rect.width() - (horizontal_padding * 2)
        if width > max_width:
            width = max_width

        if rect:
            available_width = abs(rect.right() - ctx.rect.right()) - (horizontal_padding * 1.5)
            if width > available_width:
                width = available_width

        # Determine the starting x position based on alignment
        if align_right:
            x = ctx.rect.right() - width
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
            text_bg_rect.setRight(ctx.rect.right() - horizontal_padding)
        elif stretch and align_right:
            text_bg_rect.setLeft(rect.right() + common.Size.Separator(4.0))
            text_bg_rect.setRight(ctx.rect.right() - (horizontal_padding * 2.0))

        if align_right and text_bg_rect.width() < horizontal_padding * 2.0:
            return text_bg_rect

        # Set clipping path to the text background rectangle
        painter_path = QtGui.QPainterPath()
        painter_path.setFillRule(QtCore.Qt.WindingFill)
        _o = common.Size.Separator(1.0)
        painter_path.addRoundedRect(
            text_bg_rect.adjusted(-_o, -_o, _o, _o),
            common.Size.Indicator(1.5),
            common.Size.Indicator(1.5)
        )
        ctx.painter.setClipPath(painter_path)

        ctx.painter.setBrush(QtCore.Qt.NoBrush)
        ctx.painter.setPen(QtCore.Qt.NoPen)

        # Draw the background
        if draw_background:
            ctx.painter.save()
            ctx.painter.setOpacity(0.5)
            ctx.painter.setBrush(common.Color.Opaque())
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

            # Draw a gradient from the left edge to left + margin
            if n == 1 and accent_first:
                ctx.painter.save()
                gradient = QtGui.QLinearGradient(
                    text_bounding_rect.topLeft(),
                    text_bounding_rect.topLeft() + QtCore.QPoint(common.Size.Margin(2.0), 0)
                )
                gradient.setColorAt(0.0, common.Color.Opaque())
                gradient.setColorAt(1.0, common.Color.Transparent())
                ctx.painter.setBrush(gradient)
                ctx.painter.setPen(QtCore.Qt.NoPen)
                ctx.painter.drawRect(text_bounding_rect)
                ctx.painter.restore()

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

            if align_right and text_bounding_rect.right() > ctx.rect.right():
                segment_max_width = ctx.rect.right() - x_pos - horizontal_padding
                segment_text = metrics.elidedText(segment_text, QtCore.Qt.ElideRight, segment_max_width)
                segment_width = metrics.horizontalAdvance(segment_text)
                text_bounding_rect.setWidth(segment_width + (horizontal_padding * 2))

            # Stretch the last segment if needed
            if not align_right and n == num_segments - 1 and stretch:
                text_bounding_rect.setRight(ctx.rect.right())

            # Stretch the first segment if aligned right
            if align_right and n == 0 and stretch:
                text_bounding_rect.setLeft(rect.right())

            # Fill the background for the leading item to give prominence
            if n == 0 and accent_first:
                ctx.painter.fillRect(text_bounding_rect, common.Color.DarkBackground().lighter(120))

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

            # Hover state
            if text_bounding_rect.toRect() == self.filter_candidate_rectangle:
                ctx.painter.save()

                color = common.Color.Text()
                color = common.Color.Green() if shift else color
                color = common.Color.Red() if alt else color
                alpha = 30 if no_modifier else 80
                color.setAlpha(alpha)

                ctx.painter.setBrush(color)
                ctx.painter.setPen(QtCore.Qt.NoPen)
                ctx.painter.drawRect(text_bounding_rect)

                ctx.painter.restore()
            elif draw_outline and n < num_segments - 1:
                # Draw separator line between segments
                _rect = text_bounding_rect.adjusted(
                    text_bounding_rect.width() - common.Size.Separator(2.0), 0, 0, 0)
                ctx.painter.fillRect(_rect, common.Color.VeryDarkBackground())

            ctx.painter.restore()

        # Draw outline
        if draw_outline and ctx.selected:
            ctx.painter.save()
            ctx.painter.setOpacity(1.0)
            pen = QtGui.QPen(common.Color.Opaque())
            pen.setWidthF(common.Size.Separator(4.0))
            ctx.painter.setPen(pen)
            ctx.painter.setBrush(QtCore.Qt.NoBrush)
            ctx.painter.drawPath(painter_path.simplified())
            ctx.painter.restore()

        return text_bg_rect

    @save_painter
    def paint_outlines(self, ctx):
        """Paints the background for all list items."""

        def _draw_outline(ctx, color):
            ctx.painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

            painter_path = QtGui.QPainterPath()
            painter_path.setFillRule(QtCore.Qt.WindingFill)

            r = QtCore.QRect(ctx.rect).adjusted(common.Size.Separator(), common.Size.Separator(),
                                                -common.Size.Separator(), -common.Size.Separator())

            if ctx.index.column() == 0:
                pass
            elif ctx.index.column() == 1:

                r_left = QtCore.QRect(r)
                r_left.setRight(r.center().x())

                r_right = QtCore.QRect(r)
                r_right.setLeft(ctx.rect.center().x() - common.Size.Indicator(1.5))
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
                r_right.setLeft(ctx.rect.center().x() - common.Size.Indicator(1.5))
                r_right.setRight(r.right())

                painter_path.addRoundedRect(
                    r_right, common.Size.Indicator(1.5), common.Size.Indicator(1.5),
                )
                painter_path.addRect(r_left)
            elif ctx.index.column() == 3:
                r_right = QtCore.QRect(r)
                r_right.setLeft(r.center().x())

                r_left = QtCore.QRect(r)
                r_left.setRight(ctx.rect.center().x() + common.Size.Indicator(1.5))
                r_left.setLeft(r.left() - common.Size.Indicator(1.5))

                painter_path.addRoundedRect(
                    r_right, common.Size.Indicator(1.5), common.Size.Indicator(1.5),
                )
                painter_path.addRect(r_left)

            clip_path = QtGui.QPainterPath()
            clip_path.addRect(ctx.rect)
            ctx.painter.setClipPath(clip_path.simplified())

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

        if ctx.index.flags() == QtCore.Qt.NoItemFlags:
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
            ctx.rect,
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
            ctx.painter.drawRect(ctx.rect)

        o = 0.8 if ctx.selected or ctx.active or ctx.hover else 0.65
        ctx.painter.setOpacity(o)

        if not pixmap:
            return

        # Let's make sure the image is fully fitted, even if the image's size
        # doesn't match ThumbnailRect
        s = float(ctx.rect.height())
        longest_edge = float(max((pixmap.width(), pixmap.height())))
        ratio = s / longest_edge
        w = pixmap.width() * ratio
        h = pixmap.height() * ratio
        r = QtCore.QRect(0, 0, int(w), int(h))

        r.moveCenter(ctx.rect.center())
        if ctx.archived:
            ctx.painter.setOpacity(0.1)
        ctx.painter.drawPixmap(r, pixmap, pixmap.rect())

    @save_painter
    def paint_buttons(self, ctx):
        if not ctx.index.isValid():
            return
        if ctx.index.column() != 3:
            return
        if ctx.index.flags() == QtCore.Qt.NoItemFlags:
            return

        icon_size = common.Size.Margin(1.0)
        padding = common.Size.Indicator(1.0)

        icon_area_rect = QtCore.QRect(ctx.rect)
        icon_area_rect.setHeight(icon_size + (padding * 2))
        icon_area_rect = icon_area_rect.adjusted(
            padding, 0, -padding, 0)

        icon_area_rect.moveCenter(ctx.rect.center())

        ctx.painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        ctx.painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, on=True)

        if ctx.hover or ctx.selected:
            ctx.painter.setBrush(common.Color.DarkBackground().lighter(150))
        else:
            ctx.painter.setBrush(common.Color.DarkBackground())
        ctx.painter.setPen(QtCore.Qt.NoPen)

        ctx.painter.drawRoundedRect(
            icon_area_rect,
            common.Size.Indicator(1.5),
            common.Size.Indicator(1.5)
        )

        clip_path = QtGui.QPainterPath()
        clip_path.addRoundedRect(
            icon_area_rect,
            common.Size.Indicator(1.5),
            common.Size.Indicator(1.5)
        )
        ctx.painter.setClipPath(clip_path.simplified())

        icons = self.parent().icons

        button_width = float((icon_area_rect.width() - padding) / float(len(icons)))

        icon_button_rect = QtCore.QRect(icon_area_rect)
        icon_button_rect.setWidth(button_width)
        center = icon_button_rect.center()
        icon_button_rect.moveTopLeft(icon_area_rect.topLeft())
        icon_button_rect.moveLeft(icon_button_rect.left() + (padding * 0.5))

        icon_button_rect.setHeight(common.Size.Margin(0.9))
        icon_button_rect.moveCenter(center)

        values = icons.values()
        last_idx = len(values) - 1

        state = QtGui.QIcon.State.Off
        mode = QtGui.QIcon.Mode.Normal

        for idx, v in enumerate(icons.values()):
            if ctx.archived and idx != last_idx:
                self.add_button_rectangle(ctx.index.data(common.IdRole), idx, QtCore.QRect(icon_button_rect))
                icon_button_rect.moveLeft(icon_button_rect.left() + button_width)
                continue

            if icon_button_rect == self.button_candidate_rectangle:
                color = common.Color.Text()
            else:
                color = common.Color.VeryDarkBackground()

            if v['icon']:
                if v['icon'] == 'favourite' and ctx.index.flags() & common.MarkedAsFavourite:
                    state = QtGui.QIcon.State.On
                    mode = QtGui.QIcon.Mode.Active
                    icon = ui.get_icon(v['icon'])
                elif v['icon'] == 'archivedHidden' and ctx.index.flags() & common.MarkedAsArchived:
                    state = QtGui.QIcon.State.On
                    mode = QtGui.QIcon.Mode.Active
                    icon = ui.get_icon('archivedVisible')
                else:
                    icon = ui.get_icon(v['icon'], color=color)

                icon.paint(
                    ctx.painter,
                    icon_button_rect,
                    alignment=QtCore.Qt.AlignCenter,
                    mode=mode,
                    state=state
                )
            else:
                self.paint_custom_item_icon(ctx, icon_button_rect)
            self.add_button_rectangle(ctx.index.data(common.IdRole), idx, QtCore.QRect(icon_button_rect))
            icon_button_rect.moveLeft(icon_button_rect.left() + button_width)

    @save_painter
    def paint_custom_item_icon(self, ctx, rect):
        """Paints a custom icon for an item.

        """
        if not ctx.index.isValid():
            return
        if not ctx.index.data(QtCore.Qt.DisplayRole):
            return
        if not ctx.index.data(common.ParentPathRole):
            return

        rect = QtCore.QRect(rect)
        center = rect.center()
        rect.setWidth(rect.height())
        rect.moveCenter(center)

        # Draw background
        ctx.painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        ctx.painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, on=True)

        ctx.painter.setBrush(common.Color.Opaque())
        ctx.painter.setPen(QtCore.Qt.NoPen)

        if len(ctx.index.data(common.ParentPathRole)) == 3:
            ctx.painter.drawEllipse(rect)
            if ctx.index.data(common.SGLinkedRole):
                icon = QtGui.QIcon()
                pixmap = images.rsc_pixmap(
                    'sg', common.Color.Text(), common.Size.Margin()
                )
                icon.addPixmap(pixmap)
                icon.paint(ctx.painter, rect, alignment=QtCore.Qt.AlignCenter)
            else:
                icon = QtGui.QIcon()
                pixmap = images.rsc_pixmap(
                    'sg', common.Color.Background(), common.Size.Margin(0.8)
                )
                icon.addPixmap(pixmap)
                icon.paint(ctx.painter, rect, alignment=QtCore.Qt.AlignCenter)

            try:
                if ctx.index.data(common.AssetCountRole):
                    ctx.painter.setClipping(False)
                    font, metrics = common.Font.LightFont(common.Size.SmallText(0.8))
                    center = rect.bottomRight()

                    h = metrics.lineSpacing() + common.Size.Separator(4.0)
                    rect.setSize(
                        QtCore.QSize(h, h)
                    )
                    rect.moveCenter(center)

                    o = common.Size.Separator(1.0)
                    rect = rect.adjusted(o, o, -o, -o)
                    ctx.painter.setBrush(common.Color.Blue())
                    ctx.painter.setPen(common.Color.Opaque())
                    ctx.painter.drawEllipse(rect)
                    ctx.painter.setPen(common.Color.Text())

                    text = f'{ctx.index.data(common.AssetCountRole)}'

                    ctx.painter.drawText(
                        rect,
                        QtCore.Qt.AlignCenter,
                        text,
                        boundingRect=rect
                    )
            except:
                pass

        if len(ctx.index.data(common.ParentPathRole)) == 4 and ctx.index.data(common.AssetLinkRole):
            # ctx.painter.drawEllipse(rect)

            icon = QtGui.QIcon()
            pixmap = images.rsc_pixmap(
                'link', common.Color.SecondaryText(), common.Size.Margin(0.7)
            )
            icon.addPixmap(pixmap)
            icon.paint(ctx.painter, rect, alignment=QtCore.Qt.AlignCenter)
        # Paint

    @save_painter
    def paint_db_status(self, ctx):
        """Paints the item's configuration status.

        """

        if not ctx.index.isValid():
            return

        if ctx.index.column() != 2:
            return

        if not ctx.index.data(QtCore.Qt.DisplayRole):
            return

        if not ctx.index.data(common.ParentPathRole):
            return

        db = database.get(*ctx.index.data(common.ParentPathRole)[0:3])
        if db.is_valid():
            return

        rect = QtCore.QRect(
            0, 0, common.Size.Margin(), common.Size.Margin()
        )
        rect.moveCenter(ctx.rect.center())

        ctx.painter.setOpacity(1.0) if ctx.hover else ctx.painter.setOpacity(0.9)

        pixmap = images.rsc_pixmap(
            'alert', common.Color.Red(), common.Size.Margin()
        )
        ctx.painter.drawPixmap(rect, pixmap, pixmap.rect())
        ctx.painter.setBrush(common.Color.Red())
        ctx.painter.setPen(QtCore.Qt.NoPen)
        ctx.painter.setOpacity(0.1)
        ctx.painter.drawRect(ctx.rect)

    @save_painter
    def paint_deleted(self, ctx):
        """Paints a deleted item.

        """
        if ctx.index.flags() != QtCore.Qt.NoItemFlags | common.MarkedAsArchived:
            return

        rect = QtCore.QRect(ctx.rect)
        rect.setHeight(common.Size.Separator(2.0))
        rect.moveCenter(ctx.rect.center())
        ctx.painter.setBrush(common.Color.VeryDarkBackground())
        ctx.painter.drawRect(rect)

    @save_painter
    def paint_drag_items(self, ctx):
        """Overlay to indicate the source of a drag operation."""
        # no drag operation
        if self.parent().drag_source_row == -1:
            return

        # Drag destination
        if (
                ctx.index.flags() & QtCore.Qt.ItemIsDropEnabled and
                self.parent().drag_source_row != ctx.index.row() and
                ctx.index.column() == 2
        ):
            ctx.painter.setOpacity(0.5)
            ctx.painter.setBrush(common.Color.VeryDarkBackground())
            ctx.painter.drawRoundedRect(ctx.rect, common.Size.Indicator(1.5), common.Size.Indicator(1.5))

            ctx.painter.setOpacity(1.0)
            ctx.painter.setBrush(QtCore.Qt.NoBrush)
            pen = QtGui.QPen(common.Color.SelectedText())
            pen.setWidthF(common.Size.Separator(2.0))
            ctx.painter.setPen(pen)
            ctx.painter.drawRect(ctx.rect)

            font, metrics = common.Font.MediumFont(
                common.Size.SmallText()
            )
            ctx.painter.setFont(font)
            text = 'Drop to paste item properties'
            ctx.painter.setPen(common.Color.Green())
            ctx.painter.drawText(
                ctx.rect.adjusted(
                    common.Size.Margin(), 0, -common.Size.Margin(), 0
                ),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter |
                QtCore.Qt.TextWordWrap,
                text,
                boundingRect=ctx.rect,
            )
            return

        if ctx.index.row() == self.parent().drag_source_row and ctx.index.column() == 2:
            ctx.painter.setBrush(common.Color.VeryDarkBackground())
            ctx.painter.drawRoundedRect(ctx.rect, common.Size.Indicator(1.5), common.Size.Indicator(1.5))

            ctx.painter.setPen(common.Color.Background())
            font, metrics = common.Font.MediumFont(
                common.Size.SmallText()
            )
            ctx.painter.setFont(font)

            text = ''
            if ctx.index.data(common.ItemTabRole) in (common.FileTab, common.FavouriteTab):
                text = '"Drag+Shift" grabs all files    |    "Drag+Alt" grabs the ' \
                       'first file    |    "Drag+Shift+Alt" grabs the parent folder'
            if ctx.index.data(common.ItemTabRole) in (common.BookmarkTab, common.AssetTab):
                text = 'Copied properties'

            ctx.painter.drawText(
                ctx.rect.adjusted(
                    common.Size.Margin(), 0, -common.Size.Margin(), 0
                ),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter |
                QtCore.Qt.TextWordWrap,
                text,
                boundingRect=ctx.rect,
            )
        else:
            ctx.painter.setOpacity(0.33)
            ctx.painter.setBrush(common.Color.VeryDarkBackground())
            ctx.painter.drawRect(ctx.rect)


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


class AssetItemViewDelegate(ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.asset_items.AssetItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'icon_bw_sm'

    def paint(self, painter, option, index):
        """Paints the extra columns of
        :class:`~bookmarks.items.asset_items.AssetItemView`.

        """
        ctx = super().paint(painter, option, index)

        if not ctx:
            return

        if index.column() < 4:
            return

        source_model = index.model().sourceModel()
        source_index = index.model().mapToSource(index)

        p = source_model.parent_path()
        k = source_model.task()
        t = common.FileItem

        _data = common.get_data(p, k, t)

        if not _data:
            return
        if source_index.row() not in _data:
            return
        if not _data[source_index.row()][common.AssetProgressRole]:
            return
        if index.column() - 4 not in _data[source_index.row()][common.AssetProgressRole]:
            return

        data = _data[source_index.row()][common.AssetProgressRole][index.column() - 4]

        right_edge = self.paint_progress_background(ctx, data)
        self.paint_progress_name(ctx, data, right_edge)
        self.paint_progress_leading_shadow(ctx)

        return ctx

    @save_painter
    def paint_progress_leading_shadow(self, ctx):
        if ctx.index.column() != 4:
            return

        rect = QtCore.QRect(ctx.rect)
        o = common.Size.Margin(3.0)
        rect.setWidth(o)

        ctx.painter.setOpacity(0.5)
        pixmap = images.rsc_pixmap(
            'gradient', None, rect.height()
        )
        ctx.painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(o * 0.5)
        ctx.painter.drawPixmap(rect, pixmap, pixmap.rect())

    @save_painter
    def paint_progress_background(self, ctx, data):
        rect = QtCore.QRect(ctx.rect)
        rect.setBottom(rect.bottom() - common.Size.Separator())

        # Draw background
        color = progress.STATES[data['value']]['color']
        ctx.painter.setBrush(color)
        ctx.painter.setPen(QtCore.Qt.NoPen)
        if ctx.hover:
            ctx.painter.setOpacity(1.0)
        else:
            ctx.painter.setOpacity(0.85)
        ctx.painter.drawRect(rect)

        if ctx.selected:
            _color = common.Color.LightBackground()
            ctx.painter.setBrush(_color)
            ctx.painter.setOpacity(0.15)
            ctx.painter.drawRect(rect)

        rect.setWidth(rect.height())
        center = rect.center()

        r = common.Size.Margin()
        rect.setSize(QtCore.QSize(r, r))
        rect.moveCenter(center)
        rect.moveLeft(ctx.rect.left() + common.Size.Indicator(2.0))

        if data['value'] == progress.OmittedState:
            if ctx.hover:
                ctx.painter.setOpacity(1.0)
            else:
                ctx.painter.setOpacity(0.1)
        else:
            ctx.painter.setOpacity(0.5)

        pixmap = images.rsc_pixmap(
            progress.STATES[data['value']]['icon'],
            color=None,
            size=r
        )

        ctx.painter.drawPixmap(rect, pixmap, pixmap.rect())
        return rect.right()

    @save_painter
    def paint_progress_name(self, ctx, data, right_edge):

        text = progress.STATES[data['value']]['name']

        if data['value'] == progress.OmittedState:
            text = f'Edit\n{data["name"]}' if ctx.hover else ''
            ctx.painter.setOpacity(0.25)
        ctx.painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 255)))
        _rect = QtCore.QRect(ctx.rect)

        _o = common.Size.Indicator(2.0)
        _rect.setLeft(right_edge + _o)

        font, metrics = common.Font.LightFont(common.Size.SmallText())
        ctx.painter.setFont(font)
        ctx.painter.drawText(
            _rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text
        )

    def createEditor(self, parent, option, index):
        """Creates a combobox editor used to change a state value.

        """
        if index.column() < 4:
            return super().createEditor(parent, option, index)

        editor = QtWidgets.QComboBox(parent=parent)
        editor.setStyleSheet(
            f'border-radius:0px;'
            f'selection-background-color:rgba(180,180,180,255);'
            f'margin:0px;'
            f'padding:0px;'
            f'min-width:{common.Size.DefaultWidth(0.33)}px;'
            f'height:{option.rect.height()}px;'
        )
        editor.currentIndexChanged.connect(
            lambda _: self.commitData.emit(editor)
        )
        editor.currentIndexChanged.connect(
            lambda _: self.closeEditor.emit(editor)
        )
        QtCore.QTimer.singleShot(100, editor.showPopup)
        return editor

    def setEditorData(self, editor, index):
        """Loads the state values from the current index into the editor.

        """
        if index.column() < 4:
            return super().setEditorData(editor, index)

        source_model = index.model().sourceModel()
        source_index = index.model().mapToSource(index)

        p = source_model.parent_path()
        k = source_model.task()
        t = common.FileItem

        _data = common.get_data(p, k, t)
        data = _data[source_index.row()][common.AssetProgressRole][index.column() - 4]

        for state in sorted(data['states']):
            editor.addItem(
                progress.STATES[state]['name'],
                userData=state
            )
            icon = progress.STATES[state]['icon']

            editor.setItemIcon(
                editor.count() - 1,
                ui.get_icon(icon, color=None),
            )
            editor.setItemData(
                editor.count() - 1,
                progress.STATES[state]['color'],
                role=QtCore.Qt.BackgroundRole
            )
            editor.setItemData(
                editor.count() - 1,
                QtCore.QSize(1, common.Size.RowHeight(1.0)),
                role=QtCore.Qt.SizeHintRole
            )
        editor.setCurrentText(
            progress.STATES[data['value']]['name']
        )

    def setModelData(self, editor, model, index):
        """Saves the current state value to the bookmark database.

        """
        if index.column() < 4:
            return super().setModelData(editor, model, index)

        source_model = index.model().sourceModel()
        source_index = index.model().mapToSource(index)

        p = source_model.parent_path()
        k = source_model.task()
        t = common.FileItem

        data = common.get_data(p, k, t)

        # We don't have to modify the internal data directly because
        # the db.set_value call will trigger an item refresh
        progress_data = copy.deepcopy(data[source_index.row()][common.AssetProgressRole])
        progress_data[index.column() - 4]['value'] = editor.currentData()

        # Write current data to the database
        pp = data[source_index.row()][common.ParentPathRole]
        db = database.get(*pp[0:3])
        db.set_value(
            data[source_index.row()][common.PathRole],
            'progress',
            progress_data,
            database.AssetTable
        )

    def updateEditorGeometry(self, editor, option, index):
        """Resizes the editor.

        """
        if index.column() < 4:
            super().updateEditorGeometry(editor, option, index)
            return

        super().updateEditorGeometry(editor, option, index)
        editor.setGeometry(option.rect)


class FileItemViewDelegate(ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.file_items.FileItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'file_item'


class FavouriteItemViewDelegate(FileItemViewDelegate):
    """The delegate used to render
    :class:`bookmarks.items.favourite_items.FavouriteItemView` items.

    """
    fallback_thumb = 'favourite_item'
