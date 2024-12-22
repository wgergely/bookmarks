"""File items are files found inside an asset item. They're made up of ``server``,
``job``, ``root``, ``asset``, ``task`` and ``file`` path segments.

.. code-block:: python
    :linenos:

    # The following file path...
    my_file = '//my/server/my_job/my_asset/my_task_folder/take1/my_file.psd
    # ...is constructed like this:
    my_file = f'{server}/{job}/{root}/{asset}/{task}/take1/my_file.psd'
    # Note the relative path segment ``take1/my_file.psd``


Note the two new path segments file items introduce: ``task`` items, and a relative
`file` segment, ``take1/my_file.psd``.

:class:`FileItemModel` will always load recursively **all** files found in a specified
task folder. In the real world, these correspond to workspace folders used by DCCs,
such as the `scenes`, `cache`, `images`, `render`, etc. folders. These folders are the
main containers for file items.

The relative file path segment is what :class:`FileItemView` displays.
This segment often includes a series of subdirectories the view represents as
interactive labels. These labels can be used to filter the list view.

.. note:
    In summary , :class:`FileItemModel` will **not** load file items from the root
    of an asset item, but from subdirectories called ``task`` items. It will load
    all files from all subdirectories from this folder but provides filter options in the
    form of interactive labels.

Important to note that :class:`FileItemModel` interacts with two data sets
simultaneously: a *collapsed* sequence and a regular file data set.
See the :mod:`~bookmarks.common.sequence` module for details on sequence definitions, and
:meth:`~bookmarks.items.models.BaseItemModel.model_data`.

"""
import functools

from PySide2 import QtCore
from ... import common, contextmenu, actions
from . import threadedview
from ..delegate import file as filedelegate
from ..model import file as filemodel
from ...threads import threads

active_keys = {
    'server',
    'job',
    'root',
    'asset',
    'task',
}


class FileItemViewContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with :class:`FileItemView`.

    """

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.scripts_menu()
        self.separator()
        self.task_folder_toggle_menu()
        self.separator()
        self.launcher_menu()
        self.separator()
        if self.index and self.index.isValid() and self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.sg_publish_menu()
            self.publish_menu()
            self.separator()
        self.sg_url_menu()
        self.sg_browse_tasks_menu()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.sg_rv_menu()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.convert_menu()
        self.separator()
        self.add_file_menu()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.delete_selected_files_menu()
        self.separator()
        self.bookmark_url_menu()
        self.asset_url_menu()
        self.reveal_item_menu()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.copy_menu()
        self.separator()
        self.edit_active_bookmark_menu()
        self.edit_active_asset_menu()
        self.notes_menu()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.toggle_item_flags_menu()
        self.separator()
        self.row_size_menu()
        self.sort_menu()
        self.list_filter_menu()
        self.refresh_menu()
        self.separator()
        self.preferences_menu()
        self.separator()
        self.window_menu()
        self.quit_menu()


class FileItemView(threadedview.ThreadedItemView):
    """The view used to display :class:`FileItemModel` items.

    """
    Delegate = filedelegate.FileItemViewDelegate
    ContextMenu = FileItemViewContextMenu

    queues = (threads.FileInfo, threads.FileThumbnail)

    def __init__(self, icon='file', parent=None):
        super().__init__(
            icon=icon,
            parent=parent
        )
        common.signals.fileAdded.connect(
            functools.partial(self.show_item, role=common.PathRole)
        )

    def get_source_model(self):
        return filemodel.FileItemModel(parent=self)

    def inline_icons_count(self):
        """Inline buttons count.

        """
        if self.buttons_hidden():
            return 0
        return 4

    def key_enter(self):
        """Custom key action.

        """
        index = common.get_selected_index(self)
        if not index.isValid():
            self.activate(index)

    def get_hint_string(self):
        """Returns an informative hint text.

        """
        model = self.model().sourceModel()
        k = model.task()
        if not k:
            return 'No asset folder selected'
        return f'No files found in "{k}"'

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def show_item(self, v, role=QtCore.Qt.DisplayRole, update=True, limit=10000):
        """This slot is called by the `itemAdded` signal.

        For instance, when new file is added we'll use this method to reveal it
        in the files tab.

        """
        proxy = self.model()
        model = proxy.sourceModel()
        k = model.task()

        if not all(model.parent_path()):
            return
        source_path = '/'.join(model.parent_path())

        # We probably saved outside the asset, we won't be showing the
        # file...
        if source_path not in v:
            return

        # Show files tab
        if common.current_tab() != common.FileTab:
            actions.change_tab(common.FileTab)

        # Change task folder
        task = v.replace(source_path, '').strip('/').split('/', maxsplit=1)[0]
        if k != task:
            common.signals.taskFolderChanged.emit(task)

        data = model.model_data()
        t = model.data_type()
        if t == common.SequenceItem:
            v = common.proxy_path(v)

        # Refresh the model if
        if len(data) < limit:
            model.reset_data(force=True)

        # Delay the selection to let the model process events
        QtCore.QTimer.singleShot(
            300, functools.partial(
                self.select_item, v, role=role
            )
        )
