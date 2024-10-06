"""The base context menu implementation used across Bookmarks.

All context menus derive from the :class:`BaseContextMenu`. The class contains the 
definitions of all menu options. See :meth:`BaseContextMenu.setup` for menu overrides
and definitions. 

"""
import collections
import functools
import importlib
import json
import os
import uuid

from PySide2 import QtWidgets, QtGui, QtCore

from . import actions
from . import common
from . import database
from . import images
from . import shortcuts
from . import ui
from .external import rv
from .shotgun import actions as sg_actions
from .shotgun import shotgun


def key():
    """Utility method used to generate a hexadecimal uuid string."""
    return uuid.uuid1().hex


def resize_event_override(cls, event):
    """Private utility method used to implement rounded corners.

    """
    path = QtGui.QPainterPath()

    # the rectangle must be translated and adjusted by 1 pixel to correctly
    # map the rounded shape
    rect = QtCore.QRectF(cls.rect()).adjusted(0.5, 0.5, -1.5, -1.5)
    o = int(common.Size.Indicator(1.5))
    path.addRoundedRect(rect, o, o)

    # QRegion is bitmap based, so the returned QPolygonF (which uses float values must
    # be transformed to an integer based QPolygon
    region = QtGui.QRegion(path.toFillPolygon(QtGui.QTransform()).toPolygon())
    cls.setMask(region)


def show_event_override(cls, event):
    """Private utility method for manually calculating the width of
    :class:.`BaseContextMenu`.

    I might be misunderstanding how styling menus effect appearance and resulting
    size. What is certain, that QT doesn't seem to be able to display the menus
    with a correct width, and hence we'll calculate width manually here.

    """
    widths = []
    metrics = QtGui.QFontMetrics(cls.font())

    menu_height = common.Size.Margin(2.0)
    icon_padding = common.Size.Margin()

    show_icons = common.settings.value('settings/show_menu_icons')
    show_icons = not show_icons if show_icons is not None else True

    for action in cls.actions():
        w = 0
        w += menu_height
        if show_icons:
            w += icon_padding
        if action.text():
            w += metrics.horizontalAdvance(action.text())
        if action.shortcut() and action.shortcut().toString(
                format=QtGui.QKeySequence.NativeText
        ):
            w += icon_padding
            w += metrics.horizontalAdvance(
                action.shortcut().toString(
                    format=QtGui.QKeySequence.NativeText
                )
            )
        w += menu_height
        widths.append(int(w))

    if not widths:
        return

    cls.setFixedWidth(max(widths))


