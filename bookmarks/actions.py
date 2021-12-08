# -*- coding: utf-8 -*-
"""Actions modules.

A list common actions used across `Bookmarks`.

"""
import functools
import json
import os
import re
import subprocess
import weakref
import zipfile

from PySide2 import QtCore, QtWidgets, QtGui

from . import common
from . import database
from . import images


def edit_persistent_bookmarks():
    """Opens `common.static_bookmarks_template`.

    """
    execute(common.get_rsc(
        f'{common.TemplateResource}/{common.static_bookmarks_template}'))


def add_server(v):
    """Add an item to the list of user specified servers.

    Args:
        v (str): A path to server, e.g. `Q:/jobs`.

    """
    # Disallow adding persistent servers
    for bookmark in common.static_bookmarks.values():
        if bookmark[common.ServerKey] == v:
            return

    common.servers[v] = v
    common.settings.set_servers(common.servers)
    common.signals.serversChanged.emit()


def remove_server(v):
    """Remove an item from the list of user specified servers.

    Args:
        v (str): A path to server, e.g. `Q:/jobs`.

    """
    # Disallow removing persistent servers
    for bookmark in common.static_bookmarks.values():
        if bookmark[common.ServerKey] == v:
            return

    if v in common.servers:
        del common.servers[v]

    common.settings.set_servers(common.servers)
    common.signals.serversChanged.emit()


def add_bookmark(server, job, root):
    """Save the given bookmark in `user_settings`.

    Each bookmark is stored as dictionary entry:

    ..code-block:: python

        bookmarks = {
            '//server/jobs/MyFirstJob/data/shots': {
                {
                    common.ServerKey: '//server/jobs',
                    common.JobKey:  'MyFirstJob',
                    common.RootKey:  'data/shots'
                }
            },
            '//server/jobs/MySecondJob/data/shots': {
                {
                    common.ServerKey: '//server/jobs',
                    common.JobKey:  'MySecondJob',
                    common.RootKey:  'data/shots'
                }
            }
        }

    Saved bookmarks can be retrieved using `common.settings.get_bookmarks`

    Args:
        server (str): A path segment.
        job (str): A path segment.
        root (str): A path segment.

    """
    for arg in (server, job, root):
        common.check_type(arg, str)

    k = common.bookmark_key(server, job, root)
    common.bookmarks[k] = {
        common.ServerKey: server,
        common.JobKey: job,
        common.RootKey: root
    }
    common.settings.set_bookmarks(common.bookmarks)
    common.signals.bookmarkAdded.emit(server, job, root)


def remove_bookmark(server, job, root):
    """Remove the given bookmark from the settings file.

    Removing the bookmark will also close and delete the bookmarks' database.

    Args:
        server (str): A path segment.
        job (str): A path segment.
        root (str): A path segment.

    """
    for arg in (server, job, root):
        common.check_type(arg, str)

    # If the active bookmark is removed, make sure we're clearing the active
    # bookmark. This will cause all models to reset so show the bookmark tab.
    if (
            common.active(common.ServerKey) == server and
            common.active(common.JobKey) == job and
            common.active(common.RootKey) == root
    ):
        set_active(common.ServerKey, None)
        change_tab(common.BookmarkTab)

    # Close, and delete all cached bookmark databases of this bookmark
    database.remove_db(server, job, root)

    k = common.bookmark_key(server, job, root)
    if k not in common.bookmarks:
        raise RuntimeError(
            'Key does not seem to match any current bookmarks.')

    del common.bookmarks[k]
    common.settings.set_bookmarks(common.bookmarks)
    common.signals.bookmarkRemoved.emit(server, job, root)


def add_favourite(source_paths, source):
    common.check_type(source_paths, (tuple, list))
    common.check_type(source, str)

    common.favourites[source] = source_paths
    common.settings.set_favourites(common.favourites)
    common.signals.favouritesChanged.emit()


def remove_favourite(source_paths, source):
    common.check_type(source_paths, (tuple, list))
    common.check_type(source, str)

    if source not in common.favourites:
        return

    del common.favourites[source]
    common.settings.set_favourites(common.favourites)
    common.signals.favouritesChanged.emit()


