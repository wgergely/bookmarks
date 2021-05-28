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
from . import settings
from . import bookmark_db
from . import actions
from . import shortcuts

from .lists import delegate


def stacked_widget():
    from . import main
    if not main.instance():
        return None
    return main.instance().stackedwidget


def current_widget():
    from . import main
    if not main.instance():
        return None
    return main.instance().stackedwidget.currentWidget()


def current_index():
    from . import main
    if not main.instance():
        return None
    return main.instance().stackedwidget.currentIndex()


class QuickSwitchMenu(contextmenu.BaseContextMenu):
    def stacked_widget(self):
        return self.parent().parent().parent().stackedwidget

    @property
    def index(self):
        return current_widget().model().sourceModel().active_index()

    @index.setter
    def index(self, v):
        pass

    def add_switch_menu(self, widget, label):
        """Adds the items needed to quickly change bookmarks or assets."""
        off_pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.MARGIN())
        on_pixmap = images.ImageCache.get_rsc_pixmap(
            u'check', common.GREEN, common.MARGIN())

        self.menu[label] = {
            u'disabled': True
        }

        active_index = widget.model().sourceModel().active_index()
        for n in xrange(widget.model().rowCount()):
            index = widget.model().index(n, 0)

            name = index.data(QtCore.Qt.DisplayRole)
            active = False
            if active_index.isValid():
                n = active_index.data(QtCore.Qt.DisplayRole)
                active = n.lower() == name.lower()

            thumbnail_path = images.get_cached_thumbnail_path(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
                index.data(QtCore.Qt.StatusTipRole),
            )
            pixmap = images.ImageCache.get_pixmap(
                thumbnail_path, common.MARGIN() * 2)
            pixmap = pixmap if pixmap else off_pixmap
            pixmap = on_pixmap if active else pixmap
            icon = QtGui.QIcon(pixmap)
            self.menu[name.upper()] = {
                u'icon': icon,
                u'action': functools.partial(widget.activate, index)
            }
        return


