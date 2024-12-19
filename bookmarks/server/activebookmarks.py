import functools
import json
import os

from PySide2 import QtWidgets, QtCore, QtGui

from . import activebookmarks_presets
from .lib import ServerAPI
from .. import contextmenu, common, ui


class Node:
    def __init__(self, key='', parent=None):
        self.parent = parent
        self.children = []
        self.data = ['', '']  # [Key, Value]
        if key:
            self.data[0] = key
        if parent:
            parent.add_child(self)

    def add_child(self, child):
        self.children.append(child)
        child.parent = self
        self.sort_children()

    def sort_children(self):
        self.children.sort(key=lambda node: node.data[0].lower())

    def child(self, row):
        return self.children[row]

    def child_count(self):
        return len(self.children)

    def row(self):
        if self.parent:
            return self.parent.children.index(self, )
        return 0

    def set_data(self, column, value):
        if 0 <= column < len(self.data):
            self.data[column] = value
            return True
        return False

    def get_data(self, column):
        if 0 <= column < len(self.data):
            return self.data[column]
        return None


class AddBookmarkDialog(QtWidgets.QDialog):
    """Dialog to add a new bookmark with server, job, and root.
    Paths can include forward slashes, and the user can proceed even if paths are invalid.
    Selecting folders through the pickers will store relative paths, but the default directory
    used when picking is constructed from the currently entered server/job/root as absolute paths.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Add Bookmark')
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Maximum)

        self.server_editor = None
        self.job_editor = None
        self.root_editor = None
        self.ok_button = None
        self.cancel_button = None

        self._server_completer = None
        self._job_completer = None
        self._root_completer = None

        self.bookmarks = ServerAPI.bookmarks()

        self._create_ui()
        self._connect_signals()
        self._init_completers()
        self._validate_inputs()

    def _normalize_path_part(self, part):
        return part.replace('\\', '/')

    def _create_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Server field
        server_row = ui.add_row('Server', parent=self)
        self.server_editor = ui.LineEdit(required=True, parent=self)
        self.server_editor.setPlaceholderText('Select or enter a server')
        server_row.layout().addWidget(self.server_editor)
        server_action = QtWidgets.QAction(self.server_editor)
        server_action.setIcon(ui.get_icon('folder', color=common.Color.Text()))
        server_action.triggered.connect(self._pick_server_folder)
        self.server_editor.addAction(server_action, QtWidgets.QLineEdit.TrailingPosition)
        main_layout.addWidget(server_row)

        # Job field
        job_row = ui.add_row('Job', parent=self)
        self.job_editor = ui.LineEdit(required=True, parent=self)
        self.job_editor.setPlaceholderText('Select or enter a job under the selected server')
        job_row.layout().addWidget(self.job_editor)
        job_action = QtWidgets.QAction(self.job_editor)
        job_action.setIcon(ui.get_icon('folder', color=common.Color.Text()))
        job_action.triggered.connect(self._pick_job_folder)
        self.job_editor.addAction(job_action, QtWidgets.QLineEdit.TrailingPosition)
        main_layout.addWidget(job_row)

        # Root field
        root_row = ui.add_row('Root', parent=self)
        self.root_editor = ui.LineEdit(required=True, parent=self)
        self.root_editor.setPlaceholderText('Select or enter a root folder under the selected job')
        root_row.layout().addWidget(self.root_editor)
        root_action = QtWidgets.QAction(self.root_editor)
        root_action.setIcon(ui.get_icon('folder', color=common.Color.Text()))
        root_action.triggered.connect(self._pick_root_folder)
        self.root_editor.addAction(root_action, QtWidgets.QLineEdit.TrailingPosition)
        main_layout.addWidget(root_row)

        # Buttons
        button_row = ui.add_row(None, parent=self)
        self.ok_button = ui.PaintedButton('Add', parent=self)
        button_row.layout().addWidget(self.ok_button, 1)
        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        button_row.layout().addWidget(self.cancel_button)
        main_layout.addWidget(button_row)

    def _connect_signals(self):
        self.server_editor.textChanged.connect(self._on_server_changed)
        self.job_editor.textChanged.connect(self._on_job_changed)
        self.root_editor.textChanged.connect(self._validate_inputs)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _init_completers(self):
        servers = [v['server'] for v in self.bookmarks.values()]
        self._server_completer = QtWidgets.QCompleter(sorted(servers), parent=self)
        self._server_completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self._server_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.server_editor.setCompleter(self._server_completer)

        jobs = [v['job'] for v in self.bookmarks.values()]
        self._job_completer = QtWidgets.QCompleter(jobs, parent=self)
        self._job_completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self._job_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.job_editor.setCompleter(self._job_completer)

        roots = [v['root'] for v in self.bookmarks.values()]
        self._root_completer = QtWidgets.QCompleter(roots, parent=self)
        self._root_completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self._root_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.root_editor.setCompleter(self._root_completer)

    def _on_server_changed(self):
        server = self._normalize_path_part(self.server_editor.text())
        self.server_editor.blockSignals(True)
        self.server_editor.setText(server)
        self.server_editor.blockSignals(False)

        self.job_editor.clear()
        self.root_editor.clear()
        self._validate_inputs()

    def _on_job_changed(self):
        job = self._normalize_path_part(self.job_editor.text())
        self.job_editor.blockSignals(True)
        self.job_editor.setText(job)
        self.job_editor.blockSignals(False)

        self.root_editor.clear()
        self._validate_inputs()

    def _default_directory(self, for_field):
        """
        Construct an absolute path to use as the starting directory for the file dialog.
        For the server field: if server is set, use its absolute path, else desktop
        For the job field: if server is set, absolute path of server, else desktop
        For the root field: if server & job set, absolute path of server/job; if only server set, absolute path of server; else desktop
        """
        desktop = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DesktopLocation)

        server = self.server_editor.text().strip()
        job = self.job_editor.text().strip()

        # Normalize
        server = self._normalize_path_part(server)
        job = self._normalize_path_part(job)

        if for_field == 'server':
            # If server set, get abs path of server, else desktop
            if server:
                return os.path.abspath(server)
            return desktop

        elif for_field == 'job':
            # If server set, abs(server), else desktop
            if server:
                return os.path.abspath(server)
            return desktop

        elif for_field == 'root':
            # If server & job set: abs(server/job)
            # If only server set: abs(server)
            # Else: desktop
            if server and job:
                return os.path.abspath(os.path.join(server, job))
            elif server:
                return os.path.abspath(server)
            return desktop

        return desktop

    def _pick_server_folder(self):
        start_path = self._default_directory('server')
        chosen = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Server Directory', start_path)
        if chosen:
            # Compute relative path from start_path to chosen
            rel_path = os.path.relpath(chosen, start_path).replace('\\', '/')
            self.server_editor.setText(self._normalize_path_part(rel_path))

    def _pick_job_folder(self):
        start_path = self._default_directory('job')
        chosen = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Job Directory', start_path)
        if chosen:
            rel_path = os.path.relpath(chosen, start_path).replace('\\', '/')
            self.job_editor.setText(self._normalize_path_part(rel_path))

    def _pick_root_folder(self):
        start_path = self._default_directory('root')
        chosen = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Root Directory', start_path)
        if chosen:
            rel_path = os.path.relpath(chosen, start_path).replace('\\', '/')
            self.root_editor.setText(self._normalize_path_part(rel_path))

    def _validate_inputs(self):
        server = self._normalize_path_part(self.server_editor.text())
        job = self._normalize_path_part(self.job_editor.text())
        root = self._normalize_path_part(self.root_editor.text())

        def check_path_valid(p):
            p = p.strip()
            if not p:
                return False
            # If absolute and doesn't exist, invalid. If relative or just a name, consider valid.
            if os.path.isabs(p):
                return os.path.isdir(p)
            return True

        valid_server = check_path_valid(server)
        valid_job = check_path_valid(job)
        valid_root = check_path_valid(root)

        self._set_lineedit_state(self.server_editor, valid_server)
        self._set_lineedit_state(self.job_editor, valid_job)
        self._set_lineedit_state(self.root_editor, valid_root)

        self.ok_button.setEnabled(True)

    def _set_lineedit_state(self, editor, valid):
        pal = editor.palette()
        if not valid and editor.text().strip():
            pal.setColor(QtGui.QPalette.Base, QtGui.QColor('#FFCCCC'))
        else:
            pal.setColor(QtGui.QPalette.Base, QtGui.QColor('#FFFFFF'))
        editor.setPalette(pal)

    @common.error
    @common.debug
    def accept(self):
        server = self._normalize_path_part(self.server_editor.text())
        job = self._normalize_path_part(self.job_editor.text())
        root = self._normalize_path_part(self.root_editor.text())

        if not (server and job and root):
            res = common.show_message(
                'Invalid Input',
                body='All fields are required. Proceed anyway?',
                message_type='error',
                buttons=[common.YesButton, common.NoButton],
                modal=True
            )
            if res == QtWidgets.QDialog.Rejected:
                return

        # Just proceed even if invalid directories, user has the choice
        if not (os.path.isdir(server) and os.path.isdir(job) and os.path.isdir(root)):
            res = common.show_message(
                'Invalid Path',
                body='The specified paths do not all exist. Proceed anyway?',
                message_type='error',
                buttons=[common.YesButton, common.NoButton],
                modal=True
            )
            if res == QtWidgets.QDialog.Rejected:
                return

        super().accept()

    def get_values(self):
        server = self._normalize_path_part(self.server_editor.text())
        job = self._normalize_path_part(self.job_editor.text())
        root = self._normalize_path_part(self.root_editor.text())
        return (server, job, root)


class SavePresetDialog(QtWidgets.QDialog):
    """Custom dialog for saving presets with a validated name."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle('Save Preset')

        self._editor = None
        self.save_button = None
        self.cancel_button = None

        self._create_ui()
        self._connect_signals()

    @property
    def editor(self):
        return self._editor

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)

        o = common.Size.Margin()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        row = ui.add_row('Name', parent=self)

        # Line edit with validator
        self._editor = ui.LineEdit(required=True, parent=row)
        self._editor.setPlaceholderText('Enter a name for the preset...')

        values = activebookmarks_presets.get_api().get_presets().keys()
        completer = QtWidgets.QCompleter(sorted(values), parent=self._editor)
        completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchContains)
        common.set_stylesheet(completer.popup())
        self._editor.setCompleter(completer)

        action = QtWidgets.QAction(self._editor)
        action.setIcon(ui.get_icon('preset', color=common.Color.Text()))
        action.triggered.connect(completer.complete)
        self._editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

        validator = QtGui.QRegExpValidator(QtCore.QRegExp(r'[^\$\s\\/:*?"<>|]*'))
        self._editor.setValidator(validator)

        row.layout().addWidget(self._editor)

        # Exclude special characters the filename cannot contain

        row = ui.add_row(None, parent=self)

        self.save_button = ui.PaintedButton('Save', parent=row)
        self.cancel_button = ui.PaintedButton('Cancel', parent=row)
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

    def _connect_signals(self):
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.RowHeight()
        )

    def get_preset_name(self):
        """Return the text entered in the line edit."""
        return self.line_edit.text()