def clear_favourites(prompt=True):
    """Clear the list of saved items.

    """
    if prompt:
        from . import ui
        mbox = ui.MessageBox(
            'Ar you sure you want to remove all starred items?',
            buttons=[ui.YesButton, ui.NoButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

    common.favourites = {}
    common.settings.set_favourites(common.favourites)
    common.signals.favouritesChanged.emit()


def export_favourites(*args, destination=None):
    """Saves all My File items as a zip archive.

    """
    common.check_type(destination, (None, str))

    if destination is None:
        destination, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption='Select where to save your favourites',
            filter='*.{}'.format(common.favorite_file_ext),
            dir=QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.HomeLocation),
        )
        if not destination:
            return

    data = common.favourites.copy()

    # Assemble the zip file
    with zipfile.ZipFile(destination, 'w') as _zip:

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


def import_favourites(*args, source=None):
    """Import a previously exported favourites file.

    Args:
        source (str): Path to a file. Defaults to `None`.

    """
    common.check_type(source, (None, str))
    if source is None:
        source, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption='Select the favourites file to import',
            filter='*.{}'.format(common.favorite_file_ext)
        )
        if not source:
            return

    with zipfile.ZipFile(source) as _zip:
        corrupt = _zip.testzip()
        if corrupt:
            raise RuntimeError(
                'This zip archive seem corrupted: {}.'.format(corrupt))

        if common.favorite_file_ext not in _zip.namelist():
            raise RuntimeError('Invalid file.')

        with _zip.open(common.favorite_file_ext) as _f:
            v = _f.read()

        data = json.loads(v)

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
                    root = '/'.join((server, job, root,
                                     common.bookmark_cache_dir))
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
            with db.connection():
                db.setValue(source, k, database.b64decode(v), table=table)

    common.favourites = data
    common.settings.set_favourites(data)
    common.signals.favouritesChanged.emit()


def prune_bookmarks():
    """Removes invalid bookmark items from the current set.

    """
    if not common.bookmarks:
        return

    for k, v in common.bookmarks.items():
        if not QtCore.QFileInfo(k).exists():
            remove_bookmark(
                v[common.ServerKey],
                v[common.JobKey],
                v[common.RootKey]
            )


def set_active(k, v):
    """Sets the given path as the active path segment for the given key.

    Args:
        k (str): An active key, e.g. `common.ServerKey`.
        v (str or None): A path segment, e.g. '//myserver/jobs'.

    """
    common.check_type(k, str)
    common.check_type(k, (str, None))

    if k not in common.ActiveSectionCacheKeys:
        raise ValueError('Invalid active key. Key must be the one of "{}"'.format(
            '", "'.join(common.ActiveSectionCacheKeys)))

    common.active_paths[common.active_mode][k] = v
    if common.active_mode == common.SynchronisedActivePaths:
        common.settings.setValue(common.ActiveSection, k, v)


@common.error
@common.debug
def set_task_folder(v):
    set_active(common.TaskKey, v)
    common.source_model(common.FileTab).reset_data()
    common.widget(common.FileTab).model().invalidateFilter()


@common.error
@common.debug
def toggle_sequence():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
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
def toggle_archived_items():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    w = common.widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsArchived)
    proxy.set_filter_flag(common.MarkedAsArchived, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsArchived, not val)


@common.error
@common.debug
def toggle_active_item():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    w = common.widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsActive)
    proxy.set_filter_flag(common.MarkedAsActive, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsActive, not val)


@common.error
@common.debug
def toggle_favourite_items():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    w = common.widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsFavourite)
    proxy.set_filter_flag(common.MarkedAsFavourite, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsFavourite, not val)


@common.error
@common.debug
def toggle_inline_icons():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return

    widget = common.widget()
    state = not widget.buttons_hidden()

    common.sort_by_basename = state
    widget.set_buttons_hidden(state)

    widget.model().sourceModel().sort_data()


@common.error
@common.debug
@QtCore.Slot()
def generate_thumbnails_changed(state):
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    if state == QtCore.Qt.Checked:
        return

    from . threads import threads

    for t in (common.FileTab, common.FavouriteTab):
        w = common.widget(t)
        for k in w.queues:
            if state == QtCore.Qt.Checked:
                threads.THREADS[k]['queue'].clear()
            elif state == QtCore.Qt.Unchecked:
                if threads.THREADS[k]['role'] == common.ThumbnailLoaded:
                    w.queue_visible_indexes(k)


@QtCore.Slot()
def toggle_task_view():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    if common.current_tab() != common.FileTab:
        return
    common.widget(common.TaskTab).setHidden(
        not common.widget(common.TaskTab).isHidden())
    common.signals.taskViewToggled.emit()


