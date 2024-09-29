
import collections
import functools
import os

from PySide2 import QtCore, QtWidgets, QtGui

from . import lib
from .lib import LinksAPI
from .model import AssetLinksModel
from .. import actions, images
from .. import common
from .. import contextmenu
from .. import shortcuts
from .. import ui


class LinksContextMenu(contextmenu.BaseContextMenu):

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.add_parent_menu()
        self.separator()
        self.add_presets_menu()
        self.separator()
        self.add_reveal_menu()
        self.add_child_menu()
        self.separator()
        self.add_view_menu()

    def add_parent_menu(self):
        """Add link menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if node.is_leaf():
            return

        self.menu[contextmenu.key()] = {
            'text': 'Add Folder to Preset',
            'icon': ui.get_icon('add_link', color=common.Color.Green()),
            'action': self.parent().add_link,
            'shortcut': shortcuts.get(
                shortcuts.LinksViewShortcuts,
                shortcuts.AddLink
            ).key(),
            'description': shortcuts.hint(
                shortcuts.LinksViewShortcuts,
                shortcuts.AddLink
            )
        }

        self.separator()

        self.menu[contextmenu.key()] = {
            'text': 'Copy',
            'icon': ui.get_icon('link'),
            'action': self.parent().copy_links,
            'shortcut': shortcuts.get(
                shortcuts.LinksViewShortcuts,
                shortcuts.CopyLinks
            ).key(),
            'description': shortcuts.hint(
                shortcuts.LinksViewShortcuts,
                shortcuts.CopyLinks
            )
        }
        self.menu[contextmenu.key()] = {
            'text': 'Paste',
            'icon': ui.get_icon('add_link'),
            'action': self.parent().paste_links,
            'disabled': not common.get_clipboard(common.AssetLinksClipboard),
            'shortcut': shortcuts.get(
                shortcuts.LinksViewShortcuts,
                shortcuts.PasteLinks
            ).key(),
            'description': shortcuts.hint(
                shortcuts.LinksViewShortcuts,
                shortcuts.PasteLinks
            )
        }
        self.menu[contextmenu.key()] = {
            'text': 'Apply clipboard to all',
            'icon': ui.get_icon('add_link'),
            'action': self.parent().apply_clipboard_to_all,
            'disabled': not common.get_clipboard(common.AssetLinksClipboard),
            'shortcut': shortcuts.get(
                shortcuts.LinksViewShortcuts,
                shortcuts.PasteLinksToAll
            ).key(),
            'description': shortcuts.hint(
                shortcuts.LinksViewShortcuts,
                shortcuts.PasteLinksToAll
            ),
        }

        self.separator()

        self.menu[contextmenu.key()] = {
            'text': 'Remove links',
            'icon': ui.get_icon('remove_link', color=common.Color.Red()),
            'action': self.parent().clear_links,
            'shortcut': shortcuts.get(
                shortcuts.LinksViewShortcuts,
                shortcuts.RemoveLink
            ).key(),
            'description': shortcuts.hint(
                shortcuts.LinksViewShortcuts,
                shortcuts.RemoveLink
            )
        }
        self.menu[contextmenu.key()] = {
            'text': 'Remove missing',
            'action': self.parent().prune_links,
            'description': 'Remove links that don\'t point to existing folders.',
        }

    def add_presets_menu(self):
        """Add presets menu.

        """
        args = common.active('root', args=True)
        if not args:
            return

        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if node.is_leaf():
            return

        if node.api().get(force=True):
            self.menu[contextmenu.key()] = {
                'text': 'Save as New Preset...',
                'icon': ui.get_icon('add_preset', color=common.Color.Green()),
                'action': self.parent().save_preset_to_database,
                'help': 'Save the current set of links as a preset.',
            }

        presets = lib.LinksAPI.presets()
        if not presets:
            return

        k = 'Apply Preset'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[f'{k}:icon'] = ui.get_icon('preset')

        k_ = 'Apply Preset to All Items'
        if k_ not in self.menu:
            self.menu[k_] = collections.OrderedDict()
            self.menu[f'{k_}:icon'] = ui.get_icon('preset')

        self.separator()

        k__ = 'Remove Preset'
        if k__ not in self.menu:
            self.menu[k__] = collections.OrderedDict()
            self.menu[f'{k__}:icon'] = ui.get_icon('preset', color=common.Color.Red())

        self.menu[contextmenu.key()] = {
            'text': 'Remove All Presets',
            'icon': ui.get_icon('preset', color=common.Color.Red()),
            'action': self.parent().remove_all_presets,
            'help': 'Remove all presets.',
        }

        for _k in presets:
            self.menu[k][contextmenu.key()] = {
                'text': _k,
                'icon': ui.get_icon('preset', color=common.Color.Blue()),
                'action': functools.partial(self.parent().apply_preset, _k),
                'help': f'Add the preset path: {_k}.',
            }
            self.menu[k_][contextmenu.key()] = {
                'text': _k,
                'icon': ui.get_icon('preset', color=common.Color.Blue()),
                'action': functools.partial(self.parent().apply_preset, _k, apply_to_all=True),
                'help': f'Add the preset path: {_k}.',
            }
            self.menu[k__][contextmenu.key()] = {
                'text': _k,
                'icon': ui.get_icon('preset', color=common.Color.Red()),
                'action': functools.partial(self.parent().clear_preset, _k),
                'help': f'Add the preset path: {_k}.',
            }

    def add_child_menu(self):
        if not self.index.isValid():
            return

        node = self.index.internalPointer()

        if not node:
            return

        if not node.is_leaf():
            return

        parent_node = node.parent()

        self.menu[contextmenu.key()] = {
            'text': 'Remove',
            'icon': ui.get_icon('remove_link', color=common.Color.Red()),
            'action': self.parent().remove_link,
            'shortcut': shortcuts.get(
                shortcuts.LinksViewShortcuts,
                shortcuts.RemoveLink
            ).key(),
            'description': shortcuts.hint(
                shortcuts.LinksViewShortcuts,
                shortcuts.RemoveLink
            )
        }

    def add_reveal_menu(self):
        """Add reveal menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if node.exists():
            self.menu[contextmenu.key()] = {
                'text': 'Reveal in Explorer',
                'icon': ui.get_icon('folder'),
                'action': self.parent().reveal,
                'shortcut': shortcuts.get(
                    shortcuts.LinksViewShortcuts,
                    shortcuts.RevealLink
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.LinksViewShortcuts,
                    shortcuts.RevealLink
                ),
            }

    def add_view_menu(self):
        """Add the view menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'icon': ui.get_icon('refresh'),
            'action': self.parent().add_paths_from_active,
            'shortcut': shortcuts.get(
                shortcuts.LinksViewShortcuts,
                shortcuts.ReloadLinks
            ).key(),
            'description': shortcuts.hint(
                shortcuts.LinksViewShortcuts,
                shortcuts.ReloadLinks
            ),
        }
        self.menu[contextmenu.key()] = {
            'text': 'Expand All',
            'icon': ui.get_icon('expand'),
            'action': (self.parent().expandAll, self.parent().save_expanded_nodes),
            'help': 'Expand all items.',
        }
        self.menu[contextmenu.key()] = {
            'text': 'Collapse All',
            'icon': ui.get_icon('collapse'),
            'action': (self.parent().collapseAll, self.parent().save_expanded_nodes),
            'help': 'Collapse all items.',
        }


class PresetNameDialog(QtWidgets.QDialog):
    """
    PresetNameDialog is a custom QDialog that allows the user to input or select a preset name from a combobox.

    __init__(parent=None)
        Initializes the PresetNameDialog with default settings. Takes an optional parent widget.

    _create_ui()
        Constructs the user interface, laying out the editor, combo box, and buttons.

    _connect_signals()
        Connects the interactive elements (buttons, combo box) to their respective event handlers.

    _init_data()
        Initializes the data for the combo box, retrieving preset names and setting up initial state.

    _on_preset_selected(index)
        Slot function for handling changes in the combo box selection.

    paintEvent(event"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Enter Preset Name')

        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        self.ok_button = None
        self.editor = None
        self.presets_combobox = None

        self._create_ui()
        self._connect_signals()
        self._init_data()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Indicator(6.0)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        self.editor = ui.LineEdit(parent=self)
        self.editor.setPlaceholderText('Enter a preset name, for example, \'Preset1\'')
        self.editor.setMinimumWidth(common.Size.DefaultWidth(0.5))

        self.setFocusProxy(self.editor)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)

        row = ui.add_row(None, height=None, parent=self)
        row.layout().addWidget(self.editor, 1)

        self.presets_combobox = QtWidgets.QComboBox(parent=self)
        self.presets_combobox.setView(QtWidgets.QListView())
        self.presets_combobox.setDisabled(True)

        row.layout().addWidget(self.presets_combobox, 0)

        self.ok_button = ui.PaintedButton('Ok', parent=self)
        self.cancel_button = ui.PaintedButton('Cancel', parent=self)

        row = ui.add_row(None, height=None, parent=self)
        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

        self.layout().addWidget(row, 0)

    def _connect_signals(self):
        self.ok_button.clicked.connect(lambda: self.done(QtWidgets.QDialog.Accepted))
        self.editor.returnPressed.connect(lambda: self.done(QtWidgets.QDialog.Accepted))

        self.cancel_button.clicked.connect(lambda: self.done(QtWidgets.QDialog.Rejected))

        self.presets_combobox.currentIndexChanged.connect(self._on_preset_selected)

    def _init_data(self):
        node = self.parent().get_node_from_selection()
        if not node:
            raise ValueError('No node selected.')

        presets = node.api().presets()
        if not presets:
            return

        self.presets_combobox.blockSignals(True)

        self.presets_combobox.clear()
        self.presets_combobox.addItem('Select a preset...')
        self.presets_combobox.model().item(0).setFlags(QtCore.Qt.NoItemFlags)

        self.presets_combobox.setDisabled(False)
        self.presets_combobox.addItems(presets.keys())
        for i in range(1, self.presets_combobox.count()):
            self.presets_combobox.setItemIcon(
                i,
                ui.get_icon('preset', color=common.Color.Blue())
            )

        self.presets_combobox.addItem('Save as new...')
        self.presets_combobox.setItemIcon(
            self.presets_combobox.count() - 1,
            ui.get_icon('add_preset', color=common.Color.Green())
        )

        self.presets_combobox.setCurrentIndex(0)
        self.presets_combobox.blockSignals(False)

    @common.error
    @common.debug
    @QtCore.Slot(int)
    def _on_preset_selected(self, index):
        v = self.presets_combobox.currentText()
        if v == 'Select a preset...':
            return
        if v == 'Save as new...':
            self.editor.clear()
            self.editor.setFocus(QtCore.Qt.OtherFocusReason)
            return

        self.editor.setText(v)

        self.presets_combobox.blockSignals(True)
        self.presets_combobox.setCurrentIndex(0)
        self.presets_combobox.blockSignals(False)

    def paintEvent(self, event):

        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(common.Color.Blue())
        pen.setWidthF(common.Size.Separator(2.0))
        painter.setPen(pen)

        painter.setBrush(common.Color.Background())

        o = common.Size.Indicator(2.0)
        _o = common.Size.Indicator()
        painter.drawRoundedRect(
            self.rect().adjusted(_o, _o, -_o, -_o),
            o,
            o
        )

    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            return super().done(r)

        if not self.editor.text():
            common.show_message(
                'Invalid Name',
                body='Must provide a name for the preset.',
                message_type='error'
            )
            return

        super().done(r)

    def exec_(self):
        r = super().exec_()
        if r == QtWidgets.QDialog.Accepted:
            return self.editor.text()
        return None

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(0.5),
            common.Size.RowHeight()
        )


