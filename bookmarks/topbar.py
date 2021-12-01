# -*- coding: utf-8 -*-
"""The bar above the bookmark/asset/file widgets.

"""
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from . import log
from . import common
from . import ui
from . import contextmenu
from . import images

from . import database
from . import actions
from . import shortcuts

from .lists import delegate


class QuickSwitchMenu(contextmenu.BaseContextMenu):
    def add_switch_menu(self, idx, label):
        """Adds the items needed to quickly change bookmarks or assets."""
        off_pixmap = images.ImageCache.get_rsc_pixmap(
            'icon_bw', common.color(common.TextSecondaryColor), common.size(common.WidthMargin))
        on_pixmap = images.ImageCache.get_rsc_pixmap(
            'check', common.color(common.GreenColor), common.size(common.WidthMargin))

        self.menu[label] = {
            'disabled': True
        }

        active_index = common.active_index(idx)
        for n in range(common.model(idx).rowCount()):
            index = common.model(idx).index(n, 0)

            name = index.data(QtCore.Qt.DisplayRole)
            active = False
            if active_index.isValid():
                n = active_index.data(QtCore.Qt.DisplayRole)
                active = n.lower() == name.lower()

            pixmap, _ = images.get_thumbnail(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
                index.data(QtCore.Qt.StatusTipRole),
                size=common.size(common.WidthMargin) * 4,
                fallback_thumb='icon_bw'
            )
            pixmap = pixmap if pixmap else off_pixmap
            pixmap = on_pixmap if active else pixmap
            icon = QtGui.QIcon(pixmap)
            self.menu[name.upper()] = {
                'icon': icon,
                'action': functools.partial(common.widget(idx).activate, index)
            }
        return


class SwitchBookmarkMenu(QuickSwitchMenu):
    @common.error
    @common.debug
    def setup(self):
        self.add_menu()
        self.separator()
        self.add_switch_menu(
            common.BookmarkTab,
            'Change Bookmark'
        )

    def add_menu(self):
        self.menu['add'] = {
            'icon': ui.get_icon('add', color=common.color(common.GreenColor)),
            'text': 'Add Bookmark...',
            'action': actions.show_add_bookmark,
            'shortcut': shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }


class SwitchAssetMenu(QuickSwitchMenu):
    @common.error
    @common.debug
    def setup(self):
        self.add_menu()
        self.separator()
        self.add_switch_menu(
            common.AssetTab,
            'Change Asset'
        )

    def add_menu(self):
        self.menu['add'] = {
            'icon': ui.get_icon('add', color=common.color(common.GreenColor)),
            'text': 'Add Asset...',
            'action': actions.show_add_asset,
            'shortcut': shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }


class FilterHistoryMenu(contextmenu.BaseContextMenu):
    @common.error
    @common.debug
    def setup(self):
        self.history_menu()

    def history_menu(self):
        w = common.widget()
        proxy = w.model()
        model = w.model().sourceModel()

        v = model.get_local_setting(common.TextFilterKeyHistory)
        v = v.split(';') if v else []
        v.reverse()

        self.menu[contextmenu.key()] = {
            'text': 'Show All Items  (alt + click)',
            'action': functools.partial(proxy.set_filter_text, ''),
        }

        self.separator()

        for t in v:
            if not t:
                continue

            self.menu[contextmenu.key()] = {
                'icon': ui.get_icon('filter'),
                'text': t,
                'action': functools.partial(proxy.set_filter_text, t),
            }

        self.separator()

        self.menu[contextmenu.key()] = {
            'icon': ui.get_icon('close', color=common.color(common.RedColor)),
            'text': 'Clear History',
            'action': (
                functools.partial(proxy.set_filter_text, ''),
                lambda: model.set_local_setting(
                    common.TextFilterKeyHistory, '')
            ),
        }


class BaseControlButton(ui.ClickableIconButton):
    """Base-class used for control buttons on the top bar."""

    def __init__(self, pixmap, description, color=(common.color(common.TextSelectedColor), common.color(common.TextDisabledColor)), parent=None):
        super(BaseControlButton, self).__init__(
            pixmap,
            color,
            common.size(common.WidthMargin),
            description=description,
            parent=parent
        )
        common.signals.updateButtons.connect(self.update)


