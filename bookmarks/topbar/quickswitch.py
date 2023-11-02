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
            item_icon = ui.get_icon(
                'bookmark_item',
                color=common.color(common.color_secondary_text)
            )
        elif common.current_tab() == common.AssetTab:
            item_icon = ui.get_icon(
                'asset_item',
                color=common.color(common.color_secondary_text)
            )
        elif common.current_tab() == common.FileTab:
            item_icon = ui.get_icon(
                'file_item',
                color=common.color(common.color_secondary_text)
            )
        elif common.current_tab() == common.FavouriteTab:
            item_icon = ui.get_icon(
                'favourite_item',
                color=common.color(common.color_secondary_text)
            )

        on_icon = ui.get_icon('check', color=common.color(common.color_green))

        self.menu[label] = {
            'disabled': True
        }

        model = common.model(idx)
        for n in range(model.rowCount()):
            index = model.index(n, 0)

            pixmap, _ = images.get_thumbnail(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
                index.data(common.PathRole),
                size=common.size(common.size_margin) * 4,
                fallback_thumb='icon_bw'
            )
            if not pixmap or pixmap.isNull():
                icon = ui.get_icon('icon_bw')
            elif active_index.isValid() and active_index.data(common.PathRole) == index.data(common.PathRole):
                icon = on_icon
            else:
                icon = QtGui.QIcon(pixmap)

            name = index.data(QtCore.Qt.DisplayRole)
            self.menu[contextmenu.key()] = {
                'text': name,
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
            'Change bookmark'
        )

    def add_menu(self):
        self.menu['add'] = {
            'icon': ui.get_icon('add', color=common.color(common.color_green)),
            'text': 'Manage Bookmark Items...',
            'action': actions.show_bookmarker,
            'shortcut': shortcuts.string(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ),
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
            'shortcut': shortcuts.string(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ),
        }
