import os

from PySide2 import QtCore, QtWidgets

from .model import AssetLinksModel


class AssetLinksView(QtWidgets.QTreeView):
    """
    A view class for displaying and interacting with asset links.
    """

    def __init__(self, path, parent=None):
        """
        Initialize the AssetLinksView.

        Args:
            path (str): Path to a folder containing a .links file.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle('Asset Links')

        # Set up the model
        self.setModel(AssetLinksModel(path, parent=self))

        # Enable context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

        # Expand all items for visibility
        self.expandAll()

    def open_context_menu(self, position):
        """
        Open the context menu at the given position.

        Args:
            position (QPoint): The position to open the context menu.
        """
        index = self.indexAt(position)
        menu = QtWidgets.QMenu()

        if index.isValid():
            node = index.internalPointer()
            data = node.data()

            if node.parent() == self.model()._root_node:
                # This is the links root node
                add_action = menu.addAction('Add Link')
                clear_action = menu.addAction('Clear Links')
                prune_action = menu.addAction('Prune Links')

                action = menu.exec_(self.viewport().mapToGlobal(position))

                if action == add_action:
                    self.add_link()
                elif action == clear_action:
                    self.clear_links()
                elif action == prune_action:
                    self.prune_links()
            else:
                # This is a link node
                remove_action = menu.addAction('Remove Link')
                action = menu.exec_(self.viewport().mapToGlobal(position))

                if action == remove_action:
                    self.remove_link(data)
        else:
            # Clicked outside any item
            pass

    def add_link(self):
        """
        Add a new link.
        """
        # Get the root path from the model's Links instance
        root_path = self.model().links().path

        # Set options to show directories only and open in the root path
        options = QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        link_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Link", root_path, options)

        # If the user doesn't select anything, terminate the function
        if not link_path:
            return

        # Ensure the selected folder is inside the Links root directory
        link_path = os.path.abspath(link_path).replace('\\', '/')
        root_path = os.path.abspath(root_path).replace('\\', '/')

        if not link_path.startswith(root_path):
            QtWidgets.QMessageBox.warning(
                self,
                'Invalid Selection',
                'Selected folder must be inside the Links root directory.',
            )
            return

        try:
            # Convert absolute path to relative link
            relative_link = self.model().links().to_relative(link_path)
            self.model().add_link(relative_link)
            self.expandAll()
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, 'Invalid Link', str(e))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to add link:\n{e}')

    def clear_links(self):
        """
        Clear all links.
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            'Clear All Links',
            'Are you sure you want to clear all links?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                self.model().clear_links()
                self.expandAll()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to clear links:\n{e}')

    def remove_link(self, link):
        """
        Remove a link.

        Args:
            link (str): The link to remove.
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            'Remove Link',
            f'Are you sure you want to remove the link:\n{link}?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                self.model().remove_link(link)
                self.expandAll()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to remove link:\n{e}')

    def prune_links(self):
        """
        Prune invalid links.
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            'Prune Links',
            'This will remove all invalid links. Do you want to continue?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                removed = self.model().prune_links()
                self.expandAll()
                result = f'Pruned:\n{", ".join(removed)}' if removed else 'No pruning was necessary.'
                QtWidgets.QMessageBox.information(
                    self,
                    'Prune Links',
                    result,
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to prune links:\n{e}')
