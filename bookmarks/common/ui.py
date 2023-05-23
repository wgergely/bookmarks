"""Collection of common utility methods used by UI elements.

The app has some DPI awareness, although, I'm pretty confident it wasn't implemented
correctly. Still, all size values must be queried using :func:`.size()` to get a DPI
dependent pixel value.

"""

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common


def size(v):
    """Return a size value based on the current UI scale factors.

    Args:
        v (int): A size value in pixels.

    """
    _v = (float(v) * (float(common.dpi) / 72.0)) * float(common.ui_scale_factor)
    return int(_v)


def color(v):
    """Get and cache a QColor."""
    r = repr(v)
    if r not in common.color_cache:
        common.color_cache[r] = QtGui.QColor(*v)
    return common.color_cache[r]


def rgb(v):
    """Returns the `rgba(r,g,b,a)` string representation of a QColor.

    Args:
            v (QColor or int): A color.

    Returns:
            str: The string representation of the color.

    """
    if not isinstance(v, QtGui.QColor):
        v = common.color(v)
    r = repr(v)
    if r not in common.color_cache_str:
        common.color_cache_str[r] = (
            f'rgba({",".join([str(f) for f in v.getRgb()])})'
        )
    return common.color_cache_str[r]


def status_bar_message(message):
    """Decorator function used to show a status bar message.
    
    """

    def decorator(function):
        """Function decorator."""

        def wrapper(*args, **kwargs):
            """Function wrapper."""
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


def fit_screen_geometry(w):
    """Fit the given widget's size to the available screen geometry.
    
    
    Args:
        w (QtWidget): The widget to fit to screen geometry.
        
    """
    app = QtWidgets.QApplication.instance()
    for screen in app.screens():
        _geo = screen.availableGeometry()
        if _geo.contains(common.cursor.pos(screen)):
            w.setGeometry(_geo)
            return


def center_window(w):
    """Move the given widget to the available screen geometry's middle.

    Args:
        w (QWidget): The widget to center.

    """
    w.adjustSize()
    app = QtWidgets.QApplication.instance()
    for screen in app.screens():
        _geo = screen.availableGeometry()
        r = w.rect()
        if _geo.contains(common.cursor.pos(screen)):
            w.move(_geo.center() + (r.topLeft() - r.center()))
            return


def move_widget_to_available_geo(w):
    """Moves the given widget inside available screen geometry.

    Args:
        w (QWidget): The widget to move.

    """
    app = QtWidgets.QApplication.instance()
    if w.window():
        screen_idx = app.desktop().screenNumber(w.window())
    else:
        screen_idx = app.desktop().primaryScreen()

    screen = app.screens()[screen_idx]
    screen_rect = screen.availableGeometry()

    # Widget's rectangle in the global screen space
    rect = QtCore.QRect()
    top_left = w.mapToGlobal(w.rect().topLeft())
    rect.setTopLeft(top_left)
    rect.setWidth(w.rect().width())
    rect.setHeight(w.rect().height())

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

    w.move(x, y)


def set_stylesheet(w):
    """Apply the app's custom stylesheet to the given widget.

    Args:
        w (QWidget): A widget to apply the stylesheet to.

    Returns:
            str: The stylesheet applied to the widget.

    """
    if not common.stylesheet:
        init_stylesheet()

    w.setStyleSheet(common.stylesheet)


