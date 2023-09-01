"""The view and model used to display task folder items.

Folders found in an asset's root are referred to as `task folders`. Bookmarks
generally expects them to be associated with a task or data-type e.g. ``render``,
``comp``, ``textures``, etc.

Some default task-folders are defined by :mod:`bookmarks.tokens.tokens`.

"""
import functools
import os

from PySide2 import QtWidgets, QtGui, QtCore

from . import delegate
from . import models
from . import views
from .. import common
from .. import contextmenu
from .. import images
from .. import log
from ..tokens import tokens


class TaskItemContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with :class:`TaskItemView`.

    """

    @common.debug
    @common.error
    def setup(self):
        """Creates the context menu.

        """
        self.reveal_item_menu()
        self.copy_menu()
        self.separator()
        self.toggle_item_flags_menu()
        self.sort_menu()
        self.list_filter_menu()
        self.separator()
        self.refresh_menu()


class TaskItemViewDelegate(delegate.ItemDelegate):
    """Delegate used to paint :class:`TaskItemView`.
    
    """

    def paint(self, painter, option, index):
        """The main paint method.

        """
        args = self.get_paint_arguments(painter, option, index)
        self.paint_background(*args)
        self.paint_name(*args)

    def get_description_rect(self, *args, **kwargs):
        """Get description rectangle.

        """
        return QtCore.QRect()

    def get_text_segments(self, *args, **kwargs):
        """Get text segments.

        """
        return []

    @delegate.save_painter
    def paint_background(self, *args):
        """Paints the background.

        """
        rectangles, painter, option, index, selected, focused, active, archived, \
            favourite, hover, font, metrics, cursor_position = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Set rect with separator
        rect = QtCore.QRect(option.rect)
        rect.setHeight(rect.height() - common.size(common.size_separator))
        rect.setLeft(common.size(common.size_indicator))

        if index.data(QtCore.Qt.DisplayRole) == common.active('task'):
            o = common.size(common.size_separator)
            _rect = rect.adjusted(o, o, -o, -o)

            o = common.size(common.size_indicator) * 2
            painter.setOpacity(0.66)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.color(common.color_green))
            painter.drawRoundedRect(_rect, o, o)

            painter.setOpacity(1.0)
            pen = QtGui.QPen(common.color(common.color_green))
            pen.setWidth(common.size(common.size_separator) * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(_rect, o, o)
            return

        painter.setOpacity(0.9)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(common.color(common.color_separator))
        painter.drawRect(option.rect)
        color = common.color(common.color_dark_background)
        painter.setBrush(color)
        painter.drawRect(rect)

        if hover or selected:
            painter.setOpacity(0.2)
            color = common.color(common.color_light_background)
            painter.setBrush(color)
            painter.drawRect(rect)

    @delegate.save_painter
    def paint_name(self, *args):
        """Paints the name and the number of files available for the given
        task item.

        """
        rectangles, painter, option, index, selected, focused, active, archived, \
            favourite, hover, font, metrics, cursor_position = args
        if not index.data(QtCore.Qt.DisplayRole):
            return

        active = index.data(QtCore.Qt.DisplayRole) == common.active('task')

        if index.data(common.NoteCountRole):
            color = common.color(
                common.color_selected_text
            ) if hover else common.color(common.color_text)
        else:
            color = common.color(common.color_text) if hover else common.color(
                common.color_light_background
            )
        color = common.color(common.color_selected_text) if active else color
        color = common.color(common.color_selected_text) if selected else color

        font = common.font_db.bold_font(
            common.size(common.size_font_medium)
        )[0]

        o = common.size(common.size_margin)
        rect = QtCore.QRect(option.rect)

        if index.data(common.NoteCountRole):
            pixmap = images.rsc_pixmap(
                'folder', common.color(common.color_separator), o
            )
        else:
            pixmap = images.rsc_pixmap(
                'folder', common.color(common.color_dark_background), o
            )

        _rect = QtCore.QRect(0, 0, o, o)
        _rect.moveCenter(option.rect.center())
        _rect.moveLeft(
            option.rect.left() + ((o + common.size(common.size_indicator)) * 0.5)
        )
        painter.drawPixmap(_rect, pixmap, pixmap.rect())

        rect = rect.marginsRemoved(QtCore.QMargins(o * 2, 0, o, 0))

        text = index.data(QtCore.Qt.DisplayRole)
        width = common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            color
        )
        rect.setLeft(rect.left() + width)

        items = []

        if index.data(QtCore.Qt.ToolTipRole):
            color = common.color(
                common.color_selected_text
            ) if active else common.color(common.color_text)
            color = common.color(common.color_selected_text) if hover else color
            color = common.color(common.color_selected_text) if selected else color
            items.append((index.data(QtCore.Qt.ToolTipRole), color))

        for idx, val in enumerate(items):
            text, color = val
            if idx == 0:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
            else:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight

            width = common.draw_aliased_text(
                painter,
                common.font_db.medium_font(common.size(common.size_font_small))[0],
                rect,
                '    ｜    ', align, common.color(common.color_separator)
            )
            rect.setLeft(rect.left() + width)

            width = common.draw_aliased_text(
                painter,
                common.font_db.bold_font(
                    common.size(common.size_font_medium)
                )[0],
                rect,
                text,
                align,
                color
            )
            rect.setLeft(rect.left() + width)

    def sizeHint(self, option, index):
        """Size hint.

        """
        return self.parent().model().sourceModel().row_size


class TaskItemModel(models.ItemModel):
    """Task folder item model used to get task folders of an asset item.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        common.signals.taskFolderChanged.connect(self.reset_data)

    def source_path(self):
        """The model's source path.

        """
        return common.active('asset', args=True)

    def data_type(self):
        """The model's data type.

        """
        return common.FileItem

    def item_generator(self, path):
        try:
            it = os.scandir(path)
        except OSError as e:
            log.error(e)
            return

        # Get folders from the root of the bookmark item
        for entry in it:
            if self._interrupt_requested:
                return
            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue

            yield entry

    @common.status_bar_message('Loading task folders...')
    @models.initdata
    @common.error
    @common.debug
    def init_data(self):
        """Collects the data needed to populate the task item model.

        """
        p = self.source_path()
        k = self.task()
        t = self.data_type()

        if not p or not all(p) or not k or t is None:
            return

        data = common.get_data(p, k, t)
        source = '/'.join(p)

        flags = (
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled
        )

        source_path = self.source_path()
        if not source_path or not all(source_path):
            return
        _source_path = '/'.join(source_path)

        config = tokens.get(*source_path[0:3])

        for entry in self.item_generator(source):
            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue

            path = entry.path.replace('\\', '/')

            idx = len(data)
            description = config.get_description(entry.name)

            data[idx] = common.DataDict(
                {
                    QtCore.Qt.DisplayRole: entry.name,
                    QtCore.Qt.EditRole: entry.name,
                    common.PathRole: path,
                    QtCore.Qt.SizeHintRole: self.row_size,
                    #
                    QtCore.Qt.StatusTipRole: description,
                    QtCore.Qt.AccessibleDescriptionRole: description,
                    QtCore.Qt.WhatsThisRole: description,
                    QtCore.Qt.ToolTipRole: description,
                    #
                    common.QueueRole: self.queues,
                    common.DataTypeRole: common.FileItem,
                    common.ItemTabRole: common.TaskTab,
                    #
                    common.EntryRole: [entry, ],
                    common.FlagsRole: flags,
                    common.ParentPathRole: source_path,
                    common.DescriptionRole: description,
                    common.NoteCountRole: self.file_count(path),
                    common.FileDetailsRole: '',
                    common.SequenceRole: None,
                    common.FramesRole: [],
                    common.StartPathRole: None,
                    common.EndPathRole: None,
                    #
                    common.FileInfoLoaded: False,
                    common.ThumbnailLoaded: True,
                    #
                    common.SortByNameRole: entry.name.lower(),
                    common.SortByLastModifiedRole: entry.name.lower(),
                    common.SortBySizeRole: entry.name.lower(),
                    common.SortByTypeRole: entry.name.lower(),
                    #
                    common.IdRole: idx,
                    #
                    common.SGLinkedRole: False,
                }
            )

    @common.error
    @common.debug
    @QtCore.Slot()
    def reset_data(self, *args, force=False, emit_active=True):
        """Force model data reset every time.

        """
        return super().reset_data(force=True, emit_active=emit_active)

    def default_row_size(self):
        """Returns the default item size.

        """
        return QtCore.QSize(1, common.size(common.size_row_height) * 1.2)

    def filter_setting_dict_key(self):
        """The custom dictionary key used to save filter settings to the user settings
        file.

        """
        return 'task'

    def file_count(self, source):
        """Counts the number of file items the current task folder has.

        """
        count = 0
        for _ in self.item_generator(source):
            count += 1
            if count > 9:
                break
        return count


