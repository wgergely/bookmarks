# -*- coding: utf-8 -*-
"""A list of common actions.

"""
import re
import json
import zipfile
import os
import subprocess
import functools

from PySide2 import QtCore, QtWidgets, QtGui

from . import settings
from . import bookmark_db
from . import common
from . import images


def add_server(v):
    servers = tuple(common.SERVERS) + (v,)
    settings.instance().set_servers(servers)
    common.signals.serversChanged.emit()


def remove_server(v):
    servers = list(common.SERVERS)
    if v in servers:
        servers.remove(v)
    settings.instance().set_servers(servers)
    common.signals.serversChanged.emit()


def add_bookmark(server, job, root, persistent=False):
    """Save the given bookmark in `local_settings`.

    Each bookmark is stored as dictionary entry:

    ..code-block:: python

        {
            '//server/jobs/Job1234/data/shots': {
                {
                    settings.ServerKey: '//server/jobs',
                    settings.JobKey:  'Job1234',
                    settings.RootKey:  'data/shots'
                }
            },
        }

    Saved bookmarks can be retrieved using `settings.instance().get_bookmarks`

    Args:
        server (unicode): A path segment.
        job (unicode): A path segment.
        root (unicode): A path segment.
        persistent (unicode): Adds the bookmark to our persistent bookmark list. Not implemented.

    """
    for arg in (server, job, root):
        if not isinstance(arg, unicode):
            raise TypeError(
                'Invalid type, expected {}, got {}'.format(unicode, type(arg)))

    k = settings.bookmark_key(server, job, root)
    common.BOOKMARKS[k] = {
        settings.ServerKey: server,
        settings.JobKey: job,
        settings.RootKey: root
    }
    settings.instance().set_bookmarks(common.BOOKMARKS)
    common.signals.bookmarksChanged.emit()


