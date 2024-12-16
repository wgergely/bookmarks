"""Application item launcher module.

Each bookmark item can be configured with a list of app items, usually DCCs used
on the given production.

The default launcher item definition is found at: attr:`~bookmarks.application_launcher.DEFAULT_ITEM`. The item
launcher values are stored in the bookmark item database as an encoded JSON values.

:mod:`~bookmarks.application_launcher` contains the editor used to add and editor launcher items
via :mod:`bookmarks.editors.bookmark_properties`.

:mod:`~bookmarks.launcher.gallery` is the viewer, used to launch saved items. It's
accessible as a context menu in the item tabs.

"""

import functools

from PySide2 import QtCore, QtWidgets, QtGui

from . import actions
from . import common
from . import contextmenu
from . import database
from . import images
from . import ui

#: Default launcher item definition
DEFAULT_ITEM = {
    common.idx(reset=True, start=0): {
        'key': 'name',
        'placeholder': 'Name, for example, "Maya"',
        'widget': ui.LineEdit,
        'description': 'Enter the item\'s name, for example, Maya',
        'button': None,
    },
    common.idx(): {
        'key': 'path',
        'placeholder': 'Path, for example, "C:/maya/maya.exe"',
        'widget': ui.LineEdit,
        'description': 'Path to the executable.',
        'button': 'Pick',
    },
    common.idx(): {
        'key': 'thumbnail',
        'placeholder': 'Path to an image, for example, "C:/images/maya.png"',
        'widget': ui.LineEdit,
        'description': 'Path to an image file used to represent this item',
        'button': 'Pick',
    },
    common.idx(): {
        'key': 'hidden',
        'placeholder': None,
        'widget': functools.partial(QtWidgets.QCheckBox, 'Hidden'),
        'description': 'Hide the item from the application launcher.',
        'button': None,
    },
}

#: Default launcher item size
THUMBNAIL_EDITOR_SIZE = common.Size.Margin(5.0)


def close():
    """Opens the :class:`ApplicationLauncherWidget` editor.

    """
    if common.launcher_widget is None:
        return
    try:
        common.launcher_widget.close()
        common.launcher_widget.deleteLater()
    except:
        pass
    common.launcher_widget = None


def show():
    """Shows the :class:`ApplicationLauncherWidget` editor.

    """
    close()
    common.launcher_widget = ApplicationLauncherWidget()
    common.launcher_widget.open()
    return common.launcher_widget


class ApplicationLauncherItemEditor(QtWidgets.QDialog):
    """Widget used to edit launcher items associated with the current bookmark.

    """
    #: Signal emitted when a launcher item changes
    itemChanged = QtCore.Signal(dict)
    #: Signal emitted when a launcher item was added
    itemAdded = QtCore.Signal(dict)

    def __init__(self, data=None, parent=None):
        super().__init__(parent=parent)

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
            common.set_stylesheet(self)

        o = common.Size.Margin(0.5)

        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        grp = ui.get_group(
            margin=common.Size.Indicator(),
            vertical=False, parent=self
        )
        grp.layout().setAlignment(QtCore.Qt.AlignCenter)

        h = common.Size.Margin(2.0)

        self.thumbnail_viewer_widget = QtWidgets.QLabel(parent=grp)
        w = h * len(DEFAULT_ITEM) + (common.Size.Indicator(2.0))
        self.thumbnail_viewer_widget.setFixedSize(QtCore.QSize(w, w))
        grp.layout().addWidget(self.thumbnail_viewer_widget, 0)

        self.thumbnail_viewer_widget.setPixmap(images.rsc_pixmap('icon', color=None, size=w))

        _grp = ui.get_group(
            margin=common.Size.Indicator(), parent=grp
        )
        _grp.layout().setAlignment(QtCore.Qt.AlignCenter)

        for k in DEFAULT_ITEM:
            row = ui.add_row(None, height=None, parent=_grp)
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
        """Initializes the editor data with default data.

        """
        self.update_thumbnail_image(item['thumbnail'])

        for idx in DEFAULT_ITEM:
            k = DEFAULT_ITEM[idx]['key']

            if k not in item:
                continue

            if not hasattr(self, k + '_editor'):
                continue

            editor = getattr(self, k + '_editor')

            if isinstance(editor, QtWidgets.QCheckBox):
                editor.setChecked(item[k])
                continue

            if isinstance(editor, QtWidgets.QLineEdit):
                editor.setText(item[k])
                continue

    @QtCore.Slot(str)
    def update_thumbnail_image(self, path):
        """Updates the item's thumbnail image.

        Args:
            path (str): Path to an image file.

        """
        image = QtGui.QImage(path)
        if not path or image.isNull():
            h = common.Size.Margin(2.0)
            w = h * len(DEFAULT_ITEM) + (common.Size.Indicator(2.0))
            self.thumbnail_viewer_widget.setPixmap(images.rsc_pixmap('icon', None, w))
            return

        image.setDevicePixelRatio(common.pixel_ratio)
        image = images.resize_image(
            image, self.thumbnail_viewer_widget.width()
        )

        self.thumbnail_viewer_widget.setPixmap(QtGui.QPixmap.fromImage(image))

    @QtCore.Slot()
    @common.error
    @common.debug
    def action(self):
        """Add item action.

        """
        if not self.name_editor.text():
            raise RuntimeError('Must enter a name.')

        if not self.path_editor.text():
            raise RuntimeError('Must specify a path to an executable.')

        if not self.thumbnail_editor.text():
            if common.show_message(
                    'No thumbnail image specified.',
                    body=f'Are you sure you want continue without specifying a thumbnail image?',
                    buttons=[common.YesButton, common.CancelButton],
                    modal=True, ) == QtWidgets.QDialog.Rejected:
                return

        data = {}
        for idx in DEFAULT_ITEM:
            k = DEFAULT_ITEM[idx]['key']
            editor = getattr(self, k + '_editor')

            if isinstance(editor, QtWidgets.QCheckBox):
                v = editor.isChecked()
            elif isinstance(editor, QtWidgets.QLineEdit):
                v = editor.text()
                v = v if v else None
            else:
                v = None

            data[k] = v

        if self._data and self._data != data:
            self.itemChanged.emit(data)
        else:
            self.itemAdded.emit(data)

        self.done(QtWidgets.QDialog.Accepted)

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
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.RowHeight()
        )


class ApplicationLauncherListContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with the ThumbnailEditorWidget.

    """

    def setup(self):
        """Creates the context menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Add item...',
            'icon': ui.get_icon('add', color=common.Color.Green()),
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
            'icon': ui.get_icon('close', color=common.Color.Red()),
            'action': functools.partial(self.parent().remove_item, self.index)
        }


class ApplicationLauncherListWidget(ui.ListWidget):
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

    @QtCore.Slot()
    def emit_data_change(self):
        """Slot connected to the itemAdded signal.

        """
        self.dataUpdated.emit(self.data())

    def remove_item(self, item):
        """Remove launcher item action.

        """
        self.takeItem(self.row(item))
        self.emit_data_change()

    def contextMenuEvent(self, event):
        """Event handler.

        """
        item = self.itemAt(event.pos())
        menu = ApplicationLauncherListContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def edit_item(self, item):
        """Slot used top edit a widget item.

        """
        editor = ApplicationLauncherItemEditor(
            data=item.data(QtCore.Qt.UserRole),
            parent=self
        )
        editor.itemChanged.connect(
            lambda v: self.update_item(item, v)
        )
        editor.open()

    @QtCore.Slot()
    def add_new_item(self):
        """Add new item action.

        """
        editor = ApplicationLauncherItemEditor(
            data=None,
            parent=self
        )
        editor.itemAdded.connect(self.add_item)
        editor.itemAdded.connect(self.emit_data_change)
        editor.open()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    @QtCore.Slot(dict)
    def update_item(self, item, data):
        """Update item action.

        """
        item.setData(QtCore.Qt.DisplayRole, data['name'])
        item.setData(QtCore.Qt.UserRole, data)

        pixmap = QtGui.QPixmap(data['thumbnail'])
        pixmap.setDevicePixelRatio(common.pixel_ratio)
        icon = QtGui.QIcon(pixmap)
        item.setData(QtCore.Qt.DecorationRole, icon)

        self.emit_data_change()

    def data(self):
        """Returns launcher item data.

        """
        v = {}
        for idx in range(self.count()):
            v[idx] = self.item(idx).data(QtCore.Qt.UserRole)
        return v

    def init_data(self, data):
        """Initialises the editor.

        """
        self.clear()

        # Sort the data by name
        data = {k: v for k, v in sorted(data.items(), key=lambda item: item[1]['name'])}

        for idx in data:
            self.add_item(data[idx])

    def add_item(self, data):
        """Adds a new launcher item to the editor.

        """
        item = QtWidgets.QListWidgetItem()

        size = QtCore.QSize(1, common.Size.RowHeight())
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
        """Returns the launcher item data.

        """
        return self.data()

    def setValue(self, v):
        """Sets the launcher item data.

        """
        self.init_data(v)


class ApplicationLauncherWidget(ui.GalleryWidget):
    """A generic gallery widget used to let the user pick an item.

    """

    def __init__(self, parent=None):
        super().__init__(
            'Application Launcher',
            item_height=common.Size.RowHeight(4.0),
            parent=parent
        )

    def item_generator(self):
        """Yields the available launcher items stored in the bookmark item database.

        """
        server = common.active('server')
        job = common.active('job')
        root = common.active('root')

        if not all((server, job, root)):
            return

        db = database.get(server, job, root)
        v = db.value(
            db.source(),
            'applications',
            database.BookmarkTable
        )

        if not isinstance(v, dict) or not v:
            self.close()

            if common.show_message(
                    'The application launcher has not yet been configured.',
                    body='You can add new items in the current bookmark item\'s property editor. '
                         'Do you want to open the editor now?',
                    buttons=[common.YesButton, common.NoButton],
                    modal=True,
            ) == QtWidgets.QDialog.Rejected:
                return
            actions.edit_bookmark()
            return

        for k in sorted(v, key=lambda idx: v[idx]['name']):
            yield v[k]

    def init_data(self):
        """Initializes data.

        """
        row = 0
        idx = 0

        for v in self.item_generator():
            if 'name' not in v or not v['name']:
                continue
            label = v['name']

            if 'path' not in v or not v['path']:
                continue
            path = v['path']

            if not QtCore.QFileInfo(path).exists():
                continue

            if 'thumbnail' not in v or not v['thumbnail']:
                thumbnail = images.rsc_pixmap(
                    'icon',
                    None,
                    None,
                    get_path=True,
                )
            else:
                thumbnail = v['thumbnail']
            if 'hidden' not in v or not v['hidden']:
                is_hidden = False
            else:
                is_hidden = v['hidden']

            if is_hidden:
                continue

            item = ui.GalleryItem(
                label, path, thumbnail, height=self._item_height, parent=self
            )

            column = idx % self.columns
            if column == 0:
                row += 1

            self.scroll_area.widget().layout().addWidget(item, row, column)
            item.clicked.connect(self.itemSelected)
            item.clicked.connect(self.close)

            idx += 1