class SwitchBookmarkMenu(QuickSwitchMenu):
    @common.error
    @common.debug
    def setup(self):
        self.add_menu()
        self.separator()
        self.add_switch_menu(
            stacked_widget().widget(common.BookmarkTab),
            u'Change Bookmark'
        )

    def add_menu(self):
        self.menu[u'add'] = {
            u'icon': self.get_icon(u'add', color=common.GREEN),
            u'text': u'Add Bookmark...',
            u'action': actions.show_add_bookmark,
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
            stacked_widget().widget(common.AssetTab),
            u'Change Asset'
        )

    def add_menu(self):
        self.menu[u'add'] = {
            u'icon': self.get_icon(u'add', color=common.GREEN),
            u'text': u'Add Asset...',
            u'action': actions.show_add_asset,
            'shortcut': shortcuts.string(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }


class FilterHistoryMenu(contextmenu.BaseContextMenu):
    @common.error
    @common.debug
    def setup(self):
        self.history_menu()

    def history_menu(self):
        w = current_widget()
        proxy = w.model()
        model = w.model().sourceModel()

        v = model.get_local_setting(settings.TextFilterKeyHistory)
        v = v.split(';') if v else []
        v.reverse()

        self.menu[contextmenu.key()] = {
            u'text': u'Show All Items  (alt + click)',
            u'action': functools.partial(proxy.set_filter_text, u''),
        }

        self.separator()

        for t in v:
            if not t:
                continue

            self.menu[contextmenu.key()] = {
                u'icon': self.get_icon(u'filter'),
                u'text': t,
                u'action': functools.partial(proxy.set_filter_text, t),
            }

        self.separator()

        self.menu[contextmenu.key()] = {
            u'icon': self.get_icon(u'close', color=common.RED),
            u'text': u'Clear History',
            u'action': (
                functools.partial(proxy.set_filter_text, u''),
                lambda: model.set_local_setting(
                    settings.TextFilterKeyHistory, u'')
            ),
        }


class BaseControlButton(ui.ClickableIconButton):
    """Base-class used for control buttons on the top bar."""

    def __init__(self, pixmap, description, color=(common.SELECTED_TEXT, common.DISABLED_TEXT), parent=None):
        super(BaseControlButton, self).__init__(
            pixmap,
            color,
            common.MARGIN(),
            description=description,
            parent=parent
        )
        common.signals.updateButtons.connect(self.update)


class FilterButton(BaseControlButton):
    def __init__(self, parent=None):
        super(FilterButton, self).__init__(
            u'filter',
            u'Set Filter  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.ToggleSearch)),
            parent=parent
        )

        self.clicked.connect(common.signals.toggleFilterButton)
        common.signals.toggleFilterButton.connect(self.update)

    def state(self):
        if not current_widget():
            return False
        filter_text = current_widget().model().filter_text()
        if not filter_text:
            return False
        if filter_text == u'/':
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
            current_widget().model().set_filter_text(u'')
            current_widget().model().filterTextChanged.emit(u'')
            return

        super(FilterButton, self).mouseReleaseEvent(event)


class ToggleSequenceButton(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleSequenceButton, self).__init__(
            u'collapse',
            u'Show Files or Sequences  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.ToggleSequence)),
            parent=parent
        )

        self.clicked.connect(common.signals.toggleSequenceButton)
        common.signals.toggleSequenceButton.connect(self.update)

    def pixmap(self):
        if self.state():
            return images.ImageCache.get_rsc_pixmap(u'collapse', self._on_color, common.MARGIN())
        return images.ImageCache.get_rsc_pixmap(u'expand', self._off_color, common.MARGIN())

    def state(self):
        if not current_widget():
            return
        datatype = current_widget().model().sourceModel().data_type()
        if datatype == common.FileItem:
            return False
        if datatype == common.SequenceItem:
            return True
        return False

    def update(self):
        super(ToggleSequenceButton, self).update()
        if current_index() in (common.FileTab, common.FavouriteTab):
            self.show()
        else:
            self.hide()


class ToggleArchivedButton(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleArchivedButton, self).__init__(
            u'archivedVisible',
            u'Show/Hide Archived Items  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.ToggleArchived)),
            parent=parent
        )

        self.clicked.connect(common.signals.toggleArchivedButton)
        common.signals.toggleArchivedButton.connect(self.update)

    def pixmap(self):
        if self.state():
            return images.ImageCache.get_rsc_pixmap(u'archivedVisible', self._on_color, common.MARGIN())
        return images.ImageCache.get_rsc_pixmap(u'archivedHidden', self._off_color, common.MARGIN())

    def state(self):
        if not current_widget():
            return
        return current_widget().model().filter_flag(common.MarkedAsArchived)

    def update(self):
        super(ToggleArchivedButton, self).update()
        if current_index() < common.FavouriteTab:
            self.show()
        else:
            self.hide()


class ToggleInlineIcons(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleInlineIcons, self).__init__(
            u'showbuttons',
            u'Show/Hide List Buttons  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.HideInlineButtons)),
            parent=parent
        )

        self.clicked.connect(common.signals.toggleInlineIcons)
        common.signals.toggleInlineIcons.connect(self.update)

    def state(self):
        if not current_widget():
            return False
        val = current_widget().buttons_hidden()
        return val

    def hideEvent(self, event):
        common.SORT_WITH_BASENAME = False


class ToggleFavouriteButton(BaseControlButton):
    def __init__(self, parent=None):
        super(ToggleFavouriteButton, self).__init__(
            u'favourite',
            u'Show/Hide My Files Only  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.ToggleFavourite)),
            parent=parent
        )
        self.clicked.connect(common.signals.toggleFavouritesButton)
        common.signals.toggleFavouritesButton.connect(self.update)

    def state(self):
        if not current_widget():
            return
        val = current_widget().model().filter_flag(common.MarkedAsFavourite)
        return val

    def update(self):
        super(ToggleFavouriteButton, self).update()
        if current_index() < common.FavouriteTab:
            self.show()
        else:
            self.hide()


class SlackButton(BaseControlButton):
    def __init__(self, parent=None):
        super(SlackButton, self).__init__(
            u'slack',
            u'Slack Massenger',
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
        if table != bookmark_db.BookmarkTable:
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
        args = [settings.active(f) for f in (
            settings.ServerKey, settings.JobKey, settings.RootKey)]
        if not all(args):
            self.setHidden(True)
            return False

        db = bookmark_db.get_db(*args)
        slacktoken = db.value(
            db.source(),
            u'slacktoken',
            table=bookmark_db.BookmarkTable
        )

        if not slacktoken:
            self.setHidden(True)
            return False

        self.setHidden(False)
        return True


class RefreshButton(BaseControlButton):
    def __init__(self, parent=None):
        super(RefreshButton, self).__init__(
            u'refresh',
            u'Refresh items  -  {}'.format(shortcuts.string(
                shortcuts.MainWidgetShortcuts, shortcuts.Refresh)),
            parent=parent
        )
        self.clicked.connect(actions.refresh)
        self.clicked.connect(self.update)

    def state(self):
        """The state of the auto-thumbnails"""
        if not current_widget():
            return False

        model = current_widget().model().sourceModel()
        if not hasattr(model, 'refresh_needed'):
            return False
        return model.refresh_needed()


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
        super(BaseTabButton, self).__init__(parent=parent)
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
        if current_index() == common.FileTab and self.tab_idx == common.FileTab:
            actions.toggle_task_view()
            return

        if current_index() == self.tab_idx:
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
        o = common.INDICATOR_WIDTH() * 6
        _, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        return metrics.width(self.text()) + o

    @QtCore.Slot()
    def adjust_size(self):
        """Slot responsible for setting the size of the widget to match the text."""
        self.setMaximumWidth(self.get_width())
        self.setMinimumWidth(common.MARGIN() * 2)
        self.update()

    def showEvent(self, event):
        self.adjust_size()

    def paintEvent(self, event):
        """The control button's paint method - shows the the set text and
        an underline if the tab is active."""
        if not stacked_widget():
            return

        rect = QtCore.QRect(self.rect())

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        option = QtWidgets.QStyleOptionButton()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        painter.setPen(QtCore.Qt.NoPen)

        if current_index() == self.tab_idx:
            color = common.SELECTED_TEXT if hover else common.TEXT
            painter.setBrush(color)
        else:
            color = common.TEXT if hover else common.BG
            painter.setBrush(color)

        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())

        # When the width of the button is very small, we'll switch to an icon
        # representation instead of text:
        if self.tab_idx == common.FileTab and current_index() == common.FileTab:
            # Draw icon
            pixmap = images.ImageCache.get_rsc_pixmap(
                'down',
                common.SELECTED_TEXT,
                common.MARGIN()
            )
            _rect = QtCore.QRect(0, 0, common.MARGIN(), common.MARGIN())
            _rect.moveCenter(self.rect().center())
            painter.drawPixmap(
                _rect,
                pixmap,
                pixmap.rect()
            )
        else:
            if (metrics.width(self.text()) + (common.MARGIN() * 0.5)) < self.rect().width():
                # Draw label
                width = metrics.width(self.text())
                x = (self.width() / 2.0) - (width / 2.0)
                y = self.rect().center().y() + (metrics.ascent() * 0.5)
                path = delegate.get_painter_path(x, y, font, self.text())
                painter.drawPath(path)
            else:
                # Draw icon
                pixmap = images.ImageCache.get_rsc_pixmap(
                    self.icon,
                    color,
                    common.MARGIN()
                )
                _rect = QtCore.QRect(0, 0, common.MARGIN(), common.MARGIN())
                _rect.moveCenter(self.rect().center())
                painter.drawPixmap(
                    _rect,
                    pixmap,
                    pixmap.rect()
                )

        # Draw indicator line below icon or text
        rect.setHeight(common.ROW_SEPARATOR() * 2.0)
        painter.setPen(QtCore.Qt.NoPen)
        rect.setWidth(self.rect().width())

        if current_index() == self.tab_idx:
            painter.setOpacity(0.9)
            color = common.TEXT if hover else common.RED
        else:
            painter.setOpacity(0.3)
            color = common.TEXT if hover else common.BLUE

        painter.setBrush(color)
        painter.drawRect(rect)
        painter.end()


class BookmarksTabButton(BaseTabButton):
    """The button responsible for revealing the ``BookmarksWidget``"""
    icon = u'bookmark'

    def __init__(self, parent=None):
        super(BookmarksTabButton, self).__init__(
            u'Bookmarks',
            common.BookmarkTab,
            u'Click to see the list of added bookmarks',
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
            u'Assets',
            common.AssetTab,
            u'Click to see the list of available assets',
            parent=parent
        )

    def text(self):
        widget = stacked_widget().widget(common.BookmarkTab)
        if not widget.model().sourceModel().active_index().isValid():
            return u'-'
        return super(AssetsTabButton, self).text()

    def contextMenuEvent(self, event):
        menu = SwitchAssetMenu(QtCore.QModelIndex(), parent=self)
        pos = self.mapToGlobal(event.pos())
        menu.move(pos)
        menu.exec_()


class FilesTabButton(BaseTabButton):
    """The buttons responsible for swtiching the the FilesWidget and showing
    the switch to change the data-key."""
    icon = u'file'

    def __init__(self, parent=None):
        super(FilesTabButton, self).__init__(
            u'Files',
            common.FileTab,
            u'Click to see or change the current task folder',
            parent=parent)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        common.signals.taskViewToggled.connect(self.update)

    def text(self):
        widget = stacked_widget().widget(common.AssetTab)
        if not widget.model().sourceModel().active_index().isValid():
            return u'-'
        return super(FilesTabButton, self).text()

    def view(self):
        from . import main
        return main.instance().taskswidget

    def contextMenuEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        """Indicating the visibility of the TaskFolderWidget."""
        if not self.view().isHidden():
            painter = QtGui.QPainter()
            painter.begin(self)

            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

            rect = self.rect()
            rect.setHeight(common.ROW_SEPARATOR() * 2.0)

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.GREEN)
            painter.drawRect(rect)

            o = common.MARGIN()
            pixmap = images.ImageCache.get_rsc_pixmap('gradient2', None, o)
            painter.drawPixmap(self.rect(), pixmap, pixmap.rect())

            rect = QtCore.QRect(0, 0, o, o)
            rect.moveCenter(self.rect().center())
            pixmap = images.ImageCache.get_rsc_pixmap(
                'folder', common.GREEN, o)
            painter.drawPixmap(rect, pixmap, pixmap.rect())

            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
        else:
            super(FilesTabButton, self).paintEvent(event)


