# -*- coding: utf-8 -*-
"""All context-menus derive from the `BaseContextMenu` defined below.

"""
import functools
import uuid
import collections

from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import database
from . import images
from . import settings
from . import shortcuts
from . import actions
from . external import rv
from . external import ffmpeg
from .shotgun import actions as sg_actions
from .shotgun import shotgun


def key():
    return uuid.uuid1().hex


def show_event(widget, event):
    w = []
    for action in widget.actions():
        if not action.text():
            continue
        metrics = widget.fontMetrics()
        width = metrics.horizontalAdvance(action.text())
        width += (common.MARGIN() * 7)
        w.append(int(width))
    if w:
        widget.setFixedWidth(max(w))


class BaseContextMenu(QtWidgets.QMenu):
    """Base class containing the context menu definitions.

    The menu structure is defined in `self.menu`, a `collections.OrderedDict` instance.
    The data is expanded into a UI layout by `self.create_menu`. The menu is principally designed
    to work with index-based views and as a result the default constructor takes
    a QModelIndex, stored in `self.index`.

    Properties:
        index (QModelIndex): The index the context menu is associated with.

    Methods:
        create_menu():  Populates the menu with actions based on the ``self.menu`` given.

    """

    def __init__(self, index, parent=None):
        super(BaseContextMenu, self).__init__(parent=parent)
        self.index = index
        self.menu = collections.OrderedDict()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setTearOffEnabled(False)
        self.setSeparatorsCollapsible(True)

        self.setup()
        self.create_menu(self.menu)

    @common.debug
    @common.error
    def setup(self):
        raise NotImplementedError(
            'Abstract method must be overriden in subclass.')

    @common.debug
    @common.error
    def create_menu(self, menu, parent=None):
        """Expands the given menu set into a UI layout.

        """
        show_icons = settings.instance().value(
            settings.SettingsSection,
            settings.ShowMenuIconsKey
        )
        show_icons = not show_icons if show_icons is not None else True

        if not parent:
            parent = self

        for k, v in menu.items():
            if ':' in k:
                continue

            if isinstance(v, collections.OrderedDict):
                submenu = QtWidgets.QMenu(k, parent=parent)
                submenu.create_menu = self.create_menu
                submenu.showEvent = functools.partial(show_event, submenu)

                if k + ':icon' in menu and show_icons:
                    submenu.setIcon(QtGui.QIcon(menu[k + ':icon']))
                if k + ':text' in menu:
                    submenu.setTitle(menu[k + ':text'])

                if k + ':action' in menu:
                    name = menu[k + ':text'] if k + ':text' in menu else k
                    icon = menu[k + ':icon'] if k + \
                        ':icon' in menu and show_icons else QtGui.QIcon()
                    shortcut = menu[k + ':shortcut'] if k + \
                        ':shortcut' in menu else None

                    action = submenu.addAction(name)
                    action.setIconVisibleInMenu(True)

                    if show_icons:
                        action.setIcon(icon)

                    if shortcut:
                        action.setShortcutVisibleInContextMenu(True)
                        action.setShortcut(shortcut)
                        action.setShortcutContext(
                            QtCore.Qt.WidgetWithChildrenShortcut)

                    if isinstance(v, collections.Iterable):
                        for func in menu[k + ':action']:
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
                        QtCore.Qt.WidgetWithChildrenShortcut)
                if 'visible' in v:
                    action.setVisible(v['visible'])
                else:
                    action.setVisible(True)

    def get_icon(self, name, color=common.SECONDARY_TEXT, size=common.ROW_HEIGHT(), opacity=1.0, resource=images.GuiResource):
        icon = QtGui.QIcon()

        pixmap = images.ImageCache.get_rsc_pixmap(
            name, color, size, opacity=opacity)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Normal)

        _c = common.SELECTED_TEXT if color else None
        pixmap = images.ImageCache.get_rsc_pixmap(
            name, _c, size, opacity=opacity, resource=resource)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Active)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Selected)

        _c = common.SEPARATOR if color else None
        pixmap = images.ImageCache.get_rsc_pixmap(
            'close', _c, size, opacity=0.5, resource=resource)

        icon.addPixmap(pixmap, mode=QtGui.QIcon.Disabled)

        return icon

    def showEvent(self, event):
        """Elides the action text to fit the size of the widget upon showing."""
        show_event(self, event)

    def separator(self, menu=None):
        if menu is None:
            menu = self.menu
        menu['separator' + key()] = None

    def window_menu(self):
        if not common.STANDALONE:
            return

        w = self.parent().window()
        on_top_active = w.windowFlags() & QtCore.Qt.WindowStaysOnTopHint
        frameless_active = w.windowFlags() & QtCore.Qt.FramelessWindowHint

        on_icon = self.get_icon('check', color=common.GREEN)
        logo_icon = self.get_icon('logo', color=None)

        k = 'Window Options'
        self.menu[k] = collections.OrderedDict()
        self.menu[k + ':icon'] = logo_icon

        try:
            self.menu[k][key()] = {
                'text': 'Open a New {} Instance...'.format(common.PRODUCT),
                'icon': logo_icon,
                'action': actions.exec_instance,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.OpenNewInstance).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.OpenNewInstance),
            }

            self.separator(self.menu[k])
        except:
            pass

        self.menu[k][key()] = {
            'text': 'Keep Window Always on Top',
            'icon': on_icon if on_top_active else None,
            'action': actions.toggle_stays_on_top
        }
        self.menu[k][key()] = {
            'text': 'Frameless Window',
            'icon': on_icon if frameless_active else None,
            'action': actions.toggle_frameless
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
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Maximize).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Maximize),
            }
            self.menu[k][key()] = {
                'text': 'Minimise',
                'icon': on_icon if minimised else None,
                'action': actions.toggle_minimized,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Minimize).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Minimize),
            }
            self.menu[k][key()] = {
                'text': 'Full Screen',
                'icon': on_icon if full_screen else None,
                'action': actions.toggle_fullscreen,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.FullScreen).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.FullScreen),
            }
        except:
            pass

    def sort_menu(self):
        item_on_icon = self.get_icon('check', color=common.GREEN)

        m = self.parent().model().sourceModel()
        sortorder = m.sort_order()
        sortrole = m.sort_role()

        k = 'Sort List'
        self.menu[k] = collections.OrderedDict()
        self.menu[k + ':icon'] = self.get_icon('sort')


        self.menu[k][key()] = {
            'text': 'Ascending' if not sortorder else 'Descending',
            'icon': self.get_icon('arrow_down') if not sortorder else self.get_icon('arrow_up'),
            'action': actions.toggle_sort_order,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSortOrder).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSortOrder),
        }

        self.separator(self.menu[k])

        for _k in common.DEFAULT_SORT_VALUES:
            self.menu[k][key()] = {
                'text': common.DEFAULT_SORT_VALUES[_k],
                'icon': item_on_icon if sortrole == _k else None,
                'action': functools.partial(
                    actions.change_sorting,
                    _k,
                    sortorder
                )
            }

    def reveal_item_menu(self):
        if not self.index.isValid():
            return

        path = common.get_sequence_startpath(
            self.index.data(QtCore.Qt.StatusTipRole))

        self.menu[key()] = {
            'text': 'Show Item in File Manager',
            'icon': self.get_icon('folder'),
            'action': functools.partial(actions.reveal, path),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RevealItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.RevealItem),
        }
        return

    def bookmark_url_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return

        k = 'Open URL...'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('bookmark')

        server, job, root = self.index.data(common.ParentPathRole)[0:3]

        db = database.get_db(server, job, root)
        primary_url = db.value(
            db.source(),
            'url1',
            table=database.BookmarkTable
        )
        secondary_url = db.value(
            db.source(),
            'url2',
            table=database.BookmarkTable
        )

        if not any((primary_url, secondary_url)):
            return

        if primary_url:
            self.menu[k][key()] = {
                'text': primary_url,
                'icon': self.get_icon('bookmark'),
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(primary_url)),
            }
        if secondary_url:
            self.menu[k][key()] = {
                'text': secondary_url,
                'icon': self.get_icon('bookmark'),
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(secondary_url))
            }

        self.separator(self.menu[k])

    def asset_url_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return
        if len(self.index.data(common.ParentPathRole)) < 4:
            return

        k = 'Open URL...'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('bookmark')

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        asset = self.index.data(common.ParentPathRole)[3]

        db = database.get_db(server, job, root)
        primary_url = db.value(db.source(asset), 'url1')
        secondary_url = db.value(db.source(asset), 'url2')

        if not any((primary_url, secondary_url)):
            return

        if primary_url:
            self.menu[k][key()] = {
                'text': primary_url,
                'icon': self.get_icon('bookmark'),
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(primary_url)),
            }
        if secondary_url:
            self.menu[k][key()] = {
                'text': secondary_url,
                'icon': self.get_icon('bookmark'),
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(secondary_url))
            }

        self.separator(self.menu[k])

    def copy_menu(self):
        if not self.index.isValid():
            return

        k = 'Copy File Path'
        self.menu[k] = collections.OrderedDict()
        self.menu['{}:icon'.format(k)] = self.get_icon('copy')

        path = self.index.data(QtCore.Qt.StatusTipRole)
        for mode in (common.WindowsPath, common.MacOSPath, common.UnixPath, common.SlackPath):
            m = key()
            n = actions.copy_path(path, mode=mode, copy=False)

            if len(n) > 25:
                metrics = QtGui.QFontMetrics(self.font())
                n = metrics.elidedText(n, QtCore.Qt.ElideMiddle, common.WIDTH() * 0.6)

            self.menu[k][m] = {
                'text': n,
                'icon': self.get_icon('copy', color=common.SEPARATOR),
                'action': functools.partial(actions.copy_path, path, mode=mode),
            }

            # Windows/MacOS
            if common.get_platform() == mode:
                self.menu[k][m]['shortcut'] = shortcuts.get(
                    shortcuts.MainWidgetShortcuts, shortcuts.CopyItemPath).key()
                self.menu[k][m]['description'] = shortcuts.hint(
                    shortcuts.MainWidgetShortcuts, shortcuts.CopyItemPath)
            elif mode == common.UnixPath:
                self.menu[k][m]['shortcut'] = shortcuts.get(
                    shortcuts.MainWidgetShortcuts, shortcuts.CopyAltItemPath).key()
                self.menu[k][m]['description'] = shortcuts.hint(
                    shortcuts.MainWidgetShortcuts, shortcuts.CopyAltItemPath)

        self.separator(self.menu[k])

        p = '/'.join(self.index.data(common.ParentPathRole)[0:4])
        path = '$JOB/{}'.format(path.replace(p, '').strip('/'))
        if len(path) > 25:
            metrics = QtGui.QFontMetrics(self.font())
            n = metrics.elidedText(path, QtCore.Qt.ElideMiddle, common.WIDTH() * 0.6)

        self.menu[k][m] = {
            'text': actions.copy_path(path, mode=None, copy=False),
            'icon': self.get_icon('hip', color=None, resource=images.FormatResource),
            'action': functools.partial(actions.copy_path, path, mode=None),
        }




    def toggle_item_flags_menu(self):
        if not self.index.isValid():
            return

        on_icon = self.get_icon('check', color=common.GREEN)
        favourite_icon = self.get_icon('favourite')
        archived_icon = self.get_icon('archivedVisible')

        favourite = self.index.flags() & common.MarkedAsFavourite
        archived = self.index.flags() & common.MarkedAsArchived

        if self.__class__.__name__ == 'BookmarksWidgetContextMenu':
            text = 'Remove Bookmark'
        else:
            text = 'Archived'

        k = 'Flags'
        self.menu[k] = collections.OrderedDict()

        self.menu[k][key()] = {
            'text': text,
            'icon': archived_icon if not archived else on_icon,
            'checkable': False,
            'action': actions.toggle_archived,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemArchived).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemArchived),
        }
        self.menu[k][key()] = {
            'text': 'My File',
            'icon': favourite_icon if not favourite else on_icon,
            'checkable': False,
            'action': actions.toggle_favourite,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemFavourite).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemFavourite),
        }
        return

    def list_filter_menu(self):
        item_on = self.get_icon('check', color=common.GREEN)
        item_off = None

        k = 'List Filters'
        self.menu[k] = collections.OrderedDict()
        self.menu['{}:icon'.format(k)] = self.get_icon('filter')

        self.menu[k]['EditSearchFilter'] = {
            'text': 'Edit Search Filter...',
            'icon': self.get_icon('filter'),
            'action': actions.toggle_filter_editor,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSearch).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSearch),
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
                'action': functools.partial(actions.toggle_flag, common.MarkedAsActive, not active),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleActive).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleActive),
            }
        if favourite or all_off:
            self.menu[k][key()] = {
                'text': 'Show Favourites',
                'icon': item_on if favourite else item_off,
                'disabled': active,
                'action': functools.partial(actions.toggle_flag, common.MarkedAsFavourite, not favourite),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleFavourite).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleFavourite),
            }
        if archived or all_off:
            self.menu[k][key()] = {
                'text': 'Show Archived',
                'icon': item_on if archived else item_off,
                'disabled': active if active else favourite,
                'action': functools.partial(actions.toggle_flag, common.MarkedAsArchived, not archived),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleArchived).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleArchived),
            }

    def row_size_menu(self):
        k = 'Change Row Height'
        self.menu[k] = collections.OrderedDict()
        self.menu[k + ':icon'] = self.get_icon('expand')

        self.menu[k][key()] = {
            'text': 'Increase',
            'icon': self.get_icon('arrow_up'),
            'action': actions.increase_row_size,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RowIncrease).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.RowIncrease),
        }
        self.menu[k][key()] = {
            'text': 'Decrease',
            'icon': self.get_icon('arrow_down'),
            'action': actions.decrease_row_size,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RowDecrease).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.RowDecrease),
        }
        self.menu[k][key()] = {
            'text': 'Reset',
            'icon': self.get_icon('minimize'),
            'action': actions.reset_row_size,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RowReset).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.RowReset),
        }

    def refresh_menu(self):
        self.menu[key()] = {
            'text': 'Refresh List',
            'action': actions.refresh,
            'icon': self.get_icon('refresh'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Refresh).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Refresh),
        }

    def preferences_menu(self):
        self.menu[key()] = {
            'text': 'Preferences...',
            'action': actions.show_preferences,
            'icon': self.get_icon('settings'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.OpenPreferences).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.OpenPreferences),
        }

    def quit_menu(self):
        if not common.STANDALONE:
            return
        self.menu[key()] = {
            'text': 'Quit {}'.format(common.PRODUCT),
            'action': actions.quit,
            'icon': self.get_icon('close'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Quit).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Quit)
        }

    def set_generate_thumbnails_menu(self):
        item_on_icon = self.get_icon('spinner', color=common.GREEN)
        item_off_icon = self.get_icon('spinner', color=common.SEPARATOR)

        model = self.parent().model().sourceModel()
        enabled = model.generate_thumbnails_enabled()

        self.menu[key()] = {
            'text': 'Make Thumbnails',
            'icon': item_on_icon if enabled else item_off_icon,
            'action': common.signals.toggleMakeThumbnailsButton,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleGenerateThumbnails).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleGenerateThumbnails),
        }

    def title(self):
        if not self.index.isValid():
            return
        title = self.index.data(QtCore.Qt.StatusTipRole).split('/')[-1]
        self.menu[key()] = {
            'text': title,
            'disabled': True,
        }

    def thumbnail_menu(self):
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
            self.index.data(QtCore.Qt.StatusTipRole),
        )
        thumbnail_path = images.get_thumbnail(
            server,
            job,
            root,
            self.index.data(QtCore.Qt.StatusTipRole),
            fallback_thumb=self.parent().itemDelegate().fallback_thumb,
            get_path=True
        )

        self.menu[key()] = {
            'text': 'Preview',
            'icon': self.get_icon('image'),
            'action': actions.preview
        }

        self.separator()

        self.menu[key()] = {
            'text': 'Capture Screen...',
            'icon': self.get_icon('capture_thumbnail'),
            'action': actions.capture_thumbnail
        }

        self.menu[key()] = {
            'text': 'Pick Thumbnail File...',
            'icon': self.get_icon('image'),
            'action': actions.pick_thumbnail_from_file
        }

        self.menu[key()] = {
            'text': 'Pick Thumbnail From Library...',
            'icon': self.get_icon('image'),
            'action': actions.pick_thumbnail_from_library
        }

        self.separator()

        if QtCore.QFileInfo(item_thumbnail_path).exists():
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
                'icon': self.get_icon('close', color=common.RED)
            }
        elif QtCore.QFileInfo(thumbnail_path).exists():
            self.menu[key()] = {
                'text': 'Reveal File...',
                'action': functools.partial(
                    actions.reveal,
                    thumbnail_path,
                )
            }

    def bookmark_editor_menu(self):
        icon = self.get_icon('add', color=common.GREEN)
        self.menu[key()] = {
            'text': 'Add Bookmark...',
            'icon': icon,
            'action': actions.show_add_bookmark,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.AddItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }

    def add_asset_to_bookmark_menu(self):
        if not self.index.isValid():
            return
        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        self.menu[key()] = {
            'text': 'Add Asset...',
            'icon': self.get_icon('add'),
            'action': functools.partial(actions.show_add_asset, server=server, job=job, root=root),
        }

    def collapse_sequence_menu(self):
        expand_pixmap = self.get_icon('expand')
        collapse_pixmap = self.get_icon('collapse', common.GREEN)

        currenttype = self.parent().model().sourceModel().data_type()
        groupped = currenttype == common.SequenceItem

        self.menu[key()] = {
            'text': 'Show Sequences' if groupped else 'Show Files',
            'icon': expand_pixmap if groupped else collapse_pixmap,
            'checkable': False,
            'action': common.signals.toggleSequenceButton,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSequence).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSequence),
        }

    def task_toggles_menu(self):
        taskfolder_pixmap = self.get_icon('folder')
        item_on_pixmap = self.get_icon('check')
        item_off_pixmap = QtGui.QIcon()

        k = 'Select Task Folder'
        self.menu[k] = collections.OrderedDict()
        self.menu['{}:icon'.format(k)] = taskfolder_pixmap

        model = self.parent().model().sourceModel()

        settings.instance().verify_active()
        if not settings.active(settings.AssetKey):
            return
        parent_item = (
            settings.active(settings.ServerKey),
            settings.active(settings.JobKey),
            settings.active(settings.RootKey),
            settings.active(settings.AssetKey),
        )

        if not parent_item:
            return
        if not all(parent_item):
            return

        dir_ = QtCore.QDir('/'.join(parent_item))
        dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        for entry in sorted(dir_.entryList()):
            task = model.task()
            if task:
                checked = task == entry
            else:
                checked = False
            self.menu[k][entry] = {
                'text': entry.title(),
                'icon': item_on_pixmap if checked else item_off_pixmap,
                'action': functools.partial(model.taskFolderChanged.emit, entry)
            }

    def remove_favourite_menu(self):
        self.menu[key()] = {
            'text': 'Remove from My Files',
            'icon': self.get_icon('close', color=common.RED),
            'checkable': False,
            'action': actions.toggle_favourite
        }

    def control_favourites_menu(self):
        remove_icon = self.get_icon('close')

        self.menu[key()] = {
            'text': 'Export My Files...',
            'checkable': False,
            'action': actions.export_favourites
        }
        self.menu[key()] = {
            'text': 'Import My Files...',
            'checkable': False,
            'action': actions.import_favourites,
        }

        self.separator()

        self.menu[key()] = {
            'text': 'Clear My Files',
            'icon': remove_icon,
            'checkable': False,
            'action': actions.clear_favourites
        }

    def add_file_menu(self):
        self.menu[key()] = {
            'text': 'Add Template File...',
            'icon': self.get_icon('add', color=common.GREEN),
            'action': actions.show_add_file,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.AddItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }

    def add_file_to_asset_menu(self):
        if not self.index.isValid():
            return

        asset = self.index.data(common.ParentPathRole)[3]
        self.menu[key()] = {
            'text': 'Add Template File...',
            'icon': self.get_icon('add', color=common.GREEN),
            'action': functools.partial(actions.show_add_file, asset=asset)
        }

    def notes_menu(self):
        if not self.index.isValid():
            return

        self.menu[key()] = {
            'text': 'Show Notes...',
            'icon': self.get_icon('todo'),
            'action': actions.show_todos,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.OpenTodo).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.OpenTodo),
        }

    def edit_selected_bookmark_menu(self):
        if not self.index.isValid():
            return

        settings_icon = self.get_icon('settings')
        server, job, root = self.index.data(common.ParentPathRole)[0:3]

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit Bookmark Properties...',
            'icon': settings_icon,
            'action': functools.partial(actions.edit_bookmark, server=server, job=job, root=root),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.EditItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.EditItem),
        }

    def bookmark_clipboard_menu(self):
        if not self.index.isValid():
            return

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = self.get_icon('settings')

        self.separator(menu=self.menu[k])

        self.menu[k][key()] = {
            'text': 'Copy Bookmark Properties',
            'action': actions.copy_bookmark_properties,
            'icon': self.get_icon('copy'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties),
        }

        if not database.CLIPBOARD[database.BookmarkTable]:
            return

        self.menu[k][key()] = {
            'text': 'Paste Bookmark Properties',
            'action': actions.paste_bookmark_properties,
            'icon': self.get_icon('copy'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties),
        }

    def asset_clipboard_menu(self):
        if not self.index.isValid():
            return

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = self.get_icon('settings')

        self.separator(menu=self.menu[k])

        self.menu[k][key()] = {
            'text': 'Copy Asset Properties',
            'action': actions.copy_asset_properties,
            'icon': self.get_icon('copy'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties),
        }

        if not database.CLIPBOARD[database.AssetTable]:
            return

        self.menu[k][key()] = {
            'text': 'Paste Asset Properties',
            'action': actions.paste_asset_properties,
            'icon': self.get_icon('copy'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties),
        }

    def edit_active_bookmark_menu(self):
        settings_icon = self.get_icon('settings')

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit Bookmark Properties...',
            'icon': settings_icon,
            'action': actions.edit_bookmark,
        }

    def edit_selected_asset_menu(self):
        if not self.index.isValid():
            return

        settings_icon = self.get_icon('settings')
        asset = self.index.data(common.ParentPathRole)[3]

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit Asset Properties...',
            'icon': settings_icon,
            'action': functools.partial(actions.edit_asset, asset=asset),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.EditItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.EditItem),
        }

    def edit_active_asset_menu(self):
        settings_icon = self.get_icon('settings')

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit Asset Properties...',
            'icon': settings_icon,
            'action': actions.edit_asset,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.EditItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.EditItem),
        }

    def edit_selected_file_menu(self):
        if not self.index.isValid():
            return

        settings_icon = self.get_icon('settings')
        _file = self.index.data(QtCore.Qt.StatusTipRole)

        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': 'Edit File Properties...',
            'icon': settings_icon,
            'action': functools.partial(actions.edit_file, _file),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.EditItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.EditItem),
        }

    def show_addasset_menu(self):
        add_pixmap = self.get_icon('add', color=common.GREEN)
        self.menu[key()] = {
            'icon': add_pixmap,
            'text': 'Add Asset...',
            'action': actions.show_add_asset,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.AddItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }

    def launcher_menu(self):
        if not self.index.isValid():
            server = settings.active(settings.ServerKey)
            job = settings.active(settings.JobKey)
            root = settings.active(settings.RootKey)
        else:
            server, job, root = self.index.data(common.ParentPathRole)[0:3]

        if not all((server, job, root)):
            return

        db = database.get_db(server, job, root)
        with db.connection():
            v = db.value(
                db.source(),
                'applications',
                table=database.BookmarkTable
            )

        if not isinstance(v, dict) or not v:
            return

        k = 'Launcher'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = self.get_icon('icon_bw')

        for _k in sorted(v, key=lambda k: v[k]['name']):
            try:
                pixmap = QtGui.QPixmap(v[_k]['thumbnail'])
                pixmap.setDevicePixelRatio(images.pixel_ratio)
                icon = QtGui.QIcon(pixmap)
            except:
                icon = QtGui.QIcon()

            self.menu[k][key()] = {
                'icon': icon,
                'text': v[_k]['name'],
                'action': functools.partial(actions.execute, v[_k]['path']),
            }


    def sg_thumbnail_menu(self):
        if not self.index.isValid():
            return

        p = self.index.data(common.ParentPathRole)
        source = self.index.data(QtCore.Qt.StatusTipRole)
        server, job, root = p[0:3]
        asset = p[3] if len(p) > 3 else None

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

        k = 'Shotgun'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = self.get_icon('shotgun')

        sg_properties = shotgun.ShotgunProperties(server, job, root, asset)
        sg_properties.init()
        is_valid = sg_properties.verify()

        self.menu[k][key()] = {
            'text': 'Upload Thumbnail to Shotgun...',
            'action': functools.partial(sg_actions.upload_thumbnail, sg_properties, thumbnail_path),
            'icon': self.get_icon('shotgun', color=common.GREEN),
            'disabled': not is_valid,
        }

    def sg_url_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return

        k = 'Shotgun'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('bookmark')

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        if len(self.index.data(common.ParentPathRole)) >= 4:
            asset = self.index.data(common.ParentPathRole)[3]
        else:
            asset = None

        sg_properties = shotgun.ShotgunProperties(server, job, root, asset)
        sg_properties.init()

        self.separator(self.menu[k])
        for url in reversed(sg_properties.urls()):
            self.menu[k][key()] = {
                'text': url,
                'icon': self.get_icon('shotgun'),
                'action': functools.partial(QtGui.QDesktopServices.openUrl, QtCore.QUrl(url))
            }

    def sg_link_bookmark_menu(self):
        if not self.index.isValid():
            return

        k = 'Shotgun'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('shotgun')

        server, job, root = self.index.data(common.ParentPathRole)[0:3]

        sg_properties = shotgun.ShotgunProperties(server, job, root)
        sg_properties.init()
        is_valid = sg_properties.verify(connection=True)

        self.menu[k][key()] = {
            'text': 'Link Bookmark with Shotgun...',
            'icon': self.get_icon('shotgun'),
            'action': functools.partial(sg_actions.link_bookmark_entity, server, job, root),
            'disabled': not is_valid,
        }

    def sg_link_asset_menu(self):
        if not self.index.isValid():
            return
        if len(self.index.data(common.ParentPathRole)) < 4:
            return

        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        is_valid = sg_properties.verify(bookmark=True)

        k = 'Shotgun'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('shotgun')

        server, job, root, asset = self.index.data(common.ParentPathRole)[0:4]
        for entity_type in ('Asset', 'Shot', 'Sequence'):
            self.menu[k][key()] = {
                'text': 'Link item with Shotgun {}'.format(entity_type.title()),
                'icon': self.get_icon('shotgun'),
                'action': functools.partial(sg_actions.link_asset_entity, server, job, root, asset, entity_type),
                'disabled': not is_valid,
            }

    def sg_link_assets_menu(self):
        k = 'Shotgun'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('shotgun')

        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        is_valid = sg_properties.verify(bookmark=True)

        self.separator(self.menu[k])
        self.menu[k][key()] = {
            'text': 'Link Assets with Shotgun',
            'icon': self.get_icon('shotgun', color=common.GREEN),
            'action': sg_actions.link_assets,
            'disabled': not is_valid,
        }

        self.separator(self.menu[k])

    def sg_rv_menu(self):
        if not self.index.isValid():
            return

        disabled = True if not common.get_path_to_executable(settings.RVKey) else False

        k = 'Shotgun'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('shotgun')

        path = common.get_sequence_startpath(
            self.index.data(QtCore.Qt.StatusTipRole))

        self.menu[k][key()] = {
            'text': 'Push to RV',
            'icon': self.get_icon('shotgun'),
            'action': functools.partial(rv.push, path),
            'disabled': disabled,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.PushToRV).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.PushToRV),
        }

    def sg_publish_menu(self):
        server = settings.active(settings.ServerKey)
        job = settings.active(settings.JobKey)
        root = settings.active(settings.RootKey)
        asset = settings.active(settings.AssetKey)

        sg_properties = shotgun.ShotgunProperties(server, job, root, asset)
        disabled = not bool(sg_properties.verify())

        k = 'Shotgun'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('shotgun')

        self.menu[k][key()] = {
            'text': 'Publish',
            'icon': self.get_icon('shotgun', color=common.GREEN),
            'action': sg_actions.publish,
            'disabled': disabled,
        }

        self.separator(self.menu[k])

        self.menu[k][key()] = {
            'text': 'Browse Tasks',
            'icon': self.get_icon('shotgun'),
            'action': sg_actions.show_task_picker,
            'disabled': disabled
        }

    def convert_menu(self):
        if not self.index.isValid():
            return

        disabled = True if not common.get_path_to_executable(settings.FFMpegKey) else False

        k = 'Convert'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('shotgun')

        path = common.get_sequence_startpath(
            self.index.data(QtCore.Qt.StatusTipRole))
        ext = QtCore.QFileInfo(path).suffix()

        if ext.lower() not in images.get_oiio_extensions():
            return

        pixmap = self.get_icon('file')

        for _k in ffmpeg.PRESETS:
            func = functools.partial(
                ffmpeg.launch_ffmpeg_command, path, ffmpeg.PRESETS[_k]['preset']
            )
            self.menu[k][key()] = {
                'text': ffmpeg.PRESETS[_k]['name'],
                'icon': pixmap,
                'action': func,
                'disabled': disabled,
            }

    def import_json_menu(self):
        k = 'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()

        self.menu[k][key()] = {
            'text': 'Apply data from JSON to Visible Items',
            'action': actions.import_asset_properties_from_json,
        }
