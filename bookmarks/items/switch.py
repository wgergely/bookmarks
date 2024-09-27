"""The view and model used to display task folder items.

Folders found in an asset's root are referred to as `task folders`. Bookmarks
generally expects them to be associated with a task or data-type for example, ``render``,
``comp``, ``textures``, etc.

Some default task-folders are defined by :mod:`bookmarks.tokens.tokens`.

"""
import functools
import os
import weakref

from PySide2 import QtWidgets, QtGui, QtCore

from . import delegate
from . import models
from . import views
from .. import common
from .. import contextmenu
from .. import images
from .. import log
from .. import ui
from ..threads import threads


class SwitchItemsContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with :class:`TaskSwitchView`.

    """

    @common.debug
    @common.error
    def setup(self):
        """Creates the context menu.

        """
        self.reveal_item_menu()
        self.copy_menu()
        self.separator()
        self.refresh_menu()


class BaseSwitchView(views.ThreadedItemView):
    """The view responsible for displaying the available data-keys.

    """
    ContextMenu = SwitchItemsContextMenu
    queues = ()

    def __init__(self, tab_idx, parent=None):
        super().__init__(
            icon='folder',
            parent=parent
        )
        self.tab_idx = tab_idx

        self.filter_indicator_widget.setHidden(True)

        self._context_menu_active = False

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )

        # Shadow effect
        self.effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.effect.setBlurRadius(common.Size.Margin(2.0))
        self.effect.setXOffset(0)
        self.effect.setYOffset(0)
        self.effect.setColor(QtGui.QColor(0, 0, 0, 200))
        self.setGraphicsEffect(self.effect)

        self.clicked.connect(self.item_clicked)

    @QtCore.Slot(QtCore.QModelIndex)
    def item_clicked(self, index):
        """Slot connected to th clicked signal.

        """
        if not index.isValid():
            return
        self.hide()
        self.activate(index)
        self.emit_item_clicked(index)

    def emit_item_clicked(self, index):
        pass

    def key_enter(self):
        """Custom key action.

        """
        index = common.get_selected_index(self)
        self.item_clicked(index)

    @QtCore.Slot(int)
    def tab_changed(self, idx):
        """Slot connected called when the current tab has changed.

        """
        if idx != self.tab_idx:
            self.hide()
            return
        self.model().sourceModel().reset_data()

    @QtCore.Slot(QtCore.QRect)
    def resize_widget(self, rect):
        """Slot -> Resizes the view to the given rect.

        """
        o = common.Size.Margin()
        rect = rect.adjusted(o, 0, -o, -o)

        center = rect.center()
        max_width = common.Size.DefaultWidth()
        if rect.width() > max_width:
            rect.setWidth(max_width)
            rect.moveCenter(center)

        self.setGeometry(rect)

        top_left = common.widget(self.tab_idx).mapToGlobal(rect.topLeft())
        top_left.setY(top_left.y() - common.Size.Margin(2.0))
        self.move(top_left)

    def inline_icons_count(self):
        """Inline buttons count.

        """
        return 0

    def paint_hint(self, widget, event):
        return ''

    def paint_status_message(self, widget, event):
        return ''

    def hideEvent(self, event):
        """Event handler.

        """
        super().hideEvent(event)

        common.widget(self.tab_idx).verticalScrollBar().setHidden(False)
        common.widget(self.tab_idx).setFocus()
        common.signals.switchViewToggled.emit()

    def showEvent(self, event):
        """Event handler.

        """
        super().showEvent(event)

        common.widget(self.tab_idx).verticalScrollBar().setHidden(True)
        self.setFocus()
        self.resize_widget(common.widget(self.tab_idx).geometry())
        common.signals.switchViewToggled.emit()

    def save_selection(self):
        pass

    def restore_selection(self):
        """Select the current active item.

        """
        key = None
        if self.tab_idx == 0:
            key = f'{common.active("server")}/{common.active("job")}/{common.active("root")}'
        elif self.tab_idx == 1:
            key = common.active('asset')
        elif self.tab_idx == 2:
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

            o = common.Size.Indicator(2.0)
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

            _o = common.Size.Margin(2.0)
            rect = QtCore.QRect(widget.rect()).adjusted(_o, _o, -_o, -_o)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.Color.DarkBackground())
            painter.drawRoundedRect(rect, o, o)

            pen = QtGui.QPen(common.Color.Blue())
            pen.setWidthF(common.Size.Separator(2.0))
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            f = pen.widthF()
            rect = QtCore.QRect(rect).adjusted(f * 0.5, f * 0.5, -f, -f)
            painter.drawRoundedRect(rect, o, o)

            painter.end()
            return True

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


class TaskSwitchViewDelegate(delegate.ItemDelegate):
    """Delegate used to paint :class:`TaskSwitchView`.
    
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
        rect.setHeight(rect.height() - common.Size.Separator())
        rect.setLeft(common.Size.Indicator())

        o = common.Size.Separator()
        _rect = rect.adjusted(o, o, -o, -o)
        o = common.Size.Indicator(2.0)

        if index.data(QtCore.Qt.DisplayRole) == common.active('task'):

            painter.setOpacity(0.66)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.Color.Green())
            painter.drawRoundedRect(_rect, o, o)

            painter.setOpacity(1.0)
            pen = QtGui.QPen(common.Color.Green())
            pen.setWidth(common.Size.Separator(2.0))
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(_rect, o, o)
        elif selected:
            painter.setOpacity(0.66)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.Color.LightBackground())
            painter.drawRoundedRect(_rect, o, o)

            painter.setOpacity(1.0)
            pen = QtGui.QPen(common.Color.Blue())
            pen.setWidth(common.Size.Separator(2.0))
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(_rect, o, o)
        elif hover:
            painter.setOpacity(0.3)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.Color.LightBackground())
            painter.drawRoundedRect(_rect, o, o)

    @delegate.save_painter
    def paint_name(self, *args):
        """Paints the name and the number of files available for the given
        task item.

        """
        rectangles, painter, option, index, selected, focused, active, archived, \
            favourite, hover, font, metrics, cursor_position = args

        if not index.data(QtCore.Qt.DisplayRole):
            return

        if hasattr(index.model(), 'sourceModel'):
            tab_idx = index.model().sourceModel().tab_idx
        else:
            tab_idx = index.model().tab_idx

        if tab_idx == common.BookmarkTab:
            active = index.data(common.PathRole) == common.active('root', path=True)
            has_children = False
        elif tab_idx == common.AssetTab:
            active = index.data(common.PathRole) == common.active('asset', path=True)
            has_children = False
        elif tab_idx == common.FileTab:
            active = index.data(common.PathRole) == common.active('task', path=True)
            has_children = bool(index.data(common.NoteCountRole))

        o = common.Size.Margin()
        rect = QtCore.QRect(option.rect)

        color = common.Color.LightBackground()
        color = common.Color.Text() if hover else color
        color = common.Color.SelectedText() if selected or active or has_children else color

        font = common.Font.MediumFont(common.Size.MediumText())[0]

        _rect = QtCore.QRect(0, 0, o, o)
        _rect.moveCenter(option.rect.center())
        _rect.moveLeft(
            option.rect.left() + ((o + common.Size.Indicator()) * 0.5)
        )

        icon = index.data(QtCore.Qt.DecorationRole)
        icon = ui.get_icon('check', color=common.Color.Green(), size=o) if active else icon
        if icon:
            icon.paint(painter, _rect, QtCore.Qt.AlignCenter)

        rect = rect.marginsRemoved(QtCore.QMargins(o * 2, 0, o, 0))

        text = index.data(QtCore.Qt.DisplayRole)
        width = common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            color
        )
        rect.setLeft(rect.left() + width)

        items = []

        if index.data(common.DescriptionRole):

            color = common.Color.Green() if active else common.Color.SecondaryText()
            color = common.Color.Text() if hover else color
            color = common.Color.Text() if selected else color
            items.append((index.data(common.DescriptionRole), color))

        for idx, val in enumerate(items):
            text, color = val
            if idx == 0:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
            else:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight

            width = common.draw_aliased_text(
                painter,
                common.Font.MediumFont(common.Size.SmallText())[0],
                rect,
                '    ｜    ', align, common.Color.VeryDarkBackground()
            )
            rect.setLeft(rect.left() + width)

            width = common.draw_aliased_text(
                painter,
                common.Font.MediumFont(common.Size.MediumText())[0],
                rect,
                text,
                align,
                color
            )
            rect.setLeft(rect.left() + width)

    def sizeHint(self, option, index):
        """Size hint.

        """
        return QtCore.QSize(0, common.Size.RowHeight())


