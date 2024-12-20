"""Widgets used by :class:`bookmarks.file_saver.file_saver.FileSaverWidget`.

"""

from PySide2 import QtCore, QtWidgets

from .. import common, tokens
from .. import ui

NoMode = 'invalid'
SceneMode = 'scene'
CacheMode = 'export'


class TaskComboBox(QtWidgets.QComboBox):
    """Task item picker.

    """

    def __init__(self, mode=SceneMode, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        model = TaskModel(mode)
        self.setModel(model)

    def set_mode(self, mode):
        """Sets the mode of the task picker.

        """
        model = self.model()
        model.set_mode(mode)

        self.clear()
        model.init_data()


class TaskModel(ui.AbstractListModel):
    """Task item picker model.

    """

    def __init__(self, mode, parent=None):
        self._mode = mode
        super().__init__(parent=parent)

    def mode(self):
        """Returns the mode of the task picker.

        """
        return self._mode

    def set_mode(self, v):
        """Sets the mode of the task picker.

        """
        self._mode = v

    @common.error
    @common.debug
    def init_data(self):
        """Initializes data.

        """
        self._data = {}

        k = common.active('asset', path=True)
        if not k or not QtCore.QFileInfo(k).exists():
            return

        # Load the available task folders from the active bookmark item's `tokens`.
        self._add_separator('No Task')
        self.add_item(tokens.get_folder(tokens.SceneFolder))
        self._add_separator('Scene')
        self._add_sub_folders(tokens.SceneFolder, 'icon_bw')
        self._add_separator('Cache')
        self._add_sub_folders(tokens.CacheFolder, 'file')
        self._add_separator('Custom (click \'Pick\' to add new)')

    def _add_sub_folders(self, token, icon):
        folder = tokens.get_folder(token)
        description = tokens.get_description(token)
        for sub_folder in tokens.get_subfolders(token):

            if common.active('task') == sub_folder:
                _icon = ui.get_icon(
                    'check',
                    color=common.Color.Green(),
                    size=common.Size.Margin(2.0)
                )
            else:
                _icon = ui.get_icon(
                    icon,
                    size=common.Size.Margin(2.0)
                )

            v = f'{folder}/{sub_folder}'
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: self.display_name(v),
                QtCore.Qt.DecorationRole: _icon,
                QtCore.Qt.ForegroundRole: common.Color.Text(),
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.StatusTipRole: description,
                QtCore.Qt.AccessibleDescriptionRole: description,
                QtCore.Qt.WhatsThisRole: description,
                QtCore.Qt.ToolTipRole: description,
                QtCore.Qt.UserRole: f'{folder}/{sub_folder}',
            }

    def add_item(self, path):
        """Adds a new task item.

        Args:
            path (str): The path of the item to add.

        """
        self.modelAboutToBeReset.emit()
        self.beginResetModel()

        _icon = ui.get_icon(
            'folder',
            size=common.Size.Margin(2.0)
        )
        description = 'Custom task folder.'
        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: self.display_name(path),
            QtCore.Qt.DecorationRole: _icon,
            QtCore.Qt.ForegroundRole: common.Color.Text(),
            QtCore.Qt.SizeHintRole: self.row_size,
            QtCore.Qt.StatusTipRole: description,
            QtCore.Qt.AccessibleDescriptionRole: description,
            QtCore.Qt.WhatsThisRole: description,
            QtCore.Qt.ToolTipRole: description,
            QtCore.Qt.UserRole: path,
        }

        self.endResetModel()


class TemplateModel(ui.AbstractListModel):
    """Template item picker model.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def init_data(self):
        """Initializes data.

        """
        config = tokens.get(*common.active('root', args=True))
        data = config.data()
        if not isinstance(data, dict):
            return

        template = common.settings.value('file_saver/template')
        for v in data[tokens.FileNameConfig].values():
            if template == v['name']:
                icon = ui.get_icon(
                    'check',
                    color=common.Color.Green(),
                    size=common.Size.Margin(2.0)
                )
            else:
                icon = ui.get_icon(
                    'file',
                    size=common.Size.Margin(2.0)
                )

            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: v['name'],
                QtCore.Qt.DecorationRole: icon,
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.StatusTipRole: v['description'],
                QtCore.Qt.AccessibleDescriptionRole: v['description'],
                QtCore.Qt.WhatsThisRole: v['description'],
                QtCore.Qt.ToolTipRole: v['description'],
                QtCore.Qt.UserRole: v['value'],
            }


class TemplateComboBox(QtWidgets.QComboBox):
    """Template item picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        model = TemplateModel()
        self.setModel(model)


class FormatModel(ui.AbstractListModel):
    """Format item picker model.

    """

    def init_data(self):
        """Initializes data.

        """
        config = tokens.get(*common.active('root', args=True))
        data = config.data()
        if not isinstance(data, dict):
            return

        for v in data[tokens.FileFormatConfig].values():
            self._add_separator(v['name'])

            for ext in [f.lower().strip() for f in v['value'].split(',')]:
                try:
                    icon = ui.get_icon(
                        ext,
                        color=None,
                        size=common.Size.Margin(2.0),
                        resource=common.FormatResource
                    )
                except:
                    icon = ui.get_icon(
                        'file',
                        size=common.Size.Margin(2.0)
                    )

                self._data[len(self._data)] = {
                    QtCore.Qt.DisplayRole: ext,
                    QtCore.Qt.DecorationRole: icon,
                    QtCore.Qt.SizeHintRole: self.row_size,
                    QtCore.Qt.StatusTipRole: v['description'],
                    QtCore.Qt.AccessibleDescriptionRole: v['description'],
                    QtCore.Qt.WhatsThisRole: v['description'],
                    QtCore.Qt.ToolTipRole: v['description'],
                    QtCore.Qt.UserRole: ext,
                }


class FormatComboBox(QtWidgets.QComboBox):
    """Format item picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        model = FormatModel()
        self.setModel(model)


class FileNameInfo(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedHeight(common.Size.RowHeight(1.5))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