def remove_bookmark(server, job, root, prompt=True):
    """Remove the given bookmark from the settings file.

    Removing the bookmark will also close and delete the bookmarks' database.

    Args:
        server (unicode): A path segment.
        job (unicode): A path segment.
        root (unicode): A path segment.

    """
    for arg in (server, job, root):
        if not isinstance(arg, unicode):
            raise TypeError(
                'Invalid type, expected {}, got {}'.format(unicode, type(arg)))

    if (
        settings.active(settings.ServerKey) == server and
        settings.active(settings.JobKey) == job and
        settings.active(settings.RootKey) == root
    ) and not prompt:
        return

    if (
        settings.active(settings.ServerKey) == server and
        settings.active(settings.JobKey) == job and
        settings.active(settings.RootKey) == root
    ) and prompt:
        from . import ui
        mbox = ui.MessageBox(
            u'Are you sure you want to remove the active bookmark?',
            buttons=[ui.OkButton, ui.CancelButton],
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

        set_active(settings.ServerKey, None)
        change_tab(common.BookmarkTab)

    # Close, and delete all cached bookmark databases of this bookmark
    bookmark_db.remove_db(server, job, root)

    k = settings.bookmark_key(server, job, root)
    if k not in common.BOOKMARKS:
        raise RuntimeError(u'Could not remove bookmark.',
                           u'Key does not seem to match any current bookmarks.')

    del common.BOOKMARKS[k]
    settings.instance().set_bookmarks(common.BOOKMARKS)
    common.signals.bookmarksChanged.emit()


def add_favourite(parent_paths, source):
    if not isinstance(parent_paths, (tuple, list)):
        raise TypeError('Invalid type, expected {}, got {}'.format(
            tuple, type(parent_paths)))
    if not isinstance(source, unicode):
        raise TypeError('Invalid type, expected {}, got {}'.format(
            unicode, type(source)))

    common.FAVOURITES[source] = parent_paths
    common.FAVOURITES_SET = set(common.FAVOURITES)
    settings.instance().set_favourites(common.FAVOURITES)
    common.signals.favouritesChanged.emit()


def remove_favourite(parent_paths, source):
    if not isinstance(parent_paths, (tuple, list)):
        raise TypeError('Invalid type, expected {}, got {}'.format(
            tuple, type(parent_paths)))
    if not isinstance(source, unicode):
        raise TypeError('Invalid type, expected {}, got {}'.format(
            unicode, type(source)))

    if source not in common.FAVOURITES:
        return

    del common.FAVOURITES[source]
    common.FAVOURITES_SET = set(common.FAVOURITES)
    settings.instance().set_favourites(common.FAVOURITES)
    common.signals.favouritesChanged.emit()


def clear_favourites(prompt=True):
    """Clear the list of saved items.

    """
    if prompt:
        from . import ui
        mbox = ui.MessageBox(
            u'Ar you sure you want to clear My Files?',
            buttons=[ui.YesButton, ui.NoButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

    common.FAVOURITES = {}
    common.FAVOURITES_SET = set()
    settings.instance().set_favourites(common.FAVOURITES)
    common.signals.favouritesChanged.emit()


def export_favourites(destination=None):
    """Saves all My File items as a zip archive.

    """
    if destination is None:
        destination, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption=u'Select where to save your favourites',
            filter=u'*.{}'.format(common.FAVOURITE_FILE_FORMAT),
            dir=QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.HomeLocation),
        )
        if not destination:
            return

    if not isinstance(destination, unicode):
        raise TypeError('Invalid type, expected {}, got {}'.format(
            unicode, type(destination)))

    data = common.FAVOURITES.copy()

    # Assamble the zip file
    with zipfile.ZipFile(destination, 'w') as _zip:

        # Add thumbnail to zip
        for source, parent_paths in common.FAVOURITES.iteritems():
            server, job, root = parent_paths[0:3]

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
            with bookmark_db.transactions(server, job, root) as db:
                if source == db.source():
                    table = bookmark_db.BookmarkTable
                else:
                    table = bookmark_db.AssetTable

                v = db.value(source, k, table=table)
                if v:
                    _zip.writestr(
                        file_info.baseName() + k,
                        bookmark_db.b64encode(v)
                    )

        # Let's Save the current list favourites to the zip
        v = json.dumps(
            data,
            ensure_ascii=True,
            encoding='utf-8'
        )
        _zip.writestr(common.FAVOURITE_FILE_FORMAT, v)

    return destination


def import_favourites(source=None):
    """Import a previously exported favourites file.

    Args:
        source (unicode): Path to a file. Defaults to `None`.

    """
    if source is None:
        source, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption=u'Select the favourites file to import',
            filter=u'*.{}'.format(common.FAVOURITE_FILE_FORMAT)
        )
        if not source:
            return

    with zipfile.ZipFile(source) as _zip:
        corrupt = _zip.testzip()
        if corrupt:
            raise RuntimeError(
                u'This zip archive seem corrupted: {}.'.format(corrupt))

        if common.FAVOURITE_FILE_FORMAT not in _zip.namelist():
            raise RuntimeError(u'Invalid file.')
        v = _zip.open(common.FAVOURITE_FILE_FORMAT).read()

        data = json.loads(v, 'utf-8')

        for _source, parent_paths in data.iteritems():
            server, job, root = parent_paths[0:3]

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
                    root = u'/'.join((server, job, root,
                                      common.BOOKMARK_ROOT_DIR))
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

            with bookmark_db.transactions(server, job, root) as db:
                if source == db.source():
                    table = bookmark_db.BookmarkTable
                else:
                    table = bookmark_db.AssetTable
                db.setValue(source, k, bookmark_db.b64decode(v), table=table)

    common.FAVOURITES = data
    common.FAVOURITES_SET = set(data)
    settings.instance().set_favourites(data)
    common.signals.favouritesChanged.emit()


def prune_bookmarks():
    """Removes all invalid bookmarks from the current list."""
    if not common.BOOKMARKS:
        return

    _valid = {}
    _invalid = []
    for k, v in common.BOOKMARKS.iteritems():
        if not QtCore.QFileInfo(k).exists():
            _invalid.append(k)
            continue
        _valid[k] = v

    # Nothing to do if all bookmarks are valid
    if common.BOOKMARKS == _valid:
        return

    # Otherwise save the valid bookmarks and signal the changes
    settings.instance().set_bookmarks(_valid)
    common.signals.bookmarksChanged.emit()


