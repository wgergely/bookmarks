""""""
import weakref

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import log
from .. import ui


class BaseFilterModel(ui.AbstractListModel):

    def __init__(self, section_name_label, data_source, tab_index, parent=None):
        self.tab_index = tab_index

        self.show_all_label = ' - Show All -'
        self.section_name_label = section_name_label
        self.data_source = data_source

        super().__init__(parent=parent)

        common.signals.internalDataReady.connect(self.internal_data_ready)
        common.signals.bookmarksChanged.connect(self.reset_data)
        common.signals.bookmarkActivated.connect(self.reset_data)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DecorationRole:
            _text = common.model(self.tab_index).filter_text()
            _text = _text.lower().strip() if _text else ''

            if not _text:
                return super().data(index, role)

            text = super().data(index, QtCore.Qt.DisplayRole)
            if not text:
                return super().data(index, role)
            if text == self.show_all_label:
                return super().data(index, role)
            if text == self.section_name_label:
                return super().data(index, role)

            text = text.lower().strip()
            if _text == text:
                return ui.get_icon('check', color=common.color(common.color_green))

            if _text == f'"{text}"':
                return ui.get_icon('check', color=common.color(common.color_green))

        return super().data(index, role)

    @QtCore.Slot(weakref.ref)
    def internal_data_ready(self, ref):
        if not ref():
            return

        source_model = common.source_model(self.tab_index)
        data = common.get_data(
            source_model.source_path(),
            source_model.task(),
            source_model.data_type()
        )

        if ref() != data:
            return

        self.reset_data()

    def reset_data(self):
        self.beginResetModel()
        self.init_data()
        self.endResetModel()

    def init_data(self, *args, **kwargs):
        """Initializes data.

        """
        self._data = common.DataDict()

        source_model = common.source_model(self.tab_index)

        data = common.get_data(
            source_model.source_path(),
            source_model.task(),
            source_model.data_type()
        )

        if not hasattr(data, self.data_source):
            log.error(f'No {self.data_source} found in data!')
            return
        if not getattr(data, self.data_source):
            return

        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: self.section_name_label,
            QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.size(common.size_row_height) * 0.66),
            common.FlagsRole: QtCore.Qt.NoItemFlags,
            QtCore.Qt.TextAlignmentRole: QtCore.Qt.AlignCenter,
        }

        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: self.show_all_label,
            QtCore.Qt.DecorationRole: ui.get_icon('archivedVisible', color=common.color(common.color_green)),
            QtCore.Qt.SizeHintRole: self.row_size,
            QtCore.Qt.TextAlignmentRole: QtCore.Qt.AlignCenter,
        }

        icon = ui.get_icon('sg')

        for task in sorted(getattr(data, self.data_source)):
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: task,
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.DecorationRole: icon,
                QtCore.Qt.StatusTipRole: task,
                QtCore.Qt.AccessibleDescriptionRole: task,
                QtCore.Qt.WhatsThisRole: task,
                QtCore.Qt.ToolTipRole: task,
                QtCore.Qt.TextAlignmentRole: QtCore.Qt.AlignCenter,
            }


class BaseFilterButton(QtWidgets.QComboBox):
    """The combo box used to set a text filter based on the available ShotGrid task names.

    """
    def __init__(self, Model, tab_index, parent=None):
        super().__init__(parent=parent)

        self.tab_index = tab_index
        self.setView(QtWidgets.QListView(parent=self))
        self.setModel(Model())

        self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.setFixedHeight(common.size(common.size_margin))
        self.setMinimumWidth(common.size(common.size_margin))

        common.signals.updateTopBarButtons.connect(lambda: self.setHidden(not common.current_tab() == self.tab_index))
        common.model(self.tab_index).filterTextChanged.connect(self.select_text)
        common.signals.internalDataReady.connect(self.select_text)

        self.textActivated.connect(self.update_filter_text)

    @QtCore.Slot(str)
    def update_filter_text(self, text):
        """Update the filter text.

        Args:
            text (str): The text to set as the filter text.

        """
        if text == self.model().show_all_label:
            text = ''
        else:
            text = f'"{text.lower().strip()}"'

        common.model(self.tab_index).set_filter_text(text)

    @QtCore.Slot()
    def select_text(self, *args, **kwargs):
        """Update the filter text.

        """
        self.setCurrentIndex(0)

        _text = common.model(self.tab_index).filter_text()
        _text = _text.lower().strip() if _text else ''

        if not _text:
            return

        for i in range(self.count()):
            text = self.itemText(i)
            if not text:
                continue
            if text == self.model().show_all_label:
                continue
            if text == self.model().section_name_label:
                continue

            text = text.lower().strip()
            if _text == text:
                self.setCurrentIndex(i)
                return

            if _text == f'"{text}"':
                self.setCurrentIndex(i)
                return


class TaskFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'Tasks',
            'sg_task_names',
            common.AssetTab,
            parent=parent
        )


class TaskFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available ShotGrid task names.

    """
    def __init__(self, parent=None):
        super().__init__(
            TaskFilterModel,
            common.AssetTab,
            parent=parent
        )


class EntityFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'Assets',
            'shotgun_names',
            common.AssetTab,
            parent=parent
        )


class EntityFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available ShotGrid task names.

    """
    def __init__(self, parent=None):
        super().__init__(
            EntityFilterModel,
            common.AssetTab,
            parent=parent
        )



class TypeFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'File Types',
            'file_types',
            common.FileTab,
            parent=parent
        )

        common.signals.assetActivated.connect(self.reset_data)
        common.signals.taskFolderChanged.connect(self.reset_data)


class TypeFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available file types

    """
    def __init__(self, parent=None):
        super().__init__(
            TypeFilterModel,
            common.FileTab,
            parent=parent
        )