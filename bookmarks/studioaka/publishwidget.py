"""FFMpeg control widget used to convert a source image sequence to a movie.

"""
import functools

from PySide2 import QtCore, QtWidgets

from . import publish
from .. import common, ui
from ..editor import base
from ..external import ffmpeg_widget

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


def show(ref):
    close()
    global instance
    instance = PublishFootageWidget(ref)
    instance.open()
    return instance


class PublishTypeComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        self.blockSignals(True)
        for k, v in publish.PRESETS.items():
            self.addItem(v['name'], userData=k)
        self.blockSignals(False)


SECTIONS = {
    0: {
        'name': 'Aka Publish',
        'icon': 'studioaka',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'Publish Type',
                    'key': 'publish_type',
                    'validator': None,
                    'widget': PublishTypeComboBox,
                    'placeholder': None,
                    'description': 'Select a publish type',
                },
            },
            1: {
                0: {
                    'name': 'Make Video',
                    'key': 'publish_makevideo',
                    'validator': None,
                    'widget': functools.partial(
                        QtWidgets.QCheckBox, 'Convert Sequence'
                    ),
                    'placeholder': None,
                    'description': 'Select to create view from the image sequence',
                },
                1: {
                    'name': 'Video Size',
                    'key': 'publish_videosize',
                    'validator': None,
                    'widget': ffmpeg_widget.SizeComboBox,
                    'placeholder': None,
                    'description': 'Set the output video size.',
                },
                2: {
                    'name': 'Video Preset',
                    'key': 'publish_videopreset',
                    'validator': None,
                    'widget': ffmpeg_widget.PresetComboBox,
                    'placeholder': None,
                    'description': 'Select the video preset',
                },
                3: {
                    'name': 'Video Timecode',
                    'key': 'publish_videotimecode',
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Add Timecode'),
                    'placeholder': None,
                    'description': 'Add an informative bar and a timecode.',
                },
            },
            2: {
                0: {
                    'name': 'Copy Path',
                    'key': 'publish_copypath',
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Copy to Cliboard'),
                    'placeholder': None,
                    'description': 'Copy the path to the clipboard after finish.',
                },
                1: {
                    'name': 'Reveal Publish',
                    'key': 'publish_reveal',
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Reveal'),
                    'placeholder': None,
                    'description': 'Reveal the published files in the explorer.',
                },
            },
        },
    },
}


class PublishFootageWidget(base.BasePropertyEditor):
    """Publishes a footage.

    """

    def __init__(self, ref, parent=None):
        super().__init__(
            SECTIONS,
            None,
            None,
            None,
            fallback_thumb='icon',
            hide_thumbnail_editor=True,
            buttons=('Publish', 'Cancel'),
            parent=parent
        )
        self._ref = ref
        self._connect_settings_save_signals(common.SECTIONS['publish'])

    @common.error
    @common.debug
    def init_data(self):
        self.load_saved_user_settings(common.SECTIONS['publish'])

    @common.error
    @common.debug
    def save_changes(self):
        """Start the publish process.

        """
        preset = self.publish_type_editor.currentData()
        ffmpeg_preset = self.publish_videopreset_editor.currentData()
        make_movie = self.publish_makevideo_editor.isChecked()
        copy_path = self.publish_copypath_editor.isChecked()
        add_timecode = self.publish_videotimecode_editor.isChecked()
        video_size = self.publish_videosize_editor.currentData()
        reveal_publish = self.publish_reveal_editor.isChecked()

        data = self._ref()
        if not data:
            return

        mbox = ui.MessageBox(
            'Are you sure you want to publish this item?',
            'This will overwrite any existing publish files.',
            buttons=[ui.YesButton, ui.CancelButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

        publish.publish_footage(
            preset,
            data[common.PathRole],
            sorted(data[common.FramesRole]),
            server=data[common.ParentPathRole][0],
            job=data[common.ParentPathRole][1],
            root=data[common.ParentPathRole][2],
            asset=data[common.ParentPathRole][3],
            task=data[common.ParentPathRole][4],
            ffmpeg_preset=ffmpeg_preset,
            add_timecode=add_timecode,
            video_size=video_size,
            make_movie=make_movie,
            copy_path=copy_path,
            reveal_publish=reveal_publish,
        )

    def sizeHint(self):
        return QtCore.QSize(
            common.size(common.DefaultWidth) * 0.66,
            common.size(common.DefaultHeight) * 1.33
        )
