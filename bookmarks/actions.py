"""User actions module.

The user usually triggers these actions via keyboard shortcuts or by
interactions with the UI.

"""
import functools
import json
import os
import re
import subprocess
import zipfile

from PySide2 import QtCore, QtWidgets, QtGui

from . import common, tokens
from . import database
from . import images
from . import log


def must_be_initialized(func):
    """Decorator function sure functions only run when :attr:`common.main_widget`
    exists and initialized.

    """

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        """Function wrapper.

        """
        if common.main_widget is None or not common.main_widget.is_initialized:
            return
        return func(*args, **kwargs)

    return func_wrapper


def toggle_debug(state):
    """Toggles debugging staten on or off.

    When on, the app will print debugging information to the console.

    Args:
        state (QtCore.Qt.CheckState): Debugging state.

    """
    if not isinstance(state, QtCore.Qt.CheckState):
        state = bool(state)
    else:
        if state == QtCore.Qt.Checked:
            state = True
        elif state == QtCore.Qt.Unchecked:
            state = False
    common.debug_on = state


def add_favourite(source_paths, source):
    """Add and save a favourite item.

    Args:
        source_paths (list): A list of parent paths.
        source (str): The item to save as a favourite item.

    """
    if not source_paths or not source:
        return

    common.favourites[source] = source_paths
    common.settings.set_favourites(common.favourites)
    common.signals.favouriteAdded.emit(source_paths, source)


def remove_favourite(source_paths, source):
    """Remove a saved favourite item.

    Args:
        source_paths (list): A list of parent paths.
        source (str): The item to save as a favourite item.

    """
    if not source_paths or not source:
        return

    if source not in common.favourites:
        return

    del common.favourites[source]
    common.settings.set_favourites(common.favourites)
    common.signals.favouriteRemoved.emit(source_paths, source)


@QtCore.Slot()
def filter_flag_changed(flag, parent_paths, source, state=None, limit=9999):
    """Slot used to keep item filter flag values updated across all datasets.

    For instance, the favourite item model might set flag values that we want to
    keep updated in other models too.

    Args:
        flag (int): A filter flag.
        parent_paths (list): The parent paths that make up the source file.
        source (str): The source file path.
        state (bool): The favourite state flat value.
        limit (int): The maximum number of items to check.

    """
    if len(parent_paths) == 3:
        models = (common.source_model(idx=common.BookmarkTab),)
    elif len(parent_paths) == 4:
        models = (common.source_model(idx=common.AssetTab),)
    elif len(parent_paths) > 4:
        models = (common.source_model(idx=common.FileTab), common.source_model(idx=common.FavouriteTab),)
    else:
        return

    for model in models:

        p = model.parent_path()
        k = model.task()

        # Make sure data is up-to-date in all data sets.
        for t in (common.FileItem, common.SequenceItem,):
            data = common.get_data(p, k, t)

            for n, item in enumerate(data.values()):
                # Bail if the data set is large
                if n > limit:
                    break
                if common.proxy_path(item[common.PathRole]) == source or item[common.PathRole] == source:
                    if state and not item[common.FlagsRole] & flag:
                        item[common.FlagsRole] |= flag
                    if not state and (item[common.FlagsRole] & flag):
                        item[common.FlagsRole] &= ~flag


@common.error
@common.debug
def clear_favourites(prompt=True):
    """Clear the list of saved favourite items.

    Args:
        prompt (bool): If True, will prompt the user for confirmation.

    """
    if prompt:
        if common.show_message(
                'Are you sure you want to clear your saved items?', body='This action not undoable.',
                buttons=[common.YesButton, common.NoButton], modal=True
        ) == QtWidgets.QDialog.Rejected:
            return

    common.favourites = {}
    common.settings.set_favourites(common.favourites)


@common.error
@common.debug
def export_favourites(*args, destination=None):
    """Saves all favourite items to a zip file.

    Args:
        args (tuple): A `server`, `job`, `root` argument tuple.
        destination (str): The path to save the zip file to. Optional.

    """
    if destination is None:
        destination, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption='Save Favourites', filter=f'*.{common.favorite_file_ext}',
            dir=QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.HomeLocation
            ), )
        if not destination:
            return

    data = common.favourites.copy()

    # Assemble the zip file
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_STORED) as _zip:

        # Add thumbnail to zip
        for source, source_paths in common.favourites.items():
            server, job, root = source_paths[0:3]

            thumbnail_path = images.get_cached_thumbnail_path(
                server, job, root, source
            )

            file_info = QtCore.QFileInfo(thumbnail_path)
            if file_info.exists():
                _zip.write(thumbnail_path, file_info.fileName())

            # Add description
            k = 'description'
            db = database.get(server, job, root)
            if source == db.source():
                table = database.BookmarkTable
            else:
                table = database.AssetTable

            v = db.value(source, k, table)
            if v:
                _zip.writestr(
                    file_info.baseName() + k, database.b64encode(v)
                )

        # Let's Save the current list favourites to the zip
        v = json.dumps(
            data, ensure_ascii=True, sort_keys=False, indent=4
        )
        _zip.writestr('data.json', v)

    return destination


