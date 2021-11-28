"""

"""
from PySide2 import QtCore

from .. import common



def init_signals():
    common.signals = CoreSignals()


class CoreSignals(QtCore.QObject):
    logChanged = QtCore.Signal()

    # Top Bar
    updateButtons = QtCore.Signal()
    checkSlackToken = QtCore.Signal()

    # Status Bar
    showStatusTipMessage = QtCore.Signal(str)
    showStatusBarMessage = QtCore.Signal(str)
    clearStatusBarMessage = QtCore.Signal()

    thumbnailUpdated = QtCore.Signal(str)

    # Signal used to update elements after a value is updated in the bookmark database
    databaseValueUpdated = QtCore.Signal(str, str, str, object)

    serversChanged = QtCore.Signal()

    bookmarkAdded = QtCore.Signal(str, str, str)
    bookmarkRemoved = QtCore.Signal(str, str, str)

    favouritesChanged = QtCore.Signal()

    assetAdded = QtCore.Signal(str)
    fileAdded = QtCore.Signal(str)

    toggleFilterButton = QtCore.Signal()
    toggleSequenceButton = QtCore.Signal()
    toggleArchivedButton = QtCore.Signal()
    toggleInlineIcons = QtCore.Signal()
    toggleFavouritesButton = QtCore.Signal()
    toggleMakeThumbnailsButton = QtCore.Signal()

    sessionModeChanged = QtCore.Signal(int)

    tabChanged = QtCore.Signal(int)
    taskViewToggled = QtCore.Signal()

    # Templates
    templatesChanged = QtCore.Signal()
    templateExpanded = QtCore.Signal(str)

    # Shotgun
    entitySelected = QtCore.Signal(dict)
    assetsLinked = QtCore.Signal()
    shotgunEntityDataReady = QtCore.Signal(str, list)

    # General activation signals
    bookmarkActivated = QtCore.Signal(str, str, str)
    assetActivated = QtCore.Signal(str, str, str, str)
    fileActivated = QtCore.Signal(str, str, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        from .. import actions
        self.toggleFilterButton.connect(actions.toggle_filter_editor)
        self.toggleSequenceButton.connect(actions.toggle_sequence)
        self.toggleArchivedButton.connect(actions.toggle_archived_items)
        self.toggleInlineIcons.connect(actions.toggle_inline_icons)
        self.toggleFavouritesButton.connect(actions.toggle_favourite_items)
        self.toggleMakeThumbnailsButton.connect(actions.toggle_make_thumbnails)
        self.databaseValueUpdated.connect(actions.asset_identifier_changed)
