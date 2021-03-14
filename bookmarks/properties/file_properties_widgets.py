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


def active_bookmark():
    """The active bookmark.

    """
    args = [settings.ACTIVE[k]
            for k in (settings.ServerKey, settings.JobKey, settings.RootKey)]
    if not all(args):
        return None
    return u'/'.join(args)


def init_data(func):
    """Wrappter for `init_data()`.

    """
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

    def init_data(self):
        bookmark = active_bookmark()
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'bookmark', common.SEPARATOR, common.MARGIN() * 2)
        icon = QtGui.QIcon(pixmap)

        if not common.BOOKMARKS:
            return

        for k in sorted(common.BOOKMARKS.keys()):
            active = bookmark == k
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: k,
                QtCore.Qt.DecorationRole: active_icon() if active else icon,
                QtCore.Qt.ForegroundRole: common.SELECTED_TEXT if active else common.SECONDARY_TEXT,
                QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.ROW_HEIGHT()),
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
    def __init__(self, parent=None):
        self._source = active_bookmark()
        super(AssetsModel, self).__init__(parent=parent)

    def init_data(self):
        bookmark = self._source
        if not bookmark:
            return

        server = settings.ACTIVE[settings.ServerKey]
        job = settings.ACTIVE[settings.JobKey]
        root = settings.ACTIVE[settings.RootKey]
        asset = settings.ACTIVE[settings.AssetKey]

        pixmap = images.ImageCache.get_rsc_pixmap(
            'asset', common.SEPARATOR, common.MARGIN() * 2)
        icon = QtGui.QIcon(pixmap)

        # Let's get the identifier from the bookmark database
        with bookmark_db.transactions(server, job, root) as db:
            ASSET_IDENTIFIER = db.value(
                bookmark, u'identifier', table=bookmark_db.BookmarkTable)

        for entry in _scandir.scandir(bookmark):
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

            active = asset == entry.name
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: entry.name,
                QtCore.Qt.DecorationRole: active_icon() if active else icon,
                QtCore.Qt.ForegroundRole: common.SELECTED_TEXT if active else common.SECONDARY_TEXT,
                QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.ROW_HEIGHT()),
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
        model._mode = mode

        self.clear()
        model.init_data()


class TaskModel(BaseModel):
    def __init__(self, mode, parent=None):
        self._mode = mode
        super(TaskModel, self).__init__(parent=parent)

    def init_data(self):
        self._data = {}

        server = settings.ACTIVE[settings.ServerKey]
        job = settings.ACTIVE[settings.JobKey]
        root = settings.ACTIVE[settings.RootKey]

        if not all((server, job, root)):
            return
        config = asset_config.get(server, job, root)
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
                        u'folder', common.SEPARATOR, common.MARGIN() * 2)
                icon = QtGui.QIcon(pixmap)

                self._data[len(self._data)] = {
                    QtCore.Qt.DisplayRole: _v['value'].upper(),
                    QtCore.Qt.DecorationRole: icon,
                    QtCore.Qt.ForegroundRole: common.TEXT if v['name'] == 'scene' else common.SECONDARY_TEXT,
                    QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.ROW_HEIGHT()),
                    QtCore.Qt.StatusTipRole: _v['description'],
                    QtCore.Qt.AccessibleDescriptionRole: _v['description'],
                    QtCore.Qt.WhatsThisRole: _v['description'],
                    QtCore.Qt.ToolTipRole: _v['description'],
                    QtCore.Qt.UserRole: u'{}/{}'.format(v['value'], _v['value']),
                }

    def add_item(self, path):
        self.modelAboutToBeReset.emit()
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SEPARATOR, common.MARGIN() * 2)
        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: path.split(u'/').pop().upper(),
            QtCore.Qt.DecorationRole: QtGui.QIcon(pixmap),
            QtCore.Qt.ForegroundRole: common.TEXT,
            QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.ROW_HEIGHT()),
            QtCore.Qt.UserRole: path,
        }
        self.modelReset.emit()


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
                QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.ROW_HEIGHT()),
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
                    QtCore.Qt.DisplayRole: ext.upper(),
                    QtCore.Qt.DecorationRole: icon,
                    QtCore.Qt.SizeHintRole: QtCore.QSize(1, common.ROW_HEIGHT()),
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
        args = (p.server, p.job, p.root)
        with bookmark_db.transactions(*args) as db:
            v = db.value(
                u'/'.join(args),
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
        args = (p.server, p.job, p.root)
        with bookmark_db.transactions(*args) as db:
            db.setValue(
                u'/'.join(args),
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