def toggle_filter_editor():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    w = common.widget()
    if w.filter_editor.isHidden():
        w.filter_editor.open()
    else:
        w.filter_editor.done(QtWidgets.QDialog.Rejected)


@QtCore.Slot(str)
@QtCore.Slot(str)
@QtCore.Slot(str)
@QtCore.Slot(object)
def asset_identifier_changed(table, source, key, value):
    """Refresh the assets model if the identifier changes.

    """
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
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
    def func_wrapper():
        if common.main_widget is None or not common.main_widget.is_initialized:
            return None
        index = common.selected_index()
        if not index.isValid():
            return None
        return func(index)

    return func_wrapper


@common.error
@common.debug
def increase_row_size():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    widget = common.widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.row_size().height() + common.size(common.thumbnail_size / 15)
    if v >= common.thumbnail_size:
        return

    widget.set_row_size(v)
    widget.reset_row_layout()


@common.error
@common.debug
def decrease_row_size():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    widget = common.widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.row_size().height() - common.size(common.thumbnail_size / 15)
    if v <= model.default_row_size().height():
        v = model.default_row_size().height()

    widget.set_row_size(v)
    widget.reset_row_layout()


@common.error
@common.debug
def reset_row_size():
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    widget = common.widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.default_row_size().height()

    widget.set_row_size(v)
    widget.reset_row_layout()


@common.error
@common.debug
def show_add_bookmark():
    from .bookmark_editor import bookmark_editor_widget as editor
    widget = editor.show()
    return widget


@common.error
@common.debug
def show_add_asset(server=None, job=None, root=None):
    if not all((server, job, root)):
        server = common.active(common.ServerKey)
        job = common.active(common.JobKey)
        root = common.active(common.RootKey)

    if not all((server, job, root)):
        return None

    from .property_editor import asset_editor as editor
    widget = editor.show(server, job, root)
    return widget


@common.error
@common.debug
def show_add_file(asset=None, extension=None, file=None, create_file=True, increment=False):
    server = common.active(common.ServerKey)
    job = common.active(common.JobKey)
    root = common.active(common.RootKey)

    if asset is None:
        asset = common.active(common.AssetKey)

    args = (server, job, root, asset)
    if not all(args):
        return None

    from .property_editor import file_editor as editor
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
def show_add_favourite():
    raise NotImplementedError('Function not yet implemented')


@common.error
@common.debug
def edit_bookmark(server=None, job=None, root=None):
    if not all((server, job, root)):
        server = common.active(common.ServerKey)
        job = common.active(common.JobKey)
        root = common.active(common.RootKey)

    if not all((server, job, root)):
        return None

    from .property_editor import bookmark_editor as editor
    widget = editor.show(server, job, root)

    widget.open()
    return widget


@common.error
@common.debug
def edit_asset(asset=None):
    server = common.active(common.ServerKey)
    job = common.active(common.JobKey)
    root = common.active(common.RootKey)

    if not all((server, job, root)):
        return None
    if asset is None:
        asset = common.active(common.AssetKey)
    if asset is None:
        return

    from .property_editor import asset_editor as editor

    widget = editor.show(server, job, root, asset=asset)
    return widget


@common.error
@common.debug
def edit_file(f):
    server = common.active(common.ServerKey)
    job = common.active(common.JobKey)
    root = common.active(common.RootKey)
    asset = common.active(common.AssetKey)

    if not all((server, job, root, asset)):
        return

    from .property_editor import file_editor as editor
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
    from .property_editor import preference_editor as editor
    widget = editor.show()
    return widget


@common.error
@common.debug
def show_slack():
    """Opens the Slack widget used to send messages using SlackAPI.

    """
    server = common.active(common.ServerKey)
    job = common.active(common.JobKey)
    root = common.active(common.RootKey)

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
    idx = common.current_tab()
    if idx == common.BookmarkTab:
        show_add_bookmark()
    elif idx == common.AssetTab:
        show_add_asset()
    elif idx == common.FileTab:
        show_add_file()
    elif idx == common.FavouriteTab:
        show_add_favourite()


@common.error
@common.debug
@selection
def edit_item(index):
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
        v = index.data(QtCore.Qt.StatusTipRole)
        edit_file(v)


@common.error
@common.debug
def refresh(idx=None):
    w = common.widget(idx=idx)
    model = w.model().sourceModel()
    model.reset_data(force=True)


