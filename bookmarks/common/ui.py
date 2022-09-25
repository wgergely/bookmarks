# -*- coding: utf-8 -*-
"""Collection of common utility methods used by UI elements.

Bookmarks has some DPI awareness, although, I'm pretty confident it wasn't
implemented correctly. Still,
all size values must be queried using :func:`.size()` to get a DPI dependent pixel
value.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from .. import common


def size(v):
    """Return a size value based on the current UI scale factors.

    Args:
        v (int): A size value in pixels.

    """
    v = (float(v) * (float(common.dpi) / 72.0)) * float(common.ui_scale_factor)
    return int(v)


def color(v):
    """Get and cache a QColor."""
    r = repr(v)
    if r not in common.color_cache:
        common.color_cache[r] = QtGui.QColor(*v)
    return common.color_cache[r]


def rgb(v):
    """Returns the `rgba(r,g,b,a)` string representation of a QColor.

    Args:
            v (QColor): A color.

    Returns:
            str: The string representation of the color.

    """
    v = 'rgba({})'.format(','.join([str(f) for f in v.getRgb()]))
    return v


def status_bar_message(message):
    def decorator(function):
        def wrapper(*args, **kwargs):
            from .. import log
            from . import signals

            if common.debug_on:
                log.debug(message)
            signals.showStatusBarMessage.emit(message)
            result = function(*args, **kwargs)
            signals.showStatusBarMessage.emit('')
            return result

        return wrapper

    return decorator


def fit_screen_geometry(widget):
    app = QtWidgets.QApplication.instance()
    for screen in app.screens():
        _geo = screen.availableGeometry()
        if _geo.contains(common.cursor.pos(screen)):
            widget.setGeometry(_geo)
            return


def center_window(widget):
    widget.adjustSize()
    app = QtWidgets.QApplication.instance()
    for screen in app.screens():
        _geo = screen.availableGeometry()
        r = widget.rect()
        if _geo.contains(common.cursor.pos(screen)):
            widget.move(_geo.center() + (r.topLeft() - r.center()))
            return


def move_widget_to_available_geo(widget):
    """Moves the widget inside the available screen geometry, if any of the
    edges fall outside it.

    """
    app = QtWidgets.QApplication.instance()
    if widget.window():
        screen_idx = app.desktop().screenNumber(widget.window())
    else:
        screen_idx = app.desktop().primaryScreen()

    screen = app.screens()[screen_idx]
    screen_rect = screen.availableGeometry()

    # Widget's rectangle in the global screen space
    rect = QtCore.QRect()
    topLeft = widget.mapToGlobal(widget.rect().topLeft())
    rect.setTopLeft(topLeft)
    rect.setWidth(widget.rect().width())
    rect.setHeight(widget.rect().height())

    x = rect.x()
    y = rect.y()

    if rect.left() < screen_rect.left():
        x = screen_rect.x()
    if rect.top() < screen_rect.top():
        y = screen_rect.y()
    if rect.right() > screen_rect.right():
        x = screen_rect.right() - rect.width()
    if rect.bottom() > screen_rect.bottom():
        y = screen_rect.bottom() - rect.height()

    widget.move(x, y)


def set_stylesheet(widget):
    """Set Bookmark's custom stylesheet to the given widget.

    The tokenized stylesheet is stored in `common.stylesheet_file`.

    Args:
            widget (QWidget): A widget t apply the stylesheet to.

    Returns:
            str: The stylesheet applied to the widget.

    """
    if common.stylesheet:
        widget.setStyleSheet(common.stylesheet)
        return

    path = common.get_rsc(common.stylesheet_file)

    with open(path, 'r', encoding='utf-8') as f:
        f.seek(0)
        qss = f.read()

    try:
        from .. import images
        primary = common.font_db.primary_font(
            size(common.FontSizeMedium))[0].family()
        secondary = common.font_db.secondary_font(
            size(common.FontSizeSmall)
        )[0].family()

        qss = qss.format(
            PrimaryFont=primary,
            SecondaryFont=secondary,
            FontSizeSmall=int(size(common.FontSizeSmall)),
            FontSizeMedium=int(size(common.FontSizeMedium)),
            FontSizeLarge=int(size(common.FontSizeLarge)),
            HeightSeparator=int(size(common.HeightSeparator)),
            WidthIndicator=int(size(common.WidthIndicator)),
            WidthIndicator1=int(size(common.WidthIndicator) * 1.33),
            WidthIndicator2=int(size(common.WidthIndicator) * 1.8),
            WidthMargin=int(size(common.WidthMargin)),
            WidthMargin2=int(size(common.WidthMargin) * 2),
            WidthMargin3=int(size(common.WidthMargin) * 4),
            SmallHeight=int(size(common.HeightRow) * 0.66),
            BackgroundColor=rgb(common.color(common.BackgroundColor)),
            BackgroundLightColor=rgb(common.color(common.BackgroundLightColor)),
            BackgroundDarkColor=rgb(common.color(common.BackgroundDarkColor)),
            TextColor=rgb(common.color(common.TextColor)),
            TextSecondaryColor=rgb(common.color(common.TextSecondaryColor)),
            TextSelectedColor=rgb(common.color(common.TextSelectedColor)),
            TextDisabledColor=rgb(common.color(common.TextDisabledColor)),
            GreenColor=rgb(common.color(common.GreenColor)),
            RedColor=rgb(common.color(common.RedColor)),
            SeparatorColor=rgb(common.color(common.SeparatorColor)),
            BlueColor=rgb(common.color(common.BlueColor)),
            OpaqueColor=rgb(common.color(common.OpaqueColor)),
            branch_closed=images.ImageCache.get_rsc_pixmap(
                'branch_closed', None, None, get_path=True
            ),
            branch_open=images.ImageCache.get_rsc_pixmap(
                'branch_open', None, None, get_path=True
            ),
            check=images.ImageCache.get_rsc_pixmap(
                'check', None, None, get_path=True
            ),
            close=images.ImageCache.get_rsc_pixmap(
                'close', None, None, get_path=True
            )
        )
    except KeyError as err:
        from . import log
        msg = f'Looks like there might be an error in the stylesheet file: {err}'
        log.error(msg)
        raise

    common.stylesheet = qss
    widget.setStyleSheet(common.stylesheet)
    return common.stylesheet


def draw_aliased_text(painter, font, rect, text, align, color, elide=None):
    """Allows drawing aliased text using *QPainterPath*.

    This is slow to calculate but ensures the rendered text looks *smooth* (on
    Windows espcially, I noticed a lot of aliasing issues). We're also eliding
    the given text to the width of the given rectangle.

    Args:
            painter (QPainter):         The active painter.
            font (QFont):               The font to use to paint.
            rect (QRect):               The rectangle to fit the text in.
            text (str):             The text to paint.
            align (Qt.AlignmentFlag):   The alignment flags.
            color (QColor):             The color to use.

    Returns:
            int: The width of the drawn text in pixels.

    """
    painter.save()

    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)

    metrics = QtGui.QFontMetrics(font)

    if elide is None:
        elide = QtCore.Qt.ElideLeft
        if QtCore.Qt.AlignLeft & align:
            elide = QtCore.Qt.ElideRight
        if QtCore.Qt.AlignRight & align:
            elide = QtCore.Qt.ElideLeft
        if QtCore.Qt.AlignHCenter & align:
            elide = QtCore.Qt.ElideMiddle

    text = metrics.elidedText(
        text,
        elide,
        rect.width() * 1.01
    )
    width = metrics.horizontalAdvance(text)

    if QtCore.Qt.AlignLeft & align:
        x = rect.left()
    if QtCore.Qt.AlignRight & align:
        x = rect.right() - width
    if QtCore.Qt.AlignHCenter & align:
        x = rect.left() + (rect.width() * 0.5) - (width * 0.5)
    else:
        x = rect.left()

    y = rect.center().y() + (metrics.ascent() * 0.5) - (metrics.descent() * 0.5)

    # Making sure text fits the rectangle
    painter.setBrush(color)
    painter.setPen(QtCore.Qt.NoPen)

    from ..items import delegate
    path = delegate.get_painter_path(x, y, font, text)
    painter.drawPath(path)

    painter.restore()
    return width


@QtCore.Slot(QtWidgets.QWidget)
@QtCore.Slot(str)
def save_selection(widget, key, *args, **kwargs):
    index = common.get_selected_index(widget)
    v = index.data(QtCore.Qt.DisplayRole) if index.isValid() else None
    common.settings.setValue(key, v)


@QtCore.Slot(QtWidgets.QWidget)
@QtCore.Slot(str)
def restore_selection(widget, key, *args, **kwargs):
    v = common.settings.value(key)
    if not v:
        widget.selectionModel().clear()
        return
    select_index(widget, v)


@QtCore.Slot(QtWidgets.QWidget)
@QtCore.Slot(str)
def select_index(widget, v, *args, **kwargs):
    selected_index = common.get_selected_index(widget)

    if 'role' in kwargs:
        role = kwargs['role']
    else:
        role = QtCore.Qt.DisplayRole

    for n in range(widget.model().rowCount()):
        index = widget.model().index(n, 0)

        if v != index.data(role):
            continue

        if selected_index != index:
            widget.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )

        widget.scrollTo(index, QtWidgets.QAbstractItemView.EnsureVisible)
        return

    widget.selectionModel().clear()


def get_selected_index(widget):
    if not widget.selectionModel().hasSelection():
        return QtCore.QModelIndex()
    index = next(
        (f for f in widget.selectionModel().selectedIndexes()),
        QtCore.QModelIndex()
    )
    if not index.isValid():
        return QtCore.QModelIndex()
    return QtCore.QPersistentModelIndex(index)
