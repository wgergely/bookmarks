import collections
import functools
import os
import re

from PySide2 import QtWidgets, QtCore

from .lib import ServerAPI, JobStyle
from .model import ServerModel, NodeType
from .. import contextmenu, common, shortcuts, ui, actions
from ..editor import base
from ..editor.base_widgets import ThumbnailEditorWidget
from ..templates.lib import TemplateItem, TemplateType


class ServerContextMenu(contextmenu.BaseContextMenu):

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.add_server_menu()
        self.add_job_menu()
        self.separator()
        self.set_job_style_menu()
        self.separator()
        self.add_reveal_menu()
        self.separator()
        self.remove_server_menu()
        self.separator()
        self.add_view_menu()

    def add_server_menu(self):
        """Add the server menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Add Server...',
            'icon': ui.get_icon('add', color=common.Color.Green()),
            'action': self.parent().add_server,
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.AddServer
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.AddServer
            )
        }

    def add_job_menu(self):
        """Add the job menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        self.menu[contextmenu.key()] = {
            'text': 'Add Job...',
            'icon': ui.get_icon('add_folder', color=common.Color.Green()),
            'action': self.parent().add_job,
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.AddJob
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.AddJob
            )
        }

    def set_job_style_menu(self):
        """Set the job style menu.

        """
        k = 'Job Style'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('icon_bw_sm')

        for style in JobStyle:
            name = style.name
            # split name by capital letters
            name_split = re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))', name)
            display_name = ' '.join(name_split)

            icon = None
            if common.settings.value(ServerAPI.job_style_settings_key) == style.value:
                icon = ui.get_icon('check', color=common.Color.Green())

            self.menu[k][contextmenu.key()] = {
                'text': display_name,
                'icon': icon,
                'action': functools.partial(self.parent().set_job_style, style),
                'checkable': True,
            }

    def add_reveal_menu(self):
        """Add reveal menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if os.path.exists(node.path()):
            self.menu[contextmenu.key()] = {
                'text': 'Reveal in Explorer',
                'icon': ui.get_icon('folder'),
                'action': self.parent().reveal,
                'shortcut': shortcuts.get(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RevealServer
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RevealServer
                ),
            }

    def remove_server_menu(self):
        """Remove server menu.

        """
        node = self.parent().get_node_from_selection()

        if node and node.type == NodeType.ServerNode:
            self.menu[contextmenu.key()] = {
                'text': 'Remove...',
                'icon': ui.get_icon('close', color=common.Color.Red()),
                'action': self.parent().remove_server,
                'shortcut': shortcuts.get(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RemoveServer
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RemoveServer
                ),
            }
        if node and node.type == NodeType.RootNode:
            self.menu[contextmenu.key()] = {
                'text': 'Remove...',
                'icon': ui.get_icon('close', color=common.Color.Red()),
                'action': self.parent().remove_server,
                'shortcut': shortcuts.get(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RemoveServer
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RemoveServer
                ),
            }

        # Remove all
        self.menu[contextmenu.key()] = {
            'text': 'Remove All Servers',
            'icon': ui.get_icon('close', color=common.Color.Red()),
            'action': self.parent().remove_all_servers,
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.RemoveAllServers
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.RemoveAllServers
            ),
        }

    def add_view_menu(self):
        """Add view menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'icon': ui.get_icon('refresh'),
            'action': self.parent().init_data,
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.ReloadServers
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.ReloadServers
            ),
        }
        self.menu[contextmenu.key()] = {
            'text': 'Expand All',
            'icon': ui.get_icon('expand'),
            'action': (self.parent().expandAll),
            'help': 'Expand all items.',
        }
        self.menu[contextmenu.key()] = {
            'text': 'Collapse All',
            'icon': ui.get_icon('collapse'),
            'action': (self.parent().collapseAll),
            'help': 'Collapse all items.',
        }


class AddServerDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Add Server')

        self.name_editor = None
        self.ok_button = None
        self.cancel_button = None

        self._init_ui()
        self._init_completer()
        self._connect_signals()

    def _init_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Indicator(6.0)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        row = ui.add_row(None, height=None, parent=self)
        self.name_editor = ui.LineEdit(row, parent=self)
        self.name_editor.setPlaceholderText('Enter a path to a server...')

        action = QtWidgets.QAction(self.name_editor)
        action.setIcon(ui.get_icon('preset', color=common.Color.Text()))
        self.name_editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

        action = QtWidgets.QAction(self.name_editor)
        action.setIcon(ui.get_icon('folder', color=common.Color.Text()))
        self.name_editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

        self.name_editor.setValidator(base.path_validator)

        row.layout().addWidget(self.name_editor)

        row = ui.add_row(None, height=None, parent=self)

        self.ok_button = ui.PaintedButton('Add', parent=self)
        row.layout().addWidget(self.ok_button, 1)

        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        row.layout().addWidget(self.cancel_button)

        self.setFocusProxy(self.name_editor)

    def _connect_signals(self):
        self.name_editor.actions()[-1].triggered.connect(self.pick_folder)
        self.name_editor.actions()[-2].triggered.connect(self.name_editor.completer().complete)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    @common.error
    @common.debug
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            return super().done(r)

        v = self.name_editor.text()
        if not v:
            raise ValueError('Must enter a valid path.')
        if not os.path.exists(v):
            raise ValueError(f'Path "{v}" does not exist.')

        ServerAPI.add_server(v)
        super().done(r)

    @common.error
    @common.debug
    @QtCore.Slot()
    def pick_folder(self):
        """Pick a folder."""
        v = self.name_editor.text()
        if v and os.path.exists(v):
            p = v
        else:
            p = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DesktopLocation)

        path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select a server folder', p)
        if not path:
            return
        if not os.path.exists(path):
            raise ValueError(f'Path "{path}" does not exist.')

        self.name_editor.setText(path)

    def _init_completer(self):
        servers = []

        _saved_servers = ServerAPI.get_servers()
        _saved_servers = _saved_servers if _saved_servers else {}

        servers += list(_saved_servers.keys())

        drives = ServerAPI.get_mapped_drives()
        for k in drives:
            servers.append(k)
            servers.append(drives[k])

        servers = sorted({k.replace('\\', '/').rstrip('/'): k for k in servers}.values())

        completer = QtWidgets.QCompleter(servers, parent=self)
        completer.setCompletionMode(QtWidgets.QCompleter.UnfilteredPopupCompletion)
        self.name_editor.setCompleter(completer)
        common.set_stylesheet(completer.popup())

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight(0.1)
        )


