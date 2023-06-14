"""FFMpeg control widget used to convert a source image sequence to a movie.

"""
import functools
import os

import pyimageutil
from PySide2 import QtCore, QtWidgets

from . import ffmpeg
from .. import common
from .. import database
from .. import images
from .. import log
from .. import ui
from ..editor import base
from ..external import rv
from ..tokens import tokens


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


def show(index):
    """Opens the :class:`FFMpegWidget` editor.

    Args:
        index (QModelIndex): The source image sequence index.

    Returns:
        QWidget: The FFMpegWidget instance.

    """
    close()
    common.ffmpeg_export_widget = FFMpegWidget(index)
    common.ffmpeg_export_widget.open()
    return common.ffmpeg_export_widget


class TimecodeModel(ui.AbstractListModel):
    """Template item picker model.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def init_data(self):
        """Initializes data.

        """
        config = tokens.get(*common.active('root', args=True))
        data = config.data()
        if not isinstance(data, dict):
            return

        template = common.settings.value('ffmpeg/timecode_preset')
        for v in data[tokens.FFMpegTCConfig].values():
            if template == v['name']:
                icon = ui.get_icon(
                    'check',
                    color=common.color(common.color_green),
                    size=common.size(common.size_margin) * 2
                )
            else:
                icon = ui.get_icon(
                    'branch_closed',
                    size=common.size(common.size_margin) * 2
                )

            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: v['name'],
                QtCore.Qt.DecorationRole: icon,
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.StatusTipRole: v['description'],
                QtCore.Qt.AccessibleDescriptionRole: v['description'],
                QtCore.Qt.WhatsThisRole: v['description'],
                QtCore.Qt.ToolTipRole: v['description'],
                QtCore.Qt.UserRole: v['value'],
            }


class TimecodeComboBox(QtWidgets.QComboBox):
    """Timecode preset picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        model = TimecodeModel()
        self.setModel(model)


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
        db = database.get(*common.active('root', args=True))
        width = db.value(db.source(), 'width', database.BookmarkTable)
        height = db.value(db.source(), 'width', database.BookmarkTable)
        if all((width, height)):
            self.addItem(f'Project | {int(height)}p', userData=(width, height))

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
                    'name': 'Add timecode',
                    'key': 'ffmpeg_add_timecode',
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Add Timecode'),
                    'placeholder': None,
                    'description': 'Add an informative bar and a timecode.',
                },
                3: {
                    'name': 'Timecode preset',
                    'key': 'ffmpeg_timecode_preset',
                    'validator': None,
                    'widget': TimecodeComboBox,
                    'placeholder': None,
                    'description': 'Select the timecode preset to use.',
                },
                4: {
                    'name': 'Push to RV',
                    'key': 'ffmpeg_pushtorv',
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Push to RV'),
                    'placeholder': None,
                    'description': 'Open the converted clip with RV.',
                },
            },
        },
    },
}