class FilterButton(BaseControlButton):
    def __init__(self, parent=None):
        super(FilterButton, self).__init__(
            'filter',
            'Set Filter  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.ToggleSearch)),
            parent=parent
        )

        self.clicked.connect(common.signals.toggleFilterButton)
        common.signals.toggleFilterButton.connect(self.update)

    def state(self):
        if not common.widget():
            return False
        filter_text = common.widget().model().filter_text()
        if not filter_text:
            return False
        if filter_text == '/':
            return False
        return True

    def contextMenuEvent(self, event):
        menu = FilterHistoryMenu(QtCore.QModelIndex(), parent=self)
        pos = self.mapToGlobal(event.pos())
        menu.move(pos)
        menu.exec_()

    def mouseReleaseEvent(self, event):
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        if alt_modifier or shift_modifier or control_modifier:
            common.widget().model().set_filter_text('')
            common.widget().model().filterTextChanged.emit('')
            return

        super(FilterButton, self).mouseReleaseEvent(event)


class ToggleSequenceButton(BaseControlButton):
    def __init__(self, parent=None):
        super().__init__(
            'collapse',
            'Show Files or Sequences  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.ToggleSequence)),
            parent=parent
        )

        self.clicked.connect(common.signals.toggleSequenceButton)
        common.signals.toggleSequenceButton.connect(self.update)

    def pixmap(self):
        if self.state():
            return images.ImageCache.get_rsc_pixmap('collapse', self._on_color, common.size(common.WidthMargin))
        return images.ImageCache.get_rsc_pixmap('expand', self._off_color, common.size(common.WidthMargin))

    def state(self):
        if not common.widget():
            return
        datatype = common.widget().model().sourceModel().data_type()
        if datatype == common.FileItem:
            return False
        if datatype == common.SequenceItem:
            return True
        return False

    def update(self):
        super().update()
        if common.current_tab() in (common.FileTab, common.FavouriteTab):
            self.show()
        else:
            self.hide()


class ToggleArchivedButton(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleArchivedButton, self).__init__(
            'archivedVisible',
            'Show/Hide Archived Items  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.ToggleArchived)),
            parent=parent
        )

        self.clicked.connect(common.signals.toggleArchivedButton)
        common.signals.toggleArchivedButton.connect(self.update)

    def pixmap(self):
        if self.state():
            return images.ImageCache.get_rsc_pixmap('archivedVisible', self._on_color, common.size(common.WidthMargin))
        return images.ImageCache.get_rsc_pixmap('archivedHidden', self._off_color, common.size(common.WidthMargin))

    def state(self):
        if not common.widget():
            return
        return common.widget().model().filter_flag(common.MarkedAsArchived)

    def update(self):
        super(ToggleArchivedButton, self).update()
        if common.current_tab() < common.FavouriteTab:
            self.show()
        else:
            self.hide()


class ToggleInlineIcons(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleInlineIcons, self).__init__(
            'branch_closed',
            'Show/Hide List Buttons  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.HideInlineButtons)),
            parent=parent
        )

        self.clicked.connect(common.signals.toggleInlineIcons)
        common.signals.toggleInlineIcons.connect(self.update)

    def state(self):
        if not common.widget():
            return False
        val = common.widget().buttons_hidden()
        return val

    def hideEvent(self, event):
        common.sort_by_basename = False


class ToggleFavouriteButton(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleFavouriteButton, self).__init__(
            'favourite',
            'Show Starred Only  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.ToggleFavourite)),
            parent=parent
        )
        self.clicked.connect(common.signals.toggleFavouritesButton)
        common.signals.toggleFavouritesButton.connect(self.update)

    def state(self):
        if not common.widget():
            return
        val = common.widget().model().filter_flag(common.MarkedAsFavourite)
        return val

    def update(self):
        super(ToggleFavouriteButton, self).update()
        if common.current_tab() < common.FavouriteTab:
            self.show()
        else:
            self.hide()


class SlackButton(BaseControlButton):
    def __init__(self, parent=None):
        super(SlackButton, self).__init__(
            'slack',
            'Slack Massenger',
            parent=parent
        )
        common.signals.databaseValueUpdated.connect(self.check_updated_value)

    @QtCore.Slot()
    def action(self):
        """Opens the set slack workspace."""
        actions.show_slack()

    def state(self):
        return True

    @QtCore.Slot()
    def check_updated_value(self, table, source, key, value):
        if table != database.BookmarkTable:
            return
        if key != 'slacktoken':
            return
        if value:
            self.setHidden(False)
            return True
        self.setHidden(True)
        return False

    @QtCore.Slot()
    def check_token(self):
        """Checks if the current bookmark has an active slack token set.

        If the value is set we'll show the button, otherwise it will stay hidden.

        """
        args = [common.active(f) for f in (
            common.ServerKey, common.JobKey, common.RootKey)]
        if not all(args):
            self.setHidden(True)
            return False

        db = database.get_db(*args)
        slacktoken = db.value(
            db.source(),
            'slacktoken',
            table=database.BookmarkTable
        )

        if not slacktoken:
            self.setHidden(True)
            return False

        self.setHidden(False)
        return True


