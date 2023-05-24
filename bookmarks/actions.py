"""User actions module.

These actions are usually triggered by the user via keyboard shortcuts or by
interactions with the UI.

"""
import functools
import json
import os
import re
import subprocess
import zipfile

from PySide2 import QtCore, QtWidgets, QtGui

from . import common
from . import database
from . import images


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


@common.error
@common.debug
def reveal_default_bookmarks_json():
    """Reveals :attr:`common.default_bookmarks_template` in the file explorer.

    """
    reveal(
        common.rsc(
            f'{common.TemplateResource}/{common.default_bookmarks_template}'
        )
    )


@common.error
@common.debug
def add_server(v):
    """Adds a server item to the list of user specified servers.

    Args:
        v (str): A path to a server, e.g. `Q:/jobs`.

    """
    common.check_type(v, str)

    for bookmark in common.default_bookmarks.values():
        if bookmark['server'] == v:
            raise RuntimeError(f'Cannot add {v}. Server is already a default server.)')

    common.servers[v] = v
    common.settings.set_servers(common.servers)
    common.signals.serverAdded.emit(v)


@common.error
@common.debug
def remove_server(v):
    """Remove a server item from the list of user specified servers.

    Args:
        v (str): A path to a server, e.g. `Q:/jobs`.

    """
    for bookmark in common.default_bookmarks.values():
        if bookmark['server'] == v:
            raise RuntimeError('Default server cannot be removed.')

    bookmarks = [_v for _v in common.bookmarks.values() if v in _v['server']]
    if bookmarks:
        raise RuntimeError(
            f'Can\'t remove "{v}".\nServer has {len(bookmarks)} active bookmarks.'
        )

    if v in common.servers:
        del common.servers[v]

    common.settings.set_servers(common.servers)
    common.signals.serverRemoved.emit(v)


def add_bookmark(server, job, root):
    """Add the given bookmark item and save it in the user settings file.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.

    """
    for arg in (server, job, root):
        common.check_type(arg, str)

    k = common.bookmark_key(server, job, root)
    common.bookmarks[k] = {
        'server': server,
        'job': job,
        'root': root
    }
    common.settings.set_bookmarks(common.bookmarks)
    common.signals.bookmarkAdded.emit(server, job, root)


def remove_bookmark(server, job, root):
    """Remove the given bookmark from the user settings file.

    Removing a bookmark item will close and delete the item's database controller
    instances.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): A path segment.

    """
    for arg in (server, job, root):
        common.check_type(arg, str)

    # If the active bookmark is removed, make sure we're clearing the active
    # bookmark. This will cause all models to reset so show the bookmark tab.
    if (
            common.active('server') == server and
            common.active('job') == job and
            common.active('root') == root
    ):
        set_active('server', None)
        change_tab(common.BookmarkTab)

    # Close, and delete all cached bookmark databases of this bookmark
    database.remove_db(server, job, root)

    k = common.bookmark_key(server, job, root)
    if k not in common.bookmarks:
        return

    del common.bookmarks[k]
    common.settings.set_bookmarks(common.bookmarks)
    common.signals.bookmarkRemoved.emit(server, job, root)


def add_favourite(source_paths, source):
    """Add and save a favourite item.

    Args:
        source_paths (list): A list of parent paths.
        source (str): The item to save as a favourite item.

    """
    if not source_paths or not source:
        return

    common.check_type(source_paths, (tuple, list))
    common.check_type(source, str)

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

    common.check_type(source_paths, (tuple, list))
    common.check_type(source, str)

    if source not in common.favourites:
        return

    del common.favourites[source]
    common.settings.set_favourites(common.favourites)
    common.signals.favouriteRemoved.emit(source_paths, source)