class FFMpegWidget(base.BasePropertyEditor):
    """Widget used to convert an image sequence to a video.

    """

    def __init__(self, index, parent=None):
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
        self._index = index
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

        # Check output video file
        seq = index.data(common.SequenceRole)
        preset = self.ffmpeg_preset_editor.currentData()
        ext = next(
            v['output_extension'] for v in ffmpeg.PRESETS.values() if
            v['preset'] == preset
            )

        if self.ffmpeg_add_timecode_editor.isChecked():
            destination = f'{seq.group(1).strip().strip("_").strip(".")}' \
                          f'{seq.group(3).strip().strip("_").strip(".")}_tc.' \
                          f'{ext}'
        else:
            destination = f'{seq.group(1).strip().strip("_")}' \
                          f'{seq.group(3).strip().strip("_")}' \
                          f'{ext}'

        _f = QtCore.QFile(destination)
        if _f.exists():
            mbox = ui.MessageBox(
                f'{destination} already exists.',
                'Do you want to replace it with a new version?',
                buttons=[ui.YesButton, ui.CancelButton]
            )
            if mbox.exec_() == QtWidgets.QDialog.Rejected:
                return False
            if not _f.remove():
                raise RuntimeError(f'Could not remove {destination}')

        pbar = ui.get_progress_bar(
            'Pre-converting frames',
            f'Pre-converting {int(frames[-1]) - int(frames[0])} frames, please wait.',
            0,
            0,
            parent=self
        )
        pbar.setValue(0)

        pbar.open()
        QtWidgets.QApplication.instance().processEvents()

        jpeg_paths = self.oiio_process_frames()
        pbar.open()
        if pbar.wasCanceled():
            pbar.close()
            return

        timecode_preset = self.ffmpeg_timecode_preset_editor.currentData()
        if not timecode_preset:
            raise RuntimeError('No timecode preset was selected.')

        pbar.setLabelText('Making video frames (2/2)...')

        try:
            mov = ffmpeg.convert(
                jpeg_paths[0],
                self.ffmpeg_preset_editor.currentData(),
                size=self.ffmpeg_size_editor.currentData(),
                timecode=self.ffmpeg_add_timecode_editor.isChecked(),
                timecode_preset=timecode_preset,
                output_path=destination,
                parent=self
            )
        except:
            pbar.close()
            raise

        for f in jpeg_paths:
            images.ImageCache.flush(f)
            if not QtCore.QFile(f).remove():
                log.error(f'Failed to remove {f}')

        if not mov:
            pbar.close()
            raise RuntimeError('No movie file was saved.')

        if not QtCore.QFileInfo(mov).exists():
            pbar.close()
            raise RuntimeError(f'Could not find {mov}')

        common.widget(common.FileTab).show_item(
            destination,
            role=common.PathRole,
            update=True
        )

        if self.ffmpeg_pushtorv_editor.isChecked():
            try:
                rv.push(destination)
            except:
                log.error('Failed to push to RV.')

        ui.OkBox(f'Movie saved to {destination}').open()
        log.success(f'Movie saved to {destination}')
        return True

    def oiio_process_frames(self):
        """Convert the source frames to jpeg images using OpenImageIO.

        This allows us to feed more exotic sequences to FFMpeg, but the process comes with
        a significant performance cost.

        Returns:
            tuple: A tuple of jpeg file paths.

        """
        index = self._index
        seq = index.data(common.SequenceRole)

        frames = index.data(common.FramesRole)
        frames_it = (f for f in frames)
        all_frames = [str(f).zfill(len(frames[0])) for f in
                      range(int(frames[0]), int(frames[-1]) + 1)]

        _dir = QtCore.QDir(f'{common.temp_path()}/ffmpeg')
        if not _dir.exists():
            if not _dir.mkpath('.'):
                raise RuntimeError('Could not create ffmpeg temp dir')

        # Remove any frames in the temp directory
        for entry in os.scandir(_dir.path()):
            if entry.is_dir():
                continue
            _f = QtCore.QFile(entry.path)
            if not _f.remove():
                log.error(f'Could not remove {_f.filePath()}')

        # Preconvert source using OpenImageIO
        source_paths = []
        destination_paths = []

        for frame in all_frames:

            if frame in frames:
                source_frame = next(frames_it)

            source_path = f'{seq.group(1)}{source_frame}{seq.group(3)}.{seq.group(4)}'
            destination_path = f'{_dir.path()}/ffmpeg_{frame}.jpg'

            source_paths.append(source_path)
            destination_paths.append(destination_path)

        # Call the pre-conversion function
        try:
            if not pyimageutil.convert_images(source_paths, destination_paths, max_size=-1, release_gil=False):
                raise RuntimeError(f'{source_frame} could not be read')
            for f in destination_paths:
                if not os.path.isfile(f):
                    raise RuntimeError(f'{f} does not exist')

        except Exception:
            log.error('Pre-conversion failed')
            raise

        return destination_paths

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width) * 0.66,
            common.size(common.size_height) * 0.66
        )
