"""Quick item switch menus used by the top bar.

"""
import functools

from PySide2 import QtGui, QtCore

from .. import actions
from .. import common
from .. import contextmenu
from .. import images
from .. import shortcuts
from .. import ui


class BaseQuickSwitchMenu(contextmenu.BaseContextMenu):
    """A context menu used to quickly change the active bookmark or asset.

    """

    def add_switch_menu(self, idx, label):
        """Adds the items needed to quickly change bookmarks or assets."""
        active_index = common.active_index(idx)
        if not common.model(idx).rowCount():
            return

        if common.current_tab() == common.BookmarkTab:
            off_icon = ui.get_icon(
                'bookmark_item',
                color=common.color(common.color_secondary_text)
            )
        elif common.current_tab() == common.AssetTab:
            off_icon = ui.get_icon(
                'asset_item',
                color=common.color(common.color_secondary_text)
            )
        elif common.current_tab() == common.FileTab:
            off_icon = ui.get_icon(
                'file_item',
                color=common.color(common.color_secondary_text)
            )
        elif common.current_tab() == common.FavouriteTab:
            off_icon = ui.get_icon(
                'favourite_item',
                color=common.color(common.color_secondary_text)
            )

        on_icon = ui.get_icon('check', color=common.color(common.color_green))


        self.menu[label] = {
            'disabled': True
        }

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
                index.data(common.PathRole),
                size=common.size(common.size_margin) * 4,
                fallback_thumb='icon_bw'
            )

            if pixmap and not pixmap.isNull():
                icon = QtGui.QIcon(pixmap)
            elif active:
                icon = on_icon
            else:
                icon = off_icon

            self.menu[name.upper()] = {
                'icon': icon,
                'action': functools.partial(common.widget(idx).activate, index)
            }


class SwitchBookmarkMenu(BaseQuickSwitchMenu):
    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.add_menu()
        self.separator()
        self.add_switch_menu(
            common.BookmarkTab,
            'Switch active bookmark'
        )

    def add_menu(self):
        self.menu['add'] = {
            'icon': ui.get_icon('add', color=common.color(common.color_green)),
            'text': 'Manage Bookmark Items...',
            'action': actions.show_bookmarker,
            'shortcut': shortcuts.string(shortcuts.MainWidgetShortcuts,
                                         shortcuts.AddItem),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts,
                                          shortcuts.AddItem),
        }


class SwitchAssetMenu(BaseQuickSwitchMenu):
    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.add_menu()
        self.separator()
        self.add_switch_menu(
            common.AssetTab,
            'Switch active asset'
        )

    def add_menu(self):
        self.menu['add'] = {
            'icon': ui.get_icon('add', color=common.color(common.color_green)),
            'text': 'Create new asset...',
            'action': actions.show_add_asset,
            'shortcut': shortcuts.string(shortcuts.MainWidgetShortcuts,
                                         shortcuts.AddItem),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts,
                                          shortcuts.AddItem),
        }
