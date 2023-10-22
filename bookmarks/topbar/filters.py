""""""
import weakref

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import log
from .. import ui


class BaseFilterModel(ui.AbstractListModel):

    def __init__(self, section_name_label, data_source, tab_index, icon, parent=None):
        self.tab_index = tab_index

        self.icon = icon
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

        data = common.get_data(
            source_model.source_path(), source_model.task(), source_model.data_type()
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
            QtCore.Qt.TextAlignmentRole: QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom,
        }

        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: '',
            common.FlagsRole: QtCore.Qt.NoItemFlags,
            QtCore.Qt.SizeHintRole:QtCore.QSize(1, common.size(common.size_separator)),
        }
        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: '',
            common.FlagsRole: QtCore.Qt.NoItemFlags,
            QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.size(common.size_separator)),
        }

        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: self.show_all_label,
            QtCore.Qt.DecorationRole: ui.get_icon('archivedVisible', color=common.color(common.color_green)),
            QtCore.Qt.SizeHintRole: self.row_size,
            QtCore.Qt.TextAlignmentRole: QtCore.Qt.AlignCenter,
        }

        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: '',
            common.FlagsRole: QtCore.Qt.NoItemFlags,
            QtCore.Qt.SizeHintRole:QtCore.QSize(1, common.size(common.size_separator)),
        }
        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: '',
            common.FlagsRole: QtCore.Qt.NoItemFlags,
            QtCore.Qt.SizeHintRole:QtCore.QSize(1, common.size(common.size_separator)),
        }

        icon = ui.get_icon(self.icon)

        for v in sorted(getattr(data, self.data_source)):
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: v,
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.DecorationRole: icon,
                QtCore.Qt.StatusTipRole: v,
                QtCore.Qt.AccessibleDescriptionRole: v,
                QtCore.Qt.WhatsThisRole: v,
                QtCore.Qt.ToolTipRole: v,
                QtCore.Qt.TextAlignmentRole: QtCore.Qt.AlignCenter,
            }


class BaseFilterButton(QtWidgets.QComboBox):
    """The combo box used to set a text filter based on the available ShotGrid task names.

    """

    def __init__(self, Model, tab_index, parent=None):
        super().__init__(parent=parent)

        self.tab_index = tab_index
        view = QtWidgets.QListView(parent=self)
        view.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.AdjustToContents
        )
        self.setView(view)
        self.setModel(Model())

        self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.setFixedHeight(common.size(common.size_margin))
        self.setMinimumWidth(common.size(common.size_margin) * 3)

        min_width = self.minimumSizeHint().width()
        self.view().setMinimumWidth(min_width * 3)

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
            'Assets', 'shotgun_names', common.AssetTab, 'sg', parent=parent
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

        common.signals.assetActivated.connect(self.reset_data)
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

        common.signals.assetActivated.connect(self.reset_data)
        common.signals.taskFolderChanged.connect(self.reset_data)

    def init_data(self, *args, **kwargs):
        super().init_data(*args, **kwargs)

        data = {}

        insert_idx = 3

        for idx, v in self._data.items():
            if idx == 1:
                data[idx] = v

                k = '- Hide Folders -'
                data[idx + insert_idx] = {
                    QtCore.Qt.DisplayRole: k,
                    QtCore.Qt.SizeHintRole: self.row_size,
                    QtCore.Qt.DecorationRole: ui.get_icon('archivedHidden', color=common.color(common.color_red)),
                    QtCore.Qt.StatusTipRole: k,
                    QtCore.Qt.AccessibleDescriptionRole: k,
                    QtCore.Qt.WhatsThisRole: k,
                    QtCore.Qt.ToolTipRole: k,
                    QtCore.Qt.TextAlignmentRole: QtCore.Qt.AlignCenter,
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
        if text == '- Hide Folders -':
            filter_texts = []
            for i in range(self.count()):
                text = self.itemText(i)
                if not text:
                    continue
                if text == self.model().show_all_label:
                    continue
                if text == self.model().section_name_label:
                    continue
                if text == '- Hide Folders -':
                    continue
                filter_texts.append(f'--"{text}"')
                common.model(self.tab_index).set_filter_text(' '.join(filter_texts))
        else:
            super().update_filter_text(text)
class ServersFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'Servers', 'servers', common.BookmarkTab, 'icon', parent=parent
        )

        common.signals.assetActivated.connect(self.reset_data)
        common.signals.taskFolderChanged.connect(self.reset_data)


class ServersFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available file types

    """

    def __init__(self, parent=None):
        super().__init__(
            ServersFilterModel, common.BookmarkTab, parent=parent
        )


class JobsFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'Jobs', 'jobs', common.BookmarkTab, 'icon', parent=parent
        )

        common.signals.assetActivated.connect(self.reset_data)
        common.signals.taskFolderChanged.connect(self.reset_data)


class JobsFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available file types

    """

    def __init__(self, parent=None):
        super().__init__(
            JobsFilterModel, common.BookmarkTab, parent=parent
        )


class RootsFilterModel(BaseFilterModel):

    def __init__(self, parent=None):
        super().__init__(
            'Bookmarks', 'roots', common.BookmarkTab, 'icon', parent=parent
        )

        common.signals.assetActivated.connect(self.reset_data)
        common.signals.taskFolderChanged.connect(self.reset_data)


class RootsFilterButton(BaseFilterButton):
    """The combo box used to set a text filter based on the available file types

    """

    def __init__(self, parent=None):
        super().__init__(
            RootsFilterModel, common.BookmarkTab, parent=parent
        )
