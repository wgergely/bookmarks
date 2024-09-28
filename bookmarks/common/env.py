"""Utility methods and classes used to parse environment values.

Mainly used to get binary paths, such as ffmpeg.

"""
import functools
import os
import re
import shutil

from PySide2 import QtCore, QtWidgets

external_binaries = (
    'ffmpeg',
    'rvpush',
    'rv',
    'oiiotool'
)


def get_binary(binary_name):
    """Binary path getter.

    The paths are resolved from the following sources and order:
        - active bookmark item's app launcher items
        - distribution folder's bin directory
        - user settings
        - environment variables in a ``{PREFIX}_{BINARY_NAME}`` format,
        for example, ``BOOKMARKS_FFMPEG``, or ``BOOKMARKS_RV``. These environment variables
        should point to an appropriate executable, for example
        ``BOOKMARKS_FFMPEG=C:/ffmpeg/ffmpeg.exe``

        If the environment variable is absent, look at the PATH environment to
        see if the binary is available there.

    Args:
        binary_name (str): Name of a binary, lower-case, without spaces. For example, `aftereffects`, `oiiotool`.

    Returns:
        str: Path to an executable binary, or `None` if the binary isn't found in any of the sources.

    """
    # Sanitize the binary name
    binary_name = re.sub(r'\s+', '', binary_name).lower().strip()

    # Check the active bookmark item's database for possible values
    from .. import database
    from .. import common

    args = common.active('root', args=True)

    if args:
        db = database.get(*args)
        applications = db.value(db.source(), 'applications', database.BookmarkTable)
        if applications:
            # Sanitize names, so they're all lower-case and without spaces
            names = [re.sub(r'\s+', '', v['name']).lower().strip() for v in applications.values()]
            if binary_name in names:
                v = applications[names.index(binary_name)]['path']
                if v and QtCore.QFileInfo(v).exists():
                    return v

    # Check the user settings for possible values
    v = get_user_setting(binary_name)
    if v and QtCore.QFileInfo(v).exists():
        return v


    # Check the distribution folder for possible values
    root = os.environ.get('Bookmarks_ROOT', None)

    if root and QtCore.QFileInfo(root).exists():
        bin_dir = QtCore.QFileInfo(f'{root}/bin')
        if bin_dir.exists():
            for entry in os.scandir(bin_dir.filePath()):
                try:
                    if not entry.is_file():
                        continue
                except:
                    continue

                match = re.match(
                    rf'^{binary_name}$|{binary_name}\..+',
                    entry.name,
                    flags=re.IGNORECASE
                )
                if match:
                    return QtCore.QFileInfo(entry.path).filePath()

    # Check the environment variables for possible values
    key = f'{common.product}_{binary_name}'.upper()
    v = os.environ.get(key, None)
    if v and QtCore.QFileInfo(v).exists():
        return QtCore.QFileInfo(v).filePath()

    # Check the PATH environment for possible values
    v = _parse_path_env(binary_name)
    return v


def get_user_setting(binary_name):
    """Check if there's a corresponding user setting for the given binary name.

    The user settings are stored using the binary name prefixed with a 'bin',
    like so: `bin_ffmpeg`.

    Args:
        binary_name (str): The name of the binary.

    Returns:
        str: Path to a binary or None if there's no value found.

    """
    from . import common
    key = f'settings/bin_{binary_name}'
    v = common.settings.value(key)
    if not v:
        return

    file_info = QtCore.QFileInfo(v)
    if isinstance(v, str) and v and file_info.exists():
        return file_info.filePath()
    return None


def _parse_path_env(binary_name):
    return shutil.which(binary_name)


class EnvPathEditor(QtWidgets.QWidget):
    """Utility widget used to edit the binary paths.

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
        """Create ui.

        """
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        from .. import ui
        from .. import common
        common.set_stylesheet(self)

        for name in external_binaries:
            row = ui.add_row(name, parent=self)

            editor = ui.LineEdit(parent=row)
            editor.setPlaceholderText(f'Path to {name}.exe...')
            row.layout().addWidget(editor, 1)

            button1 = ui.PaintedButton('Pick', parent=row)
            row.layout().addWidget(button1, 0)
            button2 = ui.PaintedButton('Reveal', parent=row)
            row.layout().addWidget(button2, 0)

            setattr(self, f'{name}_editor', editor)
            setattr(self, f'{name}_button1', button1)
            setattr(self, f'{name}_button2', button2)

    def _connect_signals(self):
        """Connect signals.

        """
        from . import common
        for name in external_binaries:
            if not name:
                continue
            editor = getattr(self, f'{name}_editor')
            editor.textChanged.connect(
                functools.partial(common.settings.setValue, f'settings/bin_{name}')
            )

            button1 = getattr(self, f'{name}_button1')
            button1.clicked.connect(functools.partial(self.pick, name))
            button2 = getattr(self, f'{name}_button2')
            button2.clicked.connect(functools.partial(self.reveal, name))

    @QtCore.Slot(str)
    def pick(self, name):
        """Pick a binary file from the file explorer.

        """
        from . import common

        editor = getattr(self, f'{name}_editor')
        f = f'{name}.exe' if common.get_platform() == common.PlatformWindows else \
            '*.*'
        res = QtWidgets.QFileDialog.getOpenFileName(
            caption=f'Select {name} executable...',
            filter=f,
            dir='/'
        )
        path, _ = res
        if not path:
            return
        editor.setText(path)

    @QtCore.Slot(str)
    def reveal(self, name):
        """Reveal a binary file in the file explorer.

        Args:
            name (str): The name of the binary file to be revealed.

        """
        from .. import actions
        editor = getattr(self, f'{name}_editor')
        v = editor.text()
        if not v:
            return
        if not QtCore.QFileInfo(v).exists():
            return
        actions.reveal(editor.text())

    def init_data(self):
        """Initializes data.

        """
        for name in external_binaries:
            v = get_binary(name)
            if not name:
                continue
            editor = getattr(self, f'{name}_editor')
            editor.blockSignals(True)
            editor.setText(v)
            editor.blockSignals(False)