@common.error
@common.debug
def import_favourites(*args, source=None):
    """Import a previously exported favourites file.

    Args:
        source (str): Path to a file. Defaults to `None`.

    """
    if source is None:
        source, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption='Import Favourites', filter=f'*.{common.favorite_file_ext}'
        )
        if not source:
            return

    with zipfile.ZipFile(source, compression=zipfile.ZIP_STORED) as _zip:
        corrupt = _zip.testzip()
        if corrupt:
            raise RuntimeError(
                f'This zip archive seem corrupted: {corrupt}.'
            )

        if 'data.json' not in _zip.namelist():
            raise RuntimeError('Invalid file.')

        with _zip.open('data.json') as _f:
            v = _f.read()

        data = json.loads(
            v, parse_int=int, parse_float=float, object_hook=common.int_key
        )

        for _source, source_paths in data.items():
            server, job, root = source_paths[0:3]

            thumbnail_path = images.get_cached_thumbnail_path(
                server, job, root, _source, )

            # There's a thumbnail already, we'll skip
            file_info = QtCore.QFileInfo(thumbnail_path)
            if not file_info.exists():
                # Let's write the thumbnails to disk
                if file_info.fileName() in _zip.namelist():
                    root = '/'.join(
                        (server, job, root, common.bookmark_item_data_dir)
                    )
                    _zip.extract(
                        file_info.fileName(), root
                    )
                    images.ImageCache.flush(thumbnail_path)

            # Add description
            k = 'description'
            if not file_info.baseName() + k in _zip.namelist():
                continue

            v = _zip.read(file_info.baseName() + k)
            if not v:
                continue

            db = database.get(server, job, root)
            if source == db.source():
                table = database.BookmarkTable
            else:
                table = database.AssetTable
            db.set_value(source, k, database.b64decode(v), table)

    common.settings.set_favourites(data)
    common.signals.favouritesChanged.emit()


@QtCore.Slot(QtCore.QModelIndex)
def activate_scenes_task_folder(index):
    """Slot responsible for applying the default to scene folder setting.

    The slot is connected to :class:`bookmarks.items.file_items.FileItemModel`'s
    `activeChanged` signal, is used it to modify the active task path before
    resetting the file model.

    Args:
        index (QtCore.QModelIndex): The index of the activated asset items.

    """
    v = common.settings.value('settings/default_to_scenes_folder')
    if not v:
        return

    if not index.isValid():
        return

    # Get the current scene folder name from the token configuration.
    common.set_active('task', tokens.get_folder(tokens.SceneFolder))


@common.error
@common.debug
def set_task_folder(v):
    """Sets the active task folder.

    Args:
        v (str): A `task` path segment, for example, 'scenes'.

    """
    common.set_active('task', v)
    common.source_model(common.FileTab).reset_data()
    common.widget(common.FileTab).model().invalidateFilter()


@common.error
@common.debug
@must_be_initialized
def toggle_sequence():
    """Toggles the data type of the file item model.

    """
    if common.current_tab() not in (common.FileTab, common.FavouriteTab):
        return

    model = common.source_model()
    datatype = model.data_type()
    if datatype == common.FileItem:
        model.dataTypeChanged.emit(common.SequenceItem)
    else:
        model.dataTypeChanged.emit(common.FileItem)


@common.error
@common.debug
@must_be_initialized
def toggle_archived_items():
    """Toggles the ``MarkedAsArchived`` item filter of the current tab model.

    """
    w = common.widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsArchived)
    proxy.set_filter_flag(common.MarkedAsArchived, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsArchived, not val)


@common.error
@common.debug
@must_be_initialized
def toggle_active_item():
    """Toggles the ``MarkedAsActive`` item filter of the current tab model.

    """
    w = common.widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsActive)
    proxy.set_filter_flag(common.MarkedAsActive, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsActive, not val)


@common.error
@common.debug
@must_be_initialized
def toggle_favourite_items():
    """Toggles the ``MarkedAsFavourite`` item filter of the current tab model.

    """
    w = common.widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsFavourite)
    proxy.set_filter_flag(common.MarkedAsFavourite, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsFavourite, not val)


@common.error
@common.debug
@must_be_initialized
def adjust_tab_button_size(*args, **kwargs):
    """Slot used to adjust the size of the top bar buttons size.

    """
    w = common.main_widget.topbar_widget
    w.button(common.BookmarkTab).adjust_size()
    w.button(common.AssetTab).adjust_size()
    w.button(common.FileTab).adjust_size()
    w.button(common.FavouriteTab).adjust_size()


@common.error
@common.debug
@must_be_initialized
def toggle_inline_icons():
    """Toggles the inline icon visibility of the current tab view.

    """
    widget = common.widget()
    state = not widget.buttons_hidden()

    widget.set_buttons_hidden(state)

    widget.model().sourceModel().sort_data()


@common.error
@common.debug
@must_be_initialized
def toggle_progress_columns():
    """Toggles the visibility of the progress tracker columns.

    """
    widget = common.widget(common.AssetTab)
    state = not widget.progress_hidden()
    widget.set_progress_hidden(state)


