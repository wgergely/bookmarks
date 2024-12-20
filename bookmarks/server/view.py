"""
This module implements a Server Editor dialog and related widgets that provide
a tree view and context menu for managing servers, jobs, and links.

"""

import collections
import functools
import os
import re

from PySide2 import QtWidgets, QtCore, QtGui

from .activebookmarks import ActiveBookmarksWidget
from .lib import ServerAPI, JobDepth
from .model import ServerModel, NodeType, Node, ServerFilterProxyModel
from .. import contextmenu, common, shortcuts, ui, actions, log
from ..editor import base
from ..editor.base_widgets import ThumbnailEditorWidget
from ..templates.lib import TemplateType, get_saved_templates
from ..templates.view import TemplatesEditor


def show():
    """Show :class:`ServerEditorDialog`."""
    if common.server_editor:
        close()

    if not isinstance(common.server_editor, ServerEditorDialog):
        common.server_editor = ServerEditorDialog()

    common.server_editor.open()
    return common.server_editor


def close():
    """Close the :class:`ServerEditorDialog`."""
    if not common.server_editor:
        return
    try:
        common.server_editor.close()
        common.server_editor.deleteLater()
    except:
        pass
    common.server_editor = None


class ServerContextMenu(contextmenu.BaseContextMenu):
    """Context menu of :class:`ServerView`."""

    @common.error
    @common.debug
    def setup(self):
        node = None
        if self.index.isValid():
            node = self.index.internalPointer()

        if not self.index.isValid():
            self.separator()
            self.add_server_menu()
        elif node and node.type == NodeType.ServerNode:
            self.separator()
            self.add_job_menu()
        elif node and node.type == NodeType.JobNode:
            self.separator()
            self.add_link_menu()
            self.separator()
            self.add_links_copy_paste_actions()
        elif node and node.type == NodeType.LinkNode:
            self.bookmark_link_menu()
            self.remove_link_menu()

        self.separator()

        self.create_link_folder_menu()
        self.create_all_link_folders_menu()

        self.separator()

        if self.index.isValid():
            self.add_server_menu()

        self.remove_server_menu()
        self.set_job_style_menu()
        self.add_reveal_menu()

        self.separator()

        self.add_view_menu()

        self.separator()
        self.add_refresh_menu()

    def add_links_copy_paste_actions(self):
        """
        Add actions similar to the links module for copying, pasting, and manipulating links.
        """
        self.menu[contextmenu.key()] = {
            'text': 'Copy Links',
            'icon': ui.get_icon('link'),
            'action': self.parent().copy_links,
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.CopyLinks
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.CopyLinks
            )
        }

        self.menu[contextmenu.key()] = {
            'text': 'Paste Links',
            'icon': ui.get_icon('add_link'),
            'action': self.parent().paste_links,
            'disabled': not common.get_clipboard(common.AssetLinksClipboard),
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.PasteLinks
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.PasteLinks
            )
        }

        self.separator()

        self.menu[contextmenu.key()] = {
            'text': 'Remove links',
            'icon': ui.get_icon('remove_link', color=common.Color.Red()),
            'action': self.parent().clear_links,
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.RemoveLink
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.RemoveLink
            )
        }

        self.menu[contextmenu.key()] = {
            'text': 'Remove missing',
            'action': self.parent().prune_links,
            'description': 'Remove links that do not point to existing folders.'
        }

    def add_server_menu(self):
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
        if not self.index.isValid():
            return
        node = self.index.internalPointer()
        if not node or node.type != NodeType.ServerNode:
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

    def add_link_menu(self):
        if not self.index.isValid():
            return
        node = self.index.internalPointer()
        if not node or node.type != NodeType.JobNode:
            return
        self.menu[contextmenu.key()] = {
            'text': 'Add Link...',
            'icon': ui.get_icon('add_link', color=common.Color.Green()),
            'action': self.parent().add_link,
            'description': 'Add a root folder to the job folder\'s link file.'
        }

    def bookmark_link_menu(self):
        if not self.index.isValid():
            return
        node = self.index.internalPointer()
        if node and node.type == NodeType.LinkNode:
            if node.is_bookmarked():
                self.menu[contextmenu.key()] = {
                    'text': 'Remove Bookmark',
                    'icon': ui.get_icon('bookmark', color=common.Color.Red()),
                    'action': self.parent().unbookmark_link,
                    'description': 'Remove the link from the bookmarks.'
                }
            else:
                self.menu[contextmenu.key()] = {
                    'text': 'Bookmark Link',
                    'icon': ui.get_icon('add_link', color=common.Color.Green()),
                    'action': self.parent().bookmark_link,
                    'description': 'Add a root folder to the job folder\'s link file.'
                }

        self.separator()

    def remove_link_menu(self):
        if not self.index.isValid():
            return
        node = self.index.internalPointer()
        if node and node.type == NodeType.LinkNode:
            self.menu[contextmenu.key()] = {
                'text': 'Remove Link',
                'action': self.parent().remove_link,
                'description': 'Remove a root folder from the job folder\'s link file.'
            }

    def set_job_style_menu(self):
        k = 'Job Style'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('icon_bw_sm')

        for style in JobDepth:
            name = style.name
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
        if not self.index.isValid():
            return
        node = self.index.internalPointer()
        if node and os.path.exists(node.path()):
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
        node = self.parent().get_node_from_selection()
        if node and node.type in (NodeType.ServerNode, NodeType.RootNode):
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

        # Clear servers
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

        self.separator()

    def add_view_menu(self):
        self.menu[contextmenu.key()] = {
            'text': 'Expand All',
            'icon': ui.get_icon('expand'),
            'action': self.parent().expandAll,
            'help': 'Expand all items.',
        }
        self.menu[contextmenu.key()] = {
            'text': 'Collapse All',
            'icon': ui.get_icon('collapse'),
            'action': self.parent().collapseAll,
            'help': 'Collapse all items.',
        }

    def add_refresh_menu(self):
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

    def create_link_folder_menu(self):
        node = self.index.internalPointer()
        if not node or node.type != NodeType.LinkNode:
            return

        if node.exists(force=True):
            return

        self.menu[contextmenu.key()] = {
            'text': 'Create Folder',
            'icon': ui.get_icon('add_folder'),
            'action': self.parent().create_link_folder,
            'description': 'Create folder'
        }

    def create_all_link_folders_menu(self):
        node = self.index.internalPointer()
        if not node or node.type == NodeType.ServerNode:
            return

        if not node.children():
            return

        self.menu[contextmenu.key()] = {
            'text': 'Create All Folders',
            'icon': ui.get_icon('add_folder', color=common.Color.Green()),
            'action': self.parent().create_all_link_folders,
            'description': 'Create all folders'
        }