@QtCore.Slot(tuple)
@QtCore.Slot(str)
@QtCore.Slot(bool)
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
        tab_idx = common.BookmarkTab
    elif len(parent_paths) == 4:
        tab_idx = common.AssetTab
    elif len(parent_paths) > 4:
        tab_idx = common.FileTab
    else:
        return

    model = common.source_model(idx=tab_idx)

    p = model.source_path()
    k = model.task()

    # Make sure data is up-to-date in all data sets.
    for t in (common.FileItem, common.SequenceItem,):
        data = common.get_data(p, k, t)

        for n, item in enumerate(data.values()):
            # Bail if the data set is large
            if n > limit:
                break

            if item[common.PathRole] == source:
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
        from . import ui
        mbox = ui.MessageBox(
            'Are you sure you want to clear your saved items?',
            buttons=[ui.YesButton, ui.NoButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

    common.favourites = {}
    common.settings.set_favourites(common.favourites)
    common.signals.favouritesChanged.emit()


@common.error
@common.debug
def export_favourites(*args, destination=None):
    """Saves all favourite items to a zip file.

    Args:
        args (tuple): A `server`, `job`, `root` argument tuple.
        destination (str): The path to save the zip file to. Optional.

    """
    common.check_type(destination, (None, str))

    if destination is None:
        destination, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption='Select where to save your favourites',
            filter=f'*.{common.favorite_file_ext}',
            dir=QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.HomeLocation
            ),
        )
        if not destination:
            return

    data = common.favourites.copy()

    # Assemble the zip file
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_STORED) as _zip:

        # Add thumbnail to zip
        for source, source_paths in common.favourites.items():
            server, job, root = source_paths[0:3]

            thumbnail_path = images.get_cached_thumbnail_path(
                server,
                job,
                root,
                source
            )

            file_info = QtCore.QFileInfo(thumbnail_path)
            if file_info.exists():
                _zip.write(thumbnail_path, file_info.fileName())

            # Add description
            k = 'description'
            db = database.get_db(server, job, root)
            if source == db.source():
                table = database.BookmarkTable
            else:
                table = database.AssetTable

            v = db.value(source, k, table)
            if v:
                _zip.writestr(
                    file_info.baseName() + k,
                    database.b64encode(v)
                )

        # Let's Save the current list favourites to the zip
        v = json.dumps(
            data,
            ensure_ascii=True,
        )
        _zip.writestr(common.favorite_file_ext, v)

    return destination


@common.error
@common.debug
def import_favourites(*args, source=None):
    """Import a previously exported favourites file.

    Args:
        source (str): Path to a file. Defaults to `None`.

    """
    common.check_type(source, (None, str))
    if source is None:
        source, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption='Select the favourites file to import',
            filter=f'*.{common.favorite_file_ext}'
        )
        if not source:
            return

    with zipfile.ZipFile(source, compression=zipfile.ZIP_STORED) as _zip:
        corrupt = _zip.testzip()
        if corrupt:
            raise RuntimeError(
                f'This zip archive seem corrupted: {corrupt}.'
            )

        if common.favorite_file_ext not in _zip.namelist():
            raise RuntimeError('Invalid file.')

        with _zip.open(common.favorite_file_ext) as _f:
            v = _f.read()

        data = json.loads(
            v,
            parse_int=int,
            parse_float=float,
            object_hook=common.int_key
        )

        for _source, source_paths in data.items():
            server, job, root = source_paths[0:3]

            thumbnail_path = images.get_cached_thumbnail_path(
                server,
                job,
                root,
                _source,
            )

            # There's a thumbnail already, we'll skip
            file_info = QtCore.QFileInfo(thumbnail_path)
            if not file_info.exists():
                # Let's write the thumbnails to disk
                if file_info.fileName() in _zip.namelist():
                    root = '/'.join(
                        (server, job, root,
                         common.bookmark_cache_dir)
                    )
                    _zip.extract(
                        file_info.fileName(),
                        root
                    )
                    images.ImageCache.flush(thumbnail_path)

            # Add description
            k = 'description'
            if not file_info.baseName() + k in _zip.namelist():
                continue

            v = _zip.read(file_info.baseName() + k)
            if not v:
                continue

            db = database.get_db(server, job, root)
            if source == db.source():
                table = database.BookmarkTable
            else:
                table = database.AssetTable
            db.set_value(source, k, database.b64decode(v), table=table)

    common.settings.set_favourites(data)
    common.signals.favouritesChanged.emit()


@common.error
@common.debug
def prune_bookmarks():
    """Removes invalid bookmark items from the current set.

    """
    if not common.bookmarks:
        return
    n = 0
    for k in list(common.bookmarks.keys()):
        if not QtCore.QFileInfo(k).exists():
            n += 1
            remove_bookmark(
                common.bookmarks[k]['server'],
                common.bookmarks[k]['job'],
                common.bookmarks[k]['root']
            )

    from . import ui
    mbox = ui.OkBox(
        f'{n} items pruned.',
    )
    mbox.open()