@common.error
@common.debug
@QtCore.Slot(QtCore.Qt.CheckState)
@must_be_initialized
def generate_thumbnails_changed(state):
    """Slot called when the thumbnail generating preference has changed.

    Args:
        state (QtCore.Qt.CheckState): The preference state.

    """
    from .threads import threads

    for t in (common.FileTab, common.FavouriteTab):
        w = common.widget(t)
        for k in w.queues:
            if state == QtCore.Qt.Checked:
                threads.THREADS[k]['queue'].clear()
            elif state == QtCore.Qt.Unchecked:
                if threads.THREADS[k]['role'] == common.ThumbnailLoaded:
                    w.start_delayed_queue_timer()


@must_be_initialized
def toggle_filter_editor():
    """Toggles the search filter editor view of the current item view.

    """
    w = common.widget()
    if w.filter_editor.isHidden():
        w.filter_editor.show()
    else:
        w.filter_editor.close()


def selection(func):
    """Decorator function to ensure `QModelIndexes` passed to worker threads
    are in a valid state.

    """

    @functools.wraps(func)
    @must_be_initialized
    def func_wrapper():
        """Function wrapper."""
        index = common.selected_index()
        if not index.isValid():
            return None
        return func(index)

    return func_wrapper


@common.error
@common.debug
@must_be_initialized
def increase_row_size():
    """Increases the row size of the current tab view.

    """
    widget = common.widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.row_size.height() + common.Size.Thumbnail((1.0 / 30.0), apply_scale=False)
    if v >= common.Size.Thumbnail(apply_scale=False):
        return

    widget.set_row_size(v)


@common.error
@common.debug
@must_be_initialized
def decrease_row_size():
    """Decreases the row size of the current tab view.

    """
    widget = common.widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.row_size.height() - common.Size.Thumbnail((1.0 / 30.0), apply_scale=False)
    if v <= model.default_row_size().height():
        v = model.default_row_size().height()

    widget.set_row_size(v)


@common.error
@common.debug
@must_be_initialized
def reset_row_size():
    """Reset the current tab view row size to its default value.

    """
    widget = common.widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.default_row_size().height()

    widget.set_row_size(v)


@common.error
@common.debug
def show_servers_editor():
    """Shows :class:`~bookmarks.server.view.ServerEditorDialog` widget.

    """
    from .server import view as editor
    editor.show()


@common.error
@common.debug
def show_add_asset(server=None, job=None, root=None):
    """Shows the dialog used to create
    a new asset item.

    Args:
        server (str): `server` path segment. Optional.
        job (str): `job` path segment. Optional.
        root (str): `root` path segment. Optional.

    """
    if not all((server, job, root)):
        server = common.active('server')
        job = common.active('job')
        root = common.active('root')

    if not all((server, job, root)):
        return None

    from .editor import addjobeditor as editor
    editor.show()


@common.error
@common.debug
def show_add_file(extension=None, file=None, create_file=True, increment=False):
    """Shows :class:`~bookmarks.file_saver.FileSaverWidget` to add a new empty template
    path file.

    Args:
        extension (str): An format, for example, 'psd'.
        file (str): Path to an existing file. Optional.
        create_file (bool): Creates an empty file if True.
        increment (bool): Increment the version number element of ``file``.

    Returns:
        The editor widget instance.

    """
    from .file_saver import main as editor
    widget = editor.show(
        file=file, create_file=create_file, increment=increment, extension=extension
    )
    widget.itemCreated.connect(common.signals.fileAdded)
    return widget


@common.error
@common.debug
def edit_bookmark(server=None, job=None, root=None):
    """Shows :class:`~bookmarks.editor.bookmark_properties.BookmarkPropertyEditor` to
    edit the properties of a bookmark item.

    Args:
        server (str): `server` path segment. Optional.
        job (str): `job` path segment. Optional.
        root (str): `root` path segment. Optional.

    """
    if not all((server, job, root)):
        server = common.active('server')
        job = common.active('job')
        root = common.active('root')

    if not all((server, job, root)):
        return None

    from .editor import bookmark_properties as editor
    editor.show(server, job, root)


@common.error
@common.debug
def edit_asset(asset=None):
    """Shows :class:`~bookmarks.editor.asset_properties.AssetPropertyEditor` to
    edit the properties of a bookmark item.

    Args:
        asset (str): `asset` path segment.

    """
    server = common.active('server')
    job = common.active('job')
    root = common.active('root')

    if not all((server, job, root)):
        return None
    if asset is None:
        asset = common.active('asset')
    if asset is None:
        return

    from .editor import asset_properties as editor
    widget = editor.show(server, job, root, asset=asset)
    return widget


@common.error
@common.debug
def edit_asset_links():
    """Shows the editor used to edit asset links and template presets."""
    if not common.active('root'):
        raise RuntimeError('No active root set.')

    from .templates import view as editor
    editor.show()