class LinksView(QtWidgets.QTreeView):
    """
     linksFileChanged = QtCore.Signal(str)
         Signal emitted when the links file changes.

     def __init__(self, parent=None):
         Initialize the LinksView.

     def _init_shortcuts(self):
         Initializes shortcuts.

     def _init_model(self):
         Initializes the model for the tree view.

     def _connect_signals(self):
         Connects the necessary signals for the view.

     @QtCore.Slot()
     def emit_links_file_changed(self, *args, **kwargs):
         Emit the linksFileChanged signal.

     def contextMenuEvent(self, event):
         Context menu event.

     def sizeHint(self):
         Return the recommended size for the view.

    """

    linksFileChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        """
        Initialize the LinksView.

        """
        super().__init__(parent=parent)
        self.setWindowTitle('Asset Links')

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.setHeaderHidden(True)

        self._expanded_nodes = []
        self._selected_node = None

        self._init_shortcuts()
        self._init_model()
        self._connect_signals()

    def _init_shortcuts(self):
        """Initializes shortcuts.

        """
        shortcuts.add_shortcuts(self, shortcuts.LinksViewShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.LinksViewShortcuts
        )
        connect(shortcuts.AddLink, self.add_link)
        connect(shortcuts.RemoveLink, self.remove_link)
        connect(shortcuts.CopyLinks, self.copy_links)
        connect(shortcuts.PasteLinks, self.paste_links)
        connect(shortcuts.PasteLinksToAll, self.apply_clipboard_to_all)
        connect(shortcuts.RevealLink, self.reveal)
        connect(shortcuts.ReloadLinks, self.add_paths_from_active)

    def _init_model(self):
        self.setModel(AssetLinksModel(parent=self))

    def _connect_signals(self):
        self.selectionModel().selectionChanged.connect(self.emit_links_file_changed)
        self.selectionModel().currentChanged.connect(self.emit_links_file_changed)
        self.model().modelReset.connect(self.emit_links_file_changed)

        self.model().modelAboutToBeReset.connect(self.save_expanded_nodes)
        self.model().layoutAboutToBeChanged.connect(self.save_expanded_nodes)
        self.model().modelReset.connect(self.restore_expanded_nodes)
        self.model().layoutChanged.connect(self.restore_expanded_nodes)
        self.expanded.connect(self.save_expanded_nodes)
        self.collapsed.connect(self.save_expanded_nodes)

        self.selectionModel().selectionChanged.connect(self.save_selected_node)
        self.model().modelAboutToBeReset.connect(self.save_selected_node)
        self.model().layoutAboutToBeChanged.connect(self.save_selected_node)

        self.model().modelReset.connect(self.restore_selected_node)
        self.model().layoutChanged.connect(self.restore_selected_node)
        self.expanded.connect(self.restore_selected_node)

    @QtCore.Slot()
    def emit_links_file_changed(self, *args, **kwargs):
        """
        Emit the linksFileChanged signal.

        """
        if not self.selectionModel().hasSelection():
            self.linksFileChanged.emit('')
            return

        if self.selectionModel().currentIndex().isValid():
            index = self.selectionModel().currentIndex()
        else:
            index = next(f for f in self.selectionModel().selectedIndexes())

        if not index.isValid():
            self.linksFileChanged.emit('')
            return

        node = index.internalPointer()
        if not node:
            self.linksFileChanged.emit('')
            return

        p = node.parent().path() if node.is_leaf() else node.path()
        self.linksFileChanged.emit(p)

    def contextMenuEvent(self, event):
        """Context menu event.

        """
        index = self.indexAt(event.pos())
        menu = LinksContextMenu(index, parent=self)
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

        node = index.internalPointer()
        if not node:
            return None

        return node

    @QtCore.Slot()
    def save_expanded_nodes(self, *args, **kwargs):
        """
        Save the expanded nodes.

        """
        if not self.model():
            self._expanded_nodes = []

        # Iterate over all direct child indexes of the root node
        for i in range(self.model().rowCount(parent=self.rootIndex())):
            index = self.model().index(i, 0, self.rootIndex())
            if not index.isValid():
                continue

            if self.isExpanded(index):
                node = index.internalPointer()
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

        if not self.model():
            return

        for i in range(self.model().rowCount(parent=self.rootIndex())):
            index = self.model().index(i, 0, self.rootIndex())
            if not index.isValid():
                continue

            node = index.internalPointer()
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

        if node.is_leaf():
            path = node.api().to_absolute(node.path())
        else:
            path = node.path()

        self._selected_node = path

    @QtCore.Slot()
    def restore_selected_node(self):
        """
        Restore the selected node.

        """

        def _it_children(parent_index):
            for i in range(self.model().rowCount(parent=parent_index)):
                index = self.model().index(i, 0, parent_index)
                if not index.isValid():
                    continue

                if index.model().hasChildren(parent=index):
                    for child_index in _it_children(index):
                        yield child_index

                yield index

        if not self._selected_node:
            return

        for index in _it_children(self.rootIndex()):
            node = index.internalPointer()
            if not node:
                continue

            if node.is_leaf():
                path = node.api().to_absolute(node.path())
            else:
                path = node.path()

            if path == self._selected_node:
                self.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.setCurrentIndex(index)
                self.scrollTo(index)
                break

    @common.error
    @common.debug
    def add_path(self, path):
        """
        Add a new path to the view.

        Args:
            path (str): The path to add.
        """
        self.model().add_path(path)

    @common.error
    @common.debug
    @QtCore.Slot()
    def reload_path(self, path):
        """
        Reload the give path.

        Args:
            path (str): The path to reload.
        """
        model = self.model()
        if not model:
            return

        self.model().reload_path(path)

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_paths_from_active(self):
        """Refresh the model with the folder paths in the active root item root."""
        # Refresh cached api data
        LinksAPI.update_cached_data()

        path = common.active('root', path=True)
        if not path:
            raise ValueError('A root item must be active!')
        if not os.path.exists(path):
            raise ValueError(f'Path does not exist: {path}')

        self.model().clear()

        for entry in os.scandir(path):
            if not entry.is_dir():
                continue
            if entry.is_symlink():
                continue
            if not os.access(entry.path, os.W_OK):
                continue
            if entry.name.startswith('.'):
                continue
            self.model().add_path(entry.path.replace('\\', '/'))

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_link(self):
        """Add a new link."""
        node = self.get_node_from_selection()
        if not node:
            return

        if node.is_leaf():
            raise ValueError('Cannot add a link to a leaf node.')

        options = QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        link_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            f'Add link to {node.path()}',
            node.path(),
            options
        )

        if link_path == node.path():
            raise ValueError('Cannot add a link to itself.')

        # If the user doesn't select anything, terminate the function
        if not link_path:
            return

        # Ensure the selected folder is inside the Links root directory
        link_path = os.path.abspath(link_path).replace('\\', '/')
        root_path = os.path.abspath(node.path()).replace('\\', '/')

        if not link_path.startswith(root_path):
            common.show_message(
                'Invalid Selection',
                body='Selected folder must be inside the Links root directory.',
                message_type='error'
            )
            return

        # Convert the absolute path to the relative link
        relative_link = node.api().to_relative(link_path)
        self.model().add_link(node.path(), relative_link)

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_link(self):
        """
        Remove a link from the given parent path.

        """
        node = self.get_node_from_selection()
        if not node:
            return

        if not node.is_leaf():
            self.clear_links()
            return

        self.model().remove_link(node.parent().path(), node.path())

    @common.error
    @common.debug
    @QtCore.Slot()
    def clear_links(self, force=False):
        """
        Clear all links.
        """
        node = self.get_node_from_selection()
        if not node:
            return

        if node.is_leaf():
            raise ValueError('Cannot clear links from a leaf node.')

        if not force:
            if common.show_message(
                    'Remove links',
                    body='Are you sure you want to remove the links from the selected item? This action not undoable.',
                    buttons=[common.YesButton, common.NoButton], modal=True, message_type='error'
            ) == QtWidgets.QDialog.Rejected:
                return

        self.model().clear_links(node.path())

    @common.error
    @common.debug
    @QtCore.Slot()
    def prune_links(self):
        """
        Prune invalid links.
        """
        node = self.get_node_from_selection()
        if not node:
            return

        if node.is_leaf():
            raise ValueError('Cannot prune links from a leaf node.')

        if common.show_message(
                'Prune Links',
                body='This will remove all invalid links. Do you want to continue? The action is not undoable.',
                buttons=[common.YesButton, common.NoButton], modal=True
        ) == QtWidgets.QDialog.Rejected:
            return

        removed_links = self.model().prune_links(node.path())
        result = f'Pruned:\n{", ".join(removed_links)}' if removed_links else 'No pruning was necessary.'
        common.show_message('Done.', body=result)

    @common.error
    @common.debug
    @QtCore.Slot()
    def copy_links(self):
        """
        Copy all links to the clipboard.
        """
        node = self.get_node_from_selection()
        if not node:
            return

        if node.is_leaf():
            node.api().copy_to_clipboard(links=[node.path(), ])
            return
        node.api().copy_to_clipboard()

    @common.error
    @common.debug
    @QtCore.Slot()
    def paste_links(self):
        """
        Paste links from the clipboard.
        """
        node = self.get_node_from_selection()
        if not node:
            return

        if node.is_leaf():
            path = node.parent().path()
        else:
            path = node.path()

        skipped = self.model().paste_links(path)

        if skipped:
            common.show_message(
                'Not all links were pasted!',
                body=f'Skipped {len(skipped)} item{"s" if len(skipped) > 1 else ""}:\n"{", ".join(skipped)}"',
                message_type='info'
            )

    @common.error
    @common.debug
    @QtCore.Slot()
    def apply_clipboard_to_all(self):
        """
        Paste links from the clipboard to all items.
        """
        if not common.get_clipboard(common.AssetLinksClipboard):
            raise ValueError('No links in the clipboard.')

        if not common.show_message(
                'Paste to All',
                body='Are you sure you want to paste the links to all items? This action is not undoable.',
                buttons=[common.YesButton, common.NoButton], modal=True
        ) == QtWidgets.QDialog.Accepted:
            return

        # Loop through all indexes
        for i in range(self.model().rowCount(parent=self.rootIndex())):
            index = self.model().index(i, 0, self.rootIndex())
            if not index.isValid():
                continue

            self.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)
            self.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect)

            self.clear_links(force=True)
            self.paste_links()

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

        if node.is_leaf():
            path = node.api().to_absolute(node.path())
        else:
            path = node.path()

        actions.reveal(path)

    @common.error
    @common.debug
    @QtCore.Slot()
    def save_preset_to_database(self):
        """
        Save the current view as a preset.
        """
        node = self.get_node_from_selection()
        if not node:
            return

        if not node.api().get(force=True):
            raise ValueError('No links to save as a preset.')

        # Create a popup name editor
        name = PresetNameDialog(parent=self).exec_()
        if not name:
            return

        if not name:
            raise ValueError('Must provide a name for the preset.')

        presets = node.api().presets()

        if name in presets:
            if common.show_message(
                    'Overwrite Preset',
                    body=f'Preset "{name}" already exists. Overwrite?',
                    buttons=[common.YesButton, common.NoButton], modal=True
            ) == QtWidgets.QDialog.Rejected:
                return

        node.api().save_preset_to_database(name, node.path())

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def apply_preset(self, preset, apply_to_all=False):
        """
        Apply a preset path to the view.

        Args:
            preset (str): The preset path to apply.
            apply_to_all (bool): Whether to apply the preset to all items.

        """
        node = self.get_node_from_selection()
        if not node:
            return

        if common.show_message(
                'Apply Preset?',
                body=f'Are you sure you want to apply "{preset}"?\n'
                     f'This action is not undoable and will override the current links.',
                buttons=[common.YesButton, common.NoButton], modal=True
        ) == QtWidgets.QDialog.Rejected:
            return

        if node.is_leaf():
            node = node.parent()

        if apply_to_all:
            path = None
        else:
            path = node.path()

        self.model().apply_preset(preset, path=path)

    @common.error
    @common.debug
    @QtCore.Slot()
    def clear_preset(self, preset):
        """Remove the selected preset."""
        if not common.show_message(
                'Remove Preset',
                body=f'Are you sure you want to remove the preset "{preset}"? This action is not undoable.',
                buttons=[common.YesButton, common.NoButton], modal=True
        ) == QtWidgets.QDialog.Accepted:
            return

        lib.LinksAPI.clear_preset(preset)

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_all_presets(self):
        """Remove all presets."""
        if not common.show_message(
                'Remove All Presets',
                body='Are you sure you want to remove all presets? This action is not undoable.',
                buttons=[common.YesButton, common.NoButton], modal=True
        ) == QtWidgets.QDialog.Accepted:
            return

        lib.LinksAPI.clear_presets()


