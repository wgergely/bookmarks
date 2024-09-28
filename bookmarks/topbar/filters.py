""""""
import weakref

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import log
from .. import ui

show_all_label = 'Show All'
hide_all_label = 'Hide All'

class BaseFilterModel(ui.AbstractListModel):
    row_size = QtCore.QSize(1, common.Size.RowHeight(0.8))

    def __init__(self, section_name_label, data_source, tab_index, icon, parent=None):
        self.tab_index = tab_index

        self.icon = icon
        self.section_name_label = section_name_label
        self.data_source = data_source

        super().__init__(parent=parent)

        common.signals.internalDataReady.connect(self.on_internal_data_ready)
        common.signals.bookmarksChanged.connect(self.reset_data)
        common.signals.bookmarkItemActivated.connect(self.reset_data)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        return super().data(index, role)

    @QtCore.Slot(weakref.ref)
    def on_internal_data_ready(self, ref):
        if not ref():
            return

        source_model = common.source_model(self.tab_index)
        data = common.get_data(
            source_model.source_path(), source_model.task(), source_model.data_type()
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

        p = source_model.source_path()
        k = source_model.task()
        t = source_model.data_type()
        data = common.get_data(p, k, t)

        if not hasattr(data, self.data_source):
            log.error(f'No {self.data_source} found in data!')
            return
        if not getattr(data, self.data_source):
            return

        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: show_all_label,
            QtCore.Qt.DecorationRole: ui.get_icon(
                'archivedVisible', color=common.Color.Green()),
            QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.Size.RowHeight(0.66)),
        }

        for v in sorted(getattr(data, self.data_source)):
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: v,
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.StatusTipRole: v,
                QtCore.Qt.AccessibleDescriptionRole: v,
                QtCore.Qt.WhatsThisRole: v,
                QtCore.Qt.ToolTipRole: v,
            }


class BaseFilterButton(QtWidgets.QComboBox):
    """The combo box used to set a text filter based on the available ShotGrid task names.

    """

    def __init__(self, model_cls, tab_index, parent=None):
        super().__init__(parent=parent)

        self.tab_index = tab_index

        view = QtWidgets.QListView(parent=self)
        view.setSpacing(0)

        self.setView(view)
        self.setModel(model_cls(parent=self))

        self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.setFixedHeight(common.Size.Margin())
        self.setMinimumWidth(common.Size.Margin(3.0))
        self.setMaxVisibleItems(48)

        self.view().setMinimumWidth(common.Size.DefaultWidth(0.33))

        common.signals.internalDataReady.connect(self.update_visibility)
        common.signals.updateTopBarButtons.connect(self.update_visibility)

        common.model(self.tab_index).filterTextChanged.connect(self.select_text)
        common.signals.internalDataReady.connect(self.select_text)

        self.textActivated.connect(self.update_filter_text)
        self.model().modelReset.connect(self.select_text)


    @QtCore.Slot(str)
    def update_filter_text(self, text):
        """Update the filter text.

        Args:
            text (str): The text to set as the filter text.

        """
        if text == show_all_label:
            text = ''
        else:
            text = f'"{text.lower().strip()}"'

        common.model(self.tab_index).set_filter_text(text)

    @QtCore.Slot()
    def update_visibility(self, *args, **kwargs):
        """Update the visibility of the widget.

        """
        if not common.current_tab() == self.tab_index:
            self.setHidden(True)
            return

        source_model = common.source_model(self.tab_index)
        p = source_model.source_path()
        k = source_model.task()
        t = source_model.data_type()
        data = common.get_data(p, k, t)
        if not data:
            self.setHidden(True)
            return

        if not self.model()._data:
            self.setHidden(True)
            return

        self.setHidden(False)

    @QtCore.Slot()
    def select_text(self, *args, **kwargs):
        """Update the filter text.

        """
        self.setCurrentIndex(0)

        _text = common.model(self.tab_index).filter_text()
        _text = _text.lower().strip() if _text else ''

        if not _text:
            self.setCurrentIndex(0)
            return

        for i in range(self.count()):
            text = self.itemText(i)
            if not text:
                continue

            text = text.lower().strip()
            if text == show_all_label:
                continue
            if _text == text:
                self.setCurrentIndex(i)
                return

            if _text == f'"{text}"':
                self.setCurrentIndex(i)
                return
        self.setCurrentIndex(0)


class TaskFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'Tasks', 'sg_task_names', common.AssetTab, 'sg', parent=parent
        )


class TaskFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available ShotGrid task names.

    """

    def __init__(self, parent=None):
        super().__init__(
            TaskFilterModel, common.AssetTab, parent=parent
        )


class EntityFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'Assets', 'sg_names', common.AssetTab, 'sg', parent=parent
        )


class EntityFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available ShotGrid task names.

    """

    def __init__(self, parent=None):
        super().__init__(
            EntityFilterModel, common.AssetTab, parent=parent
        )


class TypeFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'File Types', 'file_types', common.FileTab, 'file', parent=parent
        )

        common.signals.assetItemActivated.connect(self.reset_data)
        common.signals.taskFolderChanged.connect(self.reset_data)


class TypeFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available file types

    """

    def __init__(self, parent=None):
        super().__init__(
            TypeFilterModel, common.FileTab, parent=parent
        )


class SubdirFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'Folders', 'subdirectories', common.FileTab, 'folder', parent=parent
        )

        common.signals.assetItemActivated.connect(self.reset_data)
        common.signals.taskFolderChanged.connect(self.reset_data)

    def init_data(self, *args, **kwargs):
        super().init_data(*args, **kwargs)

        data = {}

        insert_idx = 3

        for idx, v in self._data.items():
            if idx == 1:
                data[idx] = v

                data[idx + insert_idx] = {
                    QtCore.Qt.DisplayRole: hide_all_label,
                    QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.Size.RowHeight(0.66)),
                    QtCore.Qt.DecorationRole: ui.get_icon(
                        'archivedHidden', color=common.Color.Red()),
                    QtCore.Qt.StatusTipRole: hide_all_label,
                    QtCore.Qt.AccessibleDescriptionRole: hide_all_label,
                    QtCore.Qt.WhatsThisRole: hide_all_label,
                    QtCore.Qt.ToolTipRole: hide_all_label,
                }
                continue

            if idx > insert_idx:
                idx += 1
            data[idx] = v

        self._data = data


class SubdirFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available file types

    """

    def __init__(self, parent=None):
        super().__init__(
            SubdirFilterModel, common.FileTab, parent=parent
        )

    @QtCore.Slot(str)
    def update_filter_text(self, text):
        """Update the filter text.

        Args:
            text (str): The text to set as the filter text.

        """
        if text == hide_all_label:
            filter_texts = []
            for i in range(self.count()):
                text = self.itemText(i)
                if not text:
                    continue
                if text == show_all_label:
                    continue
                if text == hide_all_label:
                    continue
                filter_texts.append(f'--"{text}"')
                common.model(self.tab_index).set_filter_text(' '.join(filter_texts))
        else:
            super().update_filter_text(text)



class JobsFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'Jobs', 'jobs', common.BookmarkTab, 'icon', parent=parent
        )

        common.signals.assetItemActivated.connect(self.reset_data)
        common.signals.taskFolderChanged.connect(self.reset_data)


class JobsFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available file types

    """

    def __init__(self, parent=None):
        super().__init__(
            JobsFilterModel, common.BookmarkTab, parent=parent
        )