class AddJobDialog(QtWidgets.QDialog):

    def __init__(self, root_path, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Add Job')

        self._root_path = root_path

        self.client_row = None
        self.job_row = None
        self.department_row = None

        self.client_editor = None
        self.job_editor = None
        self.department_editor = None
        self._thumbnail_editor = None

        self.asset_template_combobox = None

        self.summary_label = None

        self.job_style = None

        self.ok_button = None
        self.cancel_button = None

        self._init_job_style()
        self._create_ui()
        self._connect_signals()

        self._apply_job_style()
        self._init_completers()

        self.update_timer = common.Timer(parent=self)
        self.update_timer.setInterval(300)
        self.update_timer.timeout.connect(self.update_summary)
        self.update_timer.start()

        QtCore.QTimer.singleShot(100, self._init_templates)

    def _init_job_style(self):
        v = common.settings.value(ServerAPI.job_style_settings_key)
        v = JobStyle(v) if isinstance(v, int) else JobStyle.NoSubdirectories.value
        self.job_style = v

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().setSpacing(0)
        widget.layout().setAlignment(QtCore.Qt.AlignCenter)
        widget.setStyleSheet(f'background-color: {common.Color.VeryDarkBackground(qss=True)};')
        widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self._thumbnail_editor = ThumbnailEditorWidget(
            fallback_thumb='folder_sm',
            parent=self
        )
        widget.layout().addWidget(self._thumbnail_editor, 0)
        self.layout().addWidget(widget, 0)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(widget)
        o = common.Size.Indicator(6.0)
        widget.layout().setContentsMargins(o, o, o, o)
        widget.layout().setSpacing(o * 0.5)

        row = ui.add_row(None, height=None, parent=widget)
        self.summary_label = QtWidgets.QLabel(parent=self)
        self.summary_label.setText('')
        self.summary_label.setTextFormat(QtCore.Qt.RichText)
        row.layout().addWidget(self.summary_label, 1)

        grp = ui.get_group(parent=widget)

        row = ui.add_row('Client', height=None, parent=grp)
        self.client_editor = ui.LineEdit(required=True, parent=self)
        self.client_editor.setPlaceholderText('Enter client name, for example: Netflix')
        self.client_editor.setValidator(base.name_validator)
        row.layout().addWidget(self.client_editor)
        self.client_row = row

        row = ui.add_row('Job', height=None, parent=grp)
        self.job_editor = ui.LineEdit(required=True, parent=self)
        self.job_editor.setPlaceholderText('Enter job name, for example: StrangerThings')
        self.job_editor.setValidator(base.name_validator)
        row.layout().addWidget(self.job_editor)
        self.job_row = row

        row = ui.add_row('Department', height=None, parent=grp)
        self.department_editor = ui.LineEdit(required=True, parent=self)
        self.department_editor.setPlaceholderText('Enter department name, for example: Production')
        self.department_editor.setValidator(base.name_validator)
        row.layout().addWidget(self.department_editor)
        self.department_row = row

        grp = ui.get_group(parent=widget)

        row = ui.add_row('Asset Template', height=None, parent=grp)
        self.asset_template_combobox = QtWidgets.QComboBox(parent=self)
        self.asset_template_combobox.setView(QtWidgets.QListView(parent=self.asset_template_combobox))
        row.layout().addWidget(self.asset_template_combobox, 1)

        widget.layout().addStretch(100)

        row = ui.add_row(None, height=None, parent=widget)
        self.ok_button = ui.PaintedButton('Add', parent=self)
        row.layout().addWidget(self.ok_button, 1)

        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        row.layout().addWidget(self.cancel_button)

        self.layout().addWidget(widget, 1)

    def _apply_job_style(self):
        if self.job_style == JobStyle.NoSubdirectories:
            self.client_row.hide()
            self.department_row.hide()
        elif self.job_style == JobStyle.JobsHaveClient:
            self.department_row.hide()
        elif self.job_style == JobStyle.JobsHaveClientAndDepartment:
            pass

    def _init_templates(self):
        templates = TemplateItem.get_saved_templates(TemplateType.UserTemplate)
        templates = [f for f in templates]
        if not templates:
            self.asset_template_combobox.addItem('No templates found.', userData=None)
            self.asset_template_combobox.setItemData(
                0,
                ui.get_icon('close', color=common.Color.VeryDarkBackground()),
                QtCore.Qt.DecorationRole
            )
            return

        for template in templates:
            self.asset_template_combobox.addItem(template['name'], userData=template)

    def _init_completers(self):

        def _it(path, depth, max_depth):
            depth += 1
            if depth > max_depth:
                return
            for entry in os.scandir(path):
                if not entry.is_dir():
                    continue
                if entry.name.startswith('.'):
                    continue
                if not os.access(entry.path, os.R_OK | os.W_OK):
                    continue
                p = entry.path.replace('\\', '/')
                _rel_path = p[len(self._root_path) + 1:].strip('/')

                if depth == max_depth:
                    yield _rel_path
                abs_path = entry.path.replace('\\', '/')
                yield from _it(abs_path, depth, max_depth)

        def _add_completer(editor, values):
            completer = QtWidgets.QCompleter(values, parent=editor)
            completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            completer.setFilterMode(QtCore.Qt.MatchContains)
            common.set_stylesheet(completer.popup())

            action = QtWidgets.QAction(editor)
            action.setIcon(ui.get_icon('preset', color=common.Color.Text()))
            action.triggered.connect(completer.complete)
            editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

            action = QtWidgets.QAction(editor)
            action.setIcon(ui.get_icon('uppercase', color=common.Color.SecondaryText()))
            action.triggered.connect(lambda: editor.setText(editor.text().upper()))
            editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

            action = QtWidgets.QAction(editor)
            action.setIcon(ui.get_icon('lowercase', color=common.Color.SecondaryText()))
            action.triggered.connect(lambda: editor.setText(editor.text().lower()))
            editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

            editor.setCompleter(completer)

        if self.job_style == JobStyle.NoSubdirectories:
            values = sorted([f for f in _it(self._root_path, -1, 1)])
            _add_completer(self.job_editor, set(values))

        elif self.job_style == JobStyle.JobsHaveClient:
            values = sorted([f for f in _it(self._root_path, -1, 2)])
            client_values = [f.split('/')[0] for f in values if len(f.split('/')) >= 1]
            job_values = [f.split('/')[1] for f in values if len(f.split('/')) >= 2]

            _add_completer(self.client_editor, set(client_values))
            _add_completer(self.job_editor, set(job_values))

        elif self.job_style == JobStyle.JobsHaveClientAndDepartment:
            values = sorted([f for f in _it(self._root_path, -1, 3)])
            client_values = [f.split('/')[0] for f in values if len(f.split('/')) >= 1]
            job_values = [f.split('/')[1] for f in values if len(f.split('/')) >= 2]
            department_values = [f.split('/')[2] for f in values if len(f.split('/')) >= 3]

            _add_completer(self.client_editor, set(client_values))
            _add_completer(self.job_editor, set(job_values))
            _add_completer(self.department_editor, set(department_values))

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    @QtCore.Slot()
    def update_summary(self):
        summary = f'The job will be created at <span style="color: {common.Color.Green(qss=True)}">{self._root_path}'
        invalid_label = f'<span style="color: {common.Color.LightYellow(qss=True)}">Make sure to fill out all required fields.</span>'

        jt = self.job_editor.text()
        ct = self.client_editor.text()
        dt = self.department_editor.text()

        if self.job_style == JobStyle.NoSubdirectories:
            if not jt:
                self.summary_label.setText(invalid_label)
                return
            summary = f'{summary}/{jt}'
        elif self.job_style == JobStyle.JobsHaveClient:
            if not all((ct, jt)):
                self.summary_label.setText(invalid_label)
                return
            summary = f'{summary}/{ct}/{jt}'
        elif self.job_style == JobStyle.JobsHaveClientAndDepartment:
            if not all((ct, jt, dt)):
                self.summary_label.setText(invalid_label)
                return
            summary = f'{summary}/{ct}/{jt}/{dt}'
        summary = f'{summary}</span>'

        if self.asset_template_combobox.currentData():
            template = self.asset_template_combobox.currentData()
            summary = f'{summary} using the template "{template["name"]}"'
        else:
            summary = f'{summary} without using a template.'

        self.summary_label.setText(summary)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(1.5),
            common.Size.DefaultHeight(0.1)
        )

    @common.error
    @common.debug
    @QtCore.Slot(int)
    def done(self):
        jt = self.job_editor.text()

        if self.job_style == JobStyle.NoSubdirectories:
            if not jt:
                raise ValueError('Job name is required.')

            path = f'{self._root_path}/{jt}'
            if os.path.exists(path):
                raise ValueError(f'Job already exists at "{path}".')

            os.makedirs(path)

            if self.asset_template_combobox.currentData():
                template = self.asset_template_combobox.currentData()
                template.extract_template(
                    path,
                    extract_contents_to_links=False,
                    ignore_existing_folders=False
                )

            return super().done(QtWidgets.QDialog.Accepted)


