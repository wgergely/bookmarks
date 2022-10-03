"""Common signals used across Bookmarks.

"""
from PySide2 import QtCore

from .. import common


def init_signals():
    """Initialize signals."""
    common.signals = CoreSignals()


class CoreSignals(QtCore.QObject):
    """A utility class used to store application-wide signals.

    """
    #: Update top bar widget buttons
    updateTopBarButtons = QtCore.Signal()

    #: Show a status tip message
    showStatusTipMessage = QtCore.Signal(str)
    #: Show a status bar message
    showStatusBarMessage = QtCore.Signal(str)
    #: Clear a status bar message
    clearStatusBarMessage = QtCore.Signal()

    #: Signal a thumbnail update
    thumbnailUpdated = QtCore.Signal(str)

    #: Signals a value update in the bookmark database
    databaseValueUpdated = QtCore.Signal(str, str, str, object)

    #: Signal called when thumbnail generating is enabled or disabled
    generateThumbnailsChanged = QtCore.Signal(QtCore.Qt.CheckState)
    #: Signal called when thumbnail color background is enabled or disabled
    paintThumbnailBGChanged = QtCore.Signal(QtCore.Qt.CheckState)

    #: Signal emitted when saved server values have changed
    serversChanged = QtCore.Signal()
    #: Signal emitted when a server was added
    serverAdded = QtCore.Signal(str)
    #: Signal emitted when a server is removed
    serverRemoved = QtCore.Signal(str)

    #: Signal emitted when a job was added
    jobAdded = QtCore.Signal(str)

    #: Signal emitted when a bookmark item was added
    bookmarkAdded = QtCore.Signal(str, str, str)
    #: Signal emitted when a bookmark item was removed
    bookmarkRemoved = QtCore.Signal(str, str, str)

    #: Signal emitted when saved favourite items have changed
    favouritesChanged = QtCore.Signal()

    #: Signal emitted when an asset was added
    assetAdded = QtCore.Signal(str)
    #: Signal emitted when a file was added
    fileAdded = QtCore.Signal(str)

    #: Signals a filter button state change
    toggleFilterButton = QtCore.Signal()
    #: Signals a filter button state change
    toggleSequenceButton = QtCore.Signal()
    #: Signals a filter button state change
    toggleArchivedButton = QtCore.Signal()
    #: Signals a filter button state change
    toggleInlineIcons = QtCore.Signal()
    #: Signals a filter button state change
    toggleFavouritesButton = QtCore.Signal()

    #: Signal emitted when the active path mode changes
    activeModeChanged = QtCore.Signal(int)

    #: Signal emitted when the item tab changes
    tabChanged = QtCore.Signal(int)
    #: Signal emitted then the task view visibility changes
    taskViewToggled = QtCore.Signal()

    #: Signal when saved templates change
    templatesChanged = QtCore.Signal()
    #: Signal emitted after a template is expanded
    templateExpanded = QtCore.Signal(str)

    #: Signal a ShotGrid entity selection
    sgEntitySelected = QtCore.Signal(dict)
    #: Signal a ShotGrid entity linkage change
    sgAssetsLinked = QtCore.Signal()
    #: Signal a ShotGrid entity data load
    sgEntityDataReady = QtCore.Signal(str, list)

    #: Signal a ShotGrid connection attempt
    sgConnectionAttemptStarted = QtCore.Signal()
    #: Signal a ShotGrid connection success
    sgConnectionSuccessful = QtCore.Signal()
    #: Signal a ShotGrid connection failure
    sgConnectionFailed = QtCore.Signal(str)
    #: Signal a ShotGrid connection closure
    sgConnectionClosed = QtCore.Signal()

    #: Signal emitted when a bookmark item is activated by the user
    bookmarkActivated = QtCore.Signal(str, str, str)
    #: Signal emitted when an asset item is activated by the user
    assetActivated = QtCore.Signal(str, str, str, str)
    #: Signal emitted when a file item is activated by the user
    fileActivated = QtCore.Signal(str, str, str, str, str)

    #: Signal emitted when a task folder is changed by the user
    taskFolderChanged = QtCore.Signal(str)

    #: Signals an item is ready to be processed by a thread
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

        self.taskFolderChanged.connect(actions.adjust_tab_button_size)
        self.bookmarkActivated.connect(actions.adjust_tab_button_size)
        self.assetActivated.connect(actions.adjust_tab_button_size)

        self.sgConnectionAttemptStarted.connect(actions.show_sg_connecting_message)
        self.sgConnectionSuccessful.connect(actions.hide_sg_connecting_message)
        self.sgConnectionFailed.connect(actions.hide_sg_connecting_message)
        self.sgConnectionClosed.connect(actions.hide_sg_connecting_message)

        self.sgConnectionFailed.connect(actions.hide_sg_connecting_message)
        self.sgConnectionFailed.connect(actions.show_sg_error_message)
