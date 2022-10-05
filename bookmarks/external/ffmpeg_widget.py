"""FFMpeg control widget used to convert a source image sequence to a movie.

"""
import functools

from PySide2 import QtCore, QtWidgets

from . import ffmpeg
from .. import common
from .. import images
from ..editor import base
from .. import log


def close():
    """Closes the :class:`FFMpegWidget` editor.

    """
    if common.ffmpeg_export_widget is None:
        return
    try:
        common.ffmpeg_export_widget.close()
        common.ffmpeg_export_widget.deleteLater()
    except:
        pass
    common.ffmpeg_export_widget = None


def show(source):
    """Opens the :class:`FFMpegWidget` editor.

    """
    close()
    common.ffmpeg_export_widget = FFMpegWidget(source)
    common.ffmpeg_export_widget.open()
    return common.ffmpeg_export_widget


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
        for v in ffmpeg.PRESETS.values():
            self.addItem(v['name'], userData=v['preset'])
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
        self.blockSignals(True)
        for v in ffmpeg.SIZE_PRESETS.values():
            self.addItem(v['name'], userData=v['value'])
        self.blockSignals(False)


#: UI layout definition
SECTIONS = {
    0: {
        'name': 'Convert Image Sequence to Video',
        'icon': 'convert',
        'color': common.color(common.color_dark_background),
        'groups': {
            0: {
                0: {
                    'name': 'Preset',
                    'key': 'ffmpeg_preset',
                    'validator': None,
                    'widget': PresetComboBox,
                    'placeholder': None,
                    'description': 'Select the preset to use.',
                },
                1: {
                    'name': 'Size',
                    'key': 'ffmpeg_size',
                    'validator': None,
                    'widget': SizeComboBox,
                    'placeholder': None,
                    'description': 'Set the output video size.',
                },
                2: {
                    'name': 'Timecode',
                    'key': 'ffmpeg_timecode',
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Add Timecode'),
                    'placeholder': None,
                    'description': 'Add an informative bar and a timecode.',
                },
            },
        },
    },
}


class FFMpegWidget(base.BasePropertyEditor):
    """Widget used to convert an image sequence to a video.

    """

    def __init__(self, source, parent=None):
        super().__init__(
            SECTIONS,
            None,
            None,
            None,
            fallback_thumb='convert',
            hide_thumbnail_editor=True,
            buttons=('Convert', 'Cancel'),
            parent=parent
        )
        self._file = source
        self._connect_settings_save_signals(common.SECTIONS['ffmpeg'])

    @common.error
    @common.debug
    def init_data(self):
        """Initializes data.

        """
        self.load_saved_user_settings(common.SECTIONS['ffmpeg'])

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        if not common.is_collapsed(self._file):
            raise RuntimeError(f'{self._file} is not a sequence.')

        start_path = common.get_sequence_start_path(self._file)
        start_seq = common.get_sequence(start_path)
        start_n = int(start_seq.group(2))

        end_path = common.get_sequence_end_path(self._file)
        end_seq = common.get_sequence(end_path)
        end_n = int(end_seq.group(2))

        padding = len(start_seq.group(2))

        _destinations = []

        pbar = ffmpeg.get_progress_bar(start_n, end_n)
        pbar.open()

        for n in range(start_n, end_n + 1):
            pbar.setValue(n)

            n = f'{n}'.zfill(padding)
            source = f'{start_seq.group(1)}{n}{start_seq.group(3)}.{start_seq.group(4)}'
            file_info = QtCore.QFileInfo(source)
            destination = f'{file_info.path()}/temp_{file_info.baseName()}.jpg'
            _destinations.append(destination)

            # Convert to jpeg
            buf = images.oiio_get_buf(source)
            if not buf:
                continue
            buf.write(destination)

        pbar.close()

        file_info = QtCore.QFileInfo(self._file)
        _file = f'{file_info.path()}/temp_{file_info.baseName()}.jpg'

        mov = ffmpeg.convert(
            _file,
            self.ffmpeg_preset_editor.currentData(),
            size=self.ffmpeg_size_editor.currentData(),
            timecode=self.ffmpeg_timecode_editor.isChecked()
        )

        # Remove temp files
        for f in _destinations:
            images.ImageCache.flush(f)
            if not QtCore.QFile(f).remove():
                log.error(f'Failed to remove {f}')

        if not mov:
            return False

        # Rename output video
        _mov = mov.replace('temp_', '')
        QtCore.QFile.rename(mov, _mov)
        common.widget(common.FileTab).show_item(_mov, role=common.PathRole, update=True)
        return True


    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width) * 0.66,
            common.size(common.size_height) * 0.66
        )
