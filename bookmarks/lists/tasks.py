# -*- coding: utf-8 -*-
"""The view and model used to display task folder items.

Hint:

    Folders found in an asset's root are referred to as `task folders`. Bookmarks
    generally expects them to be associated with a task or data-type eg. ``render``,
    ``comp``, ``textures``, etc.

    Some default task-folders are defined by :mod:`bookmarks.asset_config.asset_config`.

"""
import functools
import os

from PySide2 import QtWidgets, QtGui, QtCore

from . import basemodel
from . import basewidget
from . import delegate
from .. import common
from .. import contextmenu
from .. import images
from ..asset_config import asset_config
from ..threads import threads


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
        rect.setHeight(rect.height() - common.size(common.HeightSeparator))
        rect.setLeft(common.size(common.WidthIndicator))

        if index.data(QtCore.Qt.DisplayRole) == common.active(common.TaskKey):
            o = common.size(common.HeightSeparator)
            _rect = rect.adjusted(o, o, -o, -o)

            o = common.size(common.WidthIndicator) * 2
            painter.setOpacity(0.66)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.color(common.GreenColor))
            painter.drawRoundedRect(_rect, o, o)

            painter.setOpacity(1.0)
            pen = QtGui.QPen(common.color(common.GreenColor))
            pen.setWidth(common.size(common.HeightSeparator) * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(_rect, o, o)
            return

        painter.setOpacity(0.9)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(common.color(common.SeparatorColor))
        painter.drawRect(option.rect)
        color = common.color(common.BackgroundDarkColor)
        painter.setBrush(color)
        painter.drawRect(rect)

        if hover or selected:
            painter.setOpacity(0.2)
            color = common.color(common.BackgroundLightColor)
            painter.setBrush(color)
            painter.drawRect(rect)

    @delegate.paintmethod
    def paint_name(self, *args):
        """Paints the name and the number of files available for the given data-key."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not index.data(QtCore.Qt.DisplayRole):
            return

        active = index.data(QtCore.Qt.DisplayRole) == common.active(common.TaskKey)

        if index.data(common.TodoCountRole):
            color = common.color(
                common.TextSelectedColor) if hover else common.color(common.TextColor)
        else:
            color = common.color(common.TextColor) if hover else common.color(
                common.BackgroundLightColor)
        color = common.color(common.TextSelectedColor) if active else color
        color = common.color(common.TextSelectedColor) if selected else color

        font = common.font_db.primary_font(
            common.size(common.FontSizeMedium))[0]

        o = common.size(common.WidthMargin)
        rect = QtCore.QRect(option.rect)

        if index.data(common.TodoCountRole) and index.data(common.TodoCountRole) > 0:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'folder', common.color(common.SeparatorColor), o)
        else:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'folder', common.color(common.BackgroundDarkColor), o)

        _rect = QtCore.QRect(0, 0, o, o)
        _rect.moveCenter(option.rect.center())
        _rect.moveLeft(
            option.rect.left() + ((o + common.size(common.WidthIndicator)) * 0.5))
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
                text = '999+ items'
            else:
                text = f'{index.data(common.TodoCountRole)} items'
            color = common.color(common.TextSelectedColor) if selected else common.color(
                common.GreenColor)
            color = common.color(common.TextSelectedColor) if hover else color
            items.append((text, color))
        else:
            color = common.color(common.TextColor) if active else common.color(
                common.BackgroundColor)
            color = common.color(common.TextColor) if hover else color
            color = common.color(common.TextSelectedColor) if selected else color
            items.append(('(empty)', color))

        if index.data(QtCore.Qt.ToolTipRole):
            color = common.color(
                common.TextSelectedColor) if active else common.color(common.TextColor)
            color = common.color(common.TextSelectedColor) if hover else color
            color = common.color(common.TextSelectedColor) if selected else color
            items.append((index.data(QtCore.Qt.ToolTipRole), color))

        for idx, val in enumerate(items):
            text, color = val
            if idx == 0:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
            else:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight

            width = common.draw_aliased_text(
                painter, common.font_db.secondary_font(common.size(common.FontSizeSmall))[0], rect,
                '    |    ', align, common.color(common.SeparatorColor))
            rect.setLeft(rect.left() + width)

            width = common.draw_aliased_text(
                painter,
                common.font_db.primary_font(
                    common.size(common.FontSizeMedium))[0],
                rect,
                text,
                align,
                color
            )
            rect.setLeft(rect.left() + width)

    def sizeHint(self, option, index):
        return self.parent().model().sourceModel().row_size


class TaskFolderModel(basemodel.BaseModel):
    """This model holds all the necessary data needed to display items to
    select for selecting the asset subfolders and/or bookmarks and assets.

    The model keeps track of the selections internally and is updated
    via the signals and slots.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        common.signals.tabChanged.connect(self.reset_data)
        common.signals.taskFolderChanged.connect(self.reset_data)

    def source_path(self):
        return common.active(common.AssetKey, args=True)

    def data_type(self):
        return common.FileItem

    @basemodel.initdata
    def init_data(self):
        common.clear_watchdirs(common.TaskItemMonitor)

        flags = (
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsDropEnabled |
            QtCore.Qt.ItemIsEditable
        )
        data = self.model_data()
        source_path = self.source_path()
        if not source_path or not all(source_path):
            return
        _source_path = '/'.join(source_path)

        config = asset_config.get(*source_path[0:3])

        # Add the parent path
        _dirs = [_source_path]

        entries = sorted(
            ([f for f in os.scandir(_source_path)]), key=lambda x: x.name)

        for entry in entries:
            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue

            path = entry.path.replace('\\', '/')
            _dirs.append(path)

            idx = len(data)
            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: entry.name,
                QtCore.Qt.EditRole: entry.name,
                QtCore.Qt.StatusTipRole: path,
                QtCore.Qt.ToolTipRole: '',
                QtCore.Qt.ToolTipRole: config.get_description(entry.name),
                QtCore.Qt.SizeHintRole: self.row_size,
                #
                common.QueueRole: self.queues,
                common.DataTypeRole: common.FileItem,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: source_path,
                common.DescriptionRole: '',
                common.TodoCountRole: 0,
                common.FileDetailsRole: '',
                common.SequenceRole: None,
                common.FramesRole: [],
                common.StartPathRole: None,
                common.EndPathRole: None,
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
            common.set_watchdirs(common.TaskItemMonitor, _dirs)

    @QtCore.Slot()
    def reset_data(self):
        """Slot used to verify the current task folder.

        """
        v = common.active(common.TaskKey)
        if not v:
            return super().reset_data()

        p = common.active(common.TaskKey, args=True)
        if not p or not all(p):
            super().reset_data(force=True)
            return

        if not QtCore.QFileInfo('/'.join(p)).exists():
            return super().reset_data(force=True)

        return super().reset_data()

    def default_row_size(self):
        return QtCore.QSize(1, common.size(common.HeightRow) * 1.2)

    def user_settings_key(self):
        return common.TaskKey


class TaskFolderWidget(basewidget.ThreadedBaseWidget):
    """The view responsible for displaying the available data-keys."""
    SourceModel = TaskFolderModel
    Delegate = TaskFolderWidgetDelegate
    ContextMenu = TaskFolderContextMenu

    queues = (threads.TaskFolderInfo,)

    def __init__(self, parent=None):
        super().__init__(
            icon='folder',
            parent=parent
        )
        self._context_menu_active = False
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def connect_signals(self):
        self.clicked.connect(self.item_clicked)
        common.signals.tabChanged.connect(self.tab_changed)
        common.widget(common.FileTab).resized.connect(self.resize_widget)

    @QtCore.Slot(QtCore.QModelIndex)
    def item_clicked(self, index):
        if not index.isValid():
            return
        self.hide()
        self.activate(index)
        QtCore.QTimer.singleShot(
            1,
            functools.partial(
                common.signals.taskFolderChanged.emit,
                index.data(QtCore.Qt.DisplayRole)
            )
        )

    def action_on_enter_key(self):
        if not self.selectionModel().hasSelection():
            return
        index = self.selectionModel().currentIndex()

        if not index.isValid():
            return

        self.hide()
        self.activate(index)
        QtCore.QTimer.singleShot(
            1,
            functools.partial(
                common.signals.taskFolderChanged.emit,
                index.data(QtCore.Qt.DisplayRole)
            )
        )


    @QtCore.Slot(int)
    def tab_changed(self, idx):
        if idx != common.FileTab:
            self.hide()

    def resize_widget(self, rect):
        self.setGeometry(rect)

    def inline_icons_count(self):
        return 0

    def hideEvent(self, event):
        common.widget(common.FileTab).verticalScrollBar().setHidden(False)
        common.widget().setFocus()
        common.signals.taskViewToggled.emit()
        return super().hideEvent(event)

    def showEvent(self, event):
        common.widget(common.FileTab).verticalScrollBar().setHidden(True)
        self.select_active_item()
        self.setFocus()
        common.signals.taskViewToggled.emit()
        return super().showEvent(event)

    def select_active_item(self):
        key = common.active(common.TaskKey)
        if not key:
            return
        for n in range(self.model().rowCount()):
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
            painter.setBrush(common.color(common.SeparatorColor))
            painter.setOpacity(0.75)
            painter.drawRect(self.rect())
            painter.end()
            return True
        return False

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if self._context_menu_active:
            return
        if event.lostFocus():
            self.hide()

    def contextMenuEvent(self, event):
        self._context_menu_active = True
        super().contextMenuEvent(event)
        self._context_menu_active = False

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.hide()
            return
        super().mousePressEvent(event)
