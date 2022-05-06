import functools
import os
import re

from PySide2 import QtCore, QtWidgets

external_binaries = (
    'ffmpeg',
    'rvpush',
    'rv',
    'oiiotool'
)


def get_binary(binary_name):
    """External binary paths must be set explicitly by the environment or by the
    user in the user settings.

    Bookmarks will look for user defined binary paths, or failing that,
    environment values in a ``{PREFIX}_{BINARY_NAME}`` format,
    e.g. ``BOOKMARKS_FFMPEG``, or ``BOOKMARKS_RV``. These environment variables
    should point to an appropriate executable, e.g.
    ``BOOKMARKS_FFMPEG=C:/ffmpeg/ffmpeg.exe``

    If the environment variable is absent, we'll look at the PATH environment to
    see if the binary is available there.

    Args:
        binary_name (str): One of the pre-defined external binary names.
            E.g. `ffmpeg`.

    Returns:
        str: Path to an executable binary, or `None` if the binary is not found.

    """
    if binary_name.lower() not in [f.lower() for f in external_binaries]:
        raise ValueError(f'{binary_name} is not a recognised binary name.')

    v = _get_user_setting(binary_name)
    if v:
        return v

    from . import product

    key = f'{product}_{binary_name}'.upper()
    if key in os.environ:
        v = os.environ[key]
        try:
            if v and os.path.isfile(v):
                return QtCore.QFileInfo(v).filePath()
        except:
            pass

    return _parse_path_env(binary_name)


def _get_user_setting(binary_name):
    """Check if there's a corresponding user setting for the given binary name.

    The user settings are stored using the binary name prefixed with a 'bin',
    like so: `bin_ffmpeg`.

    Args:
        binary_name (str): The name of the binary.

    Returns:
        str: Path to a binary or None if there's no value found.

    """
    from . import common
    key = f'bin_{binary_name}'.lower()
    v = common.settings.value(common.SettingsSection, key)
    file_info = QtCore.QFileInfo(v)
    if isinstance(v, str) and v and file_info.exists():
        return file_info.filePath()
    return None


def _parse_path_env(binary_name):
    items = {
        os.path.normpath(k.lower()).strip(): QtCore.QFileInfo(k).filePath() for k
        in os.environ['PATH'].split(';')
    }

    for k, v in items.items():
        if not os.path.isdir(v):
            continue

        for entry in os.scandir(v):
            try:
                if not entry.is_file():
                    continue
            except:
                continue

            _filepath = QtCore.QFileInfo(entry.path).filePath()
            _name = _filepath.split('/')[-1]

            match = re.match(rf'{binary_name}.*', _name, flags=re.IGNORECASE)
            if not match:
                continue

            return _filepath

    return None


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
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        from .. import ui
        from .. import common
        common.set_stylesheet(self)

        for name in external_binaries:
            row = ui.add_row(
                name,
                padding=common.size(common.WidthMargin),
                parent=self
            )

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
        from . import common
        for name in external_binaries:
            if not name:
                continue
            editor = getattr(self, f'{name}_editor')
            editor.textChanged.connect(
                functools.partial(
                    common.settings.setValue,
                    common.SettingsSection,
                    f'bin_{name}'
                )
            )

            button1 = getattr(self, f'{name}_button1')
            button1.clicked.connect(functools.partial(self.pick, name))
            button2 = getattr(self, f'{name}_button2')
            button2.clicked.connect(functools.partial(self.reveal, name))

    @QtCore.Slot(str)
    def pick(self, name):
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
        from .. import actions
        editor = getattr(self, f'{name}_editor')
        v = editor.text()
        if not v:
            return
        if not QtCore.QFileInfo(v).exists():
            return
        actions.reveal(editor.text())

    def init_data(self):
        for name in external_binaries:
            v = get_binary(name)
            if not name:
                continue
            editor = getattr(self, f'{name}_editor')
            editor.blockSignals(True)
            editor.setText(v)
            editor.blockSignals(False)
