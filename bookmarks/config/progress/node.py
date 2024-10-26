class Node(object):
    """Represents a task node with attributes for use in a model.

    Attributes:
        value (str): The internal value identifier of the task.
        parent (Node): The parent node in the hierarchy.
        children (list of Node): The child nodes in the hierarchy.
    """

    def __init__(self, task, parent=None):
        self._task = task

        self.value = task['value']

        self.parent = parent
        self.children = []

    @property
    def task(self):
        return self._task

    def add_child(self, child):
        """Adds a child node to this node.

        Args:
            child (Node): The child node to add.
        """
        child.parent = self
        self.children.append(child)

    def remove_child(self, position):
        """Removes a child node at a given position.

        Args:
            position (int): The index of the child to remove.

        Returns:
            bool: True if the child was removed, False otherwise.
        """
        if 0 <= position < len(self.children):
            child = self.children.pop(position)
            child.parent = None
            return True
        return False

    def child(self, row):
        """Gets the child node at a given row.

        Args:
            row (int): The index of the child node.

        Returns:
            Node: The child node at the specified index.
        """
        if 0 <= row < len(self.children):
            return self.children[row]
        return None

    def child_count(self):
        """Gets the number of child nodes.

        Returns:
            int: The number of child nodes.
        """
        return len(self.children)

    def row(self):
        """Gets the row number of this node in its parent's children.

        Returns:
            int: The index of this node in the parent's children list.
        """
        if self.parent:
            return self.parent.children.index(self, )
        return 0
