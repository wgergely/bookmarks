"""Collection of common utility methods used by UI elements.

The app has some DPI awareness, although, I'm pretty confident it wasn't implemented
correctly. Still, all size values must be queried using :func:`.size()` to get a DPI
dependent pixel value.

"""
import os
import re

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common

OkButton = 'Ok'
YesButton = 'Yes'
SaveButton = 'Save'
CancelButton = 'Cancel'
NoButton = 'No'


def _init_ui_scale():
    v = common.settings.value('settings/ui_scale')

    if v is None or not isinstance(v, str):
        common.ui_scale_factor = 1.0
        return

    if '%' not in v:
        v = 1.0
    else:
        v = v.strip('%')
    try:
        v = float(v) * 0.01
    except:
        v = 1.0
    v = round(v, 2)
    if not common.ui_scale_factors or v not in common.ui_scale_factors:
        v = 1.0

    common.ui_scale_factor = v


def _init_dpi():
    if common.get_platform() == common.PlatformWindows:
        common.dpi = 72.0
    elif common.get_platform() == common.PlatformMacOS:
        common.dpi = 96.0
    elif common.get_platform() == common.PlatformUnsupported:
        common.dpi = 72.0


def _init_stylesheet():
    """Loads and stores the custom stylesheet used by the app.

    The stylesheet template is stored in the ``rsc/stylesheet.qss`` file, and we use
    the values in ``config.json`` to expand it.

    Returns:
        str: The stylesheet.

    """
    from .. import images
    from . import core

    path = common.rsc(common.stylesheet_file)
    if not os.path.isfile(path):
        raise FileNotFoundError(f'Stylesheet file not found: {path}')

    if common.stylesheet:
        raise RuntimeError('Stylesheet already initialized!')

    with open(path, 'r', encoding='utf-8') as f:
        qss = f.read()

    kwargs = {}

    for enum in core.Font:
        if not enum:
            raise RuntimeError(f'Font {enum.name} not found!')
        font, _ = enum(common.Size.MediumText())
        kwargs[enum.name] = font.family()

    for enum in core.Color:
        key = enum.name
        if key in kwargs:
            raise KeyError(f'Key {key} already set!')
        kwargs[enum.name] = common.Color.rgb(enum())

    for enum in core.Size:
        for i in [float(f) / 10.0 for f in range(1, 101)]:
            key = f'{enum.name}@{i:.1f}'
            if key in kwargs:
                raise KeyError(f'Key {key} already set!')
            kwargs[key] = round(enum() * i)

    # Gui resource paths
    for entry in os.scandir(common.rsc('gui')):
        if not entry.name.endswith('png'):
            continue
        key = f'{entry.name.split(".")[0]}'
        if key in kwargs:
            raise KeyError(f'Key {key} already set!')

        # Image path
        kwargs[key] = images.rsc_pixmap(key, None, None, get_path=True)

    # Custom Image Data
    pixmap = images.rsc_pixmap(
        'server',
        QtGui.QColor(0,0,0,255),
        common.Size.RowHeight(3.0),
        opacity=0.2
    )
    pixmap.save(f'{common.temp_path()}/ServerViewBackground.png')
    kwargs[f'ServerViewBackground'] = f'{common.temp_path()}/ServerViewBackground.png'

    pixmap = images.rsc_pixmap(
        'bookmark',
        QtGui.QColor(0,0,0,255),
        common.Size.RowHeight(3.0),
        opacity=0.2
    )
    pixmap.save(f'{common.temp_path()}/BookmarkItemView.png')
    kwargs[f'BookmarkItemView'] = f'{common.temp_path()}/BookmarkItemView.png'

    # Tokens are defined as "<token>" in the stylesheet file
    for match in re.finditer(r'<(.*?)>', qss):
        if not match:
            continue

        key = match.group(1)
        if key not in kwargs:
            raise KeyError(f'Key {key} not found in kwargs!')

        qss = qss.replace(f'<{key}>', str(kwargs[key]))

    # Make sure all tokens are replaced
    if re.search(r'<(.*?)>', qss):
        raise RuntimeError('Not all tokens were replaced!')

    common.stylesheet = qss
    return qss


def rsc(rel_path):
    """Get the absolute path to a resource item from the relative path.

    Args:
        rel_path (str): The relative path to the resource item.

    Returns:
        str: The absolute path to the resource item.

    """
    v = os.path.normpath('/'.join((__file__, os.pardir, os.pardir, 'rsc', rel_path)))

    f = QtCore.QFileInfo(v)
    if not f.exists():
        raise RuntimeError(f'{f.filePath()} does not exist.')
    return f.filePath()


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


