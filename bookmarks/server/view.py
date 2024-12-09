import collections
import functools
import os
import re

from PySide2 import QtWidgets, QtCore

from .lib import ServerAPI, JobDepth
from .model import ServerModel, NodeType, Node, ServerFilterProxyModel
from .preview import DictionaryPreview
from .. import contextmenu, common, shortcuts, ui, actions
from ..editor import base
from ..editor.base_widgets import ThumbnailEditorWidget
from ..templates.lib import TemplateItem, TemplateType
from ..templates.view import TemplatesEditor


def show():
    """Show the server view.

    """
    if common.server_editor:
        close()

    if not isinstance(common.server_editor, ServerEditorDialog):
        common.server_editor = ServerEditorDialog()

    common.server_editor.open()
    return common.server_editor


def close():
    """Close the server view.

    """
    if not common.server_editor:
        return
    try:
        common.server_editor.close()
        common.server_editor.deleteLater()
    except:
        pass
    common.server_editor = None


class ServerContextMenu(contextmenu.BaseContextMenu):

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """

        self.bookmark_job_folder_menu()
        self.separator()
        self.add_link_menu()
        self.remove_link_menu()
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

    def add_link_menu(self):
        """Add the root folder menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if node.type == NodeType.JobNode:
            self.menu[contextmenu.key()] = {
                'text': 'Add Link...',
                'icon': ui.get_icon('add_link', color=common.Color.Green()),
                'action': self.parent().add_link,
                'description': 'Add a root folder to the job folder\'s link file.'
            }

    def bookmark_job_folder_menu(self):
        """Add the root folder menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if node.type == NodeType.BookmarkNode:
            self.menu[contextmenu.key()] = {
                'text': 'Bookmark Job Folder',
                'icon': ui.get_icon('add_link', color=common.Color.Green()),
                'action': self.parent().bookmark_job_folder,
                'description': 'Add a root folder to the job folder\'s link file.'
            }

    def remove_link_menu(self):
        """Remove the root folder menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if node.type == NodeType.BookmarkNode:
            self.menu[contextmenu.key()] = {
                'text': 'Remove Link',
                'action': self.parent().remove_link,
                'description': 'Remove a root folder from the job folder\'s link file.'
            }

    def set_job_style_menu(self):
        """Set the job style menu.

        """
        k = 'Job Style'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('icon_bw_sm')

        for style in JobDepth:
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
                'text': 'Remove server...',
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
            'text': 'Clear Servers',
            'icon': ui.get_icon('close'),
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

        servers = sorted({k.replace('\\', '/'): k for k in servers}.values())

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
        v = JobDepth(v) if isinstance(v, int) else JobDepth.NoParent.value
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
        if self.job_style == JobDepth.NoParent:
            self.client_row.hide()
            self.department_row.hide()
        elif self.job_style == JobDepth.HasParent:
            self.department_row.hide()
        elif self.job_style == JobDepth.HasGrandparent:
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
            with os.scandir(path) as it:
                for entry in it:
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

        if self.job_style == JobDepth.NoParent:
            values = sorted([f for f in _it(self._root_path, -1, 1)])
            _add_completer(self.job_editor, set(values))

        elif self.job_style == JobDepth.HasParent:
            values = sorted([f for f in _it(self._root_path, -1, 2)])
            client_values = [f.split('/')[0] for f in values if len(f.split('/')) >= 1]
            job_values = [f.split('/')[1] for f in values if len(f.split('/')) >= 2]

            _add_completer(self.client_editor, set(client_values))
            _add_completer(self.job_editor, set(job_values))

        elif self.job_style == JobDepth.HasGrandparent:
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

        if self.job_style == JobDepth.NoParent:
            if not jt:
                self.summary_label.setText(invalid_label)
                return
            summary = f'{summary}/{jt}'
        elif self.job_style == JobDepth.HasParent:
            if not all((ct, jt)):
                self.summary_label.setText(invalid_label)
                return
            summary = f'{summary}/{ct}/{jt}'
        elif self.job_style == JobDepth.HasGrandparent:
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
        ct = self.client_editor.text()
        dt = self.department_editor.text()

        if self.job_style == JobDepth.NoParent:
            if not jt:
                raise ValueError('Job name is required.')
            rel_path = jt
        elif self.job_style == JobDepth.HasParent:
            if not all((ct, jt)):
                raise ValueError('Client and job name are required.')
            rel_path = f'{ct}/{jt}'
        elif self.job_style == JobDepth.HasGrandparent:
            if not all((ct, jt, dt)):
                raise ValueError('Client, job, and department are required.')
            rel_path = f'{ct}/{jt}/{dt}'
        else:
            raise ValueError('Check the selected job style is valid.')

        path = f'{self._root_path}/{rel_path}'
        if os.path.exists(path):
            raise FileExistsError(f'Path "{path}" already exists.')
        os.makedirs(path)

        if self.asset_template_combobox.currentData():
            template = self.asset_template_combobox.currentData()
            template.extract_template(
                path,
                extract_contents_to_links=False,
                ignore_existing_folders=False
            )

        common.signals.jobAdded.emit(self._root_path, rel_path)

        return super().done(r)

    @common.error
    @common.debug
    @QtCore.Slot()
    def edit_asset_templates(self):
        dialog = EditAssetTemplatesDialog(parent=self)
        dialog.open()


