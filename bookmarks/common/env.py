"""Utility methods and classes used to parse environment values.

These utilities are mainly used to determine the paths of external binaries
needed by the app (for example, ffmpeg, rv, oiiotool). The resolution order
for binary paths is as follows:

1. Active bookmark item settings, if available
2. User settings as set by the user preferences
3. Distribution folder's `bin` directory
4. Environment variables in the `BOOKMARKS_<BINARY_NAME>` format
5. System PATH lookup, via `shutil.which`

If a binary can't be found using any of these methods, `None` is returned.
"""
import functools
import os
import re
import shutil

from PySide2 import QtCore, QtWidgets

from . import common

__all__ = [
    'external_binaries',
    'get_binary',
    'get_user_setting',
    'EnvPathEditor',
]

external_binaries = (
    'ffmpeg',
    'rvpush',
    'rv',
    'oiiotool'
)


def _to_forward_slashes(path):
    if not path:
        return None
    return path.replace('\\', '/')


def get_binary(binary_name):
    """Get a path to an external binary used by the app.

    The binary name is sanitized (lowercased, spaces removed) before searching.

    Resolution order:
        1. Active bookmark item's app settings.
        2. User settings (`bin_<binary_name>`).
        3. Distribution folder's `bin` directory (if `Bookmarks_ROOT` is set).
        4. Environment variable `BOOKMARKS_<BINARY_NAME>`.
        5. System PATH lookup.

    Args:
        binary_name (str): Name of the binary, for example, 'ffmpeg' or 'oiiotool'.

    Returns:
        str or None: The absolute path to the binary if found, otherwise None.
    """
    from .. import database
    from . import common

    # Normalize the binary name
    binary_name = re.sub(r'\s+', '', binary_name).lower().strip()

    # Check active bookmark DB
    args = common.active('root', args=True)
    if args:
        db = database.get(*args)
        applications = db.value(db.source(), 'applications', database.BookmarkTable)
        if applications:
            names = [re.sub(r'\s+', '', v['name']).lower().strip() for v in applications.values()]
            if binary_name in names:
                idx = names.index(binary_name)
                path_from_db = applications[idx]['path']
                if path_from_db and QtCore.QFileInfo(path_from_db).exists():
                    return _to_forward_slashes(path_from_db)

    # Check user settings
    user_path = get_user_setting(binary_name)
    if user_path and QtCore.QFileInfo(user_path).exists():
        return _to_forward_slashes(user_path)

    # Check distribution folder
    root = os.environ.get('Bookmarks_ROOT', None)
    if root and QtCore.QFileInfo(root).exists():
        bin_dir = QtCore.QFileInfo(os.path.join(root, 'bin'))
        if bin_dir.exists():
            with os.scandir(bin_dir.filePath()) as it:
                for entry in it:
                    try:
                        if not entry.is_file():
                            continue
                    except OSError:
                        continue
                    pattern = rf'^{binary_name}$|{binary_name}\..+'
                    if re.match(pattern, entry.name, flags=re.IGNORECASE):
                        return _to_forward_slashes(QtCore.QFileInfo(entry.path).filePath())

    # Check environment variable
    from . import common
    key = f'{common.product}_{binary_name}'.upper()
    env_path = os.environ.get(key, None)
    if env_path and QtCore.QFileInfo(env_path).exists():
        return _to_forward_slashes(QtCore.QFileInfo(env_path).filePath())

    # Check system PATH
    found = shutil.which(binary_name)
    if found:
        return _to_forward_slashes(found)
    return None


def get_user_setting(binary_name):
    """Retrieve a user-defined binary path from the application settings.

    The setting key is expected in the format: 'settings/bin_<binary_name>'.

    Args:
        binary_name (str): Name of the binary.

    Returns:
        str or None: The stored path if found and valid, otherwise None.
    """
    from . import common
    key = f'settings/bin_{binary_name}'
    v = common.settings.value(key)
    if not v:
        return None
    if isinstance(v, str) and v and QtCore.QFileInfo(v).exists():
        return _to_forward_slashes(QtCore.QFileInfo(v).filePath())
    return None


class EnvPathEditor(QtWidgets.QWidget):
    """A widget that allows users to edit and set paths for external binaries.

    This widget dynamically creates a row per external binary, consisting of:
    - A line edit for the binary path
    - A "Pick" button to choose a path via file dialog
    - A "Reveal" button to show the binary location in the system's file explorer
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum,
        )
        self._create_ui()
        self._connect_signals()
        self.init_data()

    def _create_ui(self):
        """Create the user interface elements."""
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        from .. import ui
        from . import common
        common.set_stylesheet(self)

        for name in external_binaries:
            row = ui.add_row(name, parent=self)
            editor = ui.LineEdit(parent=row)
            editor.setPlaceholderText(f'Path to {name}...')
            row.layout().addWidget(editor, 1)

            button_pick = ui.PaintedButton('Pick', parent=row)
            row.layout().addWidget(button_pick, 0)
            button_reveal = ui.PaintedButton('Reveal', parent=row)
            row.layout().addWidget(button_reveal, 0)

            setattr(self, f'{name}_editor', editor)
            setattr(self, f'{name}_button1', button_pick)
            setattr(self, f'{name}_button2', button_reveal)

    def _connect_signals(self):
        """Connect widget signals to their handlers."""
        from . import common
        for name in external_binaries:
            if not name:
                continue
            editor = getattr(self, f'{name}_editor')
            editor.textChanged.connect(
                functools.partial(common.settings.setValue, f'settings/bin_{name}')
            )

            button_pick = getattr(self, f'{name}_button1')
            button_pick.clicked.connect(functools.partial(self.pick, name))

            button_reveal = getattr(self, f'{name}_button2')
            button_reveal.clicked.connect(functools.partial(self.reveal, name))

    @QtCore.Slot(str)
    @common.error(show_error=True)
    def pick(self, name):
        """Open a file dialog to select a binary file.

        If the user cancels the dialog, no changes are made.

        Args:
            name (str): The binary name being set.
        """
        from . import common
        editor = getattr(self, f'{name}_editor')
        file_filter = f'{name}.exe' if common.get_platform() == common.PlatformWindows else '*.*'
        selected, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption=f'Select {name} executable...',
            filter=file_filter,
            dir='/'
        )
        if selected:
            editor.setText(_to_forward_slashes(selected))

    @QtCore.Slot(str)
    @common.error(show_error=True)
    def reveal(self, name):
        """Show the selected binary in the file explorer if it exists.

        Args:
            name (str): The binary name being revealed.
        """
        from .. import actions
        editor = getattr(self, f'{name}_editor')
        v = editor.text()
        if v and QtCore.QFileInfo(v).exists():
            actions.reveal(v)

    @common.debug
    def init_data(self):
        """Initialize editors with existing binary paths if available."""
        for name in external_binaries:
            if not name:
                continue
            current_path = get_binary(name)
            editor = getattr(self, f'{name}_editor')
            editor.blockSignals(True)
            editor.setText(current_path if current_path else '')
            editor.blockSignals(False)