def set_active(k, v):
    """Sets the given path as the active path segment for the given key.

    Args:
        k (unicode): An active key, eg. `settings.ServerKey`.
        v (unicode): A path segment, eg. '//myserver/jobs'.

    """
    if k not in settings.ACTIVE_KEYS:
        raise ValueError('Invalid active key. Key must be the one of "{}"'.format(
            '", "'.join(settings.ACTIVE_KEYS)))
    settings.instance().setValue(settings.ActiveSection, k, v)
    settings.instance().verify_active()


@common.error
@common.debug
def toggle_sequence():
    if instance() is None:
        return
    idx = instance().stackedwidget.currentIndex()
    if idx not in (common.FileTab, common.FavouriteTab):
        return

    model = instance().widget().model().sourceModel()
    datatype = model.data_type()
    if datatype == common.FileItem:
        model.dataTypeChanged.emit(common.SequenceItem)
    else:
        model.dataTypeChanged.emit(common.FileItem)


@common.error
@common.debug
def toggle_archived_items():
    if instance() is None:
        return
    w = instance().widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsArchived)
    proxy.set_filter_flag(common.MarkedAsArchived, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsArchived, not val)


@common.error
@common.debug
def toggle_active_item():
    if instance() is None:
        return
    w = instance().widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsActive)
    proxy.set_filter_flag(common.MarkedAsActive, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsActive, not val)


@common.error
@common.debug
def toggle_favourite_items():
    if instance() is None:
        return
    w = instance().widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsFavourite)
    proxy.set_filter_flag(common.MarkedAsFavourite, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsFavourite, not val)


@common.error
@common.debug
def toggle_simple():
    if instance() is None:
        return
    if instance().stackedwidget.currentIndex() not in (common.FileTab, common.FavouriteTab):
        return

    widget = instance().widget()
    state = not widget.buttons_hidden()

    common.SORT_WITH_BASENAME = state
    widget.set_buttons_hidden(state)

    widget.model().sourceModel().sort_data()
    widget.reset()


@common.error
@common.debug
def toggle_make_thumbnails():
    if instance() is None:
        return
    widget = instance().widget()
    model = widget.model().sourceModel()
    state = not model.generate_thumbnails_enabled()
    model.set_generate_thumbnails_enabled(state)

    from .threads import threads
    for k in widget.queues:
        if threads.THREADS[k]['role'] != common.ThumbnailLoaded:
            continue
        widget.queue_visible_indexes(k)


@QtCore.Slot()
def toggle_task_view():
    if not instance():
        return
    if instance().stackedwidget.currentIndex() != common.FileTab:
        return
    instance().taskswidget.setHidden(not instance().taskswidget.isHidden())
    common.signals.taskViewToggled.emit()


def toggle_filter_editor():
    if instance() is None:
        return
    w = instance().widget()
    if w.filter_editor.isHidden():
        w.filter_editor.open()
    else:
        w.filter_editor.done(QtWidgets.QDialog.Rejected)


@QtCore.Slot(unicode)
@QtCore.Slot(unicode)
@QtCore.Slot(unicode)
@QtCore.Slot(object)
def asset_identifier_changed(table, source, key, value):
    """Refresh the assets model if the identifier changes.

    """
    if instance() is None:
        return
    # All shotgun fields should be prefix by 'shotgun_'
    if not (table == bookmark_db.BookmarkTable and key == 'identifier'):
        return
    widget = instance().stackedwidget.widget(common.AssetTab)
    widget.model().sourceModel().modelDataResetRequested.emit()


def selection(func):
    """Decorator function to ensure `QModelIndexes` passed to worker threads
    are in a valid state.

    """
    @functools.wraps(func)
    def func_wrapper():
        if instance() is None:
            return None
        index = instance().index()
        if not index.isValid():
            return None
        return func(index)
    return func_wrapper


def instance():
    from . import main
    try:
        return main.instance()
    except RuntimeError:
        return None
    except:
        raise


@common.error
@common.debug
def increase_row_size():
    if instance() is None:
        return
    widget = instance().widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.row_size().height() + common.psize(20)
    if v >= images.THUMBNAIL_IMAGE_SIZE:
        return

    widget.set_row_size(v)
    widget.reset_row_layout()