class ServerView(QtWidgets.QTreeView):
    JobDepthChanged = QtCore.Signal(int)
    bookmarkNodeSelected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Servers')

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        # Enable dragging
        self.setDragEnabled(True)
        self.setWordWrap(False)

        if not parent:
            common.set_stylesheet(self)

        self.setHeaderHidden(False)
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
        connect(shortcuts.AddBookmark, self.bookmark_job_folder)
        connect(shortcuts.RevealServer, self.reveal)
        connect(shortcuts.ReloadServers, self.init_data)

    def _init_model(self):
        proxy = ServerFilterProxyModel(parent=self)
        proxy.setSourceModel(ServerModel(parent=self))
        self.setModel(proxy)

        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.header().setCascadingSectionResizes(True)

        self.resize_to_contents()

    def _connect_signals(self):
        self.expanded.connect(self.add_expanded)
        self.collapsed.connect(self.remove_expanded)

        self.expanded.connect(self.model().invalidateFilter)
        self.model().sourceModel().dataChanged.connect(self.model().invalidateFilter)
        self.model().dataChanged.connect(lambda x, y: self.expand(x))

        self.model().sourceModel().rowsInserted.connect(self.restore_expanded_nodes)

        self.expanded.connect(self.resize_to_contents)
        self.collapsed.connect(self.resize_to_contents)

        self.selectionModel().selectionChanged.connect(self.save_selected_node)
        self.model().modelAboutToBeReset.connect(self.save_selected_node)
        self.model().sourceModel().rowsAboutToBeInserted.connect(self.save_selected_node)

        self.model().modelAboutToBeReset.connect(self.save_expanded_nodes)

        self.model().modelReset.connect(self.restore_expanded_nodes)
        self.model().modelReset.connect(self.restore_selected_node)

        self.selectionModel().selectionChanged.connect(self.emit_root_folder_selected)
        self.model().modelAboutToBeReset.connect(self.emit_root_folder_selected)

        common.signals.jobAdded.connect(self.on_job_added)
        common.signals.bookmarksChanged.connect(self.init_data)

    @QtCore.Slot()
    def resize_to_contents(self, *args, **kwargs):
        metrics = self.fontMetrics()

        def _get_longest_name(section):
            def _it(parent_index, width):
                for i in range(self.model().sourceModel().rowCount(parent_index)):

                    child_index = self.model().sourceModel().index(i, section, parent_index)

                    name = child_index.data(QtCore.Qt.DisplayRole)
                    if metrics.horizontalAdvance(name) >= width:
                        width = metrics.horizontalAdvance(name)
                    width = _it(child_index, width)
                return width

            index = self.model().sourceModel().index(0, 0, QtCore.QModelIndex())
            return _it(index, 0)

        width = _get_longest_name(1)
        print(width)
        self.header().resizeSection(1, width * 20.0)

    @QtCore.Slot(str, str)
    def on_job_added(self, server, job):
        """Handle the job added signal.

        """
        self.init_data()

        model = self.model().sourceModel()

        def _it(parent_index):
            for i in range(model.rowCount(parent_index)):
                _index = model.index(i, 0, parent_index)
                if not _index.isValid():
                    continue
                node = _index.internalPointer()
                if not node:
                    continue
                index = self.model().mapFromSource(_index)
                if node.server == server:
                    node.children_fetched = False
                    model.fetchMore(_index)
                    if model.hasChildren(_index):
                        self.expand(index)

                if node.server == server and node.job == job:
                    self.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)
                    self.setCurrentIndex(index)
                    if model.hasChildren(_index):
                        self.expand(index)
                    return

                _it(_index)

        _it(self.rootIndex())

    @QtCore.Slot(str, str, str)
    def on_link_added(self, server, job, root):

        model = self.model().sourceModel()

        def _it(parent_index):
            for i in range(model.rowCount(parent_index)):
                _index = model.index(i, 0, parent_index)
                if not _index.isValid():
                    continue
                node = _index.internalPointer()
                if not node:
                    continue

                index = self.model().mapFromSource(_index)
                if node.server == server:
                    node.children_fetched = False
                    model.fetchMore(_index)
                    if model.hasChildren(_index):
                        self.expand(index)

                if node.server == server and node.job == job:
                    node.children_fetched = False
                    model.fetchMore(_index)
                    if model.hasChildren(_index):
                        self.expand(index)

                if node.server == server and node.job == job and node.root == root:
                    self.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)
                    self.setCurrentIndex(index)
                    self.scrollTo(index)
                    return

                _it(_index)

        _it(self.rootIndex())

    def contextMenuEvent(self, event):
        """Context menu event.

        """
        index = self.indexAt(event.pos())
        source_index = self.model().mapToSource(index)
        persistent_index = QtCore.QPersistentModelIndex(source_index)

        menu = ServerContextMenu(persistent_index, parent=self)
        menu.move(event.globalPos())
        menu.exec_()

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight()
        )

    def mouseDoubleClickEvent(self, event):
        node = self.get_node_from_selection()
        if not node:
            return super().mouseDoubleClickEvent(event)

        if not node.type == NodeType.BookmarkNode:
            return super().mouseDoubleClickEvent(event)

        event.accept()
        self.bookmark_job_folder()

    def add_expanded(self, index):
        if not index.isValid():
            return
        source_index = self.model().mapToSource(index)
        node = source_index.internalPointer()
        if not node:
            return
        if node.path() in self._expanded_nodes:
            return
        self._expanded_nodes.append(node.path())

    def remove_expanded(self, index):
        if not index.isValid():
            return
        source_index = self.model().mapToSource(index)
        node = source_index.internalPointer()
        if not node:
            return

        idx = self._expanded_nodes.index(node.path())
        if idx != -1:
            self._expanded_nodes.pop(idx)

    @QtCore.Slot()
    def save_expanded_nodes(self):
        """
        Save the expanded nodes.

        """
        self._expanded_nodes = []

        def _it(parent_index):
            model = self.model().sourceModel()
            for i in range(model.rowCount(parent_index)):
                index = model.index(i, 0, parent_index)
                node = index.internalPointer()
                if not node:
                    continue

                if self.isExpanded(self.model().mapFromSource(index)):
                    self._expanded_nodes.append(node.path())
                _it(index)

        _it(QtCore.QModelIndex())

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

    def get_node_from_selection(self):
        """
        Get the internal node from the current selection.

        """
        if not self.selectionModel().hasSelection():
            return None

        index = next((f for f in self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return None

        node = self.model().mapToSource(index).internalPointer()
        if not node:
            return None

        return node

    @QtCore.Slot()
    def restore_expanded_nodes(self, *args, **kwargs):
        """
        Restore the expanded nodes.

        """
        if not self._expanded_nodes:
            return

        model = self.model().sourceModel()

        def _it(parent_index):
            for i in range(model.rowCount(parent_index)):
                _index = model.index(i, 0, parent_index)
                if not _index.isValid():
                    continue
                yield _index
                yield from _it(_index)

        for source_index in _it(self.rootIndex()):
            node = source_index.internalPointer()
            if not node:
                continue

            index = self.model().mapFromSource(source_index)
            if not index.isValid():
                continue

            if node.path() in self._expanded_nodes:
                if model.hasChildren(source_index):
                    self.expand(index)

    @QtCore.Slot()
    def save_selected_node(self, *args, **kwargs):
        """
        Save the selected node.

        """
        if not self.model() or not self.model().sourceModel():
            return

        node = self.get_node_from_selection()
        if not node:
            return

        self._selected_node = node.path()

    @QtCore.Slot()
    def restore_selected_node(self, *args, **kwargs):
        if not self._selected_node:
            return

        # Start from the root and expand nodes recursively to load data
        def _expand_and_find(parent_index):
            model = self.model().sourceModel()
            for i in range(model.rowCount(parent_index)):
                index = model.index(i, 0, parent_index)
                node = index.internalPointer()
                if not node:
                    continue

                # Expand the node to trigger data loading
                proxy_index = self.model().mapFromSource(index)
                if not proxy_index.isValid():
                    continue

                model.fetchMore(index)
                if model.hasChildren(index):
                    self.expand(proxy_index)

                if node.path() == self._selected_node:
                    self.selectionModel().select(proxy_index, QtCore.QItemSelectionModel.ClearAndSelect)
                    self.setCurrentIndex(proxy_index)
                    return True

                if _expand_and_find(index):
                    return True

            return False

        # Start the recursive search from the root index
        _expand_and_find(QtCore.QModelIndex())

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_server(self):
        """Add a server.

        """
        dialog = AddServerDialog(parent=self)
        dialog.exec_()

        v = dialog.get_data()
        if not v:
            return
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

        self.model().sourceModel().remove_servers()

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
    def add_link(self):
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

        index = next(iter(self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return
        source_index = self.model().mapToSource(index)
        if not source_index.isValid():
            return

        # Calculate row idx
        rel_path = abs_path.replace(f'{node.server}/{node.job}', '').strip('/')
        current_roots = [f.root for f in node.children()]
        all_roots = sorted(current_roots + [rel_path], key=lambda s: s.lower())
        idx = all_roots.index(rel_path)

        self.model().sourceModel().beginInsertRows(source_index, idx, idx)
        node.api().add_link(node.server, node.job, rel_path)
        child_node = Node(node.server, job=node.job, root=rel_path, parent=node)
        node.insert_child(idx, child_node)
        self.model().sourceModel().endInsertRows()

        self.on_link_added(node.server, node.job, rel_path)

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_link(self):
        node = self.get_node_from_selection()
        if not node:
            return

        if node.type != NodeType.BookmarkNode:
            return

        if node.is_bookmarked():
            raise ValueError('Cannot remove a bookmarked root folder. Remove the bookmark first.')

        index = next(iter(self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return
        source_index = self.model().mapToSource(index)
        if not source_index.isValid():
            return

        node.api().remove_link(node.server, node.job, node.root)

        idx = node.parent().children().index(node, )
        self.model().sourceModel().beginRemoveRows(source_index.parent(), idx, idx)
        node.parent().remove_child(idx)
        self.model().sourceModel().endRemoveRows()

    @common.error
    @common.debug
    @QtCore.Slot()
    def bookmark_job_folder(self):
        node = self.get_node_from_selection()
        if not node:
            return

        if node.type != NodeType.BookmarkNode:
            return

        node.api().bookmark_job_folder(
            node.server,
            node.job,
            node.root
        )


class ServerEditor(QtWidgets.QSplitter):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        if not self.parent():
            common.set_stylesheet(self)

        self.filter_toolbar = None
        self.text_filter_editor = None
        self.server_view = None

        self.preview_widget = None

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
        action.triggered.connect(self.server_view.expandAll)
        self.filter_toolbar.addAction(action)

        action = QtWidgets.QAction('Show Linked Folders', parent=self)
        icon = ui.get_icon('link')
        action.setIcon(icon)
        action.setToolTip('Show Linked Folders')
        action.setCheckable(True)
        action_grp.addAction(action)
        action.triggered.connect(self.server_view.model().set_hide_non_candidates)
        action.triggered.connect(self.server_view.expandAll)
        self.filter_toolbar.addAction(action)

        self.filter_toolbar.addSeparator()

        button = QtWidgets.QToolButton(parent=self)
        button.setText('Job Style')
        icon = ui.get_icon('sort', color=common.Color.Yellow())
        button.setIcon(icon)
        button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(button)
        action_grp = QtWidgets.QActionGroup(self)
        action_grp.setExclusive(True)
        for style in JobDepth:
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

        self.preview_widget = DictionaryPreview(parent=self)
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
            self.server_view.add_link()

    def _connect_signals(self):
        self.server_view.bookmarkNodeSelected.connect(self.preview_widget.bookmark_node_changed)
        self.preview_widget.selectionChanged.connect(self.server_view.on_link_added)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(2.0),
            common.Size.DefaultHeight(1.5)
        )


class ServerEditorDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Manage Servers, Jobs, and Bookmarks')

        self.server_editor = None
        self.ok_button = None
        self.cancel_button = None

        if not self.parent():
            common.set_stylesheet(self)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Indicator(2.0)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        self.server_editor = ServerEditor(parent=self)
        self.layout().addWidget(self.server_editor, 100)

        row = ui.add_row(None, height=None, parent=self)

        self.ok_button = ui.PaintedButton('Done', parent=self)
        row.layout().addWidget(self.ok_button, 1)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
