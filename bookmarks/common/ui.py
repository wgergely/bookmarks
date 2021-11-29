# -*- coding: utf-8 -*-
"""Contains various UI definitions and methods used to construct, and
define ui elements.

"""
import os
from PySide2 import QtWidgets, QtGui, QtCore

from .. import common


COLOR_CACHE = {}


def size(v):
    """Return a size value based on the current UI scale factors.

    Args:
        v (int): A size value in pixels.

    """
    v = (float(v) * (float(common.dpi) / 72.0)) * float(common.ui_scale_factor)
    return int(v)


def color(v):
    r = repr(v)
    if r not in COLOR_CACHE:
        COLOR_CACHE[r] = QtGui.QColor(*v)
    return COLOR_CACHE[r]

def rgb(v):
    """Returns the `rgba(r,g,b,a)` string representation of a QColor.

    Args:
            v (QColor): A color.

    Returns:
            str: The string representation of the color.

    """
    return 'rgba({})'.format(','.join([str(f) for f in v.getRgb()]))


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
    edges fall outside of it.

    """
    app = QtWidgets.QApplication.instance()
    if widget.window():
        screenID = app.desktop().screenNumber(widget.window())
    else:
        screenID = app.desktop().primaryScreen()

    screen = app.screens()[screenID]
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


def set_custom_stylesheet(widget):
    """Set Bookmark's custom stylesheet to the given widget.

    The tokenised stylesheet is stored in the rsc/stylesheet.qss file.
    We'll load and expand the tokens, then store the stylesheet as `STYLESHEET`
    in the module.

    Args:
            widget (QWidget): A widget t apply the stylesheet to.

    Returns:
            str: The stylesheet applied to the widget.

    """
    if common.stylesheet:
        widget.setStyleSheet(common.stylesheet)
        return

    path = os.path.normpath(
        os.path.abspath(
            os.path.join(
                __file__,
                os.pardir,
                os.pardir,
                'rsc',
                'stylesheet.qss'
            )
        )
    )

    if not os.path.isfile(path):
        raise RuntimeError(f'{path} could not be found.')

    with open(path, 'r', encoding='utf-8') as f:
        f.seek(0)
        qss = f.read()

    try:
        from .. import images
        qss = qss.format(
            PRIMARY_FONT=common.font_db.primary_font(
                size(common.FontSizeMedium))[0].family(),
            SECONDARY_FONT=common.font_db.secondary_font(
                size(common.FontSizeSmall))[0].family(),
            FontSizeSmall=int(size(common.FontSizeSmall)),
            FontSizeMedium=int(size(common.FontSizeMedium)),
            FontSizeLarge=int(size(common.FontSizeLarge)),
            RADIUS=int(size(common.WidthIndicator) * 1.5),
            RADIUS_SM=int(size(common.WidthIndicator)),
            SCROLLBAR_SIZE=int(size(common.WidthIndicator) * 2),
            SCROLLBAR_MINHEIGHT=int(size(common.WidthMargin) * 5),
            HeightSeparator=int(size(common.HeightSeparator)),
            WidthMargin=int(size(common.WidthMargin)),
            WidthIndicator=int(size(common.WidthIndicator)),
            CONTEXT_MENU_HEIGHT=int(size(common.WidthMargin) * 2),
            CONTEXT_MENU_ICON_PADDING=int(size(common.WidthMargin)),
            ROW_HEIGHT=int(size(common.HeightRow)),
            BG=rgb(common.color(common.BackgroundColor)),
            SELECTED_BG=rgb(common.color(common.BackgroundLightColor)),
            DARK_BG=rgb(common.color(common.BackgroundDarkColor)),
            TEXT=rgb(common.color(common.TextColor)),
            SECONDARY_TEXT=rgb(common.color(common.TextSecondaryColor)),
            SELECTED_TEXT=rgb(common.color(common.TextSelectedColor)),
            DISABLED_TEXT=rgb(common.color(common.TextDisabledColor)),
            GREEN=rgb(common.color(common.GreenColor)),
            RED=rgb(common.color(common.RedColor)),
            SEPARATOR=rgb(common.color(common.SeparatorColor)),
            BLUE=rgb(common.color(common.BlueColor)),
            TRANSPARENT=rgb(common.color(common.Transparent)),
            TRANSPARENT_BLACK=rgb(common.color(common.OpaqueColor)),
            BRANCH_CLOSED=images.ImageCache.get_rsc_pixmap(
                'branch_closed', None, None, get_path=True),
            BRANCH_OPEN=images.ImageCache.get_rsc_pixmap(
                'branch_open', None, None, get_path=True),
            CHECKED=images.ImageCache.get_rsc_pixmap(
                'check', None, None, get_path=True),
            UNCHECKED=images.ImageCache.get_rsc_pixmap(
                'close', None, None, get_path=True),
        )
    except KeyError as err:
        from . import log
        msg = 'Looks like there might be an error in the stylesheet file: {}'.format(
            err)
        log.error(msg)
        raise KeyError(msg)

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

    y = rect.center().y() + (metrics.ascent() * 0.5) - (metrics.descent() * 0.5)

    # Making sure text fits the rectangle
    painter.setBrush(color)
    painter.setPen(QtCore.Qt.NoPen)

    from .. lists import delegate
    path = delegate.get_painter_path(x, y, font, text)
    painter.drawPath(path)

    painter.restore()
    return width
