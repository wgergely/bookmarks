# -*- coding: utf-8 -*-
"""The threads and associated worker classes.

Thumbnail and file-load work on carried out on secondary threads.
Each thread is assigned a single Worker - usually responsible for taking
a *weakref.ref* from the thread's queue.

"""
from PySide2 import QtWidgets, QtGui, QtCore
from . import common


OpenNewInstance = 0

RowIncrease = OpenNewInstance + 1
RowDecrease = RowIncrease + 1
RowReset = RowDecrease + 1

ToggleSortOrder = RowReset + 1

ShowBookmarksTab = ToggleSortOrder + 1
ShowAssetsTab = ShowBookmarksTab + 1
ShowFilesTab = ShowAssetsTab + 1
ShowFavouritesTab = ShowFilesTab + 1

NextTab = ShowFavouritesTab + 1
PreviousTab = NextTab + 1

AddItem = PreviousTab + 1
EditItem = AddItem + 1
RemoveItem = EditItem + 1

Refresh = RemoveItem + 1
AltRefresh = Refresh + 1

CopyItemPath = AltRefresh + 1
CopyAltItemPath = CopyItemPath + 1
RevealItem = CopyAltItemPath + 1
RevealAltItem = RevealItem + 1

CopyProperties = RevealAltItem + 1
PasteProperties = CopyProperties + 1

Quit = PasteProperties + 1
Minimize = Quit + 1
Maximize = Minimize + 1
FullScreen = Maximize + 1

ToggleGenerateThumbnails = FullScreen + 1
ToggleSearch = ToggleGenerateThumbnails + 1
ToggleSequence = ToggleSearch + 1
ToggleArchived = ToggleSequence + 1
ToggleFavourite = ToggleArchived + 1
ToggleActive = ToggleFavourite + 1

HideInlineButtons = ToggleActive + 1
OpenSlack = HideInlineButtons + 1
OpenPreferences = OpenSlack + 1
OpenTodo = OpenPreferences + 1

ToggleItemArchived = OpenTodo + 1
ToggleItemFavourite = ToggleItemArchived + 1

PushToRV = ToggleItemFavourite + 1

BookmarkEditorShortcuts = {
    AddItem: {
        'value': QtGui.QKeySequence.New,
        'default': QtGui.QKeySequence.New,
        'repeat': False,
        'description': 'Add item',
        'shortcut': None,
    },
    RemoveItem: {
        'value': QtGui.QKeySequence.Delete,
        'default': QtGui.QKeySequence.Delete,
        'repeat': False,
        'description': 'Add item',
        'shortcut': None,
    }
}

