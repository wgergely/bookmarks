"""Common signals used across Bookmarks.

"""
import functools
import weakref

from PySide2 import QtCore

from .. import common


def init_signals(connect_signals=True):
    """Initialize signals."""
    common.signals = CoreSignals(connect_signals=connect_signals)


class CoreSignals(QtCore.QObject):
    """A utility class used to store application-wide signals.

    """
    #: Signal emitted by worker threads when the internal data of a model is fully loaded
    internalDataReady = QtCore.Signal(weakref.ref)

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

    #: Signals a value change in the bookmark database -(db table, source path, column, new value)
    databaseValueChanged = QtCore.Signal(str, str, str, object)

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
    jobAdded = QtCore.Signal(str, str) # root, job

    #: Signal emitted when a bookmark item was added
    bookmarksChanged = QtCore.Signal()
    #: Signal emitted when a bookmark item was added
    bookmarkAdded = QtCore.Signal(str, str, str)
    #: Signal emitted when a bookmark item was removed
    bookmarkRemoved = QtCore.Signal(str, str, str)

    #: Signal emitted when saved favourite items have changed
    favouritesChanged = QtCore.Signal()
    #: Signal emitted when a favourite item was added
    favouriteAdded = QtCore.Signal(tuple, str)
    #: Signal emitted when a favourite item was removed
    favouriteRemoved = QtCore.Signal(tuple, str)

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

    #: Signal emitted when the filter text changes of a list view's proxy model
    filterTextChanged = QtCore.Signal(str)

    #: Signal emitted when the active path mode changes
    activeModeChanged = QtCore.Signal(int)

    #: Signal emitted when the item tab changes
    tabChanged = QtCore.Signal(int)
    #: Signal emitted then the task view visibility changes
    switchViewToggled = QtCore.Signal()

    #: Signal called when an item was archived
    itemArchived = QtCore.Signal(tuple, str)
    #: Signal called when an item was unarchived
    itemUnarchived = QtCore.Signal(tuple, str)

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

    #: Signal emitted when the active value has been changed
    activeChanged = QtCore.Signal()
    #: Signal emitted when a bookmark item is set active
    bookmarkItemActivated = QtCore.Signal(str, str, str)
    #: Signal emitted when an asset item is set active
    assetItemActivated = QtCore.Signal(str, str, str, str)
    #: Signal emitted when a file item is set active
    fileItemActivated = QtCore.Signal(str, str, str, str, str)

    #: Signal emitted when a task folder is changed by the user
    taskFolderChanged = QtCore.Signal(str)

    #: Signals an item is ready to be processed by a thread
    threadItemsQueued = QtCore.Signal()

    def __init__(self, connect_signals=True, parent=None):
        super().__init__(parent=parent)

        if not connect_signals:
            return

        from .. import actions

        self.toggleFilterButton.connect(actions.toggle_filter_editor)
        self.toggleSequenceButton.connect(actions.toggle_sequence)
        self.toggleArchivedButton.connect(actions.toggle_archived_items)
        self.toggleInlineIcons.connect(actions.toggle_inline_icons)

        self.toggleFavouritesButton.connect(actions.toggle_favourite_items)

        self.assetAdded.connect(actions.show_asset)

        self.taskFolderChanged.connect(actions.set_task_folder)

        self.generateThumbnailsChanged.connect(actions.generate_thumbnails_changed)

        self.taskFolderChanged.connect(actions.adjust_tab_button_size)
        self.bookmarkItemActivated.connect(actions.adjust_tab_button_size)
        self.assetItemActivated.connect(actions.adjust_tab_button_size)

        self.sgConnectionAttemptStarted.connect(
            lambda *x: common.show_message(
                'ShotGrid is connecting, please wait.', disable_animation=True,
                buttons=[], message_type=None
            )
        )
        self.sgConnectionSuccessful.connect(common.close_message)
        self.sgConnectionFailed.connect(common.close_message)
        self.sgConnectionClosed.connect(common.close_message)

        self.sgConnectionFailed.connect(common.close_message)
        self.sgConnectionFailed.connect(
            lambda x: common.show_message('An error occurred.', body=x, message_type='error')
        )

        # Item flag signals
        self.favouriteAdded.connect(
            functools.partial(
                actions.filter_flag_changed,
                common.MarkedAsFavourite,
                state=True
            )
        )
        self.favouriteRemoved.connect(
            functools.partial(
                actions.filter_flag_changed,
                common.MarkedAsFavourite,
                state=False
            )
        )

        self.itemArchived.connect(
            functools.partial(
                actions.filter_flag_changed,
                common.MarkedAsArchived,
                state=True
            )
        )
        self.itemUnarchived.connect(
            functools.partial(
                actions.filter_flag_changed,
                common.MarkedAsArchived,
                state=False
            )
        )
