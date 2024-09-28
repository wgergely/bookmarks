"""AkaConvert control widget.

"""
import functools
import os
import re

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import database
from ..editor import base


def close():
    """Closes the :class:`AkaConvertWidget` editor.

    """
    if common.akaconvert_widget is None:
        return
    try:
        common.akaconvert_widget.close()
        common.akaconvert_widget.deleteLater()
    except:
        pass
    common.akaconvert_widget = None


def show(index):
    """Opens the :class:`AkaConvertWidget` editor.

    Args:
        index (QModelIndex): The source image sequence index.

    Returns:
        QWidget: The AkaConvertWidget instance.

    """
    close()
    common.akaconvert_widget = AkaConvertWidget(index)
    common.akaconvert_widget.open()
    return common.akaconvert_widget


KEY = 'AKACONVERT_ROOT'

SIZE_PRESETS = {
    common.idx(reset=True, start=0): {
        'name': 'Original',
        'value': (None, None)
    },
    common.idx(): {
        'name': '1080p',
        'value': (1920, 1080)
    },
    common.idx(): {
        'name': f'{int(1080 * 1.5)}p',
        'value': (1920 * 1.5, 1080 * 1.5)
    },
    common.idx(): {
        'name': f'{int(1080 * 2)}p',
        'value': (1920 * 2, 1080 * 2)
    },
}


def get_framerate(fallback_framerate=24.0):
    """Get the currently set frame-rate from the bookmark item database.

    Returns:
        float: The current frame-rate set in the active context.

    """
    if not all(common.active('root', args=True)):
        return fallback_framerate

    db = database.get(*common.active('root', args=True))

    bookmark_framerate = db.value(common.active('root', path=True), 'framerate', database.BookmarkTable)
    asset_framerate = db.value(common.active('asset', path=True), 'asset_framerate', database.AssetTable)

    v = asset_framerate or bookmark_framerate or fallback_framerate
    if not isinstance(v, (int, float)) or v < 1.0:
        return fallback_framerate

    return v


def get_environment(func):
    """Decorator function to check if the environment variable exists.

    """

    def wrapper(*args, **kwargs):
        """Wrapper function.

        """
        if KEY not in os.environ:
            raise RuntimeError(f'Environment variable not found: {KEY}')

        if not QtCore.QFileInfo(os.environ[KEY]).exists():
            raise RuntimeError(f'Environment variable found, but the folder does not exist: {os.environ[KEY]}')

        return func(QtCore.QFileInfo(os.environ[KEY]).absoluteFilePath(), *args, **kwargs)

    return wrapper


@get_environment
def get_convert_script_path(root):
    """Return the path to AkaConvert.bat.

    """
    v = f'{root}/AkaConvert.bat'
    if not QtCore.QFileInfo(v).exists():
        raise RuntimeError(f'AkaConvert not found: {v}')
    return QtCore.QFileInfo(v).absoluteFilePath()


@get_environment
def get_oiiotool_path(root):
    """Return the path to oiiotool.exe.

    """
    v = f'{root}/bin/oiiotool.exe'
    if not QtCore.QFileInfo(v).exists():
        raise RuntimeError(f'Could not find {v}.')
    return QtCore.QFileInfo(v).absoluteFilePath()


@get_environment
def get_ocio_colourspaces(root):
    """Return the list of OCIO colourspaces.

    """
    assumed = (
        'ACES - ACES2065-1', 'ACES - ACEScg', 'Utility - sRGB - Texture', 'Utility - Raw', 'Utility - Curve - Rec.709',
        'Utility - Curve - sRGB', 'Utility - Linear - Rec.2020', 'Utility - Linear - Rec.709',
        'Utility - Linear - sRGB', 'Utility - Gamma 1.8 - Rec.709 - Texture', 'Utility - Gamma 2.2 - Rec.709 - Texture',
        'Output - sRGB', 'Output - sRGB (D60 sim.)', 'Output - Rec.709', 'Output - Rec.709 (D60 sim.)',)

    proc = QtCore.QProcess()
    proc.setProgram(get_oiiotool_path())
    proc.setArguments(['--help', ])

    env = QtCore.QProcessEnvironment.systemEnvironment()
    # We want to pass on AkaConvert's ocio environment variable

    # aces config directory
    ocio_config_path = f'{root}/ocio_config/aces_1.2/config.ocio'

    if not QtCore.QFileInfo(ocio_config_path).exists():
        raise RuntimeError(f'Could not find {ocio_config_path}.')

    # Insert the OCIO config path into the environment variable
    env.insert('OCIO', ocio_config_path)
    proc.setProcessEnvironment(env)

    # Start the process and capture the output
    proc.start()
    proc.waitForFinished()
    output = proc.readAllStandardOutput().data().decode('utf-8')

    # Check if the output contains the OCIO config path
    if 'OpenColorIO' not in output:
        raise RuntimeError(
            f'Was not able to find OpenColorIO in the output: {output}. Was OpenImageIO compiled with OCIO support?'
        )

    # Find the line starting with "Known color spaces:" and extract the colourspaces
    m = re.search(r'Known color spaces:(.*)', output, re.IGNORECASE | re.MULTILINE)
    if not m:
        raise RuntimeError(f'Was not able to find the colourspaces in the output.')

    all_colourspaces = [x.strip().strip('"') for x in m.group(1).split(',')]

    # Check if the assumed colourspaces are in the list of all colourspaces
    good_colourspaces = []
    for c in assumed:
        if [f for f in all_colourspaces if c.strip().lower() in f.strip().lower()]:
            good_colourspaces.append(c)

    if not good_colourspaces:
        raise RuntimeError(f'Was not able to find any of the expected colourspaces. Is the OCIO config correct?')

    return sorted(good_colourspaces)


