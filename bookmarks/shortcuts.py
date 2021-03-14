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
        'description': u'Add item',
        'shortcut': None,
    },
    RemoveItem: {
        'value': QtGui.QKeySequence.Delete,
        'default': QtGui.QKeySequence.Delete,
        'repeat': False,
        'description': u'Add item',
        'shortcut': None,
    }
}

MainWidgetShortcuts = {
    OpenNewInstance: {
        'value': u'Ctrl+Shift+N',
        'default': u'Ctrl+Shift+N',
        'repeat': False,
        'description': u'Open a new {} instance...'.format(common.PRODUCT),
        'shortcut': None,
    },
    RowIncrease: {
        'value': QtGui.QKeySequence.ZoomIn,
        'default': QtGui.QKeySequence.ZoomIn,
        'repeat': True,
        'description': u'Increase row',
        'shortcut': None,
    },
    RowDecrease: {
        'value': QtGui.QKeySequence.ZoomOut,
        'default': QtGui.QKeySequence.ZoomOut,
        'repeat': True,
        'description': u'Decrease row',
        'shortcut': None,
    },
    RowReset: {
        'value': u'Ctrl+0',
        'default': u'Ctrl+0',
        'repeat': False,
        'description': u'Reset row size to its default height',
        'shortcut': None,
    },
    ToggleSortOrder: {
        'value': u'Ctrl+Down',
        'default': u'Ctrl+Down',
        'repeat': False,
        'description': u'Toggle sort order',
        'shortcut': None,
    },
    ShowBookmarksTab: {
        'value': u'Alt+1',
        'default': u'Alt+1',
        'repeat': False,
        'description': u'Show bookmarks',
        'shortcut': None,
    },
    ShowAssetsTab: {
        'value': u'Alt+2',
        'default': u'Alt+2',
        'repeat': False,
        'description': u'Show assets',
        'shortcut': None,
    },
    ShowFilesTab: {
        'value': u'Alt+3',
        'default': u'Alt+3',
        'repeat': False,
        'description': u'Show files',
        'shortcut': None,
    },
    ShowFavouritesTab: {
        'value': u'Alt+4',
        'default': u'Alt+4',
        'repeat': False,
        'description': u'Show favourites',
        'shortcut': None,
    },
    NextTab: {
        'value': u'Ctrl+Right',
        'default': u'Ctrl+Right',
        'repeat': True,
        'description': u'Next Tab',
        'shortcut': None,
    },
    PreviousTab: {
        'value': u'Ctrl+Left',
        'default': u'Ctrl+Left',
        'repeat': True,
        'description': u'Previous Tab',
        'shortcut': None,
    },
    AddItem: {
        'value': QtGui.QKeySequence.New,
        'default': QtGui.QKeySequence.New,
        'repeat': False,
        'description': u'Add item',
        'shortcut': None,
    },
    Refresh: {
        'value': QtGui.QKeySequence.Refresh,
        'default': QtGui.QKeySequence.Refresh,
        'repeat': False,
        'description': u'Refresh',
        'shortcut': None,
    },
    AltRefresh: {
        'value': u'Ctrl+R',
        'default': u'Ctrl+R',
        'repeat': False,
        'description': u'Refresh',
        'shortcut': None,
    },
    CopyItemPath: {
        'value': u'Ctrl+C',
        'default': u'Ctrl+C',
        'repeat': False,
        'description': u'Copy file path',
        'shortcut': None,
    },
    CopyAltItemPath: {
        'value': u'Ctrl+Shift+C',
        'default': u'Ctrl+Shift+C',
        'repeat': False,
        'description': u'Copy folder path',
        'shortcut': None,
    },
    RevealItem: {
        'value': u'Ctrl+O',
        'default': u'Ctrl+O',
        'repeat': False,
        'description': u'Reveal item in the file explorer...',
        'shortcut': None,
    },
    RevealAltItem: {
        'value': u'Ctrl+Shift+O',
        'default': u'Ctrl+Shift+O',
        'repeat': False,
        'description': u'Reveal primary URL...',
        'shortcut': None,
    },
    EditItem: {
        'value': u'Ctrl+E',
        'default': u'Ctrl+E',
        'repeat': False,
        'description': u'Edit Properties...',
        'shortcut': None,
    },
    CopyProperties: {
        'value': u'Ctrl+Alt+C',
        'default': u'Ctrl+Alt+C',
        'repeat': False,
        'description': u'Copy Properties...',
        'shortcut': None,
    },
    PasteProperties: {
        'value': u'Ctrl+Alt+V',
        'default': u'Ctrl+Alt+V',
        'repeat': False,
        'description': u'Paste Properties...',
        'shortcut': None,
    },
    Quit: {
        'value': u'Ctrl+Q',
        'default': u'Ctrl+Q',
        'repeat': False,
        'description': u'Quit the application.',
        'shortcut': None,
    },
    Minimize: {
        'value': u'Ctrl+H',
        'default': u'Ctrl+H',
        'repeat': False,
        'description': u'Minimize Window',
        'shortcut': None,
    },
    Maximize: {
        'value': u'Ctrl+Shift+M',
        'default': u'Ctrl+Shift+M',
        'repeat': False,
        'description': u'Maximize Window',
        'shortcut': None,
    },
    FullScreen: {
        'value': QtGui.QKeySequence.FullScreen,
        'default': QtGui.QKeySequence.FullScreen,
        'repeat': False,
        'description': u'Show Full Screen',
        'shortcut': None,
    },
    ToggleGenerateThumbnails: {
        'value': u'Alt+T',
        'default': u'Alt+T',
        'repeat': False,
        'description': u'Create thumbnails from image files',
        'shortcut': None,
    },
    ToggleSearch: {
        'value': u'Alt+F',
        'default': u'Alt+F',
        'repeat': False,
        'description': u'Set a search a filter',
        'shortcut': None,
    },
    ToggleSequence: {
        'value': u'Alt+G',
        'default': u'Alt+G',
        'repeat': False,
        'description': u'Expand sequences',
        'shortcut': None,
    },
    ToggleArchived: {
        'value': u'Alt+A',
        'default': u'Alt+A',
        'repeat': False,
        'description': u'Show archived items',
        'shortcut': None,
    },
    ToggleFavourite: {
        'value': u'Alt+S',
        'default': u'Alt+S',
        'repeat': False,
        'description': u'Show favourites only',
        'shortcut': None,
    },
    ToggleActive: {
        'value': u'Alt+D',
        'default': u'Alt+D',
        'repeat': False,
        'description': u'Show active item only',
        'shortcut': None,
    },
    HideInlineButtons: {
        'value': u'Alt+H',
        'default': u'Alt+H',
        'repeat': False,
        'description': u'Hide buttons',
        'shortcut': None,
    },
    OpenSlack: {
        'value': u'Alt+M',
        'default': u'Alt+M',
        'repeat': False,
        'description': u'Open Slack',
        'shortcut': None,
    },
    OpenPreferences: {
        'value': u'Ctrl+.',
        'default': u'Ctrl+.',
        'repeat': False,
        'description': u'Show {} Preferences'.format(common.PRODUCT),
        'shortcut': None,
    },
    OpenTodo: {
        'value': u'Alt+N',
        'default': u'Alt+N',
        'repeat': False,
        'description': u'Show {} Preferences'.format(common.PRODUCT),
        'shortcut': None,
    },
    ToggleItemArchived: {
        'value': u'Ctrl+A',
        'default': u'Ctrl+A',
        'repeat': False,
        'description': u'Show {} Preferences'.format(common.PRODUCT),
        'shortcut': None,
    },
    ToggleItemFavourite: {
        'value': u'Ctrl+S',
        'default': u'Ctrl+S',
        'repeat': False,
        'description': u'Show {} Preferences'.format(common.PRODUCT),
        'shortcut': None,
    },
    PushToRV: {
        'value': u'Ctrl+P',
        'default': u'Ctrl+P',
        'repeat': False,
        'description': u'Push footage to RV',
        'shortcut': None,
    },
}





def _verify_shortuts(shortcuts):
    values = []
    for v in shortcuts.itervalues():
        if v['value'] in values:
            raise ValueError('{} is used more than once'.format(v['value']))
        values.append(v['value'])


@common.debug
@common.error
def add_shortcuts(widget, shortcuts, context=QtCore.Qt.WidgetWithChildrenShortcut):
    _verify_shortuts(shortcuts)
    for v in shortcuts.itervalues():
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
