from PySide2 import QtWidgets, QtCore

from .popup import FilterPopupDialog
from .. import common
from .. import ui


class SwitcherGroup(QtWidgets.QWidget):
    """
    Custom widget that contains the three switcher buttons and draws a rounded rectangle behind them.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # Initialize attributes
        self._bookmark_switcher_button = None
        self._asset_switcher_button = None
        self._task_switcher_button = None

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        """
        Create the UI elements for the switcher group.
        """
        # Create layout
        layout = QtWidgets.QHBoxLayout(self)
        padding = common.Size.Margin(0.2)  # Adjust padding as needed
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(common.Size.Indicator(1.0))

        # Icon size
        icon_size = common.Size.Margin(1.0)
        icon_size_qsize = QtCore.QSize(icon_size, icon_size)

        # Create 'Previous' button
        prev_icon = ui.get_icon('arrow_left', size=icon_size)
        self._prev_button = QtWidgets.QToolButton()
        self._prev_button.setIcon(prev_icon)
        self._prev_button.setToolTip('Previous Item')
        self.layout().addWidget(self._prev_button)

        # Bookmark item switcher
        bookmark_icon = ui.get_icon('bookmark', size=icon_size, color=common.Color.Text())
        self._bookmark_switcher_button = QtWidgets.QToolButton()
        self._bookmark_switcher_button.setIcon(bookmark_icon)
        self._bookmark_switcher_button.setToolTip('Bookmark Item Switcher')
        self._bookmark_switcher_button.setIconSize(icon_size_qsize)
        layout.addWidget(self._bookmark_switcher_button)

        # Asset item switcher
        asset_switcher_icon = ui.get_icon('asset', size=icon_size, color=common.Color.Text())
        self._asset_switcher_button = QtWidgets.QToolButton()
        self._asset_switcher_button.setIcon(asset_switcher_icon)
        self._asset_switcher_button.setToolTip('Asset Item Switcher')
        self._asset_switcher_button.setIconSize(icon_size_qsize)
        layout.addWidget(self._asset_switcher_button)

        # Task folder switcher
        task_switcher_icon = ui.get_icon('folder', size=icon_size, color=common.Color.Text())
        self._task_switcher_button = QtWidgets.QToolButton()
        self._task_switcher_button.setIcon(task_switcher_icon)
        self._task_switcher_button.setToolTip('Task Folder Switcher')
        self._task_switcher_button.setIconSize(icon_size_qsize)
        layout.addWidget(self._task_switcher_button)

        # Create 'Next' button
        next_icon = ui.get_icon('arrow_right', size=icon_size)
        self._next_button = QtWidgets.QToolButton()
        self._next_button.setIcon(next_icon)
        self._next_button.setToolTip('Next Item')
        self.layout().addWidget(self._next_button)

        # Set focus policies
        self._prev_button.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._next_button.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._bookmark_switcher_button.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._asset_switcher_button.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._task_switcher_button.setFocusPolicy(QtCore.Qt.StrongFocus)

    def _connect_signals(self):
        """
        Connect signals to their respective slots.
        """
        self._next_button.clicked.connect(self._on_next_button_clicked)
        self._prev_button.clicked.connect(self._on_prev_button_clicked)
        self._bookmark_switcher_button.clicked.connect(self._on_bookmark_switcher_clicked)
        self._asset_switcher_button.clicked.connect(self._on_asset_switcher_clicked)
        self._task_switcher_button.clicked.connect(self._on_task_switcher_clicked)

    @QtCore.Slot()
    @common.debug
    @common.error
    def _on_next_button_clicked(self):
        """
        Slot for the 'Next' button clicked signal.
        """
        # Implement logic to navigate to the next item
        pass

    @QtCore.Slot()
    @common.debug
    @common.error
    def _on_prev_button_clicked(self):
        """
        Slot for the 'Previous' button clicked signal.
        """
        # Implement logic to navigate to the previous item
        pass

    @QtCore.Slot()
    @common.debug
    @common.error
    def _on_bookmark_switcher_clicked(self):
        """
        Slot for the 'Bookmark Item Switcher' button clicked signal.
        """
        # Implement logic to switch between bookmark items
        self.parent()._show_filter_dialog('Bookmark', self._bookmark_switcher_button)

    @QtCore.Slot()
    @common.debug
    @common.error
    def _on_asset_switcher_clicked(self):
        """
        Slot for the 'Asset Item Switcher' button clicked signal.
        """
        # Implement logic to switch between asset items
        self.parent()._show_filter_dialog('Asset', self._asset_switcher_button)

    @QtCore.Slot()
    @common.debug
    @common.error
    def _on_task_switcher_clicked(self):
        """
        Slot for the 'Task Folder Switcher' button clicked signal.
        """
        # Implement logic to switch between task folders
        self.parent()._show_filter_dialog('Task', self._task_switcher_button)


class ItemControlBar(QtWidgets.QToolBar):
    """
    Custom toolbar containing item filters and actions.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        if not parent:
            common.set_stylesheet(self)

        # Initialize attributes
        self._add_action = None
        self._prev_button = None
        self._switcher_group = None
        self._next_button = None
        self._job_button = None
        self._asset_button = None
        self._task_button = None
        self._formats_button = None

        self._create_ui()
        self._connect_signals()
        self._init_data()

    def _create_ui(self):
        """
        Create UI elements for the control bar.
        """
        # Set icon size using common.Size enum
        icon_size = common.Size.Margin(1.0)
        self.setIconSize(QtCore.QSize(icon_size, icon_size))

        # Set layout spacing
        self.layout().setSpacing(common.Size.Indicator(2.0))

        # Create 'Add' action
        add_icon = ui.get_icon('add', color=common.Color.Green(), size=icon_size)
        self._add_action = self.addAction(add_icon, 'Add New')
        self._add_action.setToolTip('Add a new item')

        # Create the switcher group widget
        self._switcher_group = SwitcherGroup(parent=self)
        self.addWidget(self._switcher_group)


        spacer = QtWidgets.QWidget()
        spacer.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        spacer.setFocusPolicy(QtCore.Qt.NoFocus)
        spacer.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        spacer.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.addWidget(spacer)

        # Create 'Job' filter button
        job_icon = ui.get_icon('bookmark', size=icon_size)
        self._job_button = QtWidgets.QToolButton()
        self._job_button.setText('Jobs')
        self._job_button.setIcon(job_icon)
        self._job_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.addWidget(self._job_button)

        # Create 'Asset' filter button
        asset_icon = ui.get_icon('asset', size=icon_size)
        self._asset_button = QtWidgets.QToolButton()
        self._asset_button.setText('Asset')
        self._asset_button.setIcon(asset_icon)
        self._asset_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.addWidget(self._asset_button)

        # Create 'Task' filter button
        task_icon = ui.get_icon('sg', size=icon_size)
        self._task_button = QtWidgets.QToolButton()
        self._task_button.setText('Task')
        self._task_button.setIcon(task_icon)
        self._task_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.addWidget(self._task_button)

        # Create 'Folders' filter button
        folders_icon = ui.get_icon('folder', size=icon_size)
        self._folders_button = QtWidgets.QToolButton()
        self._folders_button.setText('Folders')
        self._folders_button.setIcon(folders_icon)
        self._folders_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.addWidget(self._folders_button)

        # Create 'Formats' filter button
        formats_icon = ui.get_icon('file', size=icon_size)
        self._formats_button = QtWidgets.QToolButton()
        self._formats_button.setText('File Type')
        self._formats_button.setIcon(formats_icon)
        self._formats_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.addWidget(self._formats_button)

        # Set focus policies
        self._job_button.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._asset_button.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._task_button.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._formats_button.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._folders_button.setFocusPolicy(QtCore.Qt.StrongFocus)

    def _connect_signals(self):
        """
        Connect signals to their respective slots.
        """
        self._add_action.triggered.connect(self._on_add_triggered)
        self._job_button.clicked.connect(self._on_job_button_clicked)
        self._asset_button.clicked.connect(self._on_asset_button_clicked)
        self._task_button.clicked.connect(self._on_task_button_clicked)
        self._formats_button.clicked.connect(self._on_formats_button_clicked)
        self._folders_button.clicked.connect(self._on_folders_button_clicked)

    def _init_data(self):
        """
        Initialize data for the control bar.
        """
        pass  # Implement data initialization if necessary

    def _on_add_triggered(self):
        """
        Slot for the 'Add' action triggered signal.
        """
        # Implement the logic to open the add new dialog
        pass

    def _on_job_button_clicked(self):
        """
        Slot for the 'Job' button clicked signal.
        """
        self._show_filter_dialog('Job', self._job_button)

    def _on_asset_button_clicked(self):
        """
        Slot for the 'Asset' button clicked signal.
        """
        self._show_filter_dialog('Asset', self._asset_button)

    def _on_task_button_clicked(self):
        """
        Slot for the 'Task' button clicked signal.
        """
        self._show_filter_dialog('Task', self._task_button)

    def _on_formats_button_clicked(self):
        """
        Slot for the 'Formats' button clicked signal.
        """
        self._show_filter_dialog('Format', self._formats_button)

    def _on_folders_button_clicked(self):
        """
        Slot for the 'Formats' button clicked signal.
        """
        self._show_filter_dialog('Folder', self._folders_button)

    def _show_filter_dialog(self, filter_type, button):
        """
        Display the FilterPopupDialog below the specified button.

        Args:
            filter_type (str): The type of filter to display.
            button (QtWidgets.QToolButton): The button that was clicked.
        """
        dialog = FilterPopupDialog(filter_type, parent=self)
        # Position the dialog below the button
        pos = button.mapToGlobal(QtCore.QPoint(
            -(dialog.width() * 0.5) + (button.width() * 0.5), button.height()))
        dialog.move(pos)
        dialog.show()
