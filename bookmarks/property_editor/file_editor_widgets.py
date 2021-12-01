# -*- coding: utf-8 -*-
"""A list of widgets used by the `FileBasePropertyEditor`.

"""
import os
import functools

from PySide2 import QtCore, QtWidgets, QtGui

from .. import database
from .. import common
from .. import ui

from .. import images
from ..asset_config import asset_config
from . import base

NoMode = 'invalid'
SceneMode = 'scene'
CacheMode = 'export'

ROW_SIZE = QtCore.QSize(1, common.size(common.HeightRow))


def init_data(func):
    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        return func(self, *common.active(common.AssetKey, args=True))
    return func_wrapper


class BaseModel(QtCore.QAbstractListModel):
    """Generic base model used to store custom data.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._data = {}

        self.beginResetModel()
        self.init_data()
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._data)

    def display_name(self, v):
        return v.split('/')[-1]

    @init_data
    def init_data(self, source, server, job, root):
        raise NotImplementedError('Must be overriden in subclass.')

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
        k = common.active(common.RootKey, path=True)
        if not k or not QtCore.QFileInfo(k).exists():
            return

        pixmap = images.ImageCache.get_rsc_pixmap(
            'bookmark',
            common.color(common.SeparatorColor),
            common.size(common.WidthMargin) * 2
        )
        icon = QtGui.QIcon(pixmap)

        if not load_all:
            self._data[0] = {
                QtCore.Qt.DisplayRole: self.display_name(k),
                QtCore.Qt.DecorationRole: ui.get_icon('check', color=common.color(common.GreenColor)),
                QtCore.Qt.ForegroundRole: common.color(common.TextSelectedColor),
                QtCore.Qt.SizeHintRole: ROW_SIZE,
                QtCore.Qt.StatusTipRole: k,
                QtCore.Qt.AccessibleDescriptionRole: k,
                QtCore.Qt.WhatsThisRole: k,
                QtCore.Qt.ToolTipRole: k,
            }
            return

        if not common.bookmarks:
            return

        for k in sorted(common.bookmarks.keys()):
            active = common.active(common.RootKey, path=True) == k
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: self.display_name(k),
                QtCore.Qt.DecorationRole: ui.get_icon('check', color=common.color(common.GreenColor)) if active else icon,
                QtCore.Qt.ForegroundRole: common.color(common.TextSelectedColor) if active else common.color(common.TextSecondaryColor),
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
        k = common.active(common.AssetKey, path=True)
        if not k or not QtCore.QFileInfo(k).exists():
            return

        pixmap = images.ImageCache.get_rsc_pixmap(
            'asset',
            common.color(common.SeparatorColor),
            common.size(common.WidthMargin) * 2
        )
        icon = QtGui.QIcon(pixmap)

        if not load_all:
            self._data[0] = {
                QtCore.Qt.DisplayRole: self.display_name(k),
                QtCore.Qt.DecorationRole: ui.get_icon('check', color=common.color(common.GreenColor)),
                QtCore.Qt.ForegroundRole: common.color(common.TextSelectedColor),
                QtCore.Qt.SizeHintRole: ROW_SIZE,
                QtCore.Qt.StatusTipRole: k,
                QtCore.Qt.AccessibleDescriptionRole: k,
                QtCore.Qt.WhatsThisRole: k,
                QtCore.Qt.ToolTipRole: k,
            }
            return

        # Let's get the identifier from the bookmark database
        db = database.get_db(*common.active(common.RootKey, args=True))
        ASSET_IDENTIFIER = db.value(
            db.source(),
            'identifier',
            table=database.BookmarkTable
        )

        for entry in os.scandir(db.source()):
            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue
            filepath = entry.path.replace('\\', '/')

            if ASSET_IDENTIFIER:
                identifier = '{}/{}'.format(
                    filepath, ASSET_IDENTIFIER)
                if not QtCore.QFileInfo(identifier).exists():
                    continue

            active = common.active(common.AssetKey, path=True) == entry.name
            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: self.display_name(filepath),
                QtCore.Qt.DecorationRole: ui.get_icon('check', color=common.color(common.GreenColor)) if active else icon,
                QtCore.Qt.ForegroundRole: common.color(common.TextSelectedColor) if active else common.color(common.TextSecondaryColor),
                QtCore.Qt.SizeHintRole: ROW_SIZE,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.AccessibleDescriptionRole: filepath,
                QtCore.Qt.WhatsThisRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
            }

    def display_name(self, v):
        k = common.active(common.RootKey, path=True)
        return v.replace(k, '').strip('/').split('/', maxsplit=1)[0]


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

        k = common.active(common.AssetKey, path=True)
        if not k or not QtCore.QFileInfo(k).exists():
            return

        # Load the available task folders from the active bookmark item's `asset_config`.
        config = asset_config.get(*common.active(common.RootKey, args=True))
        data = config.data()
        if not isinstance(data, dict):
            return

        current_folder = common.settings.value(
            common.CurrentUserPicksSection,
            'task'
        )

        for v in sorted(data[asset_config.AssetFolderConfig].values(), key=lambda x: x['value']):
            if v['name'] != self._mode:
                continue
            if 'subfolders' not in v:
                continue

            for _v in sorted(v['subfolders'].values(), key=lambda x: x['value']):
                if current_folder == _v['value']:
                    pixmap = images.ImageCache.get_rsc_pixmap(
                        'check', common.color(common.GreenColor), common.size(common.WidthMargin) * 2)
                else:
                    pixmap = images.ImageCache.get_rsc_pixmap(
                        'icon_bw', None, common.size(common.WidthMargin) * 2)
                icon = QtGui.QIcon(pixmap)

                name = '{}/{}'.format(v['value'], _v['value'])
                self._data[len(self._data)] = {
                    QtCore.Qt.DisplayRole: self.display_name(name),
                    QtCore.Qt.DecorationRole: icon,
                    QtCore.Qt.ForegroundRole: common.color(common.TextColor) if v['name'] == 'scene' else common.color(common.TextSecondaryColor),
                    QtCore.Qt.SizeHintRole: ROW_SIZE,
                    QtCore.Qt.StatusTipRole: _v['description'],
                    QtCore.Qt.AccessibleDescriptionRole: _v['description'],
                    QtCore.Qt.WhatsThisRole: _v['description'],
                    QtCore.Qt.ToolTipRole: _v['description'],
                    QtCore.Qt.UserRole: name,
                }

    def add_item(self, path):
        self.modelAboutToBeReset.emit()

        self.beginResetModel()

        pixmap = images.ImageCache.get_rsc_pixmap(
            'folder', common.color(common.SeparatorColor), common.size(common.WidthMargin) * 2)
        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: path.split('/').pop(),
            QtCore.Qt.DecorationRole: QtGui.QIcon(pixmap),
            QtCore.Qt.ForegroundRole: common.color(common.TextColor),
            QtCore.Qt.SizeHintRole: ROW_SIZE,
            QtCore.Qt.UserRole: path,
        }

        self.endResetModel()


class TemplateModel(BaseModel):
    def init_data(self):
        server = common.active(common.ServerKey)
        job = common.active(common.JobKey)
        root = common.active(common.RootKey)

        if not all((server, job, root)):
            return

        config = asset_config.get(server, job, root)
        data = config.data()
        if not isinstance(data, dict):
            return

        template = common.settings.value(
            common.FileSaverSection,
            common.CurrentTemplateKey
        )
        for v in data[asset_config.FileNameConfig].values():
            if template == v['name']:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    'check', common.color(common.GreenColor), common.size(common.WidthMargin) * 2)
            else:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    'file', common.color(common.SeparatorColor), common.size(common.WidthMargin) * 2)
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
        server = common.active(common.ServerKey)
        job = common.active(common.JobKey)
        root = common.active(common.RootKey)

        if not all((server, job, root)):
            return

        config = asset_config.get(server, job, root)
        data = config.data()
        if not isinstance(data, dict):
            return

        for v in data[asset_config.FileFormatConfig].values():
            if v['flag'] == asset_config.ImageFormat:
                continue
            for ext in [f.lower().strip() for f in v['value'].split(',')]:
                try:
                    pixmap = images.ImageCache.get_rsc_pixmap(
                        ext, None, common.size(common.WidthMargin) * 2, resource=common.FormatResource)
                except:
                    pixmap = images.ImageCache.get_rsc_pixmap(
                        'placeholder', common.color(common.SeparatorColor), common.size(common.WidthMargin) * 2)

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
        self.setFixedHeight(common.size(common.HeightRow))
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setText('Hello world')

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        o = common.size(common.HeightSeparator)
        rect = self.rect().adjusted(o, o, -o, -o)
        pen = QtGui.QPen(common.color(common.SeparatorColor))
        pen.setWidthF(common.size(common.HeightSeparator))
        painter.setPen(pen)
        painter.setBrush(common.color(common.BackgroundDarkColor))

        o = common.size(common.WidthIndicator)
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
        self.editor.setPlaceholderText('Enter a prefix, eg. \'MYB\'')
        self.editor.setValidator(base.textvalidator)
        self.setFocusProxy(self.editor)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.ok_button = ui.PaintedButton('Save')

        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))
        self.editor.returnPressed.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

        self.setWindowTitle('Edit Prefix')
        self.layout().addWidget(self.editor, 1)
        self.layout().addWidget(self.ok_button, 0)

        self.init_data()

    def init_data(self):
        self.parent().prefix_editor.setText(self.editor.text())

        p = self.parent()
        db = database.get_db(p.server, p.job, p.root)

        v = db.value(
            db.source(),
            'prefix',
            table=database.BookmarkTable
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

        db = database.get_db(p.server, p.job, p.root)
        with db.connection():
            db.setValue(
                db.source(),
                'prefix',
                self.editor.text(),
                table=database.BookmarkTable
            )

        super(PrefixEditor, self).done(result)

    def sizeHint(self):
        return QtCore.QSize(common.size(common.DefaultWidth) * 0.5, common.size(common.HeightRow))


if __name__ == '__main__':
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])

    w = TemplateComboBox()
    w.show()
    app.exec_()
