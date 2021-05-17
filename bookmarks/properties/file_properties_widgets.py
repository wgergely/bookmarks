# -*- coding: utf-8 -*-
"""A list of widgets used by the `FilePropertiesWidget`.

"""

import functools
from PySide2 import QtCore, QtWidgets, QtGui

import _scandir

from .. import bookmark_db
from .. import common
from .. import ui
from .. import settings
from .. import images
from . import asset_config
from . import base

NoMode = u'invalid'
SceneMode = u'scene'
CacheMode = u'export'

ROW_SIZE = QtCore.QSize(1, common.ROW_HEIGHT())


def active_icon():
    """Checkmark icon.

    """
    return QtGui.QIcon(
        images.ImageCache.get_rsc_pixmap(
            u'check',
            common.GREEN,
            common.MARGIN() * 2
        )
    )


_keys = (
    settings.ServerKey,
    settings.JobKey,
    settings.RootKey,
    settings.AssetKey,
    settings.TaskKey,
)


def _active(n, join=True):
    v = [settings.ACTIVE[k] for k in _keys[0:n]]
    if not all(v):
        return None
    if join:
        return u'/'.join(v)
    return v


def active_bookmark():
    return _active(3)


def active_asset():
    return _active(4)


def active_task():
    return _active(5)


def init_data(func):
    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        keys = (
            settings.ServerKey,
            settings.JobKey,
            settings.RootKey,
            settings.AssetKey
        )
        args = [settings.ACTIVE[k] for k in keys]
        return func(self, *args)
    return func_wrapper


class BaseModel(QtCore.QAbstractListModel):
    """Generic base model used to store custom data.

    """

    def __init__(self, parent=None):
        super(BaseModel, self).__init__(parent=parent)
        self._data = {}
        self.beginResetModel()
        self.init_data()
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._data)

    def display_name(self, v):
        return v.split(u'/')[-1]

    @init_data
    def init_data(self, source, server, job, root):
        raise NotImplementedError(u'Must be overriden in subclass.')

    def index(self, row, column, parent=QtCore.QModelIndex()):
        return self.createIndex(row, 0, parent=parent)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        idx = index.row()
        if idx not in self._data:
            return None
        if role not in self._data[idx]:
            return None
        return self._data[idx][role]

    def flags(self, index):
        return (
            QtCore.Qt.ItemNeverHasChildren |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable
        )


class BookmarksModel(BaseModel):
    def __init__(self, parent=None):
        super(BookmarksModel, self).__init__(parent=parent)

    def init_data(self, load_all=False):
        k = active_bookmark()
        if not k or not QtCore.QFileInfo(k).exists():
            return

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'bookmark',
            common.SEPARATOR,
            common.MARGIN() * 2
        )
        icon = QtGui.QIcon(pixmap)

        if not load_all:
            self._data[0] = {
                QtCore.Qt.DisplayRole: self.display_name(k),
                QtCore.Qt.DecorationRole: active_icon(),
                QtCore.Qt.ForegroundRole: common.SELECTED_TEXT,
                QtCore.Qt.SizeHintRole: ROW_SIZE,
                QtCore.Qt.StatusTipRole: k,
                QtCore.Qt.AccessibleDescriptionRole: k,
                QtCore.Qt.WhatsThisRole: k,
                QtCore.Qt.ToolTipRole: k,
            }
            return

        if not common.BOOKMARKS:
            return

        for k in sorted(common.BOOKMARKS.keys()):
            active = active_bookmark() == k
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: self.display_name(k),
                QtCore.Qt.DecorationRole: active_icon() if active else icon,
                QtCore.Qt.ForegroundRole: common.SELECTED_TEXT if active else common.SECONDARY_TEXT,
                QtCore.Qt.SizeHintRole: ROW_SIZE,
                QtCore.Qt.StatusTipRole: k,
                QtCore.Qt.AccessibleDescriptionRole: k,
                QtCore.Qt.WhatsThisRole: k,
                QtCore.Qt.ToolTipRole: k,
            }


class BookmarkComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(BookmarkComboBox, self).__init__(parent=parent)
        self.setModel(BookmarksModel())


