"""Widgets used by :class:`bookmarks.file_saver.file_saver.FileSaverWidget`.

"""

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import database
from .. import ui
from ..editor import base
from ..tokens import tokens

NoMode = 'invalid'
SceneMode = 'scene'
CacheMode = 'export'


class BookmarkItemModel(ui.AbstractListModel):
    """Bookmark item picker model.

    """

    def __init__(self, server, job, root, parent=None):
        self.server = server
        self.job = job
        self.root = root
        super().__init__(parent=parent)

    def init_data(self):
        """Initializes data.

        """
        k = '/'.join((self.server, self.job, self.root))
        if not k or not QtCore.QFileInfo(k).exists():
            return

        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: self.display_name(k),
            QtCore.Qt.DecorationRole: ui.get_icon(
                'check', color=common.color(common.color_green)
            ),
            QtCore.Qt.ForegroundRole: common.color(common.color_selected_text),
            QtCore.Qt.SizeHintRole: self.row_size,
            QtCore.Qt.StatusTipRole: k,
            QtCore.Qt.AccessibleDescriptionRole: k,
            QtCore.Qt.WhatsThisRole: k,
            QtCore.Qt.ToolTipRole: k,
        }


class BookmarkComboBox(QtWidgets.QComboBox):
    """Bookmark item picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        model = BookmarkItemModel(
            self.window().server,
            self.window().job,
            self.window().root,
        )
        self.setModel(model)


class AssetItemModel(ui.AbstractListModel):
    """Asset item picker model.

    """

    def __init__(self, server, job, root, asset, parent=None):
        self.server = server
        self.job = job
        self.root = root
        self.asset = asset
        super().__init__(parent=parent)

    def init_data(self):
        """Initializes data.

        """
        k = '/'.join((self.server, self.job, self.root, self.asset))
        if not k or not QtCore.QFileInfo(k).exists():
            return

        icon = ui.get_icon(
            'asset',
            size=common.size(common.size_margin) * 2,
            color=common.color(common.color_separator)
        )

        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: self.display_name(k),
            QtCore.Qt.DecorationRole: ui.get_icon(
                'check', color=common.color(common.color_green)
            ),
            QtCore.Qt.ForegroundRole: common.color(common.color_selected_text),
            QtCore.Qt.SizeHintRole: self.row_size,
            QtCore.Qt.StatusTipRole: k,
            QtCore.Qt.AccessibleDescriptionRole: k,
            QtCore.Qt.WhatsThisRole: k,
            QtCore.Qt.ToolTipRole: k,
        }

    def display_name(self, v):
        """Returns a customized display name.

        Args:
            v (str): The name of the asset item to modify.

        """
        k = '/'.join((self.server, self.job, self.root))
        return v.replace(k, '').strip('/').split('/', maxsplit=1)[0]


class AssetComboBox(QtWidgets.QComboBox):
    """Asset item picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        model = AssetItemModel(
            self.window().server,
            self.window().job,
            self.window().root,
            self.window().asset,
        )
        self.setModel(model)


class TaskComboBox(QtWidgets.QComboBox):
    """Task item picker.

    """

    def __init__(self, mode=SceneMode, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        model = TaskModel(
            self.window().server,
            self.window().job,
            self.window().root,
            self.window().asset,
            mode
        )
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

    def __init__(self, server, job, root, asset, mode, parent=None):
        self.server = server
        self.job = job
        self.root = root
        self.asset = asset
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

        k = '/'.join((self.server, self.job, self.root, self.asset))
        if not k or not QtCore.QFileInfo(k).exists():
            return

        # Load the available task folders from the active bookmark item's `tokens`.
        self._add_separator('Scenes')
        self._add_sub_folders(tokens.SceneFolder, 'icon_bw')
        self._add_separator('Caches')
        self._add_sub_folders(tokens.CacheFolder, 'file')
        self._add_separator('Custom (click \'Pick\' to add new)')

    def _add_sub_folders(self, token, icon):
        folder = tokens.get_folder(token)
        description = tokens.get_description(token)
        for sub_folder in tokens.get_subfolders(token):

            if common.active('task') == sub_folder:
                _icon = ui.get_icon(
                    'check',
                    color=common.color(common.color_green),
                    size=common.size(common.size_margin) * 2
                )
            else:
                _icon = ui.get_icon(
                    icon,
                    size=common.size(common.size_margin) * 2
                )

            v = f'{folder}/{sub_folder}'
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: self.display_name(v),
                QtCore.Qt.DecorationRole: _icon,
                QtCore.Qt.ForegroundRole: common.color(common.color_text),
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.StatusTipRole: description,
                QtCore.Qt.AccessibleDescriptionRole: description,
                QtCore.Qt.WhatsThisRole: description,
                QtCore.Qt.ToolTipRole: description,
                QtCore.Qt.UserRole: v,
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
            size=common.size(common.size_margin) * 2
        )

        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: self.display_name(path),
            QtCore.Qt.DecorationRole: _icon,
            QtCore.Qt.ForegroundRole: common.color(common.color_text),
            QtCore.Qt.SizeHintRole: self.row_size,
            QtCore.Qt.UserRole: path,
        }

        self.endResetModel()