@common.error
@common.debug
def edit_file(f):
    """Edit the given file.

    """
    from .file_saver import main as editor
    widget = editor.show(
        extension=QtCore.QFileInfo(f).suffix(), file=f
    )
    return widget


@common.error
@common.debug
def show_preferences():
    """Shows the :class:`~bookmarks.editor.preferences.PreferenceEditor` editor widget.

    """
    from .editor import preferences as editor
    widget = editor.show()
    return widget


@common.error
@common.debug
def add_item():
    """Triggers the current tab's add item action.

    """
    idx = common.current_tab()
    if idx == common.BookmarkTab:
        show_servers_editor()
    elif idx == common.AssetTab:
        show_add_asset()
    elif idx == common.FileTab:
        show_add_file()
    elif idx == common.FavouriteTab:
        pass


@common.error
@common.debug
@selection
def edit_item_properties(index):
    """Action used to open an item editor.

    """
    pp = index.data(common.ParentPathRole)
    if len(pp) == 3:
        server, job, root = index.data(common.ParentPathRole)[0:3]
        edit_bookmark(
            server=server, job=job, root=root, )
    elif len(pp) == 4:
        v = index.data(common.ParentPathRole)[-1]
        edit_asset(asset=v)
    elif len(pp) >= 4:
        v = index.data(common.PathRole)
        edit_file(v)


@common.error
@common.debug
def refresh(idx=None):
    """Refresh the model of an item view.

    Args:
        idx (int): The item tab number. Optional.

    """
    w = common.widget(idx=idx)
    model = w.model().sourceModel()

    # Remove the asset list cache if we're forcing a refresh on the asset tab
    if common.current_tab() == common.AssetTab:
        # Read from the cache if it exists
        p = model.parent_path()
        source = '/'.join(p) if p else ''
        assets_cache_dir = QtCore.QDir(f'{common.active("root", path=True)}/{common.bookmark_item_data_dir}/assets')
        if not assets_cache_dir.exists():
            assets_cache_dir.mkpath('.')
        assets_cache_name = common.get_hash(source)
        cache = f'{assets_cache_dir.path()}/{assets_cache_name}.cache'

        if assets_cache_dir.exists() and os.path.exists(cache):
            log.debug(__name__, 'Removing asset cache {cache}')
            os.remove(cache)

    model.reset_data(force=True)


@common.error
@common.debug
def toggle_flag(flag, v):
    """Toggle an item filter flag in the current item tab.

    Args:
        flag (int): An item filter flag.
        v (bool): The filter flag value.

    """
    proxy = common.widget().model()
    proxy.set_filter_flag(flag, v)
    proxy.filterFlagChanged.emit(flag, v)


@common.error
@common.debug
def toggle_full_screen():
    """Toggle full-screen view.

    """
    if common.main_widget.isFullScreen():
        common.main_widget.showNormal()
    else:
        common.main_widget.showFullScreen()


@common.error
@common.debug
def toggle_maximized():
    """Toggle maximized view.

    """
    if common.main_widget.isMaximized():
        common.main_widget.showNormal()
    else:
        common.main_widget.showMaximized()


@common.error
@common.debug
def toggle_minimized():
    """Toggle minimized view.

    """
    if common.main_widget.isMinimized():
        common.main_widget.showNormal()
    else:
        common.main_widget.showMinimized()


@common.error
@common.debug
def toggle_stays_always_on_top():
    """Toggle :class:`~bookmarks.standalone.BookmarksAppWindow` stacking value.

    """
    if common.init_mode != common.Mode.Standalone:
        return

    w = common.main_widget
    flags = w.windowFlags()
    state = flags & QtCore.Qt.WindowStaysOnTopHint

    common.settings.setValue('settings/always_always_on_top', not state)
    w.hide()
    w.update_window_flags()
    w.activateWindow()
    w.showNormal()


@common.error
@common.debug
def exec_instance():
    """Opens a new app instance.

    """
    if common.get_platform() == common.PlatformWindows:
        if common.env_key not in os.environ:
            s = 'Bookmarks does not seem to be installed correctly:\n'
            s += f'"{common.env_key}" environment variable is not set.'
            raise RuntimeError(s)

        p = os.environ[common.env_key] + os.path.sep + 'bookmarks.exe'
        subprocess.Popen(p)
    elif common.get_platform() == common.PlatformMacOS:
        raise NotImplementedError('Not implemented.')
    elif common.get_platform() == common.PlatformUnsupported:
        raise NotImplementedError('Not implemented.')


@common.error
@common.debug
@must_be_initialized
def change_tab(idx):
    """Changes the current item tab.

    """
    if common.current_tab() == idx:
        return
    common.signals.tabChanged.emit(idx)


@common.error
@common.debug
def next_tab():
    """Shows the next available item tab.

    """
    n = common.current_tab()
    n += 1
    if n > (common.main_widget.stacked_widget.count() - 1):
        common.signals.tabChanged.emit(common.BookmarkTab)
        return
    common.signals.tabChanged.emit(n)