@common.error
@common.debug
def toggle_flag(flag, v):
    proxy = common.widget().model()
    proxy.set_filter_flag(flag, v)
    proxy.filterFlagChanged.emit(flag, v)


@common.error
@common.debug
def toggle_fullscreen():
    if common.main_widget.isFullScreen():
        common.main_widget.showNormal()
    else:
        common.main_widget.showFullScreen()


@common.error
@common.debug
def toggle_maximized():
    if common.main_widget.isMaximized():
        common.main_widget.showNormal()
    else:
        common.main_widget.showMaximized()


@common.error
@common.debug
def toggle_minimized():
    if common.main_widget.isMinimized():
        common.main_widget.showNormal()
    else:
        common.main_widget.showMinimized()


@common.error
@common.debug
def toggle_stays_on_top():
    if common.init_mode == common.EmbeddedMode:
        return

    w = common.main_widget
    flags = w.windowFlags()
    state = flags & QtCore.Qt.WindowStaysOnTopHint

    common.settings.setValue(
        common.UIStateSection,
        common.WindowAlwaysOnTopKey,
        not state
    )
    w.hide()
    w.update_window_flags()
    w.activateWindow()
    w.showNormal()


@common.error
@common.debug
def toggle_frameless():
    if common.init_mode == common.EmbeddedMode:
        return

    w = common.main_widget
    flags = w.windowFlags()
    state = flags & QtCore.Qt.FramelessWindowHint

    common.settings.setValue(
        common.UIStateSection,
        common.WindowFramelessKey,
        not state
    )

    w.hide()
    w.update_window_flags()
    w.activateWindow()
    w.showNormal()


@common.error
@common.debug
def exec_instance():
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
def change_tab(idx):
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    if common.current_tab() == idx:
        return
    common.signals.tabChanged.emit(idx)


@common.error
@common.debug
def next_tab():
    n = common.current_tab()
    n += 1
    if n > (common.main_widget.stacked_widget.count() - 1):
        common.signals.tabChanged.emit(common.BookmarkTab)
        return
    common.signals.tabChanged.emit(n)


@common.error
@common.debug
def previous_tab():
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
    model = common.widget().model().sourceModel()
    model.sortingChanged.emit(role, order)


@common.error
@common.debug
def toggle_sort_order():
    model = common.widget().model().sourceModel()
    order = model.sort_order()
    role = model.sort_role()
    model.sortingChanged.emit(role, not order)


@common.error
@common.debug
@selection
def copy_selected_path(index):
    if not index.data(common.FileInfoLoaded):
        return
    if common.get_platform() == common.PlatformMacOS:
        mode = common.MacOSPath
    elif common.get_platform() == common.PlatformWindows:
        mode = common.WindowsPath
    else:
        mode = common.UnixPath
    copy_path(
        index.data(QtCore.Qt.StatusTipRole),
        mode=mode,
        first=False
    )


@common.error
@common.debug
@selection
def copy_selected_alt_path(index):
    if not index.data(common.FileInfoLoaded):
        return
    copy_path(
        index.data(QtCore.Qt.StatusTipRole),
        mode=common.UnixPath,
        first=True
    )


@common.debug
@common.error
@selection
def show_todos(index):
    from . import notes
    parent = common.widget()
    editors = [f for f in parent.children() if isinstance(
        f, notes.TodoEditorWidget)]
    if editors:
        for editor in editors:
            editor.done(QtWidgets.QDialog.Rejected)

    source_index = parent.model().mapToSource(index)

    editor = notes.TodoEditorWidget(source_index, parent=parent)
    parent.resized.connect(editor.setGeometry)
    editor.finished.connect(editor.deleteLater)
    editor.open()


@common.debug
@common.error
@selection
def preview(index):
    """Displays a preview of the currently selected item.

    For alembic archives, this is the hierarchy of the archive file. For
    image files we'll try to load and display the image itself, and
    for any other case we will fall back to cached or default thumbnail
    images.

    """
    if not index.isValid():
        return

    source = index.data(QtCore.Qt.StatusTipRole)
    source = common.get_sequence_startpath(source)

    if '.abc' in source.lower():
        from .lists.widgets import alembic_widget
        editor = alembic_widget.AlembicPreviewWidget(source)
        common.widget().selectionModel().currentChanged.connect(editor.close)
        common.widget().selectionModel().currentChanged.connect(editor.deleteLater)
        editor.show()
        return

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
    model = index.model()
    data = model.sourceModel().model_data()
    idx = model.mapToSource(index).row()
    ref = weakref.ref(data[idx])

    from .lists.widgets import image_viewer
    image_viewer.show(source, ref, common.widget())