class PresetComboBox(QtWidgets.QComboBox):
    """FFMpeg preset picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        self.blockSignals(True)
        for k in ('h264', 'prores', 'dnxhd'):
            self.addItem(k.upper(), userData=k)
        self.blockSignals(False)


class SizeComboBox(QtWidgets.QComboBox):
    """FFMpeg output size picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        db = database.get(*common.active('root', args=True))
        bookmark_width = db.value(db.source(), 'width', database.BookmarkTable)
        bookmark_height = db.value(db.source(), 'height', database.BookmarkTable)
        asset_width = db.value(common.active('asset', path=True), 'asset_width', database.AssetTable)
        asset_height = db.value(common.active('asset', path=True), 'asset_height', database.AssetTable)

        width = asset_width or bookmark_width or None
        height = asset_height or bookmark_height or None

        if all((width, height)):
            self.addItem(f'Project | {int(height)}p', userData=(width, height))
            self.addItem(f'Project | {int(height * 0.5)}p', userData=(int(width * 0.5), int(height * 0.5)))

        self.blockSignals(True)
        for v in SIZE_PRESETS.values():
            self.addItem(v['name'], userData=v['value'])

        self.blockSignals(False)


class AcesComboBox(QtWidgets.QComboBox):
    """FFMpeg preset picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        self.blockSignals(True)
        for k in ('aces_1.2',):
            self.addItem(k, userData=k)
        self.blockSignals(False)


class ColorComboBox(QtWidgets.QComboBox):
    """FFMpeg preset picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        self.blockSignals(True)
        for k in get_ocio_colourspaces():
            self.addItem(k, userData=k)
        self.blockSignals(False)