@common.error
@common.debug
def previous_tab():
    """Shows the previous item tab.

    """
    n = common.current_tab()
    n -= 1
    if n < 0:
        n = common.main_widget.stacked_widget.count() - 1
        common.signals.tabChanged.emit(n)
        return
    common.signals.tabChanged.emit(n)


@common.error
@common.debug
def change_sorting(role, order):
    """Change the sorting role of the current item view model.

    """
    model = common.widget().model().sourceModel()
    model.sortingChanged.emit(role, order)


@common.error
@common.debug
def toggle_sort_order():
    """Change the sorting order of the current item view model.

    """
    model = common.widget().model().sourceModel()
    order = model.sort_order()
    role = model.sort_by()
    model.sortingChanged.emit(role, not order)


@common.error
@common.debug
@selection
def copy_selected_path(index):
    """Copies the path of the given item to the clipboard.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    if not index.data(common.FileInfoLoaded):
        return
    if common.get_platform() == common.PlatformMacOS:
        mode = common.MacOSPath
    elif common.get_platform() == common.PlatformWindows:
        mode = common.WindowsPath
    else:
        mode = common.UnixPath
    copy_path(
        index.data(common.PathRole), mode=mode, first=False
    )


@common.error
@common.debug
@selection
def copy_selected_alt_path(index):
    """Copies the path of the given item to the clipboard.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    if not index.data(common.FileInfoLoaded):
        return
    copy_path(
        index.data(common.PathRole), mode=common.UnixPath, first=True
    )


@common.debug
@common.error
@selection
def show_notes(index):
    """Shows the :class:`~bookmarks.notes.NoteEditor` editor.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    from . import notes
    editor = notes.show(index)
    return editor


@common.debug
@common.error
@selection
def preview_thumbnail(index):
    """Displays a preview of the currently selected item.

    For image files we'll try to load and display the image itself, and for any
    other case we will fall back to cached or default thumbnail images.

    """
    if not index.isValid():
        return

    source = index.data(common.PathRole)
    source = common.get_sequence_start_path(source)

    # Let's try to open the image outright
    # If this fails, we will try and look for a saved thumbnail image,
    # and if that fails too, we will display a general thumbnail.

    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = images.get_thumbnail(
        server, job, root, source, get_path=True, fallback_thumb=common.widget().itemDelegate().fallback_thumb
    )
    if not source:
        return

    # Let's get a weakref to the model data
    ref = common.get_ref_from_source_index(index)

    from .items.widgets import image_viewer
    image_viewer.show(source, ref, common.widget(), oiio=False)


@common.debug
@common.error
@selection
def preview_image(index):
    """Shows a preview of the given image.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    if not index.isValid():
        return

    source = index.data(common.PathRole)
    source = common.get_sequence_start_path(source)

    if QtCore.QFileInfo(source).suffix() not in images.get_oiio_extensions():
        raise RuntimeError(f'{source} is not a valid image file.')

    # Let's get a weakref to the model data
    ref = common.get_ref_from_source_index(index)

    from .items.widgets import image_viewer
    image_viewer.show(source, ref, common.widget(), oiio=True)


@common.debug
@common.error
@selection
def reveal_selected(index):
    """Reveal the currently selected item in the file explorer.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    reveal(index)


@common.debug
@common.error
@selection
def reveal_url(index):
    """Opens the given item's primary ULR.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    source_path = index.data(common.ParentPathRole)
    if len(source_path) == 3:
        table = database.BookmarkTable
    else:
        table = database.AssetTable

    source = '/'.join(source_path)
    db = database.get(*source_path[0:3])

    if not index.isValid():
        return
    if not index.data(common.PathRole):
        return

    server, job, root = index.data(common.ParentPathRole)[0:3]
    if len(index.data(common.ParentPathRole)) >= 4:
        asset = index.data(common.ParentPathRole)[3]
    else:
        asset = None

    from .shotgun import shotgun
    sg_properties = shotgun.SGProperties(server, job, root, asset)
    sg_properties.init()
    if sg_properties.verify():
        urls = sg_properties.urls()
        if urls:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(list(reversed(urls))[0]))
            return

    v = db.value(source, 'url1', table)
    if v:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(v)),

    v = db.value(source, 'url2', table)
    if v:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(v)),