class AssetsModel(BaseModel):
    def init_data(self, load_all=False):
        k = active_asset()
        if not k or not QtCore.QFileInfo(k).exists():
            return

        pixmap = images.ImageCache.get_rsc_pixmap(
            'asset',
            common.SEPARATOR,
            common.MARGIN() * 2
        )
        icon = QtGui.QIcon(pixmap)

        if not load_all:
            self._data[0] = {
                QtCore.Qt.DisplayRole: self.display_name(k),
                QtCore.Qt.DecorationRole: active_icon(),
                QtCore.Qt.ForegroundRole: common.SELECTED_TEXT,
                QtCore.Qt.SizeHintRole: ROW_SIZE,
                QtCore.Qt.StatusTipRole: k,
                QtCore.Qt.AccessibleDescriptionRole: k,
                QtCore.Qt.WhatsThisRole: k,
                QtCore.Qt.ToolTipRole: k,
            }
            return

        # Let's get the identifier from the bookmark database
        db = bookmark_db.get_db(*_active(3, join=False))
        ASSET_IDENTIFIER = db.value(
            db.source(),
            u'identifier',
            table=bookmark_db.BookmarkTable
        )

        for entry in _scandir.scandir(db.source()):
            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue
            filepath = entry.path.replace(u'\\', u'/')

            if ASSET_IDENTIFIER:
                identifier = u'{}/{}'.format(
                    filepath, ASSET_IDENTIFIER)
                if not QtCore.QFileInfo(identifier).exists():
                    continue

            active = active_asset() == entry.name
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: self.display_name(filepath),
                QtCore.Qt.DecorationRole: active_icon() if active else icon,
                QtCore.Qt.ForegroundRole: common.SELECTED_TEXT if active else common.SECONDARY_TEXT,
                QtCore.Qt.SizeHintRole: ROW_SIZE,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.AccessibleDescriptionRole: filepath,
                QtCore.Qt.WhatsThisRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
            }


class AssetComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(AssetComboBox, self).__init__(parent=parent)
        self.setModel(AssetsModel())


class TaskComboBox(QtWidgets.QComboBox):
    def __init__(self, mode=SceneMode, parent=None):
        super(TaskComboBox, self).__init__(parent=parent)
        self.setModel(TaskModel(mode=mode))

    def set_mode(self, mode):
        model = self.model()
        model.set_mode(mode)

        self.clear()
        model.init_data()


class TaskModel(BaseModel):
    def __init__(self, mode, parent=None):
        self._mode = mode
        super(TaskModel, self).__init__(parent=parent)

    def mode(self):
        return self._mode

    def set_mode(self, v):
        self._mode = v

    def init_data(self):
        self._data = {}

        k = active_asset()
        if not k or not QtCore.QFileInfo(k).exists():
            return

        # Load the available task folders from the active bookmark item's
        # asset config.
        config = asset_config.get(*_active(3, join=False))
        data = config.data()
        if not isinstance(data, dict):
            return

        for v in sorted(data[asset_config.AssetFolderConfig].values(), key=lambda x: x['value']):
            if v['name'] != self._mode:
                continue
            if u'subfolders' not in v:
                continue

            current_folder = settings.instance().value(
                settings.FileSaverSection,
                settings.CurrentFolderKey
            )
            for _v in sorted(v['subfolders'].values(), key=lambda x: x['value']):
                if current_folder == _v['value']:
                    pixmap = images.ImageCache.get_rsc_pixmap(
                        u'check', common.GREEN, common.MARGIN() * 2)
                else:
                    pixmap = images.ImageCache.get_rsc_pixmap(
                        u'icon_bw', None, common.MARGIN() * 2)
                icon = QtGui.QIcon(pixmap)

                name = u'{}/{}'.format(v['value'], _v['value'])
                self._data[len(self._data)] = {
                    QtCore.Qt.DisplayRole: self.display_name(name),
                    QtCore.Qt.DecorationRole: icon,
                    QtCore.Qt.ForegroundRole: common.TEXT if v['name'] == 'scene' else common.SECONDARY_TEXT,
                    QtCore.Qt.SizeHintRole: ROW_SIZE,
                    QtCore.Qt.StatusTipRole: _v['description'],
                    QtCore.Qt.AccessibleDescriptionRole: _v['description'],
                    QtCore.Qt.WhatsThisRole: _v['description'],
                    QtCore.Qt.ToolTipRole: _v['description'],
                    QtCore.Qt.UserRole: name,
                }

            k = active_task()
            if not k:
                return
            name = k.replace(active_asset(), u'').strip(u'/')
            description = u'Active task folder'
            if not [f for f in self._data if self._data[f][QtCore.Qt.DisplayRole] == name]:
                self._data[len(self._data)] = {
                    QtCore.Qt.DisplayRole: self.display_name(name),
                    QtCore.Qt.DecorationRole: active_icon(),
                    QtCore.Qt.ForegroundRole: common.SELECTED_TEXT,
                    QtCore.Qt.SizeHintRole: ROW_SIZE,
                    QtCore.Qt.StatusTipRole: description,
                    QtCore.Qt.AccessibleDescriptionRole: description,
                    QtCore.Qt.WhatsThisRole: description,
                    QtCore.Qt.ToolTipRole: description,
                    QtCore.Qt.UserRole: name,
                }

    def add_item(self, path):
        self.modelAboutToBeReset.emit()

        self.beginResetModel()

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SEPARATOR, common.MARGIN() * 2)
        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: path.split(u'/').pop(),
            QtCore.Qt.DecorationRole: QtGui.QIcon(pixmap),
            QtCore.Qt.ForegroundRole: common.TEXT,
            QtCore.Qt.SizeHintRole: ROW_SIZE,
            QtCore.Qt.UserRole: path,
        }

        self.endResetModel()