@common.error
@common.debug
def decrease_row_size():
    if instance() is None:
        return
    widget = instance().widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.row_size().height() - common.psize(20)
    if v <= model.default_row_size().height():
        v = model.default_row_size().height()

    widget.set_row_size(v)
    widget.reset_row_layout()


@common.error
@common.debug
def reset_row_size():
    if instance() is None:
        return
    widget = instance().widget()
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
        server = settings.active(settings.ServerKey)
        job = settings.active(settings.JobKey)
        root = settings.active(settings.RootKey)

    if not all((server, job, root)):
        return None

    from .properties import asset_properties_widget as editor
    widget = editor.show(server, job, root)
    return widget


@common.error
@common.debug
def show_add_file(asset=None, extension=None, file=None, create_file=True, increment=False):
    server = settings.active(settings.ServerKey)
    job = settings.active(settings.JobKey)
    root = settings.active(settings.RootKey)

    if asset is None:
        asset = settings.active(settings.AssetKey)

    args = (server, job, root, asset)
    if not all(args):
        return None

    from .properties import file_properties_widget as editor
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
        server = settings.active(settings.ServerKey)
        job = settings.active(settings.JobKey)
        root = settings.active(settings.RootKey)

    if not all((server, job, root)):
        return None

    from .properties import bookmark_properties_widget as editor
    widget = editor.show(server, job, root)

    widget.open()
    return widget


@common.error
@common.debug
def edit_asset(asset=None):
    server = settings.active(settings.ServerKey)
    job = settings.active(settings.JobKey)
    root = settings.active(settings.RootKey)

    if not all((server, job, root)):
        return None
    if asset is None:
        asset = settings.active(settings.AssetKey)
    if asset is None:
        return

    from .properties import asset_properties_widget as editor

    widget = editor.show(server, job, root, asset=asset)
    return widget


@common.error
@common.debug
def edit_file(f):
    server = settings.active(settings.ServerKey)
    job = settings.active(settings.JobKey)
    root = settings.active(settings.RootKey)
    asset = settings.active(settings.AssetKey)

    if not all((server, job, root, asset)):
        return

    from .properties import file_properties_widget as editor
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
def edit_favourite(f):
    raise NotImplementedError(u'Function not yet implemented.')


@common.error
@common.debug
def show_preferences():
    from .properties import preference_properties_widget as editor
    widget = editor.show()
    return widget


@common.error
@common.debug
def show_slack():
    """Opens the Slack widget used to send messages using SlackAPI.

    """
    server = settings.active(settings.ServerKey)
    job = settings.active(settings.JobKey)
    root = settings.active(settings.RootKey)

    args = (server, job, root)
    if not all(args):
        return

    with bookmark_db.transactions(*args) as db:
        token = db.value(
            db.source(),
            u'slacktoken',
            table=bookmark_db.BookmarkTable
        )
    if token is None:
        raise RuntimeError(u'Slack is not yet configured.')

    from . import slack
    widget = slack.show(token)
    return widget


@common.error
@common.debug
def quit():
    from .threads import threads
    common.quit()
    if common.STANDALONE:
        QtWidgets.QApplication.instance().quit()


@common.error
@common.debug
def add_item():
    idx = instance().stackedwidget.currentIndex()
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
    idx = instance().stackedwidget.currentIndex()
    if idx == common.BookmarkTab:
        server, job, root = index.data(common.ParentPathRole)[0:3]
        edit_bookmark(
            server=server,
            job=job,
            root=root,
        )
    elif idx == common.AssetTab:
        v = index.data(common.ParentPathRole)[-1]
        edit_asset(asset=v)
    elif idx == common.FileTab:
        v = index.data(QtCore.Qt.StatusTipRole)
        edit_file(v)
    elif idx == common.FavouriteTab:
        v = index.data(QtCore.Qt.StatusTipRole)
        edit_favourite(v)


@common.error
@common.debug
def refresh():
    w = instance().widget()
    model = w.model().sourceModel()
    model.modelDataResetRequested.emit()


@common.error
@common.debug
def toggle_flag(flag, v):
    proxy = instance().widget().model()
    proxy.set_filter_flag(flag, v)
    proxy.filterFlagChanged.emit(flag, v)


