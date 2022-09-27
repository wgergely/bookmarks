"""Common signals used across Bookmarks.

"""
from PySide2 import QtCore

from .. import common


def init_signals():
    common.signals = CoreSignals()


class CoreSignals(QtCore.QObject):
    """A utility class used to keep application-wide signals.

    """
    logChanged = QtCore.Signal()

    # Top Bar
    updateTopBarButtons = QtCore.Signal()
    checkSlackToken = QtCore.Signal()

    # Status Bar
    showStatusTipMessage = QtCore.Signal(str)
    showStatusBarMessage = QtCore.Signal(str)
    clearStatusBarMessage = QtCore.Signal()

    thumbnailUpdated = QtCore.Signal(str)

    # Signal used to update elements after a value is updated in the bookmark database
    databaseValueUpdated = QtCore.Signal(str, str, str, object)

    generateThumbnailsChanged = QtCore.Signal()

    serversChanged = QtCore.Signal()
    serverAdded = QtCore.Signal(str)
    serverRemoved = QtCore.Signal(str)

    jobAdded = QtCore.Signal(str)

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

    adjustTabButtonSize = QtCore.Signal()

    activeModeChanged = QtCore.Signal(int)

    tabChanged = QtCore.Signal(int)
    taskViewToggled = QtCore.Signal()

    # Templates
    templatesChanged = QtCore.Signal()
    templateExpanded = QtCore.Signal(str)

    # ShotGrid
    sgEntitySelected = QtCore.Signal(dict)
    sgAssetsLinked = QtCore.Signal()
    sgEntityDataReady = QtCore.Signal(str, list)

    sgConnectionAttemptStarted = QtCore.Signal()
    sgConnectionSuccessful = QtCore.Signal()
    sgConnectionFailed = QtCore.Signal(str)
    sgConnectionClosed = QtCore.Signal()

    # General activation signals
    bookmarkActivated = QtCore.Signal(str, str, str)
    assetActivated = QtCore.Signal(str, str, str, str)
    fileActivated = QtCore.Signal(str, str, str, str, str)

    taskFolderChanged = QtCore.Signal(str)

    threadItemsQueued = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        from .. import actions

        self.toggleFilterButton.connect(actions.toggle_filter_editor)
        self.toggleSequenceButton.connect(actions.toggle_sequence)
        self.toggleArchivedButton.connect(actions.toggle_archived_items)
        self.toggleInlineIcons.connect(actions.toggle_inline_icons)

        self.toggleFavouritesButton.connect(actions.toggle_favourite_items)

        self.databaseValueUpdated.connect(actions.asset_identifier_changed)
        self.assetAdded.connect(actions.show_asset)

        self.taskFolderChanged.connect(actions.set_task_folder)

        self.generateThumbnailsChanged.connect(actions.generate_thumbnails_changed)

        self.adjustTabButtonSize.connect(actions.adjust_tab_button_size)
        self.taskFolderChanged.connect(actions.adjust_tab_button_size)
        self.bookmarkActivated.connect(actions.adjust_tab_button_size)
        self.assetActivated.connect(actions.adjust_tab_button_size)

        self.sgConnectionAttemptStarted.connect(actions.show_sg_connecting_message)
        self.sgConnectionSuccessful.connect(actions.hide_sg_connecting_message)
        self.sgConnectionFailed.connect(actions.hide_sg_connecting_message)
        self.sgConnectionClosed.connect(actions.hide_sg_connecting_message)

        self.sgConnectionFailed.connect(actions.hide_sg_connecting_message)
        self.sgConnectionFailed.connect(actions.show_sg_error_message)
