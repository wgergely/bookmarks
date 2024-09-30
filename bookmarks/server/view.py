import collections
import functools
import os
import re

from PySide2 import QtWidgets, QtCore

from .lib import ServerAPI, JobStyle
from .model import ServerModel, NodeType, Node, ServerFilterProxyModel
from .preview import DictionaryViewer
from .. import contextmenu, common, shortcuts, ui, actions
from ..editor import base
from ..editor.base_widgets import ThumbnailEditorWidget
from ..links.lib import LinksAPI
from ..templates.lib import TemplateItem, TemplateType
from ..templates.view import TemplatesEditor


class ServerContextMenu(contextmenu.BaseContextMenu):

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """

        self.add_root_folder_menu()
        self.remove_root_folder_menu()
        self.separator()
        self.add_job_menu()
        self.separator()
        self.add_server_menu()
        self.remove_server_menu()
        self.separator()
        self.set_job_style_menu()
        self.separator()
        self.add_reveal_menu()
        self.separator()
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

        if node.type == NodeType.ServerNode:
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

    def add_root_folder_menu(self):
        """Add the root folder menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if node.type == NodeType.JobNode:
            self.menu[contextmenu.key()] = {
                'text': 'Add Bookmark Folder...',
                'icon': ui.get_icon('add_link', color=common.Color.Green()),
                'action': self.parent().add_root_folder,
                'description': 'Add a root folder to the job folder\'s link file.'
            }

    def remove_root_folder_menu(self):
        """Remove the root folder menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if node.type == NodeType.BookmarkNode:
            self.menu[contextmenu.key()] = {
                'text': 'Remove Bookmark Folder...',
                'icon': ui.get_icon('remove_link', color=common.Color.Red()),
                'action': self.parent().remove_root_folder,
                'description': 'Remove a root folder from the job folder\'s link file.'
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

        self._value = None

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

        self._value = v

        super().done(r)

    def get_data(self):
        return self._value

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


class EditAssetTemplatesDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Edit Asset Templates')

        self._templates_editor = None
        self.ok_button = None
        self.cancel_button = None

        self._create_ui()
        self._connect_signals()

        QtCore.QTimer.singleShot(100, self._templates_editor.init_data)

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Indicator(6.0)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        self._templates_editor = TemplatesEditor(parent=self)
        self.layout().addWidget(self._templates_editor)

        row = ui.add_row(None, height=None, parent=self)

        self.ok_button = ui.PaintedButton('Save', parent=self)
        row.layout().addWidget(self.ok_button, 1)

        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        row.layout().addWidget(self.cancel_button)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)


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
        self.edit_asset_templates_button = None

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

        self.edit_asset_templates_button = ui.PaintedButton('Edit Templates', parent=self)
        row.layout().addWidget(self.edit_asset_templates_button)

        widget.layout().addStretch(10)

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

        self.edit_asset_templates_button.clicked.connect(self.edit_asset_templates)

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
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            return super().done(r)

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

            return super().done(r)

    @common.error
    @common.debug
    @QtCore.Slot()
    def edit_asset_templates(self):
        dialog = EditAssetTemplatesDialog(parent=self)
        dialog.open()


class ServerView(QtWidgets.QTreeView):
    jobStyleChanged = QtCore.Signal(int)
    bookmarkNodeSelected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Servers')

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        if not parent:
            common.set_stylesheet(self)

        self.setHeaderHidden(True)
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
        proxy = ServerFilterProxyModel(parent=self)
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

        self.selectionModel().selectionChanged.connect(self.emit_root_folder_selected)
        self.model().modelAboutToBeReset.connect(self.emit_root_folder_selected)
        self.model().layoutAboutToBeChanged.connect(self.emit_root_folder_selected)

        self.expanded.connect(self.restore_selected_node)
        self.model().modelReset.connect(self.restore_selected_node)
        self.model().layoutChanged.connect(self.restore_selected_node)

    @QtCore.Slot()
    def emit_root_folder_selected(self, *args, **kwargs):
        node = self.get_node_from_selection()
        if not node:
            self.bookmarkNodeSelected.emit('')
            return

        if node.type != NodeType.BookmarkNode:
            self.bookmarkNodeSelected.emit('')
            return

        self.bookmarkNodeSelected.emit(node.path())

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
        dialog.exec_()

        v = dialog.get_data()
        self.model().sourceModel().add_server(v)

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

        if node.is_bookmarked():
            raise ValueError('Cannot remove a bookmarked server. Remove all the bookmark items first.')
        self.model().sourceModel().remove_server(node.server)

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

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_root_folder(self):
        """
        Add a root folder to a job folder's link file.

        """
        node = self.get_node_from_selection()
        if not node:
            return

        if node.type != NodeType.JobNode:
            return

        abs_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select a root folder', node.path())
        if not abs_path:
            return
        if not os.path.exists(abs_path):
            raise ValueError(f'Path "{abs_path}" does not exist.')

        api = LinksAPI(node.path())
        rel_path = api.to_relative(abs_path)

        index = next(iter(self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return

        source_index = self.model().mapToSource(index)

        # Calculate row idx
        current_roots = [f.root for f in node.children()]
        all_roots = sorted(current_roots + [rel_path], key=str.lower)
        idx = all_roots.index(rel_path)

        self.model().sourceModel().beginInsertRows(source_index, idx, idx)
        api.add(rel_path)
        child_node = Node(node.server, job=node.job, root=rel_path, parent=node)
        node.insert_child(idx, child_node)
        self.model().sourceModel().endInsertRows()

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_root_folder(self):
        node = self.get_node_from_selection()
        if not node:
            return

        if node.type != NodeType.BookmarkNode:
            return

        if node.is_bookmarked:
            print(node.root)
            raise ValueError('Cannot remove a bookmarked root folder. Remove the bookmark first.')

        rel_path = node.root

        index = next(iter(self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return
        source_index = self.model().mapToSource(index)

        api = LinksAPI(node.parent().path())
        api.remove(rel_path)

        idx = node.parent().children().index(node)
        self.model().sourceModel().beginRemoveRows(source_index.parent(), idx, idx)
        node.parent().remove_child(idx)
        self.model().sourceModel().endRemoveRows()


class ServerEditor(QtWidgets.QSplitter):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        if not self.parent():
            common.set_stylesheet(self)

        self.filter_toolbar = None
        self.text_filter_editor = None
        self.server_view = None

        self.preview_widget = None

        self.ok_button = None

        self.setWindowTitle('Manage Servers and bookmarks')

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        widget = QtWidgets.QWidget(parent=self)
        widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        widget.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        QtWidgets.QVBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)

        self.filter_toolbar = QtWidgets.QToolBar('Filters', parent=self)
        self.filter_toolbar.setIconSize(QtCore.QSize(
            common.Size.Margin(1.0),
            common.Size.Margin(1.0)
        ))

        self.server_view = ServerView(parent=self)

        # Add action
        action = QtWidgets.QAction('Add', parent=self)
        action.setIcon(ui.get_icon('add', color=common.Color.Green()))
        action.setToolTip('Add a server, job, or bookmark folder.')
        action.triggered.connect(self.add)
        self.filter_toolbar.addAction(action)

        self.filter_toolbar.addSeparator()

        # Filters
        action_grp = QtWidgets.QActionGroup(self)
        action_grp.setExclusive(True)

        action = QtWidgets.QAction('Show All', parent=self)
        icon = ui.get_icon('archivedVisible')
        action.setIcon(icon)
        action.setCheckable(True)
        action.setChecked(True)
        action_grp.addAction(action)
        action.triggered.connect(self.server_view.model().reset_filters)
        self.filter_toolbar.addAction(action)

        action = QtWidgets.QAction('Show Bookmarked', parent=self)
        icon = ui.get_icon('bookmark')
        action.setIcon(icon)
        action.setToolTip('Show only bookmarked items.')
        action.setCheckable(True)
        action_grp.addAction(action)
        action.triggered.connect(self.server_view.model().set_show_bookmarked)
        self.filter_toolbar.addAction(action)

        action = QtWidgets.QAction('Hide Invalid', parent=self)
        icon = ui.get_icon('archivedHidden')
        action.setIcon(icon)
        action.setToolTip('Hide folders without any links or bookmark items')
        action.setCheckable(True)
        action_grp.addAction(action)
        action.triggered.connect(self.server_view.model().set_hide_non_candidates)
        self.filter_toolbar.addAction(action)

        button = QtWidgets.QToolButton(parent=self)
        button.setText('Job Style')
        icon = ui.get_icon('sort', color=common.Color.Yellow())
        button.setIcon(icon)
        button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(button)
        action_grp = QtWidgets.QActionGroup(self)
        action_grp.setExclusive(True)
        for style in JobStyle:
            name = style.name
            # split name by capital letters
            name_split = re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))', name)
            display_name = ' '.join(name_split)

            action = menu.addAction(display_name)
            action_grp.addAction(action)
            action.setCheckable(True)
            action.setChecked(common.settings.value(ServerAPI.job_style_settings_key) == style.value)
            action.triggered.connect(functools.partial(self.server_view.set_job_style, style))
        button.setMenu(menu)
        self.filter_toolbar.addWidget(button)

        self.text_filter_editor = ui.LineEdit(parent=self)
        self.text_filter_editor.setPlaceholderText('Search jobs...')
        self.text_filter_editor.textChanged.connect(self.server_view.model().set_text_filter)
        action = QtWidgets.QAction(self.text_filter_editor)
        icon = ui.get_icon('filter', color=common.Color.DisabledText())
        action.setIcon(icon)
        self.text_filter_editor.addAction(action, QtWidgets.QLineEdit.LeadingPosition)

        widget.layout().addWidget(self.filter_toolbar, 0)
        widget.layout().addWidget(self.text_filter_editor, 0)
        widget.layout().addWidget(self.server_view, 100)
        self.addWidget(widget)

        self.preview_widget = DictionaryViewer(parent=self)
        self.addWidget(self.preview_widget)

        self.setStretchFactor(0, 0.5)
        self.setStretchFactor(1, 0.5)

    @common.error
    @common.debug
    @QtCore.Slot()
    def add(self):
        """Add a server.

        """
        node = self.server_view.get_node_from_selection()
        if not node:
            self.server_view.add_server()
            return
        elif node.type == NodeType.ServerNode:
            self.server_view.add_job()
        elif node.type == NodeType.JobNode:
            self.server_view.add_root_folder()

    def _connect_signals(self):
        self.server_view.bookmarkNodeSelected.connect(self.preview_widget.bookmark_node_changed)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(2.0),
            common.Size.DefaultHeight(1.5)
        )