class BaseItemModel(models.ItemModel):
    """Task folder item model used to get task folders of an asset item.

    """

    def __init__(self, tab_idx, parent=None):
        super().__init__(parent=parent)
        self.tab_idx = tab_idx

    def source_path(self):
        """The model's source path.

        """
        try:
            return common.source_model(self.tab_idx).source_path()
        except:
            return None

    def task(self):
        if self.tab_idx == 0:
            return 'bookmark_switch_view'
        elif self.tab_idx == 1:
            return 'asset_switch_view'
        elif self.tab_idx == 2:
            return 'task_switch_view'

    def data_type(self):
        """The model's data type.

        """
        return common.FileItem

    @common.error
    @common.debug
    @QtCore.Slot()
    def reset_data(self, *args, force=False, emit_active=True):
        """Force model data reset every time.

        """
        return super().reset_data(force=True, emit_active=emit_active)

    def item_generator(self, path):
        model = common.model(self.tab_idx)
        for idx in range(model.rowCount()):
            yield model.index(idx, 0)

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

        for index in self.item_generator(source):
            if not index.isValid():
                continue

            pixmap, color = images.get_thumbnail(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
                index.data(common.PathRole),
                size=common.Size.RowHeight(),
                fallback_thumb='folder'
            )
            icon = QtGui.QIcon(pixmap)

            data[len(data)] = common.DataDict(
                {
                    QtCore.Qt.DisplayRole: index.data(QtCore.Qt.DisplayRole),
                    QtCore.Qt.EditRole: None,
                    common.PathRole: index.data(common.PathRole),
                    QtCore.Qt.SizeHintRole: None,
                    QtCore.Qt.DecorationRole: icon,
                    #
                    QtCore.Qt.StatusTipRole: index.data(QtCore.Qt.StatusTipRole),
                    QtCore.Qt.AccessibleDescriptionRole: index.data(
                        QtCore.Qt.AccessibleDescriptionRole
                    ),
                    QtCore.Qt.WhatsThisRole: index.data(QtCore.Qt.WhatsThisRole),
                    QtCore.Qt.ToolTipRole: index.data(QtCore.Qt.ToolTipRole),
                    #
                    common.FlagsRole: flags,
                    common.DescriptionRole: index.data(common.DescriptionRole),
                    common.NoteCountRole: 1,
                }
            )

    def filter_setting_dict_key(self):
        """The custom dictionary key used to save filter settings to the user settings
        file.

        """
        return ''