def init_stylesheet():
    """Loads and stores the custom stylesheet used by the app.
    
    The stylesheet template is stored in the ``rsc/stylesheet.qss`` file, and we use
    the values in ``config.json`` to expand it.

    Returns:
        str: The stylesheet.
    
    """
    path = common.rsc(common.stylesheet_file)

    with open(path, 'r', encoding='utf-8') as f:
        f.seek(0)
        qss = f.read()

    try:
        from .. import images
        primary = common.font_db.bold_font(
            size(common.size_font_medium))[0].family()
        secondary = common.font_db.medium_font(
            size(common.size_font_small)
        )[0].family()

        qss = qss.format(
            font_primary=primary,
            font_secondary=secondary,
            size_font_small=int(size(common.size_font_small)),
            size_font_medium=int(size(common.size_font_medium)),
            size_font_large=int(size(common.size_font_large)),
            size_separator=int(size(common.size_separator)),
            size_indicator=int(size(common.size_indicator)),
            size_indicator1=int(size(common.size_indicator) * 1.33),
            size_indicator2=int(size(common.size_indicator) * 1.8),
            size_margin=int(size(common.size_margin)),
            size_margin2=int(size(common.size_margin) * 2),
            size_margin3=int(size(common.size_margin) * 4),
            size_row_height=int(size(common.size_row_height)),
            size_row_height2=int(size(common.size_row_height) * 0.8),
            color_background=rgb(common.color_background),
            color_light_background=rgb(common.color_light_background),
            color_dark_background=rgb(common.color_dark_background),
            color_text=rgb(common.color_text),
            color_secondary_text=rgb(common.color_secondary_text),
            color_selected_text=rgb(common.color_selected_text),
            color_disabled_text=rgb(common.color_disabled_text),
            color_green=rgb(common.color_green),
            color_red=rgb(common.color_red),
            color_separator=rgb(common.color_separator),
            color_blue=rgb(common.color_blue),
            color_opaque=rgb(common.color_opaque),
            branch_closed=images.rsc_pixmap(
                'branch_closed', None, None, get_path=True
            ),
            branch_open=images.rsc_pixmap(
                'branch_open', None, None, get_path=True
            ),
            check=images.rsc_pixmap(
                'check', None, None, get_path=True
            ),
            close=images.rsc_pixmap(
                'close', None, None, get_path=True
            ),
            menu_border_radius=int(size(common.size_margin) * 0.5)
        )
    except KeyError as err:
        from . import log
        msg = f'Looks like there might be an error in the stylesheet file: {err}'
        log.error(msg)
        raise

    common.stylesheet = qss
    return qss