class AkaConvertWidget(base.BasePropertyEditor):
    """Widget used to convert an image sequence to a video.

    """
    #: UI layout definition
    sections = {
        0: {
            'name': 'AkaConvert',
            'icon': 'studioaka',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    common.idx(reset=True, start=0): {
                        'name': 'Video preset',
                        'key': 'akaconvert_preset',
                        'validator': None,
                        'widget': PresetComboBox,
                        'placeholder': None,
                        'description': 'Select the video preset',
                    },
                    common.idx(): {
                        'name': 'Output size',
                        'key': 'akaconvert_size',
                        'validator': None,
                        'widget': SizeComboBox,
                        'placeholder': None,
                        'description': 'Set the output video size',
                    },
                    common.idx(): {
                        'name': 'ACES version',
                        'key': 'akaconvert_acesprofile',
                        'validator': None,
                        'widget': AcesComboBox,
                        'placeholder': None,
                        'description': 'Select the Aces config',
                    },
                },
                1: {
                    common.idx(): {
                        'name': 'Input colour profile',
                        'key': 'akaconvert_inputcolor',
                        'validator': None,
                        'widget': ColorComboBox,
                        'placeholder': None,
                        'description': 'Select the image source\'s colour profile',
                    },
                    common.idx(): {
                        'name': 'Output colour profile',
                        'key': 'akaconvert_outputcolor',
                        'validator': None,
                        'widget': ColorComboBox,
                        'placeholder': None,
                        'description': 'Select the output colour profile',
                    },
                },
                2: {
                    common.idx(): {
                        'name': 'Add burn-in',
                        'key': 'akaconvert_videoburnin',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Add burn-in to video'),
                        'placeholder': None,
                        'description': 'Add video burn-in with timecode to the output video',
                    },
                    common.idx(): {
                        'name': 'Push to RV',
                        'key': 'akaconvert_pushtorv',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Push to RV'),
                        'placeholder': None,
                        'description': 'View the converted clip with RV.',
                    },
                },
            },
        },
    }

    def __init__(self, index, parent=None):
        super().__init__(
            None, None, None, fallback_thumb='convert', hide_thumbnail_editor=True, buttons=(
                'Convert', 'Cancel'), parent=parent
        )
        self._index = index
        self._connect_settings_save_signals(common.SECTIONS['akaconvert'])

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.setFixedWidth(common.Size.DefaultWidth())
        self.setFixedHeight(common.Size.DefaultHeight(1.05))
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.FramelessWindowHint
        )

    @common.error
    @common.debug
    def init_data(self):
        """Initializes data.

        """
        self.load_saved_user_settings(common.SECTIONS['akaconvert'])

    @common.debug
    @common.error
    def save_changes(self):
        """Saves changes.

        """
        index = self._index
        if not index.isValid():
            return False

        path = index.data(common.PathRole)
        if not path:
            return False

        is_collapsed = common.is_collapsed(path)
        if not is_collapsed:
            raise RuntimeError(f'{index.data(QtCore.Qt.DisplayRole)} is not a sequence.')

        frames = index.data(common.FramesRole)
        if not frames:
            raise RuntimeError(
                f'{index.data(QtCore.Qt.DisplayRole)} does not seem to have any frames.'
            )

        if len(frames) < 4:
            raise RuntimeError(
                f'{index.data(QtCore.Qt.DisplayRole)} is too short.'
            )

        source = common.get_sequence_start_path(path)
        if not QtCore.QFileInfo(source).exists():
            raise RuntimeError(f'{source} does not exist.')

        args = (source, '-video-framerate', f'{get_framerate()}', '-video-width',
                f'{self.akaconvert_size_editor.currentData()[0]}', '-video-height',
                f'{self.akaconvert_size_editor.currentData()[1]}', '-video-burnin',
                'true' if self.akaconvert_videoburnin_editor.isChecked() else 'false', '-video-codec',
                self.akaconvert_preset_editor.currentData(), '-aces-config',
                self.akaconvert_acesprofile_editor.currentData(), '-ocio-in-profile',
                self.akaconvert_inputcolor_editor.currentData(), '-ocio-out-profile',
                self.akaconvert_outputcolor_editor.currentData(),)

        self._error_lines = []
        self._progress_lines = []

        self.process = QtCore.QProcess(parent=self)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.convert_process_finished)

        self.process.setProgram(get_convert_script_path())
        self.process.setArguments(args)

        env = QtCore.QProcessEnvironment.systemEnvironment()
        self.process.setProcessEnvironment(env)
        self.process.start()

    @QtCore.Slot()
    def read_output(self):
        data = self.process.readAllStandardOutput().data().decode('utf-8')

        for line in data.splitlines():
            if 'Movie saved to' in line:

                # Get the path to the output video
                video_path = line.split('Movie saved to')[-1].strip().strip('"')

                if not QtCore.QFileInfo(video_path).exists():
                    print(f'Could not find the output video: {video_path}')
                else:
                    # Show the video in the files tab
                    common.signals.fileAdded.emit(video_path)

                    # Push to RV
                    if self.akaconvert_pushtorv_editor.isChecked():
                        from ..external import rv
                        rv.execute_rvpush_command(video_path, rv.PushAndClear)

            if 'Finished' in line:
                self.convert_process_finished(0, QtCore.QProcess.NormalExit)
                return

            if line.startswith('[AkaConvert Error]'):
                if line not in self._error_lines:
                    self._error_lines.append(line)
            elif line.startswith('[AkaConvert Info]'):
                if line not in self._progress_lines:
                    self._progress_lines.append(line)

        current_progress_line = self._progress_lines[-1] if self._progress_lines else None
        if current_progress_line:
            common.show_message(
                'Converting...', body=current_progress_line.replace('[AkaConvert Info]', ''), message_type=None,
                buttons=[], disable_animation=True, )

    def convert_process_finished(self, exit_code, exit_status):
        # I don't know why, but the process doesn't terminate itself and will
        # keep running in the background. So we need to terminate it manually I guess!
        if exit_code != 0:
            common.show_message(
                'Finished.',
                f'Conversion has finished but process exited with a code {exit_code}.\n{self._error_lines[-1]}'
            )
        if exit_code == 0 and exit_status == QtCore.QProcess.NormalExit:
            common.show_message(
                'Finished.', f'Conversion has finished successfully.'
            )

        raise RuntimeError('Finished.')

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(0.66), common.Size.DefaultHeight(1.2)
        )

    def showEvent(self, event):
        super().showEvent(event)

        if not self._index:
            return

        item_rect = common.widget().visualRect(self._index)
        corner = common.widget().mapToGlobal(item_rect.bottomLeft())

        self.move(corner)
        self.setGeometry(
            self.geometry().x() + (item_rect.width() / 2) - (
                    self.geometry().width() / 2), self.geometry().y(), self.geometry().width(), self.geometry(

            ).height()
        )
        common.move_widget_to_available_geo(self)