class BookmarkItemModel(BaseItemModel):

    def __init__(self, parent=None):
        super().__init__(common.BookmarkTab, parent=parent)


class AssetItemModel(BaseItemModel):

    def __init__(self, parent=None):
        super().__init__(common.AssetTab, parent=parent)


class TaskItemModel(models.ItemModel):
    """Task folder item model used to get task folders of an asset item.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.tab_idx = common.FileTab
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

        for entry in self.item_generator(source):
            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue

            path = entry.path.replace('\\', '/')
            idx = len(data)

            data[idx] = common.DataDict(
                {
                    QtCore.Qt.DisplayRole: entry.name,
                    QtCore.Qt.EditRole: entry.name,
                    common.PathRole: path,
                    QtCore.Qt.SizeHintRole: self.row_size,
                    QtCore.Qt.DecorationRole: None,
                    #
                    QtCore.Qt.StatusTipRole: path,
                    QtCore.Qt.AccessibleDescriptionRole: path,
                    QtCore.Qt.WhatsThisRole: path,
                    QtCore.Qt.ToolTipRole: path,
                    #
                    common.QueueRole: self.queues,
                    common.DataTypeRole: common.FileItem,
                    common.DataDictRole: weakref.ref(data),
                    common.ItemTabRole: common.TaskItemSwitch,
                    #
                    common.EntryRole: [entry, ],
                    common.FlagsRole: flags,
                    common.ParentPathRole: source_path,
                    common.DescriptionRole: '',
                    common.NoteCountRole: 0,
                    common.FileDetailsRole: '',
                    common.SequenceRole: None,
                    common.FramesRole: [],
                    common.StartPathRole: None,
                    common.EndPathRole: None,
                    #
                    common.FileInfoLoaded: False,
                    common.ThumbnailLoaded: True,
                    #
                    common.SortByNameRole: 'z' + entry.name.lower(),
                    common.SortByLastModifiedRole: 'z' + entry.name.lower(),
                    common.SortBySizeRole: 'z' + entry.name.lower(),
                    common.SortByTypeRole: 'z' + entry.name.lower(),
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
        return QtCore.QSize(1, common.Size.RowHeight(1.2))

    def filter_setting_dict_key(self):
        """The custom dictionary key used to save filter settings to the user settings
        file.

        """
        return 'task'


class BookmarkSwitchView(BaseSwitchView):
    """The view responsible for displaying the available data-keys.

    """
    Delegate = TaskSwitchViewDelegate
    queues = (threads.FileInfo2,)

    def __init__(self, parent=None):
        super().__init__(
            common.AssetTab,
            parent=parent
        )

    def get_source_model(self):
        return BookmarkItemModel(parent=self)

    @QtCore.Slot(QtCore.QModelIndex)
    def emit_item_clicked(self, index):
        path = index.data(common.PathRole)
        for idx in range(common.model(common.BookmarkTab).rowCount()):
            index = common.model(common.BookmarkTab).index(idx, 0)
            if index.data(common.PathRole) == path:
                common.widget(common.BookmarkTab).activate(index)
                break


class AssetSwitchView(BaseSwitchView):
    """The view responsible for displaying the available data-keys.

    """
    Delegate = TaskSwitchViewDelegate
    queues = ()

    def __init__(self, parent=None):
        super().__init__(
            common.FileTab,
            parent=parent
        )

    def get_source_model(self):
        return AssetItemModel(parent=self)

    @QtCore.Slot(QtCore.QModelIndex)
    def emit_item_clicked(self, index):
        path = index.data(common.PathRole)
        for idx in range(common.model(common.AssetTab).rowCount()):
            index = common.model(common.AssetTab).index(idx, 0)
            if index.data(common.PathRole) == path:
                common.widget(common.AssetTab).activate(index)
                break


class TaskSwitchView(BaseSwitchView):
    """The view responsible for displaying the available data-keys.

    """
    Delegate = TaskSwitchViewDelegate
    queues = (threads.FileInfo2,)

    def __init__(self, parent=None):
        super().__init__(
            common.FileTab,
            parent=parent
        )

    def get_source_model(self):
        return TaskItemModel(parent=self)

    @QtCore.Slot(QtCore.QModelIndex)
    def emit_item_clicked(self, index):
        QtCore.QTimer.singleShot(
            1,
            functools.partial(
                common.signals.taskFolderChanged.emit,
                index.data(QtCore.Qt.DisplayRole)
            )
        )
