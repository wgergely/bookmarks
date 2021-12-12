import functools

from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from ..editor import base
from . import ffmpeg


instance = None


def close():
    global instance
    if instance is None:
        return
    try:
        instance.close()
        instance.deleteLater()
    except:
        pass
    instance = None


def show(source):
    global instance

    close()
    instance = FFMpegWidget(source)
    instance.open()
    return instance



class PresetComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.init_data()

    def init_data(self):
        self.blockSignals(True)
        for v in ffmpeg.PRESETS.values():
            self.addItem(v['name'], userData=v['preset'])
        self.blockSignals(False)


class SizeComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.init_data()

    def init_data(self):
        self.blockSignals(True)
        for v in ffmpeg.SIZE_PRESETS.values():
            self.addItem(v['name'], userData=v['value'])
        self.blockSignals(False)



SETTING_KEYS = (
    'ffmpeg_preset',
    'ffmpeg_size',
    'ffmpeg_timecode',
)


SECTIONS = {
    0: {
        'name': 'Convert Image Sequence to Video',
        'icon': 'convert',
        'color': common.color(common.BackgroundDarkColor),
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
        self._connect_settings_save_signals(SETTING_KEYS)

    @common.error
    @common.debug
    def init_data(self):
        self.load_saved_user_settings(SETTING_KEYS)


    @common.error
    @common.debug
    def save_changes(self):
        """Start the conversion process.

        """
        return ffmpeg.convert(
            self._file,
            self.ffmpeg_preset_editor.currentData(),
            size=self.ffmpeg_size_editor.currentData(),
            timecode=self.ffmpeg_timecode_editor.isChecked()
        )

    def sizeHint(self):
        return QtCore.QSize(common.size(common.DefaultWidth) * 0.66, common.size(common.DefaultHeight) * 0.66)
