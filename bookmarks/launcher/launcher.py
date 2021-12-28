# -*- coding: utf-8 -*-
import os
import functools
from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import ui
from .. import images
from .. import contextmenu


DEFAULT_ITEM = {
    0: {
        'key': 'name',
        'placeholder': 'Name, eg. "Maya"',
        'widget': ui.LineEdit,
        'description': 'Enter the item\'s name, eg. Maya',
        'button': None,
    },
    1: {
        'key': 'path',
        'placeholder': 'Path, eg. "C:/maya/maya.exe"',
        'widget': ui.LineEdit,
        'description': 'Path to the executable.',
        'button': 'Pick',
    },
    2: {
        'key': 'thumbnail',
        'placeholder': 'Path to an image, eg. "C:/images/maya.png"',
        'widget': ui.LineEdit,
        'description': 'Path to an image file used to represent this item',
        'button': 'Pick',
    },
}

THUMBNAIL_EDITOR_SIZE = common.size(common.WidthMargin) * 5


class LauncherItemEditor(QtWidgets.QDialog):
    """Widget used to edit launcher items associated with the current bookmark.

    """
    itemChanged = QtCore.Signal(dict)
    itemAdded = QtCore.Signal(dict)

    def __init__(self, data=None, parent=None):
        super(LauncherItemEditor, self).__init__(parent=parent)

        self.thumbnail_viewer_widget = None
        self.done_button = None
        self._data = data

        self.setWindowTitle('Edit Launcher Item')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._create_ui()
        self._connect_signals()

        if self._data:
            self.init_data(self._data)

    def _create_ui(self):
        if not self.parent():
            common.set_custom_stylesheet(self)

        o = common.size(common.WidthMargin) * 0.5

        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        grp = ui.get_group(margin=common.size(common.WidthIndicator),
                           vertical=False, parent=self)
        grp.layout().setAlignment(QtCore.Qt.AlignCenter)

        h = common.size(common.WidthMargin) * 2

        self.thumbnail_viewer_widget = QtWidgets.QLabel(parent=grp)
        w = h * len(DEFAULT_ITEM) + (common.size(common.WidthIndicator) * 2)
        self.thumbnail_viewer_widget.setFixedSize(QtCore.QSize(w, w))
        grp.layout().addWidget(self.thumbnail_viewer_widget, 0)

        _grp = ui.get_group(margin=common.size(
            common.WidthIndicator), parent=grp)
        _grp.layout().setAlignment(QtCore.Qt.AlignCenter)

        for k in DEFAULT_ITEM:
            row = ui.add_row(None, height=None,
                             padding=common.size(common.WidthIndicator), parent=_grp)
            editor = DEFAULT_ITEM[k]['widget']()
            editor.setFixedHeight(h)

            if hasattr(editor, 'placeholderText'):
                editor.setPlaceholderText(DEFAULT_ITEM[k]['placeholder'])

            editor.setToolTip(DEFAULT_ITEM[k]['description'])
            editor.setStatusTip(DEFAULT_ITEM[k]['description'])

            row.layout().addWidget(editor, 1)
            setattr(self, DEFAULT_ITEM[k]['key'] + '_editor', editor)

            if DEFAULT_ITEM[k]['button']:
                button = ui.PaintedButton(DEFAULT_ITEM[k]['button'])
                button.setFixedHeight(h * 0.8)
                row.layout().addWidget(button, 0)
                _k = DEFAULT_ITEM[k]['key'] + '_button_clicked'

                if hasattr(self, _k):
                    button.clicked.connect(getattr(self, _k))

        self.done_button = ui.PaintedButton('Done', parent=self)
        self.layout().addWidget(self.done_button, 1)

    def _connect_signals(self):
        self.done_button.clicked.connect(self.action)
        self.thumbnail_editor.textChanged.connect(self.update_thumbnail_image)

    @QtCore.Slot()
    def init_data(self, item):
        self.update_thumbnail_image(item['thumbnail'])

        for idx in DEFAULT_ITEM:
            k = DEFAULT_ITEM[idx]['key']
            editor = getattr(self, k + '_editor')
            editor.setText(item[k])

    @QtCore.Slot(str)
    def update_thumbnail_image(self, path):
        image = QtGui.QImage(path)
        if image.isNull():
            self.thumbnail_viewer_widget.setPixmap(QtGui.QPixmap())
            return

        image.setDevicePixelRatio(common.pixel_ratio)
        image = images.ImageCache.resize_image(
            image, self.thumbnail_viewer_widget.width())

        self.thumbnail_viewer_widget.setPixmap(QtGui.QPixmap.fromImage(image))

    @QtCore.Slot()
    @common.error
    @common.debug
    def action(self):
        if not self.name_editor.text():
            raise RuntimeError('Must enter a name.')

        if not self.path_editor.text():
            raise RuntimeError('Must specify a path to an executable.')

        if not self.thumbnail_editor.text():
            raise RuntimeError('Must specify thumbnail image path.')

        data = {}
        for idx in DEFAULT_ITEM:
            k = DEFAULT_ITEM[idx]['key']
            editor = getattr(self, k + '_editor')
            v = editor.text()
            data[k] = v

        if self._data and self._data != data:
            self.itemChanged.emit(data)
        else:
            self.itemAdded.emit(data)

        self.done(QtWidgets.QDialog.Accepted)

    @QtCore.Slot()
    def path_button_clicked(self):
        self._pick(self.path_editor, caption='Pick an Executable')

    @QtCore.Slot()
    def thumbnail_button_clicked(self):
        self._pick(
            self.thumbnail_editor,
            caption='Pick a Thumbnail',
            filter=images.get_oiio_namefilters(),
            dir=QtCore.QFileInfo(common.get_rsc(
                common.FormatResource)).filePath()
        )

    def _pick(self, editor, caption=None, filter=None, dir=None):
        _file = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption=caption,
            filter=filter,
            dir=dir
        )
        if not _file[0]:
            return None

        _file = _file[0]
        file_info = QtCore.QFileInfo(_file)
        if not file_info.exists():
            return None

        v = file_info.absoluteFilePath()
        editor.setText(v)
        return v

    def sizeHint(self):
        return QtCore.QSize(common.size(common.DefaultWidth), common.size(common.HeightRow))


class LauncherListContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with the ThumbnailEditorWidget.

    """

    def setup(self):
        self.menu[contextmenu.key()] = {
            'text': 'Add item...',
            'icon': ui.get_icon('add', color=common.color(common.GreenColor)),
            'action': self.parent().add_new_item
        }

        if not self.index:
            return

        self.menu[contextmenu.key()] = {
            'text': 'Edit item...',
            'action': functools.partial(self.parent().edit_item, self.index)
        }

        self.separator()

        self.menu[contextmenu.key()] = {
            'text': 'Remove item',
            'icon': ui.get_icon('close', color=common.color(common.RedColor)),
            'action': functools.partial(self.parent().remove_item, self.index)
        }


class LauncherListWidget(ui.ListWidget):
    """Widget used to edit launcher items associated with the current bookmark.

    """
    dataUpdated = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.itemActivated.connect(self.edit_item)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.overlay.hide()

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Minimum
        )

    def emit_data_change(self):
        self.dataUpdated.emit(self.data())

    def remove_item(self, item):
        self.takeItem(self.row(item))
        self.emit_data_change()

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = LauncherListContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def edit_item(self, item):
        editor = LauncherItemEditor(
            data=item.data(QtCore.Qt.UserRole),
            parent=self
        )
        editor.itemChanged.connect(
            lambda v: self.update_item(item, v))
        editor.open()

    @QtCore.Slot()
    def add_new_item(self):
        editor = LauncherItemEditor(
            data=None,
            parent=self
        )
        editor.itemAdded.connect(self.add_item)
        editor.itemAdded.connect(self.emit_data_change)
        editor.open()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    @QtCore.Slot(dict)
    def update_item(self, item, data):
        item.setData(QtCore.Qt.DisplayRole, data['name'])
        item.setData(QtCore.Qt.UserRole, data)

        pixmap = QtGui.QPixmap(data['thumbnail'])
        pixmap.setDevicePixelRatio(common.pixel_ratio)
        icon = QtGui.QIcon(pixmap)
        item.setData(QtCore.Qt.DecorationRole, icon)

        self.emit_data_change()

    def data(self):
        v = {}
        for idx in range(self.count()):
            v[idx] = self.item(idx).data(QtCore.Qt.UserRole)
        return v

    def init_data(self, data):
        self.clear()

        common.check_type(data, dict)

        for idx in data:
            self.add_item(data[idx])

    def add_item(self, data):
        item = QtWidgets.QListWidgetItem()

        size = QtCore.QSize(1, common.size(common.HeightRow))
        pixmap = QtGui.QPixmap(data['thumbnail'])
        pixmap.setDevicePixelRatio(common.pixel_ratio)
        icon = QtGui.QIcon(pixmap)
        item.setData(QtCore.Qt.DecorationRole, icon)

        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEnabled)
        item.setData(QtCore.Qt.DisplayRole, data['name'])
        item.setData(QtCore.Qt.UserRole, data)
        item.setData(QtCore.Qt.SizeHintRole, size)
        self.addItem(item)

    def value(self):
        return self.data()

    def setValue(self, v):
        self.init_data(v)