class TemplateModel(BaseModel):
    def init_data(self):
        server = settings.ACTIVE[settings.ServerKey]
        job = settings.ACTIVE[settings.JobKey]
        root = settings.ACTIVE[settings.RootKey]

        if not all((server, job, root)):
            return

        config = asset_config.get(server, job, root)
        data = config.data()
        if not isinstance(data, dict):
            return

        template = settings.instance().value(
            settings.FileSaverSection,
            settings.CurrentTemplateKey
        )
        for v in data[asset_config.FileNameConfig].values():
            if template == v['name']:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'check', common.GREEN, common.MARGIN() * 2)
            else:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'file', common.SEPARATOR, common.MARGIN() * 2)
            icon = QtGui.QIcon(pixmap)

            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: v['name'],
                QtCore.Qt.DecorationRole: icon,
                QtCore.Qt.SizeHintRole: ROW_SIZE,
                QtCore.Qt.StatusTipRole: v['description'],
                QtCore.Qt.AccessibleDescriptionRole: v['description'],
                QtCore.Qt.WhatsThisRole: v['description'],
                QtCore.Qt.ToolTipRole: v['description'],
                QtCore.Qt.UserRole: v['value'],
            }


class TemplateComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(TemplateComboBox, self).__init__(parent=parent)
        self.setModel(TemplateModel())


class ExtensionModel(BaseModel):
    def init_data(self):
        server = settings.ACTIVE[settings.ServerKey]
        job = settings.ACTIVE[settings.JobKey]
        root = settings.ACTIVE[settings.RootKey]

        if not all((server, job, root)):
            return

        config = asset_config.get(server, job, root)
        data = config.data()
        if not isinstance(data, dict):
            return

        for v in data[asset_config.FileFormatConfig].values():
            if v['flag'] == asset_config.ImageFormat:
                continue
            for ext in [f.lower().strip() for f in v['value'].split(u',')]:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    ext, None, common.MARGIN() * 2, resource=images.FormatResource)
                if not pixmap or pixmap.isNull():
                    pixmap = images.ImageCache.get_rsc_pixmap(
                        u'placeholder', common.SEPARATOR, common.MARGIN() * 2)

                icon = QtGui.QIcon(pixmap)
                self._data[len(self._data)] = {
                    QtCore.Qt.DisplayRole: ext,
                    QtCore.Qt.DecorationRole: icon,
                    QtCore.Qt.SizeHintRole: ROW_SIZE,
                    QtCore.Qt.StatusTipRole: v['description'],
                    QtCore.Qt.AccessibleDescriptionRole: v['description'],
                    QtCore.Qt.WhatsThisRole: v['description'],
                    QtCore.Qt.ToolTipRole: v['description'],
                    QtCore.Qt.UserRole: ext,
                }


class ExtensionComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(ExtensionComboBox, self).__init__(parent=parent)
        self.setModel(ExtensionModel())


class FileNamePreview(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(FileNamePreview, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Fixed
        )
        self.setFixedHeight(common.ROW_HEIGHT())
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setText('Hello world')

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        o = common.ROW_SEPARATOR()
        rect = self.rect().adjusted(o, o, -o, -o)
        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)
        painter.setBrush(common.DARK_BG)

        o = common.INDICATOR_WIDTH()
        painter.drawRoundedRect(rect, o, o)
        painter.end()


class PrefixEditor(QtWidgets.QDialog):
    """A popup editor used to edit a bookmark prefix.

    """

    def __init__(self, parent=None):
        super(PrefixEditor, self).__init__(parent=parent)
        self._create_ui()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)

        self.editor = ui.LineEdit(parent=self)
        self.editor.setPlaceholderText(u'Enter a prefix, eg. \'MYB\'')
        self.editor.setValidator(base.textvalidator)
        self.setFocusProxy(self.editor)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.ok_button = ui.PaintedButton(u'Save')

        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))
        self.editor.returnPressed.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

        self.setWindowTitle(u'Edit Prefix')
        self.layout().addWidget(self.editor, 1)
        self.layout().addWidget(self.ok_button, 0)

        self.init_data()

    def init_data(self):
        self.parent().prefix_editor.setText(self.editor.text())

        p = self.parent()
        db = bookmark_db.get_db(p.server, p.job, p.root)

        v = db.value(
            db.source(),
            u'prefix',
            table=bookmark_db.BookmarkTable
        )

        if not v:
            return

        self.editor.setText(v)

    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            super(PrefixEditor, self).done(result)
            return

        p = self.parent()
        p.prefix_editor.setText(self.editor.text())

        db = bookmark_db.get_db(p.server, p.job, p.root)
        with db.connection():
            db.setValue(
                db.source(),
                u'prefix',
                self.editor.text(),
                table=bookmark_db.BookmarkTable
            )

        super(PrefixEditor, self).done(result)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 0.5, common.ROW_HEIGHT())


if __name__ == '__main__':
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])

    w = TemplateComboBox()
    w.show()
    app.exec_()
