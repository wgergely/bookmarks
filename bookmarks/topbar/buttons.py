"""Defines the small control buttons found on the right-hand side of the top bar.


"""
import functools

from PySide2 import QtWidgets, QtCore

from .. import actions
from .. import common
from .. import contextmenu
from .. import database
from .. import images
from .. import shortcuts
from .. import ui


class FilterHistoryMenu(contextmenu.BaseContextMenu):
    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.history_menu()

    def history_menu(self):
        w = common.widget()
        proxy = w.model()
        model = w.model().sourceModel()

        v = model.get_filter_setting('filters/text_history')
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
            'icon': ui.get_icon('close', color=common.color(common.color_red)),
            'text': 'Clear History',
            'action': (
                functools.partial(proxy.set_filter_text, ''),
                lambda: model.set_filter_setting('filters/text_history', '')),
        }


class BaseControlButton(ui.ClickableIconButton):
    """Base-class used for control buttons on the top bar."""

    def __init__(
            self,
            pixmap,
            description,
            color=(
                    common.color(common.color_selected_text),
                    common.color(common.color_disabled_text)
            ),
            parent=None
    ):
        super().__init__(
            pixmap,
            color,
            common.size(common.size_margin),
            description=description,
            parent=parent
        )
        common.signals.updateTopBarButtons.connect(self.update)


class FilterButton(BaseControlButton):
    def __init__(self, parent=None):
        s = shortcuts.string(
            shortcuts.MainWidgetShortcuts,
            shortcuts.ToggleSearch
        )
        super().__init__(
            'filter',
            f'Set Filter  -  {s}',
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
        s = shortcuts.string(
            shortcuts.MainWidgetShortcuts,
            shortcuts.ToggleSequence
        )
        super().__init__(
            'collapse',
            f'Show Files or Sequences  -  {s}',
            parent=parent
        )

        self.clicked.connect(common.signals.toggleSequenceButton)
        common.signals.toggleSequenceButton.connect(self.update)

    def pixmap(self):
        if self.state():
            return images.rsc_pixmap(
                'collapse', self._on_color,
                common.size(common.size_margin)
                )
        return images.rsc_pixmap(
            'expand', self._off_color,
            common.size(common.size_margin)
            )

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
        s = shortcuts.string(
            shortcuts.MainWidgetShortcuts,
            shortcuts.ToggleArchived
        )
        super(ToggleArchivedButton, self).__init__(
            'archivedVisible',
            f'Show/Hide Archived Items  -  {s}',
            parent=parent
        )

        self.clicked.connect(common.signals.toggleArchivedButton)
        common.signals.toggleArchivedButton.connect(self.update)

    def pixmap(self):
        if self.state():
            return images.rsc_pixmap(
                'archivedVisible',
                self._on_color,
                common.size(common.size_margin)
            )
        return images.rsc_pixmap(
            'archivedHidden',
            self._off_color,
            common.size(common.size_margin)
        )

    def state(self):
        if not common.widget():
            return
        return common.widget().model().filter_flag(common.MarkedAsArchived)


class ToggleInlineIcons(BaseControlButton):
    def __init__(self, parent=None):
        s = shortcuts.string(
            shortcuts.MainWidgetShortcuts,
            shortcuts.HideInlineButtons
        )
        super(ToggleInlineIcons, self).__init__(
            'branch_closed',
            f'Show/Hide List Buttons  -  {s}',
            parent=parent
        )

        self.clicked.connect(common.signals.toggleInlineIcons)
        common.signals.toggleInlineIcons.connect(self.update)

    def state(self):
        if not common.widget():
            return False
        val = common.widget().buttons_hidden()
        return val


class ToggleFavouriteButton(BaseControlButton):
    def __init__(self, parent=None):
        s = shortcuts.string(
            shortcuts.MainWidgetShortcuts,
            shortcuts.ToggleFavourite
        )
        super(ToggleFavouriteButton, self).__init__(
            'favourite',
            f'Show Starred Only  -  {s}',
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
            'Slack Messenger',
            parent=parent
        )
        common.signals.databaseValueUpdated.connect(self.check_updated_value)
        common.signals.bookmarkActivated.connect(self.check_token)

    @QtCore.Slot()
    def action(self):
        """Opens the set slack workspace."""
        actions.show_slack()

    def state(self):
        return True

    @QtCore.Slot()
    def check_updated_value(self, table, _, key, value):
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
    def check_token(self, *args, **kwargs):
        """Checks if the current bookmark has an active slack token set.

        If the value is set we'll show the button, otherwise it will stay hidden.

        """
        args = [common.active(f) for f in (
            'server', 'job', 'root')]
        if not all(args):
            self.setHidden(True)
            return False

        db = database.get(*args)
        slacktoken = db.value(
            db.source(),
            'slacktoken',
            database.BookmarkTable
        )

        if not slacktoken:
            self.setHidden(True)
            return False

        self.setHidden(False)
        return True


class RefreshButton(BaseControlButton):
    def __init__(self, parent=None):
        s = shortcuts.string(
            shortcuts.MainWidgetShortcuts,
            shortcuts.Refresh
        )
        super().__init__(
            'refresh',
            f'Refresh items  -  {s}',
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

        if any(
                (data[common.FileItem].refresh_needed,
                 data[common.SequenceItem].refresh_needed)
                ):
            return True

        return False
