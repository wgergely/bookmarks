"""The widgets needed by the jobs editor.

"""
import functools
import json
import os

from PySide2 import QtCore, QtGui, QtWidgets

from . import base
from .. import actions
from .. import common
from .. import contextmenu
from .. import images
from .. import shortcuts
from .. import templates
from .. import ui

cache = common.DataDict()


class ScanDepthComboBox(QtWidgets.QComboBox):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        self.blockSignals(True)
        for k in range(1, 5):
            self.addItem(str(f'{k}'), userData=k)
        self.blockSignals(False)


class AddServerDialog(QtWidgets.QDialog):
    """Dialog used to add a new server to user settings file.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.ok_button = None
        self.pick_button = None
        self.editor = None

        self.setWindowTitle('Add new server')

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint
        )

        # Shadow effect
        self.effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.effect.setBlurRadius(common.Size.Margin(2.0))
        self.effect.setXOffset(0)
        self.effect.setYOffset(0)
        self.effect.setColor(QtGui.QColor(0, 0, 0, 200))
        self.setGraphicsEffect(self.effect)

        self._create_ui()
        self._connect_signals()
        self._add_completer()

    def _create_ui(self):
        if not self.parent():
            common.set_stylesheet(self)

        QtWidgets.QVBoxLayout(self)

        o = common.Size.Margin()
        _o = common.Size.Margin(3.0)
        self.layout().setSpacing(o)
        self.layout().setContentsMargins(_o, _o, _o, _o)

        self.ok_button = ui.PaintedButton('Add', parent=self)
        self.ok_button.setFixedHeight(
            common.Size.RowHeight(0.8)
        )
        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        self.cancel_button.setFixedHeight(
            common.Size.RowHeight(0.8)
        )
        self.pick_button = ui.PaintedButton('Pick', parent=self)

        self.editor = ui.LineEdit(parent=self)
        self.editor.setPlaceholderText(
            'Enter the path to a server, for example, \'//my_server/jobs\''
        )
        self.setFocusProxy(self.editor)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)

        row = ui.add_row(None, parent=self)
        row.layout().addWidget(self.editor, 1)
        row.layout().addWidget(self.pick_button, 0)

        row = ui.add_row(None, parent=self)
        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.Color.Background())

        o = common.Size.Margin(2.0)
        painter.drawRect(self.rect().adjusted(o, o, -o, -o))
        painter.end()

    def _connect_signals(self):
        """Connect signals."""
        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted)
        )
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected)
        )
        self.pick_button.clicked.connect(self.pick)
        self.editor.textChanged.connect(
            lambda: self.editor.setStyleSheet(
                f'color: {common.Color.Green(qss=True)};'
            )
        )

    def _add_completer(self):
        """Add and populate a QCompleter with mounted drive names.

        """
        items = []
        for info in QtCore.QStorageInfo.mountedVolumes():
            if info.isValid():
                items.append(info.rootPath())
        items += common.servers.values()

        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_stylesheet(completer.popup())
        self.editor.setCompleter(completer)

    @QtCore.Slot()
    def pick(self):
        """Get an existing directory to use as a server.

        """
        _dir = QtWidgets.QFileDialog.getExistingDirectory(parent=self)
        if not _dir:
            return

        file_info = QtCore.QFileInfo(_dir)
        if file_info.exists():
            self.editor.setText(file_info.absoluteFilePath())

    @common.error
    @common.debug
    def done(self, result):
        """Finalize action.

        """
        if result == QtWidgets.QDialog.Rejected:
            super().done(result)
            return

        if not self.text():
            raise RuntimeError('No server path specified.')

        v = self.text()
        file_info = QtCore.QFileInfo(v)

        if not file_info.exists():
            self._apply_invalid_style()
            raise RuntimeError(f'{file_info.filePath()} path does not exist.')

        if not file_info.isReadable():
            self._apply_invalid_style()
            raise RuntimeError(f'{file_info.filePath()} path is not readable.')

        if v in common.servers:
            self._apply_invalid_style()
            raise RuntimeError(f'{file_info.filePath()} path already added to the server list.')

        actions.add_server(v)
        super().done(QtWidgets.QDialog.Accepted)

    def _apply_invalid_style(self):
        # Indicate the selected item is invalid and keep the editor open
        self.editor.setStyleSheet(
            'color: {0}; border-color: {0}'.format(
                common.Color.Red(qss=True)
            )
        )
        self.editor.blockSignals(True)
        self.editor.setText(self.text())
        self.editor.blockSignals(False)

    def text(self):
        """Sanitize text.

        Returns:
            str: The sanitized text.

        """
        v = self.editor.text()
        return common.strip(v) if v else ''

    def showEvent(self, event):
        """Show event handler.

        """
        super().showEvent(event)

        common.center_to_parent(self, self.parent().window())
        self.editor.setFocus()

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.RowHeight(2.0)
        )


class ServersWidgetContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with :class:`ServersWidget`.

    """

    def setup(self):
        """Creates the context menu.

        """
        self.add_menu()
        self.separator()
        if isinstance(
                self.index, QtWidgets.QListWidgetItem
        ) and self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.reveal_menu()
            self.remove_menu()
        elif isinstance(
                self.index,
                QtWidgets.QListWidgetItem
        ) and not self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.remove_menu()
        self.separator()
        self.refresh_menu()

    def add_menu(self):
        """Add server action.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Add server...',
            'action': self.parent().add,
            'icon': ui.get_icon('add', color=common.Color.Green())
        }

    def reveal_menu(self):
        """Reveal server item action.

        """
        self.menu['Reveal...'] = {
            'action': lambda: actions.reveal(f'{self.index.text()}/.'),
            'icon': ui.get_icon('folder'),
        }

    def remove_menu(self):
        """Remove server item action.

        """
        self.menu['Remove'] = {
            'action': self.parent().remove,
            'icon': ui.get_icon('close', color=common.Color.Red())
        }

    def refresh_menu(self):
        """Refresh server list action.

        """
        self.menu['Refresh'] = {
            'action': self.parent().init_data,
            'icon': ui.get_icon('refresh')
        }


class ServersWidget(ui.ListWidget):
    """List widget used to add and remove servers to and from the local
    user settings.

    """
    progressUpdate = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(
            default_icon='server',
            parent=parent
        )

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._connect_signals()
        self._init_shortcuts()

    def _init_shortcuts(self):
        """Initializes shortcuts.

        """
        shortcuts.add_shortcuts(self, shortcuts.JobEditorShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.JobEditorShortcuts
        )
        connect(shortcuts.AddItem, self.add)
        connect(shortcuts.RemoveItem, self.remove)

    def _connect_signals(self):
        """Connects signals.

        """
        super()._connect_signals()

        self.selectionModel().selectionChanged.connect(
            functools.partial(common.save_selection, self)
        )

        common.signals.serversChanged.connect(self.init_data)
        common.signals.serverAdded.connect(
            functools.partial(common.select_index, self)
        )

    @common.debug
    @common.error
    @QtCore.Slot()
    def remove(self, *args, **kwargs):
        """Remove a server item.

        """
        index = common.get_selected_index(self)
        if not index.isValid():
            return

        v = index.data(QtCore.Qt.DisplayRole)
        v = common.strip(v)
        actions.remove_server(v)

    @common.debug
    @common.error
    @QtCore.Slot()
    def add(self, *args, **kwargs):
        """Add a server item.

        """
        w = AddServerDialog(parent=self)
        w.accepted.connect(self.init_data)
        w.open()

    def contextMenuEvent(self, event):
        """Context menu event handler.

        """
        item = self.itemAt(event.pos())
        menu = ServersWidgetContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    @common.debug
    @common.error
    @QtCore.Slot()
    def init_data(self, *args, **kwargs):
        """Load data.

        """
        common.save_selection(self)

        self.selectionModel().clearSelection()
        self.selectionModel().blockSignals(True)

        self.clear()

        size = QtCore.QSize(
            0,
            common.Size.RowHeight(0.8)
        )

        for path in sorted(common.servers, key=lambda x: x.lower()):
            self.progressUpdate.emit('Loading servers', f'Loading {path}...')

            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, path)
            item.setData(QtCore.Qt.UserRole, path)
            item.setData(QtCore.Qt.StatusTipRole, path)
            item.setData(QtCore.Qt.WhatsThisRole, path)
            item.setData(QtCore.Qt.ToolTipRole, path)
            item.setSizeHint(size)

            self.validate_item(item)
            self.insertItem(self.count(), item)

        self.progressUpdate.emit('', '')
        self.selectionModel().blockSignals(False)
        common.restore_selection(self)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def validate_item(self, item):
        """Check if the given server item is valid.

        """
        selected_index = common.get_selected_index(self)

        pixmap = images.rsc_pixmap(
            'server', common.Color.Text(),
            common.Size.RowHeight(0.8)
        )
        pixmap_selected = images.rsc_pixmap(
            'server', common.Color.Green(),
            common.Size.RowHeight(0.8)
        )
        pixmap_disabled = images.rsc_pixmap(
            'close', common.Color.Red(),
            common.Size.RowHeight(0.8)
        )
        icon = QtGui.QIcon()

        file_info = QtCore.QFileInfo(item.text())
        if file_info.exists() and file_info.isReadable():
            icon.addPixmap(pixmap, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
            )
            valid = True
        else:
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            valid = False

        item.setData(QtCore.Qt.DecorationRole, icon)

        index = self.indexFromItem(item)
        if not valid and selected_index == index:
            self.selectionModel().clearSelection()


class Node(QtCore.QObject):

    def __contains__(self, v):
        if not isinstance(v, str):
            return False
        return [f for f in self.children if f.name.lower() == v.lower()] != []

    def __init__(self, name):
        self.name = name
        self.children = []
        self.parent = None

        self.fetched_children = False

    def add_child(self, child):
        child.parent = self

        children = self.children
        children.append(child)
        self.children = sorted(children, key=lambda x: x.name.lower())

    def child(self, row):
        if row < 0 or row >= len(self.children):
            return None
        return self.children[row]

    def child_count(self):
        return len(self.children)

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0


class ServerNode(Node):
    pass


class JobNode(Node):
    pass


class BookmarkItemNode(Node):
    pass


class AddJobDialog(base.BasePropertyEditor):
    """A custom `BasePropertyEditor` used to add new jobs on a server.

    """

    #: UI layout definition
    sections = {
        0: {
            'name': 'Add Job',
            'icon': '',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': 'Name',
                        'key': None,
                        'validator': base.job_name_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Name, for example, `MY_NEW_JOB`',
                        'description': 'The job\'s name, for example, `MY_NEW_JOB`.',
                    },
                },
                1: {
                    0: {
                        'name': 'Template',
                        'key': None,
                        'validator': None,
                        'widget': functools.partial(
                            templates.TemplatesWidget, templates.JobTemplateMode
                        ),
                        'placeholder': None,
                        'description': 'Select a folder template to create this asset.',
                    },
                },
            },
        },
    }

    def __init__(self, server, parent=None):
        super().__init__(
            server,
            None,
            None,
            asset=None,
            db_table=None,
            buttons=('Add job', 'Cancel'),
            hide_thumbnail_editor=False,
            section_buttons=False,
            frameless=True,
            fallback_thumb='placeholder',
            parent=parent
        )

        self.setWindowTitle(f'{self.server}: Add job')

        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        common.signals.templateExpanded.connect(self.close)
        common.signals.jobAdded.connect(self.close)
        common.signals.serversChanged.connect(self.close)

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        return None

    def init_data(self):
        """Initialize data.

        """
        # Add a QCompleter to the name_editor
        editor = self.parent().window().job_editor
        model = editor.model()
        server = model.root_node.name
        jobs = [f.name[len(server)+1:] for f in model.root_node.children if isinstance(f, JobNode)]
        completer = QtWidgets.QCompleter(sorted(jobs))
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.name_editor.setCompleter(completer)

    @common.error
    @common.debug
    def save_changes(self):
        """Verify user options and create a new job item.

        """

        value = self.name_editor.text()
        if not value:
            raise ValueError('Must enter a name to create a job.')

        # Check if there's a thumbnail set
        if not self.thumbnail_editor.image() or self.thumbnail_editor.image().isNull():
            if common.show_message(
                    'No thumbnail set for new job',
                    'Are you sure want to continue? You can add a thumbnail after the job was created by '
                    'saving a `thumbnail.png` file to the job\'s folder.',
                    buttons=[common.YesButton, common.CancelButton],
                    message_type=None,
                    modal=True
            ) == QtWidgets.QDialog.Rejected:
                return False

        value = value.replace('\\', '/')
        server = self.server

        if QtCore.QFileInfo(f'{server}/{value}').exists():
            raise RuntimeError(f'{server}/{value} already exists.')

        # Assets with relative paths
        if '/' in self.name_editor.text():
            segments = value.split('/')
            name = segments.pop()

            # Create the folder structure
            rel_path = '/'.join(segments)

            _dir = QtCore.QDir(f'{server}/{rel_path}')
            if not _dir.exists() and not _dir.mkpath('.'):
                raise RuntimeError(f'Could not create {_dir.path()}')

            # Get the folder the template will be expanded into and
            # create it if it doesn't exist
            asset_root = f'{server}/{segments.pop(0)}'
            _dir = QtCore.QDir(asset_root)
            if not _dir.exists() and not _dir.mkpath('.'):
                raise RuntimeError(f'Could not create {_dir.path()}')

            # Expand the template into the asset folder
            self.template_editor.template_list_widget.create(name, f'{server}/{rel_path}')
            path = f'{server}/{rel_path}/{name}'

            # Add the link to the first folder of the asset structure
            if not common.add_link(
                    asset_root,
                    f'{"/".join(segments)}/{name}'.strip('/'),
                    section='links/job'
            ):
                raise RuntimeError(f'Could not add link to {server}/{segments[0]}')
        else:
            name = value

            # Expand the template into the asset folder
            self.template_editor.template_list_widget.create(name, server)
            path = f'{server}/{name}'

        # Verify the job was created
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            raise RuntimeError(f'Could not find {path}')

        # Create a thumbnail
        try:
            path += f'/thumbnail.{common.thumbnail_format}'
            self.thumbnail_editor.save_image(destination=path)
        except:
            pass

        # Let the outside world know
        common.signals.jobAdded.emit(file_info.filePath())

        common.show_message(
            'Success',
            f'{name} was successfully created at\n{file_info.filePath()}',
            message_type='success'
        )

        return True

    def showEvent(self, event):
        """Show event handler.

        """
        super().showEvent(event)

        common.center_to_parent(self, self.parent().window())
        self.name_editor.setFocus()


    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(1.5),
            common.Size.DefaultHeight()
        )


class JobsViewContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with :class:`BookmarkItemEditor`.

    """

    def setup(self):
        """Creates the context menu.

        """
        self.add_menu()
        self.separator()
        self.bookmark_properties_menu()
        self.copy_properties_menu()
        self.separator()
        self.reveal_menu()
        self.copy_json_menu()
        self.show_links_menu()
        self.separator()
        self.collapse_menu()
        self.separator()
        self.refresh_menu()
        self.separator()
        self.prune_bookmarks_menu()
        self.reveal_default_bookmarks_menu()

    def collapse_menu(self):
        """Menu used to collapse items.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Collapse all',
            'action': self.parent().collapseAll,
        }

    def add_menu(self):
        """Menu used to mark a folder as a bookmark item.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Add bookmark item...',
            'action': self.parent().add_bookmark_item,
            'icon': ui.get_icon('add', color=common.Color.Green())
        }

    def reveal_menu(self):
        """Reveal bookmark item action."""
        self.menu[contextmenu.key()] = {
            'text': 'Reveal',
            'action': functools.partial(
                actions.reveal, f'{self.index.data(QtCore.Qt.UserRole)}/.'
            ),
            'icon': ui.get_icon('folder')
        }

    def refresh_menu(self):
        """Forces a model data refresh.

        """
        model = self.parent().model()
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'action': lambda: model.init_data(model.root_node.name, force=True),
            'icon': ui.get_icon('refresh')
        }

    @QtCore.Slot()
    @common.error
    @common.debug
    def bookmark_properties_menu(self):
        """Show the bookmark item property editor.

        """
        server, job, root = self.parent().window().get_args()
        if not all((server, job, root)):
            return

        self.menu[contextmenu.key()] = {
            'text': 'Edit bookmark item properties...',
            'action': functools.partial(actions.edit_bookmark, server, job, root),
            'icon': ui.get_icon('settings')
        }

    @QtCore.Slot()
    @common.error
    @common.debug
    def copy_properties_menu(self):
        """Show the bookmark item property editor.

        """
        server, job, root = self.parent().window().get_args()
        if not all((server, job, root)):
            return

        from . import clipboard

        self.menu[contextmenu.key()] = {
            'text': 'Copy bookmark item properties...',
            'action': functools.partial(clipboard.show, server, job, root),
            'icon': ui.get_icon('settings')
        }

    @QtCore.Slot()
    @common.error
    @common.debug
    def paste_properties_menu(self):
        """Show the bookmark item property editor.

        """
        server, job, root = self.parent().window().get_args()
        if not all((server, job, root)):
            return

        from . import clipboard

        self.menu[contextmenu.key()] = {
            'text': 'Copy bookmark item properties...',
            'action': functools.partial(clipboard.show, server, job, root),
            'icon': ui.get_icon('settings')
        }

    @QtCore.Slot()
    @common.error
    @common.debug
    def copy_json_menu(self):
        """Copy bookmark item as JSON.

        """
        server, job, root = self.parent().window().get_args()
        if not all((server, job, root)):
            return

        if not QtCore.QFileInfo(f'{server}/{job}/{root}').exists():
            raise RuntimeError(f'{server}/{job}/{root} does not exist.')

        d = {
            f'{server}/{job}/{root}': {
                'server': server,
                'job': job,
                'root': root
            }
        }
        s = json.dumps(
            d,
            indent=4,
        )

        def show_json(s):
            """Shows a popup with the bookmark item as json text.

            """
            w = QtWidgets.QDialog(parent=self.parent())
            w.setMinimumWidth(common.Size.DefaultWidth())
            w.setMinimumHeight(common.Size.DefaultHeight(0.5))
            b = QtWidgets.QTextBrowser(parent=w)
            b.setText(s)
            QtWidgets.QVBoxLayout(w)
            w.layout().addWidget(b)
            w.open()

            QtWidgets.QApplication.clipboard().setText(s)

        self.menu[contextmenu.key()] = {
            'text': 'Item as json...',
            'action': functools.partial(show_json, s),
            'icon': ui.get_icon('copy')
        }

    @QtCore.Slot()
    @common.debug
    @common.error
    def show_links_menu(self):
        """Show the links associated with the selected item.

        """
        if not self.parent().selectionModel().hasSelection():
            return

        index = next(iter(self.parent().selectionModel().selectedIndexes()))
        if not index.isValid():
            return

        server = self.parent().model().root_node.name
        if server == 'server':
            return

        path = index.data(QtCore.Qt.UserRole)

        v = common.get_links(
            f'{server}/{path[len(server) + 1:].split("/")[0]}',
            section='links/job'
        )

        def _show_links(s):
            """Shows a popup with the bookmark item as json text.

            """
            w = QtWidgets.QDialog(parent=self.parent())
            w.setMinimumWidth(common.Size.DefaultWidth())
            w.setMinimumHeight(common.Size.DefaultHeight(0.5))
            b = QtWidgets.QTextBrowser(parent=w)
            b.setText(s)
            QtWidgets.QVBoxLayout(w)
            w.layout().addWidget(b)
            w.open()

            QtWidgets.QApplication.clipboard().setText(s)

        self.menu[contextmenu.key()] = {
            'text': 'Show links...',
            'action': functools.partial(_show_links, '\n'.join(v)),
            'icon': ui.get_icon('copy')
        }

    @QtCore.Slot()
    @common.debug
    @common.error
    def prune_bookmarks_menu(self):
        """Prune bookmarks.

        """

        def prune():
            """Prune bookmarks.

            """
            actions.prune_bookmarks()
            server = self.parent().model().root_node.name
            if server == 'server':
                return
            self.parent().model().init_data(server, force=True)

        self.menu[contextmenu.key()] = {
            'text': 'Prune bookmark items',
            'action': prune,
        }

    @QtCore.Slot()
    @common.debug
    @common.error
    def reveal_default_bookmarks_menu(self):
        self.menu[contextmenu.key()] = {
            'text': 'Reveal default bookmarks',
            'action': actions.reveal_default_bookmarks_json,
        }


