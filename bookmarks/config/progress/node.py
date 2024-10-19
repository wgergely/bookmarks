from PySide2 import QtCore, QtGui


class Node(object):
    """Represents a task node with attributes for use in a model.

    Attributes:
        name (str): The display name of the task.
        value (str): The internal value identifier of the task.
        color (QColor): The color associated with the task.
        description (str): A brief description of the task.
        icon (str): The icon resource identifier for the task.
        status (dict): The current status information of the task.
        step: The pipeline step associated with the task.
        enabled (bool): Indicates if the task is enabled.
        parent (Node): The parent node in the hierarchy.
        children (list of Node): The child nodes in the hierarchy.
    """

    def __init__(self, data, parent=None):
        self.name = data.get('name')
        self.value = data.get('value')
        self.color = data.get('color')
        self.description = data.get('description')
        self.icon = data.get('icon')
        self.status = data.get('status', {})
        self.step = data.get('step')
        self.enabled = data.get('enabled', True)
        self.parent = parent
        self.children = []

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

    def data(self):
        """Gets the data for this node.

        Returns:
            dict: A dictionary of the node's data attributes.
        """
        return {
            'name': self.name,
            'value': self.value,
            'color': self.color,
            'description': self.description,
            'icon': self.icon,
            'status': self.status,
            'step': self.step,
            'enabled': self.enabled,
        }

    def row(self):
        """Gets the row number of this node in its parent's children.

        Returns:
            int: The index of this node in the parent's children list.
        """
        if self.parent:
            return self.parent.children.index(self, )
        return 0

    def set_status(self, status):
        """Sets the status of the task.

        Args:
            status (dict): The new status information.
        """
        self.status = status

    def get_status(self):
        """Gets the current status of the task.

        Returns:
            dict: The current status information.
        """
        return self.status