@common.error
@common.debug
def toggle_fullscreen():
    if instance().isFullScreen():
        instance().showNormal()
    else:
        instance().showFullScreen()


@common.error
@common.debug
def toggle_maximized():
    if instance().isMaximized():
        instance().showNormal()
    else:
        instance().showMaximized()


@common.error
@common.debug
def toggle_minimized():
    if instance().isMinimized():
        instance().showNormal()
    else:
        instance().showMinimized()


@common.error
@common.debug
def toggle_stays_on_top():
    if not common.STANDALONE:
        return

    from . import standalone

    w = standalone.instance()
    flags = w.windowFlags()
    state = flags & QtCore.Qt.WindowStaysOnTopHint

    settings.instance().setValue(
        settings.UIStateSection,
        settings.WindowAlwaysOnTopKey,
        not state
    )
    w.hide()
    w.init_window_flags()
    w.activateWindow()
    w.showNormal()


@common.error
@common.debug
def toggle_frameless():
    if not common.STANDALONE:
        return

    from . import standalone

    w = standalone.instance()
    flags = w.windowFlags()
    state = flags & QtCore.Qt.FramelessWindowHint

    settings.instance().setValue(
        settings.UIStateSection,
        settings.WindowFramelessKey,
        not state
    )

    w.hide()
    w.init_window_flags()
    w.update_layout()
    w.activateWindow()
    w.showNormal()


@common.error
@common.debug
def exec_instance():
    if common.get_platform() == common.PlatformWindows:
        if common.BOOKMARK_ROOT_KEY not in os.environ:
            s = u'Bookmarks does not seem to be installed correctly:\n'
            s += u'"{}" environment variable is not set'.format(
                common.BOOKMARK_ROOT_KEY)
            raise RuntimeError(s)
        p = os.environ[common.BOOKMARK_ROOT_KEY] + \
            os.path.sep + 'bookmarks.exe'
        subprocess.Popen(p)
    elif common.get_platform() == common.PlatformMacOS:
        raise NotImplementedError(u'Not yet implemented.')
    elif common.get_platform() == common.PlatformUnsupported:
        raise NotImplementedError(u'Not yet implemented.')


@common.error
@common.debug
def change_tab(idx):
    if not instance():
        return
    if instance().stackedwidget.currentIndex() == idx:
        return
    common.signals.tabChanged.emit(idx)


@common.error
@common.debug
def next_tab():
    n = instance().stackedwidget.currentIndex()
    n += 1
    if n > (instance().stackedwidget.count() - 1):
        common.signals.tabChanged.emit(common.BookmarkTab)
        return
    common.signals.tabChanged.emit(n)


@common.error
@common.debug
def previous_tab():
    n = instance().stackedwidget.currentIndex()
    n -= 1
    if n < 0:
        n = instance().stackedwidget.count() - 1
        common.signals.tabChanged.emit(n)
        return
    common.signals.tabChanged.emit(n)


@common.error
@common.debug
def change_sorting(role, order):
    model = instance().widget().model().sourceModel()
    model.sortingChanged.emit(role, order)


@common.error
@common.debug
def toggle_sort_order():
    model = instance().widget().model().sourceModel()
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
    parent = instance().widget()
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
    source = index.data(QtCore.Qt.StatusTipRole)
    source = common.get_sequence_startpath(source)

    if '.abc' in source.lower():
        from .editors import alembic_preview
        editor = alembic_preview.AlembicPreviewWidget(source)
        instance().widget().selectionModel().currentChanged.connect(editor.close)
        instance().widget().selectionModel().currentChanged.connect(editor.deleteLater)
        editor.show()
        return

    # Let's try to open the image outright
    # If this fails, we will try and look for a saved thumbnail image,
    # and if that fails too, we will display a general thumbnail.

    # Not a readable image file...
    if os.path.isfile(source) and images.oiio_get_buf(source):
        thumb_path = source
    else:
        server, job, root = index.data(common.ParentPathRole)[0:3]
        thumb_path = images.get_thumbnail(
            server,
            job,
            root,
            source,
            get_path=True
        )
        if not thumb_path:
            return

    # Finally, we'll create and show our widget, and destroy it when the
    # selection changes
    from .editors import item_preview
    editor = item_preview.ImageViewer(thumb_path, parent=instance().widget())
    instance().widget().selectionModel().currentChanged.connect(editor.delete_timer.start)
    editor.open()