class JobsModel(QtCore.QAbstractItemModel):
    progressUpdate = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.root_node = ServerNode('server')

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()

        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        node = index.internalPointer()
        if not node:
            return QtCore.QModelIndex()

        if node.parent == self.root_node:
            return QtCore.QModelIndex()

        return self.createIndex(node.parent.row(), 0, node.parent)

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()

        return parent_node.child_count()

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section == 0:
                return 'Job'
            elif section == 1:
                return 'Status'

        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(
                0,
                common.Size.RowHeight(0.8)
            )

        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter

        return None

    def data(self, index, role, parent=QtCore.QModelIndex()):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if not node:
            return None

        if role == QtCore.Qt.SizeHintRole:
            if isinstance(node, BookmarkItemNode):
                return QtCore.QSize(
                    super().parent().width() * 0.5,
                    common.Size.RowHeight(0.8)
                )
            elif isinstance(node, JobNode):
                return QtCore.QSize(
                    super().parent().width() * 0.5,
                    common.Size.RowHeight(0.8)
                )
            else:
                return QtCore.QSize(
                    super().parent().width() * 0.5,
                    common.Size.RowHeight()
                )

        if index.column() == 0:
            if role == QtCore.Qt.DisplayRole:
                return node.name[len(node.parent.name):].strip('/')

            if role == QtCore.Qt.UserRole:
                return index.internalPointer().name

            if role == QtCore.Qt.ToolTipRole:
                return index.internalPointer().name

            if role == QtCore.Qt.WhatsThisRole:
                return index.internalPointer().name

            if role == QtCore.Qt.StatusTipRole:
                return index.internalPointer().name

            if role == QtCore.Qt.ForegroundRole:
                if isinstance(node, JobNode) and self.hasChildren(index):
                    return common.Color.Text()
                elif isinstance(node, JobNode) and not self.hasChildren(index):
                    return common.Color.DisabledText()
                elif isinstance(node, BookmarkItemNode) and node.name in common.bookmarks:
                    return common.Color.Text()
                elif isinstance(node, BookmarkItemNode) and node.name not in common.bookmarks:
                    return common.Color.DisabledText()

            if role == QtCore.Qt.DecorationRole:
                if isinstance(node, ServerNode):
                    return ui.get_icon('server')
                elif isinstance(node, JobNode) and self.hasChildren(index):
                    return ui.get_icon('asset', color=common.Color.DisabledText())
                elif isinstance(node, JobNode) and not self.hasChildren(index):
                    return ui.get_icon('asset', color=common.Color.DarkBackground())
                elif isinstance(node, BookmarkItemNode) and node.name in common.bookmarks:
                    return ui.get_icon('bookmark', color=common.Color.Green())
                elif isinstance(node, BookmarkItemNode):
                    return ui.get_icon('bookmark', color=common.Color.DisabledText())

        if index.column() == 1:

            if isinstance(node, JobNode):
                if role == QtCore.Qt.DecorationRole:
                    return ui.get_icon('add_circle', color=common.Color.Green())
                if role == QtCore.Qt.DisplayRole:
                    return 'Add bookmark item'
                if role == QtCore.Qt.ForegroundRole:
                    return common.Color.Green()
                if role == QtCore.Qt.WhatsThisRole:
                    return 'Click to add a new bookmark item'
                if role == QtCore.Qt.ToolTipRole:
                    return 'Click to add a new bookmark item'
                if role == QtCore.Qt.StatusTipRole:
                    return 'Click to add a new bookmark item'

            if isinstance(node, BookmarkItemNode):
                if role == QtCore.Qt.DisplayRole:
                    if node.name in common.bookmarks:
                        return 'active'
                    else:
                        return 'inactive'
                if role == QtCore.Qt.ForegroundRole:
                    if node.name in common.bookmarks:
                        return common.Color.Green()
                    else:
                        return common.Color.DisabledText()
                if role == QtCore.Qt.DecorationRole:
                    if node.name in common.bookmarks:
                        return ui.get_icon('check', color=common.Color.Green())
                    else:
                        return ui.get_icon('close', color=common.Color.Red())
                if role == QtCore.Qt.WhatsThisRole:
                    return f'Bookmark item: {node.name}'
                if role == QtCore.Qt.ToolTipRole:
                    return f'Bookmark item: {node.name}'
                if role == QtCore.Qt.StatusTipRole:
                    return f'Bookmark item: {node.name}'

        return None

    def canFetchMore(self, index):
        """Returns True if the parent node has not been expanded yet.

        """
        if not index.isValid():
            return False

        node = index.internalPointer()

        if isinstance(node.parent, JobNode):
            return False

        if not node.fetched_children:
            return True

        return False

    def fetchMore(self, index):
        """Fetches children for the given parent node.

        """
        node = index.internalPointer()

        if node.fetched_children:
            self.progressUpdate.emit('', '')
            return

        self.layoutAboutToBeChanged.emit()

        recursion = common.settings.value('jobs/scandepth')
        recursion = int(recursion) if recursion is not None else 2

        for path in self.bookmark_item_generator(node.name, max_recursion=recursion):
            if path in node:
                continue
            node.add_child(BookmarkItemNode(path))
        self.layoutChanged.emit()

        node.fetched_children = True
        self.progressUpdate.emit('', '')

    def hasChildren(self, index):
        if not index.isValid():
            return True

        node = index.internalPointer()

        if isinstance(node.parent, JobNode):
            return False

        if not node.fetched_children:
            return True

        return node.child_count() > 0

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        if index.column() == 0:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == 1:
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    @QtCore.Slot(str)
    def init_data(self, server, force=False):
        self.progressUpdate.emit('', '')

        self.beginResetModel()

        if not force and server in cache:
            self.root_node = cache[server]
            self.endResetModel()
            self.progressUpdate.emit('', '')
            return

        self.root_node = ServerNode(server)

        if server == 'server':
            self.endResetModel()
            self.progressUpdate.emit('', '')
            return

        for job in self.item_generator():
            node = JobNode(job)
            self.root_node.add_child(node)

        self.endResetModel()

        cache[server] = self.root_node

        self.progressUpdate.emit('', '')

    def item_generator(self):
        """Scans the current server to find job items.

        """
        server = self.root_node.name
        if not server:
            return
        if server.endswith(':'):
            server = f'{server}/'

        # Parse source otherwise
        for entry in os.scandir(server):
            if not entry.is_dir():
                continue
            if entry.name.startswith('.'):
                continue
            if entry.name.startswith('$'):
                continue

            file_info = QtCore.QFileInfo(entry.path)

            if file_info.isHidden():
                continue
            if not file_info.isReadable():
                continue

            # Test access
            try:
                next(os.scandir(file_info.filePath()))
            except:
                continue

            # Use paths in the link file, if available
            links = common.get_links(file_info.filePath(), section='links/job')
            if links:
                for link in links:
                    _file_info = QtCore.QFileInfo(f'{file_info.filePath()}/{link}')
                    yield _file_info.filePath()
            else:
                yield file_info.filePath()

    def bookmark_item_generator(self, path, recursion=0, max_recursion=2):
        """Recursive scanning function for finding bookmark folders
        inside the given path.

        """
        # If links exist, return items stored in the link file and nothing else
        if recursion == 0:
            links = common.get_links(path, section='links/root')
            for v in links:
                yield f'{path}/{v}'

        # Otherwise parse the folder
        recursion += 1
        if recursion > max_recursion:
            return

        # Let unreadable paths fail silently
        try:
            it = os.scandir(path)
        except:
            return

        for entry in it:

            if not entry.is_dir():
                continue
            if entry.name.startswith('.'):
                continue
            if entry.name.startswith('$'):
                continue

            self.progressUpdate.emit(f'Scanning...', entry.name)

            file_info = QtCore.QFileInfo(entry.path)
            if file_info.isHidden():
                continue
            if not file_info.isReadable():
                continue

            # yield the match
            path = entry.path.replace('\\', '/')

            if entry.name == common.bookmark_item_cache_dir:
                _path = '/'.join(path.split('/')[:-1])
                yield _path

            yield from self.bookmark_item_generator(path, recursion=recursion, max_recursion=max_recursion)


