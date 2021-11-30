from PySide2 import QtCore

from .. import common


def widget(idx=None):
    common.check_type(idx, (int, None))

    if common.init_mode is None or not common.main_widget:
        raise RuntimeError('Not yet initialized!')

    if idx is None:
        return common.main_widget.stacked_widget.currentWidget()

    if idx == common.TaskTab:
        return common.main_widget.tasks_widget
    return common.main_widget.stacked_widget.widget(idx)


def model(idx=None):
    common.check_type(idx, (int, None))
    return widget(idx=idx).model()


def source_model(idx=None):
    common.check_type(idx, (int, None))
    return model(idx=idx).sourceModel()


def active_index(idx=None):
    common.check_type(idx, (int, None))
    return source_model(idx=idx).active_index()


def selected_index(idx=None):
    common.check_type(idx, (int, None))
    if not widget(idx=idx).selectionModel().hasSelection():
        return QtCore.QModelIndex()
    index = widget(idx=idx).selectionModel().currentIndex()
    if not index.isValid():
        return QtCore.QModelIndex()
    return index



def current_tab():
    if common.init_mode is None or not common.main_widget:
        raise RuntimeError('Not yet initialized!')
    return common.main_widget.stacked_widget.currentIndex()




# def data(idx):
#     source_model.model_data()
