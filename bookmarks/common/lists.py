"""A set of shortcuts to the main list widgets and their models'.

"""
from PySide2 import QtCore

from .. import common


def widget(idx=None):
    """Retrieves the currently visible list widget if idx is None,
    otherwise, returns the specified widget.

    Args:
        idx (int, optional): A tab index number, e.g. ``common.FileTab``.

    Returns:
        BaseListWidget: A list widget.

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
        BaseModel: A list widget's source model.

    """
    common.check_type(idx, (int, None))
    return model(idx=idx).sourceModel()


def active_index(idx=None):
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
    return common.get_selected_index(widget(idx=idx))


def current_tab():
    """The current tab index.

    Returns:
        int: The currently visible tab's index.

    """
    if common.init_mode is None or not common.main_widget:
        raise RuntimeError('Not yet initialized!')
    return common.main_widget.stacked_widget.currentIndex()