@common.debug
@common.error
@selection
def reveal_selected(index):
    reveal(index)


@common.debug
@common.error
@selection
def reveal_url(index):
    source_path = index.data(common.ParentPathRole)
    if len(source_path) == 3:
        table = database.BookmarkTable
    else:
        table = database.AssetTable

    source = '/'.join(source_path)
    db = database.get_db(*source_path[0:3])
    v = db.value(source, 'url1', table)

    if not v:
        return

    QtGui.QDesktopServices.openUrl(QtCore.QUrl(v)),


@common.debug
@common.error
@selection
def toggle_favourite(index):
    common.widget().save_selection()
    common.widget().toggle_item_flag(index, common.MarkedAsFavourite)
    common.widget().update(index)


@common.debug
@common.error
@selection
def toggle_archived(index):
    # Ignore persistent items
    if index.data(common.FlagsRole) & common.MarkedAsPersistent:
        from . import ui
        ui.MessageBox('Persistent items cannot be archived.').open()
        return

    common.widget().save_selection()
    common.widget().toggle_item_flag(index, common.MarkedAsArchived)
    common.widget().update(index)
    common.widget().model().invalidateFilter()


@QtCore.Slot(str)
@common.debug
@common.error
def show_asset(path):
    index = common.active_index(common.BookmarkTab)
    if not index or not index.isValid():
        return

    # Check if the added asset has been added to the currently active bookmark
    if index.data(QtCore.Qt.StatusTipRole) not in path:
        return

    # Change tabs otherwise
    common.signals.tabChanged.emit(common.AssetTab)

    widget = common.widget(common.AssetTab)
    widget.show_item(path, role=QtCore.Qt.StatusTipRole)


@common.debug
@common.error
def reveal(item):
    """Reveals an item in the file explorer.

    Args:
        item(str or QModelIndex): The item to show in the file manager.

    """
    if isinstance(item, (QtCore.QModelIndex, QtWidgets.QListWidgetItem)):
        path = item.data(QtCore.Qt.StatusTipRole)
    elif isinstance(item, str):
        path = item
    else:
        return

    path = common.get_sequence_endpath(path)
    if common.get_platform() == common.PlatformWindows:
        if QtCore.QFileInfo(path).isFile():
            args = ['/select,', QtCore.QDir.toNativeSeparators(path)]
        elif QtCore.QFileInfo(path).isDir():
            path = os.path.normpath(path)
            args = [path, ]
        else:
            args = ['/select,', QtCore.QDir.toNativeSeparators(path)]
        QtCore.QProcess.startDetached('explorer', args)

    elif common.get_platform() == common.PlatformMacOS:
        args = [
            '-e',
            'tell application "Finder"',
            '-e',
            'activate',
            '-e',
            'select POSIX file "{}"'.format(
                QtCore.QDir.toNativeSeparators(path)), '-e', 'end tell']
        QtCore.QProcess.startDetached('osascript', args)
    elif common.get_platform() == common.PlatformUnsupported:
        raise NotImplementedError('{} is unsupported.'.format(
            QtCore.QSysInfo().productType()))


@common.debug
@common.error
def copy_path(path, mode=common.WindowsPath, first=True, copy=True):
    """Copy a file path to the clipboard.

    The path will be conformed to the given `mode` (e.g. forward slashes
    converted to back-slashes for `WindowsPath`).

    Args:
        path (str): Description of parameter `path`.
        mode (int):     Any of `WindowsPath`, `UnixPath`, `SlackPath` or
                        `MacOSPath`. Defaults to `WindowsPath`.
        first (bool):   If `True` copy the first item of a sequence.
        copy (bool):    If copy is false the converted path won't be copied to
                        the clipboard. Defaults to `True`.

    Returns:
        str: The converted path.

    """
    if first:
        path = common.get_sequence_startpath(path)
    else:
        path = common.get_sequence_endpath(path)

    if mode is None and copy:
        QtGui.QClipboard().setText(path)
        return path
    elif mode is None and not copy:
        return path

    # Normalise path
    path = re.sub(
        r'[\/\\]',
        r'/',
        path,
        flags=re.IGNORECASE | re.UNICODE
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
            flags=re.IGNORECASE | re.UNICODE
        )

    if copy:
        QtGui.QClipboard().setText(path)
    return path