@common.debug
@common.error
@selection
def toggle_favourite(index):
    """Toggles the ``MarkedAsFavourite`` flag of the given item.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    common.widget().save_selection()
    common.widget().toggle_item_flag(index, common.MarkedAsFavourite)
    common.widget().update(index)


@common.debug
@common.error
@selection
def toggle_archived(index):
    """Toggles the ``MarkedAsArchived`` flag of the given item.

    Args:
        index (QtCore.QModelIndex): The item index.

    """

    common.widget().save_selection()
    common.widget().toggle_item_flag(index, common.MarkedAsArchived)
    common.widget().update(index)
    common.widget().model().invalidateFilter()


@QtCore.Slot(str)
@common.debug
@common.error
def show_asset(path):
    """Slot used to reveal an asset item in the asset tab.

    Args:
        path (str): Path of the asset item.

    """
    index = common.active_index(common.BookmarkTab)
    if not index or not index.isValid():
        return

    # Check if the added asset has been added to the currently active bookmark
    if index.data(common.PathRole) not in path:
        return

    # Change tabs otherwise
    common.signals.tabChanged.emit(common.AssetTab)

    widget = common.widget(common.AssetTab)
    widget.show_item(path, role=common.PathRole)


@common.debug
@common.error
def reveal(item):
    """Reveals an item in the file explorer.

    Args:
        item(str or QModelIndex): The item to show in the file manager.

    """
    if isinstance(
            item, (QtCore.QModelIndex, QtCore.QPersistentModelIndex, QtWidgets.QListWidgetItem)
    ):
        path = item.data(common.PathRole)
    elif isinstance(item, str):
        path = item
    else:
        return

    path = common.get_sequence_end_path(path)
    if common.get_platform() == common.PlatformWindows:
        if QtCore.QFileInfo(path).isFile():
            args = ['/select,', QtCore.QDir.toNativeSeparators(path)]
        elif common.is_dir(path):
            path = os.path.normpath(path)
            args = [path, ]
        else:
            args = ['/select,', QtCore.QDir.toNativeSeparators(path)]
        QtCore.QProcess.startDetached('explorer', args)
        return
    elif common.get_platform() == common.PlatformMacOS:
        args = ['-e', 'tell application "Finder"', '-e', 'activate', '-e',
                f'select POSIX file "{QtCore.QDir.toNativeSeparators(path)}"', '-e', 'end tell']
        QtCore.QProcess.startDetached('osascript', args)
        return
    elif common.get_platform() == common.PlatformUnsupported:
        raise NotImplementedError(
            f'{QtCore.QSysInfo().productType()} is unsupported.'
        )


@common.debug
@common.error
def copy_path(path, mode=common.WindowsPath, first=True, copy=True):
    """Copies the given path to the clipboard.

    The path will be conformed to the given mode. E.g. forward slashes
    converted to back-slashes for `WindowsPath`.

    Args:
        path (str): A file path.
        mode (int):
            Any of ``WindowsPath``, ``UnixPath`` or ``MacOSPath``.
            Defaults to ``WindowsPath``.
        first (bool): When `True`, copies the first item of a sequence.
        copy (bool):
            When `False`, the converted path won't be copied to the clipboard.
            Defaults to `True`.

    Returns:
        str: The path copied to the clipboard.

    """
    if first:
        path = common.get_sequence_start_path(path)
    else:
        path = common.get_sequence_end_path(path)

    if mode is None and copy:
        QtWidgets.QApplication.clipboard().setText(path)
        return path
    elif mode is None and not copy:
        return path

    # Normalise path
    path = re.sub(
        r'[\/\\]', r'/', path, flags=re.IGNORECASE
    ).strip('/')

    if mode == common.WindowsPath:
        prefix = '//' if ':' not in path else ''
    elif mode == common.UnixPath:
        prefix = '//' if ':' not in path else ''
    elif mode == common.MacOSPath:
        prefix = 'smb://'
        path = path.replace(':', '')
    else:
        prefix = ''

    path = prefix + path
    if mode == common.WindowsPath:
        path = re.sub(
            r'[\/\\]', r'\\', path, flags=re.IGNORECASE
        )

    if copy:
        QtWidgets.QApplication.clipboard().setText(path)
    return path


@common.debug
@common.error
def execute(index, first=False):
    """Given the model index, executes the index's path using
    `QDesktopServices`.

    Args:
        index (QModelIndex or str): A list item index or a path to a file.
        first (bool): Execute the first item of a collapsed sequence.

    """
    if isinstance(index, str):
        url = QtCore.QUrl.fromLocalFile(index)
        QtGui.QDesktopServices.openUrl(url)
        return

    if not index.isValid():
        return
    path = index.data(common.PathRole)
    if first:
        path = common.get_sequence_start_path(path)
    else:
        path = common.get_sequence_end_path(path)

    ext = QtCore.QFileInfo(path).suffix()

    # Handle Maya files
    if ext in ('ma', 'mb'):
        for app in (
                'maya', 'maya2017', 'maya2018', 'maya2019', 'maya2020', 'maya2022', 'maya2023', 'maya2024',
                'maya2025', 'maya2026'
        ):
            executable = common.get_binary(app)
            if not executable:
                continue
            execute_detached(executable, args=['-file', path])
            return

    # Handle Nuke files
    if ext in ('nk', 'nknc'):
        executable = common.get_binary('nuke')
        if executable:
            execute_detached(path, args=[path, ])
            return

    # Handle Houdini files
    if ext == 'hiplc':
        for app in ('houdiniinidie', 'houindie', 'houind', 'houdiniind', 'hindie'):
            executable = common.get_binary(app)
            if executable:
                execute_detached(executable, args=[path, ])
                return

    if ext == 'hip':
        for app in ('houdini', 'houdinifx', 'houfx', 'hfx', 'houdinicore', 'hcore'):
            executable = common.get_binary(app)
            if executable:
                execute_detached(executable, args=[path, ])
                return

    # Handle RV files
    if ext == 'rv':
        for app in ('rv', 'tweakrv', 'shotgunrv', 'shotgridrv', 'sgrv'):
            executable = common.get_binary(app)
            if executable:
                execute_detached(executable, args=[path, ])
                return

    # Handle blender files
    if ext in ('blend',):
        for app in ('blender', 'blender2.8', 'blender2.9', 'blender3', 'blender3.0', 'blender3.1', 'blender3.2',
                    'blender3.3', 'blender3.4', 'blender3.5'
                    ):
            executable = common.get_binary(app)
            if executable:
                execute_detached(executable, args=[path, ])
                return

    # Handle After Effects files
    if ext in ('aep',):
        for app in ('afterfx', 'aftereffects', 'ae', 'afx'):
            executable = common.get_binary(app)
            if executable:
                execute_detached(executable, args=[path, ])
                return

    url = QtCore.QUrl.fromLocalFile(path)
    QtGui.QDesktopServices.openUrl(url)


@common.debug
@common.error
@selection
def capture_thumbnail(index):
    """Captures a thumbnail for the given index.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(common.PathRole)

    if common.init_mode == common.Mode.Standalone:
        common.save_window_state(common.main_widget)
        common.main_widget.hide()

    from .items.widgets import thumb_capture as editor
    widget = editor.show(
        server=server, job=job, root=root, source=source, proxy=False
    )

    if common.init_mode == common.Mode.Standalone:
        from . import standalone
        widget.captureFinished.connect(standalone.show)

    widget.captureFinished.connect(widget.save_image)
    model = index.model().sourceModel()
    widget.accepted.connect(
        functools.partial(model.updateIndex.emit, index)
    )