MainWidgetShortcuts = {
    OpenNewInstance: {
        'value': 'Ctrl+Shift+N',
        'default': 'Ctrl+Shift+N',
        'repeat': False,
        'description': 'Open a new {} instance...'.format(common.PRODUCT),
        'shortcut': None,
    },
    RowIncrease: {
        'value': QtGui.QKeySequence.ZoomIn,
        'default': QtGui.QKeySequence.ZoomIn,
        'repeat': True,
        'description': 'Increase row',
        'shortcut': None,
    },
    RowDecrease: {
        'value': QtGui.QKeySequence.ZoomOut,
        'default': QtGui.QKeySequence.ZoomOut,
        'repeat': True,
        'description': 'Decrease row',
        'shortcut': None,
    },
    RowReset: {
        'value': 'Ctrl+0',
        'default': 'Ctrl+0',
        'repeat': False,
        'description': 'Reset row size to its default height',
        'shortcut': None,
    },
    ToggleSortOrder: {
        'value': 'Ctrl+Down',
        'default': 'Ctrl+Down',
        'repeat': False,
        'description': 'Toggle sort order',
        'shortcut': None,
    },
    ShowBookmarksTab: {
        'value': 'Alt+1',
        'default': 'Alt+1',
        'repeat': False,
        'description': 'Show bookmarks',
        'shortcut': None,
    },
    ShowAssetsTab: {
        'value': 'Alt+2',
        'default': 'Alt+2',
        'repeat': False,
        'description': 'Show assets',
        'shortcut': None,
    },
    ShowFilesTab: {
        'value': 'Alt+3',
        'default': 'Alt+3',
        'repeat': False,
        'description': 'Show files',
        'shortcut': None,
    },
    ShowFavouritesTab: {
        'value': 'Alt+4',
        'default': 'Alt+4',
        'repeat': False,
        'description': 'Show favourites',
        'shortcut': None,
    },
    NextTab: {
        'value': 'Ctrl+Right',
        'default': 'Ctrl+Right',
        'repeat': True,
        'description': 'Next Tab',
        'shortcut': None,
    },
    PreviousTab: {
        'value': 'Ctrl+Left',
        'default': 'Ctrl+Left',
        'repeat': True,
        'description': 'Previous Tab',
        'shortcut': None,
    },
    AddItem: {
        'value': QtGui.QKeySequence.New,
        'default': QtGui.QKeySequence.New,
        'repeat': False,
        'description': 'Add item',
        'shortcut': None,
    },
    Refresh: {
        'value': QtGui.QKeySequence.Refresh,
        'default': QtGui.QKeySequence.Refresh,
        'repeat': False,
        'description': 'Refresh',
        'shortcut': None,
    },
    AltRefresh: {
        'value': 'Ctrl+R',
        'default': 'Ctrl+R',
        'repeat': False,
        'description': 'Refresh',
        'shortcut': None,
    },
    CopyItemPath: {
        'value': 'Ctrl+C',
        'default': 'Ctrl+C',
        'repeat': False,
        'description': 'Copy file path',
        'shortcut': None,
    },
    CopyAltItemPath: {
        'value': 'Ctrl+Shift+C',
        'default': 'Ctrl+Shift+C',
        'repeat': False,
        'description': 'Copy folder path',
        'shortcut': None,
    },
    RevealItem: {
        'value': 'Ctrl+O',
        'default': 'Ctrl+O',
        'repeat': False,
        'description': 'Reveal item in the file explorer...',
        'shortcut': None,
    },
    RevealAltItem: {
        'value': 'Ctrl+Shift+O',
        'default': 'Ctrl+Shift+O',
        'repeat': False,
        'description': 'Reveal primary URL...',
        'shortcut': None,
    },
    EditItem: {
        'value': 'Ctrl+E',
        'default': 'Ctrl+E',
        'repeat': False,
        'description': 'Edit Properties...',
        'shortcut': None,
    },
    CopyProperties: {
        'value': 'Ctrl+Alt+C',
        'default': 'Ctrl+Alt+C',
        'repeat': False,
        'description': 'Copy Properties...',
        'shortcut': None,
    },
    PasteProperties: {
        'value': 'Ctrl+Alt+V',
        'default': 'Ctrl+Alt+V',
        'repeat': False,
        'description': 'Paste Properties...',
        'shortcut': None,
    },
    Quit: {
        'value': 'Ctrl+Q',
        'default': 'Ctrl+Q',
        'repeat': False,
        'description': 'Quit the application.',
        'shortcut': None,
    },
    Minimize: {
        'value': 'Ctrl+H',
        'default': 'Ctrl+H',
        'repeat': False,
        'description': 'Minimize Window',
        'shortcut': None,
    },
    Maximize: {
        'value': 'Ctrl+Shift+M',
        'default': 'Ctrl+Shift+M',
        'repeat': False,
        'description': 'Maximize Window',
        'shortcut': None,
    },
    FullScreen: {
        'value': QtGui.QKeySequence.FullScreen,
        'default': QtGui.QKeySequence.FullScreen,
        'repeat': False,
        'description': 'Show Full Screen',
        'shortcut': None,
    },
    ToggleGenerateThumbnails: {
        'value': 'Alt+T',
        'default': 'Alt+T',
        'repeat': False,
        'description': 'Create thumbnails from image files',
        'shortcut': None,
    },
    ToggleSearch: {
        'value': 'Alt+F',
        'default': 'Alt+F',
        'repeat': False,
        'description': 'Set a search a filter',
        'shortcut': None,
    },
    ToggleSequence: {
        'value': 'Alt+G',
        'default': 'Alt+G',
        'repeat': False,
        'description': 'Expand sequences',
        'shortcut': None,
    },
    ToggleArchived: {
        'value': 'Alt+A',
        'default': 'Alt+A',
        'repeat': False,
        'description': 'Show archived items',
        'shortcut': None,
    },
    ToggleFavourite: {
        'value': 'Alt+S',
        'default': 'Alt+S',
        'repeat': False,
        'description': 'Show favourites only',
        'shortcut': None,
    },
    ToggleActive: {
        'value': 'Alt+D',
        'default': 'Alt+D',
        'repeat': False,
        'description': 'Show active item only',
        'shortcut': None,
    },
    HideInlineButtons: {
        'value': 'Alt+H',
        'default': 'Alt+H',
        'repeat': False,
        'description': 'Hide buttons',
        'shortcut': None,
    },
    OpenSlack: {
        'value': 'Alt+M',
        'default': 'Alt+M',
        'repeat': False,
        'description': 'Open Slack',
        'shortcut': None,
    },
    OpenPreferences: {
        'value': 'Ctrl+.',
        'default': 'Ctrl+.',
        'repeat': False,
        'description': 'Show {} Preferences'.format(common.PRODUCT),
        'shortcut': None,
    },
    OpenTodo: {
        'value': 'Alt+N',
        'default': 'Alt+N',
        'repeat': False,
        'description': 'Show {} Preferences'.format(common.PRODUCT),
        'shortcut': None,
    },
    ToggleItemArchived: {
        'value': 'Ctrl+A',
        'default': 'Ctrl+A',
        'repeat': False,
        'description': 'Show {} Preferences'.format(common.PRODUCT),
        'shortcut': None,
    },
    ToggleItemFavourite: {
        'value': 'Ctrl+S',
        'default': 'Ctrl+S',
        'repeat': False,
        'description': 'Show {} Preferences'.format(common.PRODUCT),
        'shortcut': None,
    },
    PushToRV: {
        'value': 'Ctrl+P',
        'default': 'Ctrl+P',
        'repeat': False,
        'description': 'Push footage to RV',
        'shortcut': None,
    },
}





def _verify_shortuts(shortcuts):
    values = []
    for v in shortcuts.values():
        if v['value'] in values:
            raise ValueError('{} is used more than once'.format(v['value']))
        values.append(v['value'])


@common.debug
@common.error
def add_shortcuts(widget, shortcuts, context=QtCore.Qt.WidgetWithChildrenShortcut):
    _verify_shortuts(shortcuts)
    for v in shortcuts.values():
        key_sequence = QtGui.QKeySequence(v['value'])
        shortcut = QtWidgets.QShortcut(key_sequence, widget)
        shortcut.setAutoRepeat(v['repeat'])
        shortcut.setWhatsThis(v['description'])
        shortcut.setContext(context)
        v['shortcut'] = shortcut

@common.debug
@common.error
def connect(shortcuts, key, func):
    shortcuts[key]['shortcut'].activated.connect(func)


def get(shortcuts, k):
    return shortcuts[k]['shortcut']

def string(shortcuts, k):
    v = shortcuts[k]['shortcut'].key()
    if hasattr(v, 'toString'):
        return v.toString(format=QtGui.QKeySequence.NativeText)
    return v

def hint(shortcuts, k):
    return shortcuts[k]['description']