@common.debug
@common.error
@selection
def reveal_selected(index):
    reveal(index)


@common.debug
@common.error
@selection
def reveal_url(index):
    parent_path = index.data(common.ParentPathRole)
    if len(parent_path) == 3:
        table = bookmark_db.BookmarkTable
    else:
        table = bookmark_db.AssetTable

    source = u'/'.join(index.data(common.ParentPathRole))
    with bookmark_db.transactions(*index.data(common.ParentPathRole)[0:3]) as db:
        v = db.value(source, 'url1', table=table)

    if not v:
        return

    QtGui.QDesktopServices.openUrl(QtCore.QUrl(v)),


@common.debug
@common.error
@selection
def toggle_favourite(index):
    instance().widget().save_selection()
    instance().widget().toggle_item_flag(index, common.MarkedAsFavourite)
    instance().widget().update(index)


@common.debug
@common.error
@selection
def toggle_archived(index):
    instance().widget().save_selection()
    instance().widget().toggle_item_flag(index, common.MarkedAsArchived)
    instance().widget().update(index)


@common.debug
@common.error
def reveal(item):
    """Reveals an item in the file explorer.

    Args:
        item(unicode or QModelIndex): The item to show in the file manager.

    """
    if isinstance(item, (QtCore.QModelIndex, QtWidgets.QListWidgetItem)):
        path = item.data(QtCore.Qt.StatusTipRole)
    elif isinstance(item, unicode):
        path = item

    path = common.get_sequence_endpath(path)
    if common.get_platform() == common.PlatformWindows:
        if QtCore.QFileInfo(path).isFile():
            args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        elif QtCore.QFileInfo(path).isDir():
            path = os.path.normpath(os.path.abspath(path))
            args = [path, ]
        else:
            args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        QtCore.QProcess.startDetached(u'explorer', args)

    elif common.get_platform() == common.PlatformMacOS:
        args = [
            u'-e',
            u'tell application "Finder"',
            u'-e',
            u'activate',
            u'-e',
            u'select POSIX file "{}"'.format(
                QtCore.QDir.toNativeSeparators(path)), u'-e', u'end tell']
        QtCore.QProcess.startDetached(u'osascript', args)
    elif common.get_platform() == common.PlatformUnsupported:
        raise NotImplementedError('{} is unsupported.'.format(
            QtCore.QSysInfo().productType()))


@common.debug
@common.error
def copy_path(path, mode=common.WindowsPath, first=True, copy=True):
    """Copy a file path to the clipboard.

    The path will be conformed to the given `mode` (eg. forward slashes
    converted to back-slashes for `WindowsPath`).

    Args:
        path (unicode): Description of parameter `path`.
        mode (int):     Any of `WindowsPath`, `UnixPath`, `SlackPath` or
                        `MacOSPath`. Defaults to `WindowsPath`.
        first (bool):   If `True` copy the first item of a sequence.
        copy (bool):    If copy is false the converted path won't be copied to
                        the clipboard. Defaults to `True`.

    Returns:
        unicode: The converted path.

    """
    if first:
        path = common.get_sequence_startpath(path)
    else:
        path = common.get_sequence_endpath(path)

    # Normalise path
    path = re.sub(ur'[\/\\]', ur'/', path,
                  flags=re.IGNORECASE | re.UNICODE).strip(u'/')

    if mode == common.WindowsPath:
        prefix = u'//' if u':' not in path else u''
    elif mode == common.UnixPath:
        prefix = u'//' if u':' not in path else u''
    elif mode == common.SlackPath:
        prefix = u'file://'
    elif mode == common.MacOSPath:
        prefix = u'smb://'
        path = path.replace(u':', u'')
    else:
        prefix = u''
    path = prefix + path
    if mode == common.WindowsPath:
        path = re.sub(ur'[\/\\]', ur'\\', path,
                      flags=re.IGNORECASE | re.UNICODE)

    if copy:
        QtGui.QClipboard().setText(path)
    return path