class BaseContextMenu(QtWidgets.QMenu):
    """Base class containing the context menu definitions.

    The internal menu structure is defined in :attr:`BaseContextMenu.menu`,
    a `collections.OrderedDict` instance. This data is populated by the *_menu methods
    and expanded into a UI layout by :meth:`BaseContextMenu.create_menu`. The menu is
    principally designed to work with index-based views and as a result the default
    constructor takes a QModelIndex, stored in :attr:`BaseContextMenu.index`.

    The internal :attr:`BaseContextMenu.menu` dict object assumes the following form:

    .. code-block:: python
        :linenos:

        self.menu = collections.OrderedDict({
            'uuid1': {
                'text': 'My Menu Item',
                'icon': get_icon('my_menu_icon'),   # QIcon
                'shortcut: QtGui.QShortcut('Ctrl+M'), # QtGui.QShortcut
                'disabled': False,
                'action': my_menu_function1,         # a method to execute
            },
            'uuid2': {
                'text': 'My Menu Item2',
                'icon': get_icon('my_menu_icon'),
                'shortcut: QtGui.QShortcut('Ctrl+N'),
                'disabled': True,
                'action': my_menu_function2,
            }
        })

    Properties:
        index (QModelIndex): The index the context menu is associated with.

    """

    def __init__(self, index, parent=None):
        super().__init__(parent=parent)
        self.index = index
        self.menu = collections.OrderedDict()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setTearOffEnabled(False)
        self.setSeparatorsCollapsible(True)
        self.setToolTipsVisible(True)

        self.setup()
        self.create_menu(self.menu)

    @common.debug
    @common.error
    def setup(self):
        """Creates the context menu.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    @common.debug
    @common.error
    def create_menu(self, menu, parent=None):
        """Expands the internal :attr:`BaseContextMenu.menu` dict data.

        """
        show_icons = common.settings.value('settings/show_menu_icons')
        show_icons = not show_icons if show_icons is not None else True

        if not parent:
            parent = self

        for k, v in menu.items():
            if ':' in k:
                continue

            if isinstance(v, collections.OrderedDict):
                submenu = QtWidgets.QMenu(k, parent=parent)
                submenu.create_menu = self.create_menu
                submenu.showEvent = functools.partial(
                    show_event_override, submenu
                )
                submenu.resizeEvent = functools.partial(
                    resize_event_override, submenu
                )

                if f'{k}:icon' in menu and show_icons:
                    submenu.setIcon(menu[f'{k}:icon'])
                if f'{k}:text' in menu:
                    submenu.setTitle(menu[f'{k}:text'])

                if f'{k}:action' in menu:
                    name = menu[f'{k}:text'] if f'{k}:text' in menu else k
                    icon = menu[f'{k}:icon'] if f'{k}:icon' in menu and show_icons \
                        else QtGui.QIcon()
                    shortcut = menu[f'{k}:shortcut'] if f'{k}:shortcut' in menu else None

                    action = submenu.addAction(name)
                    action.setIconVisibleInMenu(True)

                    if show_icons:
                        action.setIcon(icon)

                    if shortcut:
                        action.setShortcutVisibleInContextMenu(True)
                        action.setShortcut(shortcut)
                        action.setShortcutContext(
                            QtCore.Qt.WidgetWithChildrenShortcut
                        )

                    if isinstance(v, collections.Iterable):
                        for func in menu[f'{k}:action']:
                            action.triggered.connect(func)
                    else:
                        action.triggered.connect(v)
                    action.addAction(action)
                    submenu.addSeparator()

                parent.addMenu(submenu)
                parent.create_menu(v, parent=submenu)
            else:
                if 'separator' in k:
                    parent.addSeparator()
                    continue

                action = parent.addAction(k)

                if 'data' in v:  # Skipping disabled items
                    action.setData(v['data'])
                if 'disabled' in v:  # Skipping disabled items
                    action.setDisabled(v['disabled'])
                if 'action' in v:
                    if isinstance(v['action'], (list, tuple)):
                        for func in v['action']:
                            action.triggered.connect(func)
                    else:
                        action.triggered.connect(v['action'])
                if 'text' in v:
                    action.setText(v['text'])
                else:
                    action.setText(k)
                if 'description' in v and v['description']:
                    action.setToolTip(v['description'])
                    action.setStatusTip(v['description'])
                    action.setWhatsThis(v['description'])
                if 'checkable' in v:
                    action.setCheckable(v['checkable'])
                if 'checked' in v:
                    action.setChecked(v['checked'])
                if 'icon' in v and isinstance(v['icon'], QtGui.QIcon) and show_icons:
                    action.setIconVisibleInMenu(True)
                    action.setIcon(v['icon'])
                if 'shortcut' in v and v['shortcut']:
                    action.setShortcutVisibleInContextMenu(True)
                    action.setShortcut(v['shortcut'])
                    action.setShortcutContext(
                        QtCore.Qt.WidgetWithChildrenShortcut
                    )
                if 'visible' in v:
                    action.setVisible(v['visible'])
                else:
                    action.setVisible(True)

    def resizeEvent(self, event):
        resize_event_override(self, event)

    def showEvent(self, event):
        """Show event handler.

        """
        show_event_override(self, event)

    def separator(self, menu=None):
        """Adds a menu separator item.

        Args:
            menu (str): Specify menu key.

        """
        if menu is None:
            menu = self.menu
        menu['separator' + key()] = None

    def window_menu(self):
        """General app window specific actions.

        """
        if common.init_mode != common.StandaloneMode:
            return

        w = self.parent().window()
        on_top_active = w.windowFlags() & QtCore.Qt.WindowStaysOnTopHint

        on_icon = ui.get_icon('check', color=common.Color.Green())
        logo_icon = ui.get_icon('icon')

        k = 'Window'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = logo_icon

        try:
            self.menu[k][key()] = {
                'text': 'New Window...',
                'icon': logo_icon,
                'action': actions.exec_instance,
                'shortcut': shortcuts.get(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.OpenNewInstance
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.OpenNewInstance
                ),
            }

            self.separator(self.menu[k])
        except:
            pass

        self.menu[k][key()] = {
            'text': 'Always on Top',
            'icon': on_icon if on_top_active else None,
            'action': actions.toggle_stays_always_on_top
        }

        self.separator(self.menu[k])

        w = self.parent().window()
        try:
            maximised = w.isMaximized()
            minimised = w.isMinimized()
            full_screen = w.isFullScreen()
            self.menu[k][key()] = {
                'text': 'Maximise',
                'icon': on_icon if maximised else None,
                'action': actions.toggle_maximized,
                'shortcut': shortcuts.get(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.Maximize
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.Maximize
                ),
            }
            self.menu[k][key()] = {
                'text': 'Minimise',
                'icon': on_icon if minimised else None,
                'action': actions.toggle_minimized,
                'shortcut': shortcuts.get(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.Minimize
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.Minimize
                ),
            }
            self.menu[k][key()] = {
                'text': 'Full Screen',
                'icon': on_icon if full_screen else None,
                'action': actions.toggle_full_screen,
                'shortcut': shortcuts.get(
                    shortcuts.MainWidgetShortcuts, shortcuts.FullScreen
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.MainWidgetShortcuts, shortcuts.FullScreen
                ),
            }
        except:
            pass

    def sort_menu(self):
        """List item sorting options.

        """
        item_on_icon = ui.get_icon('check', color=common.Color.Green())

        m = self.parent().model().sourceModel()
        sort_order = m.sort_order()
        sort_by = m.sort_by()

        k = 'Sort List'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('sort')

        self.menu[k][key()] = {
            'text': 'Ascending' if not sort_order else 'Descending',
            'icon': ui.get_icon('arrow_down') if not sort_order else ui.get_icon(
                'arrow_up'
            ),
            'action': actions.toggle_sort_order,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleSortOrder
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleSortOrder
            ),
        }

        self.separator(self.menu[k])

        for _k, v in common.DEFAULT_SORT_VALUES.items():
            self.menu[k][key()] = {
                'text': v,
                'icon': item_on_icon if sort_by == _k else None,
                'action': functools.partial(
                    actions.change_sorting,
                    _k,
                    sort_order
                )
            }

    def reveal_item_menu(self):
        """List item file reveal options.

        """
        if not self.index.isValid() or not self.index.data(common.PathRole):
            if common.current_tab() == common.BookmarkTab:
                return
            elif common.current_tab() == common.AssetTab:
                p = common.active('root', path=True)
            elif common.current_tab() == common.FileTab:
                p = common.active('asset', path=True)
            else:
                return
        else:
            p = self.index.data(common.PathRole)

        path = common.get_sequence_start_path(p)

        self.menu[key()] = {
            'text': 'Show Item in File Manager',
            'icon': ui.get_icon('folder'),
            'action': functools.partial(actions.reveal, path),
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.RevealItem
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.RevealItem
            ),
        }
        return

    def bookmark_url_menu(self):
        """Bookmark item URL actions.

        """
        if not self.index.isValid():
            return
        if not self.index.data(common.PathRole):
            return

        server, job, root = self.index.data(common.ParentPathRole)[0:3]

        db = database.get(server, job, root)
        primary_url = db.value(
            db.source(),
            'url1',
            database.BookmarkTable
        )
        secondary_url = db.value(
            db.source(),
            'url2',
            database.BookmarkTable
        )

        if not any((primary_url, secondary_url)):
            return

        k = 'Links'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('link')

        if primary_url:
            self.menu[k][key()] = {
                'text': primary_url,
                'icon': ui.get_icon('link'),
                'action': lambda: QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl(primary_url)
                ),
            }
        if secondary_url:
            self.menu[k][key()] = {
                'text': secondary_url,
                'icon': ui.get_icon('link'),
                'action': lambda: QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl(secondary_url)
                )
            }

        self.separator(self.menu[k])

    def asset_url_menu(self):
        """Asset item URL actions.

        """
        if not self.index.isValid():
            return
        if not self.index.data(common.PathRole):
            return
        if len(self.index.data(common.ParentPathRole)) < 4:
            return

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        asset = self.index.data(common.ParentPathRole)[3]

        db = database.get(server, job, root)
        primary_url = db.value(db.source(asset), 'url1', database.AssetTable)
        secondary_url = db.value(db.source(asset), 'url2', database.AssetTable)

        k = 'Links'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('link')

        if not any((primary_url, secondary_url)):
            return

        if primary_url:
            self.menu[k][key()] = {
                'text': primary_url,
                'icon': ui.get_icon('link'),
                'action': lambda: QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl(primary_url)
                ),
            }
        if secondary_url:
            self.menu[k][key()] = {
                'text': secondary_url,
                'icon': ui.get_icon('link'),
                'action': lambda: QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl(secondary_url)
                )
            }

        self.separator(self.menu[k])

    def copy_menu(self):
        """List item path copy actions.

        """
        if not self.index.isValid():
            return

        max_width = common.Size.DefaultWidth(0.4)

        k = 'Copy Path'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('copy')

        path = self.index.data(common.PathRole)
        metrics = QtGui.QFontMetrics(self.font())
        for mode in (
                common.WindowsPath, common.MacOSPath, common.UnixPath):
            m = key()
            n = actions.copy_path(path, mode=mode, copy=False)

            if metrics.horizontalAdvance(n) > max_width:
                n = metrics.elidedText(n, QtCore.Qt.ElideMiddle, max_width)

            self.menu[k][m] = {
                'text': n,
                'icon': ui.get_icon(
                    'copy', color=common.Color.VeryDarkBackground()
                ),
                'action': functools.partial(actions.copy_path, path, mode=mode),
            }

            # Windows/MacOS
            if common.get_platform() == mode:
                self.menu[k][m]['shortcut'] = shortcuts.get(
                    shortcuts.MainWidgetShortcuts, shortcuts.CopyItemPath
                ).key()
                self.menu[k][m]['description'] = shortcuts.hint(
                    shortcuts.MainWidgetShortcuts, shortcuts.CopyItemPath
                )
            elif mode == common.UnixPath:
                self.menu[k][m]['shortcut'] = shortcuts.get(
                    shortcuts.MainWidgetShortcuts, shortcuts.CopyAltItemPath
                ).key()
                self.menu[k][m]['description'] = shortcuts.hint(
                    shortcuts.MainWidgetShortcuts, shortcuts.CopyAltItemPath
                )

        self.separator(self.menu[k])

        # Houdini $JOB relative path
        p = '/'.join(self.index.data(common.ParentPathRole)[0:4])
        path = path.replace(p, '').strip('/')
        if not path:
            return

        path = f'$JOB/{path}'
        if metrics.horizontalAdvance(path) > max_width:
            n = metrics.elidedText(path, QtCore.Qt.ElideMiddle, max_width)

        self.menu[k][m] = {
            'text': n,
            'icon': ui.get_icon('hip', color=None, resource=common.FormatResource),
            'action': functools.partial(actions.copy_path, path, mode=None),
        }

    def toggle_item_flags_menu(self):
        """List item filter flag toggle actions.

        """
        if not self.index.isValid():
            return

        on_icon = ui.get_icon('check', color=common.Color.Green())
        favourite_icon = ui.get_icon('favourite')
        archived_icon = ui.get_icon('archivedVisible')

        favourite = self.index.flags() & common.MarkedAsFavourite
        archived = self.index.flags() & common.MarkedAsArchived

        text = 'Toggle Archived'

        k = 'Flags'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('flag')

        self.menu[k][key()] = {
            'text': text,
            'icon': archived_icon if not archived else on_icon,
            'checkable': False,
            'action': actions.toggle_archived,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleItemArchived
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleItemArchived
            ),
        }
        self.menu[k][key()] = {
            'text': 'Toggle Favourite',
            'icon': favourite_icon if not favourite else on_icon,
            'checkable': False,
            'action': actions.toggle_favourite,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleItemFavourite
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleItemFavourite
            ),
        }
        return

    def asset_progress_menu(self):
        on_icon = ui.get_icon('showbuttons')
        off_icon = ui.get_icon('showbuttons', color=common.Color.Green())
        icon = on_icon if self.parent().progress_hidden() else off_icon
        t = 'Show' if self.parent().progress_hidden() else 'Hide'

        self.separator()

        self.menu[key()] = {
            'text': f'{t} Progress Tracker',
            'icon': icon,
            'action': actions.toggle_progress_columns,
        }

        self.separator()

    def list_filter_menu(self):
        """List item filter actions.

        """
        item_on = ui.get_icon('check', color=common.Color.Green())
        item_off = None

        k = 'List Filters'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('filter')

        self.menu[k]['EditSearchFilter'] = {
            'text': 'Edit Search Filter...',
            'icon': ui.get_icon('filter'),
            'action': actions.toggle_filter_editor,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleSearch
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleSearch
            ),
        }

        proxy = self.parent().model()
        favourite = proxy.filter_flag(common.MarkedAsFavourite)
        archived = proxy.filter_flag(common.MarkedAsArchived)
        active = proxy.filter_flag(common.MarkedAsActive)

        s = (favourite, archived, active)
        all_off = all([not f for f in s])

        if active or all_off:
            self.menu[k][key()] = {
                'text': 'Show Active Item',
                'icon': item_on if active else item_off,
                'disabled': favourite,
                'action': functools.partial(
                    actions.toggle_flag, common.MarkedAsActive, not active
                ),
                'shortcut': shortcuts.get(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.ToggleActive
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.ToggleActive
                ),
            }
        if favourite or all_off:
            self.menu[k][key()] = {
                'text': 'Show Favourites',
                'icon': item_on if favourite else item_off,
                'disabled': active,
                'action': functools.partial(
                    actions.toggle_flag, common.MarkedAsFavourite, not favourite
                ),
                'shortcut': shortcuts.get(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.ToggleFavourite
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.ToggleFavourite
                ),
            }
        if archived or all_off:
            self.menu[k][key()] = {
                'text': 'Show Archived',
                'icon': item_on if archived else item_off,
                'disabled': active if active else favourite,
                'action': functools.partial(
                    actions.toggle_flag, common.MarkedAsArchived, not archived
                ),
                'shortcut': shortcuts.get(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.ToggleArchived
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.MainWidgetShortcuts,
                    shortcuts.ToggleArchived
                ),
            }

    def row_size_menu(self):
        """List item row size actions.

        """
        k = 'Change Row Height'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('expand')

        self.menu[k][key()] = {
            'text': 'Increase',
            'icon': ui.get_icon('arrow_up'),
            'action': actions.increase_row_size,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.RowIncrease
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.RowIncrease
            ),
        }
        self.menu[k][key()] = {
            'text': 'Decrease',
            'icon': ui.get_icon('arrow_down'),
            'action': actions.decrease_row_size,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.RowDecrease
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.RowDecrease
            ),
        }
        self.menu[k][key()] = {
            'text': 'Reset',
            'icon': ui.get_icon('minimize'),
            'action': actions.reset_row_size,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.RowReset
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.RowReset
            ),
        }

    def refresh_menu(self):
        """List item reload/refresh options.

        """
        self.menu[key()] = {
            'text': 'Refresh List',
            'action': actions.refresh,
            'icon': ui.get_icon('refresh'),
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.Refresh
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.Refresh
            ),
        }

    def preferences_menu(self):
        """Application preferences actions.

        """
        self.menu[key()] = {
            'text': 'Preferences...',
            'action': actions.show_preferences,
            'icon': ui.get_icon('settings'),
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.OpenPreferences
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.OpenPreferences
            ),
        }

    def quit_menu(self):
        """Application shutdown options.

        """
        if common.init_mode != common.StandaloneMode:
            return

        self.menu[key()] = {
            'text': f'Quit {common.product.title()}',
            'action': common.shutdown,
            'icon': ui.get_icon('close'),
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.Quit
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.Quit
            )
        }

    def thumbnail_menu(self):
        """Thumbnail image specific actions.

        """
        if not self.index.isValid():
            return

        self.menu[key()] = {
            'text': 'Thumbnail',
            'disabled': True,
        }

        self.separator()

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        item_thumbnail_path = images.get_cached_thumbnail_path(
            server,
            job,
            root,
            self.index.data(common.PathRole),
        )
        thumbnail_path = images.get_thumbnail(
            server,
            job,
            root,
            self.index.data(common.PathRole),
            fallback_thumb=self.parent().itemDelegate().fallback_thumb,
            get_path=True
        )

        self.menu[key()] = {
            'text': 'Preview Thumbnail',
            'icon': ui.get_icon('image'),
            'action': actions.preview_thumbnail
        }

        ext = QtCore.QFileInfo(self.index.data(common.PathRole)).suffix().lower()
        if ext in images.get_oiio_extensions():
            self.menu[key()] = {
                'text': 'Preview Image',
                'icon': ui.get_icon('image'),
                'action': actions.preview_image
            }

        self.separator()

        self.menu[key()] = {
            'text': 'Capture Screen...',
            'icon': ui.get_icon('capture_thumbnail'),
            'action': actions.capture_thumbnail
        }

        self.menu[key()] = {
            'text': 'Pick Thumbnail File...',
            'icon': ui.get_icon('image'),
            'action': actions.pick_thumbnail_from_file
        }

        self.menu[key()] = {
            'text': 'Pick Thumbnail From Library...',
            'icon': ui.get_icon('image'),
            'action': actions.pick_thumbnail_from_library
        }

        self.separator()

        if (
                QtCore.QFileInfo(item_thumbnail_path).exists() and
                f'{server}/{job}/{root}' in item_thumbnail_path
        ):
            self.menu[key()] = {
                'text': 'Reveal Thumbnail...',
                'action': functools.partial(
                    actions.reveal,
                    item_thumbnail_path,
                )
            }

            self.separator()

            self.menu[key()] = {
                'text': 'Remove Thumbnail',
                'action': actions.remove_thumbnail,
                'icon': ui.get_icon('close', color=common.Color.Red())
            }
        elif (
                QtCore.QFileInfo(thumbnail_path).exists() and
                f'{server}/{job}/{root}' in thumbnail_path
        ):
            self.menu[key()] = {
                'text': 'Reveal File...',
                'action': functools.partial(
                    actions.reveal,
                    thumbnail_path,
                )
            }

    def bookmark_editor_menu(self):
        """Bookmark item properties editor.

        """
        icon = ui.get_icon('add', color=common.Color.Green())
        self.menu[key()] = {
            'text': 'Add Bookmarks...',
            'icon': icon,
            'action': actions.show_servers_editor,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ),
        }

    def add_asset_to_bookmark_menu(self):
        """Add asset to bookmark item actions.

        """
        if not self.index.isValid():
            return
        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        self.menu[key()] = {
            'text': 'Add Asset...',
            'icon': ui.get_icon('add'),
            'action': functools.partial(
                actions.show_add_asset, server=server, job=job, root=root
            ),
        }

    def collapse_sequence_menu(self):
        """File item collapse toggle actions.

        """
        expand_pixmap = ui.get_icon('expand')
        collapse_pixmap = ui.get_icon('collapse', common.Color.Green())

        current_type = self.parent().model().sourceModel().data_type()
        groupped = current_type == common.SequenceItem

        self.menu[key()] = {
            'text': 'Show Sequences' if groupped else 'Show Files',
            'icon': expand_pixmap if groupped else collapse_pixmap,
            'checkable': False,
            'action': common.signals.toggleSequenceButton,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleSequence
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ToggleSequence
            ),
        }

    def task_folder_toggle_menu(self):
        """File item task folder picker menu.

        """
        if not common.active('asset'):
            return

        item_on_pixmap = ui.get_icon('check', color=common.Color.Green())
        item_off_pixmap = ui.get_icon('folder')

        k = 'Select asset folder...'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon(
            'folder', color=common.Color.Green()
        )

        model = common.source_model(common.FileTab)
        path = common.active('asset', path=True)
        task = model.task()

        if not path:
            return

        _dir = QtCore.QDir(path)
        _dir.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)

        for name in sorted(_dir.entryList()):
            if task:
                checked = task == name
            else:
                checked = False
            self.menu[k][key()] = {
                'text': name,
                'icon': item_on_pixmap if checked else item_off_pixmap,
                'action': functools.partial(
                    common.signals.taskFolderChanged.emit, name
                )
            }

        self.separator(self.menu[k])

        self.menu[k][key()] = {
            'text': 'Deselect',
            'action': functools.partial(common.signals.taskFolderChanged.emit, None)
        }

    def remove_favourite_menu(self):
        """List item favourite actions.

        """
        self.menu[key()] = {
            'text': 'Remove from starred...',
            'icon': ui.get_icon('close', color=common.Color.Red()),
            'checkable': False,
            'action': actions.toggle_favourite
        }

    def control_favourites_menu(self):
        """Favourite item actions.

        """
        remove_icon = ui.get_icon('close')

        self.menu[key()] = {
            'text': 'Export starred...',
            'checkable': False,
            'action': actions.export_favourites
        }
        self.menu[key()] = {
            'text': 'Import starred...',
            'checkable': False,
            'action': actions.import_favourites,
        }

        self.separator()

        self.menu[key()] = {
            'text': 'Clear starred',
            'icon': remove_icon,
            'checkable': False,
            'action': actions.clear_favourites
        }

    def add_file_menu(self):
        """Add file actions.

        """
        self.menu[key()] = {
            'text': 'Add File...',
            'icon': ui.get_icon('add', color=common.Color.Green()),
            'action': actions.show_add_file,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ),
        }

    def add_file_to_asset_menu(self):
        """Add file to asset actions.

        """
        if not self.index.isValid():
            return

        asset = self.index.data(common.ParentPathRole)[3]
        self.menu[key()] = {
            'text': 'Add Template File...',
            'icon': ui.get_icon('add', color=common.Color.Green()),
            'action': functools.partial(actions.show_add_file, asset=asset)
        }

    def notes_menu(self):
        """Note editor actions.

        """
        if not self.index.isValid():
            return

        self.menu[key()] = {
            'text': 'Notes',
            'icon': ui.get_icon('todo'),
            'action': actions.show_notes,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.OpenTodo
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.OpenTodo
            ),
        }

    def edit_selected_bookmark_menu(self):
        """Bookmark item properties editor actions.

        """
        if not self.index.isValid():
            return

        settings_icon = ui.get_icon('settings')
        server, job, root = self.index.data(common.ParentPathRole)[0:3]

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit bookmark properties...',
            'icon': settings_icon,
            'action': functools.partial(
                actions.edit_bookmark, server=server, job=job, root=root
            ),
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.EditItem
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.EditItem
            ),
        }

    def edit_active_bookmark_menu(self):
        """Active bookmark item property menu.

        """
        settings_icon = ui.get_icon('settings')

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit bookmark properties...',
            'icon': settings_icon,
            'action': actions.edit_bookmark,
        }

    def edit_selected_asset_menu(self):
        """Selected asset item property menu.

        """
        if not self.index.isValid():
            return

        settings_icon = ui.get_icon('settings')
        asset = self.index.data(common.ParentPathRole)[3]

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit asset properties...',
            'icon': settings_icon,
            'action': functools.partial(actions.edit_asset, asset=asset),
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.EditItem
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.EditItem
            ),
        }

    def edit_active_asset_menu(self):
        """Selected asset item property menu.

        """
        settings_icon = ui.get_icon('settings')

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit asset properties...',
            'icon': settings_icon,
            'action': actions.edit_asset,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.EditItem
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.EditItem
            ),
        }

    def edit_selected_file_menu(self):
        """Selected file item property menu.

        """
        if not self.index.isValid():
            return

        settings_icon = ui.get_icon('settings')
        _file = self.index.data(common.PathRole)

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit File Properties...',
            'icon': settings_icon,
            'action': functools.partial(actions.edit_file, _file),
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.EditItem
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.EditItem
            ),
        }

    def show_add_asset_menu(self):
        """Add asset menu actions.

        """
        add_pixmap = ui.get_icon('add', color=common.Color.Green())
        self.menu[key()] = {
            'icon': add_pixmap,
            'text': 'Add Asset...',
            'action': actions.show_add_asset,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.AddItem
            ),
        }

    def launcher_menu(self):
        """Application launcher menu actions.

        """
        self.menu[key()] = {
            'icon': ui.get_icon('icon'),
            'text': 'Application Launcher',
            'action': actions.pick_launcher_item,
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.ApplicationLauncher
            ).key(),
        }

    def sg_thumbnail_menu(self):
        """ShotGrid thumbnail image menu actions.

        """
        if not self.index.isValid():
            return

        p = self.index.data(common.ParentPathRole)
        source = self.index.data(common.PathRole)
        server, job, root = p[0:3]
        asset = p[3] if len(p) > 3 else None

        sg_properties = shotgun.SGProperties(server, job, root, asset)
        sg_properties.init()
        if not sg_properties.verify():
            return

        thumbnail_path = images.get_thumbnail(
            server,
            job,
            root,
            source,
            fallback_thumb=self.parent().itemDelegate().fallback_thumb,
            get_path=True
        )

        if not QtCore.QFileInfo(thumbnail_path).exists():
            return

        k = 'ShotGrid'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('sg')

        self.menu[k][key()] = {
            'text': 'Upload Thumbnail to ShotGrid...',
            'action': functools.partial(
                sg_actions.upload_thumbnail, sg_properties, thumbnail_path
            ),
            'icon': ui.get_icon('sg', color=common.Color.Green()),
        }

    def sg_url_menu(self):
        """ShotGrid URL menu actions.

        """
        if not self.index.isValid():
            return
        if not self.index.data(common.PathRole):
            return

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        if len(self.index.data(common.ParentPathRole)) >= 4:
            asset = self.index.data(common.ParentPathRole)[3]
        else:
            asset = None

        sg_properties = shotgun.SGProperties(server, job, root, asset)
        sg_properties.init()
        if not sg_properties.verify():
            return

        k = 'ShotGrid'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('sg')

        self.separator(self.menu[k])

        for url in reversed(sg_properties.urls()):
            self.menu[k][key()] = {
                'text': url,
                'icon': ui.get_icon('sg'),
                'action': functools.partial(
                    QtGui.QDesktopServices.openUrl, QtCore.QUrl(url)
                )
            }

    def sg_link_bookmark_menu(self):
        """ShotGrid bookmark item menu actions.

        """
        if not self.index.isValid():
            return

        server, job, root = self.index.data(common.ParentPathRole)[0:3]

        sg_properties = shotgun.SGProperties(server, job, root)
        sg_properties.init()
        if not sg_properties.verify(connection=True):
            return

        k = 'ShotGrid'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('sg')

        self.menu[k][key()] = {
            'text': 'Link Bookmark with ShotGrid...',
            'icon': ui.get_icon('sg'),
            'action': functools.partial(
                sg_actions.link_bookmark_entity, server, job, root
            ),
        }

    def sg_link_asset_menu(self):
        """ShotGrid asset linker menu actions.

        """
        if not self.index.isValid():
            return
        if len(self.index.data(common.ParentPathRole)) < 4:
            return

        sg_properties = shotgun.SGProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(bookmark=True):
            return

        k = 'ShotGrid'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('sg')

        server, job, root, asset = self.index.data(common.ParentPathRole)[0:4]
        for entity_type in ('Asset', 'Shot', 'Sequence'):
            self.menu[k][key()] = {
                'text': f'Link item with ShotGrid {entity_type.title()}',
                'icon': ui.get_icon('sg'),
                'action': functools.partial(
                    sg_actions.link_asset_entity, server, job, root, asset,
                    entity_type
                ),
            }

    def sg_link_assets_menu(self):
        """ShotGrid batch asset linker menu actions.

        """
        sg_properties = shotgun.SGProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(bookmark=True):
            return

        k = 'ShotGrid'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('sg')

        self.separator(self.menu[k])
        self.menu[k][key()] = {
            'text': 'Link Assets with ShotGrid',
            'icon': ui.get_icon('sg', color=common.Color.Green()),
            'action': sg_actions.link_assets,
        }

        self.separator(self.menu[k])

    def sg_rv_menu(self):
        """ShotGrid RV menu actions.

        """
        if not self.index.isValid():
            return

        if not common.get_binary('rv'):
            return

        k = 'RV'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('sg')

        path = common.get_sequence_start_path(
            self.index.data(common.PathRole)
        )

        self.menu[k][key()] = {
            'text': 'Play',
            'icon': ui.get_icon('sg'),
            'action': functools.partial(rv.execute_rvpush_command, path, rv.PushAndClear),
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.PushToRV
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.PushToRV
            ),
        }
        self.menu[k][key()] = {
            'text': 'Play full-screen',
            'icon': ui.get_icon('sg'),
            'action': functools.partial(rv.execute_rvpush_command, path, rv.PushAndClearFullScreen),
            'shortcut': shortcuts.get(
                shortcuts.MainWidgetShortcuts,
                shortcuts.PushToRVFullScreen
            ).key(),
            'description': shortcuts.hint(
                shortcuts.MainWidgetShortcuts,
                shortcuts.PushToRVFullScreen
            ),
        }

        self.separator(self.menu[k])

        self.menu[k][key()] = {
            'text': 'Add as source',
            'icon': ui.get_icon('sg'),
            'action': functools.partial(rv.execute_rvpush_command, path, rv.Add)
        }

        self.separator(self.menu[k])

    def sg_publish_menu(self):
        """ShotGrid publish menu actions.

        """
        sg_properties = shotgun.SGProperties(active=True)
        sg_properties.init()

        if not sg_properties.verify():
            return

        k = 'ShotGrid'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('sg')

        self.separator(self.menu[k])

        self.menu[k][key()] = {
            'text': 'Publish Video',
            'icon': ui.get_icon('sg', color=common.Color.Green()),
            'action': functools.partial(sg_actions.publish, formats=('mp4', 'mov')),
        }

        self.separator(self.menu[k])

    def sg_browse_tasks_menu(self):
        """ShotGrid publish menu actions.

        """
        sg_properties = shotgun.SGProperties(active=True)
        sg_properties.init()

        if not sg_properties.verify():
            return

        k = 'ShotGrid'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('sg')

        self.separator(self.menu[k])

        self.menu[k][key()] = {
            'text': 'Browse Tasks',
            'icon': ui.get_icon('sg'),
            'action': sg_actions.show_task_picker,
        }

        self.separator(self.menu[k])

    def convert_menu(self):
        """FFMpeg convert menu.

        """
        if not self.index.isValid():
            return

        path = self.index.data(common.PathRole)
        # Only sequence items can be converted
        if not common.is_collapsed(path) and not common.get_sequence(path):
            return

        # Only image sequences can be converted
        ext = QtCore.QFileInfo(path).suffix()
        # Skip videos
        if ext in ('mp4', 'mov', 'avi', 'm4v'):
            return
        if ext.lower() not in images.get_oiio_extensions():
            return

        # AkaConvert
        from .external import akaconvert
        if akaconvert.KEY in os.environ and os.environ[akaconvert.KEY]:
            self.menu[key()] = {
                'text': 'AkaConvert...',
                'icon': ui.get_icon('studioaka', color=common.Color.Blue()),
                'action': actions.convert_image_sequence_with_akaconvert
            }

        # Can only convert when FFMpeg is present
        if not common.get_binary('ffmpeg'):
            return

        self.menu[key()] = {
            'text': 'Convert Sequence...',
            'icon': ui.get_icon('convert'),
            'action': actions.convert_image_sequence
        }

        self.separator()

    def delete_selected_files_menu(self):
        """Delete file item menu actions.

        """
        if not self.index.isValid():
            return

        self.menu[key()] = {
            'icon': ui.get_icon('close', color=common.Color.Red()),
            'text': 'Delete',
            'action': actions.delete_selected_files,
        }

    def publish_menu(self):
        """Publish file item menu actions.

        """
        pixmap = ui.get_icon('file', color=common.Color.Green())
        self.menu[key()] = {
            'icon': pixmap,
            'text': 'Publish...',
            'action': actions.show_publish_widget,
        }

    def import_export_properties_menu(self):
        """Export property

        """
        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('settings')

        self.separator(menu=self.menu[k])

        # Copy / paste menu
        if self.index.isValid():
            pp = self.index.data(common.ParentPathRole)

            clipboard = None
            if len(pp) == 3:
                clipboard = common.BookmarkPropertyClipboard
            elif len(pp) == 4:
                clipboard = common.AssetPropertyClipboard

            # Copy menu
            if clipboard is not None:
                self.menu[k][key()] = {
                    'text': 'Copy Properties to Clipboard...',
                    'action': actions.copy_properties,
                    'icon': ui.get_icon('settings'),
                    'shortcut': shortcuts.get(
                        shortcuts.MainWidgetShortcuts,
                        shortcuts.CopyProperties
                    ).key(),
                    'description': shortcuts.hint(
                        shortcuts.MainWidgetShortcuts,
                        shortcuts.CopyProperties
                    ),
                }

                # Paste menu
                if common.CLIPBOARD[clipboard]:
                    self.menu[k][key()] = {
                        'text': 'Paste Properties from Clipboard',
                        'action': actions.paste_properties,
                        'icon': ui.get_icon('settings'),
                        'shortcut': shortcuts.get(
                            shortcuts.MainWidgetShortcuts,
                            shortcuts.PasteProperties
                        ).key(),
                        'description': shortcuts.hint(
                            shortcuts.MainWidgetShortcuts,
                            shortcuts.PasteProperties
                        ),
                    }

        self.separator(menu=self.menu[k])
        if self.index.isValid():
            self.menu[k][key()] = {
                'text': 'Export properties...',
                'action': actions.export_properties,
                'icon': ui.get_icon('branch_closed')
            }

            self.menu[k][key()] = {
                'text': 'Import properties...',
                'action': actions.import_properties,
                'icon': ui.get_icon('branch_backwards')
            }

        self.separator(menu=self.menu[k])

        self.menu[k][key()] = {
            'text': 'Import asset properties from json...',
            'action': actions.import_json_asset_properties,
            'icon': ui.get_icon('branch_backwards')
        }

        self.separator(menu=self.menu[k])

    def scripts_menu(self):
        """Custom scripts deployed with the Maya module.

        """
        k = 'Scripts'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('icon')

        p = os.path.normpath(f'{__file__}/../scripts/scripts.json')
        if not os.path.isfile(p):
            raise RuntimeError(f'File not found: {p}')

        with open(p, 'r') as f:
            data = json.load(f)

        @common.debug
        @common.error
        def _run(name):
            module = importlib.import_module(f'.scripts.{name}', package=__package__)

            if not hasattr(module, 'run'):
                raise RuntimeError(f'Failed to run module: {name} - Missing run() function in {module}!')

            module.run()

        for v in data.values():
            if v['name'] == 'separator':
                self.separator(menu=self.menu[k])
                continue

            # Check if the script needs active item
            if 'needs_active' in v and v['needs_active']:
                if not common.active(v['needs_active'], args=True):
                    continue
            # Check if the script needs an application to be set
            if 'needs_application' in v and v['needs_application']:
                afxs = ('aftereffects', 'afx', 'afterfx')
                if not any(([common.get_binary(f)] for f in afxs)):
                    print(f'Could not find After Effects. Tried: {afxs}')
                    continue
            if 'icon' in v and v['icon']:
                icon = ui.get_icon(v['icon'])
            else:
                icon = ui.get_icon('icon')

            self.menu[k][key()] = {
                'text': v['name'],
                'action': functools.partial(_run, v['module']),
                'icon': icon,
            }

    def edit_links_menu(self):
        """Edit links menu actions.

        """

        self.menu[key()] = {
            'text': 'Edit Asset Links...',
            'action': actions.edit_asset_links,
            'icon': ui.get_icon('link', color=common.Color.Blue()),
        }