class ServerView(QtWidgets.QTreeView):
    jobStyleChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Servers')

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        if not parent:
            common.set_stylesheet(self)

        self.setHeaderHidden(True)
        self.setIndentation(common.Size.Margin(1.0))
        self._expanded_nodes = []
        self._selected_node = None

        self._init_model()
        self._init_shortcuts()
        self._connect_signals()

        QtCore.QTimer.singleShot(100, self.init_data)

    def _init_shortcuts(self):
        shortcuts.add_shortcuts(self, shortcuts.ServerViewShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.ServerViewShortcuts
        )
        connect(shortcuts.AddServer, self.add_server)
        connect(shortcuts.RemoveServer, self.remove_server)
        connect(shortcuts.RemoveAllServers, self.remove_all_servers)
        connect(shortcuts.AddJob, self.add_job)
        connect(shortcuts.AddBookmark, self.add_bookmark)
        connect(shortcuts.RevealServer, self.reveal)
        connect(shortcuts.ReloadServers, self.init_data)

    def _init_model(self):
        proxy = QtCore.QSortFilterProxyModel(parent=self)
        proxy.setSourceModel(ServerModel(parent=self))
        self.setModel(proxy)

    def _connect_signals(self):
        self.model().modelAboutToBeReset.connect(self.save_expanded_nodes)
        self.model().layoutAboutToBeChanged.connect(self.save_expanded_nodes)
        self.model().modelReset.connect(self.restore_expanded_nodes)
        self.model().layoutChanged.connect(self.restore_expanded_nodes)
        self.expanded.connect(self.save_expanded_nodes)
        self.collapsed.connect(self.save_expanded_nodes)

        self.selectionModel().selectionChanged.connect(self.save_selected_node)
        self.model().modelAboutToBeReset.connect(self.save_selected_node)
        self.model().layoutAboutToBeChanged.connect(self.save_selected_node)

        self.expanded.connect(self.restore_selected_node)
        self.model().modelReset.connect(self.restore_selected_node)
        self.model().layoutChanged.connect(self.restore_selected_node)

    def contextMenuEvent(self, event):
        """Context menu event.

        """
        index = self.indexAt(event.pos())
        source_index = self.model().mapToSource(index)
        persistent_index = QtCore.QPersistentModelIndex(source_index)

        menu = ServerContextMenu(persistent_index, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight()
        )

    def get_node_from_selection(self):
        """
        Get the internal node from the current selection.

        """
        if not self.selectionModel().hasSelection():
            return None

        index = next(f for f in self.selectionModel().selectedIndexes())
        if not index.isValid():
            return None

        node = self.model().mapToSource(index).internalPointer()
        if not node:
            return None

        return node

    @QtCore.Slot()
    def save_expanded_nodes(self, *args, **kwargs):
        """
        Save the expanded nodes.

        """
        if not self.model() or not self.model().sourceModel():
            self._expanded_nodes = []

        # Iterate over all direct child indexes of the root node
        for i in range(self.model().rowCount(parent=self.rootIndex())):
            index = self.model().index(i, 0, self.rootIndex())
            if not index.isValid():
                continue

            if self.isExpanded(index):
                node = self.model().mapToSource(index).internalPointer()
                if not node:
                    continue
                self._expanded_nodes.append(node.path())

    @QtCore.Slot()
    def restore_expanded_nodes(self, *args, **kwargs):
        """
        Restore the expanded nodes.

        """
        if not self._expanded_nodes:
            return

        if not self.model() or not self.model().sourceModel():
            return

        for i in range(self.model().rowCount(parent=self.rootIndex())):
            index = self.model().index(i, 0, self.rootIndex())
            if not index.isValid():
                continue

            node = self.model().mapToSource(index).internalPointer()
            if not node:
                continue

            if node.path() in self._expanded_nodes:
                self.expand(index)

    @QtCore.Slot()
    def save_selected_node(self, *args, **kwargs):
        """
        Save the selected node.

        """
        node = self.get_node_from_selection()
        if not node:
            return

        self._selected_node = node.path()

    @QtCore.Slot()
    def restore_selected_node(self):
        """
        Restore the selected node.

        """

        def _it(parent_index):
            for i in range(self.model().rowCount(parent_index)):
                _index = self.model().index(i, 0, parent_index)
                if not _index.isValid():
                    continue
                yield _index
                yield from _it(_index)

        if not self._selected_node:
            return

        for index in _it(self.rootIndex()):
            node = self.model().mapToSource(index).internalPointer()
            if not node:
                continue

            if node.path() == self._selected_node:
                self.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.setCurrentIndex(index)
                self.scrollTo(index)
                break

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_server(self):
        """Add a server.

        """
        dialog = AddServerDialog(parent=self)
        dialog.open()

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_server(self):
        """Remove a server.

        """
        node = self.get_node_from_selection()
        if not node:
            return

        if node.type != NodeType.ServerNode:
            return

        ServerAPI.remove_server(node.server)

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_all_servers(self):
        """Remove all servers.

        """
        if common.show_message(
                'Are you sure you want to remove all servers?',
                body='This action cannot be undone.',
                message_type='error',
                buttons=[common.YesButton, common.NoButton],
                modal=True,

        ) == QtWidgets.QDialog.Rejected:
            return
        ServerAPI.clear_servers()

    @common.error
    @common.debug
    @QtCore.Slot()
    def init_data(self):
        """Initialize the data.

        """
        self.model().sourceModel().init_data()

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_bookmark(self):
        """Add a bookmark.

        """
        pass

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_bookmark(self):
        """Remove a bookmark.

        """
        pass

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_all_bookmarks(self):
        """Remove all bookmarks.

        """

    @common.error
    @common.debug
    @QtCore.Slot()
    def reveal(self):
        """
        Reveal the link in the file explorer.
        """
        node = self.get_node_from_selection()
        if not node:
            return

        path = node.path()
        if not path:
            return
        actions.reveal(path)

    @common.error
    @common.debug
    @QtCore.Slot()
    def set_job_style(self, style):
        """
        Set the job style.

        """
        self.model().sourceModel().set_job_style(style)

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_job(self):
        """
        Add a job.

        """
        node = self.get_node_from_selection()
        if not node:
            return

        if node.type != NodeType.ServerNode:
            return

        dialog = AddJobDialog(node.server, parent=self)
        dialog.open()


class ServerEditor(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.server_view = None

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight()
        )