class TemplateModel(ui.AbstractListModel):
    """Template item picker model.

    """

    def __init__(self, server, job, root, parent=None):
        self.server = server
        self.job = job
        self.root = root
        super().__init__(parent=parent)

    def init_data(self):
        """Initializes data.

        """
        args = (self.server, self.job, self.root)
        if not all(args):
            return

        config = tokens.get(*args)
        data = config.data()
        if not isinstance(data, dict):
            return

        template = common.settings.value('file_saver/template')
        for v in data[tokens.FileNameConfig].values():
            if template == v['name']:
                icon = ui.get_icon(
                    'check',
                    color=common.color(common.color_green),
                    size=common.size(common.size_margin) * 2
                )
            else:
                icon = ui.get_icon(
                    'file',
                    size=common.size(common.size_margin) * 2
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
        model = TemplateModel(
            self.window().server,
            self.window().job,
            self.window().root,
        )
        self.setModel(model)


class FormatModel(ui.AbstractListModel):
    """Format item picker model.

    """

    def __init__(self, server, job, root, parent=None):
        self.server = server
        self.job = job
        self.root = root
        super().__init__(parent=parent)

    def init_data(self):
        """Initializes data.

        """
        server = self.server
        job = self.job
        root = self.root

        if not all((server, job, root)):
            return

        config = tokens.get(server, job, root)
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
                        size=common.size(common.size_margin) * 2,
                        resource=common.FormatResource
                    )
                except:
                    icon = ui.get_icon(
                        'file',
                        size=common.size(common.size_margin) * 2
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
        model = FormatModel(
            self.window().server,
            self.window().job,
            self.window().root,
        )
        self.setModel(model)


class PrefixEditor(QtWidgets.QDialog):
    """A popup editor used to edit a bookmark prefix.

    """

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent=parent)
        self.ok_button = None
        self.editor = None

        self.server = server
        self.job = job
        self.root = root

        self._create_ui()
        self._connect_signals()
        self.init_data()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)

        self.setWindowTitle('Edit Prefix')

        self.editor = ui.LineEdit(parent=self)
        self.editor.setPlaceholderText('Enter a prefix, e.g. \'MYB\'')
        self.editor.setValidator(base.text_validator)
        self.setFocusProxy(self.editor)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.ok_button = ui.PaintedButton('Save', parent=self)

        self.layout().addWidget(self.editor, 1)
        self.layout().addWidget(self.ok_button, 0)

    def _connect_signals(self):
        self.ok_button.clicked.connect(lambda: self.done(QtWidgets.QDialog.Accepted))
        self.editor.returnPressed.connect(lambda: self.done(QtWidgets.QDialog.Accepted))
        self.accepted.connect(self.save_changes)

    def init_data(self):
        """Initializes data.

        """
        db = database.get_db(self.server, self.job, self.root)

        v = db.value(
            db.source(),
            'prefix',
            database.BookmarkTable
        )

        if not v:
            return

        self.editor.setText(v)

    def save_changes(self):
        """Saves changes.

        """
        if self.editor.text() == self.parent().prefix_editor.text():
            return

        self.parent().prefix_editor.setText(self.editor.text())

        db = database.get_db(
            self.parent().server,
            self.parent().job,
            self.parent().root
        )
        db.setValue(
            db.source(),
            'prefix',
            self.editor.text(),
            table=database.BookmarkTable
        )

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width) * 0.5,
            common.size(common.size_row_height)
        )