def center_to_parent(widget, parent=None):
    """Move the given widget to the widget's parent's middle.

    Args:
        widget (QWidget): The widget to center.
        parent (QWidget): Optional. The widget to center to.

    """
    if not widget.parent() and not parent:
        return
    if widget.parent() and not parent:
        parent = widget.parent()

    widget.adjustSize()
    g = parent.geometry()
    r = widget.rect()
    widget.move(g.center() + (r.topLeft() - r.center()))
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
    if common.init_mode is None:
        raise RuntimeError('Not yet initialized!')
    if not common.stylesheet:
        raise RuntimeError('Stylesheet not initialized!')

    w.setStyleSheet(common.stylesheet)


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
    elif QtCore.Qt.AlignRight & align:
        x = rect.right() - width
    elif QtCore.Qt.AlignHCenter & align:
        x = rect.left() + (rect.width() * 0.5) - (width * 0.5)
    else:
        x = rect.left()

    y = rect.center().y() + (metrics.ascent() * 0.5) - (metrics.descent() * 0.5)

    # Ensure text fits the rectangle
    painter.setBrush(color)
    painter.setPen(QtCore.Qt.NoPen)

    from ..items import delegate
    delegate.draw_painter_path(painter, x, y, font, text)

    painter.restore()
    return width


def close_message():
    """Close the message box.

    """
    if common.message_widget is None:
        return

    try:
        common.message_widget.close()
        common.message_widget.deleteLater()
        common.message_widget = None
    except:
        pass


def show_message(
        title, body='', disable_animation=False, icon='icon', message_type='info', buttons=None, modal=False,
        parent=None
):
    """Show a message box.

    Args:
        title (str): The title of the message box.
        body (str): The body of the message box.
        disable_animation (bool): Whether to show the message box without animation.
        icon (str): The icon to use.
        message_type (str): The message type. One of 'info', 'success', 'error' or None.
        buttons (list): The buttons to show.
        modal (bool): Whether the message box should be modal.
        parent (QWidget): The parent widget.

    Returns:
        int: The result of the message box.

    """
    if common.init_mode is None:
        raise RuntimeError('Bookmarks must be initialized first.')

    close_message()

    app = QtWidgets.QApplication.instance()
    if not app:
        return
    if QtCore.QThread.currentThread() != app.thread():
        return

    from .. import ui
    mbox = ui.MessageBox(
        title=title,
        body=body,
        disable_animation=disable_animation,
        icon=icon,
        message_type=message_type,
        buttons=[OkButton, ] if buttons is None else buttons,
        parent=parent
    )
    common.message_widget = mbox
    if modal:
        return mbox.exec_()

    if disable_animation:
        mbox.show()
        mbox.raise_()
        QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
        return mbox
    return mbox.open()


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
        widget.selectionModel().setCurrentIndex(
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
        idx (int, optional): A tab index number, for example, ``common.FileTab``.

    Returns:
        BaseItemView: A list widget.

    """
    common.check_type(idx, (int, None))

    if common.init_mode is None or not common.main_widget:
        raise RuntimeError('Not yet initialized!')

    if idx is None:
        return common.main_widget.stacked_widget.currentWidget()

    if idx == common.BookmarkItemSwitch:
        return common.main_widget.bookmark_switch_widget
    if idx == common.AssetItemSwitch:
        return common.main_widget.asset_switch_widget
    if idx == common.TaskItemSwitch:
        return common.main_widget.task_switch_widget
    return common.main_widget.stacked_widget.widget(idx)


def model(idx=None):
    """Retrieves a list widget's proxy model.

    If idx is None, it returns the currently visible items' model,
    otherwise, returns the specified widget's model.

    Args:
        idx (int, optional): A tab index number, for example, ``common.FileTab``.

    Returns:
        FilterProxyModel: A list widget's proxy model.

    """
    if common.init_mode is None or not common.main_widget:
        raise RuntimeError('Not yet initialized!')

    common.check_type(idx, (int, None))
    return widget(idx=idx).model()


def source_model(idx=None):
    """Retrieves a list widget's source model.

    If idx is None, it returns the currently visible items' source model,
    otherwise, returns the specified widget's source model.

    Args:
        idx (int, optional): A tab index number, for example, ``common.FileTab``.

    Returns:
        ItemModel: A list widget's source model.

    """
    common.check_type(idx, (int, None))
    return model(idx=idx).sourceModel()


def active_index(idx=None):
    """Get the active index of a specified item tab view.

    Args:
        idx (int, optional): A tab index number, e.g. ``common.FileTab``.

    Returns:
        QtCore.QModelIndex: The active index.

    """
    common.check_type(idx, (int, None))
    return source_model(idx=idx).active_index()


def selected_index(idx=None):
    """Get the selected index of a specified item tab view.

    Args:
        idx (int, optional): A tab index number, e.g. ``common.FileTab``.

    Returns:
        QtCore.QModelIndex: The selected index.

    """
    if common.init_mode is None or not common.main_widget:
        raise RuntimeError('Not yet initialized!')

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