class NumberBar(QtWidgets.QWidget):
    """
    class NumberBar(QtWidgets.QWidget):
        A custom widget that displays line numbers for a QTextEdit instance.

        __init__(self, parent=None):
            Initializes the NumberBar widget and connects signals to update its contents.

            Parameters:
            parent (QWidget): The parent widget, typically a QTextEdit instance.

        paintEvent(self, event):
            Handles the paint event to draw the line numbers bar.

            Parameters:
            event (QPaintEvent): The paint event object.

        get_width(self):
            Calculates the necessary width of the NumberBar based on the number of lines.

            Returns:
            int: The width required to display the line numbers.

        update_width(self):
            Updates"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.parent().blockCountChanged.connect(self.update_width)
        self.parent().updateRequest.connect(self.update_contents)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        if not self.parent().toPlainText():
            alpha = 0
        else:
            alpha = 20

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, alpha))
        painter.drawRoundedRect(
            event.rect(),
            common.Size.Indicator(),
            common.Size.Indicator()
        )

        block = self.parent().firstVisibleBlock()

        font = self.parent().font()
        metrics = self.parent().fontMetrics()

        # Iterate over all visible text blocks in the document.
        while block.isValid():
            block_number = block.blockNumber()
            block_top = self.parent().blockBoundingGeometry(block).translated(self.parent().contentOffset()).top()

            # Check if the position of the block is outside the visible area.
            if not block.isVisible() or block_top >= event.rect().bottom():
                break

            # We want the line number for the selected line to be bold.
            if block_number == self.parent().textCursor().blockNumber():
                painter.setPen(common.Color.Blue())
            else:
                painter.setPen(common.Color.LightBackground())
            painter.setFont(font)

            # Draw the line number right justified at the position of the line.
            paint_rect = QtCore.QRect(
                0,
                block_top,
                self.width() - (common.Size.Indicator(2.0)),
                metrics.height()
            )

            if self.parent().toPlainText():
                painter.drawText(
                    paint_rect,
                    QtCore.Qt.AlignRight,
                    f'{block_number + 1}'
                )

            block = block.next()

        painter.end()

        super().paintEvent(event)

    def get_width(self):
        metrics = self.parent().fontMetrics()

        count = self.parent().blockCount()
        width = metrics.width(f'{count}') + common.Size.Margin()
        return width

    def update_width(self):
        width = self.get_width()
        if self.width() != width:
            self.setFixedWidth(width)
            self.parent().setViewportMargins(width, 0, 0, 0)

    def update_contents(self, rect, scroll):
        font = self.parent().font()

        if scroll:
            self.scroll(0, scroll)
        else:
            self.update(0, rect.y(), self.width(), rect.height())

        if rect.contains(self.parent().viewport().rect()):
            font_size = self.parent().currentCharFormat().font().pointSize()
            font.setPointSize(font_size)
            font.setStyle(QtGui.QFont.StyleNormal)
            self.update_width()


class PlainTextEdit(QtWidgets.QPlainTextEdit):
    """
    Custom QPlainTextEdit class with a number bar for line numbers

    class PlainTextEdit(QtWidgets.QPlainTextEdit):

        def __init__(self, parent=None):
            Initializes the PlainTextEdit widget.
            Parameters:
            - parent: The parent widget.

        def sizeHint(self):
            Returns the recommended size for the widget.
            Returns:
            - QSize: The size hint.

        def minimumSizeHint(self):
            Returns the minimum size hint for the widget.
            Returns:
            - QSize: The minimum size hint.

        def resizeEvent(self, event):
            Handles the resize event and adjusts the number bar's geometry.
            Parameters:
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._number_bar = NumberBar(parent=self)
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultHeight(0.5),
            common.Size.DefaultWidth()
        )

    def minimumSizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultHeight(0.1),
            common.Size.DefaultWidth()
        )

    def resizeEvent(self, event):
        cr = self.contentsRect()
        rec = QtCore.QRect(
            cr.left(),
            cr.top(),
            self._number_bar.get_width(),
            cr.height()
        )
        self._number_bar.setGeometry(rec)

        super().resizeEvent(event)