@common.debug
@common.error
def execute(index, first=False):
    """Given the model index, executes the index's path using
    `QDesktopServices`.

    """
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
    from . import slack
    client = slack.SlackClient(token)
    client.verify_token()


@common.debug
@common.error
def suggest_prefix(job):
    substrings = re.sub(ur'[\_\-\s]+', u';', job).split(u';')
    if (not substrings or len(substrings) < 2) and len(job) > 3:
        prefix = job[0:3].upper()
    else:
        prefix = u''.join([f[0] for f in substrings]).upper()
    return prefix


@common.debug
@common.error
@selection
def capture_thumbnail(index):
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(QtCore.Qt.StatusTipRole)

    from .editors import thumb_capture as editor
    widget = editor.show(
        server=server,
        job=job,
        root=root,
        source=source,
        proxy=False
    )

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

    from .editors import thumb_picker as editor
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

    from .editors import thumb_library as editor
    widget = editor.show(
        server=server,
        job=job,
        root=root,
        source=source
    )
    widget.thumbnailSelected.connect(widget.save_image)
    model = index.model().sourceModel()
    widget.thumbnailSelected.connect(lambda x: model.updateIndex.emit(index))


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
            raise RuntimeError(u'Could not remove the thumbnail')

    source_index = index.model().mapToSource(index)
    idx = source_index.row()

    data = source_index.model().model_data()[idx]
    data[common.ThumbnailLoaded] = False
    source_index.model().updateIndex.emit(source_index)


@common.error
@common.debug
def copy_properties():
    idx = instance().stackedwidget.currentIndex()
    if idx == common.BookmarkTab:
        copy_bookmark_properties()
    elif idx == common.AssetTab:
        copy_asset_properties()
    else:
        return


@common.error
@common.debug
def paste_properties():
    idx = instance().stackedwidget.currentIndex()
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
    bookmark_db.copy_properties(
        server,
        job,
        root,
        None,
        table=bookmark_db.BookmarkTable
    )


@common.error
@common.debug
@selection
def paste_bookmark_properties(index):
    server, job, root = index.data(common.ParentPathRole)[0:3]
    bookmark_db.paste_properties(
        server,
        job,
        root,
        None,
        table=bookmark_db.BookmarkTable
    )


@common.error
@common.debug
@selection
def copy_asset_properties(index):
    server, job, root, asset = index.data(common.ParentPathRole)[0:4]
    bookmark_db.copy_properties(
        server,
        job,
        root,
        asset,
        table=bookmark_db.AssetTable
    )


@common.error
@common.debug
@selection
def paste_asset_properties(index):
    server, job, root, asset = index.data(common.ParentPathRole)[0:4]
    bookmark_db.paste_properties(
        server,
        job,
        root,
        asset,
        table=bookmark_db.AssetTable
    )


@common.error
@common.debug
def toggle_session_mode():
    # Toggle the active mode
    if common.SESSION_MODE == common.SyncronisedActivePaths:
        common.SESSION_MODE = common.PrivateActivePaths
    elif common.SESSION_MODE == common.PrivateActivePaths:
        common.SESSION_MODE = common.SyncronisedActivePaths
    else:
        common.SESSION_MODE = common.PrivateActivePaths

    # Write new mode to the lock file
    from . import session_lock
    pid = os.getpid()
    session_lock.write_current_mode_to_lock(pid)

    # Load the values from the settings file
    settings.instance().verify_active()

    # Skip if the gui is not initialized
    if not instance():
        return

    widget = instance().stackedwidget.widget(common.BookmarkTab)
    widget.model().sourceModel().modelDataResetRequested.emit()
    # # The current bookmark has changed
    widget.model().sourceModel().modelDataResetRequested.emit()
    # The current asset has changed
    widget = instance().stackedwidget.widget(common.AssetTab)
    widget.model().sourceModel().modelDataResetRequested.emit()
    # The current task folder has changed
    widget = instance().stackedwidget.widget(common.FileTab)
    widget.model().sourceModel().modelDataResetRequested.emit()

    widget.model().sourceModel().taskFolderChanged.emit(
        settings.active(settings.TaskKey))

    common.signals.sessionModeChanged.emit(common.SESSION_MODE)