@common.debug
@common.error
@selection
def pick_thumbnail_from_file(index):
    """Picks a thumbnail for the given index.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(common.PathRole)

    from .items.widgets import thumb_picker as editor
    widget = editor.show(
        server=server, job=job, root=root, source=source
    )

    widget.fileSelected.connect(widget.save_image)
    model = index.model().sourceModel()
    widget.fileSelected.connect(lambda x: model.updateIndex.emit(index))


@common.debug
@common.error
@selection
def pick_thumbnail_from_library(index):
    """Picks a thumbnail for the given index.

    Args:
        index (QtCore.QModelIndex): The item index.

    """
    server, job, root = index.data(common.ParentPathRole)[0:3][0:3]
    source = index.data(common.PathRole)

    if not all((server, job, root, source)):
        return

    from .items.widgets import thumb_library as editor
    widget = editor.show()

    widget.itemSelected.connect(
        lambda v: images.create_thumbnail_from_image(server, job, root, source, v)
    )
    widget.itemSelected.connect(
        lambda _: index.model().sourceModel().updateIndex.emit(index)
    )


def execute_detached(path, args=None):
    """Utility function used to execute a file as a detached process.

    On Windows, we'll call the given file using the file explorer as we want to
    avoid the process inheriting the parent process' environment variables.

    Args:
        path (str): The path to the file to execute.
        args (list): A list of optional arguments to pass to the process.
    """
    if common.get_platform() == common.PlatformWindows:
        proc = QtCore.QProcess()

        proc.setProgram(os.path.normpath(path))
        if args:
            proc.setArguments(args)

        # We don't want to pass on our current environment (we might be calling from inside a DCC)
        env = QtCore.QProcessEnvironment.systemEnvironment()

        # But we do want to pass on the currently active items. This information can be used in an
        # unsupported DCC to manipulate context
        if 'Bookmarks_ROOT' in os.environ:
            env.insert('Bookmarks_ROOT', os.environ['Bookmarks_ROOT'])

        env.insert('B_SERVER', common.active('server'))
        env.insert('B_JOB', common.active('job'))
        env.insert('B_ROOT', common.active('root'))
        env.insert('B_ASSET', common.active('asset'))
        env.insert('B_TASK', common.active('task'))

        proc.setProcessEnvironment(env)
        proc.startDetached()
    else:
        raise NotImplementedError('Not implemented.')


@common.debug
@common.error
def pick_launcher_item():
    """Slot called when a launcher item was clicked.

    """
    from . import application_launcher as editor
    widget = editor.show()
    widget.itemSelected.connect(execute_detached)


@common.debug
@common.error
@selection
def remove_thumbnail(index):
    """Deletes a thumbnail file and the cached entries associated
    with it.

    """
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(common.PathRole)

    thumbnail_path = images.get_cached_thumbnail_path(
        server, job, root, source
    )
    images.ImageCache.flush(thumbnail_path)

    if QtCore.QFile(thumbnail_path).exists():
        if not QtCore.QFile(thumbnail_path).remove():
            raise RuntimeError('Could not remove the thumbnail')

    source_index = index.model().mapToSource(index)
    idx = source_index.row()

    data = source_index.model().model_data()[idx]
    data[common.ThumbnailLoaded] = False
    source_index.model().updateIndex.emit(source_index)


@common.debug
@common.error
@selection
def copy_properties(index):
    pp = index.data(common.ParentPathRole)
    if not pp:
        return

    from .editor import clipboard
    editor = clipboard.show(
        *pp[0:3],
        asset=pp[3] if len(pp) == 4 else None,
    )

    return editor


@common.debug
@common.error
@selection
def paste_properties(index):
    pp = index.data(common.ParentPathRole)
    if len(pp) == 3:
        table = database.BookmarkTable
        clipboard = common.BookmarkPropertyClipboard
    elif len(pp) == 4:
        table = database.AssetTable
        clipboard = common.AssetPropertyClipboard
    else:
        raise NotImplementedError('Not implemented.')

    if not common.CLIPBOARD[clipboard]:
        raise RuntimeError('Could not paste properties. Clipboard is empty.')

    source = '/'.join(pp)

    # Write the values to the database
    for k in common.CLIPBOARD[clipboard]:
        v = common.CLIPBOARD[clipboard][k]
        database.get(*pp[0:3]).set_value(source, k, v, table)
        log.info(f'Pasted {k} = {v} to {source}')


@common.debug
@common.error
def toggle_active_mode():
    """Toggle the active path mode.

    """
    if common.active_mode == common.ActiveMode.Explicit:
        raise RuntimeError('The current active values are overridden and cannot be toggled.')

    common.active_mode = int(not bool(common.active_mode))
    common.write_current_mode_to_lock()
    common.prune_lock()

    if common.main_widget is None or not common.main_widget.is_initialized:
        return

    # Toggle the active mode
    common.signals.activeModeChanged.emit(common.active_mode)
    common.source_model(common.BookmarkTab).reset_data(force=True)


@common.error
@common.debug
@selection
def export_properties(index):
    """Exports the selected item's properties.

    """
    from . import importexport
    importexport.export_item_properties(index)


@common.error
@common.debug
@selection
def import_properties(index):
    """Imports properties and applies them to the selected item.

    """
    from . import importexport
    importexport.import_item_properties(index)


@common.error
@common.debug
def import_json_asset_properties(path=None, prompt=True):
    """Imports properties and applies them to the selected item.

    """
    from . import importexport

    model = common.model(common.AssetTab)
    indexes = [QtCore.QPersistentModelIndex(model.index(f, 0)) for f in range(model.rowCount())]
    importexport.import_json_asset_properties(indexes, prompt=prompt, path=path)


@common.debug
@common.error
@selection
def convert_image_sequence(index):
    """Convert the selected image sequence to a movie file.

    """
    from .external import ffmpeg_widget
    ffmpeg_widget.show(index)


@common.debug
@common.error
@selection
def convert_image_sequence_with_akaconvert(index):
    from .external import akaconvert
    akaconvert.show(index)


@common.debug
@common.error
@selection
def delete_selected_files(index):
    """Deletes the selected file items.

    """
    from . import log
    if common.show_message(
            'Delete file?', body='Are you sure you want to delete the selected file(s)? They will be permanently lost.',
            buttons=[common.YesButton, common.CancelButton], message_type='error',
            modal=True, ) == QtWidgets.QDialog.Rejected:
        return

    model = index.model().sourceModel()
    f_data = common.get_data(model.parent_path(), model.task(), common.FileItem)
    s_data = common.get_data(model.parent_path(), model.task(), common.SequenceItem)

    paths = set(common.get_sequence_paths(index))

    # Remove file on disk
    _failed = []
    for path in paths:
        _file = QtCore.QFile(path)
        if not _file.exists():
            continue
        if not _file.remove():
            _failed.append(path)
            log.error(f'Could not remove {path}.')

    # Mark cached file data
    for v in f_data.values():
        if v[common.PathRole] in paths:
            if v[common.PathRole] in _failed:
                continue
            paths.remove(v[common.PathRole])
            v[common.FlagsRole] = QtCore.Qt.NoItemFlags | common.MarkedAsArchived

    # Mark cache sequence data
    if not _failed:
        path = index.data(common.PathRole)
        for v in s_data.values():
            if v[common.PathRole] == path:
                v[common.FlagsRole] = QtCore.Qt.NoItemFlags | common.MarkedAsArchived

    index.model().invalidateFilter()

    if _failed:
        raise RuntimeError(
            'Not all files could be removed.\n'
            'Some might be in use by another process.'
        )


@common.error
@common.debug
@selection
def show_publish_widget(index):
    """Shows the :class:`~bookmarks.publish.editor.PublishWidget` editor.

    """
    from . import publish as editor

    widget = editor.show(index)
    return widget


@common.error
@common.debug
@selection
def push_to_rv(index):
    if common.current_tab() not in (common.FileTab, common.FavouriteTab):
        return

    path = common.get_sequence_start_path(
        index.data(common.PathRole)
    )

    from .external import rv
    rv.execute_rvpush_command(path, rv.PushAndClear)


@common.error
@common.debug
@selection
def push_to_rv_full_screen(index):
    if common.current_tab() not in (common.FileTab, common.FavouriteTab):
        return

    path = common.get_sequence_start_path(
        index.data(common.PathRole)
    )

    from .external import rv
    rv.execute_rvpush_command(path, rv.PushAndClearFullScreen)