class AddServerDialog(QtWidgets.QDialog):
    """Dialog to add a new server path."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Add Server')
        self.name_editor = None
        self.ok_button = None
        self.cancel_button = None
        self._value = None

        self._init_ui()
        self._connect_signals()
        QtCore.QTimer.singleShot(100, self._init_completer)

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
        _saved_servers = ServerAPI.get_servers() or {}
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
        self.name_editor.actions()[-2].triggered.connect(self.name_editor.completer().complete)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight(0.1)
        )


class AddJobDialog(QtWidgets.QDialog):
    """Dialog to add a new job under a server."""

    def __init__(self, root_path, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Add Job')
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Maximum)

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
        v = JobDepth(v) if isinstance(v, int) else JobDepth.Job.value
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
        row = ui.add_row(None, height=None, parent=grp)
        self.template_editor = TemplatesEditor(mode=TemplateType.UserTemplate, parent=self)
        self.template_editor.setVisible(False)
        row.layout().addWidget(self.template_editor)
        widget.layout().addStretch(10)
        row = ui.add_row(None, height=None, parent=widget)
        self.ok_button = ui.PaintedButton('Add', parent=self)
        row.layout().addWidget(self.ok_button, 1)
        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        row.layout().addWidget(self.cancel_button)
        self.layout().addWidget(widget, 1)

    def _apply_job_style(self):
        if self.job_style == JobDepth.Job:
            self.client_row.hide()
            self.department_row.hide()
        elif self.job_style == JobDepth.ClientAndJob:
            self.department_row.hide()
        elif self.job_style == JobDepth.ClientJobAndDepartment:
            pass

    def _init_templates(self):
        self.template_editor.init_data()
        templates = get_saved_templates(TemplateType.UserTemplate)
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

        if self.job_style == JobDepth.Job:
            values = sorted([f for f in _it(self._root_path, -1, 1)])
            _add_completer(self.job_editor, set(values))
        elif self.job_style == JobDepth.ClientAndJob:
            values = sorted([f for f in _it(self._root_path, -1, 2)])
            client_values = [f.split('/')[0] for f in values if len(f.split('/')) >= 1]
            job_values = [f.split('/')[1] for f in values if len(f.split('/')) >= 2]
            _add_completer(self.client_editor, set(client_values))
            _add_completer(self.job_editor, set(job_values))
        elif self.job_style == JobDepth.ClientJobAndDepartment:
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

        if self.job_style == JobDepth.Job:
            if not jt:
                self.summary_label.setText(invalid_label)
                return
            summary = f'{summary}/{jt}'
        elif self.job_style == JobDepth.ClientAndJob:
            if not all((ct, jt)):
                self.summary_label.setText(invalid_label)
                return
            summary = f'{summary}/{ct}/{jt}'
        elif self.job_style == JobDepth.ClientJobAndDepartment:
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
        if self.job_style == JobDepth.Job:
            if not jt:
                raise ValueError('Job name is required.')
            rel_path = jt
        elif self.job_style == JobDepth.ClientAndJob:
            if not all((ct, jt)):
                raise ValueError('Client and job name are required.')
            rel_path = f'{ct}/{jt}'
        elif self.job_style == JobDepth.ClientJobAndDepartment:
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
            template.template_to_folder(
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
        self.template_editor.setVisible(self.template_editor.isHidden())


class ServerView(QtWidgets.QTreeView):
    """A QTreeView that shows servers, jobs, and links, with added actions like add/remove."""
    JobDepthChanged = QtCore.Signal(int)
    bookmarkNodeSelected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Servers')
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setWordWrap(False)

        self.resize_timer = common.Timer(parent=self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(100)
        self.resize_timer.timeout.connect(self.resize_to_contents)

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
        connect = functools.partial(shortcuts.connect, shortcuts.ServerViewShortcuts)
        connect(shortcuts.AddServer, self.add_server)
        connect(shortcuts.RemoveServer, self.remove_server)
        connect(shortcuts.RemoveAllServers, self.remove_all_servers)
        connect(shortcuts.AddJob, self.add_job)
        connect(shortcuts.AddBookmark, self.bookmark_link)
        connect(shortcuts.RevealServer, self.reveal)
        connect(shortcuts.ReloadServers, self.init_data)
        connect(shortcuts.CopyLinks, self.copy_links)
        connect(shortcuts.PasteLinks, self.paste_links)
        connect(shortcuts.RemoveLink, self.clear_links)

    def _init_model(self):
        proxy = ServerFilterProxyModel(parent=self)
        proxy.setSourceModel(ServerModel(parent=self))
        self.setModel(proxy)
        self.header().setStretchLastSection(True)
        self.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        self.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        self.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Interactive)
        self.header().setMinimumSectionSize(common.Size.Margin(2.0))
        self.header().setSectionsMovable(False)

    def _connect_signals(self):
        self.expanded.connect(self.on_expanded)
        self.expanded.connect(self.start_resize_timer)

        self.collapsed.connect(self.on_collapsed)
        self.collapsed.connect(self.start_resize_timer)

        self.model().sourceModel().dataChanged.connect(self.model().invalidateFilter)

        self.model().modelReset.connect(self.start_resize_timer)
        self.model().layoutChanged.connect(self.start_resize_timer)

        self.model().modelReset.connect(self.restore_expanded_nodes)
        self.model().modelReset.connect(self.restore_selection)

        self.selectionModel().selectionChanged.connect(self.save_selection)
        self.selectionModel().selectionChanged.connect(self.emit_link_selected)

        common.signals.jobAdded.connect(self.on_job_added)
        common.signals.bookmarksChanged.connect(self.viewport().update)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.start_resize_timer()

    @QtCore.Slot()
    def start_resize_timer(self):
        self.resize_timer.start(self.resize_timer.interval())

    @QtCore.Slot()
    def resize_to_contents(self, *args, **kwargs):
        max_section_width = self.rect().width() - common.Size.Margin(1.0)
        self.header().setMaximumSectionSize(max_section_width)
        fonts = {
            0: self.model().data(self.model().index(0, 0), QtCore.Qt.FontRole),
            1: self.model().data(self.model().index(0, 1), QtCore.Qt.FontRole),
            2: self.model().data(self.model().index(0, 2), QtCore.Qt.FontRole),
        }
        _metrics = {k: QtGui.QFontMetrics(v) for k, v in fonts.items()}
        for column in range(self.model().columnCount()):
            max_width = 0
            metrics = _metrics[column]
            server_indexes = [self.model().index(i, column) for i in range(self.model().rowCount()) if
                              self.model().index(i, 0).isValid()]
            _max_width = [metrics.width(self.model().data(i, QtCore.Qt.DisplayRole)) for i in server_indexes]
            _max_width = max(_max_width) if _max_width else 0
            if column == 0:
                max_width = max(max_width, _max_width + common.Size.Margin(1.0))
            else:
                max_width = max(max_width, _max_width)
            for server_index in server_indexes:
                count = self.model().rowCount(server_index)
                job_indexes = [self.model().index(i, column, server_index) for i in range(count) if
                               self.model().index(i, 0, server_index).isValid() and self.isExpanded(server_index)]
                _max_width = [metrics.width(self.model().data(i, QtCore.Qt.DisplayRole)) for i in job_indexes]
                _max_width = max(_max_width) if _max_width else 0
                if column == 0 or column == 1:
                    max_width = max(max_width, _max_width + common.Size.Margin(1.0))
                else:
                    max_width = max(max_width, _max_width)
                for job_index in job_indexes:
                    count = self.model().rowCount(job_index)
                    link_indexes = [self.model().index(i, column, job_index) for i in range(count) if
                                    self.model().index(i, 0, job_index).isValid() and self.isExpanded(job_index)]
                    _max_width = [metrics.width(self.model().data(i, QtCore.Qt.DisplayRole)) for i in link_indexes]
                    _max_width = max(_max_width) if _max_width else 0
                    if column == 0 or column == 1:
                        max_width = max(max_width, _max_width + common.Size.Margin(1.0))
                    else:
                        max_width = max(max_width, _max_width)
            max_width += common.Size.Margin(1.0)
            max_width += common.Size.Indicator(4.0)
            if column == 0 or column == 1:
                max_width += common.Size.Margin(2.0)
            self.setColumnWidth(column, max_width)

    @QtCore.Slot(str, str)
    def on_job_added(self, server, job):
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
                if not index.isValid():
                    continue
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

    @QtCore.Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def link_selected(self, selected, deselected):
        if not selected.indexes():
            return

        index = next(iter(selected.indexes()), QtCore.QModelIndex())
        if not index.isValid():
            return

        path = index.data(QtCore.Qt.DisplayRole)
        model = self.model().sourceModel()

        def _it(parent_index):
            for i in range(model.rowCount(parent_index)):
                _index = model.index(i, 0, parent_index)
                if not _index.isValid():
                    continue
                node = _index.internalPointer()
                if not node:
                    continue
                if node.path() == path:
                    self.selectionModel().select(self.model().mapFromSource(_index),
                                                 QtCore.QItemSelectionModel.ClearAndSelect)
                    self.setCurrentIndex(self.model().mapFromSource(_index))
                    return
                _it(_index)

        _it(self.rootIndex())

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        source_index = self.model().mapToSource(index)
        persistent_index = QtCore.QPersistentModelIndex(source_index)
        menu = ServerContextMenu(persistent_index, parent=self)
        menu.move(event.globalPos())
        menu.exec_()

    def mouseDoubleClickEvent(self, event):
        node = self.get_node_from_selection()
        if not node:
            return super().mouseDoubleClickEvent(event)
        if node.type != NodeType.LinkNode:
            return super().mouseDoubleClickEvent(event)

        event.accept()
        if node.is_bookmarked():
            self.unbookmark_link()
        else:
            self.bookmark_link()

    def add_expanded(self, index):
        if not index.isValid():
            return
        source_index = self.model().mapToSource(index)
        if not source_index.isValid():
            return
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
        if not source_index.isValid():
            return
        node = source_index.internalPointer()
        if not node:
            return
        if node.path() in self._expanded_nodes:
            self._expanded_nodes.remove(node.path())

    @QtCore.Slot(QtCore.QModelIndex)
    def on_expanded(self, index):
        if not index.isValid():
            return
        source_index = self.model().mapToSource(index)
        if not source_index.isValid():
            return
        node = source_index.internalPointer()
        if not node:
            return

        path = node.path()
        self._expanded_nodes.append(path)
        self._expanded_nodes = list(set(self._expanded_nodes))

    @QtCore.Slot(QtCore.QModelIndex)
    def on_collapsed(self, index):
        if not index.isValid():
            return
        source_index = self.model().mapToSource(index)
        if not source_index.isValid():
            return
        node = source_index.internalPointer()
        if not node:
            return

        path = node.path()
        if path in self._expanded_nodes:
            self._expanded_nodes.remove(path)

        self._expanded_nodes = list(set(self._expanded_nodes))

    @QtCore.Slot()
    def emit_link_selected(self, *args, **kwargs):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.LinkNode:
            self.bookmarkNodeSelected.emit('')
            return
        self.bookmarkNodeSelected.emit(node.path())

    def get_node_from_selection(self):
        if not self.selectionModel().hasSelection():
            return None
        index = next((f for f in self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return None
        source_index = self.model().mapToSource(index)
        if not source_index.isValid():
            return None
        node = source_index.internalPointer()
        return node

    @QtCore.Slot()
    def restore_expanded_nodes(self, *args, **kwargs):
        QtCore.QTimer.singleShot(100, self._restore_expanded_nodes)

    def _restore_expanded_nodes(self):
        model = self.model().sourceModel()

        def _it(index):
            for i in range(model.rowCount(index)):
                _index = model.index(i, 0, index)
                if not _index.isValid():
                    continue
                node = _index.internalPointer()
                if not node:
                    continue
                if node.path() in self._expanded_nodes:
                    self.expand(self.model().mapFromSource(_index))
                _it(_index)

        _it(QtCore.QModelIndex())

    @QtCore.Slot()
    def save_selection(self, *args, **kwargs):
        node = self.get_node_from_selection()
        self._selected_node = node.path() if node else None

    @QtCore.Slot()
    def restore_selection(self, *args, **kwargs):
        QtCore.QTimer.singleShot(150, self._restore_selected_node)

    def _restore_selected_node(self):
        model = self.model().sourceModel()

        def _it(index):
            for i in range(model.rowCount(index)):
                _index = model.index(i, 0, index)
                if not _index.isValid():
                    continue
                node = _index.internalPointer()
                if not node:
                    continue
                if node.path() == self._selected_node:
                    self.selectionModel().select(self.model().mapFromSource(_index),
                                                 QtCore.QItemSelectionModel.ClearAndSelect)
                    self.setCurrentIndex(self.model().mapFromSource(_index))
                    return
                _it(_index)

        _it(QtCore.QModelIndex())

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_server(self):
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
        QtCore.QTimer.singleShot(100, self.model().sourceModel().init_data)

    @common.error
    @common.debug
    @QtCore.Slot()
    def reveal(self):
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
        self.model().sourceModel().set_job_style(style)

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_job(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.ServerNode:
            return
        dialog = AddJobDialog(node.server, parent=self)
        dialog.open()

    @common.error
    @common.debug
    @QtCore.Slot()
    def bookmark_link(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.LinkNode:
            return
        node.api().bookmark_link(node.server, node.job, node.root)

    @common.error
    @common.debug
    @QtCore.Slot()
    def unbookmark_link(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.LinkNode:
            return
        node.api().unbookmark_link(node.server, node.job, node.root)

    @QtCore.Slot()
    def add_link(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.JobNode:
            return
        abs_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select a link', node.path())
        if not abs_path:
            return

        abs_path = abs_path.replace('\\', '/').rstrip('/')
        rel_path = abs_path.replace(os.path.join(node.server, node.job).replace('\\', '/').strip('/'), '').strip('/')
        node.api().add_link(node.server, node.job, rel_path)  # Modify data in backend/API

        self.model().sourceModel().add_link_to_job(node, rel_path)

    @QtCore.Slot()
    def remove_link(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.LinkNode:
            return
        if node.is_bookmarked():
            raise ValueError('Can\'t remove a bookmarked link.')

        node.api().remove_link(node.server, node.job, node.root)  # Backend removal

        self.model().sourceModel().remove_link_from_job(node)

    @common.error
    @common.debug
    @QtCore.Slot()
    def copy_links(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.JobNode:
            return
        node.links_api().copy_to_clipboard()

    @common.error
    @common.debug
    @QtCore.Slot()
    def paste_links(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.JobNode:
            return

        index = next(iter(self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return

        old_links = [f.root for f in node.children()]

        skipped = node.links_api().paste_from_clipboard()
        if skipped:
            log.warning(__name__, f'Skipped {len(skipped)} item(s): {", ".join(skipped)}')

        source_index = self.model().mapToSource(index)

        current_links = node.links_api().get(force=True)
        new_links = set(current_links) - set(old_links)

        for link in new_links:
            idx = current_links.index(link)

            self.model().sourceModel().beginInsertRows(source_index, idx, idx)
            child_node = Node(node.server, job=node.job, root=link, parent=node)
            node.insert_child(idx, child_node)
            self.model().sourceModel().endInsertRows()

    @QtCore.Slot()
    def clear_links(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.JobNode:
            return
        if common.show_message(
                'Remove links',
                body='Are you sure you want to remove all links from this job?',
                buttons=[common.YesButton, common.NoButton], modal=True, message_type='error'
        ) == QtWidgets.QDialog.Rejected:
            return

        node.links_api().clear()
        self.model().sourceModel().clear_links_from_job(node)

    @QtCore.Slot()
    def prune_links(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.JobNode:
            return
        if common.show_message(
                'Prune Links',
                body='This will remove all invalid links. Continue?',
                buttons=[common.YesButton, common.NoButton], modal=True
        ) == QtWidgets.QDialog.Rejected:
            return

        removed = node.links_api().prune()
        if removed:
            self.model().sourceModel().prune_links_in_job(node, removed)

    @common.error
    @common.debug
    @QtCore.Slot()
    def create_link_folder(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.LinkNode:
            return

        path = node.path()
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            log.info(__name__, f'Created link folder: {path}')
            node.exists(force=True)
        else:
            log.warning(__name__, f'Link folder already exists: {path}')

    @common.error
    @common.debug
    @QtCore.Slot()
    def create_all_link_folders(self):
        node = self.get_node_from_selection()
        if not node or node.type != NodeType.JobNode:
            return

        for link in node.children():
            path = link.path()
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                log.info(__name__, f'Created link folder: {path}')
                link.exists(force=True)
            else:
                log.warning(__name__, f'Link folder already exists: {path}')


class ProgressBar(QtWidgets.QWidget):
    """A simple progress bar widget."""
    showProgress = QtCore.Signal()
    progress = QtCore.Signal(str)
    hideProgress = QtCore.Signal()

    def __init__(self, show_msg=False, nth=171, parent=None):
        super().__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        if not show_msg:
            self.setFixedHeight(common.Size.Indicator(1.0))
        else:
            self.setFixedHeight(common.Size.Margin(1.0))
        self._show_msg = show_msg
        self._nth = nth
        self._progress = 0
        self._message = ''

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        width = self.width()
        current_progress = self._progress % self._nth
        progress_width = width * (current_progress / self._nth)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.Color.Green())
        opacity = 1.0 * (float(current_progress) / float(self._nth))
        painter.setOpacity(opacity)
        rect = QtCore.QRect(0, 0, progress_width, self.height())
        o = common.Size.Indicator(0.5)
        painter.drawRoundedRect(rect, o, o)
        if self._show_msg:
            painter.setPen(common.Color.Text())
            painter.drawText(rect, QtCore.Qt.AlignCenter, self._message)
        painter.end()

    @QtCore.Slot()
    def start(self):
        self._message = 'Please wait...'
        self._progress = 0
        self.update()

    @QtCore.Slot()
    def stop(self):
        self._message = ''
        self._progress = 0
        self.update()

    @QtCore.Slot(str)
    def progress(self, msg):
        self._message = msg
        self._progress += 1
        self.update()
        QtCore.QCoreApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)


class ServerEditorDialog(QtWidgets.QDialog):
    """A dialog to view and manage servers, jobs, and links."""

    def __init__(self, parent=None):
        super().__init__(
            parent=parent,
            f=(
                    QtCore.Qt.CustomizeWindowHint |
                    QtCore.Qt.WindowTitleHint |
                    QtCore.Qt.WindowSystemMenuHint |
                    QtCore.Qt.WindowMinMaxButtonsHint |
                    QtCore.Qt.WindowCloseButtonHint
            )
        )

        if not self.parent():
            common.set_stylesheet(self)

        self.filter_toolbar = None
        self.text_filter_editor = None
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.fetch_progress_bar = None
        self.server_view = None
        self.active_bookmark_view = None
        self.setWindowTitle('Servers')
        if not self.parent():
            common.set_stylesheet(self)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Indicator(2.0)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)
        self.server_view = ServerView(parent=self)
        self.active_bookmark_view = ActiveBookmarksWidget(parent=self)
        self.filter_toolbar = QtWidgets.QToolBar('Filters', parent=self)
        self.filter_toolbar.setIconSize(QtCore.QSize(
            common.Size.Margin(1.0),
            common.Size.Margin(1.0)
        ))

        action = QtWidgets.QAction('Add', parent=self)
        action.setIcon(ui.get_icon('add', color=common.Color.Green()))
        action.setToolTip('Add a server, job, or bookmark folder.')
        action.triggered.connect(self.add)
        self.filter_toolbar.addAction(action)
        self.filter_toolbar.addSeparator()
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
        self.text_filter_editor.setPlaceholderText('Search...')
        self.text_filter_editor.textChanged.connect(self.server_view.model().set_text_filter)

        action = QtWidgets.QAction(self.text_filter_editor)
        icon = ui.get_icon('filter', color=common.Color.DisabledText())
        action.setIcon(icon)
        self.text_filter_editor.addAction(action, QtWidgets.QLineEdit.LeadingPosition)
        self.filter_toolbar.addSeparator()
        self.filter_toolbar.addWidget(self.text_filter_editor)
        self.layout().addWidget(self.filter_toolbar, 1)
        self.fetch_progress_bar = ProgressBar(show_msg=False, parent=self)
        self.layout().addWidget(self.fetch_progress_bar, 1)
        splitter = QtWidgets.QSplitter(parent=self)
        splitter.setOrientation(QtCore.Qt.Horizontal)
        splitter.addWidget(self.server_view)
        splitter.addWidget(self.active_bookmark_view)
        splitter.setStretchFactor(0, 0.5)
        splitter.setStretchFactor(1, 0.5)
        splitter.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.layout().addWidget(splitter, 100)
        row = ui.add_row(None, height=common.Size.RowHeight(), parent=self)
        self.ok_button = ui.PaintedButton('Done', parent=self)
        row.layout().addWidget(self.ok_button, 1)
        self.layout().addWidget(row, 1)

    def _connect_signals(self):
        self.server_view.bookmarkNodeSelected.connect(self.active_bookmark_view.selection_changed)
        self.active_bookmark_view.tree_view.selectionModel().selectionChanged.connect(self.server_view.link_selected)
        self.ok_button.clicked.connect(self.accept)

        cnx = QtCore.Qt.DirectConnection
        self.server_view.model().sourceModel().fetchAboutToStart.connect(self.fetch_progress_bar.start, type=cnx)
        self.server_view.model().sourceModel().fetchInProgress.connect(self.fetch_progress_bar.progress, type=cnx)
        self.server_view.model().sourceModel().fetchFinished.connect(self.fetch_progress_bar.stop, type=cnx)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(2.0),
            common.Size.DefaultHeight(1.5)
        )

    def showEvent(self, event):
        super().showEvent(event)
        common.restore_window_geometry(self)
        common.restore_window_state(self)

    def hideEvent(self, event):
        super().hideEvent(event)
        common.save_window_state(self)

    @common.error
    @common.debug
    @QtCore.Slot()
    def add(self):
        node = self.server_view.get_node_from_selection()
        if not node:
            self.server_view.add_server()
            return
        elif node.type == NodeType.ServerNode:
            self.server_view.add_job()
        elif node.type == NodeType.JobNode:
            self.server_view.add_link()