def set_active(k, v):
    """Sets the given path as the active path segment for the given key.

    Args:
        k (str): An active key, e.g. `'server'`.
        v (str or None): A path segment, e.g. '//myserver/jobs'.

    """
    common.check_type(k, str)
    common.check_type(k, (str, None))

    if k not in common.SECTIONS['active']:
        raise ValueError(
            'Invalid active key. Key must be the one of "{}"'.format(
                '", "'.join(common.SECTIONS['active'])
            )
        )

    common.active_paths[common.active_mode][k] = v
    if common.active_mode == common.SynchronisedActivePaths:
        common.settings.setValue(f'active/{k}', v)


@common.error
@common.debug
def set_task_folder(v):
    """Sets the active task folder.

    Args:
        v (str): A `task` path segment, e.g. 'scenes'.

    """
    set_active('task', v)
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


@QtCore.Slot()
@must_be_initialized
def toggle_task_view():
    """Shows or hides the visibility of the
    :class:~bookmarks.items.task_items.TaskItemView`` widget.

    """
    if common.current_tab() != common.FileTab:
        return
    common.widget(common.TaskTab).setHidden(
        not common.widget(common.TaskTab).isHidden()
    )
    if common.widget(common.TaskTab).isVisible():
        common.widget(common.TaskTab).model().sourceModel().reset_data()


@must_be_initialized
def toggle_filter_editor():
    """Toggles the search filter editor view of the current item view.

    """
    w = common.widget()
    if w.filter_editor.isHidden():
        w.filter_editor.open()
    else:
        w.filter_editor.done(QtWidgets.QDialog.Rejected)


@QtCore.Slot(str)
@QtCore.Slot(str)
@QtCore.Slot(str)
@QtCore.Slot(object)
@must_be_initialized
def asset_identifier_changed(table, source, key, value):
    """Refresh the assets model if the identifier changes.

    """
    # All shotgun fields should be prefixed by 'shotgun_'
    if not (table == database.BookmarkTable and key == 'identifier'):
        return
    model = common.source_model(common.AssetTab)
    model.reset_data()


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

    v = model.row_size.height() + common.size(common.thumbnail_size / 15)
    if v >= common.thumbnail_size:
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

    v = model.row_size.height() - common.size(common.thumbnail_size / 15)
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
def show_bookmarker():
    """Shows :class:`~bookmarks.bookmarker.main.BookmarkerWidget`.

    """
    from .bookmarker import main as editor
    widget = editor.show()
    return widget