class RefreshButton(BaseControlButton):
    def __init__(self, parent=None):
        super().__init__(
            'refresh',
            'Refresh items  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.Refresh)),
            parent=parent
        )
        self.clicked.connect(actions.refresh)
        self.clicked.connect(self.update)

    def state(self):
        """The state of the auto-thumbnails"""
        if not common.widget():
            return False

        model = common.widget().model().sourceModel()
        p = model.source_path()
        k = model.task()
        t = model.data_type()

        if not p or not all(p) or not k or t is None:
            return False

        data = common.get_task_data(p, k)
        if not data:
            return False

        if any((data[common.FileItem].refresh_needed, data[common.SequenceItem].refresh_needed)):
            return True

        return False


class CollapseSequenceMenu(contextmenu.BaseContextMenu):
    def __init__(self, parent=None):
        super(CollapseSequenceMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_collapse_sequence_menu()


class BaseTabButton(QtWidgets.QLabel):
    """Baseclass for text-based control buttons."""
    icon = 'asset'

    clicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()

    def __init__(self, label, idx, description, parent=None):
        super().__init__(parent=parent)
        self._label = label
        self.tab_idx = idx

        self.setStatusTip(description)
        self.setToolTip(description)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.clicked.connect(self.emit_tab_changed)
        common.signals.updateButtons.connect(self.update)

    @QtCore.Slot()
    def emit_tab_changed(self):
        if common.current_tab() == common.FileTab and self.tab_idx == common.FileTab:
            actions.toggle_task_view()
            return
        if common.current_tab() == self.tab_idx:
            return
        common.signals.tabChanged.emit(self.tab_idx)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def mouseReleaseEvent(self, event):
        """Only triggered when the left buttons is pressed."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.doubleClicked.emit()

    def text(self):
        return self._label

    def get_width(self):
        o = common.size(common.WidthIndicator) * 6
        _, metrics = common.font_db.primary_font(common.size(common.FontSizeMedium))
        return metrics.horizontalAdvance(self.text()) + o

    @QtCore.Slot()
    def adjust_size(self):
        """Slot responsible for setting the size of the widget to match the text."""
        self.setMaximumWidth(self.get_width())
        self.setMinimumWidth(common.size(common.WidthMargin) * 2)
        self.update()

    def showEvent(self, event):
        self.adjust_size()

    def paintEvent(self, event):
        """The control button's paint method - shows the the set text and
        an underline if the tab is active."""
        if common.main_widget is None or not common.main_widget._initialized:
            return

        rect = QtCore.QRect(self.rect())

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        option = QtWidgets.QStyleOptionButton()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        painter.setPen(QtCore.Qt.NoPen)

        if common.current_tab() == self.tab_idx:
            color = common.color(common.TextSelectedColor) if hover else common.color(common.TextColor)
            painter.setBrush(color)
        else:
            color = common.color(common.TextColor) if hover else common.color(common.BackgroundColor)
            painter.setBrush(color)

        font, metrics = common.font_db.primary_font(common.size(common.FontSizeMedium))

        # When the width of the button is very small, we'll switch to an icon
        # representation instead of text:
        if self.tab_idx == common.FileTab and common.current_tab() == common.FileTab:
            # Draw icon
            pixmap = images.ImageCache.get_rsc_pixmap(
                'branch_open',
                common.color(common.TextSelectedColor),
                common.size(common.WidthMargin)
            )
            _rect = QtCore.QRect(0, 0, common.size(common.WidthMargin), common.size(common.WidthMargin))
            _rect.moveCenter(self.rect().center())
            painter.drawPixmap(
                _rect,
                pixmap,
                pixmap.rect()
            )
        else:
            if (metrics.horizontalAdvance(self.text()) + (common.size(common.WidthMargin) * 0.5)) < self.rect().width():
                # Draw label
                width = metrics.horizontalAdvance(self.text())
                x = (self.width() / 2.0) - (width / 2.0)
                y = self.rect().center().y() + (metrics.ascent() * 0.5)
                path = delegate.get_painter_path(x, y, font, self.text())
                painter.drawPath(path)
            else:
                # Draw icon
                pixmap = images.ImageCache.get_rsc_pixmap(
                    self.icon,
                    color,
                    common.size(common.WidthMargin)
                )
                _rect = QtCore.QRect(0, 0, common.size(common.WidthMargin), common.size(common.WidthMargin))
                _rect.moveCenter(self.rect().center())
                painter.drawPixmap(
                    _rect,
                    pixmap,
                    pixmap.rect()
                )

        # Draw indicator line below icon or text
        rect.setHeight(common.size(common.HeightSeparator) * 2.0)
        painter.setPen(QtCore.Qt.NoPen)
        rect.setWidth(self.rect().width())

        if common.current_tab() == self.tab_idx:
            painter.setOpacity(0.9)
            color = common.color(common.TextColor) if hover else common.color(common.RedColor)
        else:
            painter.setOpacity(0.3)
            color = common.color(common.TextColor) if hover else common.color(common.BlueColor)

        painter.setBrush(color)
        painter.drawRect(rect)
        painter.end()


class BookmarksTabButton(BaseTabButton):
    """The button responsible for revealing the ``BookmarksWidget``"""
    icon = 'bookmark'

    def __init__(self, parent=None):
        super(BookmarksTabButton, self).__init__(
            'Bookmarks',
            common.BookmarkTab,
            'Click to see the list of added bookmarks',
            parent=parent
        )

    def contextMenuEvent(self, event):
        menu = SwitchBookmarkMenu(QtCore.QModelIndex(), parent=self)
        pos = self.mapToGlobal(event.pos())
        menu.move(pos)
        menu.exec_()


class AssetsTabButton(BaseTabButton):
    """The button responsible for revealing the ``AssetsWidget``"""
    icon = 'asset'

    def __init__(self, parent=None):
        super(AssetsTabButton, self).__init__(
            'Assets',
            common.AssetTab,
            'Click to see the list of available assets',
            parent=parent
        )

    def text(self):
        widget = common.widget(common.BookmarkTab)
        if not widget.model().sourceModel().active_index().isValid():
            return ''
        return super(AssetsTabButton, self).text()

    def contextMenuEvent(self, event):
        menu = SwitchAssetMenu(QtCore.QModelIndex(), parent=self)
        pos = self.mapToGlobal(event.pos())
        menu.move(pos)
        menu.exec_()


class FilesTabButton(BaseTabButton):
    """The buttons responsible for swtiching the the FilesWidget and showing
    the switch to change the data-key."""
    icon = 'file'

    def __init__(self, parent=None):
        super().__init__(
            'Files',
            common.FileTab,
            'Click to see or change the current task folder',
            parent=parent)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        common.signals.taskViewToggled.connect(self.update)

    def text(self):
        if not common.active_index(common.AssetTab).isValid():
            return ''
        return super().text()

    def contextMenuEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        """Indicating the visibility of the TaskFolderWidget."""
        if common.widget(common.TaskTab).isHidden():
            super().paintEvent(event)
            return

        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        rect = self.rect()
        rect.setHeight(common.size(common.HeightSeparator) * 2.0)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.GreenColor))
        painter.drawRect(rect)

        o = common.size(common.WidthMargin)
        pixmap = images.ImageCache.get_rsc_pixmap('gradient2', None, o)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())

        rect = QtCore.QRect(0, 0, o, o)
        rect.moveCenter(self.rect().center())
        pixmap = images.ImageCache.get_rsc_pixmap(
            'folder', common.color(common.GreenColor), o)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        painter.drawPixmap(rect, pixmap, pixmap.rect())
        painter.end()



class FavouritesTabButton(BaseTabButton):
    """Drop-down widget to switch between the list"""
    icon = 'favourite'

    def __init__(self, parent=None):
        super(FavouritesTabButton, self).__init__(
            'Starred',
            common.FavouriteTab,
            'Click to see your saved favourites',
            parent=parent
        )


class SlackDropOverlayWidget(QtWidgets.QWidget):
    """Widget used to receive a slack message drop."""

    def __init__(self, parent=None):
        super(SlackDropOverlayWidget, self).__init__(parent=parent)
        self.setAcceptDrops(True)
        self.drop_target = True
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        if not self.drop_target:
            return

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.SeparatorColor))
        painter.drawRoundedRect(
            self.rect(), common.size(common.WidthIndicator), common.size(common.WidthIndicator))

        pixmap = images.ImageCache.get_rsc_pixmap(
            'slack', common.color(common.GreenColor), self.rect().height() - (common.size(common.WidthIndicator) * 1.5))
        rect = QtCore.QRect(0, 0, common.size(common.WidthMargin), common.size(common.WidthMargin))
        rect.moveCenter(self.rect().center())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        o = common.size(common.WidthIndicator)
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.color(common.GreenColor))
        pen.setWidthF(common.size(common.HeightSeparator) * 2.0)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, o, o)
        painter.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Slack drop event"""
        try:
            from .external import slack
        except ImportError as err:
            ui.ErrorBox(
                'Could not import SlackClient',
                'The Slack API python module was not loaded:\n{}'.format(err),
            ).open()
            log.error('Slack import error.')
            return

        if event.source() == self:
            return  # Won't allow dropping an item from itself
        mime = event.mimeData()

        if not mime.hasUrls():
            return

        event.accept()

        message = []
        for f in mime.urls():
            file_info = QtCore.QFileInfo(f.toLocalFile())
            line = '```{}```'.format(file_info.filePath())
            message.append(line)

        message = '\n'.join(message)
        parent = self.parent().parent().stacked_widget
        index = parent.widget(
            common.BookmarkTab).model().sourceModel().active_index()
        if not index.isValid():
            return

        widget = parent.currentWidget().show_slack()
        widget.message_widget.append_message(message)

    def showEvent(self, event):
        pos = self.parent().rect().topLeft()
        pos = self.parent().mapToGlobal(pos)
        self.move(pos)
        self.setFixedWidth(self.parent().rect().width())
        self.setFixedHeight(self.parent().rect().height())


class TopBarWidget(QtWidgets.QWidget):
    """The bar above the stacked widget containing the main app control buttons.

    """
    slackDragStarted = QtCore.Signal(QtCore.QModelIndex)
    slackDropFinished = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self._create_ui()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        height = common.size(common.WidthMargin) + (common.size(common.WidthIndicator) * 3)
        self.setFixedHeight(height)

        # Control view/model/button
        self.bookmarks_button = BookmarksTabButton(parent=self)
        self.assets_button = AssetsTabButton(parent=self)
        self.files_button = FilesTabButton(parent=self)
        self.favourites_button = FavouritesTabButton(parent=self)

        self.refresh_button = RefreshButton(parent=self)
        self.filter_button = FilterButton(parent=self)
        self.collapse_button = ToggleSequenceButton(parent=self)
        self.archived_button = ToggleArchivedButton(parent=self)
        self.favourite_button = ToggleFavouriteButton(parent=self)
        self.slack_button = SlackButton(parent=self)
        self.slack_button.setHidden(True)
        self.inline_icons_button = ToggleInlineIcons(parent=self)

        self.layout().addWidget(self.bookmarks_button, 1)
        self.layout().addWidget(self.assets_button, 1)
        self.layout().addWidget(self.files_button, 1)
        self.layout().addWidget(self.favourites_button, 1)

        self.layout().addStretch()

        self.layout().addWidget(self.filter_button)
        self.layout().addSpacing(common.size(common.WidthIndicator))
        self.layout().addWidget(self.refresh_button)
        self.layout().addSpacing(common.size(common.WidthIndicator))
        self.layout().addWidget(self.collapse_button)
        self.layout().addSpacing(common.size(common.WidthIndicator))
        self.layout().addWidget(self.archived_button)
        self.layout().addSpacing(common.size(common.WidthIndicator))
        self.layout().addWidget(self.favourite_button)
        self.layout().addSpacing(common.size(common.WidthIndicator))
        self.layout().addWidget(self.inline_icons_button)
        self.layout().addSpacing(common.size(common.WidthIndicator))
        self.layout().addWidget(self.slack_button)

        self.layout().addSpacing(common.size(common.WidthIndicator))

        self.drop_overlay = SlackDropOverlayWidget(parent=self)
        self.drop_overlay.setHidden(True)

    def paintEvent(self, event):
        """`TopBarWidget`' paint event."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)

        pixmap = images.ImageCache.get_rsc_pixmap(
            'gradient', None, self.height())
        t = QtGui.QTransform()
        t.rotate(90)
        pixmap = pixmap.transformed(t)
        painter.setOpacity(0.8)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()