class ActiveBookmarksContextMenu(contextmenu.BaseContextMenu):
    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """

        self.add_menu()
        self.separator()
        self.remove_menu()
        self.separator()
        self.refresh_menu()
        self.expand_all_menu()
        self.collapse_all_menu()

    def add_menu(self):
        """Creates the Add menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Add Bookmark...',
            'icon': ui.get_icon('add', color=common.Color.Green()),
            'action': self.parent().add_item,
        }

    def remove_menu(self):
        """Creates the Remove menu.

        """
        if self.index.isValid():
            self.menu[contextmenu.key()] = {
                'text': 'Remove Bookmark',
                'icon': ui.get_icon('bookmark', color=common.Color.Red()),
                'action': self.parent().remove_item,
            }

            self.separator()

        self.menu[contextmenu.key()] = {
            'text': 'Remove All Bookmarks',
            'icon': ui.get_icon('close'),
            'action': self.parent().remove_all_items,
        }

    def expand_all_menu(self):
        """Creates the Expand All menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Expand All',
            'icon': ui.get_icon('expand'),
            'action': self.parent().view().expandAll,
        }

    def collapse_all_menu(self):
        """Creates the Collapse All menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Collapse All',
            'icon': ui.get_icon('collapse'),
            'action': self.parent().view().collapseAll,
        }

    def refresh_menu(self):
        """Creates the Refresh menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'icon': ui.get_icon('refresh'),
            'action': self.parent().init_data,
        }


class ActiveBookmarksModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_node = Node()
        self.bookmarks = {}
        self.init_data()

        common.signals.bookmarkAdded.connect(self.add_item)
        common.signals.bookmarkRemoved.connect(self.remove_item)

    def init_data(self):
        self.beginResetModel()
        self.bookmarks = ServerAPI.bookmarks(force=True)

        self.root_node = Node()
        for key in sorted(self.bookmarks.keys(), key=lambda x: x.lower()):
            key_node = Node(key, self.root_node)
            values = self.bookmarks[key]
            for component in ['server', 'job', 'root']:
                value = values.get(component, '')
                child_node = Node(component, key_node)
                child_node.data[1] = value
        self.endResetModel()

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0
        parent_node = self.get_node(parent)
        return parent_node.child_count()

    def columnCount(self, parent):
        return 2  # Key and Value

    def data(self, index, role):
        if not index.isValid():
            return None
        node = self.get_node(index)

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return node.get_data(index.column())

        if role == QtCore.Qt.DecorationRole:
            if not index.column() == 0:
                return None

            if not node.parent == self.root_node:
                return None

            if not os.path.exists(node.data[0]):
                return ui.get_icon('alert', color=common.Color.Red())
            return ui.get_icon('bookmark', color=common.Color.Green())

        if role == QtCore.Qt.FontRole:
            if not index.column() == 0:
                return None
            if not node.parent == self.root_node:
                return None

            font, metrics = common.Font.BoldFont(common.Size.MediumText())
            if not os.path.exists(node.data[0]):
                font, metrics = common.Font.ThinFont(common.Size.MediumText())
                return font

            return font

        if role == QtCore.Qt.SizeHintRole:
            if node.parent == self.root_node:
                height = common.Size.RowHeight()
            else:
                height = common.Size.RowHeight(0.66)
            font, metrics = common.Font.MediumFont(common.Size.MediumText())

            return QtCore.QSize(
                metrics.width(index.data(QtCore.Qt.DisplayRole)) + common.Size.Margin(),
                height,
            )
        return None

    def headerData(self, section, orientation, role):
        headers = ['Bookmarks', '']
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return headers[section]
        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        node = self.get_node(index)
        if index.column() == 1 and node.parent != self.root_node:
            return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |
                    QtCore.Qt.ItemIsEditable)
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def parent(self, index):
        node = self.get_node(index)
        parent_node = node.parent
        if parent_node == self.root_node or parent_node is None:
            return QtCore.QModelIndex()
        return self.createIndex(parent_node.row(), 0, parent_node)

    def index(self, row, column, parent):
        parent_node = self.get_node(parent)
        if row < 0 or row >= parent_node.child_count():
            return QtCore.QModelIndex()
        child_node = parent_node.child(row)
        return self.createIndex(row, column, child_node)

    def root_index(self):
        return self.createIndex(0, 0, self.root_node)

    def get_node(self, index):
        if index.isValid():
            return index.internalPointer()
        return self.root_node

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.isValid():
            value = value.strip()
            if not value:
                return False  # Reject empty strings
            node = self.get_node(index)
            if node.set_data(index.column(), value):
                # Update the dictionary if necessary
                self.update_data(node)
                self.dataChanged.emit(index, index)
                return True
        return False

    @QtCore.Slot(Node)
    def update_data(self, node):
        if node.parent and node.parent.parent == self.root_node:
            key_node = node.parent
            key = key_node.data[0]

            components = {child.data[0]: child.data[1] for child in key_node.children}
            new_key = ServerAPI.bookmark_key(
                components.get('server', ''),
                components.get('job', ''),
                components.get('root', '')
            )
            if '' in components.values():
                return

            self.bookmarks.pop(key, None)
            self.bookmarks[new_key] = components

            key_node.set_data(0, new_key)
            key_node.data[1] = ''

            self.root_node.sort_children()

            idx = self.createIndex(key_node.row(), 0, key_node)
            self.dataChanged.emit(idx, idx)
            ServerAPI.save_bookmarks(self.bookmarks)

        elif node.parent == self.root_node:
            # Do not allow editing of the key column
            pass

    @common.error
    @common.debug
    @QtCore.Slot(str, str, str)
    def add_item(self, server, job, root):
        if not all([server, job, root]):
            return False
        new_key = ServerAPI.bookmark_key(server, job, root)
        if new_key in self.bookmarks:
            return False
        components = {'server': server, 'job': job, 'root': root}

        self.beginInsertRows(
            QtCore.QModelIndex(),
            self.root_node.child_count(),
            self.root_node.child_count()
        )

        self.bookmarks[new_key] = components
        key_node = Node(new_key, self.root_node)
        for component in ['server', 'job', 'root']:
            value = components[component]
            child_node = Node(component, key_node)
            child_node.data[1] = value
        self.root_node.sort_children()
        self.endInsertRows()

        ServerAPI.save_bookmarks(self.bookmarks)
        return True

    @common.debug
    @QtCore.Slot(str)
    @QtCore.Slot(str)
    @QtCore.Slot(str)
    def remove_item(self, server, job, root):
        key = ServerAPI.bookmark_key(server, job, root)
        for i in range(self.rowCount(self.root_index())):
            index = self.index(i, 0, self.root_index())
            if not index.isValid():
                continue
            node = self.get_node(index)
            if node.data[0] == key:
                self.removeRows(i, 1)
                return
        raise ValueError(f'Bookmark "{key}" not found.')

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        parent_node = self.get_node(parent)
        if parent_node != self.root_node:
            return False  # Only allow removal of top-level items
        self.beginRemoveRows(parent, row, row + count - 1)
        for i in range(count):
            child_node = parent_node.children.pop(row)
            # Remove from dictionary
            self.bookmarks.pop(child_node.data[0], None)
        self.endRemoveRows()

        ServerAPI.save_bookmarks(self.bookmarks)
        return True

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction

    def canDropMimeData(self, data, action, row, column, parent):
        if action != QtCore.Qt.CopyAction:
            return False
        if not data.hasFormat('text/plain'):
            return False
        return True

    def dropMimeData(self, data, action, row, column, parent):
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
        if not data.hasText():
            return False
        text = data.text()

        try:
            data = json.loads(text)
            for value in data.values():
                if 'server' not in value or 'job' not in value or 'root' not in value:
                    return False
                if not self.add_item(value['server'], value['job'], value['root']):
                    return False
        except json.JSONDecodeError:
            return False

        return True


class ActiveBookmarksWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.toolbar = None
        self.tree_view = None
        self.apply_preset_action = None
        self.delete_preset_action = None

        self._create_ui()
        self._connect_signals()

        self.init_data()
        self.init_presets()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.layout().setContentsMargins(0, 0, 0, 0)

        # Toolbar
        self.toolbar = QtWidgets.QToolBar(self)
        self.toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolbar.setIconSize(QtCore.QSize(common.Size.Margin(), common.Size.Margin()))

        # Add item
        action = QtWidgets.QAction(ui.get_icon('add', color=common.Color.Green()), 'Add Bookmark', self)
        action.triggered.connect(self.add_item)
        self.toolbar.addAction(action)

        self.toolbar.addSeparator()

        # Add label "Presets"
        label = QtWidgets.QLabel('Presets', self)
        label.setStyleSheet(f'color: {common.Color.DisabledText(qss=True)};')
        self.toolbar.addWidget(label)

        # Save preset
        action = QtWidgets.QAction(ui.get_icon('add_preset', color=common.Color.DisabledText()), 'Save', self)
        action.triggered.connect(self.save_preset)
        self.toolbar.addAction(action)

        # Load preset
        action = QtWidgets.QAction(ui.get_icon('preset', color=common.Color.DisabledText()), 'Load', self)
        menu = QtWidgets.QMenu(self)
        menu.addAction('No presets...')
        menu.actions()[0].setEnabled(False)
        action.setMenu(menu)
        self.apply_preset_action = action
        action.triggered.connect(lambda: self.apply_preset_action.menu().exec_(QtGui.QCursor().pos()))
        self.toolbar.addAction(action)

        # Create QTreeView
        self.tree_view = QtWidgets.QTreeView(self)
        self.tree_view.setRootIsDecorated(False)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setObjectName('ActiveBookmarksView')

        self.tree_view.setAcceptDrops(True)
        self.tree_view.viewport().setAcceptDrops(True)
        self.tree_view.dragEnterEvent = self.dragEnterEvent
        self.tree_view.dragMoveEvent = self.dragMoveEvent

        self.tree_view.setModel(ActiveBookmarksModel(parent=self.tree_view))

        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.tree_view, 1)

    def _connect_signals(self):
        common.signals.bookmarksChanged.connect(self.init_data)
        common.signals.activeBookmarksPresetsChanged.connect(self.init_presets)

        self.model().modelReset.connect(self.set_spanned)
        self.model().rowsInserted.connect(self.set_spanned)
        self.model().rowsRemoved.connect(self.set_spanned)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def contextMenuEvent(self, event):
        """Context menu event.

        """
        index = next(iter(self.tree_view.selectedIndexes()), QtCore.QModelIndex())
        persistent_index = QtCore.QPersistentModelIndex(index)

        menu = ActiveBookmarksContextMenu(persistent_index, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def view(self):
        return self.tree_view

    def model(self):
        return self.tree_view.model()

    @QtCore.Slot(str)
    def selection_changed(self, path):
        # Select the item in the tree view
        model = self.model()

        for i in range(model.rowCount(QtCore.QModelIndex())):
            index = model.index(i, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if path == index.data(QtCore.Qt.DisplayRole):
                self.tree_view.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.tree_view.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.Select)
                return

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_item(self):
        dialog = AddBookmarkDialog(parent=self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        server, job, root = dialog.get_values()
        if not all([server, job, root]):
            raise ValueError('All fields are required.')

        if not self.model().add_item(server.strip(), job.strip(), root.strip()):
            raise ValueError('Failed to add bookmark.')

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_item(self):
        index = self.tree_view.currentIndex()
        node = self.model().get_node(index)
        if node.parent != self.model().root_node:
            raise ValueError('Cannot remove a child node.')
        row = index.row()
        self.model().removeRows(row, 1)
        self.model().dataChanged.emit(index, index)

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_all_items(self):
        self.model().removeRows(0, self.model().rowCount(self.model().root_index()))

    @common.error
    @common.debug
    @QtCore.Slot()
    def save_preset(self):
        """Save the current bookmarks as a preset.

        """
        if not common.bookmarks:
            raise ValueError('No bookmarks to save as a preset.')

        dialog = SavePresetDialog(parent=self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        preset_name = dialog.editor.text()
        if not preset_name:
            raise ValueError('Cannot save a preset with an empty name.')

        # Save the preset
        api = activebookmarks_presets.get_api()

        try:
            api.save_preset(preset_name)
        except FileExistsError:
            if common.show_message(
                    'A template with the same name already exists. Overwrite?',
                    body='This action not undoable.',
                    buttons=[common.YesButton, common.NoButton],
                    modal=True
            ) == QtWidgets.QDialog.Rejected:
                return

            api.save_preset(preset_name, force=True)

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def activate_preset(self, preset, *args, **kwargs):
        if common.show_message(
                f'Are you sure you want to activate the preset "{preset}"?',
                body='This action will overwrite the current bookmark selection.',
                buttons=[common.YesButton, common.NoButton],
                modal=True
        ) == QtWidgets.QDialog.Rejected:
            return
        api = activebookmarks_presets.get_api()
        api.activate_preset(preset)

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def delete_preset(self, preset_name, *args, **kwargs):
        """Removes the specified preset.

        """
        if not common.bookmarks:
            raise ValueError('No presets to remove.')

        if common.show_message(
                f'Are you sure you want to remove "{preset_name}"?',
                body='This action is not undoable.',
                buttons=[common.YesButton, common.NoButton],
                modal=True
        ) == QtWidgets.QDialog.Rejected:
            return

        api = activebookmarks_presets.get_api()
        api.delete_preset(preset_name)

        common.signals.activeBookmarksPresetsChanged.emit()

    @common.error
    @common.debug
    @QtCore.Slot()
    def init_data(self):
        self.model().init_data()
        self.set_spanned()

    @common.error
    @common.debug
    def init_presets(self):
        api = activebookmarks_presets.get_api()
        presets = api.get_presets(force=True)

        action = self.apply_preset_action
        menu = action.menu()
        menu.clear()
        if not presets:
            menu.addAction('No presets...').setEnabled(False)
            return

        for preset in sorted(presets.keys(), key=lambda x: x.lower()):
            _action = menu.addAction(preset)
            _action.triggered.connect(functools.partial(self.activate_preset, preset))
            menu.addAction(_action)

    def set_spanned(self):
        for i in range(self.model().rowCount(self.model().root_index())):
            self.tree_view.setFirstColumnSpanned(i, self.model().root_index(), True)