@common.debug
@common.error
def execute(index, first=False):
    """Given the model index, executes the index's path using
    `QDesktopServices`.

    Args:
        index (QModelIndex or str): A list item index or a path to a file.

    """
    common.check_type(index, (QtCore.QModelIndex, str))

    if isinstance(index, str):
        url = QtCore.QUrl.fromLocalFile(index)
        QtGui.QDesktopServices.openUrl(url)
        return

    if not index.isValid():
        return
    path = index.data(QtCore.Qt.StatusTipRole)
    if first:
        path = common.get_sequence_startpath(path)
    else:
        path = common.get_sequence_endpath(path)

    url = QtCore.QUrl.fromLocalFile(path)
    QtGui.QDesktopServices.openUrl(url)


@common.debug
@common.error
def test_slack_token(token):
    from .slack import slack
    client = slack.SlackClient(token)
    client.verify_token()


@common.debug
@common.error
def suggest_prefix(job):
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
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(QtCore.Qt.StatusTipRole)

    if common.init_mode == common.StandaloneMode:
        common.main_widget.hide()
        common.main_widget.save_window()

    from .lists.widgets import thumb_capture as editor
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
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(QtCore.Qt.StatusTipRole)

    from .lists.widgets import thumb_picker as editor
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
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(QtCore.Qt.StatusTipRole)

    if not all((server, job, root, source)):
        return

    from .lists.widgets import thumb_library as editor
    widget = editor.show()

    widget.itemSelected.connect(
        lambda v: images.load_thumbnail_from_image(server, job, root, source, v))
    widget.itemSelected.connect(
        lambda _: index.model().sourceModel().updateIndex.emit(index))


@common.debug
@common.error
def pick_launcher_item():
    from .launcher import launcher_gallery as editor
    widget = editor.show()
    widget.itemSelected.connect(lambda v: execute(v))



@common.debug
@common.error
@selection
def remove_thumbnail(index):
    """Deletes a thumbnail file and the cached entries associated
    with it.

    """
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(QtCore.Qt.StatusTipRole)

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
def copy_properties():
    idx = common.current_tab()
    if idx == common.BookmarkTab:
        copy_bookmark_properties()
    elif idx == common.AssetTab:
        copy_asset_properties()
    else:
        return


@common.error
@common.debug
def paste_properties():
    idx = common.current_tab()
    if idx == common.BookmarkTab:
        paste_bookmark_properties()
    elif idx == common.AssetTab:
        paste_asset_properties()
    else:
        return


@common.error
@common.debug
@selection
def copy_bookmark_properties(index):
    server, job, root = index.data(common.ParentPathRole)[0:3]
    database.copy_properties(
        server,
        job,
        root,
        None,
        table=database.BookmarkTable
    )


@common.error
@common.debug
@selection
def paste_bookmark_properties(index):
    server, job, root = index.data(common.ParentPathRole)[0:3]
    database.paste_properties(
        server,
        job,
        root,
        None,
        table=database.BookmarkTable
    )


@common.error
@common.debug
@selection
def copy_asset_properties(index):
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
    if common.main_widget is None or not common.main_widget.is_initialized:
        return
    # Toggle the active mode
    common.active_mode = int(not bool(common.active_mode))
    common.write_current_mode_to_lock()
    common.signals.activeModeChanged.emit(common.active_mode)
    common.source_model(common.BookmarkTab).reset_data(force=True)