class JobsView(QtWidgets.QTreeView):
    progressUpdate = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setModel(JobsModel(parent=self))

        self.setRootIsDecorated(True)
        self.setIndentation(common.Size.Margin())
        self.setUniformRowHeights(False)

        self.setItemDelegate(ui.ListWidgetDelegate(parent=self))

        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.installEventFilter(self)

        # Hide the top header
        header = QtWidgets.QHeaderView(QtCore.Qt.Horizontal, parent=self)

        header.setSectionsMovable(False)
        header.setSectionsClickable(False)
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

        header.setMinimumSectionSize(common.Size.DefaultWidth(0.2))

        self.setHeader(header)
        self.header().hide()

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        # Disable the horizontal scrollbar
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self._connect_signals()

    def _connect_signals(self):
        self.model().modelReset.connect(self.expand_active_items)

        self.model().progressUpdate.connect(self.progressUpdate)

        self.expanded.connect(self.resize_columns)
        self.collapsed.connect(self.resize_columns)
        self.model().layoutChanged.connect(self.resize_columns)
        self.model().modelReset.connect(self.resize_columns)

        self.doubleClicked.connect(self.toggle_bookmark_item)

        common.signals.jobAdded.connect(self.job_added)

    def contextMenuEvent(self, event):
        """Context menu event.

        """
        index = self.indexAt(event.pos())
        menu = JobsViewContextMenu(index, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def eventFilter(self, widget, event):
        """Event filter handler.

        """
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            ui.paint_background_icon('asset', widget)
            return True
        return False

    @QtCore.Slot()
    def resize_columns(self, *args, **kwargs):
        """Resize the columns to fit the data.

        """
        self.header().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        self.header().resizeSection(
            0,
            self.width() - self.header().sectionSize(1) - common.Size.Margin()
        )

    @QtCore.Slot(str)
    def job_added(self, path):
        """Slot -> Shows a recently added job in the view.

        Args:
            path (str): The path to the job.

        """
        if not path:
            return
        if not QtCore.QFileInfo(path).exists():
            return

        path = QtCore.QFileInfo(path).filePath()
        model = self.model()

        # Reload the data
        model.init_data(model.root_node.name, force=True)
        for node in model.root_node.children:
            if node.name.lower() == path.lower():
                index = model.createIndex(node.row(), 0, node)
                self.setExpanded(index, True)
                self.selectionModel().select(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows
                )
                self.selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows
                )
                return

    @QtCore.Slot()
    def expand_active_items(self):
        """Slot -> Expands all job items that have active bookmark items

        """
        for v in common.bookmarks:
            for node in self.model().root_node.children:
                if node.name.lower() in v.lower():
                    index = self.model().createIndex(node.row(), 0, node)
                    self.setExpanded(index, True)
                    break

    @common.debug
    @common.error
    @QtCore.Slot()
    def add_bookmark_item(self, *args, **kwargs):
        """Pick and add a folder as a new bookmark item.

        """
        if self.model().root_node.name == 'server':
            raise RuntimeError('No server selected.')

        if not self.selectionModel().hasSelection():
            raise RuntimeError('Must select a job first.')

        index = next(f for f in self.selectionModel().selectedIndexes())
        if not index.isValid():
            return

        if not QtCore.QFileInfo(index.data(QtCore.Qt.UserRole)).exists():
            raise RuntimeError(f'{index.data(QtCore.Qt.UserRole)} does not exist.')

        if not self.isExpanded(index):
            self.setExpanded(index, True)

        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            'Select a folder to use as a bookmark item',
            index.data(QtCore.Qt.UserRole),
            QtWidgets.QFileDialog.ShowDirsOnly |
            QtWidgets.QFileDialog.DontResolveSymlinks
        )

        if not path:
            return

        if index.data(QtCore.Qt.UserRole).lower() not in path.lower():
            raise RuntimeError('Bookmark item must be inside the selected job folder.')

        node = index.internalPointer()

        if path in node:
            common.show_message(
                f'Error',
                body=f'Cannot select {path.split("/")[-1]} because it is already a bookmark item.',
                message_type='error'
            )
            return

        name = path[len(node.name):].strip('/')

        # Add link
        if not common.add_link(node.name, name, section='links/root'):
            raise RuntimeError('Failed to add link.')

        self.model().layoutAboutToBeChanged.emit()
        if path not in node:
            node.add_child(BookmarkItemNode(path))

        self.model().layoutChanged.emit()

    @common.debug
    @common.error
    @QtCore.Slot()
    def add(self, *args, **kwargs):
        """Add a server item.

        """
        server = self.model().root_node.name
        if server == 'server':
            raise RuntimeError('No server selected.')

        w = AddJobDialog(server, parent=self)
        w.open()

    @QtCore.Slot()
    @common.debug
    @common.error
    def toggle_bookmark_item(self, *args, **kwargs):
        server, job, root = self.parent().window().get_args()
        if not all((server, job, root)):
            return

        if f'{server}/{job}/{root}' not in common.bookmarks:
            actions.add_bookmark(server, job, root)
        else:
            actions.remove_bookmark(server, job, root)

        if self.selectionModel().hasSelection():
            index = next(f for f in self.selectionModel().selectedIndexes())
            self.update(index)

    def mouseReleaseEvent(self, event):
        """Mouse release event.

        """
        index = self.indexAt(event.pos())
        if index.isValid() and index.column() == 1:
            node = index.internalPointer()
            if isinstance(node, JobNode):
                event.accept()
                self.add_bookmark_item(index)
                return
            if isinstance(node, BookmarkItemNode):
                event.accept()
                self.toggle_bookmark_item()
                return

        super().mouseReleaseEvent(event)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight(0.8)
        )