def draw_aliased_text(painter, font, rect, text, align, color, elide=None):
    """Allows drawing aliased text using QPainterPaths.

    This is slow to calculate but ensures the rendered text looks *smooth* (on
    Windows especially, I noticed a lot of aliasing issues). We're also eliding
    the given text to the width of the given rectangle.

    Args:
            painter (QPainter): The active painter.
            font (QFont): The font to use to paint.
            rect (QRect): The rectangle to fit the text in.
            text (str): The text to paint.
            align (Qt.AlignmentFlag): The alignment flags.
            color (QColor): The color to use.
            elide (bool): Elides the source text if True.

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
    delegate.draw_painter_path(painter, x, y, font, text)

    painter.restore()
    return width


def get_selected_index(widget):
    """Find the index of a selected item of `widget`.

    Args:
        widget (QWidget): The widget to get the selection from.

    Returns:
        QPersistentModelIndex: The selected index.

    """
    if (
            not hasattr(widget, 'selectionModel') or
            not widget.selectionModel().hasSelection()
    ):
        return QtCore.QModelIndex()

    index = next(
        (f for f in widget.selectionModel().selectedIndexes()),
        QtCore.QModelIndex()
    )
    if not index.isValid():
        return QtCore.QModelIndex()
    return QtCore.QPersistentModelIndex(index)


@QtCore.Slot(QtWidgets.QWidget)
@QtCore.Slot(str)
def save_selection(widget, *args, **kwargs):
    """Save selected item to the user settings file.

    Args:
        widget (QWidget): The widget to get the selection from.

    """
    index = get_selected_index(widget)

    if not index or not index.isValid():
        return
    v = index.data(QtCore.Qt.DisplayRole)
    if not v:
        return

    k = f'selection/{widget.__class__.__name__}'
    common.settings.setValue(k, v)


@QtCore.Slot(QtWidgets.QWidget)
@QtCore.Slot(str)
def restore_selection(widget, *args, **kwargs):
    """Restore a previously saved item selection.

    Args:
        widget (QWidget): The widget to get the selection from.

    """
    k = f'selection/{widget.__class__.__name__}'
    v = common.settings.value(k)
    if not hasattr(widget, 'selectionModel'):
        return
    if not v:
        widget.selectionModel().clear()
        return
    select_index(widget, v)


@QtCore.Slot(QtWidgets.QWidget)
@QtCore.Slot(str)
def select_index(widget, v, *args, role=QtCore.Qt.DisplayRole, **kwargs):
    """Utility function used to select and reveal an item index in a view.

    Args:
        widget (QWidget): The view containing the item to select.
        v (str): The value of role.
        role (QtCore.Qt.ItemDataRole): The value's role.

    """
    selected_index = common.get_selected_index(widget)
    for n in range(widget.model().rowCount()):
        index = widget.model().index(n, 0)

        if v != index.data(role):
            continue

        if selected_index == index:
            widget.scrollTo(
                index,
                QtWidgets.QAbstractItemView.PositionAtCenter
            )
            return

        widget.selectionModel().select(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )
        widget.scrollTo(
            index,
            QtWidgets.QAbstractItemView.PositionAtCenter
        )
        return

    widget.selectionModel().clear()


@common.error
@common.debug
@QtCore.Slot()
def save_window_state(widget, *args, **kwargs):
    """Saves the current state of a window.

    Args:
        widget (QWidget): A widget or window.

    """
    w = widget.window()
    dict_key = w.__class__.__name__

    v = common.settings.value('state/geometry')
    v = v if v else {}
    v[dict_key] = w.saveGeometry()
    common.settings.setValue('state/geometry', v)

    v = common.settings.value('state/state')
    v = v if v else {}
    v[dict_key] = int(widget.windowState())
    common.settings.setValue('state/state', v)


@common.error
@common.debug
def restore_window_geometry(widget, *args, **kwargs):
    """Restore the previously saved window geometry.
    
    Args:
        widget (QWidget): The widget to restore the window geometry.
        
    """
    w = widget.window()
    dict_key = w.__class__.__name__

    v = common.settings.value('state/geometry')
    if v and dict_key in v and v[dict_key]:
        widget.restoreGeometry(v[dict_key])


def restore_window_state(widget, *args, **kwargs):
    """Restore the previously saved window state.

    Args:
        widget (QWidget): The widget to restore the window geometry.

    """
    w = widget.window()
    dict_key = widget.__class__.__name__

    v = common.settings.value('state/state')
    state = v[dict_key] if v and dict_key in v else None
    state = QtCore.Qt.WindowNoState if state is None else QtCore.Qt.WindowState(state)

    w.activateWindow()
    if state == QtCore.Qt.WindowNoState:
        w.showNormal()
    elif state & QtCore.Qt.WindowMaximized:
        w.showMaximized()
    elif state & QtCore.Qt.WindowFullScreen:
        w.showFullScreen()
    else:
        w.showNormal()

    if hasattr(w, 'open'):
        w.open()

    return w


def widget(idx=None):
    """Retrieves the currently visible list widget if idx is None,
    otherwise, returns the specified widget.

    Args:
        idx (int, optional): A tab index number, e.g. ``common.FileTab``.

    Returns:
        BaseItemView: A list widget.

    """
    common.check_type(idx, (int, None))

    if common.init_mode is None or not common.main_widget:
        raise RuntimeError('Not yet initialized!')

    if idx is None:
        return common.main_widget.stacked_widget.currentWidget()

    if idx == common.TaskTab:
        return common.main_widget.tasks_widget
    return common.main_widget.stacked_widget.widget(idx)


def model(idx=None):
    """Retrieves a list widget's proxy model.

    If idx is None, it returns the currently visible items' model,
    otherwise, returns the specified widget's model.

    Args:
        idx (int, optional): A tab index number, e.g. ``common.FileTab``.

    Returns:
        FilterProxyModel: A list widget's proxy model.

    """
    common.check_type(idx, (int, None))
    return widget(idx=idx).model()


def source_model(idx=None):
    """Retrieves a list widget's source model.

    If idx is None, it returns the currently visible items' source model,
    otherwise, returns the specified widget's source model.

    Args:
        idx (int, optional): A tab index number, e.g. ``common.FileTab``.

    Returns:
        ItemModel: A list widget's source model.

    """
    common.check_type(idx, (int, None))
    return model(idx=idx).sourceModel()


def active_index(idx=None):
    """Get the active index of the current, or given list index.

    Args:
        idx (int, optional): A tab index number, e.g. ``common.FileTab``.

    """
    common.check_type(idx, (int, None))
    return source_model(idx=idx).active_index()


def selected_index(idx=None):
    """Retrieves a list widget's active index.

    If idx is None, it returns the currently visible items' active index,
    otherwise, returns the specified widget's active index.

    Args:
        idx (int, optional): A tab index number, e.g. ``common.FileTab``.

    Returns:
        QtCore.QModelIndex: A list widget's active index.

    """
    common.check_type(idx, (int, None))
    return get_selected_index(widget(idx=idx))


def current_tab():
    """The current tab index.

    Returns:
        int: The currently visible tab's index.

    """
    if common.init_mode is None or not common.main_widget:
        raise RuntimeError('Not yet initialized!')
    return common.main_widget.stacked_widget.currentIndex()