class TaskItemView(views.ThreadedItemView):
    """The view responsible for displaying the available data-keys.

    """
    Delegate = TaskItemViewDelegate
    ContextMenu = TaskItemContextMenu

    queues = ()

    def __init__(self, parent=None):
        super().__init__(
            icon='folder',
            parent=parent
        )
        self._context_menu_active = False
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.clicked.connect(self.item_clicked)

    def get_source_model(self):
        return TaskItemModel(parent=self)

    @QtCore.Slot(QtCore.QModelIndex)
    def item_clicked(self, index):
        """Slot connected to th clicked signal.

        """
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

    def key_enter(self):
        """Custom key action.

        """
        index = common.get_selected_index(self)
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
        """Slot connected called when the current tab has changed.

        """
        if idx != common.FileTab:
            self.hide()
            return
        self.model().sourceModel().reset_data()

    @QtCore.Slot(QtCore.QRect)
    def resize_widget(self, rect):
        """Slot used to resize the view to the given rect.

        """
        self.setGeometry(rect)

    def inline_icons_count(self):
        """Inline buttons count.

        """
        return 0

    def hideEvent(self, event):
        """Event handler.

        """
        common.widget(common.FileTab).verticalScrollBar().setHidden(False)
        common.widget().setFocus()
        common.signals.taskViewToggled.emit()
        return super().hideEvent(event)

    def showEvent(self, event):
        """Event handler.

        """
        common.widget(common.FileTab).verticalScrollBar().setHidden(True)
        self.select_active_item()
        self.setFocus()
        common.signals.taskViewToggled.emit()
        return super().showEvent(event)

    def select_active_item(self):
        """Select the current active item.

        """
        key = common.active('task')
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
        """Event filter handler.

        """
        if widget is not self:
            return super().eventFilter(widget, event)

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(widget)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.color(common.color_separator))
            painter.drawRect(widget.rect())
            painter.end()
            return super().eventFilter(widget, event)

        return super().eventFilter(widget, event)

    def keyPressEvent(self, event):
        """Key press event handler.

        """
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        """Event handler.

        """
        if self._context_menu_active:
            return
        if event.lostFocus():
            self.hide()

    def contextMenuEvent(self, event):
        """Event handler.

        """
        self._context_menu_active = True
        super().contextMenuEvent(event)
        self._context_menu_active = False

    def mousePressEvent(self, event):
        """Event handler.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.hide()
            return
        super().mousePressEvent(event)
