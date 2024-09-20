import functools
import os

from PySide2 import QtCore, QtWidgets, QtGui

from . import lib
from .model import AssetLinksModel
from .. import actions
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
            'text': 'Pick Folder',
            'icon': ui.get_icon('add', color=common.color(common.color_green)),
            'action': self.parent().add_link,
            'help': 'Add a new relative link to this asset.',
        }

        self.separator()

        self.menu[contextmenu.key()] = {
            'text': 'Copy Links',
            'icon': ui.get_icon('copy'),
            'action': self.parent().copy_links,
            'help': 'Copy all links to the clipboard.',
        }
        self.menu[contextmenu.key()] = {
            'text': 'Paste Links',
            'icon': ui.get_icon('add'),
            'action': self.parent().paste_links,
            'help': 'Paste links from the clipboard.',
        }

        self.separator()

        self.menu[contextmenu.key()] = {
            'text': 'Clear Links',
            'icon': ui.get_icon('close', color=common.color(common.color_red)),
            'action': self.parent().clear_links,
            'help': 'Clear all links.',
        }
        self.menu[contextmenu.key()] = {
            'text': 'Prune Links',
            'icon': ui.get_icon('archive'),
            'action': self.parent().prune_links,
            'help': 'Prune invalid links.',
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
            'text': 'Remove Link',
            'icon': ui.get_icon('archive', color=common.color(common.color_red)),
            'action': self.parent().remove_link,
            'help': 'Remove this link.',
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
                'help': 'Reveal the link in the file explorer.',
            }

    def add_view_menu(self):
        """Add view menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'icon': ui.get_icon('refresh'),
            'action': self.parent().reload_paths,
            'help': 'Refresh the view.',
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


class LinksView(QtWidgets.QTreeView):
    """
    A view class for displaying and interacting with asset links.
    """

    linksFileChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        """
        Initialize the LinksView.

        """
        super().__init__(parent=parent)
        self.setWindowTitle('Asset Links')
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHeaderHidden(True)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._expanded_nodes = []

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
        connect(shortcuts.RevealLink, self.reveal)
        connect(shortcuts.EditLinks, self.edit_links)

    def _init_model(self):
        self.setModel(AssetLinksModel(parent=self))

    def _connect_signals(self):
        self.selectionModel().selectionChanged.connect(self.emit_links_file_changed)
        self.model().modelAboutToBeReset.connect(
            lambda: self.emit_links_file_changed(QtCore.QModelIndex(), QtCore.QModelIndex())
        )

        self.model().modelAboutToBeReset.connect(self.save_expanded_nodes)
        self.model().layoutAboutToBeChanged.connect(self.save_expanded_nodes)
        self.model().modelReset.connect(self.restore_expanded_nodes)
        self.model().layoutChanged.connect(self.restore_expanded_nodes)
        self.expanded.connect(self.save_expanded_nodes)
        self.collapsed.connect(self.save_expanded_nodes)

    @QtCore.Slot(QtCore.QModelIndex, QtCore.QModelIndex)
    def emit_links_file_changed(self, current, previous, *args, **kwargs):
        """
        Emit the linksFileChanged signal.

        """
        if isinstance(current, QtCore.QItemSelection):
            index = next(iter(current.indexes()), QtCore.QModelIndex())
        elif isinstance(current, QtCore.QModelIndex):
            index = current
        else:
            index = QtCore.QModelIndex()

        if not index.isValid():
            self.linksFileChanged.emit('')
            return

        node = index.internalPointer()
        if not node:
            return

        if node.is_leaf():
            path = node.parent().path()
        else:
            path = node.path()

        self.linksFileChanged.emit(path)

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
            common.size(common.size_width),
            common.size(common.size_height)
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
    def reload_paths(self):
        """
        Clear all paths.
        """
        self.model().reload_paths()

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_link(self):
        """
        Add a new link.
        """
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
            raise ValueError('Cannot remove a link from a non-leaf node.')

        if common.show_message(
                'Remove Link',
                body=f'Are you sure you want to remove the link:\n{node.path()}?',
                buttons=[common.YesButton, common.NoButton], modal=True, message_type='error'
        ) == QtWidgets.QDialog.Rejected:
            return

        self.model().remove_link(node.parent().path(), node.path())

    @common.error
    @common.debug
    @QtCore.Slot()
    def clear_links(self):
        """
        Clear all links.
        """
        node = self.get_node_from_selection()
        if not node:
            return

        if node.is_leaf():
            raise ValueError('Cannot clear links from a leaf node.')

        if common.show_message(
                'Clear All Links',
                body='Are you sure you want to clear all links? This action not undoable.',
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
                'Not all links were pasted.',
                body=f'Skipped {len(skipped)} item{"s" if len(skipped) > 1 else ""}:\n{", ".join(skipped)}',
                message_type='info'
            )

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
    def edit_links(self):
        """
        Edit the links file.
        """
        raise NotImplementedError('Edit links is not implemented yet.')

    @common.error
    @common.debug
    @QtCore.Slot()
    def save_preset(self):
        """
        Save the current view as a preset.
        """
        raise NotImplementedError('Save preset is not implemented yet.')


class NumberBar(QtWidgets.QWidget):

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
            common.size(common.size_indicator),
            common.size(common.size_indicator)
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
                painter.setPen(common.color(common.color_blue))
            else:
                painter.setPen(common.color(common.color_light_background))
            painter.setFont(font)

            # Draw the line number right justified at the position of the line.
            paint_rect = QtCore.QRect(
                0,
                block_top,
                self.width() - (common.size(common.size_indicator) * 2),
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
        width = metrics.width(f'{count}') + common.size(common.size_margin)
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

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._number_bar = NumberBar(parent=self)

        self.setPlaceholderText('Select an item to view its contents.')
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)

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

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._text_editor = None
        self._apply_button = None

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
        self.layout().setSpacing(0)

        self._text_editor = PlainTextEdit(parent=self)
        self._text_editor.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.layout().addWidget(self._text_editor)

        row = ui.add_row(None, parent=self)
        self._apply_button = ui.PaintedButton(
            'Save', parent=self
        )
        row.layout().addWidget(self._apply_button, 1)

    def _connect_signals(self):
        pass

    @QtCore.Slot(str)
    def link_changed(self, path):
        if self._text_editor is None:
            return

        if path == self._current_path:
            return

        self._text_editor.clear()
        self._current_path = None

        if not path:
            self.setDisabled(True)
            return

        self.setDisabled(False)

        api = lib.LinksAPI(path)
        if not os.path.exists(api.links_file):
            return

        links = api.get(force=True)
        self._text_editor.setPlainText('\n'.join(links))
        self._current_path = path


class LinksEditor(QtWidgets.QSplitter):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        if not parent:
            common.set_stylesheet(self)

        self._links_view = None
        self._links_editor = None

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        o = common.size(common.size_indicator) * 2
        self.setContentsMargins(o, o, o, o)

        self.setWindowTitle('Asset Links Editor')

        self._links_view = LinksView(parent=self)
        self.addWidget(self._links_view)

        self._links_editor = LinksTextEditor(parent=self)
        self.addWidget(self._links_editor)

    def _connect_signals(self):
        self._links_view.linksFileChanged.connect(self._links_editor.link_changed)

    def add_path(self, path):
        self._links_view.add_path(path)
