# -*- coding: utf-8 -*-
"""Defines the view and model used to display and pick subfolders found
in an asset's root.

Folders found in an asset's root are referred to as `task folders`. Bookmarks
generally expects them to be associated with a task or data-type eg. ``render``,
``comp``, ``textures``, etc.

Core task folders are defined by `asset_config.py`.

"""
import _scandir

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common
from .. import contextmenu
from .. import images
from .. import settings
from .. import actions

from ..threads import threads
from ..properties import asset_config

from . import base
from . import delegate


class TaskFolderContextMenu(contextmenu.BaseContextMenu):
    @common.debug
    @common.error
    def setup(self):
        self.title()
        self.reveal_item_menu()
        self.copy_menu()
        self.refresh_menu()


class TaskFolderWidgetDelegate(delegate.BaseDelegate):
    """The delegate used to paint the available subfolders inside the asset folder."""

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self.get_paint_arguments(painter, option, index)
        self.paint_background(*args)
        self.paint_name(*args)
        self.paint_selection_indicator(*args)

    def get_description_rect(self, *args, **kwargs):
        return QtCore.QRect()

    def get_text_segments(self, *args, **kwargs):
        return []

    @delegate.paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Set rect with separator
        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setHeight(rect.height() - common.ROW_SEPARATOR())
        rect.moveCenter(center)

        if index.data(QtCore.Qt.DisplayRole) == settings.active(settings.TaskKey):
            o = common.ROW_SEPARATOR()
            _rect = rect.adjusted(o, o, -o, -o)

            o = common.INDICATOR_WIDTH() * 2
            painter.setOpacity(0.66)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.GREEN)
            painter.drawRoundedRect(_rect, o, o)

            painter.setOpacity(1.0)
            pen = QtGui.QPen(common.GREEN)
            pen.setWidth(common.ROW_SEPARATOR() * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(_rect, o, o)
            return

        painter.setOpacity(0.9)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(common.SEPARATOR)
        painter.drawRect(option.rect)
        background = common.DARK_BG
        color = common.SELECTED_BG if selected or hover else background
        painter.setBrush(color)
        painter.drawRect(rect)

    @delegate.paintmethod
    def paint_name(self, *args):
        """Paints the name and the number of files available for the given data-key."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not index.data(QtCore.Qt.DisplayRole):
            return

        if index.data(common.TodoCountRole):
            color = common.SELECTED_TEXT if hover else common.TEXT
        else:
            color = common.TEXT if hover else common.SELECTED_BG
        color = common.SELECTED_TEXT if selected else color

        font = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0]

        o = common.MARGIN()
        rect = QtCore.QRect(option.rect)

        if index.data(common.TodoCountRole) and index.data(common.TodoCountRole) > 0:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'folder', common.SEPARATOR, o)
        else:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'folder', common.DARK_BG, o)

        _rect = QtCore.QRect(0, 0, o, o)
        _rect.moveCenter(option.rect.center())
        _rect.moveLeft(
            option.rect.left() + ((o + common.INDICATOR_WIDTH()) * 0.5))
        painter.drawPixmap(_rect, pixmap, pixmap.rect())

        rect = rect.marginsRemoved(QtCore.QMargins(o * 2, 0, o, 0))

        text = index.data(QtCore.Qt.DisplayRole)
        width = 0
        width = common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
        rect.setLeft(rect.left() + width)

        items = []
        # Adding an indicator for the number of items in the folder
        if index.data(common.TodoCountRole):
            if index.data(common.TodoCountRole) >= 999:
                text = u'999+ items'
            else:
                text = u'{} items'.format(
                    index.data(common.TodoCountRole))
            color = common.SELECTED_TEXT if selected else common.GREEN
            color = common.SELECTED_TEXT if hover else color
            items.append((text, color))
        else:
            color = common.TEXT if selected else common.BG
            color = common.TEXT if hover else color
            items.append((u'(empty)', color))

        if index.data(QtCore.Qt.ToolTipRole):
            color = common.SELECTED_TEXT if selected else common.TEXT
            color = common.SELECTED_TEXT if hover else color
            items.append((index.data(QtCore.Qt.ToolTipRole), color))

        for idx, val in enumerate(items):
            text, color = val
            if idx == 0:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
            else:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight

            width = common.draw_aliased_text(
                painter, common.font_db.secondary_font(common.SMALL_FONT_SIZE())[0], rect, u'    |    ', align, common.SEPARATOR)
            rect.setLeft(rect.left() + width)

            width = common.draw_aliased_text(
                painter,
                common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
                rect,
                text,
                align,
                color
            )
            rect.setLeft(rect.left() + width)

    def sizeHint(self, option, index):
        """Returns the size of the TaskFolderWidgetDelegate items."""
        return index.data(QtCore.Qt.SizeHintRole)


class TaskFolderModel(base.BaseModel):
    """This model holds all the necessary data needed to display items to
    select for selecting the asset subfolders and/or bookmarks and assets.

    The model keeps track of the selections internally and is updated
    via the signals and slots.

    """
    taskFolderChangeRequested = QtCore.Signal()

    def __init__(self, parent=None):
        self._parent = parent
        self._monitor = None

        super(TaskFolderModel, self).__init__(parent=parent)

        self.modelDataResetRequested.connect(self.__resetdata__)
        common.signals.tabChanged.connect(self.check_task)

        self.init_monitor()

    @QtCore.Slot()
    def init_monitor(self):
        """We're using a QFileSystemWatcher to check keep track of any folder
        changes in the model's parent folder.

        If a new file/folder is added or changed we will trigger a model reset.

        """
        if not isinstance(self._monitor, QtCore.QFileSystemWatcher):
            self._monitor = QtCore.QFileSystemWatcher()
            self._monitor.fileChanged.connect(self.beginResetModel)
            self._monitor.fileChanged.connect(self.__resetdata__)
            self._monitor.directoryChanged.connect(self.beginResetModel)
            self._monitor.directoryChanged.connect(self.__resetdata__)

    @QtCore.Slot()
    def reset_monitor(self):
        if self._monitor is None:
            self._monitor = QtCore.QFileSystemWatcher()
        for f in self._monitor.files():
            self._monitor.removePath(f)
        for f in self._monitor.directories():
            self._monitor.removePath(f)

    def parent_path(self):
        """The model's parent folder path.

        Returns:
            tuple: A tuple of path segments.

        """
        return (
            settings.active(settings.ServerKey),
            settings.active(settings.JobKey),
            settings.active(settings.RootKey),
            settings.active(settings.AssetKey),
        )

    def data_type(self):
        return common.FileItem

    @base.initdata
    def __initdata__(self):
        """Bookmarks and assets are static. But files will be any number of """
        self.reset_monitor()

        flags = (
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsDropEnabled |
            QtCore.Qt.ItemIsEditable
        )
        data = self.model_data()

        parent_path = self.parent_path()
        if not parent_path or not all(parent_path):
            return
        _parent_path = u'/'.join(parent_path)

        # Thumbnail image
        default_thumbnail = images.ImageCache.get_rsc_pixmap(
            u'folder_sm',
            common.SECONDARY_TEXT,
            self.row_size().height()
        )
        default_thumbnail = default_thumbnail.toImage()

        config = asset_config.get(*parent_path[0:3])

        # Add the parent path
        self._monitor.addPath(_parent_path)

        entries = sorted(
            ([f for f in _scandir.scandir(_parent_path)]), key=lambda x: x.name)

        for entry in entries:
            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue

            idx = len(data)
            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: entry.name,
                QtCore.Qt.EditRole: entry.name,
                QtCore.Qt.StatusTipRole: entry.path.replace(u'\\', u'/'),
                QtCore.Qt.ToolTipRole: u'',
                QtCore.Qt.ToolTipRole: config.get_description(entry.name),
                QtCore.Qt.SizeHintRole: self.row_size(),
                #
                common.QueueRole: self.queues,
                common.DataTypeRole: common.FileItem,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: parent_path,
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: u'',
                common.SequenceRole: None,
                common.FramesRole: [],
                common.StartpathRole: None,
                common.EndpathRole: None,
                #
                common.FileInfoLoaded: False,
                common.ThumbnailLoaded: True,
                #
                common.TypeRole: common.FileItem,
                #
                common.SortByNameRole: entry.name.lower(),
                common.SortByLastModifiedRole: 0,
                common.SortBySizeRole: 0,
                common.SortByTypeRole: entry.name,
                #
                common.IdRole: idx,
                #
                common.ShotgunLinkedRole: False,
            })

    @QtCore.Slot()
    def check_task(self):
        """Slot used to verify the current task folder.

        """
        v = settings.active(settings.TaskKey)
        if not v:
            self.taskFolderChangeRequested.emit()
            return

        parent_path = self.parent_path() + (v,)
        if not all(parent_path):
            self.taskFolderChangeRequested.emit()
            return

        if not QtCore.QFileInfo(u'/'.join(parent_path)).exists():
            self.taskFolderChangeRequested.emit()

    def default_row_size(self):
        return QtCore.QSize(1, common.ROW_HEIGHT() * 1.2)

    def local_settings_key(self):
        return settings.TaskKey


class TaskFolderWidget(base.ThreadedBaseWidget):
    """The view responsonsible for displaying the available data-keys."""
    SourceModel = TaskFolderModel
    Delegate = TaskFolderWidgetDelegate
    ContextMenu = TaskFolderContextMenu

    queues = (threads.TaskFolderInfo,)

    def __init__(self, parent=None):
        super(TaskFolderWidget, self).__init__(
            icon='folder',
            parent=parent
        )
        self._context_menu_active = False
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def connect_signals(self):
        self.clicked.connect(self.activated)
        self.clicked.connect(self.hide)

        from .. import main
        widget = main.instance().stackedwidget.widget(common.FileTab)
        model = widget.model().sourceModel()

        self.clicked.connect(lambda x: model.taskFolderChanged.emit(
            x.data(QtCore.Qt.DisplayRole)))
        common.signals.tabChanged.connect(self.hide_widget)
        self.parent().resized.connect(self.resize_widget)

    def hide_widget(self, idx):
        if idx != common.FileTab:
            self.hide()

    def resize_widget(self, rect):
        self.setGeometry(rect)

    @QtCore.Slot(QtCore.QModelIndex)
    def activate(self, index):
        """Exists only for compatibility/consistency."""
        if not index.isValid():
            return
        self.activated.emit(index)

    def inline_icons_count(self):
        return 0

    def hideEvent(self, event):
        """TaskFolderWidget hide event."""
        if self.parent():
            self.parent().verticalScrollBar().setHidden(False)
        common.signals.taskViewToggled.emit()

    def showEvent(self, event):
        """TaskFolderWidget show event."""
        self.parent().verticalScrollBar().setHidden(True)
        self.select_active_item()
        self.setFocus()

    def select_active_item(self):
        key = settings.ACTIVE[settings.TaskKey]
        if not key:
            return
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            if key == index.data(QtCore.Qt.DisplayRole):
                self.selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                self.scrollTo(
                    index,
                    QtWidgets.QAbstractItemView.PositionAtCenter
                )
                break

    def eventFilter(self, widget, event):
        if widget == self.parent():
            return True
        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.SEPARATOR)
            painter.setOpacity(0.75)
            painter.drawRect(self.rect())
            painter.end()
            return True
        return False

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
        elif (event.key() == QtCore.Qt.Key_Return) or (event.key() == QtCore.Qt.Key_Enter):
            self.hide()
            return
        super(TaskFolderWidget, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if self._context_menu_active:
            return
        if event.lostFocus():
            self.hide()

    def contextMenuEvent(self, event):
        self._context_menu_active = True
        super(TaskFolderWidget, self).contextMenuEvent(event)
        self._context_menu_active = False

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.hide()
            return
        super(TaskFolderWidget, self).mousePressEvent(event)
