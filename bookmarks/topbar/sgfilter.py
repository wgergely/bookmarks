""""""
import weakref

from PySide2 import QtCore, QtGui, QtWidgets


from .. import common
from .. import ui


class BaseFilterModel(ui.AbstractListModel):

    def __init__(self, section_name_label, data_source, parent=None):

        self.show_all_label = ' - Show All -'
        self.section_name_label = section_name_label
        self.data_source = data_source

        super().__init__(parent=parent)

        common.signals.internalDataReady.connect(self.internal_data_ready)
        common.signals.bookmarksChanged.connect(self.reset_data)

    @QtCore.Slot(weakref.ref)
    def internal_data_ready(self, ref):
        if not ref():
            return

        source_model = common.source_model(common.AssetTab)
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

        source_model = common.source_model(common.AssetTab)

        data = common.get_data(
            source_model.source_path(),
            source_model.task(),
            source_model.data_type()
        )
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
    def __init__(self, Model, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView(parent=self))
        self.view().setMinimumWidth(int(common.size(common.size_width) * 0.66))
        self.setModel(Model())

        self.setFixedHeight(common.size(common.size_margin))
        self.setMinimumWidth(common.size(common.size_margin) * 6)

        common.signals.updateTopBarButtons.connect(lambda: self.setHidden(not common.current_tab() == common.AssetTab))
        common.model(common.AssetTab).filterTextChanged.connect(self.select_text)
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

        common.model(common.AssetTab).set_filter_text(text)

    @QtCore.Slot()
    def select_text(self, *args, **kwargs):
        """Update the filter text.

        """
        self.setCurrentIndex(-1)

        _text = common.model(common.AssetTab).filter_text()
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
            'ShotGrid Tasks',
            'sg_task_names',
            parent=parent
        )


class TaskFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available ShotGrid task names.

    """
    def __init__(self, parent=None):
        super().__init__(
            TaskFilterModel,
            parent=parent
        )


class EntityFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'ShotGrid Entities',
            'shotgun_names',
            parent=parent
        )


class EntityFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available ShotGrid task names.

    """
    def __init__(self, parent=None):
        super().__init__(
            EntityFilterModel,
            parent=parent
        )