class FavouritesTabButton(BaseTabButton):
    """Drop-down widget to switch between the list"""
    icon = u'favourite'

    def __init__(self, parent=None):
        super(FavouritesTabButton, self).__init__(
            u'My Files',
            common.FavouriteTab,
            u'Click to see your saved favourites',
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
        painter.setBrush(common.SEPARATOR)
        painter.drawRoundedRect(
            self.rect(), common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'slack', common.GREEN, self.rect().height() - (common.INDICATOR_WIDTH() * 1.5))
        rect = QtCore.QRect(0, 0, common.MARGIN(), common.MARGIN())
        rect.moveCenter(self.rect().center())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        o = common.INDICATOR_WIDTH()
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.GREEN)
        pen.setWidthF(common.ROW_SEPARATOR() * 2.0)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, o, o)
        painter.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Slack drop event"""
        try:
            from . import slack
        except ImportError as err:
            ui.ErrorBox(
                u'Could not import SlackClient',
                u'The Slack API python module was not loaded:\n{}'.format(err),
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
            line = u'```{}```'.format(file_info.filePath())
            message.append(line)

        message = u'\n'.join(message)
        parent = self.parent().parent().stackedwidget
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


class ListControlWidget(QtWidgets.QWidget):
    """The bar above the stacked widget containing the main app control buttons.

    """
    slackDragStarted = QtCore.Signal(QtCore.QModelIndex)
    slackDropFinished = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super(ListControlWidget, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        height = common.MARGIN() + (common.INDICATOR_WIDTH() * 3)
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

        self.layout().addStretch()

        self.layout().addWidget(self.filter_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.refresh_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.collapse_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.archived_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.favourite_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.inline_icons_button)
        self.layout().addSpacing(common.INDICATOR_WIDTH())
        self.layout().addWidget(self.slack_button)

        self.layout().addWidget(self.favourites_button, 1)
        self.layout().addSpacing(common.INDICATOR_WIDTH() * 2)

        self.drop_overlay = SlackDropOverlayWidget(parent=self)
        self.drop_overlay.setHidden(True)

    def _connect_signals(self):
        common.signals.assetAdded.connect(self.asset_added)

    def asset_added(self, path):
        from . import main
        widget = main.instance().stackedwidget.widget(common.AssetTab)
        model = widget.model().sourceModel()

        if not model.parent_path():
            return

        parent_path = u'/'.join(model.parent_path())

        # Check if the aded asset has been added to the currently active bookmark
        if parent_path not in path:
            return

        # Change tabs otherwise
        common.signals.tabChanged.emit(common.AssetTab)

    def paintEvent(self, event):
        """`ListControlWidget`' paint event."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'gradient', None, self.height())
        t = QtGui.QTransform()
        t.rotate(90)
        pixmap = pixmap.transformed(t)
        painter.setOpacity(0.8)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()