class LinksTextEditor(QtWidgets.QWidget):
    """
    Class representing a text editor for handling links files with PyQt5.

    class LinksTextEditor(QtWidgets.QWidget):

        Signal emitted when the links file is edited.
        linksFileEdited = QtCore.Signal(str)

        Initialize the LinksTextEditor instance.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.

        Create the user interface components for the text editor.

        Connect signals to the appropriate slots.

        Slot called when the .links file changed in the view.

        Args:
            path (str): The path to the links file.

        Emit a signal indicating the links file has changed, and update the links file content.

    """
    linksFileEdited = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._text_editor = None
        self._save_button = None

        self._current_path = None

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(common.Size.Indicator())

        self._text_editor = PlainTextEdit(parent=self)
        self._text_editor.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.layout().addWidget(self._text_editor)

        self._save_button = ui.PaintedButton(
            'Save', parent=self
        )
        self.layout().addWidget(self._save_button)

    def _connect_signals(self):
        self._save_button.clicked.connect(self.emit_link_file_changed)

    @QtCore.Slot(str)
    def link_changed(self, path):
        """
        Slot called when the .links file changed in the view.

        Args:
            path (str): The path to the links file.

        """
        self._current_path = path

        if self._text_editor is None:
            return

        if not path:
            self._text_editor.clear()
            self.setDisabled(True)
            return

        self._text_editor.clear()
        self.setDisabled(False)

        api = lib.LinksAPI(path)
        if not os.path.exists(api.links_file):
            self._text_editor.setPlaceholderText(f'No links file found in {api.links_file}')
            return

        links = api.get(force=True)
        if not links:
            self._text_editor.setPlaceholderText(f'No links file found in {api.links_file}')
        else:
            self._text_editor.setPlainText('\n'.join(links))

    @common.error
    @common.debug
    @QtCore.Slot()
    def emit_link_file_changed(self):
        if not self._current_path:
            return

        v = self._text_editor.toPlainText()
        links = sorted(
            {f.replace('\\', '/').strip(' .-_/') for f in v.split('\n') if f.rstrip()},
            key=str.lower
        )

        api = lib.LinksAPI(self._current_path)
        api.clear()

        for link in links:
            api.add(link, force=True)

        self.linksFileEdited.emit(self._current_path)