@common.error
@common.debug
def import_asset_properties_from_json():
    source, _ = QtWidgets.QFileDialog.getOpenFileName(
        caption='Select *.json file to import properties from',
        filter='*.json'
    )
    if not source:
        return

    # Load config values from JSON
    with open(source, 'r', encoding='utf8') as f:
        v = f.read()
    import_data = json.loads(v)

    # Progress bar
    from . import ui
    mbox = ui.MessageBox('Applying properties...', no_buttons=True)
    mbox.open()

    try:
        w = common.widget(common.AssetTab)
        proxy = w.model()
        model = w.model().sourceModel()
        data = model.model_data()

        for k in import_data:
            # Progress update
            mbox_title = f'Applying properties ({k})...'
            mbox.set_labels(mbox_title)
            QtWidgets.QApplication.instance().processEvents()

            # Iterate over visible items
            for proxy_idx in range(proxy.rowCount()):
                index = proxy.index(proxy_idx, 0)
                source_index = proxy.mapToSource(index)
                idx = source_index.row()

                # Check for any partial matches and omit items if not found
                if k.lower() not in data[idx][QtCore.Qt.StatusTipRole].lower():
                    continue
                if not data[idx][common.ParentPathRole]:
                    continue

                # Update progress bar
                mbox.set_labels((mbox_title, data[idx][QtCore.Qt.DisplayRole]))
                QtWidgets.QApplication.instance().processEvents()

                server, job, root = data[idx][common.ParentPathRole][0:3]
                if not all((server, job, root)):
                    continue

                db = database.get_db(server, job, root)
                with db.connection():
                    # Iterate over all our implemented asset keys and check if
                    # we have any data to import
                    for key in database.TABLES[database.AssetTable]:
                        if key not in import_data[k]:
                            continue

                        db.setValue(
                            data[idx][QtCore.Qt.StatusTipRole],
                            key,
                            import_data[k][key],
                            table=database.AssetTable,
                        )
    except:
        raise
    finally:
        mbox.close()


@common.debug
@common.error
@selection
def convert_image_sequence(index):
    from .external import ffmpeg_widget
    ffmpeg_widget.show(index.data(QtCore.Qt.StatusTipRole))


def add_zip_template(source, mode, prompt=False):
    """Adds the selected source zip archive as a `mode` template file.

    Args:
        source (str): Path to a source file.
        mode (str): A template mode, e.g. 'job' or 'asset'

    Returns:
        str: Path to the saved template file, or `None`.

    """
    common.check_type(source, str)
    common.check_type(mode, str)

    file_info = QtCore.QFileInfo(source)
    if not file_info.exists():
        raise RuntimeError('Source does not exist.')

    # Test the zip before saving it
    if not zipfile.is_zipfile(source):
        raise RuntimeError('Source is not a zip file.')

    with zipfile.ZipFile(source) as f:
        corrupt = f.testzip()
        if corrupt:
            raise RuntimeError(
                'The zip archive seems corrupted: {}'.format(corrupt))

    from . import templates
    root = templates.get_template_folder(mode)
    name = QtCore.QFileInfo(source).fileName()
    file_info = QtCore.QFileInfo('{}/{}'.format(root, name))

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
    arbitary name of a job or an asset item to be created.

    Args:
        source (str):           Path to a *.zip archive.
        destination (str):      Path to a folder
        name (str):             Name of the root folder where the archive
                                    contents will be expanded to.

    Returns:
        str:                    Path to the expanded archive contents.

    """
    for arg in (source, destination, name):
        common.check_type(arg, str)

    if not destination:
        raise ValueError('Destination not set')

    file_info = QtCore.QFileInfo(destination)
    if not file_info.exists():
        raise RuntimeError(
            'Destination {} does not exist.'.format(file_info.filePath()))
    if not file_info.isWritable():
        raise RuntimeError(
            'Destination {} not writable'.format(file_info.filePath()))
    if not name:
        raise ValueError('Must enter a name.')

    source_file_info = file_info = QtCore.QFileInfo(source)
    if not source_file_info.exists():
        raise RuntimeError('{} does not exist.'.format(
            source_file_info.filePath()))

    dest_file_info = QtCore.QFileInfo('{}/{}'.format(destination, name))
    if dest_file_info.exists():
        raise RuntimeError('{} exists already.'.format(
            dest_file_info.fileName()))

    with zipfile.ZipFile(source_file_info.absoluteFilePath(), 'r', zipfile.ZIP_DEFLATED) as f:
        corrupt = f.testzip()
        if corrupt:
            raise RuntimeError(
                'This zip archive seems to be corrupt: {}'.format(corrupt))

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
    from . import ui
    common.sg_error_message = ui.ErrorBox(
        'An error occured.',
        v
    ).open()


def show_sg_connecting_message():
    from . import ui
    common.sg_connecting_message = ui.MessageBox(
        'Shotgun is connecting, please wait...', no_buttons=True)
    common.sg_connecting_message.open()
    QtWidgets.QApplication.instance().processEvents()


def hide_sg_connecting_message():
    try:
        common.sg_connecting_message.hide()
        QtWidgets.QApplication.instance().processEvents()
    except:
        pass
