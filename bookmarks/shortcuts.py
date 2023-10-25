"""Application-wide shortcut definitions.

TODO: Create editor widget to make these customizable.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from . import common

OpenNewInstance = common.idx(reset=True, start=0)

RowIncrease = common.idx()
RowDecrease = common.idx()
RowReset = common.idx()

ToggleSortOrder = common.idx()

ShowBookmarksTab = common.idx()
ShowAssetsTab = common.idx()
ShowFilesTab = common.idx()
ShowFavouritesTab = common.idx()

NextTab = common.idx()
PreviousTab = common.idx()

AddItem = common.idx()
EditItem = common.idx()
RemoveItem = common.idx()

Refresh = common.idx()
AltRefresh = common.idx()

ApplicationLauncher = common.idx()

CopyItemPath = common.idx()
CopyAltItemPath = common.idx()
RevealItem = common.idx()
RevealAltItem = common.idx()

Quit = common.idx()
Minimize = common.idx()
Maximize = common.idx()
FullScreen = common.idx()

ToggleSearch = common.idx()
ToggleSequence = common.idx()
ToggleArchived = common.idx()
ToggleFavourite = common.idx()
ToggleActive = common.idx()

HideInlineButtons = common.idx()
OpenPreferences = common.idx()
OpenTodo = common.idx()

ToggleItemArchived = common.idx()
ToggleItemFavourite = common.idx()

PushToRV = common.idx()
PushToRVFullScreen = common.idx()

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
        'description': f'Open a new {common.product.title()} instance...',
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
    ApplicationLauncher: {
        'value': 'Alt+L',
        'default': 'Alt+L',
        'repeat': False,
        'description': 'Application Launcher',
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
    OpenPreferences: {
        'value': 'Ctrl+.',
        'default': 'Ctrl+.',
        'repeat': False,
        'description': f'Show {common.product.title()} Preferences',
        'shortcut': None,
    },
    OpenTodo: {
        'value': 'Alt+N',
        'default': 'Alt+N',
        'repeat': False,
        'description': f'Show {common.product.title()} Preferences',
        'shortcut': None,
    },
    ToggleItemArchived: {
        'value': 'Ctrl+A',
        'default': 'Ctrl+A',
        'repeat': False,
        'description': f'Show {common.product.title()} Preferences',
        'shortcut': None,
    },
    ToggleItemFavourite: {
        'value': 'Ctrl+S',
        'default': 'Ctrl+S',
        'repeat': False,
        'description': f'Show {common.product.title()} Preferences',
        'shortcut': None,
    },
    PushToRV: {
        'value': 'Ctrl+P',
        'default': 'Ctrl+P',
        'repeat': False,
        'description': 'Push footage to RV',
        'shortcut': None,
    },
    PushToRVFullScreen: {
        'value': 'Ctrl+Shift+P',
        'default': 'Ctrl+Shift+P',
        'repeat': False,
        'description': 'Push footage to RV in full-screen',
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
    """Helper function to initialize shortcuts.

    """
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
    """Helper function to connect a function with a shortcut.

    """
    shortcuts[key]['shortcut'].activated.connect(func)


def get(shortcuts, k):
    """Helper function used to retrieve a shortcut.

    """
    return shortcuts[k]['shortcut']


def string(shortcuts, k):
    """Returns the string representation of a shortcut.

    """
    v = shortcuts[k]['shortcut'].key()
    if hasattr(v, 'toString'):
        return v.toString(format=QtGui.QKeySequence.NativeText)
    return v


def hint(shortcuts, k):
    """Get the hint text associated with a shortcut.

    """
    return shortcuts[k]['description']