class AssetTemplatesComboBox(QtWidgets.QComboBox):
    """
    AssetTemplatesComboBox is a custom combo box widget for selecting asset templates.

    Methods:
        __init__(parent=None)
            Initializes the combo box with a custom QListView for better item display.

        init_data(force=False)
            Initializes the data in the combo box by loading asset templates.
            Parameters:
                force (bool): If True, forces re-initialization even if already initialized.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = QtWidgets.QListView(parent=self)
        self.setView(view)

        self._initialized = False

    def init_data(self, force=False):
        if not force and self._initialized:
            return

        from ..templates import lib

        self.clear()
        self.addItem('Select an asset template...')
        self.setCurrentIndex(0)

        templates = lib.TemplateItem.get_saved_templates(lib.TemplateType.DatabaseTemplate)
        if not templates:
            return

        for template in sorted(templates, key=lambda x: x['name'].lower()):
            self.addItem(template['name'], userData=template['name'])

        self._initialized = True


class LinksEditor(QtWidgets.QWidget):
    """
    LinksEditor is a custom QWidget for editing asset links.

    Attributes:
        _links_view_widget: A widget that displays the links.
        _links_editor_widget: A text editor for modifying the links.
        _create_folders_button: A button to initiate the creation of missing folders.
        _asset_templates_widget: A combo box containing asset templates.

    Methods:
        __init__(parent):
            Initializes the LinksEditor widget with provided parent.
        _create_ui():
            Sets up the user interface components of the widget.
        _connect_signals():
            Connects the signals between the links view and links editor components.
        showEvent(event):
            Sets focus to the links view widget when the event is triggered"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        if not parent:
            common.set_stylesheet(self)

        self.setWindowTitle('Asset Links Editor')

        self._links_view_widget = None
        self._links_editor_widget = None
        self._create_folders_button = None
        self._asset_templates_widget = None

        self._create_ui()
        self._connect_signals()

        self.setFocusProxy(self._links_view_widget)

    def _create_ui(self):
        self.setContentsMargins(0, 0, 0, 0)
        QtWidgets.QVBoxLayout(self)

        # Add splitter
        splitter = QtWidgets.QSplitter(parent=self)
        splitter.setOrientation(QtCore.Qt.Horizontal)
        splitter.setChildrenCollapsible(True)
        self.layout().addWidget(splitter)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(widget)

        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().setSpacing(common.Size.Margin(0.5))

        splitter.addWidget(widget)

        # Add title row
        row = ui.add_row(None, height=None, parent=widget)
        row.layout().setAlignment(QtCore.Qt.AlignLeft)

        thumbnail_label = QtWidgets.QLabel(parent=self)
        thumbnail_label.setScaledContents(True)
        thumbnail_label.setFixedHeight(common.Size.RowHeight(0.8))
        thumbnail_label.setFixedWidth(common.Size.RowHeight(0.8))
        thumbnail_label.setAlignment(QtCore.Qt.AlignCenter)
        pixmap, _ = images.get_thumbnail(
            common.active('server'),
            common.active('job'),
            common.active('root'),
            common.active('root', path=True),
            size=common.Size.RowHeight(),
            fallback_thumb='asset'
        )
        thumbnail_label.setPixmap(pixmap)

        row.layout().addWidget(thumbnail_label, 0)

        title_label = ui.PaintedLabel(
            '  |  '.join(common.active('root', args=True)[1:]),
            size=common.Size.MediumText(1.0),
            color=common.Color.Text(),
            font=common.Font.BoldFont,
            parent=self
        )
        row.layout().addWidget(title_label, 1)

        self._links_view_widget = LinksView(parent=self)
        widget.layout().addWidget(self._links_view_widget)

        bottom_row = ui.get_group(parent=widget)

        self._asset_templates_widget = AssetTemplatesComboBox(parent=self)
        self._create_folders_button = ui.PaintedButton('Create Missing', parent=self)

        ui.add_description(
            'Select an asset template to create the missing folders.\n'
            f'The template will be expanded into each missing link. '
            f'<span style="color: {common.Color.Red(qss=True)};">This action cannot be undone</span>, so ensure '
            f'the selected asset template is intended to be expanded into nested folders.',
            label='',
            icon=ui.get_icon('alert', color=common.Color.Red()),
            parent=bottom_row
        )
        bottom_row.layout().addWidget(self._asset_templates_widget, 1)

        bottom_row.layout().addWidget(self._create_folders_button, 1)
        bottom_row.layout().addStretch(1.5)

        self._links_editor_widget = LinksTextEditor(parent=self)
        self._links_editor_widget.setDisabled(True)
        splitter.addWidget(self._links_editor_widget)

    def _connect_signals(self):
        self._links_view_widget.linksFileChanged.connect(self._links_editor_widget.link_changed)

        self._links_view_widget.model().modelAboutToBeReset.connect(lambda: self._links_editor_widget.link_changed(''))
        self._links_editor_widget.linksFileEdited.connect(self._links_view_widget.reload_path)

    def showEvent(self, event):
        self._links_view_widget.setFocus(QtCore.Qt.OtherFocusReason)
