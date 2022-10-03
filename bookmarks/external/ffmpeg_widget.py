"""FFMpeg control widget used to convert a source image sequence to a movie.

"""
import functools

from PySide2 import QtCore, QtWidgets

from . import ffmpeg
from .. import common
from ..editor import base

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
        return ffmpeg.convert(
            self._file,
            self.ffmpeg_preset_editor.currentData(),
            size=self.ffmpeg_size_editor.currentData(),
            timecode=self.ffmpeg_timecode_editor.isChecked()
        )

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width) * 0.66,
            common.size(common.size_height) * 0.66
        )