@common.error
@common.debug
def show_add_asset(server=None, job=None, root=None):
    """Shows :class:`~bookmarks.editor.asset_properties.AssetPropertyEditor` to create
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

    from .editor import asset_properties as editor
    widget = editor.show(server, job, root)
    return widget


@common.error
@common.debug
def show_add_file(
        asset=None, extension=None, file=None, create_file=True, increment=False
):
    """Shows :class:`~bookmarks.file_saver.FileSaverWidget` to add a new empty template
    path file.

    Args:
        asset (str): Name of the asset.
        extension (str): An format, e.g. 'psd'.
        file (str): Path to an existing file. Optional.
        create_file (bool): Creates an empty file if True.
        increment (bool): Increment the version number element of ``file``.

    Returns:
        The editor widget instance.

    """
    server = common.active('server')
    job = common.active('job')
    root = common.active('root')

    if asset is None:
        asset = common.active('asset')

    args = (server, job, root, asset)

    if not all(args):
        return None

    from .file_saver import main as editor
    widget = editor.show(
        server,
        job,
        root,
        asset,
        file=file,
        create_file=create_file,
        increment=increment,
        extension=extension
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
def edit_file(f):
    """Edit the given file.

    """
    server = common.active('server')
    job = common.active('job')
    root = common.active('root')
    asset = common.active('asset')

    if not all((server, job, root, asset)):
        return

    from .file_saver import main as editor
    widget = editor.show(
        server,
        job,
        root,
        asset,
        extension=QtCore.QFileInfo(f).suffix(),
        file=f
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
def show_slack():
    """Opens the Slack widget used to send messages using SlackAPI.

    """
    server = common.active('server')
    job = common.active('job')
    root = common.active('root')

    args = (server, job, root)
    if not all(args):
        return

    db = database.get_db(*args)
    token = db.value(
        db.source(),
        'slacktoken',
        database.BookmarkTable
    )
    if token is None:
        raise RuntimeError('Slack is not yet configured.')

    from .slack import slack
    widget = slack.show(token)
    return widget


@common.error
@common.debug
def add_item():
    """Triggers the current tab's add item action.

    """
    idx = common.current_tab()
    if idx == common.BookmarkTab:
        show_bookmarker()
    elif idx == common.AssetTab:
        show_add_asset()
    elif idx == common.FileTab:
        show_add_file()
    elif idx == common.FavouriteTab:
        pass


@common.error
@common.debug
@selection
def edit_item(index):
    """Action used to open an item editor.

    """
    pp = index.data(common.ParentPathRole)
    if len(pp) == 3:
        server, job, root = index.data(common.ParentPathRole)[0:3]
        edit_bookmark(
            server=server,
            job=job,
            root=root,
        )
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
    """Toggle :class:`~bookmarks.standalone.BookmarksAppWindow` full-screen view.

    """
    if common.main_widget.isFullScreen():
        common.main_widget.showNormal()
    else:
        common.main_widget.showFullScreen()


@common.error
@common.debug
def toggle_maximized():
    """Toggle :class:`~bookmarks.standalone.BookmarksAppWindow` maximized view.

    """
    if common.main_widget.isMaximized():
        common.main_widget.showNormal()
    else:
        common.main_widget.showMaximized()


@common.error
@common.debug
def toggle_minimized():
    """Toggle :class:`~bookmarks.standalone.BookmarksAppWindow` minimized view.

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
    if common.init_mode == common.EmbeddedMode:
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

        p = os.environ[common.env_key] + \
            os.path.sep + 'bookmarks.exe'
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
        index.data(common.PathRole),
        mode=mode,
        first=False
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
        index.data(common.PathRole),
        mode=common.UnixPath,
        first=True
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
        server,
        job,
        root,
        source,
        get_path=True,
        fallback_thumb=common.widget().itemDelegate().fallback_thumb
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
    db = database.get_db(*source_path[0:3])

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
    sg_properties = shotgun.ShotgunProperties(server, job, root, asset)
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
    if index.data(common.FlagsRole) & common.MarkedAsDefault:
        from . import ui
        ui.MessageBox('Default bookmark items cannot be archived.').open()
        return

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
            item,
            (QtCore.QModelIndex, QtCore.QPersistentModelIndex, QtWidgets.QListWidgetItem)
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
        args = [
            '-e',
            'tell application "Finder"',
            '-e',
            'activate',
            '-e',
            'select POSIX file "{}"'.format(
                QtCore.QDir.toNativeSeparators(path)
            ), '-e', 'end tell']
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
            Any of ``WindowsPath``, ``UnixPath``, ``SlackPath`` or ``MacOSPath``.
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
        r'[\/\\]',
        r'/',
        path,
        flags=re.IGNORECASE
    ).strip('/')

    if mode == common.WindowsPath:
        prefix = '//' if ':' not in path else ''
    elif mode == common.UnixPath:
        prefix = '//' if ':' not in path else ''
    elif mode == common.SlackPath:
        prefix = 'file://'
    elif mode == common.MacOSPath:
        prefix = 'smb://'
        path = path.replace(':', '')
    else:
        prefix = ''

    path = prefix + path
    if mode == common.WindowsPath:
        path = re.sub(
            r'[\/\\]',
            r'\\',
            path,
            flags=re.IGNORECASE
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
    common.check_type(index, (QtCore.QModelIndex, str))

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

    url = QtCore.QUrl.fromLocalFile(path)
    QtGui.QDesktopServices.openUrl(url)


@common.debug
@common.error
def test_slack_token(token):
    """Tests the given slack api token.

    Args:
        token (str): The slack api token.

    """
    from .slack import slack
    client = slack.SlackClient(token)
    client.verify_token()


@common.debug
@common.error
def suggest_prefix(job):
    """Suggests a prefix for the given job.

    Args:
        job (Job): The `job` to suggest prefix for.

    """
    substrings = re.sub(r'[\_\-\s]+', ';', job).split(';')
    if (not substrings or len(substrings) < 2) and len(job) > 3:
        prefix = job[0:3].upper()
    else:
        prefix = ''.join([f[0] for f in substrings]).upper()
    return prefix


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

    if common.init_mode == common.StandaloneMode:
        common.save_window_state(common.main_widget)
        common.main_widget.hide()

    from .items.widgets import thumb_capture as editor
    widget = editor.show(
        server=server,
        job=job,
        root=root,
        source=source,
        proxy=False
    )

    if common.init_mode == common.StandaloneMode:
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
        server=server,
        job=job,
        root=root,
        source=source
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


def execute_detached(path):
    """Utility function used to execute a file as a detached process.

    On Windows, we'll call the give file through the explorer. This is so, that the
    new process does not inherit the current environment.

    """
    if common.get_platform() == common.PlatformWindows:
        proc = QtCore.QProcess()
        proc.setProgram('cmd.exe')
        proc.setArguments(
            ['/c', 'start', '/i', "%windir%\explorer.exe", os.path.normpath(path)]
        )
        proc.startDetached()


@common.debug
@common.error
def pick_launcher_item():
    """Slot called when a launcher item was clicked.

    """
    from .launcher import gallery as editor
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


@common.error
@common.debug
@selection
def copy_asset_properties(index):
    """Copy asset properties to clipboard.

    Args:
        index (QModelIndex): Index of the currently selected item.

    """
    server, job, root, asset = index.data(common.ParentPathRole)[0:4]
    database.copy_properties(
        server,
        job,
        root,
        asset,
        table=database.AssetTable
    )


@common.error
@common.debug
@selection
def paste_asset_properties(index):
    """Paste asset properties from clipboard to the selected item.

    Args:
        index (QModelIndex): Index of the currently selected item.

    """
    server, job, root, asset = index.data(common.ParentPathRole)[0:4]
    database.paste_properties(
        server,
        job,
        root,
        asset,
        table=database.AssetTable
    )


@common.error
@common.debug
def toggle_active_mode():
    """Toggle the active path mode.

    """
    common.active_mode = int(not bool(common.active_mode))
    common.write_current_mode_to_lock()

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
def import_json_asset_properties():
    """Imports properties and applies them to the selected item.

    """
    from . import importexport

    model = common.model(common.AssetTab)
    indexes = [QtCore.QPersistentModelIndex(model.index(f, 0)) for f in range(model.rowCount())]
    importexport.import_json_asset_properties(indexes)


@common.debug
@common.error
@selection
def convert_image_sequence(index):
    """Convert the selected image sequence to a movie file.

    """
    from .external import ffmpeg_widget
    ffmpeg_widget.show(index)


def add_zip_template(source, mode, prompt=False):
    """Adds the selected source zip archive as a `mode` template file.

    Args:
        source (str): Path to a zip template file.
        mode (str): A template mode (one of  'job' or 'asset').
        prompt (bool): Prompt user to confirm overriding existing files.

    Returns:
        str: Path to the saved template file, or None.

    """
    common.check_type(source, str)
    common.check_type(mode, str)

    file_info = QtCore.QFileInfo(source)
    if not file_info.exists():
        raise RuntimeError('Source does not exist.')

    # Test the zip before saving it
    if not zipfile.is_zipfile(source):
        raise RuntimeError('Source is not a zip file.')

    with zipfile.ZipFile(source, compression=zipfile.ZIP_STORED) as f:
        corrupt = f.testzip()
        if corrupt:
            raise RuntimeError(f'The zip archive seems corrupt: {corrupt}')

    from . import templates
    root = templates.get_template_folder(mode)
    name = QtCore.QFileInfo(source).fileName()
    file_info = QtCore.QFileInfo(f'{root}/{name}')

    # Let's check if file exists before we copy anything...
    s = 'A template file with the same name exists already.'
    if file_info.exists() and not prompt:
        raise RuntimeError(s)

    if file_info.exists():
        from . import ui
        mbox = ui.MessageBox(
            s,
            'Do you want to overwrite the existing file?',
            buttons=[ui.YesButton, ui.CancelButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return None
        QtCore.QFile.remove(file_info.filePath())

    # If copied successfully, let's reload the
    if not QtCore.QFile.copy(source, file_info.filePath()):
        raise RuntimeError('An unknown error occurred adding the template.')

    common.signals.templatesChanged.emit()
    return file_info.filePath()


def extract_zip_template(source, destination, name):
    """Expands the selected source zip archive to `destination` as `name`.

    The contents will be expanded to a `{destination}/{name}` where name is an
    arbitrary name of a job or an asset item to be created.

    Args:
        source (str): Path to a zip archive.
        destination (str): Path to a folder
        name (str):
            Name of the root folder where the archive contents will be expanded to.

    Returns:
        str: Path to the expanded archive contents.

    """
    for arg in (source, destination, name):
        common.check_type(arg, str)
    if not destination:
        raise ValueError('Destination not set')

    if '/' in name:
        name = name.split('/')[-1]
        destination += '/' + '/'.join(name.split('/')[:-1])

    file_info = QtCore.QFileInfo(destination)
    if not file_info.exists():
        raise RuntimeError(f'{file_info.filePath()} does not exist.')
    if not file_info.isWritable():
        raise RuntimeError(f'{file_info.filePath()} not writable')

    if not name:
        raise ValueError('Must enter a name.')

    source_file_info = QtCore.QFileInfo(source)
    if not source_file_info.exists():
        raise RuntimeError(
            f'{source_file_info.filePath()} does not exist.'
        )

    dest_file_info = QtCore.QFileInfo(f'{destination}/{name}')
    if dest_file_info.exists():
        raise RuntimeError(
            f'{dest_file_info.fileName()} exists already.'
        )

    with zipfile.ZipFile(
            source_file_info.absoluteFilePath(), 'r', compression=zipfile.ZIP_STORED
    ) as f:
        corrupt = f.testzip()
        if corrupt:
            raise RuntimeError(f'The zip archive seems corrupt: {corrupt}')

        f.extractall(
            dest_file_info.absoluteFilePath(),
            members=None,
            pwd=None
        )

    common.signals.templateExpanded.emit(dest_file_info.filePath())
    return dest_file_info.filePath()


def remove_zip_template(source, prompt=True):
    """Deletes a zip template file from the disk.

    Args:
        source (str): Path to a zip template file.
        prompt (bool): Prompt the user for confirmation.

    """
    common.check_type(source, str)

    file_info = QtCore.QFileInfo(source)

    if not file_info.exists():
        raise RuntimeError('Template does not exist.')

    if prompt:
        from . import ui
        mbox = ui.MessageBox(
            'Are you sure you want to delete this template?',
            buttons=[ui.CancelButton, ui.YesButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

    if not QtCore.QFile.remove(source):
        raise RuntimeError('Could not delete the template archive.')

    common.signals.templatesChanged.emit()


@common.error
@common.debug
def pick_template(mode):
    """Prompts the user to pick a new `*.zip` file containing a template
    directory structure.

    The template is copied to ``%localappdata%/[product]/[mode]_templates/*.zip``
    folder.

    Args:
        mode (str): A template mode, e.g. `JobTemplateMode`.

    """
    common.check_type(mode, str)

    dialog = QtWidgets.QFileDialog(parent=None)
    dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    dialog.setViewMode(QtWidgets.QFileDialog.List)
    dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
    dialog.setNameFilters(['*.zip', ])
    dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
    dialog.setLabelText(
        QtWidgets.QFileDialog.Accept,
        'Select a {} template'.format(mode.title())
    )
    dialog.setWindowTitle(
        'Select *.zip archive to use as a {} template'.format(mode.lower())
    )
    if dialog.exec_() == QtWidgets.QDialog.Rejected:
        return
    source = next((f for f in dialog.selectedFiles()), None)
    if not source:
        return

    add_zip_template(source, mode)


def show_sg_error_message(v):
    """Shows a ShotGrid error message.

    """
    from . import ui
    common.sg_error_message = ui.ErrorBox(
        'An error occurred.',
        v
    ).open()


def show_sg_connecting_message():
    """Shows a ShotGrid connection progress message.

    """
    from . import ui
    common.sg_connecting_message = ui.MessageBox(
        'ShotGrid is connecting, please wait...', no_buttons=True
    )
    common.sg_connecting_message.open()
    QtWidgets.QApplication.instance().processEvents()


def hide_sg_connecting_message():
    """Hides a ShotGrid connection progress message.

    """
    try:
        common.sg_connecting_message.hide()
        QtWidgets.QApplication.instance().processEvents()
    except:
        pass


@common.debug
@common.error
@selection
def delete_selected_files(index):
    """Deletes the selected file items.

    """
    from . import ui
    from . import log
    mbox = ui.ErrorBox(
        'Are you sure you want to delete this file?',
        f'{index.data(QtCore.Qt.DisplayRole)} will be permanently lost.',
        buttons=[ui.YesButton, ui.NoButton]
    )
    if mbox.exec_() == QtWidgets.QDialog.Rejected:
        return

    model = index.model().sourceModel()
    f_data = common.get_data(model.source_path(), model.task(), common.FileItem)
    s_data = common.get_data(model.source_path(), model.task(), common.SequenceItem)

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
    rv.push(path, command=rv.DEFAULT)


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
    rv.push(path, command=rv.FULLSCREEN)
