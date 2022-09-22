# -*- coding: utf-8 -*-
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
        off_pixmap = images.ImageCache.get_rsc_pixmap(
            'icon_bw', common.color(common.TextSecondaryColor),
            common.size(common.WidthMargin))
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
                index.data(common.PathRole),
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


class SwitchBookmarkMenu(BaseQuickSwitchMenu):
    @common.error
    @common.debug
    def setup(self):
        self.add_menu()
        self.separator()
        self.add_switch_menu(
            common.BookmarkTab,
            'Switch active bookmark'
        )

    def add_menu(self):
        self.menu['add'] = {
            'icon': ui.get_icon('add', color=common.color(common.GreenColor)),
            'text': 'Add new bookmark...',
            'action': actions.show_add_bookmark,
            'shortcut': shortcuts.string(shortcuts.MainWidgetShortcuts,
                                         shortcuts.AddItem),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts,
                                          shortcuts.AddItem),
        }


class SwitchAssetMenu(BaseQuickSwitchMenu):
    @common.error
    @common.debug
    def setup(self):
        self.add_menu()
        self.separator()
        self.add_switch_menu(
            common.AssetTab,
            'Switch active asset'
        )

    def add_menu(self):
        self.menu['add'] = {
            'icon': ui.get_icon('add', color=common.color(common.GreenColor)),
            'text': 'Create new asset...',
            'action': actions.show_add_asset,
            'shortcut': shortcuts.string(shortcuts.MainWidgetShortcuts,
                                         shortcuts.AddItem),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts,
                                          shortcuts.AddItem),
        }
